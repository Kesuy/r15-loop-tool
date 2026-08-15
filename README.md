# R15 循环跑分工具

用于自动循环运行 **Cinebench R15 多核测试**，也可读取已有的 `R15benchmark.txt`，生成响应式 HTML 折线图。

## 主要改进

- 图表宽度固定为浏览器可视区域的 `100%`，不再按循环次数扩展到超宽页面。
- 图表高度限制在当前视口内，大量循环不会把页面无限拉长。
- Y 轴根据实际成绩动态计算范围，不再固定为 `0–6500`，分数波动更清晰。
- 超过 30 次时自动隐藏逐点标签，避免文字重叠。
- 大量数据默认显示前 60 次，可通过底部滑块、鼠标滚轮缩放和拖动查看全部结果。
- 窗口大小变化时自动重绘；双击图表恢复显示全部数据。
- 顶部显示循环次数、最高分、最低分和平均分。

## Windows EXE 使用方法

1. 把 `R15循环工具-<版本>-windows-x86_64.exe` 放入 Cinebench R15 根目录。
2. 双击运行。
3. 输入 `Y` 并填写循环次数，或输入 `N` 读取已有的 `R15benchmark.txt`。
4. 完成后自动生成并打开 `R15曲线图.html`。

> HTML 图表使用 ECharts CDN，首次打开时需要联网加载图表脚本。

## 命令行用法

直接读取已有结果，不进入交互模式：

```powershell
.\R15循环工具.exe --report R15benchmark.txt --output R15曲线图.html --no-open
```

自动跑 10 次：

```powershell
.\R15循环工具.exe --runs 10
```

查看完整参数：

```powershell
.\R15循环工具.exe --help
```

## 本地开发

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

Windows 打包：

```powershell
pyinstaller --noconfirm --clean --onefile --console --name "R15循环工具" --icon icon.ico main.py
```

## 测试覆盖

- Cinebench 多核成绩解析
- 无成绩时的错误处理
- 动态 Y 轴比例尺
- 250 次循环的固定页面尺寸、缩放控件、标签降噪与 HTML 大小
- 读取指定报告时不触发交互输入
- GitHub Actions 中对真实 Windows EXE 进行报告生成 smoke test
