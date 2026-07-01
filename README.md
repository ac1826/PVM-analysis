# PVM 肉品产值分析报表

这是一个 GitHub Pages 静态看板，用于展示三厂每日 Excel 报表分析结果。项目采用数据处理和网页展示分离的结构，网页只读取标准 JSON 数据。

## 每日流程

1. 在本地启动上传工具。
2. 一次性上传蚌埠、大连、铁岭三个厂当天 Excel。
3. 点击“一键分析并同步到 GitHub Pages”。
4. 本仓库自动获得新的 JSON 数据。
5. GitHub Pages 读取最新数据并刷新看板。

## 数据契约

看板只依赖这三个位置：

- `data/latest.json`：最新日报，用于默认打开页面。
- `data/daily/YYYY-MM-DD.json`：每日历史数据，用于日期切换和后续趋势分析。
- `data/index.json`：日报日期索引，用于页面下拉选择。

`data/index.json` 示例：

```json
{
  "schema_version": 1,
  "latest_date": "2026-07-01",
  "dates": ["2026-07-01", "2026-06-30"]
}
```

## 页面文件

- `index.html`：GitHub Pages 看板模板。
- `data/`：日报数据。
- `.nojekyll`：让 GitHub Pages 直接按静态文件发布。

## 本地上传分析工具

本地工具路径：

```text
C:\Users\Lenovo\Documents\Codex\2026-07-01\w-x\daily_factory_dashboard
```

推荐启动命令：

```powershell
cd C:\Users\Lenovo\Documents\Codex\2026-07-01\w-x\daily_factory_dashboard
C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe -m streamlit run app.py --server.port 8502
```
