# Spec：修复高亮规则开关切换不即时刷新

## Intent

高亮规则管理页复选框切换后，当前页面列表不即时更新，需退出重进才生效。用户要求：修复 Bug、解释根因、全面排查同类问题、审查并同步更新前端设计规范（规范未覆盖此模式）。

## Scope

**做**：
- 修复 `HighlightRuleActivity.onEnableToggle` 原地修改问题（改 copy）
- 全面排查同类模式（已由子代理全量审计完成，仅此 1 处）
- `frontend-ui-standards.md` 补齐 Compose 列表状态不可变更新约束（§4 红线 / §5 门禁 / §6 已知坑）

**不做**：
- 不将 `HighlightRule` 字段改 val（编辑弹窗依赖 var 原地编辑，改动面大、收益低）
- 不迁移 `HighlightRule` 到 Room（ViewModel 注释已有升级路径，另行规划）
- 不改 RecyclerView 体系页面的原地修改坏味道（无重组失效，仅备忘）

**影响模块**：`ui/highlight`（1 个文件）、`docs/project-rules/frontend-ui-standards.md`

## Approach

### Selected Approach

回调处改用 `rule.copy(enabled = enabled)` 创建新实例传给 `viewModel.update(rule)`。

理由：
1. 与全项目其它 28 处 Compose 列表开关切换的 copy 模式**完全对齐**（ReplaceRule/BookSource/RssSource/DictRule/TxtTocRule 等先例）
2. 一行修复，不引入新抽象，不触碰存储层与编辑弹窗链路
3. 从语义上根治：列表状态更新 = 不可变数据替换，强跳过按引用比较时新旧实例必然不同 → 行重组

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| `items(..., key = { it.id })` 外再叠 `contentType`/手动 `key(rule.enabled)` | 治标：把重组责任转嫁给每个调用点，其它页面复用此反模式时仍会踩坑；且 enabled 进 key 会导致整行重建而非重组 |
| `HighlightRule` 字段全改 val（不可变数据类） | 编辑弹窗 `HighlightRuleEditDialog` 现依赖 var 原地编辑后保存，改 val 需同步重写编辑链路，改动面与风险不成比例 |
| ViewModel.update 内部统一 `rule.copy()` 防御 | 能修本 Bug，但原地修改的反模式仍留在回调处，语义更隐晦；且无法防止其它调用点先改后传（Store load 出的实例本身也会被污染） |
| 迁移 Room + Flow 响应式 | 超出本次范围，ViewModel 注释已登记为升级路径 |

### Drawbacks

- `HighlightRule` 仍是 var 字段的 unstable 类型，后续新增 Compose 页面仍可能写出原地修改反模式——接受理由：本方案通过**规范补齐**（红线+门禁清单+已知坑）建立防线，且全量审计确认现存代码仅此一处，风险可控。

### Prior Art

- `DictRuleActivity.kt:273-277`：`viewModel.update(it.copy(enabled = checked))`
- `TxtTocRuleActivity.kt:301-305`：`viewModel.update(it.copy(enable = checked))`

## Requirements

1. R1：复选框选中/取消后，当前行 Checkbox 状态**立即**重绘（无需退出重进）
2. R2：开关状态正确持久化（SharedPreferences），重进后状态一致
3. R3：`ReadBook.upHighlightRules()` 即时生效链路保持不变（阅读器高亮同步刷新）
4. R4：编辑/删除/置顶/置底/导入/预设等其它操作刷新行为不受影响
5. R5：前端设计规范补齐后，可指导后续页面避免同类反模式

## Scenarios

**正常流程**：
1. 进入高亮规则管理页 → 点击某规则复选框取消选中 → 该行 Checkbox 立即变为未选中（不改其它行）
2. 再次点击选中 → 立即选中

**异常流程**：
1. 快速连续点击同一复选框 → 每次均创建新实例，最终状态与最后一次点击一致
2. 开关后立即返回阅读器 → 高亮规则按最新启用状态生效（R3 链路）

**边界条件**：
1. 开关后旋转屏幕/进程重建 → 状态从 Store 恢复，与持久化一致
2. 开关后再次进入编辑弹窗 → 读到的 enabled 为最新值（copy 实例已落库）
