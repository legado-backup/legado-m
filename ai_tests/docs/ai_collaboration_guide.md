# AI 协作指南

> **定位**：AI agent 介入 V3 E2E 测试的实操手册（[S13](../../docs/project-rules/ai_e2e_testing_workflow.md) 是规范，本文是操作步骤）。
> **触发**：OpenSpec 步骤 5.5.6（manual 用例需 AI 判定）/ 5.5.8（反馈闭环需 AI 审阅）。
> **受众**：Claude/GPT 等 AI agent，或人工审查者。

---

## 一、AI agent 接入流程

### 1.1 触发时机

| 时机 | 触发条件 | 产物 |
|------|---------|------|
| 5.5.6 | verdict == manual（AI 无法自动判定） | ai-prompt.md + ai_verdict 回填 |
| 5.5.8 | 存在 fail/manual 用例 | feedback_suggestions.md/.json |

### 1.2 读取输入（5.5.6 manual 介入）

```bash
# 1. 获取报告目录（最新一次运行）
REPORT_DIR=$(ls -td ai_tests/reports/report_* | head -1)

# 2. 读取 manual 用例清单
cat $REPORT_DIR/manual_cases.md

# 3. 读取受影响模块（V3）
cat $REPORT_DIR/affected_modules.json

# 4. 对每个 manual 用例，读取证据
ls $REPORT_DIR/cases/{tc_id}/
# → step-XX-*.png（截图）
# → step-XX-*.xml（UI XML）
# → log-slice.txt（日志切片）

# 5. 读取判定指引
cat $REPORT_DIR/cases/{tc_id}/ai-prompt.md
```

### 1.3 给出判定

基于 ai-prompt.md 的判定指引 + 证据目录，对每个 manual 用例输出：

```json
{
  "tc_id": "TC-XXX",
  "ai_verdict": "pass",
  "ai_reason": "截图 step-01 显示搜索结果列表正常加载，log-slice 无 FATAL，符合预期 element_visible",
  "feedback_signal": null
}
```

若判定为 fail：

```json
{
  "tc_id": "TC-XXX",
  "ai_verdict": "fail",
  "ai_reason": "log-slice 含 NullPointerException，截图显示空白页",
  "feedback_signal": {
    "failure_pattern": "NullPointerException at BookAdapter",
    "suggested_rule": "add NullPointerException to CRASH_PATTERNS.Other",
    "suggested_prompt": "增加 adapter 判空提示"
  }
}
```

### 1.4 回填结果

将 ai_verdict 写入 `report.json` 的 `cases[].ai_verdict` 字段：

```bash
# Python 示例：回填 ai_verdict
python -c "
import json
p = '$REPORT_DIR/report.json'
r = json.load(open(p, encoding='utf-8'))
for c in r['cases']:
    if c['tc_id'] == 'TC-XXX':
        c['ai_verdict'] = 'pass'
        c['ai_reason'] = '截图正常'
json.dump(r, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

---

## 二、manual 用例处理流程

```
verdict == manual（5.5.5 规则判定无法自动确定）
  ↓
生成 ai-prompt.md（5.5.6，含证据摘要 + 预期结果 + 判定指引）
  ↓
AI agent 介入（1.2 读取 + 1.3 判定 + 1.4 回填）
  ↓
ai_verdict == pass → 用例通过
ai_verdict == fail → 进入失败用例处理流程（第三章）+ 触发反馈闭环
ai_verdict == manual（仍无法判定）→ 标记"需用户人工介入"，在 report.md 中置顶提示
```

---

## 三、失败用例处理流程

```
verdict == fail（5.5.5 规则判定失败）
  ↓
置顶到 report.md 失败用例区（5.5.7）
  ↓
提取 feedback_signal.failure_pattern（5.5.5 已输出）
  ↓
触发反馈闭环（5.5.8，见第四章）
  ↓
AI 修复代码 → 重新运行复测：
  python ai_tests/run_e2e.py --tc {失败TC-ID}
  ↓
复测通过 → 关闭失败；复测仍失败 → 继续反馈闭环
```

---

## 四、V3 反馈闭环处理流程（5.5.8）

### 4.1 触发

```bash
python ai_tests/run_e2e.py --feedback
```

M16 `FeedbackLoop.process` 读取 `report.json`，输出 4 类反馈建议到 `feedback_suggestions.md/.json`。

### 4.2 审阅 4 类建议

| 建议类型 | 文件 | AI 审阅动作 | 写入目标 |
|---------|------|------------|---------|
| `rule_suggestions` | feedback_suggestions.md | 审阅新异常模式 → 扩展崩溃规则 | `config.CRASH_PATTERNS`（固化层，需 OpenSpec） |
| `prompt_suggestions` | feedback_suggestions.md | 审阅 manual 调优建议 → 调优提示词 | `ai_tests/templates/ai_prompt_template.j2` |
| `known_issue_suggestions` | known_issues.md（已自动追加） | 补充规避方式 + 分类 | `ai_tests/docs/known_issues.md`（持续迭代层） |
| `regression_history_entry` | regression_history.md（已自动追加） | 可补充分析 | `ai_tests/docs/regression_history.md`（持续迭代层） |

### 4.3 沉淀操作

**规则库扩展**（rule_suggestions）：
1. 读取 `feedback_suggestions.json` 的 `rule_suggestions`
2. 对每条建议：确认异常模式真实有效 → 通过 OpenSpec 流程修改 `config.CRASH_PATTERNS`（固化层保护）
3. 重新运行 `gen_module_matrix.py` 确认无回归

**提示词调优**（prompt_suggestions）：
1. 读取 `feedback_suggestions.json` 的 `prompt_suggestions`
2. 对每条建议：确认调优方向 → 修改 `ai_tests/templates/ai_prompt_template.j2`（持续迭代层，可直接改）
3. 下次 manual 用例生成时自动应用新提示词

**陷阱库补充**（known_issue_suggestions）：
1. M16 已自动追加陷阱到 `known_issues.md`（含场景/根因/关联 TC-ID）
2. AI 补充"规避方式"字段（原为"待 AI 审阅补充"）
3. 确认分类（环境类/兼容类/源码类/规则类/提示词类）

---

## 五、命令速查

| 命令 | 说明 | 阶段 |
|------|------|------|
| `python ai_tests/run_e2e.py` | 全量 E2E 测试 | 5.5.2~5.5.7 |
| `python ai_tests/run_e2e.py --diff HEAD~1` | V3 源码影响分析 | 5.5.1 |
| `python ai_tests/run_e2e.py --feedback` | V3 反馈闭环 | 5.5.8 |
| `python ai_tests/run_e2e.py --tc TC-XXX` | 复测指定用例 | 失败复测 |
| `python ai_tests/run_e2e.py --gen-test BookshelfActivity` | V3 生成 B 轨 Python 用例 | M9 |
| `python ai_tests/run_e2e.py --update-source-map` | 更新 source_map.json | M8 维护 |
| `python ai_tests/scripts/gen_module_matrix.py` | 生成覆盖率报告 | 14.4 |
| `python ai_tests/lib/feedback_loop.py --report <report.json>` | 单独触发反馈闭环 | 5.5.8 |

---

## 六、相关文档

| 文档 | 说明 |
|------|------|
| [S13 ai_e2e_testing_workflow.md](../../docs/project-rules/ai_e2e_testing_workflow.md) | 八步强制流程规范 |
| [S14 test-case-design-guide.md](../../docs/project-rules/test-case-design-guide.md) | 用例设计规范 |
| [source_impact_guide.md](./source_impact_guide.md) | M8 source_map.json 维护 |
| [source_test_guide.md](./source_test_guide.md) | M9 B 轨用例生成 |
| [known_issues.md](./known_issues.md) | 陷阱库 |
| [regression_history.md](./regression_history.md) | 回归历史 |
| [usage.md](./usage.md) | 详细使用文档 |
| [troubleshooting.md](./troubleshooting.md) | 故障排查 |
