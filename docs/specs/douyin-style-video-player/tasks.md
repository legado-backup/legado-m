# Tasks: 抖音风格沉浸式竖屏视频播放器重设计

> **状态**：🔄 开发中（阶段8.1+8.2 已完成，编译通过）
> **创建日期**：2026-07-10
> **任务编号规则**：T{阶段}.{序号}，阶段 1=架构搭建 / 2=悬浮控件 / 3=状态切换 / 4=横屏适配 / 5=设置面板 / 6=Bug修复 / 7=验证

## 阶段1：架构搭建（ViewPager2 + Fragment）

- [ ] 1.1 创建 VideoFragment.kt — 单个视频播放 Fragment，持有播放器视图 + 悬浮控件层 + 设置面板入口
- [ ] 1.2 创建 VideoPagerAdapter.kt — ViewPager2 的 FragmentStateAdapter，管理 VideoFragment 列表
- [ ] 1.3 重构 activity_video_player.xml — LinearLayout 替换为 ConstraintLayout + ViewPager2 容器
- [ ] 1.4 重构 VideoPlayerActivity.kt — 改为容器角色，持有 ViewPager2，管理 VideoFragment 实例
- [ ] 1.5 创建 fragment_video.xml — VideoFragment 布局：播放器视图（铺满）+ 悬浮控件层（ConstraintLayout 叠加）
- [ ] 1.6 数据传递机制设计 — VideoPlayerActivity → VideoFragment 传递 videoUrl/videoTitle/rssEpisodes/book 数据
- [ ] 1.7 ViewPager2 配置 — 垂直方向（ORIENTATION_VERTICAL）+ setOffscreenPageLimit(1) + 用户输入启用

## 阶段2：悬浮控件布局

- [ ] 2.1 左下角视频标题 — TextView 固定左下角，支持长文本省略（maxLines=2, ellipsize=end）
- [ ] 2.2 右侧竖直功能按钮容器 — LinearLayout vertical，居中右侧
- [ ] 2.3 静音按钮 — ImageButton，切换静音状态（图标变化）
- [ ] 2.4 收藏按钮 — ImageButton，切换收藏状态（图标变化）
- [ ] 2.5 倍速按钮 — ImageButton，点击弹出倍速选择（0.5x/0.75x/1.0x/1.25x/1.5x/2.0x/3.0x）
- [ ] 2.6 设置按钮 — ImageButton，点击弹出 BottomSheetDialog 设置面板
- [ ] 2.7 下方全屏按钮 — ImageButton 水平居中（仅横屏比例视频显示），点击切换横屏全屏
- [ ] 2.8 控件样式设计 — 抖音风格图标 + 半透明背景 + 圆角

## 阶段3：三种状态切换

- [ ] 3.1 定义状态枚举 — STATE_PURE（纯净播放态）/ STATE_NORMAL（竖屏常态）/ STATE_FULLSCREEN（横屏全屏态）
- [ ] 3.2 纯净播放态实现 — 所有悬浮控件隐藏（visibility=GONE 或 alpha=0 动画），仅保留视频画面
- [ ] 3.3 竖屏常态实现 — 显示左下角标题 + 右侧功能按钮 + 下方全屏按钮（横屏比例视频）
- [ ] 3.4 横屏全屏态实现 — Activity 旋转为横屏 + 视频铺满横屏 + 功能按钮适配横屏布局
- [ ] 3.5 单击切换显隐 — GestureDetector 检测单击，切换 PURE ↔ NORMAL 状态
- [ ] 3.6 控件显隐动画 — alpha + translation 动画（300ms），平滑过渡
- [ ] 3.7 默认进入纯净播放态 — 视频加载完成后自动进入 STATE_PURE

## 阶段4：横屏适配

- [ ] 4.1 横屏比例视频检测 — 检测视频宽高比（videoWidth/videoHeight > 1.2 判定为横屏）
- [ ] 4.2 等比缩放居中展示 — 横屏视频在竖屏容器内保持原始宽高比，居中展示（不拉伸裁剪）
- [ ] 4.3 全屏按钮显示逻辑 — 仅横屏比例视频显示下方全屏按钮
- [ ] 4.4 全屏按钮点击切换 — 点击切换到 STATE_FULLSCREEN，Activity requestedOrientation = LANDSCAPE
- [ ] 4.5 双指缩放手势检测 — ScaleGestureDetector 检测双指向外拉伸（scaleFactor > 1.2）
- [ ] 4.6 双指缩放触发全屏 — 触发横屏全屏（与点击全屏按钮效果一致）
- [ ] 4.7 横屏全屏状态返回 — 横屏全屏态点击返回键/全屏按钮恢复竖屏常态
- [ ] 4.8 横屏布局适配 — 横屏全屏态下功能按钮位置适配（右侧居中或顶部）

## 阶段5：设置面板（100%功能保留）

- [ ] 5.1 创建 VideoSettingsDialog.kt — BottomSheetDialogFragment，设置面板容器
- [ ] 5.2 创建 layout_video_settings.xml — 设置面板布局（垂直滚动 LinearLayout）
- [ ] 5.3 快进快退功能迁移 — ←30s / ←10s / 10s→ / 30s→ 四按钮迁移到设置面板
- [ ] 5.4 倍速选择迁移 — 倍速 Spinner 迁移到设置面板（与右侧倍速按钮联动）
- [ ] 5.5 调试面板迁移 — 调试信息切换 + 调试日志显示迁移到设置面板
- [ ] 5.6 多集选择列表迁移 — RecyclerView 多集列表迁移到设置面板
- [ ] 5.7 复制URL功能迁移 — 复制播放地址按钮迁移到设置面板
- [ ] 5.8 视频简介迁移 — 视频简介展示迁移到设置面板
- [ ] 5.9 书籍信息迁移 — 封面/书名/作者/简介迁移到设置面板（书籍源模式）
- [ ] 5.10 章节/卷选择迁移 — 章节列表 + 卷列表迁移到设置面板（书籍源模式）
- [ ] 5.11 菜单功能迁移 — 自定义按钮/配置/登录/编辑源/日志/其他播放器迁移到设置面板
- [ ] 5.12 播放地址展示迁移 — 当前播放地址展示迁移到设置面板（可展开/折叠）

## 阶段6：3003 Bug 修复

- [x] 6.1 分析 VideoUrlExtractor.kt 当前提取逻辑 — 确认五种提取方法的调用顺序
- [x] 6.2 新增播放器页面 URL 识别方法 — extractPlayerPageUrl()：检测 `?url=` 或 `&url=` 参数
- [x] 6.3 提取 url 参数值并 URL 解码 — URLDecoder.decode 提取实际视频流 URL
- [x] 6.4 集成到 R5 提取流程 — 在五种提取方法之后增加播放器页面 URL 解析步骤 + isVideoUrl 放行 url= 参数
- [ ] 6.5 单元测试验证 — 构造播放器页面 URL 测试用例，验证提取结果

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
