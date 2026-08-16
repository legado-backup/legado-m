# P10 · 书源编辑器 BookSourceEdit（S3 骨架样板）· v2

> 骨架级样板页（S3 表单/编辑器页）完整设计文档。开发/接线本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：BookSourceEditActivity → `ui/book/source/edit/`（含 6 Tab + CodeView + KeyboardToolPop）
- **骨架归类**：S3 表单/编辑器页（S3 唯一样板页）
- **对应 task**：tasks.md 12.16n（v2.8 预审，pages-inventory C2）、12.xx（待接线）、V-x（真机验证）；pages-inventory C2
- **fork 借鉴来源**：background/forks-deep-dive §7（HapeLee/MoRealm 表单）、§3（编辑器）

## 1. 设计意图

BookSourceEdit 是 S3 表单/编辑器骨架唯一样板页，编辑书源字段（URL/名称/分组 + **6 大规则 Tab：基本/搜索/发现/详情/目录/正文**，字段 13/11/10/11/10/11）。核心挑战：**规则字段编辑依赖 CodeView 编辑器内核（N 不迁移）+ KeyboardToolPop 补全**，是全 App 最复杂表单页。设计采用**渐进 Compose 化**：字段容器/分组卡片/底部保存 Compose 化，CodeView 编辑器内核保留原生 View（AD-02 红线）。它确立 S3 骨架范式：GlassTopAppBar + SettingsCard 分组字段 + CodeView + KeyboardToolPop + 未保存拦截，供替换编辑/自动任务/词典等 S3 页抄写。

> ⚠️ **风险评估（2026-08-12 实施者）**：6 Tab + CodeView + JSON 字段编辑全量 Compose 重写风险高，建议**谨慎/分阶段**（先字段区 Compose，CodeView 保留 View 桥接），避免破坏书源引擎。
>
> ✅ **V3 裁决（2026-08-13 收敛，源码核实）**：**Tab 用 Compose `PrimaryScrollableTabRow`（6 Tab 需横向滚动）+ `when(selectedTabIndex)` 切换 6 个独立 LazyColumn**。否决 HorizontalPager（源码现状 `BookSourceEditActivity.kt:238-250` 用 View `TabLayout` + 单 RecyclerView 换 `editEntities` 数组；6 Tab 含重型 CodeView 内核，Pager 默认预组合相邻页会并行 composition 同时实例化相邻 Tab 的 CodeView，违背红线「每 CodeView 只注册一次」；表单编辑页滑动翻页非核心交互）。否决单 LazyColumn 整体换数组（Compose 换数组 item key 变化触发 CodeView 重建，同样违背红线）。`when` 切 6 个独立 LazyColumn 使每 Tab 独立 composition 状态 + CodeView 单次注册，与现状「按 Tab 切换内容」语义一致。

## 2. 布局结构

```
┌─────────────────────────────────────┐
│ GlassTopAppBar 磨砂顶栏              │  ← 返回/标题/菜单（全屏编辑/保存/调试/清Cookie/复制粘贴源/扫码/分享文本+二维码/日志/帮助/登录/源变量，12+ 项）
├─────────────────────────────────────┤
│ 顶部快捷工具条 SettingsCard 分组       │  ← 类型 Spinner（默认/音频/图片/文件/视频）+ 5 ThemeCheckBox（删死字段 cb_is_enable_review）
├─────────────────────────────────────┤
│ Tab 区（6 Tab：基本/搜索/发现/详情/目录/正文）│
├─────────────────────────────────────┤
│ ┌─ 字段分组 SettingsCard ────────┐  │  ← 分组字段表单
│ │  SettingsClickRow/输入行        │  │
│ └─────────────────────────────────┘  │
│ ┌─ CodeView 代码编辑区 ──────────┐  │  ← 内核保留（N）
│ │  + KeyboardToolPop 补全条       │  │
│ └─────────────────────────────────┘  │
├─────────────────────────────────────┤
│ 底部保存/取消 12dp 圆角 48dp 高       │
└─────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 顶栏 | `GlassTopAppBar`（§3.4） | — | 返回/标题/12+ 项菜单（下沉 `AppDropdownMenu`，对齐 C2 V2） |
| 快捷工具条 | `SettingsCard` 分组（类型 Spinner + 5 ThemeCheckBox） | VM StateFlow | 收敛 C2 V10；删 `cb_is_enable_review` 死字段 |
| Tab | `PrimaryScrollableTabRow`（6 Tab 滚动）+ `when(selectedTabIndex)` 切 6 个独立 LazyColumn | ViewModel | 6 Tab（基本/搜索/发现/详情/目录/正文）；**V3 裁决：否决 Pager/单 LazyColumn 换数组**（见 §0 裁决） |
| 字段分组 | `SettingsCard` + `SettingsClickRow`（§3.4 卡18dp/h16v12） | VM StateFlow | 分组字段 |
| 代码编辑 | CodeView（N 不迁移）+ KeyboardToolPop | — | 内核保留，AndroidView 桥接 |
| 底部 | 保存/取消按钮（12dp 圆角 48dp） | — | |

## 3. 组件选型（§3.4 规格引用）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `GlassTopAppBar` | surface 实底 + titleMedium | 顶栏 |
| `SettingsCard` | 卡 18dp、标题 h16 v12、surfaceVariant、1dp elevation | 字段分组容器 |
| `SettingsClickRow` | h16 v12、bodyLarge | 字段行 |
| `AppEditDialog` | M3 AlertDialog 字段输入 | 规则小窗/字段编辑 |
| `AppDropdownMenu` | M3 DropdownMenu（§3.4） | 顶栏 12+ 项菜单下沉（对齐 C2 V2） |

> 🔴 **内核红线（pages-inventory C2 预审，CodeView 侧）**：`RuleComplete.kt` 零 UI 依赖纯函数，type 1/2/3 映射表需**逐行原样搬迁** + autoComplete 作为 VM 持久态；`CodeView` 6 Pattern（addLegadoPattern/addJsonPattern/addJsPattern）用 **AndroidView 桥接原样实例** + 每 CodeView 只注册一次 + TextWatcher 回写桥接受控输入；`KeyboardToolPop`（PopupWindow，5+ 页复用）**原样保留**，仅复刻 insets 接线否则键盘弹出工具条错位。

## 4. 交互流程

| 触发 | 行为 | ≤2 步 | 备注 |
|------|------|-------|------|
| Tab 切换 | 切换规则编辑区 | ✅ | TabRow 同步 Pager |
| 字段编辑 | SettingsClickRow → AppEditDialog | ✅ | 输入回写 VM |
| CodeView | 键盘工具条补全（undo/redo/帮助插入） | ✅ | 内核保留 |
| 全屏编辑 | 跳 CodeEditActivity（带回光标 360ms） | ✅ | 内核 |
| 保存 | 校验（URL/名称非空 + **URL 变更书架迁移弹窗**）→ 落库 | ✅ | 未保存退出拦截 runCatching 对比原始值 |
| RuleComplete 补全 | CodeView addLegado/addJson/addJs Pattern 自动补全 | ✅ | 内核映射表搬迁入 VM |
| 正文 Tab 净化 | replaceRegex 净化替换（replacement/scope_timeout） | ✅ | C2 功能点（净化二级页 V11 待产品确认） |

## 5. 状态管理（§4 范式）

- 数据源：BookSourceEditViewModel（编辑态数据类）+ onSave 校验
- 字段全部提升为 VM 数据类；未保存拦截用 `runCatching` 对比原始值（§2 S3）
- **禁止**：Fragment 散落 mutableStateOf；remember 帧固定 AppConfig

## 6. 三态（表单页）

- 加载：字段区 loading 态（顶部 LinearProgress）；空态不适用；错误：规则校验失败 → Snackbar/错误提示（`ThemedSnackbarHost`）

## 7. i18n 与无障碍

- 全部文案 `strings.xml` 双语（Tab/字段名/保存取消/校验提示）；无硬编码中文
- CodeView 触控 ≥48dp；KeyboardToolPop 按钮 ≥48dp

## 8. 验收标准（交付门禁）

- [x] 布局与 §2 框图一致；6 Tab（基本/搜索/发现/详情/目录/正文）完整；CodeView 内核保留（AD-02 红线）
- [x] 内核红线三条落地：RuleComplete 映射表搬迁入 VM + CodeView 6 Pattern 单次注册桥接 + KeyboardToolPop insets 复刻
- [x] 组件来自 §3 表，规格与 §3.4 一致
- [x] 顶部快捷工具条 SettingsCard 分组 + 删 `cb_is_enable_review` 死字段
- [x] 字段分组用 SettingsCard；无私有表单布局
- [x] 未保存退出拦截完整；保存校验（URL/名称非空 + URL 变更书架迁移弹窗）通过落库
- [ ] 真机功能点覆盖用例全过（FR-11：6 Tab 编辑/自动补全/净化替换/保存校验/全屏编辑）
- [x] §3.3 实施回执已填（tasks 12.16n + pages-inventory C2）
- [x] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt

```
Material 3 Android 阅读App 高保真UI设计稿，书源编辑表单页，顶部Tab 6个（基础/发现/书籍/目录/正文/JS），分组卡片表单字段，代码编辑区，底部保存取消按钮，低饱和护眼色系，卡片圆角18dp，大量留白，中文界面
```

## 10. 变更记录

- 2026-08-13：建立本完整文档（S3 骨架样板，标注渐进 Compose 化风险）
