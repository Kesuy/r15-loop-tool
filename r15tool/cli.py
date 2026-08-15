from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from .report import parse_scores, render_report

DEFAULT_BENCHMARK = "R15benchmark.txt"
DEFAULT_OUTPUT = "R15曲线图.html"
DEFAULT_EXE = "CINEBENCH Windows 64 Bit.exe"


def _same_file(first: Path, second: Path) -> bool:
    try:
        return first.samefile(second)
    except OSError:
        return first.resolve() == second.resolve()


def run_benchmark(executable: Path, report: Path, runs: int) -> None:
    if runs < 1:
        raise ValueError("循环次数必须大于 0")
    if not executable.is_file():
        raise FileNotFoundError(f"未找到 Cinebench：{executable}")
    for index in range(runs):
        mode = "wb" if index == 0 else "ab"
        with report.open(mode) as stream:
            completed = subprocess.run(
                [str(executable), "-cb_cpux"],
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
                cwd=executable.parent,
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"第 {index + 1} 次跑分失败，退出码 {completed.returncode}"
            )
        print(f"已经完成第 {index + 1} 次")


def generate(report: Path, output: Path, *, open_browser: bool = True) -> Path:
    if _same_file(report, output):
        raise ValueError("跑分报告和 HTML 输出不能是同一个文件")
    scores = parse_scores(report.read_text(encoding="utf-8", errors="ignore"))
    result = render_report(scores, output)
    if open_browser:
        if os.name == "nt":
            os.startfile(result)  # type: ignore[attr-defined]
        else:
            webbrowser.open(result.as_uri())
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cinebench R15 循环跑分与 HTML 报告工具"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--runs", type=int, help="执行跑分的循环次数")
    parser.add_argument(
        "--cinebench",
        type=Path,
        default=Path(DEFAULT_EXE),
        help="Cinebench R15 可执行文件",
    )
    mode.add_argument(
        "--report", type=Path, help=f"读取已有跑分文本文件（默认：{DEFAULT_BENCHMARK}）"
    )
    parser.add_argument(
        "--output", type=Path, default=Path(DEFAULT_OUTPUT), help="输出 HTML 文件"
    )
    parser.add_argument("--no-open", action="store_true", help="生成后不自动打开浏览器")
    return parser


def _interactive_runs() -> int | None:
    while True:
        choice = (
            input("输入 Y 开始循环，输入 N 读取已有文件，按 Enter 确认: ")
            .strip()
            .lower()
        )
        if choice == "n":
            return None
        if choice == "y":
            try:
                runs = int(input("请输入 R15 循环次数，按 Enter 确认: "))
                if runs > 0:
                    return runs
            except ValueError:
                pass
            print("循环次数必须是大于 0 的整数。")
            continue
        print("无效输入，请输入 Y 或 N。")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("Cinebench R15 循环跑分工具")
    try:
        report = (args.report or Path(DEFAULT_BENCHMARK)).resolve()
        output = args.output.resolve()
        executable = args.cinebench.resolve()
        runs = (
            args.runs
            if args.runs is not None or args.report is not None
            else _interactive_runs()
        )
        if _same_file(report, output):
            raise ValueError("跑分报告和 HTML 输出不能是同一个文件")
        if runs is not None and _same_file(report, executable):
            raise ValueError("Cinebench 可执行文件和跑分报告不能是同一个文件")
        if runs is not None and _same_file(output, executable):
            raise ValueError("Cinebench 可执行文件和 HTML 输出不能是同一个文件")
        if runs is not None:
            run_benchmark(executable, report, runs)
        result = generate(report, output, open_browser=not args.no_open)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    print(f"图表已保存到：{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
