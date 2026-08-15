from pathlib import Path

import pytest

from r15tool.report import axis_bounds, parse_scores, render_report

SAMPLE = """CINEBENCH 15.0
Rendering (Multiple CPU) 1245.67 cb
noise
Rendering (Multiple CPU) 1310.20 cb
"""


def test_parse_scores_extracts_multiple_cpu_results():
    assert parse_scores(SAMPLE) == [1245.67, 1310.20]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Rendering (Multiple CPU) 1234.00 cb in 65.2 seconds", 1234.0),
        ("Rendering (Multiple CPU): 1234 cb (16 CPUs)", 1234.0),
        ("Rendering (Multiple CPU) 1,234 cb", 1234.0),
        ("Rendering (Multiple CPU) : 4649.00 pts", 4649.0),
        ("Rendering (Multiple CPU) : 4769.29 pt", 4769.29),
    ],
)
def test_parse_scores_uses_the_value_with_the_score_unit(line: str, expected: float):
    assert parse_scores(line) == [expected]


def test_parse_scores_rejects_report_without_results():
    with pytest.raises(ValueError, match="未找到"):
        parse_scores("CINEBENCH 15.0\nno score here")


@pytest.mark.parametrize(
    "malformed",
    ["Rendering (Multiple CPU) pass 16 of 20", "Rendering (Multiple CPU) 1,2 cb"],
)
def test_parse_scores_rejects_malformed_score(malformed: str):
    with pytest.raises(ValueError, match="未找到"):
        parse_scores(malformed)


def test_axis_bounds_scale_to_the_actual_score_range():
    low, high = axis_bounds([1200, 1250, 1300])
    assert low < 1200
    assert high > 1300
    assert high - low < 6500


def test_axis_bounds_handles_equal_scores():
    low, high = axis_bounds([1500, 1500])
    assert low < 1500 < high


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_axis_bounds_rejects_non_finite_scores(invalid: float):
    with pytest.raises(ValueError, match="有限数字"):
        axis_bounds([invalid])


def test_large_report_stays_responsive_and_uses_zoom(tmp_path: Path):
    scores = [1200 + index % 37 for index in range(250)]
    output = tmp_path / "report.html"

    render_report(scores, output)

    html = output.read_text(encoding="utf-8")
    assert 'class="chart-shell"' in html
    assert "width: 100%" in html
    assert "height: min(68vh, 640px)" in html
    assert '"type":"slider"' in html
    assert '"type":"inside"' in html
    assert '"show":false' in html
    assert '"right":72' in html
    assert '"interval":3' in html
    assert 'integrity="sha384-' in html
    assert "ResizeObserver" in html
    assert "250 次" in html
    assert len(html) < 150_000


def test_short_report_shows_point_labels(tmp_path: Path):
    output = tmp_path / "report.html"
    render_report([1200, 1210, 1220], output)
    html = output.read_text(encoding="utf-8")
    assert '"show":true' in html
