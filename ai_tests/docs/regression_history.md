# 回归历史

> 由 M16 反馈闭环自动追加，AI 审阅后可补充分析。
>
> **文件性质**：持续迭代层文件。M16 `feedback_loop.py` 运行时以追加模式（`"a"`）向本文件末尾追加表格行，初始表头会被保留。

## 字段说明

| 字段 | 说明 | 数据来源 |
|------|------|---------|
| 时间 | 反馈闭环执行时间（ISO 8601 截断到秒） | `datetime.now().isoformat()[:19]` |
| APK 版本 | 当前测试的 APK 文件名 | `report.apk_info.name` |
| 用例数 | 本轮回归执行的用例总数 | `len(report.cases)` |
| pass | 判定为 pass 的用例数 | `verdict == "pass"` 计数 |
| fail | 判定为 fail 的用例数 | `verdict == "fail"` 计数 |
| manual | 判定为 manual（需人工判定）的用例数 | `verdict == "manual"` 计数 |
| pass率 | pass 用例占比（百分比，保留 1 位小数） | `pass / total * 100` |
| manual率 | manual 用例占比（百分比，保留 1 位小数） | `manual / total * 100` |
| 失败模式Top3 | fail/manual 用例中失败模式出现频率 Top3 | `feedback_signal.failure_pattern` 或 `reason[:30]` 聚合排序 |

### 反馈闭环触发次数

每次运行 `feedback_loop.py process(report)` 即触发一次反馈闭环，对应表格中的一行记录。统计本文件的行数即为反馈闭环累计触发次数。

> 触发命令：`python -m ai_tests.lib.feedback_loop --report reports/{run_id}/report.json`
> 或通过 `python ai_tests/run_e2e.py --feedback`（编排层接入后自动触发）。

## 回归记录

| 时间 | APK 版本 | 用例数 | pass | fail | manual | pass率 | manual率 | 失败模式Top3 |
|------|---------|-------|------|------|--------|-------|---------|-------------|
