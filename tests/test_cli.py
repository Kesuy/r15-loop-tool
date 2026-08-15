from pathlib import Path
from types import SimpleNamespace

import pytest

from r15tool.cli import build_parser, generate, main, run_benchmark


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


def test_runs_and_existing_report_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--runs", "2", "--report", "existing.txt"])


def test_generate_refuses_to_overwrite_source_report(tmp_path: Path):
    report = tmp_path / "scores.txt"
    report.write_text("Rendering (Multiple CPU) 1234 cb\n", encoding="utf-8")

    with pytest.raises(ValueError, match="不能是同一个文件"):
        generate(report, report, open_browser=False)

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
