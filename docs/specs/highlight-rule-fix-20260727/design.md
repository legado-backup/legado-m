# 阅读高亮规则系统修复 - 技术设计

> **创建时间**：2026-07-27
> **依据**：`docs/temp-analysis/highlight-rule-analysis-20260727.md`（根因结论）+ 2026-07-27 源码核验（所有锚点行号以当前源码为准）
> **状态**：设计阶段
> **设计总则**：修复全部落在匹配层/数据层/快绘守卫，**零排版引擎改动**；绘制管线（Canvas 自绘 + 逐通道 merge）已验证支持字体+颜色叠加，不动。

---

## §1 架构现状速览（源码核验确认）

### 1.1 绘制管线（无冲突，不改）

```
ContentTextView.upHighlight()                    ContentTextView.kt:111-152
  ├─ 规则区间 ruleRanges（整章匹配，按页窗口过滤）   ContentTextView.kt:124-128
  ├─ 手动区间 manualRanges（排在规则之后 → 手动压规则） ContentTextView.kt:129-133
  └─ HighlightMatcher.resolve() 逐列 merge        HighlightMatcher.kt:25-52（merge 调用点 42 行）
       └─ HighlightStyle.merge() 按通道 last-wins  HighlightStyle.kt:38-51
            └─ 写入 TextColumn.highlightStyle      TextColumn.kt:46-56
                 └─ TextColumn.draw()              TextColumn.kt:58-95
                      ├─ 字色   64-73 行
                      ├─ 背景 fill 74-77 行
                      ├─ 字体 HighlightDraw.applyTextStyle() 78 行 → HighlightDraw.kt:35-43
                      │    └─ ChapterProvider.getHighlightTypeface()（HashMap 缓存）ChapterProvider.kt:242-261
                      ├─ drawText 80-86 行 → restoreTextStyle() 87 行 → HighlightDraw.kt:45-49
                      └─ 着重号 88-91 行
```

**关键结论**：fontPath 与 textColor/fill 是 merge 的独立通道（HighlightStyle.kt:38-51），同一次 drawText 内先设色再换字体再绘制，**绘制层天然支持叠加，无需任何改动**。

### 1.2 匹配链路（根因所在）

```
ReadBook.loadHighlightRules()        ReadBook.kt:261-264（只加载启用规则）
  └─ HighlightRuleStore.loadEnabled() HighlightRuleStore.kt:62-64（filter enabled && pattern.isNotBlank）
ReadBook.ruleMatchesOfChapter()      ReadBook.kt:273-306（snapshot 282-288；版本缓存 284-287/301-304）
  └─ HighlightRuleMatcher.match()     HighlightRuleMatcher.kt:22-30
       ├─ isRegex=true  → matchRegex()   43-63（超时保护 49/61 行）
       └─ isRegex=false → matchLiteral() 32-41（text.indexOf 纯字面量查找 ← 内置规则全部走这里，永不命中）
```

### 1.3 数据链路（根因所在）

```
存储：SharedPreferences PreferKey.highlightRuleItems（PreferKey.kt:227），非 Room
HighlightRuleStore.load()   HighlightRuleStore.kt:42-60（blank → 空列表 45-47，不播种）
HighlightRuleStore.reset()  HighlightRuleStore.kt:78-83（有播种能力，全工程无调用方）
HighlightRuleStore.normalizeRules()      258-289（内置刷新通道 266-280，保留用户 enabled/颜色）
HighlightRuleStore.shouldRefreshBuiltin() 369-378（只处理乱码/旧 pattern，不修正 isRegex）
HighlightRuleStore.sanitizeRule()        291-326（isRegex 默认 false，322 行）
预设添加：HighlightPresetRuleDialog.onAddRule（HighlightPresetRuleDialog.kt:80-89，84 行覆盖新 id）
  → HighlightRuleActivity.showPresetRuleDialog（HighlightRuleActivity.kt:81-88，85 行 toast）
  → HighlightRuleViewModel.update()（HighlightRuleViewModel.kt:34-46，38-39 行 idx<0 静默丢弃）
即时生效：仅 HighlightRuleActivity.onDestroy（139-142）与 HighlightRuleEditDialog.save（238 行）调 ReadBook.upHighlightRules()
```

---

## §2 R-P1-1 修复设计（双引号字体覆盖）

### 2.1 根因源码锚点

| 角色 | 锚点 |
|------|------|
| 主根因：isRegex 默认 false | HighlightRule.kt:33 |
| 主根因：12 条内置正则规则未设 isRegex | HighlightRuleStore.kt:129-256 |
| 分派点：false 走字面量匹配 | HighlightRuleMatcher.kt:27、32-41 |
| 次要根因：内置对话规则自带字色 | HighlightRuleStore.kt:138 |
| 附带缺陷：fill-only 不计数 | HighlightStyle.kt:31-34 + TextColumn.kt:46-56 |
| 附带缺陷：快绘吞 fill | TextLine.kt:284-292（checkFastDraw）、196-229（fastDrawTextLine） |

### 2.2 方案 A（推荐，必须）：修匹配层 isRegex，不动绘制层

**锚点 1**：`HighlightRuleStore.createDefaultRules()`（HighlightRuleStore.kt:129-256）——12 条内置规则全部补 `isRegex = true`。改动示例（每条规则构造函数加一个参数，共 12 处）：

```kotlin
HighlightRule(
    id = "dialog_default",
    name = "对话高亮",
    pattern = "“[^”\n]{1,120}”|\"[^\"\n]{1,120}\"|「[^」\n]{1,120}」|『[^』\n]{1,120}』",
    ...
    isRegex = true   // 新增：12 条全部补齐
)
```

**锚点 2**：存量愈合——`normalizeRules()`（HighlightRuleStore.kt:258-289）刷新判定处（266-267 行）增加 isRegex 愈合条件：

```kotlin
val builtin = builtins[safeRule.id]
// 新增：内置 id + pattern 未被用户改动 + isRegex=false → 走刷新通道（自动带上 isRegex=true，且保留用户 enabled/颜色自定义）
val needsRegexHeal = builtin != null && !safeRule.isRegex && safeRule.pattern == builtin.pattern
val base = if (builtin != null && (shouldRefreshBuiltin(safeRule) || needsRegexHeal)) {
    builtin.copy(...)   // 沿用现有刷新通道（268-280 行）
} else { ... }
```

愈合写库沿用 `load()` 已有的 `normalized != rules` 回写逻辑（HighlightRuleStore.kt:51-53），一次性愈合，后续读取零开销。

**理由**：颜色规则一旦真正命中，merge 天然完成字体+颜色叠加，零绘制层改动、零回归风险；同一处修正同时解决问题 2 的"预设启用无效"（R-P1-2a）。

### 2.3 方案 B（可选 UX 增强）：字体规则去色提示

- 在 `HighlightStyleDialog.bindFontRow()`（HighlightStyleDialog.kt:203-211）字体行增加提示文案："字体规则建议清除字色，避免覆盖其他颜色规则"。
- 或用户编辑内置对话规则加字体时，将其 textColor 置 0，使字体规则只占 fontPath 通道。
- 理由：消除 last-wins 通道竞争（HighlightRuleStore.kt:138），符合"字体归字体、颜色归颜色"心智模型。

### 2.4 方案 C（建议顺带）：fill-only 快绘吞样式修复

**推荐改法（快绘补画 fill）**：`TextLine.fastDrawTextLine()`（TextLine.kt:196-229）在已有的逐列选中框循环（223-228 行）中补画 fill 矩形，与 `TextColumn.draw()` 的 fill 逻辑（TextColumn.kt:74-77）一致：

```kotlin
// fastDrawTextLine() 内，替换/扩展现有 223-228 行的逐列循环
for (i in columns.indices) {
    val column = columns[i] as TextColumn
    val fill = column.highlightStyle?.fill ?: 0
    if (fill != 0) {
        canvas.drawRect(column.start, 0f, column.end, height, view.highlightPaint(fill))
    }
    if (column.selected) {
        canvas.drawRect(column.start, 0f, column.end, height, view.selectedPaint)
    }
}
```

**备选改法（守卫快绘）**：`TextColumn.highlightStyle` setter（TextColumn.kt:46-56）新增 `fillColumnCount` 计数，`checkFastDraw()`（TextLine.kt:284-292）增加 `fillColumnCount == 0` 条件。改动面更大，仅在补画方案有性能顾虑时采用。

**理由**：`optimizeRender` 开启用户背景下，黄底/蓝底等背景色高亮不丢；测试矩阵需覆盖 optimizeRender 开/关。

### 2.5 成熟方案参考

- 当前实现本身借鉴**蛋蛋Max / 阅读T**（代码注释 F-P1-2），其内置高亮规则均以正则语义参与匹配——本次方案 A 即对齐上游语义。
- 用户点名的 **md3 衍生版**（legado-with-MD3）规则引擎同为"规则 pattern 默认按正则匹配"模型，且支持跨段落引号匹配；本期仅对齐其匹配语义，UI 风格借鉴（用户提及的大工程）不在本期范围。
- merge last-wins 叠加模型与 CSS 级联语义一致，属于成熟设计，保留不动。

### 2.6 日志设计（AppLog.put，不用 Timber）

| 时机 | 日志内容 | 说明 |
|------|---------|------|
| 存量愈合触发 | `AppLog.put("高亮规则：愈合内置规则 ${rule.id} 的 isRegex")` | 只记 id，不记 pattern 明文；愈合发生在 load() 内，单次 |
| 快绘补画 fill 启用 | 无需常驻日志；调试期可在 checkFastDraw 放行走快绘且无 styled 列时记 DEBUG 级计数 | 交付前清理调试日志（遵守 logging-during-refactoring 规范） |

### 2.7 风险与回退

| 场景 | 风险 | 对策 |
|------|------|------|
| 用户将内置规则 pattern 改成本文（字面量用法） | 强制 isRegex=true 改变语义 | 愈合条件加"pattern 与当前内置一致"前置判断（§2.2 锚点 2），用户改过的 pattern 不动 |
| 存量内置规则用户改过 enabled/颜色 | 愈合刷新覆盖用户自定义 | 刷新通道已保留 enabled/textColor 等（HighlightRuleStore.kt:268-280），仅修补 pattern/isRegex |
| 整章正则匹配性能（12 条全量扫整章） | 长章节耗时 | 已有超时保护（timeoutMillisecond=3000，HighlightRuleMatcher.kt:49/61）+ 版本号缓存（ReadBook.kt:284-287/301-304） |
| 快绘补画 fill 的性能 | 每行多一次逐列循环 | 循环与现有选中框循环合并，列数为单行列数（个位数~30），可忽略 |
| 回退 | — | 改动集中在 HighlightRuleStore.kt 单文件（方案 A）+ TextLine.kt 单文件（方案 C），git revert 单文件即可 |

---

## §3 R-P1-2 修复设计（预设规则不生效 + 无初始化）

### 3.1 根因源码锚点

| 子问题 | 锚点 |
|--------|------|
| a 初始化缺失：blank 直接返空 | HighlightRuleStore.kt:42-60（45-47 行） |
| a 初始化缺失：reset 无调用方 | HighlightRuleStore.kt:78-83（全工程检索 0 调用） |
| b 写库断裂：新 id 覆盖 | HighlightPresetRuleDialog.kt:84 |
| b 写库断裂：idx<0 静默丢弃 | HighlightRuleViewModel.kt:34-46（38-39 行） |
| b 假成功 toast | HighlightRuleActivity.kt:85 |
| c 启用无效：isRegex 不修正 | HighlightRuleStore.kt:322、369-378（同 §2.2，方案 A 一并解决） |
| 即时性：仅 onDestroy 刷新 | HighlightRuleActivity.kt:139-142 |

### 3.2 修复 a：首启播种

**锚点**：`HighlightRuleStore.load()`（HighlightRuleStore.kt:44-47）。

```kotlin
val stored = context.getPrefString(PreferKey.highlightRuleItems)
if (stored.isNullOrBlank()) {
    return reset(context)   // 从未初始化 → 播种 12 条内置规则并写库
}
```

判别语义：
- `null/blank` = 从未初始化 → 播种（覆盖新装与升级老用户未用过该功能的场景）
- `"[]"` = 用户曾清空全部规则 → 非 blank，走正常解析返回空列表，**尊重用户清空，不重复播种**（save 写空列表后 stored 为 `"[]"`，天然满足）

默认启用状态已联动设置页开关：`createDefaultRules` 读取 `PreferKey.highlightRuleDialog / BookTitle / BracketNote`（HighlightRuleStore.kt:137/146/157，PreferKey.kt:224-226），对话/书名号/括号/标题 4 条默认启用（标题强调为硬编码 true，HighlightRuleStore.kt:170），播种行为与用户预期一致。`reset()` 内部经 `save()` 自动完成 `HighlightRuleGroupStore.ensureFromRules`（HighlightRuleStore.kt:74），分组同步无需额外处理。

### 3.3 修复 c：内置规则 isRegex 修正 + 存量愈合

**与 §2.2 方案 A 为同一处改动**（createDefaultRules 补 `isRegex = true` + normalizeRules 愈合条件），一次实施同时解决问题 1 与问题 2 的"不生效"表象，不重复列任务。

### 3.4 修复 b：预设添加写库 + 即时生效

**锚点 1**：`HighlightRuleViewModel.update()`（HighlightRuleViewModel.kt:34-46）——update 语义升级为 upsert（与 `HighlightRuleEditDialog.save()` 的 229-236 行行为对齐）：

```kotlin
val idx = list.indexOfFirst { it.id == rule.id }
if (idx >= 0) list[idx] = rule else list.add(rule)   // idx<0 时追加，不再静默丢弃
```

**锚点 2**：`HighlightPresetRuleDialog` 添加时保留内置 id（HighlightPresetRuleDialog.kt:83-86）：

```kotlin
onAddRule(item.copy(group = groupToUse))   // 去掉 id = System.currentTimeMillis().toString() 覆盖
```

保留内置 id 的好处：重复添加走 upsert 刷新而非堆积副本；添加的内置规则自动进入 normalizeRules 愈合通道管辖。

**锚点 3**：即时生效——`HighlightRuleViewModel.update()` 写库成功后立即调 `ReadBook.upHighlightRules()`（对标 HighlightRuleEditDialog.kt:238 的既有模式），勾选/添加后返回阅读页立即生效，不再依赖 `HighlightRuleActivity.onDestroy`（HighlightRuleActivity.kt:139-142）时序（onDestroy 调用保留，幂等无害）。

### 3.5 成熟方案参考

- **蛋蛋Max / 阅读T**（本功能借鉴来源）：首启即内置一套常用高亮规则，预设添加即写库——本期播种 + upsert 方案与其行为对齐。
- 项目内既有先例：`HighlightRuleEditDialog.save()`（HighlightRuleEditDialog.kt:229-236）已是"替换或追加"的 upsert 并实现保存后即时 `upHighlightRules()`（238 行），ViewModel 修复即向该先例对齐，无新引入模式。
- 存储保持 SharedPreferences + GSON（HighlightRule.kt:15-36 全字段默认值，反序列化兼容旧备份 JSON 缺 isRegex 字段的场景，经 sanitizeRule HighlightRuleStore.kt:322 默认值兜底）。

### 3.6 日志设计（AppLog.put）

| 时机 | 日志内容 | 说明 |
|------|---------|------|
| 首启播种 | `AppLog.put("高亮规则：首启播种内置规则 ${defaults.size} 条")` | 只记数量 |
| 预设添加走 add 分支 | `AppLog.put("高亮规则：新增规则 ${rule.id}（upsert-add）")` | 只记 id；替换分支不记（避免噪音） |
| 即时刷新 | `ReadBook.upHighlightRules()` 内已有 `highlightRulesVersion++`（ReadBook.kt:263），不新增日志 | 保持现有行为 |

### 3.7 风险与回退

| 场景 | 风险 | 对策 |
|------|------|------|
| 已有用户规则（stored 非 blank） | 播种造成重复/覆盖 | 只在 blank 时播种；`"[]"` 不播种（§3.2 判别语义） |
| 用户故意删除全部规则 | 重启后规则"复活"引发投诉 | `"[]"` 非 blank 不播种，语义自洽；验收标准 §1.2-5 覆盖 |
| 旧备份 JSON 无 isRegex 字段 | 恢复后内置 id 规则仍 isRegex=false | sanitizeRule 默认 false（HighlightRuleStore.kt:322）→ 恢复内置 id 规则时经 normalizeRules 愈合通道修正（§2.2 锚点 2） |
| 预设重复添加 | 列表堆积同规则副本 | 保留内置 id + upsert 语义去重（§3.4 锚点 2） |
| 并发：load/save 与阅读线程并发 | 写冲突 | 已有 `@Volatile cachedRules`（HighlightRuleStore.kt:35-36）+ ReadBook snapshot（ReadBook.kt:282-288）；播种写库仅 load 首调一次 |
| update 改 upsert 的语义扩散 | 其他调用方依赖"不存在则忽略" | 全工程调用方仅 HighlightRuleActivity（update/delete/toTop/toBottom/upOrder）与 Adapter 勾选链路，均为"操作已存在或应存在规则"，upsert 更符直觉；实施时 Grep `viewModel.update` / `callBack.update` 复核调用方清单 |
| 回退 | — | 改动集中在 HighlightRuleStore.kt / HighlightRuleViewModel.kt / HighlightPresetRuleDialog.kt 三个文件，git revert 即可 |

---

## §4 测试设计

### 4.1 JVM 仿真器验证（纯函数，免真机）

- `HighlightRuleMatcher`（HighlightRuleMatcher.kt:8-64）与 `HighlightMatcher`（HighlightMatcher.kt:8-53）均为纯函数无 Android 依赖（KDoc 明示 JVM 可测）。
- 用 `createDefaultRules` 的 12 条 pattern + 各自 `sampleText`（HighlightRuleStore.kt:131-255）构造 `Rule(isRegex=true)`，断言每条规则对自身 sampleText 至少 1 次命中；同一批 pattern 以 `isRegex=false` 断言 0 命中（回归对照）。
- merge 叠加断言：fontPath 规则样式与 textColor 规则样式 merge 后两通道同时非默认。

### 4.2 真机验收矩阵（对应 spec.md 验收标准）

| # | 场景 | 前置 | 预期 |
|---|------|------|------|
| 1 | 清除应用数据启动 → 高亮规则管理 | 新装 | 12 条内置规则，4 条默认勾选 |
| 2 | 预设对话框添加任一规则 → 杀进程重启 | — | 规则仍在列表 |
| 3 | 启用"对话高亮"→ 含对话章节 | — | 引号区域着色 |
| 4 | 对话规则设独立字体 + 启用颜色规则 | — | 引号区域字体+颜色同时呈现 |
| 5 | 管理页勾选/取消 → 直接返回阅读页 | — | 高亮立即出现/消失 |
| 6 | optimizeRender 开/关 × fill 高亮 | 开启渲染优化 | 两种状态背景色均可见 |
| 7 | 删除全部规则 → 重启 | — | 列表保持为空（不重复播种） |
| 8 | 回归：手动划线与规则同区叠加 | — | 手动压规则，顺序不变 |

> 测试执行须用测试包 `io.legado.miss.app.debug`（代码优化任务），脚本固定使用 `ai_tests/scripts/`。
