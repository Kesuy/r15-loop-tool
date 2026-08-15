import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from r15tool.cli import (
    _configure_text_stream,
    build_parser,
    generate,
    main,
    run_benchmark,
)


def test_console_stream_is_configured_for_safe_utf8_output():
    class FakeStream:
        options = None

        def reconfigure(self, **kwargs):
            self.options = kwargs

    stream = FakeStream()
    _configure_text_stream(stream)
    assert stream.options == {"encoding": "utf-8", "errors": "replace"}


def test_explicit_report_generates_without_interactive_prompt(
    tmp_path: Path, monkeypatch
):
    report = tmp_path / "scores.txt"
    output = tmp_path / "scores.html"
    report.write_text("Rendering (Multiple CPU) 1234.00 cb\n", encoding="utf-8")

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: (_ for _ in ()).throw(AssertionError("unexpected prompt")),
    )

    assert main(["--report", str(report), "--output", str(output), "--no-open"]) == 0
    assert output.is_file()


def test_packaged_app_generates_and_opens_report_next_to_executable(
    tmp_path: Path, monkeypatch
):
    app_dir = tmp_path / "cinebench"
    app_dir.mkdir()
    executable = app_dir / "CINEBENCH Windows 64 Bit.exe"
    executable.touch()
    launch_dir = tmp_path / "unrelated-working-directory"
    launch_dir.mkdir()
    opened = []

    def fake_run(*_args, **kwargs):
        kwargs["stdout"].write(b"Rendering (Multiple CPU) 1234.00 cb\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.chdir(launch_dir)
    monkeypatch.setattr("r15tool.cli.sys.frozen", True, raising=False)
    monkeypatch.setattr("r15tool.cli.sys.executable", str(app_dir / "R15-loop.exe"))
    monkeypatch.setattr("r15tool.cli.subprocess.run", fake_run)
    if os.name == "nt":
        monkeypatch.setattr(
            "r15tool.cli.os.startfile",
            lambda path: opened.append(Path(path).resolve()),
            raising=False,
        )
    else:
        monkeypatch.setattr("r15tool.cli.webbrowser.open", lambda uri: opened.append(uri))

    assert main(["--runs", "1"]) == 0
    output = app_dir / "R15曲线图.html"
    assert output.is_file()
    expected_opened = output.resolve() if os.name == "nt" else output.resolve().as_uri()
    assert opened == [expected_opened]


@pytest.mark.parametrize(
    "encoding",
    ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gb18030"],
)
def test_generate_reads_windows_report_encodings(tmp_path: Path, encoding: str):
    report = tmp_path / "R15benchmark.txt"
    output = tmp_path / "R15曲线图.html"
    report.write_bytes("Rendering (Multiple CPU) 1234.00 cb\r\n".encode(encoding))

    result = generate(report, output, open_browser=False)

    assert result == output.resolve()
    assert output.is_file()
    assert "1,234 cb" in output.read_text(encoding="utf-8")


def test_generate_opens_only_after_html_exists(tmp_path: Path, monkeypatch):
    report = tmp_path / "R15benchmark.txt"
    output = tmp_path / "R15曲线图.html"
    report.write_text("Rendering (Multiple CPU) 1234 cb\n", encoding="utf-8")
    opened = []

    if os.name == "nt":
        monkeypatch.setattr(
            "r15tool.cli.os.startfile",
            lambda path: opened.append((Path(path), output.is_file())),
            raising=False,
        )
    else:
        monkeypatch.setattr(
            "r15tool.cli.webbrowser.open",
            lambda uri: opened.append((uri, output.is_file())),
        )

    generate(report, output)

    assert opened and opened[0][1] is True


def test_runs_and_existing_report_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--runs", "2", "--report", "existing.txt"])


def test_generate_refuses_to_overwrite_source_report(tmp_path: Path):
    report = tmp_path / "scores.txt"
    report.write_text("Rendering (Multiple CPU) 1234 cb\n", encoding="utf-8")

    with pytest.raises(ValueError, match="不能是同一个文件"):
        generate(report, report, open_browser=False)

    assert report.read_text(encoding="utf-8").startswith("Rendering")


def test_generate_refuses_hard_link_alias_of_source_report(tmp_path: Path):
    report = tmp_path / "scores.txt"
    output = tmp_path / "alias.html"
    report.write_text("Rendering (Multiple CPU) 1234 cb\n", encoding="utf-8")
    os.link(report, output)

    with pytest.raises(ValueError, match="不能是同一个文件"):
        generate(report, output, open_browser=False)

    assert report.read_text(encoding="utf-8").startswith("Rendering")


def test_benchmark_runs_from_cinebench_directory(tmp_path: Path, monkeypatch):
    executable = tmp_path / "cinebench" / "CINEBENCH Windows 64 Bit.exe"
    executable.parent.mkdir()
    executable.touch()
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("r15tool.cli.subprocess.run", fake_run)
    run_benchmark(executable, tmp_path / "report.txt", 1)

    assert calls[0][1]["cwd"] == executable.parent


def test_main_rejects_benchmark_executable_as_report_before_running(
    tmp_path: Path, monkeypatch
):
    executable = tmp_path / "R15benchmark.txt"
    executable.write_bytes(b"original executable")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "r15tool.cli.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert main(["--runs", "1", "--cinebench", str(executable), "--no-open"]) == 1
    assert executable.read_bytes() == b"original executable"


def test_main_rejects_report_as_html_output_before_running(tmp_path: Path, monkeypatch):
    executable = tmp_path / "CINEBENCH Windows 64 Bit.exe"
    executable.touch()
    report = tmp_path / "R15benchmark.txt"
    report.write_text("existing report", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "r15tool.cli.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert main(["--runs", "1", "--output", str(report), "--no-open"]) == 1
    assert report.read_text(encoding="utf-8") == "existing report"


def test_main_rejects_benchmark_executable_as_html_output_before_running(
    tmp_path: Path, monkeypatch
):
    executable = tmp_path / "CINEBENCH Windows 64 Bit.exe"
    executable.write_bytes(b"original executable")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "r15tool.cli.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert (
        main(
            [
                "--runs",
                "1",
                "--cinebench",
                str(executable),
                "--output",
                str(executable),
                "--no-open",
            ]
        )
        == 1
    )
    assert executable.read_bytes() == b"original executable"


@pytest.mark.parametrize("alias_role", ["report", "output"])
def test_main_rejects_hard_link_alias_of_executable_before_running(
    tmp_path: Path, monkeypatch, alias_role: str
):
    executable = tmp_path / "CINEBENCH Windows 64 Bit.exe"
    executable.write_bytes(b"original executable")
    alias = tmp_path / ("R15benchmark.txt" if alias_role == "report" else "alias.html")
    os.link(executable, alias)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "r15tool.cli.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    arguments = ["--runs", "1", "--cinebench", str(executable), "--no-open"]
    if alias_role == "output":
        arguments.extend(["--output", str(alias)])

    assert main(arguments) == 1
    assert executable.read_bytes() == b"original executable"
