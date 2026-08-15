from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from statistics import mean

_SCORE_LINE = re.compile(r"Rendering\s*\(Multiple CPU\)(.*)", re.IGNORECASE)
_SCORE_VALUE = re.compile(
    r"(?<![\d,])((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:cb|pts?)\b",
    re.IGNORECASE,
)


def parse_scores(text: str) -> list[float]:
    """从 Cinebench R15 文本输出中提取所有多核得分。"""
    scores: list[float] = []
    for line in text.splitlines():
        match = _SCORE_LINE.search(line)
        if not match:
            continue
        score = _SCORE_VALUE.search(match.group(1))
        if score:
            scores.append(float(score.group(1).replace(",", "")))
    if not scores:
        raise ValueError("未找到 Cinebench R15 多核跑分结果")
    return scores


def axis_bounds(scores: Iterable[float]) -> tuple[float, float]:
    """根据实际分数生成带留白的易读 Y 轴范围。"""
    values = list(scores)
    if not values:
        raise ValueError("至少需要一个跑分结果")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("跑分结果必须是有限数字")
    minimum, maximum = min(values), max(values)
    spread = maximum - minimum
    padding = max(spread * 0.12, abs(maximum) * 0.02, 10)
    raw_step = max((spread + 2 * padding) / 8, 1)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude
    nice = (
        1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    )
    step = nice * magnitude
    lower = max(0, math.floor((minimum - padding) / step) * step)
    upper = math.ceil((maximum + padding) / step) * step
    if lower == upper:
        upper = lower + step
    return lower, upper


def _display_number(value: float) -> str:
    return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"


def render_report(scores: Iterable[float], output: str | Path) -> Path:
    """生成固定视口高度、可缩放且会随窗口调整大小的 HTML 报告。"""
    values = [float(value) for value in scores]
    if not values:
        raise ValueError("至少需要一个跑分结果")
    output_path = Path(output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    y_min, y_max = axis_bounds(values)
    count = len(values)
    labels = list(range(1, count + 1))
    show_labels = count <= 30
    show_zoom = count > 60
    initial_end = min(100.0, 60 / count * 100)
    label_interval = max(0, math.ceil(min(count, 60) / 15) - 1)
    data_zoom = (
        [
            {
                "type": "inside",
                "start": 0,
                "end": initial_end,
                "zoomOnMouseWheel": True,
            },
            {
                "type": "slider",
                "start": 0,
                "end": initial_end,
                "height": 24,
                "bottom": 24,
            },
        ]
        if show_zoom
        else []
    )
    option = {
        "animation": count <= 500,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "line", "lineStyle": {"color": "#94a3b8"}},
            "valueFormatter": "__FORMATTER__",
        },
        "grid": {
            "left": 72,
            "right": 96,
            "top": 64,
            "bottom": 92 if show_zoom else 58,
        },
        "xAxis": {
            "type": "category",
            "name": "循环次数",
            "nameLocation": "middle",
            "nameGap": 42,
            "boundaryGap": False,
            "data": labels,
            "axisLabel": {"hideOverlap": True, "interval": label_interval},
        },
        "yAxis": {
            "type": "value",
            "name": "得分 (cb)",
            "min": y_min,
            "max": y_max,
            "scale": True,
            "splitLine": {"lineStyle": {"color": "#e5e7eb"}},
        },
        "dataZoom": data_zoom,
        "series": [
            {
                "name": "R15 多核得分",
                "type": "line",
                "data": values,
                "showSymbol": count <= 120,
                "symbolSize": 7,
                "sampling": "lttb",
                "lineStyle": {"width": 2, "color": "#2563eb"},
                "itemStyle": {"color": "#2563eb"},
                "areaStyle": {"color": "rgba(37, 99, 235, 0.08)"},
                "label": {
                    "show": show_labels,
                    "position": "top",
                    "distance": 8,
                    "color": "#334155",
                    "fontSize": 11,
                    "backgroundColor": "rgba(255,255,255,.82)",
                    "borderRadius": 3,
                    "padding": [2, 4],
                    "formatter": "{c}",
                },
                "labelLayout": {"hideOverlap": True},
                "markPoint": {
                    "symbol": "circle",
                    "symbolSize": 16,
                    "label": {"show": False},
                    "tooltip": {"formatter": "{b}: {c} cb"},
                    "data": [
                        {
                            "type": "max",
                            "name": "最高分",
                            "itemStyle": {
                                "color": "#16a34a",
                                "borderColor": "#ffffff",
                                "borderWidth": 3,
                            },
                        },
                        {
                            "type": "min",
                            "name": "最低分",
                            "itemStyle": {
                                "color": "#dc2626",
                                "borderColor": "#ffffff",
                                "borderWidth": 3,
                            },
                        },
                    ]
                },
                "markLine": {
                    "symbol": ["none", "none"],
                    "lineStyle": {"color": "#64748b", "type": "dashed"},
                    "label": {
                        "formatter": "平均 {c}",
                        "color": "#475569",
                        "backgroundColor": "rgba(255,255,255,.92)",
                        "borderRadius": 4,
                        "padding": [3, 6],
                    },
                    "data": [{"type": "average", "name": "平均值"}],
                },
            }
        ],
    }
    option_json = json.dumps(option, ensure_ascii=False, separators=(",", ":"))
    option_json = option_json.replace('"__FORMATTER__"', "value => `${value} cb`")
    hint = (
        "可拖动底部滑块或使用鼠标滚轮缩放；双击图表可恢复全部数据。"
        if show_zoom
        else "将鼠标移到数据点可查看成绩；绿色为最高分，红色为最低分。"
    )
    average = mean(values)
    table_rows = "".join(
        f"<tr><td>{index}</td><td>{_display_number(value)} cb</td>"
        f"<td>{value - average:+,.2f} cb</td></tr>"
        for index, value in enumerate(values, start=1)
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cinebench R15 循环跑分报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js" integrity="sha384-pPi0zxBAoDu6+JXW/C68UZLvBUUtU+7zonhif43rqj7pxsGyqyqzcian2Rj37Rss" crossorigin="anonymous"></script>
<style>
:root {{ color-scheme: light; font-family: Inter, "Microsoft YaHei", system-ui, sans-serif; color: #172033; background: #f3f6fb; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: clamp(12px, 2.5vw, 32px); }}
main {{ width: min(100%, 1600px); margin: 0 auto; }}
h1 {{ margin: 0 0 18px; font-size: clamp(22px, 3vw, 34px); }}
.stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }}
.stat, .chart-shell {{ background: #fff; border: 1px solid #e5eaf2; border-radius: 14px; box-shadow: 0 7px 24px rgba(30, 48, 80, .07); }}
.stat {{ padding: 14px 16px; }}
.stat span {{ display: block; color: #667085; font-size: 13px; }}
.stat strong {{ display: block; margin-top: 5px; font-size: clamp(18px, 2vw, 25px); }}
.chart-shell {{ width: 100%; padding: 10px; overflow: hidden; }}
#chart {{ width: 100%; height: min(68vh, 640px); min-height: 420px; }}
.hint {{ margin: 12px 4px 0; color: #667085; font-size: 13px; }}
.raw-data {{ margin-top: 14px; padding: 12px 16px; background: #fff; border: 1px solid #e5eaf2; border-radius: 12px; }}
.raw-data summary {{ cursor: pointer; color: #475569; font-weight: 600; }}
.table-wrap {{ margin-top: 12px; max-height: 320px; overflow: auto; }}
table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 9px 12px; border-bottom: 1px solid #eef2f6; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ position: sticky; top: 0; background: #f8fafc; color: #475569; font-size: 13px; }}
.chart-error {{ display: grid; place-items: center; padding: 32px; color: #b42318; text-align: center; }}
@media (max-width: 700px) {{ .stats {{ grid-template-columns: repeat(2, 1fr); }} body {{ padding: 10px; }} #chart {{ min-height: 360px; }} }}
@media print {{ body {{ padding: 0; background: #fff; }} .stat, .chart-shell, .raw-data {{ box-shadow: none; }} .hint {{ display: none; }} .table-wrap {{ max-height: none; overflow: visible; }} }}
</style>
</head>
<body>
<main>
<h1>Cinebench R15 循环跑分报告</h1>
<section class="stats" aria-label="跑分摘要">
<div class="stat"><span>循环次数</span><strong>{count} 次</strong></div>
<div class="stat"><span>最高分</span><strong>{_display_number(max(values))} cb</strong></div>
<div class="stat"><span>最低分</span><strong>{_display_number(min(values))} cb</strong></div>
<div class="stat"><span>平均分</span><strong>{_display_number(mean(values))} cb</strong></div>
</section>
<section class="chart-shell"><div id="chart" role="img" aria-label="R15 多核得分折线图"></div></section>
<p class="hint">{hint}</p>
<details class="raw-data">
<summary>查看详细成绩</summary>
<div class="table-wrap"><table>
<thead><tr><th>循环</th><th>得分</th><th>较平均分</th></tr></thead>
<tbody>{table_rows}</tbody>
</table></div>
</details>
</main>
<script>
const chartElement = document.getElementById("chart");
if (typeof echarts === "undefined") {{
  chartElement.className = "chart-error";
  chartElement.textContent = "图表组件加载失败，请检查网络连接后刷新页面；详细成绩仍可在下方查看。";
}} else {{
  const chart = echarts.init(chartElement, null, {{ renderer: "canvas" }});
  const option = {option_json};
  chart.setOption(option);
  new ResizeObserver(() => chart.resize()).observe(chartElement);
  chart.getZr().on("dblclick", () => chart.dispatchAction({{ type: "dataZoom", start: 0, end: 100 }}));
}}
</script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
