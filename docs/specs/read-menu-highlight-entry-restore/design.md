# design — 阅读页三个点菜单补回漏挂动作项（7 项）

> 2026-08-30 范围演变：初判 1 项（高亮规则）→ 全面排查扩为 6 项漏挂 → 穿透自审再发现 1 项存量迁移 bug（段落规则误显示），共 7 项。

## Technical Approach

三个点弹层现状：`ReadMenuTitleBar`（ReadMenuComposeComponents.kt）右上角三点 Icon 的 `clickable` 内调用 `buildOverflowActions()` 构建 `List<ModernActionPopup.Action>`，经 `ModernActionPopup.show()` 展示。动作列表为硬编码中文 title + 回调 lambda。

### 漏挂/错挂清单（XML 项 → 补挂条件）

| 动作项 | 显示条件 | 勾选态 | 行为（复用 ReadBookActivity 既有逻辑） | 备注 |
|--------|---------|--------|--------------------------------------|------|
| 高亮规则管理 | 无条件 | — | `startActivity<HighlightRuleActivity>()` | 唯一入口丢失 |
| 设置字符集 | 本地书（`isLocalBook`） | — | `showCharsetConfig()` | 离线缓存页有替代入口 |
| TXT目录规则 | 本地 TXT（`book.isLocalTxt`） | — | `TxtTocRuleDialog(book.tocUrl)` | 目录页有替代入口 |
| 删除注音标签 | EPUB（真实 `book.isEpub`） | `book.getDelTag(Book.rubyTag)` | 翻转 delTag + `saveRead(fullUpdate)` + 重载 | 唯一入口丢失 |
| 删除H标签 | EPUB（真实 `book.isEpub`） | `book.getDelTag(Book.hTag)` | 同上 | 唯一入口丢失 |
| 核心调度模式 | EPUB 核心模式（`isEpubCoreBook()`） | — | `showEpubCoreScheduleModeDialog()` | 唯一入口丢失 |
| 段落规则（修正） | 改用真实 `book.isEpub` 隐藏 | — | 既有回调不变 | 存量 bug：现误用 isEpubCoreBook()，普通 EPUB 书误显示 |

### 实施链路

1. **State 拆字段（阻塞点 P1 修复）**：`ReadMenuTitleBarState` 改为携带三个独立布尔：`isLocalTxt`（`ReadBook.book?.isLocalTxt`）、`isEpub`（`ReadBook.book?.isEpub` 真实值）、`isEpubCoreMode`（`callBack.isEpubCoreBook()`）。**禁止**沿用现有 `isEpub = callBack.isEpubCoreBook()` 混用语义（该方法 = `book.isEpub && AppConfig.useExperimentalEpubCore`，仅核心模式为 true）
2. `ReadMenuTitleBarActions` 增加 6 个回调字段：`onHighlightRuleClick` / `onSetCharsetClick` / `onTocRegexClick` / `onDelRubyTagClick` / `onDelHTagClick` / `onEpubScheduleModeClick`
3. `buildOverflowActions()` 扩参，按 XML 相对顺序精确插入：
   - 列表首部（添加书签之前）：TXT目录规则?（isLocalTxt）→ 设置字符集?（isLocalBook）
   - 「添加书签」之后：高亮规则管理
   - 「重新分段」之后、「图片样式」之前：删除注音标签?（isEpub，checkable）→ 删除H标签?（isEpub，checkable）→ 核心调度模式?（isEpubCoreMode）
   - 「段落规则」隐藏条件改用真实 `isEpub`
   - checkable 项沿用「替换净化」的 `checked + persistent` 模式，勾选态即时读 `ReadBook.book`
4. `ReadMenu.kt`：`CallBack` 接口增加 6 方法（**已核实唯一实现类为 ReadBookActivity，编译安全**）；调用点 wiring；state 构造补 3 字段
5. `ReadBookActivity.kt`：实现 6 方法（复用 onMenuItemClick 既有逻辑体；del ruby/h tag 的翻转逻辑提取为私有方法供 XML 路径与新回调共用，避免复制）

## Architecture Decisions

### AD-01: 动作项硬编码追加而非资源驱动
- **Context**: `buildOverflowActions` 现有 17 项全部为硬编码中文 title，XML 菜单与 Compose 列表并存双轨
- **Concern**: 补回的 6 项以何种方式加入列表
- **Decision**: 按既有模式硬编码追加，不做资源驱动重构
- **Goal**: 最小改动、与既有项风格零差异、低回归风险
- **Tradeoff**: 双轨（XML/Compose）继续并存，后续增项仍需双处维护
- **Status**: Accepted

### AD-02: 双入口并存（阅读页 + 统一功能区）
- **Context**: 统一功能区已有 `highlightRule` 入口（cce20ba93），阅读页入口本次补回
- **Concern**: 是否保留两处入口
- **Decision**: 保留双入口，不做去重
- **Goal**: 阅读场景就近管理 + 我的页集中管理并存，与换源等既有功能入口布局一致
- **Tradeoff**: 入口冗余，可接受（高亮规则为高频创作型功能）
- **Status**: Accepted

### AD-03: State 拆分 isEpub 与 isEpubCoreMode 双字段
- **Context**: 现有 wiring `isEpub = callBack.isEpubCoreBook()` 将「EPUB 书」与「EPUB 核心模式」混为一谈（后者 = 前者 && useExperimentalEpubCore），已实锤导致段落规则在普通 EPUB 书误显示
- **Concern**: 补回的 ruby/H 标签（应见所有 EPUB）与核心调度模式（应仅核心模式）需要两种不同条件
- **Decision**: State 携带 `isEpub`（book.isEpub 真实值）与 `isEpubCoreMode`（isEpubCoreBook()）两个独立字段，各自条件各取所需，顺带修正段落规则隐藏条件
- **Goal**: 全部 EPUB 相关条件语义精确，且消除存量误显示
- **Tradeoff**: 修正段落规则行为属用户可感知变化（普通 EPUB 书不再显示段落规则），但与原版 XML 语义一致
- **Status**: Accepted

### AD-04: 勾选态直接读 ReadBook.book 而非经 State 流转
- **Context**: 弹层每次点击时即时构建动作列表（非长驻 Composable），既有替换净化/重新分段已直接读 `ReadBook.book`
- **Concern**: del ruby/h tag 勾选态的获取方式
- **Decision**: 与既有 checkable 项一致，`buildOverflowActions` 内直接读 `ReadBook.book?.getDelTag(...)`
- **Goal**: 勾选态始终即时准确，不引入额外状态同步
- **Tradeoff**: 依赖点击时点数据新鲜度——与既有模式一致，风险已被既有项验证
- **Status**: Accepted

## Data Flow

用户点击三个点 → `buildOverflowActions()` 按书类型条件生成动作列表（勾选态即时读 `ReadBook.book`）→ `ModernActionPopup.show()` 弹层 → 点击动作项 → 对应回调 lambda → `ReadMenu.Callback` 方法 → `ReadBookActivity` 实现（跳转 Activity / 弹 DialogFragment / 翻转 delTag 后重载正文）。无数据库 schema 变更（delTag 为 Book 既有字段）。

## File Changes

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/ui/book/read/ReadMenuComposeComponents.kt` | `ReadMenuTitleBarState` +3 字段（isLocalTxt/isEpub/isEpubCoreMode）；`ReadMenuTitleBarActions` +6 回调；`buildOverflowActions` 扩参 +6 条件动作项 +段落规则条件修正；三点 clickable 透传 |
| `app/src/main/java/io/legado/app/ui/book/read/ReadMenu.kt` | `CallBack` 接口 +6 方法；调用点 wiring；state 构造补 3 字段 |
| `app/src/main/java/io/legado/app/ui/book/read/ReadBookActivity.kt` | 实现 6 个 CallBack 方法；del ruby/h tag 翻转逻辑提取为私有方法复用 |

不涉及资源文件、manifest、数据库。

## 穿透自审记录（2026-08-30 二轮）

| 检查项 | 结论 |
|--------|------|
| CallBack 实现类数量 | 仅 ReadBookActivity 1 个（Grep `ReadMenu\.Callback` 全库 + 类声明 L243 核实），接口扩方法编译安全 |
| isEpub 语义 | 阻塞点 P1 实锤并修复（AD-03） |
| 入口唯一性 | TXT目录规则（目录页）、设置字符集（离线缓存页）有替代入口；高亮规则/EPUB×3 唯一入口丢失 |
| 底部按钮行/长按子弹层 | 无漏项（前轮已核） |
| 验证风险 | S2/S3 需本地 TXT 与 EPUB 样本书，实施阶段先确认设备书架样本 |
