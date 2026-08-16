# P3 书籍详情页（BookInfo）

> **已接线页升级 v2（2026-08-13）**：对齐 BookInfoActivity 12.23 壳层接线现状（7 项已修）+ 登记剩余违例。另一 AI 开发本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：BookInfoActivity（`ui/book/info/`，1189 行，View 壳 + Compose 桥接）
- **骨架归类**：S4 详情/阅读页
- **对应 task**：tasks.md `12.23`（S4 壳层接线，已交付）、`12.16m`（v2.8 预审）；pages-inventory B6
- **fork 借鉴来源**：forks-deep-dive §11.1（325506 导航路由）、§9.4（书源详情）；HapeLee 封面 Hero

## 1. 设计意图（一段话）

详情页是「读/收/换源」决策中枢，核心目标 = **一键开始阅读 + 信息一览无余 + 操作 ≤2 步**。与旧版差异：① 顶栏已换 `GlassTopAppBar`（12.23 接线）；② 底部操作栏已 Compose 化（OutlinedButton 加/删书架 + Button 阅读，12dp 圆角 48dp 高）；③ 16 项顶栏菜单已全下沉 `AppDropdownMenu`（MenuAction.checked 勾选态）。**本文档是验收的「为什么」：详情页改造不得破坏四渲染简介/换源/分组/目录/书架/阅读分发的完整性。**

## 2. 布局结构（文字框图 + 区块表）

```
┌──────────────────────────────────────┐
│ GlassTopAppBar 顶栏（12.23 ✅）        │ ← 返回/书名/更多(AppDropdownMenu 16项)
├──────────────────────────────────────┤
│ 封面（CardView 静态，V3 Hero 待落地）    │ ← 点击 ChangeCoverDialog / 长按 PhotoDialog
│ 书名/作者/字数/状态                     │
│ [开始阅读] [加入书架]  Compose 按钮组    │ ← 12.23 ✅ 12dp圆角 48dp高
├──────────────────────────────────────┤
│ 简介四渲染（useweb/usehtml/md/纯文本）   │ ← 内核行为保留
│ 章节目录预览（1行 → TocActivity）        │ ← V4 多Tab/目录预览待落地
│ 标签 / 分组 / 下载                       │
└──────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 顶栏 | `GlassTopAppBar`（§3.4：surface 实底） | — | 12.23 ✅ |
| 底部操作 | Compose `Button`（§1.1：12dp 圆角）/`OutlinedButton` | BookInfoViewModel | 12.23 ✅ |
| 顶栏菜单 | `AppDropdownMenu`（§3.4：条目≥48dp，checked 勾选） | MenuAction 数据驱动 | 12.23 ✅ 16 项 |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `GlassTopAppBar` | surface 实底、titleMedium、标准高度 | 顶栏 ✅ |
| `AppDropdownMenu` | M3 DropdownMenu、条目 h12、checked 勾选 primary | 16 项菜单 ✅ |
| `AppModalBottomSheet` | L1 浮层面板 | 换源/分组（V8 后续） |

> ⚠️ §3.4 引用组件均 ✅。规格与代码冲突以 §3.4 为准。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点「开始阅读」 | `tvRead` 按类型分发进阅读 | ✅ | 现状 |
| 点「加入书架」 | 即时状态变更 | ✅ | V12 微交互动画待落地 |
| 点封面 | ChangeCoverDialog | ✅ | |
| 长按封面 | PhotoDialog | ✅ | |
| 点「目录」 | 跳 TocActivity | ✅ | V4 目录预览待落地 |
| 点分组/换源 | GroupSelectDialog / ChangeBookSourceDialog | ✅ | V8 L2 族收敛待落地 |
| 顶栏菜单 | `AppDropdownMenu` 16 项 | ✅ | 12.23 ✅ |

## 5. 状态管理（§4 范式）

- 数据源：复用现状 `BookInfoViewModel` 数据流（不改业务）
- **⚠️ V5 违例待修**：VM 两 LiveData + 可变公有字段（inBookshelf/hasCustomBtn/bookSource）+ Activity 直写 VM 字段（:160/:204-206/:502）+ 7 私有态散落——需收敛为 StateFlow + 受控组件。
- 旋转/进程：现状无 onSaveInstanceState 丢失——补 `rememberSaveable`（P1 队列）。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 现状文字「章节:加载中」 | **V10 违例**：需换顶部 LinearProgress/骨架 |
| 空态 | — | 详情页一般无空态（书籍不存在 → 错误态） |
| 错误 | 仅 toast，无占位 | **V10 违例**：需 `EmptyStatePlaceholder` 错误分支 + 重试 |

## 7. i18n 与无障碍

- **12.23 已修（V6）**：i18n 硬编码 15 处 → 16 key 双语（上传中/未配置webDav/下载中/书源不存在/源变量注释/书籍变量注释/Unexpected webFileData/Loading/未找到书籍/webDav没有配置/下载远程书籍失败/LoadTocError/已下载/清理缓存出错）。
- **12.23 已修（V7）**：layout-land `#50000000` → transparent50 token。
- **12.23 已修（V11）**：ic_book_last/ic_groups/ic_folder_open 语义错位 + 触控 <48dp → AccentBgTextView 48dp+。
- 新增文案走 strings.xml（zh+en）双语；Icon contentDescription。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（顶栏 + 封面信息 + 按钮组 + 简介 + 目录预览）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] **V3**：共享折叠封面（AD-08 默认关）落地；**V4**：多 Tab 信息流 + 目录预览 + 相似推荐
- [ ] **V5**：状态收敛 StateFlow；**V10**：三态用规范组件
- [ ] **V8**：6 类业务弹窗（删除确认/WebFile/换源/分组/封面/变量）收敛 L2 Dialog 族
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory B6）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App 书籍详情页高保真：顶部磨砂栏，
左侧大圆角封面（Hero效果放大留白），右作者书名小字，底部两个圆角主操作按钮
"开始阅读""加入书架"，浅色暖黄背景护眼，下方简介线性与目录列表，低饱和配色无撞色，中文界面
```

## 10. 变更记录

- 2026-08-13：v2 升级——对齐 12.23 壳层接线现状（GlassTopAppBar/按钮组/AppDropdownMenu 16 项/i18n/色 token/无障碍 7 项已修），登记 V3/V4/V5/V8/V10 后续队列。
