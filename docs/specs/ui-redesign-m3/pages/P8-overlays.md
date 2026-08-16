# P8 正文内浮层 / 弹窗族（Overlays & Dialog）

> **升级 v2（2026-08-13）**：本页覆盖「阅读器浮层 Sheet 化（AD-06）+ 全仓 Dialog 收敛到 S6 三层体系（L1 Sheet / L2 Dialog 族 / L3 透明窗壳）」。另一 AI 开发时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：阅读器浮层（`ui/book/read/` read_menu/search_menu/config 弹窗族/TextActionMenu）+ 全仓 Dialog 族收敛（`ui/widget/components/` Dialog 族 6 组件已建）+ 阅读器弹层族（🆕 待建）
- **骨架归类**：S6 弹窗/透明窗（L1 浮层面板 + L2 语义 Dialog 族 + L3 透明窗壳）；**阅读器浮层以 P2-reader 为权威版（S5）**
- **对应 task**：tasks.md `12.22`（Dialog 族 6 组件已建）、`12.24`（Phase4 阅读器浮层 Sheet 化已交付）；pages-inventory B1（阅读器）、B2-B4（目录/书签/高亮）
- **fork 借鉴来源**：forks-deep-dive §3（HapeLee 双引擎 ModalBottomSheet / MoRealm 单 Box 兄弟浮层栈）、§9.5（legado-archive）、§10.2/§11.3（Legado_Max/325506 Dialog 体系）

## 1. 设计意图（一段话）

核心目标 = **消灭多层弹窗嵌套 + 浮层语义统一**。痛点：原版 config/ 12 个 Dialog 风格各异、阅读器多层弹窗（弹窗里再弹窗）。解法：阅读器浮层统一 `AppModalBottomSheet`（单一 activeSheet 单态 + 三类渲染），业务 Dialog 全收敛 L2 Dialog 族（6 组件已建）。**本文档是验收的「为什么」：任何弹窗/浮层改造不得破坏「BackHandler 优先级链」「3s 自动隐藏」「阅读设置不藏三层内」三项。**

## 2. 布局结构（文字框图 + 区块表）

```
阅读器（S5 全屏沉浸，P2-reader 权威版）：
┌──────────────────────────────────────┐
│ 正文层 AndroidView（ReadView，零改动）   │ ← AD-02 红线
├──────────────────────────────────────┤
│ ② 菜单层：scrim + 顶栏 + 亮度竖条 + 底栏 │ ← R1 渐进 Compose 化
├──────────────────────────────────────┤
│ ④ 弹层区：单一 activeSheet（一次一个）   │ ← AppModalBottomSheet
│    目录/书签/高亮 三Tab · 阅读设置 · 更多  │ ← ReaderBookSheet（🆕 待建）
├──────────────────────────────────────┤
│ ⑤ 选区菜单 TextActionSelectionMenu     │ ← 锚点坐标来自 View
└──────────────────────────────────────┘

全仓 Dialog（S6 三层体系）：
L1 浮层面板 → AppModalBottomSheet（内容多/多Tab/可拖拽）
L2 语义 Dialog 族 → ConfirmDialog/AppEditDialog/AppSelectDialog/
    AppNumberPickerDialog/AppTextDialog/AppWaitDialog（✅ 已建 12.22）
L3 透明窗壳 → FileAssociation/OnLineImport/VerificationCode/OpenUrlConfirm（保留）
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 弹层容器 | `AppModalBottomSheet`（§3.4：containerColor=surface） | activeSheet 单态 | 孤儿待接线 |
| 目录/书签/高亮 | **现状** `BookTocBookmarkSheet`（双 Tab 目录/书签，已接线 12.24）｜**蓝图** `ReaderBookSheet`（三 Tab HorizontalPager 72% 高） | Room Flow | from HapeLee |
| 阅读设置 | 可拉伸面板（字号/亮度/夜间/行距/对齐一屏） | ReadBookConfig | 最高优先级 |
| 选区菜单 | `TextActionSelectionMenu`（🆕 待建：View 坐标桥接） | textMenuPosition | 替换 TextActionMenu |
| 高亮色盘 | `HighlightStyleDialog` 升级 chooser（色板+下划线） | HighlightStyle | 2 行 6 色 |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `AppModalBottomSheet` | L1 浮层面板容器 | 弹层区统一宿主 |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp、destructive 确认钮 error | 删除/清空确认 |
| `AppEditDialog` | EditField 列表 + 间距 8dp | 单/多字段输入（替代 DialogEditText） |
| `AppSelectDialog` | RadioButton primary 高亮 | 分组选择/换源/主题列表 |
| `AppNumberPickerDialog` | Slider+输入双联动 | 自动翻页速度/进度跳页 |
| `AppTextDialog` | Markwon 渲染、内容 maxHeight 70% | 文本/MD/HTML 查看 |
| `AppWaitDialog` | 裸 Dialog 居中 primary 转圈 | 阻塞等待 |
| `ReaderBookSheet`（🆕 待建） | 三 Tab HorizontalPager 72% 高（§3.4 阅读器族 🔵） | 目录/书签/高亮弹层 |
| `ReaderMoreActionsSheet`（🆕 待建） | 阅读设置可拉伸面板（§3.4 阅读器族 🔵） | 字号/亮度/夜间/行距/对齐 |
| `TextActionSelectionMenu`（🆕 待建） | 选区工具条（View 坐标桥接，色盘 2 行 6 色） | 替换 TextActionMenu |
| `HighlightStyleDialog`（存量升级） | 高亮色盘 chooser（色板+下划线） | 高亮选色 |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 目录/书签空态 |
| `BookTocBookmarkSheet`（✅ 已接线 12.24） | 双 Tab：目录/书签 + 章节列表 | **现状基座**（ReaderBookSheet 蓝图三 Tab 由它演进） |

> ⚠️ Dialog 族 6 组件 §3.4 全 ✅（12.22 已建）。`AppModalBottomSheet` 已接线（§3 组件表 ✅）；`ReaderBookSheet`/`ReaderMoreActionsSheet`/`TextActionSelectionMenu`/`HighlightStyleDialog` 已登记 ui-standards §3 组件目录（🆕 待建/存量升级），真值行待接线时补。**职责边界**：阅读器浮层以 `P2-reader.md` 为权威版（R0-R4 渐进），本页负责 S6 三层体系 + 全仓 Dialog 收敛台账。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 底栏「目录」 | 弹 `ReaderBookSheet`（章节列表+进度%+多选书签） | ✅ | 1 步 |
| 底栏「更多」 | `ReaderMoreActionsSheet`（字号/亮度/夜间/行距/对齐一屏） | ✅ | 阅读设置不藏三层内 |
| 长按高亮文字 | 工具条划色（色盘 2 行 6 色）→ 直接改样式 | ✅ | 无二级 |
| 浮层 3s 无操作 | 自动收起半透明胶囊（保留进度） | — | 排除滚动/输入焦点 |
| BackHandler | 弹层→搜索→自动翻页→菜单路由→退出 | — | MoRealm 优先级链 |

## 5. 状态管理（§4 范式）

- **单一 `activeSheet` 单态**（sealed interface）+ `activeDialog`：一次一个浮层，杜绝多层弹窗嵌套。
- 渲染三策略：① 常驻组合 + show 标志（绝大多数，保进出场动画）；② `when(activeSheet)` 条件组合（轻量/需独立 VM，key+DisposableEffect）；③ `activeDialog` → L2 Dialog 族。
- `menuLayoutIsVisible` 三信号等价（bottomDialog>0 || readMenu.isVisible || searchMenu.bottomMenuVisible）——Compose 壳必须保持，被 onBackPressed/upSystemUiVisibility/autoPager 6+ 处引用。
- BackHandler 优先级链：弹层 → 搜索 → 自动翻页 → 菜单路由返回 → 退出阅读。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 章节加载沿用正文层（零改动） | 正文引擎不迁移 |
| 空态 | 目录/书签空 → `EmptyStatePlaceholder` | 待接线 |
| 错误 | 阅读设置/搜索无结果 → 空占位 + 重试 | 待接线 |

## 7. i18n 与无障碍

- `BookTocBookmarkSheet` Tab「目录/书签」已修复为 `stringResource(R.string.source_tab_toc/bookmark)`（复用存量双语 key）✅。
- **⚠️ 公共组件硬编码中文 3 处待清**（§6.1）：`PillNavigationBar`（Tab label 已废弃 defaultTabs()）、`SettingsSearchBar`（「搜索设置」）、`SummaryCard`（「书」）——接线页全部继承，公共组件 i18n 最先清。
- 触控 ≥48dp；Icon contentDescription；颜色只 colorScheme。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 阅读器浮层遵循 P2-reader 权威版（R0-R4 渐进，正文零改动红线 6 条）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] 单一 activeSheet 单态 + BackHandler 优先级链生效（无多层弹窗嵌套）
- [ ] 阅读设置一屏可达（不藏三层内）；浮层 3s 无操作自动淡隐（排除滚动/输入）
- [ ] 全仓 Dialog 已收敛 S6 三层体系（页面无私有弹窗布局）
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory B1）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App 阅读中底部软弹抽屉(BottomSheet)高保真：
章节目录列表在纸感阅读器下半部，可拉伸，圆角顶，列表项有 分割线 与 当前章高亮，
页码百分比在底部,浅色暖黄护眼配色,抽屉外正文虚化,回收禁用多层弹窗,中文界面
```

## 10. 变更记录

- 2026-08-13：v2 升级——确立 S6 三层体系（L1 Sheet/L2 Dialog 族 6 组件已建 12.22/L3 透明窗壳保留）+ 阅读器浮层单一 activeSheet 单态（对应 task 12.22/12.24）。
