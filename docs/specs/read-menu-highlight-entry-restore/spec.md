# spec — 阅读页三个点菜单补回高亮规则管理入口

## Intent

用户在阅读器小说页面右上角三个点中找不到「高亮规则管理」入口。git 排查证实：08-29 Compose 迁移（e706bae53）将三个点弹层改为 `buildOverflowActions()` 硬编码动作列表，从 XML 菜单（17 项）逐项翻译时漏掉了 `menu_highlight_rule`，并非有意移除。本任务补回该入口，恢复用户预期交互。

## Scope

> 2026-08-30 全面排查扩大范围：XML `book_read.xml` 全量逐项比对发现同批 Compose 迁移漏译共 6 项（详见 tasks §1.2），一并补回。

### 做
- `buildOverflowActions()` 补回 6 个漏挂动作项（含各自生效条件与勾选态）：
  1. 高亮规则管理（所有书）
  2. 设置字符集（本地书；离线缓存页已有替代入口，阅读页仍需恢复）
  3. TXT目录规则（本地TXT；目录页已有替代入口，阅读页仍需恢复）
  4. 删除注音标签（EPUB，checkable）
  5. 删除H标签（EPUB，checkable）
  6. EPUB核心调度模式（EPUB核心模式）
- 修正存量迁移 bug（第 7 项）：「段落规则」隐藏条件由 `isEpubCoreBook()` 改为真实 `book.isEpub`（现普通 EPUB 书误显示）
- State 语义拆分：`isEpub`（真实）与 `isEpubCoreMode`（核心模式）双字段
- 补全回调链路：`ReadMenuTitleBarActions` 扩充回调 → `ReadMenu.CallBack` 扩充方法 → `ReadBookActivity` 实现（复用 onMenuItemClick 既有处理逻辑）
- L2 真机验证：三个点弹层各项可见性条件正确、点击行为正确

### 不做
- 不动「我的」统一功能区既有入口（双入口并存，与换源等既有模式一致）
- 不动 XML `book_read.xml`（ActionMode 等旧路径仍在消费，删除属无收益风险）
- 不重构 `buildOverflowActions`（硬编码中文名是既有风格，本次只追加不翻新）

## Approach

### Selected Approach
在 `ReadMenuComposeComponents.kt` 的 `ReadMenuTitleBarActions` 扩充回调字段（`onHighlightRuleClick` 等 6 项对应回调），`buildOverflowActions()` 扩充参数并按 XML 原顺序在对应位置追加动作项（checkable 项沿用替换净化的 `checked + persistent` 模式，勾选态直接读 `ReadBook.book` 现有 API）；`ReadMenu.kt` 的 `Callback` 接口扩充对应方法（如 `showHighlightRuleManage()`），调用点 wiring；`ReadBookActivity` 实现各方法（复用 onMenuItemClick 既有处理逻辑体）。选此方案因完全复用既有动作项模式（与段落规则/日志等一致），改动最小、零新依赖。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 删除 XML `menu_highlight_rule`，只留统一功能区入口 | 用户明确要求恢复阅读页入口；统一功能区入口是并行补位产物，非替代品 |
| `buildOverflowActions` 改为从 XML menu 资源自动读取 | 重构既有 17 项硬编码列表，超出本次范围且引入 title 资源映射复杂度 |
| 在 `ReadBookActivity` 用 `openOptionsMenu()` 回退旧形态弹层 | 破坏 08-29 Compose 化成果，视觉/主题不一致 |

### Drawbacks
- 高亮规则与段落规则分居列表两端（高亮在书签后、段落在目录后），与统一功能区聚合理念不同。接受理由：与 XML 原顺序一致，用户记忆路径优先。

### Prior Art
- `buildOverflowActions` 既有 17 项动作的模式（ModernActionPopup.Action）
- `ReadMenu.Callback` → `ReadBookActivity` 实现的既有回调模式（如 `showParagraphRuleManage()`）

## Requirements

1. R1：三个点弹层必须包含「高亮规则管理」项，位于「添加书签」之后
2. R2：其余 5 个漏挂项按条件显示（设置字符集=本地书；TXT目录规则=本地TXT；删除注音/H标签=真实 EPUB 且勾选态正确；EPUB核心调度模式=EPUB核心模式）
3. R3：「段落规则」在普通 EPUB 书（非核心模式）不再显示（对齐原版 XML 语义）
4. R4：点击后行为与旧 XML 菜单完全一致（跳转/弹框/勾选翻转+重载），阅读菜单先收起
5. R5：不改变既有无条件动作的顺序与行为

## Scenarios

- S1 正常：打开任意书籍 → 三个点 → 「高亮规则管理」→ 进入管理页 → 返回无残留
- S2 本地书：打开本地 TXT → 三个点 → 可见「设置字符集」「TXT目录规则」，在线书不可见
- S3 EPUB：打开 EPUB（核心模式关）→ 三个点 → 可见「删除注音标签/删除H标签」（勾选态正确，点击翻转后正文重载），「核心调度模式」不可见，「段落规则」不可见；开启核心模式后「核心调度模式」可见
- S4 回归：逐项检查既有动作（书签/替换净化/重新分段等）位置与勾选态不受影响
