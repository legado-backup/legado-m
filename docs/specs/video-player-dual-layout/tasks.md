# Tasks：视频播放器双布局模式

> 状态标记：⚠️ = 代码完成（L1/L2）｜ ✅ = 场景验证通过（L3）｜ 遇到问题记录 AOAdapt 日志
> 红队基线：R1-R3 发现（4P0+12P1+7P2）已全量转化为任务项（对应括号标注）

## 1. 准备工作

- [x] 1.1 确认需求范围：对照 spec.md Scope 与用户原始需求逐条核对，确认禁改清单（SniffEngine/VideoPlaybackPipeline/VideoFragment 手势/VideoPagerAdapter）（⚠️）
- [x] 1.2 阅读源码：四分发点/setupPlayerView 复活清单/playerType 容错先例/VideoFragment.activatePlayer 分支/clonePlayState 链全部核验（⚠️）
- [x] 1.3 协调确认：align-rss 单页化已在工作树（Pipeline 存在），传统布局接线点与其兼容（1 影片页语义、复用 switchToBookFromList/VIDEO_BOOK_UNIT_SWITCHED 链）（⚠️）
- [x] 1.4 【P0-并行协调】基准快照裁决（Goal 模式自主决策）：当前快照实施+纯增量+独立资源文件规避 strings.xml 争用，详见 AOAdapt（⚠️）

## 2. 配置层

- [x] 2.1 `VideoPlay.kt` 新增 `layoutMode`（getter 异常值回落 0）+ `layoutSwitchInProgress` 切换窗口标记（✅ 编译通过）
- [x] 2.2 验证：编译通过（L1）；默认值行为与现状一致（未配置走沉浸式路径）待 L2 真机确认

## 3. 布局分发与传统布局骨架复活

- [x] 3.1 D1/D2：onCreate 初值 + `initFromIntent` 新会话分支按 `layoutMode` 分发，`dispatchLayoutMode()` 统一入口（⚠️ 编译通过，L2 待验）
- [x] 3.2 K2：`setupLegacyMode()` 调用 `setupPlayerView()` 复活（16:9 + onPrepared 校准 + 全屏按钮 + 返回监听）（⚠️）
- [x] 3.3 K3 起播接线：`startLegacyPlayback()` 镜像 activatePlayer 三分支（书源/文章/集数）+ 悬浮窗 clonePlayState 链（⚠️）
- [x] 3.4 K1 顶栏提升：根布局改垂直 LinearLayout，composeTopBar 两布局共用；全屏 gone/visible 行为与原实现等价（⚠️）
- [x] 3.5 K7 信息区双源绑定：`bindLegacyInfo()`（书源复用 showBook/showToc/showVolumes + 订阅源 showRssLegacyInfo 新写 + 缺失降级）+ rssEpisode 预留字段回退规则（⚠️）
- [x] 3.6 K4 手势：GSY 原生 + VideoPlayer 内建随 setupPlayerView 复活；seekSensitivity 差异已在 spec Drawbacks 声明（⚠️ L2 待验）
- [x] 3.7 K5/K6 跨影片接线：setupPlayerView 增加 onAutoComplete（书源 upDurIndex(+1) 末集自动切下一影片/订阅源顺延下一集）+ tv_next_film「下一部」入口（⚠️）
- [x] 3.8 D4 onNewIntent：legacy 拆卸分支（backFromFull + release）+ 防全屏窗口残留（⚠️）
- [x] 3.9 D3 悬浮窗恢复：dispatchLayoutMode 分发 + startLegacyPlayback clonePlayState 链（⚠️）
- [x] 3.10 K8 存量触点：upView/upEpisodesView/upVolumesView 保持原语义，VIDEO_BOOK_UNIT_SWITCHED 增加 legacy 分支刷新信息区（⚠️）
- [x] 3.11 编译验证：compileAppDebugKotlin BUILD SUCCESSFUL（✅ L1）；L2 真机逐项验证待装机执行

## 4. 设置中心化

- [x] 4.1 `VideoSettingsPanelContent` 新增 `host: PanelHost = PLAYER_PAGE`（现有调用点零破坏）+ "布局模式"分区（双宿主可见）+ `expand` 参数（⚠️）
- [x] 4.2 按宿主裁剪：PLAYER_PAGE=布局切换/播放控制/播放信息/功能菜单/画质增强；GLOBAL=布局模式默认值/播放设置/播放器优化/画质增强（按 spec R6 归属表）（⚠️）
- [x] 4.3 【P0-路线 B】`VideoPlayerConfigFragment.kt`：普通 Fragment + ComposeView + LegadoTheme + palette.page 根背景 + PanelHost.GLOBAL + expand 填满 + onResume 重建读取（✅ 编译通过，未继承 ComposeSettingFragment）
- [x] 4.4 UI 门禁：LegadoTheme + rememberAppSettingPalette().page 根背景 + 面板组件内部取色同源（rememberAppDialogStyle），无硬编码色；migration-registry 登记随 7.3 执行（⚠️）
- [x] 4.5 `ConfigTag.VIDEO_PLAYER` + `ConfigActivity` 分发分支 + `MySettingsData` "工具"组入口行 + 路由分支（⚠️）
- [x] 4.6 设置搜索：`buildSettingsSubSearchItems` 硬编码 6 条全局页条目（layoutMode/playerType/autoPlay/cachePlay/videoCacheSize/playerBufferStrategy，ownerConfigTag=VIDEO_PLAYER）（⚠️）
- [x] 4.7 入口归一：OtherConfigFragment 改跳转 ConfigActivity(VIDEO_PLAYER)（SettingsDialog import 清理）；pref_config_other.xml 移除 videoSetting 条目防死条目；SettingsDialog 收编仅播放页宿主 + onLayoutModeSelected 回调（⚠️）
- [x] 4.8 编译验证通过（✅ L1）；L2 真机（全局页读写/面板裁剪/跳转/搜索/双处布局选择同源）待装机执行

## 5. 布局切换生效机制

- [x] 5.1 全局页修改 `layoutMode` → 持久化 → 下次进入生效（分发点读单源）（⚠️）
- [x] 5.2 【时序契约】`switchLayoutMode()` 六步：直读位置 → layoutSwitchInProgress 短路 → 串行释放 → 新容器挂载起播 → PlayHistoryStore 权威恢复（force+positionOverride 精确落库）→ 清标记（⚠️）
- [x] 5.3 编译验证通过（✅ L1）；L2 真机双向切换续播误差≤5s 验证待装机执行

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

## 8. W2 修复批次（2026-09-04 用户真机验收反馈，见 spec.md W2 增补）

- [x] B1 全屏按钮：setupPlayerView 内 fullscreen 常显+移到倍速前（仅传统布局实例）；toggleFullScreen legacy 分支补顶栏/信息区显隐（✅ L2：点击倍速位置命中倍速弹窗=移位生效证据；显隐控制栏节点 uiautomator 时序窗口未抓到，代码链完整）
- [x] B2 功能按钮区：legacy_actions（下载/收藏/悬浮窗/设置）复用沉浸式同链（Download.start/onFragmentStarClicked/startFloatingWindow/VideoSettingsPanel BottomSheet）+ 收藏图标随 rssStar 同步（✅ L2 dump：四按钮全部渲染）
- [x] B3 页面平铺去二级页：移除 iv_chapter 二级目录页入口；信息区重排；「线路」「选集」区块标题；显隐联动各分支（✅ L2 dump+截图：hhyun/hhm3u8 线路 chips+全集完结选集平铺）
- [x] B4 命名：video_layout_mode_immersive 改"沉浸式"（✅）
- [x] B5 订阅源列表信息自动对接：showRssLegacyInfo 增强（title/description→content 去标签/计数行/封面链）+ 单URL 优雅降级（✅ 编译通过；书源路径截图确认封面海报+名称渲染）
- [x] W2 编译验证：assembleAppDebug BUILD SUCCESSFUL（3.26.090401，经历 3 轮修复：ic_picture_in_picture 资源缺失→ic_screen；ViewGroup 未 import；install Success + 启动 0 FATAL）
- [x] W2-L2：「下一部」语义修正（VideoPlaylistHolder.neighborOf 队列判定，书架直进无队列=正确隐藏）；commit 744ecf2d1 已推 origin/master

## 9. W3 修复批次（2026-09-04 用户第二轮真机反馈：只修复+编译+打测试包）

- [x] ①订阅源无「下一部」：switchLegacyFilm 接入订阅源文章列表（switchToArticle）+ bindLegacyInfo 同步刷新（✅）
- [x] ②无「上一部」：新增 tv_prev_film（◀ 上一部）+ 对称逻辑（✅）
- [x] ③全屏返回信息区丢失：toggleFullScreen 退出分支统一恢复 data+legacyActions（根因=原 book 分支才恢复）（✅）
- [x] ④订阅源图片未带：showRssLegacyInfo article 兜底链补 rssStar/rssRecord.toRssArticle()（✅）
- [x] W3 编译+打包：legado_miss_app_3.26.090406.apk（✅ 用户要求只修复+编译，L2 留用户验）

## 10. W3b 修复批次（2026-09-04 用户验收反馈：按钮不生效/图片思路校正）

- [x] ①按钮不生效根因：a) W3 部分修改被并行会话回写还原（setupLegacyMode 仍是旧绑定）b) 信息区/按钮依赖 bindLegacyInfo 一次性调用，而订阅源数据异步分阶段到达 → 事件挂钩修复：VIDEO_SUB_TITLE legacy 分支 + UP_VIDEO_INFO legacy 分支尾部挂 showRssLegacyInfo()+upNextFilmVisible()（✅）
- [x] ②命中分析：上一部/下一部并入功能按钮行（action_prev/action_next 与下载按钮同构，ic_skip_previous/ic_skip_next），tv_prev_film/tv_next_film 移除（✅）
- [x] ③「上一部/下一部」= 沉浸式上滑/下滑同链确认：switchLegacyFilm 订阅源文章模式走 switchToArticle（与沉浸式翻页同一 API）（✅ 日志实锤 offset=1→switchToArticle index=1→标题切换）
- [x] ④临时诊断日志移除（✅ Grep 0 残留）
- [x] W3b 验证：模拟器装机实测——第1篇→点下一部→标题切"后羿射日"+「◀ 上一部」出现；0 FATAL；最终包 legado_miss_app_3.26.090407.apk（✅）

## AOAdapt 日志（续）

- [x] 2026-09-03 红队 R1-R3（3 子代理并行，源码级核验）
  - Action: 三路红队对抗审查（R1 可行性+并行冲突 / R2 交互完整性+稳定性 11 项 / R3 设置中心化边界 7 项）
  - Observation: 4P0+12P1+7P2——P0：①并行冲突（设计锚定未提交快照且起播入口正被 align-rss 重写）②传统布局跨影片队列语义空洞（信息孤岛）③全局页基类路线错误（ComposeSettingFragment prefs 硬绑默认文件）④文档自相矛盾（布局模式分区归属 vs R6 场景）；P1 关键：legacy 为死代码路径（setupPlayerView 零调用/顶栏被困 viewPagerContainer 内/onNewIntent 链 ViewPager 专用/悬浮窗恢复硬编码回沉浸式）
  - Adapt: R4 整改落盘——新增 AD-07~AD-10、四分发点模型、骨架复活清单 K1-K8、路线 B 全局页、时序契约六步、并行协调约束、spec R5/R11 新增与 R3/R4/R6/R10 修正、tasks 扩至 7 章 40 项
- [x] R5 终审：**GO-WITH-NOTES**——23 项发现 22 ✅闭环 + 1 ⚠️（三宿主措辞残留）；源码锚点 20 项抽查全部吻合；实施前修复 N1（措辞统一）+ N2（订阅源预留字段注记）已完成；N3-N11 文档微调随 7.3 文档同步顺带处理
- [x] 2026-09-03 实施·基准快照裁决（tasks 1.4，Goal 模式自主决策）
  - Action: git status/log 核验——align-rss 未收口（Pipeline 已在工作树但任务未闭环），工作区含其他轨道大量未提交改动
  - Observation: 用户 /goal 指令"开始实施直到完成"，无法等待 align-rss 收口
  - Adapt: 决策=在当前快照（HEAD c47ffc993+工作区）实施：①纯增量改动（新增方法/新文件，不重写 align-rss 正在重写的 startPlay 三入口本体）②目标文件中仅 ConfigActivity.kt/strings.xml 被其他轨道占用——strings.xml 用独立资源文件 strings_video_dual_layout.xml 规避，ConfigActivity.kt 读后精确增量 Edit ③函数名锚点不依赖行号
- [x] 2026-09-03 实施·编译错误两连（第一轮 compileAppDebugKotlin）
  - Action: 首次编译验证
  - Observation: ①MySettingsSubSearchItem.summary 非空类型不可传 null（5 处）②VideoPlay.switchingInProgress 带 private set（AD-06 既有守卫）不可从 Activity 写入
  - Adapt: ①summary 改空串 ②不动既有守卫，新增专用标记 VideoPlay.layoutSwitchInProgress（public，@Volatile），savePlayHistory 短路条件扩展为二者任一，职责分离
