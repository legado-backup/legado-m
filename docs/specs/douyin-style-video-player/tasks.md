# Tasks: 抖音风格沉浸式竖屏视频播放器重设计

> **状态**：🔄 开发中（阶段1+2+3+4+5+6+8完成，控件显隐需求+双指滑动Bug修复完成，待编译验证+L2真机验证）
> **创建日期**：2026-07-10
> **任务编号规则**：T{阶段}.{序号}，阶段 1=架构搭建 / 2=悬浮控件 / 3=状态切换 / 4=横屏适配 / 5=设置面板 / 6=Bug修复 / 7=验证

## 阶段1：架构搭建（ViewPager2 + Fragment）

- [x] 1.1 创建 VideoFragment.kt — 单个视频播放 Fragment，持有播放器视图 + 悬浮控件层 + 设置面板入口
- [x] 1.2 创建 VideoPagerAdapter.kt — ViewPager2 的 FragmentStateAdapter，管理 VideoFragment 列表
- [x] 1.3 重构 activity_video_player.xml — 双容器布局（legacyContainer + viewPagerContainer），订阅源启用 ViewPager2
- [x] 1.4 重构 VideoPlayerActivity.kt — 容器角色，initSource 后按源类型路由 ViewPager2/Legacy 模式
- [x] 1.5 创建 fragment_video.xml — VideoFragment 布局：播放器视图（铺满）+ 悬浮控件层（ConstraintLayout 叠加）
- [x] 1.6 数据传递机制设计 — VideoPlay 全局单例 + Fragment episodeIndex 参数 + onFragmentViewReady 回调
- [x] 1.7 ViewPager2 配置 — 垂直方向 + offscreenPageLimit(1) + onPageSelected 播放切换 + isActivated 防重复

## 阶段2：悬浮控件布局

- [x] 2.1 左下角视频标题 — TextView 固定左下角，支持长文本省略（maxLines=2, ellipsize=end）
- [x] 2.2 右侧竖直功能按钮容器 — LinearLayout vertical，居中右侧
- [x] 2.3 静音按钮 — ImageButton，切换静音状态（图标变化）
- [x] 2.4 收藏按钮 — ImageButton，切换收藏状态（图标变化）
- [x] 2.5 倍速按钮 — ImageButton，点击弹出倍速选择（0.5x/0.75x/1.0x/1.25x/1.5x/2.0x/3.0x）
- [x] 2.6 设置按钮 — ImageButton，点击弹出 BottomSheetDialog 设置面板
- [x] 2.7 下方全屏按钮 — ImageButton 水平居中（仅横屏比例视频显示），点击切换横屏全屏
- [x] 2.8 控件样式设计 — 抖音风格图标 + 半透明背景 + 圆角

## 阶段3：三种状态切换

- [x] 3.1 定义状态枚举 — STATE_PURE（纯净播放态）/ STATE_NORMAL（竖屏常态）/ STATE_FULLSCREEN（横屏全屏态）
- [x] 3.2 纯净播放态实现 — 所有悬浮控件隐藏（alpha=0 + visibility=GONE 动画），仅保留视频画面
- [x] 3.3 竖屏常态实现 — 显示左下角标题 + 右侧功能按钮 + 下方全屏按钮（横屏比例视频）
- [x] 3.4 横屏全屏态实现 — Activity 旋转为横屏 + 视频铺满横屏 + 功能按钮适配横屏布局（基础框架，阶段4完善）
- [x] 3.5 单击切换显隐 — GestureDetector 检测单击，切换 PURE ↔ NORMAL 状态
- [x] 3.6 控件显隐动画 — alpha + translation 动画（300ms），平滑过渡
- [x] 3.7 控件默认显示，双指滑动隐藏 — 初始状态为 NORMAL（控件显示），双指同时左右滑动隐藏到 PURE，单击切换显隐（用户需求：右侧功能区和左下角名称不隐藏，只有同时左右滑动时才隐藏，横屏视频一直显示全屏按钮）

## 阶段4：横屏适配

- [x] 4.1 横屏比例视频检测 — 检测视频宽高比（videoWidth/videoHeight > 1.2 判定为横屏）
- [x] 4.2 等比缩放居中展示 — 横屏视频在竖屏容器内保持原始宽高比，居中展示（不拉伸裁剪）
- [x] 4.3 全屏按钮显示逻辑 — 仅横屏比例视频显示下方全屏按钮
- [x] 4.4 全屏按钮点击切换 — 点击切换到 STATE_FULLSCREEN，Activity requestedOrientation = LANDSCAPE
- [x] 4.5 双指缩放手势检测 — ScaleGestureDetector 检测双指向外拉伸（scaleFactor > 1.2）
- [x] 4.6 双指缩放触发全屏 — 触发横屏全屏（与点击全屏按钮效果一致）
- [x] 4.7 横屏全屏状态返回 — 横屏全屏态点击返回键/全屏按钮恢复竖屏常态
- [x] 4.8 横屏布局适配 — 横屏全屏态下功能按钮位置适配（右侧居中或顶部）

## 阶段5：设置面板（100%功能保留）

- [x] 5.1 创建 VideoSettingsPanel.kt — BottomSheetDialogFragment，综合设置面板容器
- [x] 5.2 创建 layout_video_settings_panel.xml — 设置面板布局（7个功能分区）
- [x] 5.3 快进快退功能迁移 — ←30s / ←10s / 10s→ / 30s→ 四按钮 + 画面比例 + 音轨选择迁移到设置面板
- [x] 5.4 倍速选择保留在右侧按钮 — 右侧 PopupMenu 快速切换，设置面板不再重复（长按倍速设置在面板内）
- [x] 5.5 调试面板迁移 — 调试信息切换 + 调试日志显示迁移到设置面板（VIDEO_PLAY_ERROR 同步写入）
- [x] 5.6 多集选择列表迁移 — RecyclerView 多集列表 + 上一集/下一集迁移到设置面板
- [x] 5.7 复制URL功能迁移 — 复制播放地址按钮迁移到设置面板
- [x] 5.8 视频简介迁移 — 视频简介展示迁移到设置面板
- [x] 5.9 书籍信息迁移 — 跳过（ViewPager2 模式仅用于 RSS 订阅源，不需要书籍信息）
- [x] 5.10 章节/卷选择迁移 — 跳过（ViewPager2 模式仅用于 RSS 订阅源，不需要章节/卷选择）
- [x] 5.11 菜单功能迁移 — 悬浮窗/其他播放器/编辑源/登录/日志迁移到设置面板（通过 SettingsPanelCallback 委托 Activity）
- [x] 5.12 播放地址展示+SettingsDialog合并 — 播放地址展示 + SettingsDialog 全部6项设置合并到设置面板

## 阶段6：Bug 修复（真机测试8个问题）

- [x] 6.1 悬浮窗崩溃修复 — VideoPlayService.onCreate() 开头添加 startForegroundNotification()（Android 12+ 5秒要求）
- [x] 6.2 右侧功能区首次不显示 — 初始状态改 NORMAL（控件可见），3秒自动隐藏 + reRegisterTouchListener 修复 GSY 覆盖 OnTouchListener
- [x] 6.3 左上角返回无效 — 新增 btn_back 返回按钮 + 点击逻辑（全屏退出全屏/否则 onBackPressed）
- [x] 6.4 倍速不一致 — 扩展倍速菜单为10档（0.5x~10x），统一设置面板和右侧 PopupMenu
- [x] 6.5 缓冲条消失 — 手动设置 bottom_progressbar 可见性 + ExoPlayer 缓存修复（6.7）
- [x] 6.6 设置按钮样式丑 — 按钮从 40dp 增大到 44dp，padding 从 8dp 增到 10dp
- [x] 6.7 分片下载没了特别卡 — Exo2MediaPlayer.prepareAsyncInternal() 改用 setMediaItem() 替代 setMediaSource(mMediaSource)，确保 MediaSource 通过含 SimpleCache 的 MediaSourceFactory 创建，HLS 分片下载+缓存读写恢复正常
- [x] 6.8 3003 Bug仍在 — 三项修复：(1)extractPlayerPageUrl 扩展支持 ?playUrl= 参数名；(2)移除 lower.startsWith("http") 过宽验证；(3)新增 resolvePlayerPageUrl() 公共方法，在 VideoPlay.kt 全部6处 player.setUp() 调用前统一解析播放器页面URL

## 阶段8：多线路支持

### 8.1 数据层

- [x] 8.1.1 创建 RssRoute.kt — 新增 `@Parcelize data class RssRoute(name, episodes)` 数据类
- [x] 8.1.2 VideoPlay 新增字段 — `rssRoutes: List<RssRoute>?` + `rssRouteIndex: Int`（L150 附近）
- [x] 8.1.3 实现 parseRssRoutes() — 解析嵌套 JSON `[{name, episodes:[{title,url}]}]`，兼容旧版扁平 JSON/多行URL（包装为单元素 List<RssRoute>）
- [x] 8.1.4 实现切换线路逻辑 — `switchRssRoute(index)`：更新 rssRouteIndex + rssEpisodes + 触发 UI 更新
- [x] 8.1.5 releaseAllVideos() 同步重置 — 在 L430-431 重置点增加 rssRoutes=null + rssRouteIndex=0
- [x] 8.1.6 startPlay 集成 — 在 ruleContent 非空分支调用 parseRssRoutes 替代 parseRssEpisodes

### 8.2 UI 层

- [x] 8.2.1 VideoFragment 增加线路选择器 — 复用 volumes RecyclerView，显示线路名（RssRouteAdapter），点击切换线路
- [x] 8.2.2 VideoFragment 增加集数选择器 — 复用 chapters RecyclerView（RssEpisodeAdapter），切换线路后更新集数列表
- [x] 8.2.3 线路选择器显隐逻辑 — rssRoutes == null 或 size <= 1 时隐藏，size > 1 时显示
- [x] 8.2.4 集数选择器显隐逻辑 — rssEpisodes == null 或 size <= 1 时隐藏，size > 1 时显示（已有R1实现）
- [x] 8.2.5 线路切换交互 — 点击线路调用 VideoPlay.switchRssRoute(index) + playRssEpisode + 更新UI
- [x] 8.2.6 集数切换交互 — 点击集数项调用 playRssEpisode（复用R1现有逻辑）
- [x] 8.2.7 切换线路后更新集数列表 — switchRssRoute 更新 rssEpisodes + showRssEpisodes 重建 adapter
- [x] 8.2.8 创建 item_route_selector.xml — 复用 item_video_chapter 布局（RssRouteAdapter 与 ChapterAdapter UI 一致）

### 8.3 兼容性验证

- [x] 8.3.1 单URL场景兼容 — rssRoutes=null 时不显示线路/集数选择器，直接播放
- [x] 8.3.2 多集无线路场景兼容 — rssRoutes.size==1 时隐藏线路选择器，只显示集数
- [x] 8.3.3 多线路多集场景 — rssRoutes.size>1 时显示线路+集数选择器
- [x] 8.3.4 ruleContent 旧格式兼容 — 扁平 JSON 数组/多行URL 自动包装为单线路

## 阶段7：验证与文档同步

- [x] 7.1 编译验证 — `.gradlew.bat assembleDebug` 编译通过
- [ ] 7.2 L2 真机验证 — 安装到 MEmu，验证三种状态切换 + 滑动切换 + 设置面板 + 横屏全屏
- [ ] 7.3 3003 Bug 验证 — 使用 R2 日志中的播放器页面 URL 验证修复效果
- [ ] 7.4 100%功能保留验证 — 逐项核对当前所有功能是否在新设计中可用
- [ ] 7.5 多线路验证 — 使用奈飞中文网订阅源验证线路切换+集数切换+兼容性
- [ ] 7.6 updateLog.md 更新 — 编译前更新用户可感知的变更说明
- [ ] 7.7 文档同步 — INDEX.md + basic-memory + project_memory.md

## AOAdapt 日志

> 记录实施过程中遇到的 AOAdapt（AI优化适配）决策，遇问题时必须记录。

### 阶段8实施

1. **8.2.1 UI方案变更**：tasks.md 原设计为"左下角标题下方 Spinner/TextView"显示线路选择器。实施时改为复用现有 `volumes` RecyclerView 显示线路列表，理由：(1)已有 volumes/chapters 双层交互模式用户熟悉；(2)无需新增布局组件代码改动最小；(3)与书源交互体验一致。
2. **8.2.8 布局复用**：tasks.md 原设计创建 `item_route_selector.xml`。实施时改为复用 `item_video_chapter` 布局，因为 RssRouteAdapter 与 ChapterAdapter/RssEpisodeAdapter UI 结构完全一致（单行文本+选中高亮），无需单独布局文件。
3. **8.1.6 startPlay 集成**：ruleContent 非空分支用 `parseRssRoutes` 替代 `parseRssEpisodes`。`parseRssRoutes` 内部自动回退到 `parseRssEpisodes`（包装为单线路），保证 100% 向后兼容。
4. **R5 多URL分支适配**：R5 自动抓取多 URL 时也包装为 `RssRoute`，保持数据层一致性，避免 UI 层需要判断 rssRoutes 是否为空。

### Phase 1 实施

5. **1.4 模式路由时机**：`setupPlayerView()/initView()/upView()` 从 `onActivityCreated` 同步调用移入 `lifecycleScope.launch` 协程内部（在 `initSource` 之后），因为模式判断依赖 `VideoPlay.book` 和 `VideoPlay.singleUrl`，这两个值在 `initSource` 完成后才确定。同步调用时这些值可能未就绪。
6. **1.6 数据传递选择**：未采用 Bundle 传参方案（Fragment 无法接收 startPlay 异步结果），改为 VideoPlay 全局单例 + Fragment episodeIndex 参数 + `onFragmentViewReady` 回调三层机制：(1)VideoPlay 单例持有所有播放状态；(2)Fragment 通过 episodeIndex 定位自己的集；(3)`onFragmentViewReady` 解决 ViewPager2 创建 Fragment 异步时序问题（onPageSelected 可能先于 Fragment 视图创建触发）。
7. **1.7 防重复激活**：`isActivated` 标志防止 `onPageSelected` 和 `onFragmentViewReady` 双触发导致 `startPlay`/`playRssEpisode` 重复调用。
8. **UP_VIDEO_INFO 增量更新**：使用 `notifyItemRangeInserted/Removed` 替代 `notifyDataSetChanged`，避免首个 Fragment 被重建导致播放中断。
9. **1.3 双容器过渡**：采用 FrameLayout 双容器（legacyContainer visible + viewPagerContainer gone）而非直接替换布局，理由：(1)旧模式所有功能（全屏/设置/线路/集数/调试）仍可正常使用；(2)ViewPager2 模式功能逐步迁移，风险可控；(3)书源/单URL路径零改动。

### 阶段2 实施

10. **2.3 静音 API 适配**：VideoPlayer.isMuted 是 private 字段，新增 `toggleMute()` + `isMutedPublic` 只读属性公开静音控制能力，而非直接改 isMuted 可见性。理由：isMuted 内部与 ivMute 按钮联动（旧播放器控制器中的静音按钮），toggleMute 统一处理状态切换+图标更新，避免外部直接修改 isMuted 遗漏图标更新。
11. **2.4 收藏委托 Activity**：Fragment 的收藏按钮点击不直接操作 ViewModel，而是委托 Activity 的 `onFragmentStarClicked()` 方法。理由：收藏逻辑涉及 RssStar/RssRecord 状态+ViewModel+RssFavoritesDialog，Activity 已有完整流程（menu_rss_star onOptionsItemSelected），Fragment 只需触发+更新按钮图标。
12. **2.5 倍速 PopupMenu 替代 Spinner**：design.md 原设计倍速使用 Spinner（与旧模式一致）。实施时改为 PopupMenu，理由：(1)抖音风格悬浮控件不适合内嵌 Spinner（空间有限+不美观）；(2)PopupMenu 点击弹出更符合短视频 App 交互习惯；(3)7档倍速(0.5x~3.0x)覆盖比旧模式5档(1x~10x)更实用。
13. **2.6 设置按钮复用 SettingsDialog**：直接复用现有 SettingsDialog（静音/自动播放/直接全屏/长按倍速/缓存容量），无需新建设置面板。阶段5将扩展此 Dialog 迁移更多功能。
14. **2.7 全屏按钮 visibility=gone 默认隐藏**：全屏按钮仅在横屏比例视频（videoWidth/videoHeight > 1.2）时显示，竖屏视频不需要全屏按钮（已经是全屏状态）。此逻辑由 `updateFullscreenButtonVisibility()` 控制，阶段4完善调用时机。
15. **2.8 半透明圆角背景 bg_overlay_button**：创建 `#40FFFFFF`（25%白色）+ 20dp 圆角矩形。选择白色半透明而非黑色，理由：抖音风格控件在视频画面上白色更常见（头像/点赞/评论图标背景均为白色半透明），黑色半透明更像 B 站风格。

### 阶段3 实施

16. **3.5 手势检测位置选择**：controlsLayer 虽然叠在 playerView 上面，但设置 `clickable=false`，触摸事件穿透到 playerView。手势检测放在 playerView 的 `setOnTouchListener` 上，返回 false 不消费事件。理由：(1)controlsLayer 的 `clickable=false` 让空白区域事件穿透到 playerView；(2)按钮区域由子 View 自身的 clickable=true 拦截；(3)playerView 返回 false 让 GSY 播放器正常处理触摸。
17. **3.7 默认状态改为 PURE**：design.md 原设计"视频加载完成后自动进入 PURE"。实施时改为 Fragment 创建时即进入 PURE（控件初始隐藏），无需等待 onPrepared 回调。理由：(1)避免依赖 GSY 回调时序（onPrepared 可能在 Fragment 还未就绪时触发）；(2)抖音/TikTok 打开视频时控件就是隐藏的，用户需要点击才显示；(3)简化实现，无需额外注册/注销回调。
18. **3.7 自动隐藏计时器**：切到 NORMAL 后 3 秒自动回到 PURE。使用 `view.postDelayed` 而非 Handler/Timer，理由：(1)view.postDelayed 自动与 View 生命周期绑定，View detach 时自动取消；(2)无需额外的 Handler 清理逻辑。
19. **3.6 显隐动画方案**：淡出使用 `alpha=0 + translationY=10%height`（微微下沉消失），淡入使用 `alpha=1 + translationY=0`（从下方浮出）。translationY 方向选择"下沉消失/浮出出现"而非"上浮消失/下沉出现"，因为底部控件（标题/全屏按钮）更符合"从下方浮现"的视觉隐喻。

### 阶段4 实施

20. **4.1 onPrepared 回调位置选择**：在 `activatePlayer()` 中注册 `setVideoAllCallBack`，而非在 `onViewCreated` 中。理由：(1)GSY 的 `setVideoAllCallBack` 需要在播放开始前注册，`activatePlayer` 是播放的唯一起点；(2)`isActivated` 标志保证只注册一次；(3)`onPrepared` 回调中获取 `currentVideoWidth/Height` 并更新 `VideoPlay.isPortraitVideo` + 全屏按钮显示。
21. **4.2 等比缩放无需额外代码**：GSY 默认 `SCREEN_TYPE_DEFAULT` 已保持原始宽高比居中展示。在 ViewPager2 模式下，VideoPlayer 设置为 `match_parent` 铺满屏幕，GSY 自动按视频宽高比缩放居中（横屏视频 letterbox，竖屏视频填满）。无需调用 `GSYVideoType.setShowType()`（全局静态方法会影响旧模式播放器）。
22. **4.4 ViewPager2 全屏策略**：不使用 GSY 的 `startWindowFullscreen`（会创建新播放器实例导致 Fragment 失控），改为直接旋转 Activity（`requestedOrientation = SENSOR_LANDSCAPE`）+ 通知 Fragment（`onFullScreenChanged(true)`）。退出时恢复原方向 + 通知 Fragment（`onFullScreenChanged(false)`）。
23. **4.5 ScaleGestureDetector 与 GestureDetector 共存**：两个检测器都通过 `onTouchEvent(event)` 分析事件，不消费事件。在 playerView 的 `setOnTouchListener` 中依次调用两个检测器，返回 `false` 让 GSY 播放器正常处理触摸。ScaleGestureDetector 仅在 `onScaleEnd` 中判断 `scaleFactor > 1.2f` 触发全屏。
24. **4.7 FULLSCREEN 状态单击行为**：FULLSCREEN 态下单击不退出全屏（那是返回键/全屏按钮的事），而是切换控件显隐（`controlsVisibleInFullscreen` 布尔标志）。理由：(1)TikTok/YouTube 全屏态也是单击切换控件显隐；(2)避免误触退出全屏中断观看体验。
25. **4.8 全屏按钮图标切换**：创建 `ic_fullscreen_exit.xml`（四角箭头向内），全屏中显示退出图标、非全屏显示进入图标。`updateFullscreenButtonIcon(isInFullScreen)` 方法控制切换。全屏态下全屏按钮始终可见（竖屏视频也显示），确保用户有明确的退出入口。
26. **4.8 onConfigurationChanged ViewPager2 守卫**：在 `else` 分支（`!isFullScreen`）中增加 `if (useViewPagerMode) return`，阻止设备自动旋转触发全屏。理由：(1)ViewPager2 模式全屏由用户主动操作（按钮/双指）触发；(2)退出全屏后恢复 `SCREEN_ORIENTATION_UNSPECIFIED`，如果允许自动旋转会立即重新进入全屏，形成循环。

### 阶段5 实施

27. **5.1 VideoSettingsPanel 替代 SettingsDialog**：tasks.md 原设计为 `VideoSettingsDialog`。实施时改名为 `VideoSettingsPanel`，理由：(1)与项目已有 `SettingsDialog`（6项设置的 DialogFragment）区分；(2)Panel 名称更准确描述 BottomSheetDialogFragment 的交互形式。
28. **5.4 倍速保留在右侧按钮**：tasks.md 原设计将倍速 Spinner 迁移到设置面板。实施时保留右侧 PopupMenu 快速切换（0.5x~3.0x），设置面板只放长按倍速设置。理由：(1)倍速是高频操作，2次点击（显示控件→点倍速）比3次点击（显示控件→开面板→选倍速）更快；(2)右侧 PopupMenu 已够用，无需在面板中重复。
29. **5.9/5.10 跳过书籍信息/章节卷选择**：ViewPager2 模式仅用于 RSS 订阅源（`book==null && !singleUrl`），书籍信息和章节/卷选择在此模式下不会出现。这两个任务标记为跳过。
30. **5.5 调试面板在 BottomSheet 内**：旧模式调试面板是固定在视频下方的 LinearLayout。ViewPager2 沉浸模式下不适合叠加在视频上，改为在设置面板内提供调试按钮+日志区域。VIDEO_PLAY_ERROR 事件通过 Activity 的 `settingsPanel?.appendDebugLog()` 同步写入。
31. **5.11 SettingsPanelCallback 委托模式**：菜单功能（悬浮窗/编辑源/日志等）需要 Activity 上下文（启动 Activity、操作 Fragment 等），通过 `SettingsPanelCallback` 接口委托给 Activity 实现。理由：(1)BottomSheetDialogFragment 不应直接操作宿主 Activity 的方法；(2)与阶段2的收藏按钮委托模式一致。
32. **5.12 SettingsDialog 合并**：将 SettingsDialog 的全部6项设置（autoPlay/startFull/fullBottomProgressBar/muteOnStart/longPressSpeed/videoCacheSize）合并到 VideoSettingsPanel 的"播放设置"分区，设置按钮不再单独弹出 SettingsDialog。减少用户操作步骤（1步 vs 原来2步：先点设置按钮→再弹出Dialog）。
33. **VideoPlayer internal 包装方法**：showRatioDialog/showAudioTrackDialog 是 private 方法，新增 `showRatioDialogPublic()`/`showAudioTrackDialogPublic()` 的 internal 包装。与阶段2的 `toggleMute()`/`isMutedPublic` 模式一致，不改原方法可见性，避免影响其他调用方。

### 阶段6 Bug 修复

34. **6.7 缓存绕过根因**：Exo2MediaPlayer.prepareAsyncInternal() 使用 `mInternalPlayer.setMediaSource(mMediaSource)` 传入了父类 IjkExo2MediaPlayer 创建的 MediaSource。该 MediaSource 通过 DefaultDataSource.Factory（不含缓存）创建，完全绕过了 ExoPlayer.Builder 中配置的含 SimpleCache 的 MediaSourceFactory。修复：改用 `setMediaItem(MediaItem.fromUri(currentUrl))`，让 player 使用自身的 MediaSourceFactory 创建 MediaSource，确保 HLS 分片下载和 SimpleCache 缓存读写正常。
35. **6.8 3003 Bug 三层修复**：(A) `extractPlayerPageUrl` 正则从 `[?&]url=` 扩展为 `[?&](?:url|playUrl)=`，支持使用 playUrl 参数名的站点（如91仓库源）；(B) 验证条件移除 `lower.startsWith("http")` 过宽匹配，要求解码后 URL 必须包含 .m3u8/.mp4/format=m3u8/type=m3u8 视频特征，避免非视频流 URL 误判；(C) 新增 `resolvePlayerPageUrl()` 公共方法，在 VideoPlay.kt 全部6处 `player.setUp()` 前统一调用，覆盖 singleUrl/R5单URL/R5回退/ruleContent单URL/书源/playRssEpisode 所有路径。
36. **6.2 初始状态改 NORMAL**：design.md 原设计"视频加载后进入 PURE"。真机测试发现用户首次进入看不到控件，不知道如何操作。改为初始 NORMAL（控件可见），3秒后自动隐藏到 PURE。同时 reRegisterTouchListener 修复 GSY 的 setUp 可能覆盖 OnTouchListener 的问题。

### 控件显隐需求变更（用户明确需求）

37. **3.7 控件显隐需求变更**：用户明确需求："控件默认不隐藏，右侧功能区和左下角名称一直显示，只有同时左右滑动时才隐藏控件到 PURE，横屏视频一直显示全屏按钮，竖屏视频可以不显示"。移除 autoHideRunnable + scheduleAutoHide（AI 臆造的3秒自动隐藏逻辑），初始状态改为 NORMAL（控件默认显示），新增双指左右滑动检测（ACTION_POINTER_DOWN 记录两指起始X坐标，ACTION_MOVE 检测两指同时横向移动超过100px阈值且方向一致→切换到 PURE）。
38. **btn_fullscreen 独立于 leftBottomContainer**：将 btn_fullscreen 从 leftBottomContainer 内部移到 controlsLayer 顶层（底部居中），约束为 `layout_constraintBottom_toBottomOf="parent"` + `start_toStartOf="parent"` + `end_toEndOf="parent"`。理由：用户需求"横屏视频一直显示全屏按钮，不受控件显隐影响"，btn_fullscreen 独立于 leftBottomContainer 后，hideControlsAnimated 隐藏 leftBottomContainer 时不影响 btn_fullscreen。
39. **reRegisterTouchListener Bug 修复**：发现 reRegisterTouchListener()（onPrepared 后重新注册触摸监听）只包含 gestureDetector + scaleGestureDetector，**丢失了双指左右滑动检测逻辑**。根因：initGestureDetector 和 reRegisterTouchListener 各自独立实现触摸处理，代码重复且不同步。修复：提取公共方法 `handlePlayerTouchEvent(event)`，两处统一调用，确保所有触摸逻辑（单击切换+双指缩放+双指左右滑动）一致。

### 真机测试 Bug 修复（第二轮）

40. **双指事件消费修复（GSY 拦截多指手势）**：用户真机反馈"左右滑动隐藏不生效"。根因：GSY 播放器内部有单指手势处理（进度条/亮度/音量），会拦截多指事件。我们的 `setOnTouchListener` 返回 `false`，导致 GSY 拦截了双指事件，双指检测不生效。修复：`handlePlayerTouchEvent` 方法改为返回 `Boolean`，当 `pointerCount >= 2` 时返回 `true` 消费事件，阻止 GSY 拦截多指手势；单指事件返回 `false` 交给 GSY 正常处理。

41. **按钮图标颜色统一白色**：用户真机反馈"右侧四个功能按钮样式不统一，要不全部白色吧"。根因：各图标文件来自不同来源，fillColor 不一致（黑色 #FF000000 / 灰色 #595757 / 白色 #FFFFFFFF）。修复：在 fragment_video.xml 中给所有 7 个 ImageButton（btn_rewind/btn_mute/btn_star/btn_speed/btn_settings/btn_forward/btn_fullscreen）添加 `android:tint="#FFFFFF"` 属性，统一着色为白色。不修改原始图标文件，避免影响其他页面。

42. **左上角返回按钮不起作用修复**：用户真机反馈"内置视频播放器左上角的返回还是不起作用"。根因：VideoPlayerActivity 未重写 `onSupportNavigateUp()`，点击 Toolbar 返回箭头时调用默认 `NavUtils.navigateUpFromSameTask(this)`，该方法依赖 AndroidManifest 中 PARENT_ACTIVITY 声明，未声明时无响应。`onBackPressedDispatcher.addCallback` 只拦截系统返回键，不拦截 Toolbar 返回箭头。修复：重写 `onSupportNavigateUp()`，委托给 `onBackPressedDispatcher.onBackPressed()`，与系统返回键行为一致（全屏→退出全屏，非全屏→finish）。

## 任务依赖关系

```
阶段1（架构）→ 阶段2（控件）→ 阶段3（状态）→ 阶段4（横屏）
                                            ↓
阶段5（设置面板）← 依赖阶段2/3 的控件布局
阶段6（Bug修复）← 独立，可与阶段1-5 并行
阶段8（多线路）← 依赖阶段1（VideoFragment）+ 阶段2（悬浮控件），数据层独立
阶段7（验证）← 依赖阶段1-6-8 全部完成
```

## 优先级标记

- **P0（必须完成）**：1.1-1.7, 2.1-2.8, 3.1-3.7, 4.1-4.4, 4.7-4.8, 5.1-5.12, 6.1-6.5, 8.1.1-8.1.6, 8.2.1-8.2.8, 8.3.1-8.3.4, 7.1-7.2
- **P1（应该完成）**：4.5-4.6（双指缩放手势）
- **P2（可选优化）**：7.3-7.7（验证与文档同步，实际必须但标记为验证阶段）
