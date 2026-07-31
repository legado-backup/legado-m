# 高亮规则丢失修复 + 恢复默认规则 - 功能规格

> **创建时间**：2026-07-29
> **状态**：🔄 设计中
> **前置 spec**：[highlight-rule-fix-20260727](../highlight-rule-fix-20260727/)

---

## §1 Intent（意图）

修复前序 spec `highlight-rule-fix-20260727` 实施后引入的回归 BUG（用户编辑过的内置规则 pattern 被愈合逻辑覆盖），并新增"恢复默认规则"功能，让用户清空规则后能重新初始化内置常规高亮规则。

## §2 Scope（范围）

### 2.1 In Scope（做）

- 修复 `shouldRefreshBuiltin` 愈合逻辑：增加 pattern 前置判断，用户改过 pattern 的内置规则不被覆盖
- 修复 `normalizeRules` 的 `builtin.copy()`：保留用户改过的 pattern/sampleText/name
- 新增 HighlightRuleActivity 菜单"恢复默认规则"：支持合并模式（保留自定义+补充缺失内置）+ 覆盖模式（确认后重置）
- 同步前序 spec tasks.md 实施状态 + 本 spec INDEX.md 收录

### 2.2 Out of Scope（不做）

- 不重构存储介质（保持 SharedPreferences）
- 不重构绘制架构（Canvas 自绘已验证可用）
- 不新增内置规则种类（当前 12 条已覆盖常规场景：对话/书名号/括号/标题/心理/旁白/重点/诗词/省略/数字/英文/时间）
- 不改动 isRegex 默认值（保持 false，由 createDefaultRules 显式设 true）

## §3 Approach（技术方案）

### 3.1 Selected Approach（选定方案）

**方案：修复愈合逻辑 pattern 前置判断 + 新增恢复默认菜单**

1. **R-1 愈合逻辑修复**：`shouldRefreshBuiltin` 增加 pattern 前置判断——只有 `pattern == builtin.pattern`（用户未改 pattern）时才因 `isRegex=false` 触发愈合；`normalizeRules` 的 `builtin.copy()` 保留 safeRule 的 pattern/sampleText/name（当用户改过时）
2. **R-2 恢复默认菜单**：HighlightRuleActivity 菜单新增"恢复默认规则"，弹对话框选择模式：
   - 合并模式（默认推荐）：保留用户自定义规则，补充缺失的内置规则（按 id 去重）
   - 覆盖模式（需二次确认）：重置为 12 条内置规则（用户自定义规则会丢失）

**选定理由**：精准修复 BUG 根因（愈合过度覆盖），同时提供用户可控的恢复入口。改动集中在 HighlightRuleStore.kt + HighlightRuleActivity.kt + menu 资源，低风险。

### 3.2 Alternatives Considered（考虑过的替代方案）

| 编号 | 方案 | 否决理由 |
|------|------|---------|
| A1 | 仅修复愈合逻辑，不加恢复默认菜单 | 用户清空全部规则后无法恢复内置常规规则，用户体验不完整；用户明确要求"初始化常规高亮内容规则进去软件里面" |
| A2 | 重构存储为 Room + 提供恢复默认 | 改动面大（涉及 BackupController/ReadBook/ViewModel 全链路），引入回归风险高，收益不匹配 |
| A3 | 仅加恢复默认菜单，不修愈合逻辑 | BUG 根因未修，用户编辑过的内置规则 pattern 仍会被覆盖，治标不治本 |
| A4 | 愈合逻辑完全移除 isRegex 判断 | 会导致旧版内置规则（isRegex=false）无法愈合到 isRegex=true，前序 spec 的修复目标失效 |

### 3.3 Drawbacks（已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 合并模式可能产生 id 重复规则（如果用户自定义规则 id 恰好等于内置 id） | 已通过 upsert 语义（T-B3 已实施）去重，重复添加走 replace |
| 覆盖模式有数据丢失风险 | 已要求二次确认对话框，明确提示"将删除所有自定义规则" |
| 愈合 pattern 前置判断后，用户改过 pattern 的内置规则不会自动修正 isRegex | 用户可手动在编辑对话框勾选正则；或通过"恢复默认"覆盖模式重置；符合"用户数据优先"原则 |
| shouldRefreshBuiltin 需获取 builtin 对象 | 改为接收 builtin 参数（normalizeRules 已构造 builtins map），避免重复调用 createDefaultRules |

### 3.4 Prior Art（参考）

- 前序 spec `highlight-rule-fix-20260727` 的 design.md §2.2 原方案即为 `needsRegexHeal = builtin != null && !safeRule.isRegex && safeRule.pattern == builtin.pattern`，实际实施时简化为 `!rule.isRegex` 丢失了 pattern 判断，本 spec 修正这一偏差
- 蛋蛋Max / 阅读T 的恢复默认均为"重置为内置规则"语义，本 spec 增加合并模式更友好

## §4 Requirements（需求）

- **R1**：用户编辑过 pattern 的内置规则，重启后 pattern 保持用户的修改（不被愈合覆盖）
- **R2**：用户未改过 pattern 的内置规则（isRegex=false 旧数据），重启后愈合为 isRegex=true 且 pattern 保持内置值
- **R3**：HighlightRuleActivity 菜单有"恢复默认规则"入口
- **R4**：恢复默认-合并模式：保留用户自定义规则，补充缺失的内置规则（按 id 去重）
- **R5**：恢复默认-覆盖模式：二次确认后重置为 12 条内置规则

## §5 Scenarios（验收场景）

- **S1**：编辑内置规则 dialog_default 的 pattern 为自定义正则 → 重启 → pattern 保持用户的值
- **S2**：旧版数据内置规则 isRegex=false + pattern 未改 → 重启 → isRegex 愈合为 true，pattern 保持内置值
- **S3**：清空全部规则 → 菜单点"恢复默认"→ 选合并模式 → 12 条内置规则出现，用户自定义规则（如有）保留
- **S4**：有自定义规则 → 菜单点"恢复默认"→ 选覆盖模式 → 二次确认 → 重置为 12 条内置规则，自定义规则消失
- **S5**：恢复默认后 → 阅读页高亮立即生效（ReadBook.upHighlightRules）

## §6 非目标

- 不重构存储为 Room
- 不重构绘制架构
- 不新增内置规则种类
- 不改动 isRegex 默认值
