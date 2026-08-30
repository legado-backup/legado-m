# 高亮规则空数据自动修复 - 技术设计

> **创建时间**：2026-08-08
> **状态**：🔄 设计中

---

## §1 Technical Approach（技术方法）

### 1.1 根因源码锚点

`HighlightRuleStore.load()`（HighlightRuleStore.kt:50-67）当前流程：

```
cachedRules 缓存 → 读 PreferKey.highlightRuleItems
  ├─ blank / "[]"            → reset()      ✅ 已覆盖
  ├─ 解析成功且非空           → normalizeRules → save → cachedRules  ✅
  ├─ 解析失败 / 空列表        → reset()      ✅ 已覆盖
```

**漏洞**：解析成功且非空，但列表内所有规则 name/pattern 全空（用户真机实测损坏形态）时，走 `normalizeRules`。内置 id 规则的 `shouldRefreshBuiltin` 检查 `rule.pattern == builtin.pattern`（空 != 内置值）不触发 builtin.copy 愈合，`else` 分支直接 `safeRule.copy` 保留空字段 → 列表空名 + 编辑空 + loadEnabled 过滤 pattern 空导致不生效。

### 1.2 修复方案

在 `load()` 解析成功且非空后、进入 `normalizeRules` 前插入损坏检测：

```kotlin
val rules = GSON.fromJsonArray<HighlightRule>(stored).getOrNull()?.toMutableList()
if (rules != null && rules.isNotEmpty()) {
    // H-1: 全部规则 name+pattern 均空 = 损坏数据，自动恢复内置规则
    // 真机实测：用户设备 JSON 12 条 name/pattern 全空导致列表空+编辑空+不生效
    if (rules.all { it.name.isNullOrBlank() && it.pattern.isNullOrBlank() }) {
        AppLog.put("高亮规则：检测到全部规则为空数据，已自动恢复内置规则")
        return reset(context)
    }
    val normalized = normalizeRules(rules, context)
    save(context, normalized)
    cachedRules = normalized
    return normalized.toMutableList()
}
```

## §2 Architecture Decisions（架构决策）

### AD-01: 全空规则检测放在 load() 而非 normalizeRules()
- **Context**: load() 已有三处 reset 分支（blank/"[]"/解析失败），normalizeRules 专注单条规则规范化
- **Concern**: 检测点放哪里最贴近既有 reset 语义
- **Decision**: 放在 load() 的解析成功分支入口，与既有 reset 分支同层
- **Goal**: 损坏检测与"恢复内置基线"动作同位置，职责清晰
- **Tradeoff**: normalizeRules 不复用，但仅多一次 `all{}` 遍历（12 条量级，开销可忽略）
- **Status**: Accepted

### AD-02: 触发条件用 name+pattern 双空，且为全列表 all
- **Context**: 用户实测损坏数据是 12 条全部 name/pattern 空
- **Concern**: 误伤用户自定义规则草稿（如只填 name 未填 pattern）
- **Decision**: `all { name.isNullOrBlank() && pattern.isNullOrBlank() }`——只要存在任一条 name 或 pattern 非空即不触发
- **Goal**: 最保守，仅对"完全无可用规则"的损坏数据自愈
- **Tradeoff**: 部分损坏的混合数据仍需用户手动恢复，但符合"用户数据优先"原则
- **Status**: Accepted

### AD-03: 触发时用 AppLog.put 记录
- **Context**: logging-during-refactoring 规范要求状态切换/自愈动作可追踪
- **Concern**: 用户反馈问题时能定位是否发生过自愈
- **Decision**: `AppLog.put("高亮规则：检测到全部规则为空数据，已自动恢复内置规则")`
- **Goal**: 日志即文档，用户可查
- **Tradeoff**: 应用日志多一行（仅损坏时触发）
- **Status**: Accepted

## §3 Data Flow（数据流）

```
SharedPreferences (highlightRuleItems JSON)
   │  load(context)
   ▼
GSON.fromJsonArray → rules (非空)
   │
   ├─ all{ name&pattern 空 }? ──YES──▶ AppLog.put → reset() → 12 内置规则 → save
   │
   └─ NO ──▶ normalizeRules → save → cachedRules（原有路径，无变化）
```

## §4 File Changes（文件变更）

| 文件 | 变更 | 内容 |
|------|------|------|
| `app/src/main/java/io/legado/app/ui/book/read/config/HighlightRuleStore.kt` | +5 | load() 插入全空检测（H-1） |
| `app/src/main/assets/updateLog.md` | +1 | 新增用户可感知变更条目 |
| `docs/specs/harden-blank-highlight-rules-20260808/` | +4 | 本 spec 四文档 |
| `docs/INDEX.md` | ±1 | spec 状态记录 |
