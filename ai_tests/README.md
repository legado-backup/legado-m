# ai_tests — Legado E2E 自动化测试基础设施（V3）

> 自动化端到端测试框架：APK 自动部署 → UI 自动执行 → 8 类证据收集 → 规则判定 → 七件套报告

## 5 分钟上手

### 前置条件

1. MEmu 模拟器已安装（`D:\Program Files\Microvirt\MEmu\`）
2. APK 已构建（`app/build/outputs/apk/app/debug/`）
3. Python 3.12 + 虚拟环境（`ai_tests/venv/`）

### 快速开始

```bash
# 1. 激活虚拟环境
ai_tests\venv\Scripts\activate

# 2. 全量测试（自动发现 APK + 全部用例）
python ai_tests/run_e2e.py --apk auto --tc all

# 3. 查看报告
# 报告输出到 ai_tests/reports/report_{timestamp}/
# 打开 report.md 查看人读报告
# 打开 summary.txt 查看一行摘要
```

## CLI 参数

### 基础参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--apk` | `auto` | APK 路径（`auto`=自动发现最新 APK） |
| `--tc` | `all` | 用例筛选（`all`/`P0`/`P1`/模块名/`TC-ID`） |
| `--report-dir` | 自动生成 | 报告输出目录 |
| `--no-rules` | 关闭 | 禁用规则判定（仅收集证据） |
| `--keep-device` | 关闭 | 测试完成后保留模拟器运行 |
| `--instance-id` | `0` | MEmu 实例 ID |
| `--init-device` | 关闭 | 强制重新初始化 uiautomator2 |

### V3 新增参数

| 参数 | 说明 | 状态 |
|------|------|------|
| `--diff <git_ref>` | 源码影响分析，自动选复测用例 | ⚠️ M8 未实现，降级为 `--tc all` |
| `--gen-test <Activity>` | 为 Activity 生成 Python 测试骨架 | ⚠️ M9 未实现，仅提示 |
| `--update-source-map` | 重建 source_map.json | ⚠️ M8 未实现，仅提示 |
| `--feedback` | 触发反馈闭环处理 | ⚠️ M16 未实现，仅提示 |

## 用例筛选示例

```bash
# 全量测试
python ai_tests/run_e2e.py --tc all

# 仅 P0 优先级用例
python ai_tests/run_e2e.py --tc P0

# 指定模块（如 F-P0-1 调试工具）
python ai_tests/run_e2e.py --tc F-P0-1

# 单用例
python ai_tests/run_e2e.py --tc TC-F-P0-1-01
```

## V3 双轨调度

V3 引入双轨调度机制：同 TC-ID 时 **Python 轨道优先于 MD 轨道**。

| 轨道 | 来源 | 优先级 | 状态 |
|------|------|--------|------|
| **MD 轨道（A 轨）** | `docs/tests/*.md` + `ai_tests/cases/*/case.md` | 低 | ✅ 已实现（UiExecutor 执行） |
| **Python 轨道（B 轨）** | `ai_tests/cases/*/auto_*.py` | 高 | ⚠️ M9 未实现，降级为 MD 执行 |

调度逻辑（M3 CaseParser 解析阶段处理）：
1. 扫描 `ai_tests/cases/{module}/auto_*.py` 寻找同 TC-ID 的 B 轨用例
2. 若存在 B 轨，则 `track_source="python"`，否则 `track_source="md"`
3. run_e2e.py 执行时检查 `track_source`，B 轨优先执行

> **当前状态**：M9 sourceTestGenerator 未实现，B 轨 Python 用例暂无法自动生成。检测到 `track_source="python"` 时降级为 MD 执行并 warn。M9 实现后，B 轨将自动执行 `auto_*.py`。

## V3 参数示例（降级模式）

```bash
# 源码影响分析（M8 未实现时降级为全量测试）
python ai_tests/run_e2e.py --diff HEAD~1

# 生成测试骨架（M9 未实现时仅提示）
python ai_tests/run_e2e.py --gen-test BookshelfActivity

# 反馈闭环（M16 未实现时仅提示）
python ai_tests/run_e2e.py --feedback
```

## 报告输出

执行后生成七件套报告（`ai_tests/reports/report_{timestamp}/`）：

| 文件 | 说明 |
|------|------|
| `report.md` | 人读报告（失败用例置顶 + manual 用例置顶 + 全部用例表 + V3 affected/feedback 节） |
| `report.json` | 机器可读（AI agent 接入，含 evidence_collected/ai_prompt_path/track_source） |
| `manual_cases.md` | manual 用例清单 + AI agent 接入流程 |
| `summary.txt` | 一行摘要（`pass:N/M fail:N manual:N pass_rate:X%`） |
| `affected_modules.json` | V3 受影响模块（`--diff` 时生成） |
| `feedback_suggestions.md` | V3 反馈建议（人读，规则/提示词/陷阱库建议） |
| `feedback_suggestions.json` | V3 反馈建议（机器读，M16 回填） |

### 证据归档

每用例独立目录 `cases/{tc_id}/`，包含 8 类证据：

```
cases/TC-F-P0-1-01/
├── step-01-*.png|xml     # 截图 + UI XML
├── log-slice.txt         # 日志切片
├── activity-stack.txt     # Activity 栈
├── db-state.json         # 数据库状态（MEmu 无 run-at 时降级）
├── prefs-state.json      # SharedPreferences（同上）
├── web-api-resp.json     # Web API 响应（未启动时降级）
├── meminfo.txt           # 内存状态
└── ai-prompt.md          # AI agent 分析提示词（manual 时）
```

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 全部通过 |
| `1` | 部分失败（有 fail 或 manual） |
| `2` | 致命错误（环境/APK/模拟器故障） |

CI/CD 集成示例：

```bash
python ai_tests/run_e2e.py --apk auto --tc all
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✅ 全部通过"
elif [ $exit_code -eq 1 ]; then
    echo "⚠️ 部分失败，查看报告"
else
    echo "❌ 致命错误"
fi
```

## 架构概览

```
Layer 3: 编排层（run_e2e.py）
  ↓
Layer 2: 用例与执行层
  M3 用例解析器 → M4 UI 执行器 → M5 证据收集器
  ↓
Layer 1: 基础设施层
  M1 模拟器控制 → M2 APK 部署 → M6 规则分析器 → M7 报告生成器
  ↓
Layer 0: 源码驱动层（V3，阶段 12-13）
  M8 源码影响分析器 → M9 源码→测试生成器
```

## 脚本清单（ai_tests/scripts/）

> 本节仅列出 RSS 批量优化阶段新增的验证 / 诊断 / 修复脚本。完整脚本清单见 `ai_tests/scripts/` 目录。所有脚本均通过 `ai_tests/venv/Scripts/python.exe` 执行。

### RSS 真机 DB 验证脚本

| 脚本 | 用途 | 用法 | 输出 |
|------|------|------|------|
| `real_db_sample_test.py` | 从真机 DB 抽样订阅源，用 Playwright 验证 sourceUrl 可访问性 / sortUrl 分类列表加载 / searchUrl 搜索功能 / ruleNextPage 下一页链接 / type=2 视频元素存在性 | `python ai_tests/scripts/real_db_sample_test.py` | `output/rss/v2_real_test_db_sample.json` |
| `real_db_full_test_v2.py` | 在 v1 基础上扩展 DOM 选择器（list / pagination / categories / search_form），对全部源做全量验证（每源 5s 超时，每 20 源增量保存，支持 Ctrl+C 中断保存） | `python ai_tests/scripts/real_db_full_test_v2.py` | `output/rss/v2_real_test_db_sample_v2.json` |

### DB 字段诊断与补全脚本

| 脚本 | 用途 | 用法 | 输出 |
|------|------|------|------|
| `diagnose_db_fields.py` | 诊断 DB 中订阅源 `sortUrl` / `searchUrl` / `ruleNextPage` / `ruleArticles` 字段填充率，按 `type` 分组统计 | `python ai_tests/scripts/diagnose_db_fields.py` | `output/rss/db_field_diagnose_v3.json` |
| `fix_image_source_fields.py` | 筛选 `type=1` 且 `sortUrl` 为空的源，用 Playwright 访问首页提取 `sortUrl` / `searchUrl` / `ruleArticles` / `ruleImage` / `ruleNextPage`（每 10 源增量保存） | `python ai_tests/scripts/fix_image_source_fields.py` | `output/rss/image_source_field_fix.json` |

### 失败源重试脚本

| 脚本 | 用途 | 用法 | 输出 |
|------|------|------|------|
| `retry_failed_rss_sources.py` | 读取真机 DB 全部源，用 Playwright 识别访问失败源，对每个失败源用 14 种技术手段（5 种 UA + 多种重试策略）依次重试，输出脱敏 JSON 报告 | `python ai_tests/scripts/retry_failed_rss_sources.py` | `output/rss/failed_source_retry_v2.json` + `failed_sources_list.json` + `retry_run.log` |

### 输出安全约束

上述脚本均内置脱敏机制，输出报告遵循以下约束：
- 用 `源[idx]` 替代真实名称
- URL 替换为 `[URL]`，域名替换为 `[DOMAIN]`，IP 替换为 `[IP]`
- 异常消息正则脱敏，禁止输出 cookie / token / 分类名原文

## 相关文档

- [设计文档](../docs/specs/e2e-automated-testing/design.md)
- [任务清单](../docs/specs/e2e-automated-testing/tasks.md)
- [深度分析报告](../docs/specs/e2e-automated-testing/ai-testing-research-2026.md)

## V5 订阅源批量优化脚本

### V5 阶段脚本（ai_tests/scripts/）

| 脚本 | 功能 |
|------|------|
| `v5_aggregator_split.py` | 集成站V2严格拆分（8项视频特征严格判定） |
| `v5_inspect_sorturl.py` | sortUrl检查工具 |
| `v5_video_deep_analyze.py` | 视频源深度分析 |
| `v5_video_deepfix.py` | 视频源深度修复（118个源详情页深度分析） |
| `v5_video_deepfix_mask.py` | 视频源脱敏 |
| `v5_video_breakthrough.py` | 视频源6大突破手段（88个无证据源应用6策略） |
| `v5_missing_fields_fix.py` | 135个缺字段源深度补全 |
| `v5_hard_source_fix.py` | 67个难点源处理（CF盾/登录/弹框） |
| `v5_cf_breakthrough.py` | CF盾4个破盾5大技术 |
| `v5_spa_breakthrough.py` | 3个SPA站点5大技术突破 |
| `v5_2_short_term_fix.py` | V5.2短期止损修复 |
| `v5_2_rule_verify.py` | PC Playwright验证ruleArticles |
| `v5_3_final_fix.py` | V5.3最终修复 |
| `v5_3_real_device_verify.py` | V5.3真机验证 |

### V5 工作流

1. **V5阶段（深度优化）**：
   - 分类扫描 → 导航站拆分 → 集成站V2严格拆分 → 视频源深度修复 → 视频源6大突破 → 缺字段补全 → 难点源处理 → CF盾破盾 → SPA突破
2. **V5.1阶段（字段类型修复）**：
   - 修复Gson严格类型解析错误 → 生成纯数组格式JSON
3. **V5.2阶段（短期止损）**：
   - 移除113个失效拆分子源 → 字段修复197处
4. **V5.3阶段（最终修复）**：
   - PC Playwright验证224源 → 修复6个规则问题源 → 标记153个网络层失败源enabled=false → 保留71个可用源

### V5 输出JSON（output/rss/）

| 文件 | 内容 |
|------|------|
| `optimized_v5_1_app_import_fixed.json` | V5.1最终版（328源，纯数组格式） |
| `optimized_v5_2_stable.json` | V5.2短期止损版（224源） |
| `optimized_v5_3_final.json` | V5.3最终版（224源，71启用+153禁用） |

### V5 关键报告

- `docs/specs/rss-batch-optimize-v2/v5_optimization_final_report.md` - V5优化最终成果报告
- `output/rss/v5_1_real_device_verify_report.md` - V5.1真机验证报告
- `output/rss/v5_1_field_diff_analysis.md` - V5.1字段差异分析
- `output/rss/v5_2_rule_verify_report.md` - V5.2 PC Playwright验证报告
- `output/rss/v5_3_final_verify_report.md` - V5.3最终验证报告
