# Tasks：视频播放器双布局模式

> 状态标记：⚠️ = 代码完成（L1/L2）｜ ✅ = 场景验证通过（L3）｜ 遇到问题记录 AOAdapt 日志
> 红队基线：R1-R3 发现（4P0+12P1+7P2）已全量转化为任务项（对应括号标注）

## 1. 准备工作

- [ ] 1.1 确认需求范围：对照 spec.md Scope 与用户原始需求逐条核对，确认禁改清单（SniffEngine/VideoPlaybackPipeline/VideoFragment 手势/VideoPagerAdapter）
- [ ] 1.2 阅读源码：`VideoPlayerActivity.kt` 四分发点现状（onCreate/initFromIntent 两分支/onNewIntent）、`setupPlayerView` 复活清单、`VideoPlay.kt` playerType 容错先例
- [ ] 1.3 协调确认：检查 `video-booksource-align-rss` 当前进度，确认传统布局接线点与其单页化模型兼容（1 影片页语义）
- [ ] 1.4 【P0-并行协调】基准快照确认：align-rss 已收口提交远端；`startPlay/playRssEpisode/startPlayBookChapter` 已为 Pipeline 委托；UP_VIDEO_INFO legacy 分支存活；未收口则本任务阻塞等待

## 2. 配置层

- [ ] 2.1 `VideoPlay.kt` 新增 `layoutMode`（Int，默认 0=沉浸式，1=传统；getter 异常值回落 0，参照 playerType 先例）【串行约束：排在 align-rss 队列后】
- [ ] 2.2 验证：编译通过 + 默认值行为与现状一致（未配置时走沉浸式路径）+ 异常值（2/-1）回落 0

## 3. 布局分发与传统布局骨架复活

- [ ] 3.1 D1/D2：onCreate 与 `initFromIntent` 新会话分支按 `layoutMode` 分发，抽取 `setupImmersiveMode()`/`setupLegacyMode()` 私有方法分区（P1-R2-11）
- [ ] 3.2 K2 播放器槽位复活：`setupLegacyMode()` 调用 `setupPlayerView()`（16:9 基准 + onPrepared 比例校准 + 全屏按钮 + 返回监听），验证其当前零调用状态后纳入接线（P1-F4/R2-1）
- [ ] 3.3 K3 起播接线：`setupLegacyMode()` 显式调 `VideoPlay.startPlay(binding.playerView)`，不依赖 Fragment.activatePlayer（P1-F3）
- [ ] 3.4 K1 顶栏提升：`composeTopBar` 提升到根 FrameLayout（结构级改动，AD-10），验证沉浸式路径顶栏行为零变化
- [ ] 3.5 K7 信息区双源绑定 `bindLegacyInfo()`：书源分支（复用 showCover/showBook/showBookIntro）+ 订阅源分支（description/image/duration 新写）+ 缺失降级（区块隐藏），三分支独立验证（P1-F6）；注意 rssEpisode.cover/duration 为预留字段恒空——cover 回退 rssArticle.image、duration=0 隐藏时长
- [ ] 3.6 K4 手势验证：GSY 原生 + VideoPlayer 内建（单击显隐/双击暂停/长按倍速/左右 seek）在传统布局实际可用；seekSensitivity 不生效差异记录在案（P1-F5/AD-07）
- [ ] 3.7 K5/K6 跨影片接线：末集 onAutoComplete 经 `setVideoAllCallBack` 接线自动切下一部（API 对齐 align-rss 收口后形态）+ 信息区「下一部」入口（队列耗尽隐藏）（P0-R2-6/AD-09）
- [ ] 3.8 D4 onNewIntent：legacy 拆卸分支（playerView.release）+ `backFromWindowFull` GSY 全屏窗口复位（P1-R2-11）
- [ ] 3.9 D3 悬浮窗/通知恢复：按 layoutMode 分发，legacy 分支复用 savePlayState→clonePlayState→setSurfaceToPlay→startAfterPrepared 链（P1-R2-2）
- [ ] 3.10 K8 存量触点回归：upView/upEpisodesView/upVolumesView 在 legacy 模式下真实生效验证（P2-F7）
- [ ] 3.11 编译验证 + L2 真机：传统布局下书源视频播放/选集/线路/全屏进出/返回键逐项验证

## 4. 设置中心化

- [ ] 4.1 `VideoSettingsPanelContent.kt` 新增 `host: PanelHost = PLAYER_PAGE` 默认参数（现有两调用点零破坏），新增"布局模式"分区（P0-R3-5 统一口径：两宿主均有布局模式入口）
- [ ] 4.2 按宿主裁剪：严格按 spec R6 归属表执行——PLAYER_PAGE 保留（布局切换/画面比例/音轨/快进快退/信息复制/调试/画质即时调节/功能菜单）；GLOBAL 承载全部持久偏好（含全屏底部进度条孤儿项归位）（P1-R3-3）
- [ ] 4.3 【P0-路线 B】新增 `VideoPlayerConfigFragment.kt`：普通 Fragment + ComposeView + LegadoTheme + `VideoSettingsPanelContent(PanelHost.GLOBAL)`，挂 ConfigActivity.replaceFragment；自实现 onResume 重读 + targetKey 定位；**禁止继承 ComposeSettingFragment**（P0-R3-1/AD-08）
- [ ] 4.4 UI 门禁：`how-to.md` 先读 + architecture.md Checklist 9 项逐项勾选 + `rememberAppSettingPalette()` 取色 + 根背景 palette.settings.page + 硬编码色 Grep 自查 + migration-registry.md 登记行（P1-R3-4）
- [ ] 4.5 `ConfigTag.kt` + `ConfigActivity.kt` 注册 `VIDEO_PLAYER` 分发；`MySettingsData.kt` 新增入口行（"工具"分组）+ 路由分支（P1-R3-6）
- [ ] 4.6 设置搜索：`buildSettingsSubSearchItems` 硬编码全局页关键条目（layoutMode/playerType/autoPlay/videoCache/videoCacheSize/缓冲策略，ownerConfigTag=VIDEO_PLAYER）（P1-R3-2）
- [ ] 4.7 入口归一：`OtherConfigFragment` 弹框入口改跳转 ConfigActivity(VIDEO_PLAYER)；`pref_config_other.xml` 同步防死条目；`SettingsDialog.kt` 收编为仅 PLAYER_PAGE 宿主（P1-R3-6/7）
- [ ] 4.8 编译验证 + L2 真机：全局页配置读写生效、播放页面板裁剪后无残留全局项、OtherConfig 跳转正确、搜索页可搜到视频设置条目、两处布局模式选择同源一致

## 5. 布局切换生效机制

- [ ] 5.1 全局页修改 `layoutMode` → 持久化 → 下次进入播放页生效；Activity 仅在 onCreate/onNewIntent/面板切换时读取
- [ ] 5.2 【P1-R2-3 时序契约】播放页内切换六步：直读 videoManager.currentPosition → 互斥标记短路 saveRead/定时保存 → 主线程串行释放 → 新容器 setUp → seek 续播（PlayHistoryStore 权威+双恢复点去重）→ 清标记（AD-05）
- [ ] 5.3 L2 真机：播放页内双向切换（沉浸↔传统）续播位置误差≤5 秒、无进度串写、无崩溃

## 6. 场景验证（L3）

- [ ] 6.1 场景：默认未配置 → 沉浸式布局零回归（书架/搜索/订阅三入口 + 上滑切换 + 预加载 + PiP + 悬浮窗 + 顶栏菜单）
- [ ] 6.2 场景：传统布局完整链路（书源多线路多集 + 订阅源多集）信息区渲染正确、当前集定位高亮
- [ ] 6.3 场景：简介/封面缺失时区块优雅隐藏（书源/订阅源两侧）
- [ ] 6.4 场景：传统布局横屏全屏进出 → 信息区可见性/滚动位置恢复；GSY 全屏窗口无残留
- [ ] 6.5 场景：跨影片——末集播完自动切下一部 + 「下一部」入口点击切换 + 队列耗尽隐藏
- [ ] 6.6 场景：悬浮窗/通知返回 → 布局不漂移（D3）；onNewIntent 新 Intent → 布局一致（D4）
- [ ] 6.7 场景：设置分工核对——播放页面板无持久偏好残留、全局页覆盖 spec R6 全部条目、搜索可达

## 7. 收尾与文档同步

- [ ] 7.1 `updateLog.md` 基于 git diff 更新（编译前完成，面向用户语言）
- [ ] 7.2 Grep 检查无残留调试日志（`android.util.Log.d|e` 自定义 tag）
- [ ] 7.3 文档同步：`docs/project-flow/` 相关模块文档（对照 AGENTS.md 步骤 8 映射表：quick-reference 配置说明/task-navigation 模块锚点）+ ui-standards（components.md/color.md 如涉及）+ migration-registry 状态回写 + `docs/INDEX.md` 状态流转
- [ ] 7.4 经验沉淀：传统布局死代码复活清单、四分发点模式沉淀到对应子规范/troubleshooting
- [ ] 7.5 停止 Gradle/Kotlin daemon（构建后清场门禁）

## AOAdapt 日志

- [ ] 2026-09-03 红队 R1-R3（3 子代理并行，源码级核验）
  - Action: 三路红队对抗审查（R1 可行性+并行冲突 / R2 交互完整性+稳定性 11 项 / R3 设置中心化边界 7 项）
  - Observation: 4P0+12P1+7P2——P0：①并行冲突（设计锚定未提交快照且起播入口正被 align-rss 重写）②传统布局跨影片队列语义空洞（信息孤岛）③全局页基类路线错误（ComposeSettingFragment prefs 硬绑默认文件）④文档自相矛盾（布局模式分区归属 vs R6 场景）；P1 关键：legacy 为死代码路径（setupPlayerView 零调用/顶栏被困 viewPagerContainer 内/onNewIntent 链 ViewPager 专用/悬浮窗恢复硬编码回沉浸式）
  - Adapt: R4 整改落盘——新增 AD-07~AD-10、四分发点模型、骨架复活清单 K1-K8、路线 B 全局页、时序契约六步、并行协调约束、spec R5/R11 新增与 R3/R4/R6/R10 修正、tasks 扩至 7 章 40 项
- [ ] R5 终审：**GO-WITH-NOTES**——23 项发现 22 ✅闭环 + 1 ⚠️（三宿主措辞残留）；源码锚点 20 项抽查全部吻合；实施前修复 N1（措辞统一）+ N2（订阅源预留字段注记）已完成；N3-N11 文档微调随 7.3 文档同步顺带处理
