# 阅读高亮规则系统修复 - 功能规格

> **创建时间**：2026-07-27
> **问题清单**：`issues/user/temp/20260727/001/`（高亮×2）
> **分析报告**：`docs/temp-analysis/highlight-rule-analysis-20260727.md`（只读源码分析，结论已经源码核验确认与当前代码一致）
> **状态**：设计阶段

---

## §1 核心问题详述

### 1.1 R-P1-1：双引号独立字体后颜色类高亮无法叠加

**现象**：用户给双引号设置独立字体（自建正则规则 + fontPath，命中成功）后，期望引号内文字同时叠加颜色类高亮（心理活动/重点强调等预设颜色规则），实际引号区域只有字体变化、无任何颜色叠加。表象为"字体渲染后颜色规则无法叠加"。

**已澄清的误区（源码核验确认）**：本系统不是 Span 实现，为 **Canvas 自绘 + 样式逐通道 merge**，不存在 Spannable/Span 应用顺序冲突：

- 字体通道应用点：`TextColumn.draw()`（TextColumn.kt:78）→ `HighlightDraw.applyTextStyle()`（HighlightDraw.kt:35-43）→ `ChapterProvider.getHighlightTypeface()`（ChapterProvider.kt:242-261，带 HashMap 缓存）临时替换共享 paint 的 typeface，drawText 后由 `restoreTextStyle()`（HighlightDraw.kt:45-49）还原。排版引擎中不存在引号专用字体逻辑。
- 颜色通道应用点：`TextColumn.draw()` 内字色（TextColumn.kt:64-73）、背景 fill（TextColumn.kt:74-77）、着重号（TextColumn.kt:88-91），与字体通道在**同一次 drawText 中共存**——先设色（71-73）、再换字体（78）、再绘制（80-86），互不阻断。
- 多规则叠加由 `HighlightStyle.merge()`（HighlightStyle.kt:38-51）完成：按通道 last-wins，`fontPath` 与 `textColor` 是独立通道，字体规则不会挤掉颜色规则。
- 调用链：`ContentTextView.upHighlight()`（ContentTextView.kt:111-152）→ `ReadBook.ruleMatchesOfChapter()`（ReadBook.kt:273-306）→ `HighlightRuleMatcher.match()` → `HighlightMatcher.resolve()`（HighlightMatcher.kt:25-52，逐列 merge）→ 写入 `TextColumn.highlightStyle`（TextColumn.kt:46-56）→ `TextColumn.draw()`。

**真正根因（主）**：颜色类规则根本没命中——`HighlightRule.isRegex` 默认值为 `false`（HighlightRule.kt:33），而 `HighlightRuleStore.createDefaultRules()`（HighlightRuleStore.kt:129-256）创建的 12 条内置预设规则全部是正则 pattern，却无一设置 `isRegex = true`。匹配分派点 `HighlightRuleMatcher.match()`（HighlightRuleMatcher.kt:27）：`isRegex=false` 走 `matchLiteral()`（HighlightRuleMatcher.kt:32-41），即 `text.indexOf(pattern)` 纯字面量查找——把正则源码当普通字符串在正文中检索，**永不命中**。于是颜色规则从未参与绘制，引号区域自然无颜色叠加。

**次要根因（通道竞争）**：内置 `dialog_default` 自带 `textColor = 0xFFFF8C00`（HighlightRuleStore.kt:138）。若用户给该规则加字体（styleJson 同时含 textColor+fontPath），在 merge last-wins 语义下其字色会压过列表顺序位于其前的其他颜色规则（resolve 按规则列表序逐条 merge，ContentTextView.kt:124-133；手动高亮固定排最后压过规则，ContentTextView.kt:129-133）。此行为属设计内，但用户无感知。

**附带缺陷（fill-only 快绘吞样式）**：fill-only（纯背景色）样式 `needsPerColumnDraw=false`（HighlightStyle.kt:31-34）→ 不计入 `styledColumnCount`（TextColumn.kt:46-56）→ `TextLine.checkFastDraw()`（TextLine.kt:284-292）放行快绘 → `fastDrawTextLine()`（TextLine.kt:196-229）只画整行文字和选中框、**不画 fill 矩形** → 背景色高亮消失。`AppConfig.optimizeRender` 默认 false（help/config/AppConfig.kt:51-52）故默认不触发；但内置颜色样式预设多为 fill（黄底/蓝底，HighlightStyles.kt:13-14），用户开启渲染优化后会复现"颜色不显示"。

**验收标准**：

1. 对话规则设置独立字体 + 启用一条命中引号内文本的颜色规则（如"心理活动"或自建正则颜色规则）→ 双引号区域**同时**呈现独立字体与颜色叠加
2. 启用"对话高亮"预设 → 打开含对话章节 → 引号区域按规则着色（验证 isRegex 修复）
3. 启用"书名号高亮"预设 → 书名号区域出现波浪下划线
4. `optimizeRender` 开/关两种状态下，背景色（fill）高亮均可见
5. 回归：手动划线高亮与规则高亮同区叠加时，手动压过规则（ContentTextView.kt:129-133 顺序不变）

---

### 1.2 R-P1-2：预设规则不生效 + 无初始化常用规则

**现象**：① 高亮规则管理中预设规则"启用无效"（勾选后阅读页无高亮）；② 新装/升级后规则列表为空，无内置常用规则。

**根因 a——默认规则初始化逻辑缺失（确认存在）**：

- `HighlightRuleStore.load()`（HighlightRuleStore.kt:42-60）：`stored.isNullOrBlank()` 时直接 `return mutableListOf()`（45-47 行），**不播种任何默认规则**
- `reset()`（HighlightRuleStore.kt:78-83）虽有播种能力，但**全工程无任何调用方**（已全量检索确认）
- 无任何首启/升级回调（无 Application onCreate、无数据库 callback、无版本迁移）触发播种
- 规则存 SharedPreferences `PreferKey.highlightRuleItems`（PreferKey.kt:227），非 Room，故数据库升级不会触发

**根因 b——预设规则添加被静默丢弃（写库链路断裂）**：

- `HighlightPresetRuleDialog` 点击添加 → `onAddRule(item.copy(id = System.currentTimeMillis().toString(), ...))`（HighlightPresetRuleDialog.kt:80-89，**84 行覆盖了新 id**）
- `HighlightRuleActivity.showPresetRuleDialog` → `viewModel.update(rule)`（HighlightRuleActivity.kt:81-88）
- `HighlightRuleViewModel.update()`（HighlightRuleViewModel.kt:34-46）：`idx = list.indexOfFirst { it.id == rule.id }`，`idx >= 0` 才替换，**`idx < 0` 什么都不做——静默丢弃**（38-39 行）
- 新 id 必然 `idx < 0` → 规则未入库，但 UI 仍 toast "已添加预设规则"（HighlightRuleActivity.kt:85）→ 用户重启后规则消失
- 对照：`HighlightRuleEditDialog.save()`（HighlightRuleEditDialog.kt:221-246）已是正确的 upsert（229-236 行 `idx < 0` 时 `rules.add(r)`），ViewModel 与编辑对话框行为不一致

**根因 c——匹配链路过滤 enabled 正确，但命中率为零**：

- 过滤点存在且正确：`HighlightRuleStore.loadEnabled()`（HighlightRuleStore.kt:62-64）`filter { it.enabled && it.pattern.isNotBlank() }`；`ReadBook.loadHighlightRules()`（ReadBook.kt:261-264）只加载启用规则；规则集变化经 `upHighlightRules()`（ReadBook.kt:267-270）升版本号使 TextChapter 匹配缓存失效（ReadBook.kt:273-306）
- 但同 §1.1：内置规则 `isRegex=false` → 即使入库+启用，`matchLiteral` 永不命中 → "启用后无效"
- 佐证：`normalizeRules` 的内置刷新通道 `shouldRefreshBuiltin()`（HighlightRuleStore.kt:369-378）只处理乱码/旧 pattern，不修正 isRegex；`sanitizeRule` 恢复备份时 isRegex 默认 false（HighlightRuleStore.kt:322）

**即时性缺陷**：阅读页生效依赖 `HighlightRuleActivity.onDestroy` 才调 `ReadBook.upHighlightRules()`（HighlightRuleActivity.kt:139-142），勾选后返回阅读页的即时性依赖 Activity 销毁时序；管理列表勾选链路本身正确（`HighlightRuleAdapter` cbName 勾选 → `callBack.update(it)`，HighlightRuleAdapter.kt:80-87 → update 按已有 id 替换写库成功）。

**验收标准**：

1. **初始化**：清除应用数据后启动 → 阅读页菜单进高亮规则管理 → 可见 12 条内置规则，对话/书名号/括号/标题 4 条默认勾选
2. **预设添加**：预设对话框添加任一规则 → 管理列表出现 → 杀进程重启 → 规则仍在（验证写库）
3. **预设生效**：启用"对话高亮" → 打开含对话章节 → 引号区域按规则着色；启用"书名号高亮" → 书名号出现波浪下划线
4. **即时生效**：管理页勾选/取消勾选 → 直接返回阅读页 → 高亮立即出现/消失（不依赖重启阅读器）
5. **尊重清空**：用户手动删除全部规则后重启 → 列表保持为空（不重复播种）

---

## §2 非目标（Out of Scope）

- 不重构高亮绘制架构（Canvas 自绘 + 逐通道 merge 已验证天然支持字体+颜色叠加，零绘制层改动即可解决问题 1）
- 不迁移 SharedPreferences → Room（保持现有存储介质，仅修播种/写库/愈合逻辑）
- 不改动排版引擎（TextChapterLayout/ChapterProvider）的字体度量与分行逻辑
- 不改手动划线高亮（BookHighlight/Room）链路与手动压规则的叠加顺序
- 内置规则抽离到 `assets/highlight/default_rules.json` 为可选优化，非本期必须（最低成本方案为 Kotlin 硬编码补 `isRegex = true`）
- md3 衍生版整体 UI 风格借鉴（用户提及的大工程）不在本期，本期仅修功能缺陷
