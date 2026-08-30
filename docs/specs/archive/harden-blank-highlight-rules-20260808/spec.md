# 高亮规则空数据自动修复 - 功能规格

> **创建时间**：2026-08-08
> **状态**：🔄 设计中
> **前置 spec**：[highlight-rule-restore-default-20260729](../highlight-rule-restore-default-20260729/)

---

## §1 Intent（意图）

解决用户升级后高亮规则全空的根因：设备 prefs 中 `highlightRuleItems` JSON 的全部规则 name/pattern 字段为空字符串。App 忠实展示/匹配空数据导致"列表名空 + 编辑空 + 不生效"。目标：`load()` 自动检测此损坏形态并 `reset()` 恢复 12 条内置规则，避免用户手动恢复。

## §2 Scope（范围）

### 2.1 In Scope（做）

- `HighlightRuleStore.load()` 增加损坏检测：解析出的非空列表**全部规则 name 与 pattern 均为空**时视为损坏 → `reset()`
- 记录自愈日志（AppLog.put），便于用户侧排查
- 文档同步（INDEX.md/issues-found.md/ai_memory_main.md/updateLog）

### 2.2 Out of Scope（不做）

- 不改变存储介质（SharedPreferences）
- 不修改 12 条内置规则内容
- 不修改 normalizeRules/sanitizeRule 既有逻辑
- 不处理"部分规则空、部分正常"的混合数据（保留用户自定义规则，符合用户数据优先原则）
- 不改动恢复默认规则的 UI 入口（既有功能）

## §3 Approach（技术方案）

### 3.1 Selected Approach（选定方案）

**方案：load() 增加"全空规则"损坏检测 → reset()**

在 `load()` 解析出 `rules` 且非空后、进入 `normalizeRules` 前，检测：

```kotlin
if (rules.all { it.name.isNullOrBlank() && it.pattern.isNullOrBlank() }) {
    AppLog.put("高亮规则：检测到全部规则为空数据，已自动恢复内置规则")
    return reset(context)
}
```

**触发条件**：仅当**每条**规则的 name 和 pattern 同时为空才 reset。用户自定义规则只要有一条 name 或 pattern 非空，就不触发，保留用户数据。

**选定理由**：改动单文件单方法，与既有 T-B3（空/"[]"/解析失败 reset）逻辑同构，最小风险；该形态正是用户真机实测损坏数据的完整签名（12 条全部 name/pattern 空）。

### 3.2 Alternatives Considered（考虑过的替代方案）

| 编号 | 方案 | 否决理由 |
|------|------|---------|
| A1 | 逐条修复空 name/pattern（从内置规则补回 name） | 无法区分"内置 id 损坏"与"用户自定义空规则"，且内置 id 可能已被用户改过；全空即无任何可用规则，直接重置更干净 |
| A2 | 仅靠既有"恢复默认"UI 入口 | 用户不会主动发现；损坏数据会导致列表空、编辑空、不生效三重症状，属隐蔽故障，应自动自愈 |
| A3 | 修改 normalizeRules 对空规则直接丢弃 | 会改变既有行为，且丢弃后列表可能变空（若全是自定义空规则）；不如统一 reset 恢复内置基线 |
| A4 | 仅判断 pattern 全空（不看 name） | 用户可能有"仅填 name 不填 pattern"的规则草稿，只判 pattern 全空会误重置；name+pattern 双空是更强损坏签名 |

### 3.3 Drawbacks（已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 若用户刻意把所有规则都清成空（name+pattern 全空）会触发重置 | 全空规则本就无匹配能力（loadEnabled 过滤 pattern 空），保留无意义；重置为内置规则是合理兜底 |
| 首次加载可能有一次 prefs 写入（reset 会 save） | 仅在异常数据时发生，正常路径不触发 |

### 3.4 Prior Art（参考）

- 既有 `load()` T-B3 分支（HighlightRuleStore.kt:55-56, 65-66）已对"空/"[]"/解析失败"执行 reset，本方案补齐"非空但全空字段"这一漏网形态
- `restoreDefaults(OVERWRITE)`（HighlightRuleStore.kt:109-113）已验证"重置为内置规则"语义可靠

## §4 Requirements（需求）

- **R1**：存储为 非空列表 且 全部规则 name+pattern 均空 → load() 自动 reset，恢复 12 条内置规则
- **R2**：正常数据（含部分自定义规则）加载路径完全不变，不触发 reset
- **R3**：触发时写入 AppLog 自愈日志
- **R4**：自愈后列表显示名称/编辑内容/阅读页高亮均恢复

## §5 Scenarios（验收场景）

- **S1**：注入"12 条规则 name/pattern 全空"的 prefs → 启动高亮规则页 → 自动恢复显示 12 条内置中文规则
- **S2**：正常 12 条内置数据 → 启动 → 列表正常，无额外 reset 日志
- **S3**：混合数据（1 条正常 + 11 条全空）→ 启动 → 正常数据保留，不触发 reset
- **S4**：自愈后阅读页高亮规则生效（ReadBook.loadEnabled 返回内置规则）

## §6 非目标

- 不重构存储为 Room
- 不修改内置规则内容
- 不修改 normalizeRules/sanitizeRule
- 不新增内置规则种类
