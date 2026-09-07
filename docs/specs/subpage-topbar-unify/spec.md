# spec.md — 子页面顶栏样式统一

## Intent
用户反馈：书源管理、订阅源管理、TXT目录规则、替换净化、字典规则、高亮规则管理、应用主题等页面顶栏是"标准的"，但主题设置、备份与恢复、公网Web访问、AI设置、自动任务管理、视频设置、订阅源全局搜索、书架媒体、书签、阅读记录、其他设置、精准管理、URL访问记录、日志管理、编辑订阅源等页面顶栏"五花八门，要么纯黑要么纯色"，不跟随主题设置体系。要求全面排查所有子页面并统一顶栏样式到标准决策链。

**定位升级（检查点 R2 用户锚定）**：本任务是对标 legado_NG、服务"不影响主题设置体系前提下除阅读器外全面 Compose 化"终极目标的**取色铺路子任务**——顶栏语义色单源化后，master-track B 波次的页面迁移可零成本继承顶栏颜色。

根因（探索已锁定）：4 套顶栏组件存在 3 条取色管线，`TopBarConfig.defaultBackgroundColor` 硬编码夜间 `Color.BLACK`/日间 `Color.WHITE`，被 ConfigTopBar 与 MainTopBarView(Mode.SUB) 无条件消费。

## Scope
### 包含
- `TopBarConfig` 新增统一子页顶栏取色决策函数（三级链）
- 4 套顶栏组件收敛：ConfigTopBar **消灭**（并入 GlassTopAppBar）；AppManagementTopBar、GlassTopAppBar、MainTopBarView(Mode.SUB) 接入统一函数
- XML 残留死代码顶栏清理（4 处）
- 真机 L2 全量页面顶栏验证（含设置页溢出菜单专项回归）

### 不包含
- 主页 Mode.MAIN 顶栏（主界面设计，含标签栏/搜索，不动）
- 沉浸豁免页：ImageCrop（深色裁剪）、ImageGallery/ImageDetail（黑底看图）、VideoPlayerActivity 播放器内顶栏、SearchActivity 自绘搜索头
- 顶栏包壁纸态 crop 裁切像素级对齐（GlassTopAppBar 已有近似实现，随 ConfigTopBar 消灭差异面缩小）
- Mode.SUB 22 页 View 宿主的 Compose 迁移（列入 master-track 波次随页面逐页消亡）
- 管理族顶栏高度（48dp）与字号调整（用户认可的标准，不变）
- 主题设置体系本身（ThemeStore/颜色主题功能）

## Approach

### Selected Approach
两层收敛：**取色单点化 + 组件缩减（4→3）**。

**第一层：取色单点化。** 在 `TopBarConfig` 中新增统一决策函数（暂名 `resolvePageBarColor(context, config)`），实现与 `AppManagementScaffold` 完全一致的三级决策链：

1. `TopBarConfig.hasCustomBackground(config)` → 显式自定义背景色
2. `AppConfig.immersiveManageBar` 开启 → `context.backgroundColor`（页面底色沉浸）
3. 兜底 → `context.primaryColor`（主题主色）

所有顶栏组件的"非壁纸基色"全部改为消费该函数；壁纸态（顶栏包 regular + wallpaper）保持 `withOpacity(resolveBackgroundColor, alpha)` 原语义。

**第二层：组件缩减（4→3，用户裁决 R1 检查点）。** 顶栏组件现状 4 套并存是架构债，收敛如下：

| 组件 | 终态定位 | 动作 |
|------|---------|------|
| `GlassTopAppBar` | **Compose 页唯一通用顶栏** | 保留，接入统一函数 |
| `ConfigTopBar`（ConfigActivity 私有） | **消灭** | 仅 1 个调用点（ConfigActivity:135），改用 GlassTopAppBar + MenuAction 适配（一级图标直出 + 溢出下拉菜单），删除 ConfigTopBar 定义与 decodeTopBarBitmap |
| `AppManagementTopBar`（AppManagementScaffold 内私有） | **脚手架内置顶栏**（管理族标准本体，非独立组件） | 保留，取色逻辑改调统一函数去重 |
| `MainTopBarView`（View 体系） | **View 宿主过渡态**：Mode.MAIN（主界面 4 Tab）长期保留；Mode.SUB 22 页列入 master-track 迁移清单，随页面 Compose 化逐页消亡 | 本轮 Mode.SUB 取色接统一函数 |

收敛后修顶栏 bug 只需考虑三层且边界清晰：Compose 通用页（GlassTopAppBar）/ 管理族（Scaffold 内置）/ View 残留（MainTopBarView，有明确消亡计划）。

落地理由：决策链已在管理族落地并被用户认可为标准；TopBarConfig 是各组件的共同依赖点，单点收敛改动最小；ConfigTopBar 与 GlassTopAppBar 功能重合度极高（壁纸/圆角/溢出菜单），且 H13 crop 遗留差异（ConfigTopBar 忽略 crop）随消灭自然消除。

### Alternatives Considered
| 备选方案 | 否决理由 |
|---------|---------|
| A1：仅改 `TopBarConfig.defaultBackgroundColor` 黑白兜底为 primaryColor | 治标：resolve 兜底被壁纸态/hasCustom 判定共用，直接改默认值会破坏 `hasCustomBackground` 值比较逻辑（恒真陷阱注释 TopBarConfig.kt:312-319），且无法接入沉浸开关分支 |
| A2：22 页 View 宿主一次性全部迁 Compose GlassTopAppBar（4→2） | 单轮回归面过大（22 页含书源编辑/缓存管理等重交互页），且与 master-track 波次计划冲突（页面迁移应随波次逐页进行）；本轮先统一取色 + 声明消亡路线 |
| A3：每页面逐个指定 containerColor | 反模式：30+ 页各自硬编码，下次主题体系变更又要全量返工 |
| A4：AppManagementTopBar 也并入 GlassTopAppBar（4→2） | 管理族顶栏带搜索框内嵌/选择态联动，与 Scaffold 深度耦合；且管理族视觉（48dp 紧凑）是用户认可的标准，不应变 |

### Drawbacks
- **已知缺陷**：MainTopBarView(Mode.SUB) 家族 22 页（含书源编辑、缓存管理等）将从黑白兜底变为主题主色，视觉与用户当前印象的"应用主题页"有变化
- **已知缺陷**：ConfigActivity 各页顶栏高度 56dp→M3 TopAppBar 高度（64dp），设置页顶栏视觉微变；溢出菜单交互保留但实现从私有 AppDropdownMenu 迁移到适配层
- **风险点**：`context.backgroundColor` 在设置全局背景图时返回 TRANSPARENT（MaterialValueHelper.kt），沉浸分支下顶栏可能透出窗口底色
- **风险点**：ConfigTopBar 消灭涉及溢出菜单行为迁移，三点菜单回归需专项验证
- **接受理由**：主色兜底正是管理族标准形态，用户诉求即"跟随主题设置体系"；透明风险与管理族现状一致（同链同险）；组件缩减正是消除"改一处须顾四套"的架构债
- **兜底预案**：真机验证时若沉浸分支出现透明异常，将分支 2 收窄为 `AppConfig.immersiveManageBar && context.backgroundColor != Color.TRANSPARENT`；不可接受时 Mode.SUB 可单点回退（改动隔离在 renderBackgroundLayer 一处）；ConfigTopBar 收敛若溢出菜单回归受阻，备份 bak 可快速还原（实施前备份）

## Requirements

### Requirement: 统一取色决策链
所有子页面顶栏背景色必须经 `TopBarConfig` 统一决策函数产出，禁止组件各自兜底。

#### Scenario: 未配置顶栏包且沉浸开关关闭
- **WHEN** 任一子页面顶栏渲染，无自定义背景色、`immersiveManageBar=false`
- **THEN** 顶栏背景 = `context.primaryColor`（主题主色），前景 = `contrastOn(主色)`

#### Scenario: 沉浸开关开启
- **WHEN** `AppConfig.immersiveManageBar=true` 且无自定义背景色
- **THEN** 顶栏背景 = `context.backgroundColor`（页面底色）

#### Scenario: 顶栏包自定义背景色
- **WHEN** 当前顶栏包配置了非默认背景色（`hasCustomBackground=true`）
- **THEN** 顶栏背景 = 自定义背景色，优先级最高

### Requirement: 设置族顶栏跟随主题
ConfigActivity 全部宿主 Fragment（主题设置/备份恢复/其他设置/AI设置/视频设置/精准管理/封面/欢迎页/发现/订阅源配置）顶栏不再出现夜间纯黑/日间纯白硬编码。

#### Scenario: 夜间模式进入设置页
- **WHEN** 夜间主题下进入"备份与恢复"
- **THEN** 顶栏背景 = 主题主色（非 Color.BLACK），标题/图标为对比色

### Requirement: Mode.SUB 顶栏跟随主题
MainTopBarView Mode.SUB 家族 22 页顶栏背景经统一决策函数；Mode.MAIN 保持现状不受影响。

#### Scenario: 主页与子页互不影响
- **WHEN** 从主页 Tab 切换到书源编辑页（Mode.SUB）再返回
- **THEN** 书源编辑页顶栏走统一决策链，主页顶栏渲染逻辑与改前一致

### Requirement: 组件收敛（4→3）
ConfigTopBar 消灭，ConfigActivity 全部宿主页顶栏改用 GlassTopAppBar；顶栏组件不再存在"同功能双实现"。

#### Scenario: 设置页三点菜单
- **WHEN** 在"备份与恢复"页点击顶栏溢出（三点）菜单
- **THEN** 菜单项与改前一致（MenuAction 分级：alwaysShow 一级直出，其余进溢出），点击行为不变

#### Scenario: ConfigTopBar 定义删除
- **WHEN** 全局搜索 ConfigTopBar
- **THEN** 零定义零调用（Grep 验证）

### Requirement: 壁纸态语义保持
顶栏包配置壁纸时，壁纸显示 + withOpacity(resolveBackgroundColor) 叠加语义不变。

#### Scenario: regular 顶栏包带壁纸
- **WHEN** 顶栏包为 regular 样式且配置了壁纸
- **THEN** 4 套组件均显示壁纸，背景叠加 `withOpacity(自定义/兜底色, wallpaperAlpha)`，与改前一致

### Requirement: 沉浸豁免页不回归
豁免页（ImageCrop/ImageGallery/ImageDetail/VideoPlayer 播放器内/SearchActivity）顶栏视觉保持现状。

#### Scenario: 看图页黑色背景
- **WHEN** 进入 ImageDetailActivity
- **THEN** 黑底沉浸视觉不变（不受统一函数影响）

### Requirement: XML 残留清理
4 处残留死代码顶栏移除（activity_read_record.xml 双顶栏、activity_rule_sub.xml TitleBar、activity_ai_image_provider_edit.xml TitleBar、fragment_explore.xml TitleBar），不得产生运行时回归。

#### Scenario: 阅读记录页单顶栏
- **WHEN** 打开阅读记录页
- **THEN** 仅显示 Compose GlassTopAppBar，XML 残留节点已清除且无视觉变化

## Scenarios（验证总纲）
- L1：编译通过，无残留调试日志
- L2：真机/模拟器逐页验证（日间+夜间 × 默认顶栏包 × 沉浸开关两态）：设置族 10 页 + Mode.SUB 抽查 5 页 + Glass 族抽查 8 页 + 管理族 6 页不回归 + 豁免页 4 页不回归
- L3：切换颜色主题后顶栏实时跟随；顶栏包自定义背景/壁纸优先级正确
