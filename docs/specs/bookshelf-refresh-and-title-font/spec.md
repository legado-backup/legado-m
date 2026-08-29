# Spec：书架下拉刷新转圈不消失 + 顶栏标题字号不统一修复

## Intent

消除书架页两个 UI 缺陷：① 下拉刷新转圈指示器不消失（复位机制与真实刷新完成脱钩 + 生命周期冻结）；② 书架顶栏标题字号 24sp 与其他主 Tab（20sp）不一致且为硬编码。使书架刷新行为与订阅页（事件驱动复位）对齐，标题排版与全 App 统一。

## Scope

### 包含
- `MainViewModel`：暴露 upToc 更新队列空闲状态（upTocJob 排空可观测）
- `BookshelfFragment1` / `BookshelfFragment2`：刷新复位逻辑改为事件驱动 + 兜底超时，协程迁移 `viewLifecycleOwner.lifecycleScope`，单一 Job 管理
- `MainTopBarView`：去除 `Mode.BOOKSHELF` 的 24sp 特判，统一 20sp
- `ConfigTopBar`（ConfigActivity 内，备份与恢复/主题/其他等全部设置子页顶栏）：字重 `SemiBold` 硬编码覆写去除，回归 `titleLarge`（Medium）
- `AppManagementScaffold`（书源/订阅源/替换规则/订阅规则/书架分组 5 页顶栏）：标题 19sp+SemiBold 归位 20sp+Medium（titleLarge 基线）
- `GlassTopAppBar` / `ConfigTopBar` 右侧图标按钮：图标绘制尺寸 24dp → 20dp（用户裁决"统一 20dp"口径，与主 Tab/管理页观感对齐）

### 不包含
- 订阅页/其他页面刷新逻辑（已是事件驱动，无此问题）
- material3 BOM 版本升级（竞态先观察修复效果，不升级验证版本）
- `TopBarConfig` 增加字号字段的主题化改造（标题字号全 App 统一后无差异化需求，见 Alternatives）
- SwipeRefreshLayout 体系改造（书架已是 Compose `PullToRefreshBox` 受控模式）
- 阅读器/视频播放器顶栏（历史裁决 T7 豁免）；欢迎页 49sp 品牌大字（非顶栏）；弹框/卡片标题 SemiBold（非顶栏层级）
- 主 Tab `MainTopBarView` 图标按钮 34dp 容器 + ~18dp 图标（Archive 对齐既定值 `bookshelf_action_button_size`，豁免保留）
- 图标"粗细"统一（自绘 ic_*.xml 描边 vs M3 Icons 描边）：图标资产层专项，登记 issue-list 独立处理

## Approach

### Selected Approach

**问题1（转圈不消失）—— 事件驱动复位 + 生命周期安全 + 兜底超时：**
1. `MainViewModel` 增加队列空闲可观测状态：`upTocJob` 置 null 处（队列排空点）同步更新 `MutableStateFlow(true)`，`upToc()` 入队时置 false
2. `BookshelfFragment1/2` 的 `onRefresh`：`refreshing = true` 后，在 `viewLifecycleOwner.lifecycleScope` 启动复位协程——`upTocIdle.first { it }` 带超时兜底（约 5s）后 `refreshing = false`；协程用单一 Job 引用管理（新刷新先 cancel 旧复位协程）
3. 该方案使转圈寿命 = 真实刷新寿命（且不短于触感反馈），同时消除页面销毁导致的冻结

**问题2（字号不统一）—— 全顶栏族排版归位到 titleLarge 基线（20sp/Medium）：**

全仓普查（用户质疑驱动两轮扩查）发现三处漂移，全部归位：

| 顶栏 | 现状 | 修复 |
|------|------|------|
| `MainTopBarView.kt:187`（书架特判） | 24sp | `titleText.textSize = 20f` 去特判 |
| `ConfigTopBar`（ConfigActivity.kt:244-253） | 20sp + **SemiBold** 覆写 | 删 `fontSize=`/`fontWeight=` 覆写改 `style = MaterialTheme.typography.titleLarge`（保留 palette 字体族） |
| `AppManagementScaffold.kt:188-199`（5 管理页） | **19sp**（subtitleLargeX）+ **SemiBold** | 同上归位 titleLarge（保留 fontFamily） |

基线依据：`LegadoTypography.titleLarge = 20sp/Medium`（LegadoTheme.kt:31 注释"对齐 View ToolbarTitle 20sp，主题统一 AD-19"），GlassTopAppBar 与 View TitleBar 均已在该基线，本次是把三处漂移拉回既有基线。

**问题3（右侧图标按钮大小不一）—— Compose 顶栏图标统一 20dp（用户裁决口径）：**

普查实锤四层四规格：

| 顶栏 | 行高 | 按钮容器 | 图标绘制 | 图标资产 |
|------|------|---------|---------|---------|
| `MainTopBarView`（主 Tab） | — | 34dp | ~18dp | 自绘 ic_*.xml |
| `GlassTopAppBar`（子页） | 64dp（M3 默认） | 48dp | 24dp | 调用方传入 |
| `ConfigTopBar`（设置子页） | 56dp | 48dp | 24dp | M3 imageVector |
| `AppManagementScaffold`（5 管理页） | 48dp | 36dp | 20dp | 自绘 ic_*.xml |

修复：`GlassTopAppBar` 与 `ConfigTopBar` 的 action 图标加 `Modifier.size(20.dp)`（24→20dp，与主 Tab ~18dp/管理页 20dp 观感拉齐）；`AppManagementScaffold` 20dp 保持；主 Tab 34dp 容器为 Archive 对齐既定值豁免。"粗细"（图标资产描边）登记独立专项不在本任务实施。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 保持 `delay(1000)` 盲定时，仅修 scope + Job 管理 | 只治"冻结 true"标症，刷新真实完成前转圈提前消失的脱钩问题仍在；修复不彻底 |
| 观察 `EventBus.UP_BOOKSHELF` 逐本事件计数判断完成 | 事件按批次 post 且部分书跳过更新不发事件，计数不可靠；队列空闲状态（upTocJob==null）是权威信号 |
| 升级 compose BOM 修复 material3 1.3.2 指示器竞态 | 版本升级影响面全 App，且需回归验证；竞态是叠加因素非主因，先修主因观察真机表现 |
| `TopBarConfig.Config` 新增字号字段纳入主题体系 | 主题体系职责为配色/壁纸/形态（现状字段无一涉及排版）；字号统一后全 App 无差异化诉求，加字段扩大配置面且无消费方，属过度设计 |
| 只修字号不动字重（保留 SemiBold） | 用户实感"备份与恢复等页字体大"主因即 SemiBold(600) 比 Medium(500) 粗壮；只修字号治不了视觉不统一，半途而废 |
| AppManagementScaffold 保持 19sp/SemiBold 作为管理页差异化风格 | 无出处的孤例漂移（GlassTopAppBar/ConfigTopBar/View TitleBar 均在 20sp/Medium 基线）；差异化无设计文档支撑，统一优先 |
| 图标统一 24dp（M3 基线） | 管理页 48dp 行高放不下 48dp 容器需再调行高，连锁改动；且主 Tab ~18dp 观感已确立，20dp 与全族最接近 |
| 图标粗细一并统一（全量替换 ic_*.xml 描边） | 影响 App 全部图标资产，工作量与回归面是独立专项量级；本任务先统一尺寸，粗细登记 issue-list |
| 改用 Compose `TopAppBar` 渲染主 Tab 标题 | 全部主 Tab 均为 `MainTopBarView` 自绘顶栏（refreshMainTopBars 统一刷新），推翻重来改动面巨大，与本次 bugfix 定位不符 |

### Drawbacks

- 事件驱动复位后，若某本书目录更新异常缓慢，转圈会持续较久（原 1 秒即消失"假装刷新完"）；接受理由：真实反馈优于虚假反馈，且 5s 兜底保证不会永久滞留
- 兜底超时（5s）内若刷新未完成转圈仍会消失，与原行为一致但更久；接受理由：队列空闲信号为主路径，兜底仅防信号丢失
- 书架标题从 24sp 缩至 20sp，习惯大标题的用户感知"字变小"；接受理由：跨页一致是用户明确诉求，24sp 是无出处的孤例硬编码

### Prior Art

- `ExploreFragment`（订阅页）：SwipeRefreshLayout 事件驱动复位，11 处成功/失败/取消分支显式 `isRefreshing = false`，本设计对其语义对齐
- 原版 legado 书架刷新为 View 体系 SwipeRefreshLayout + 定时复位，本项目 Compose 迁移后引入受控 `PullToRefreshBox` 才暴露冻结问题

## Requirements

### R1 刷新复位正确性
- 书架下拉刷新后，转圈指示器必须在刷新完成（upToc 队列排空）后收回，兜底不超过 5s
- 页面销毁/重建（ViewPager 回收、Activity 重建）期间不得出现转圈永久滞留
- 快速连续下拉刷新不得产生复位协程竞态

### R2 标题字号统一（全顶栏族 20sp/Medium 基线）
- 书架顶栏标题字号与订阅/我的/阅读记录/发现页一致（20sp）
- 设置子页顶栏（ConfigTopBar）标题字重回归 Medium（去 SemiBold 覆写），字号维持 20sp
- 管理页顶栏（AppManagementScaffold，5 页）标题字号 19sp→20sp、字重 SemiBold→Medium
- 字号/字重改动不得影响各顶栏字体族（palette titleFontFamily）与配色链路

### R4 右侧图标按钮尺寸统一
- GlassTopAppBar / ConfigTopBar 的 action 图标绘制尺寸统一 20dp（24→20dp）
- AppManagementScaffold 保持 20dp；主 Tab `bookshelf_action_button_size=34dp` 容器（图标 ~18dp）豁免保留
- 图标按钮点击热区（IconButton 容器）不得因图标缩小而失效
- 图标"粗细"（资产描边）登记 issue-list 独立专项，不在本任务范围

### R3 兼容性
- style1（列表）与 style2（文件夹）两个书架形态均需修复
- 不得引入新依赖、不得升级锁定版本

## Scenarios

### S1 正常刷新
GIVEN 书架页有书目
WHEN 用户下拉刷新且目录更新在 5s 内完成
THEN 转圈在队列排空后收回，耗时与真实刷新一致

### S2 刷新未完成超 5s
GIVEN 书架下拉刷新且部分书目更新缓慢超过 5s
WHEN 兜底超时触发
THEN 转圈收回，刷新任务继续在后台执行（不被取消）

### S3 刷新中页面销毁
GIVEN 下拉刷新进行中，用户快速切换 Tab 导致 Fragment 视图回收/销毁
WHEN 返回书架页
THEN 无转圈滞留（协程随 viewLifecycle 取消，状态不冻结展示）

### S4 连续快速下拉
GIVEN 用户连续多次快速下拉刷新
WHEN 第二次下拉触发时第一次复位协程未结束
THEN 旧复位协程被取消，仅保留最新一次刷新的复位逻辑，无竞态卡死

### S5 标题字号
GIVEN 依次切换 书架/订阅/我的 三个主 Tab
WHEN 观察左上角标题
THEN 三处字号视觉一致（20sp）

### S6 设置子页与管理页标题
GIVEN 依次打开 备份与恢复（设置子页）和 书源管理（管理页）
WHEN 对比其顶栏标题与主 Tab 标题
THEN 三处字号一致（20sp）、字重一致（Medium），仅字体族/配色随主题差异

### S7 管理页顶栏回归
GIVEN 打开 书源管理/订阅源管理/替换规则/订阅规则/书架分组 5 页
WHEN 观察顶栏标题
THEN 均为 20sp/Medium，标题随主题字体族，布局无挤压变形

### S8 右侧图标按钮观感
GIVEN 依次打开 主 Tab、一般子页（GlassTopAppBar）、备份与恢复（ConfigTopBar）、书源管理（AppManagementScaffold）
WHEN 对比各顶栏右侧图标按钮
THEN 图标绘制尺寸观感一致（20dp 档，主 Tab 豁免 ~18dp），点击热区正常
