# spec.md — ui-batch-fix-0905

## Intent
修复 4 个用户反馈问题：崩溃弹框误弹回归、视频书源沉浸式左下角缺多线路多集信息、经典发现页三点菜单点击无反应（Bug）+ 全前端死菜单清理、经典订阅头部操作收口。

## Scope

### 做什么
1. 崩溃确认弹框恢复为仅 `LocalConfig.appCrash == true` 时弹出（release 包）。
2. `VideoPlay.initSource` 对无卷书源（volumes 为空、toc 非空）回退包装单线路，使沉浸式左下角线路/集数选择器与详情抽屉对齐订阅源体验。
3. 经典发现页 `menu_group` 弹框 Bug：真机复现 → 定位 → 修复（保留分组快捷过滤功能）。
4. 删除死菜单项：`rss_source_sel.xml` 的 `menu_check_rss_source`；`content_select_action.xml` 的 `menu_search_content/menu_browser/menu_share_str`。
5. 经典订阅头部：仅保留搜索按钮在外；三点菜单新增：阅读记录/星标/刷新/订阅源管理/布局设置/分组管理；删除分组信息列举（`showGroupMenu` 中 `groups.forEach` 段），分组按钮整体移除。

### 不做什么
- 不动现代（modern）订阅形态头部与 `MainTopBarView.setMode()` 可见性集合。
- 不动 Compose 侧设计意图空 lambda（面板阻断穿透、分组头、下载头）。
- 不动书架/阅读记录等已正常页面的头部。
- 不改 CrashHandler 落盘策略主体（仅评估"写盘失败静默吞"是否随本次一并加兜底提示，见 design AD-01）。

## Approach

### Selected Approach
- 问题1：将 `showComposeConfirmDialog` 移回 `if (LocalConfig.appCrash)` 块内（恢复原语义），最小 diff。
- 问题2：数据层回退——`VideoPlay.initSource` 卷章映射块加 else 分支：volumes 为空但 toc 非空时，将全部章节包装为单线路 `RssRoute("线路1")`（镜像 `parseRssRoutes` 扁平回退），UI 层零改动自动生效。
- 问题3：先真机复现定位弹框失败根因（锚点/时机/条件），按根因修复；`menu_group` 功能保留不删除。
- 问题4：仅改 `RssFragment` 经典路径接线：`setActionsVisible` 隐藏星标/刷新、移除 3 个 addActionButton、手动启用 `moreButton` 并用 `ModernActionPopup` 数据驱动 6 项菜单；`showGroupMenu` 删除分组列举段（函数随分组按钮移除而删）。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 问题1：弹框加"今日已提示"去抖标记 | 治标不治本，误弹根源是条件块错位，仍会首次误弹 |
| 问题2：UI 层让选择器回退读 `VideoPlay.episodes` | 需新增 BookChapter→RssEpisode 适配器，破坏 RssEpisode 模型复用，改动面大 |
| 问题3：直接删除 `menu_group` 菜单项 | 分组快捷过滤有实现有价值，删除损失功能；应定性为 Bug 修复 |
| 问题4：在 `MainTopBarView.setMode()` 把 Mode.RSS 加入 moreButton 可见集合 | 会波及现代形态（initModernRssView 未接监听，图标凭空出现且点击无效） |

### Drawbacks
- 问题2 数据回退使"单线路书源"也显示"线路1"选择器（信息略冗余）；接受理由：与订阅源行为一致，用户可感知线路存在；兜底：单集章节（episodes 为空）不显示集数列表（沿用 size>1 判断，仅集数>1 渲染）。
- 问题1 修复后，release 真崩溃时仍可能因写盘静默失败查不到文件（历史独立问题）；兜底：本次顺带给 `saveCrashInfo2File` 失败路径补 AppLog 记录（不弹框），便于后续排查。
- 问题4 收口后高频操作（刷新/星标）多一次点击；接受理由：用户明确要求收口，头部更简洁。

## Requirements

### Requirement: 崩溃弹框仅在真实崩溃后出现
release 包中，仅当发生未捕获异常（`LocalConfig.appCrash == true`）时，MainActivity 才弹出崩溃确认框；无崩溃时任何 MainActivity 创建/重建均不弹。

#### Scenario: 无崩溃正常启动
- **WHEN** release 包冷启动/热重建 MainActivity 且从未发生崩溃
- **THEN** 不出现"检测到阅读发生了崩溃"弹框

#### Scenario: 真实崩溃后启动
- **WHEN** 发生未捕获异常后再次启动
- **THEN** 弹出崩溃确认框一次，处理后不再重复弹出

### Requirement: 视频书源沉浸式左下角展示线路/集数
无卷视频书源进入沉浸式播放时，左下角展示标题+集数横向列表（线路选择器沿用订阅源 size>1 渲染规则）；详情抽屉同步可用；切线路/集数行为与订阅源一致。

#### Scenario: 无卷书源沉浸式播放
- **WHEN** TOC 为扁平章节列表（无卷行）的视频书源以沉浸式布局播放
- **THEN** 左下角显示集数横向列表并可点击切换；线路选择器沿用与订阅源一致的 size>1 渲染规则（单线路不显示线路行，多卷/多线路书源显示）

#### Scenario: 有卷书源不回归
- **WHEN** volumes 非空的书源进入沉浸式
- **THEN** 线路/集数展示与现状一致（映射逻辑不变）

### Requirement: 经典发现页分组菜单可正常弹出
经典发现页工具栏分组按钮点击后正常弹出分组快捷过滤弹窗。

#### Scenario: 点击分组按钮
- **WHEN** 经典发现页点击工具栏分组图标
- **THEN** 弹出分组弹窗，选择分组后列表正确过滤

### Requirement: 死菜单项清理
全前端不存在"有菜单项无处理分支/永不渲染"的死项。

#### Scenario: 死项删除后
- **WHEN** 打开订阅源管理菜单 / 阅读划词菜单
- **THEN** 不再出现点击无反应项，其余功能不受影响

### Requirement: 经典订阅头部收口
经典订阅头部仅保留搜索按钮；三点菜单含：阅读记录/星标/刷新/订阅源管理/布局设置/分组管理；不再列举分组信息。

#### Scenario: 头部外观
- **WHEN** 进入经典订阅页
- **THEN** 头部仅显示标题+搜索+三点按钮，无星标/刷新/阅读记录/分组/设置独立按钮

#### Scenario: 三点菜单操作
- **WHEN** 点击三点按钮
- **THEN** 弹出 6 项菜单，各菜单项行为与收口前对应按钮一致；无分组信息列举项

#### Scenario: 现代形态不回归
- **WHEN** 切换到 modern 订阅形态
- **THEN** modern 头部渲染与现状完全一致
