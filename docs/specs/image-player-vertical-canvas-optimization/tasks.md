# 内置图片播放器垂直画布优化方案 tasks

> 状态：🔄 实施中（核心 P0 已完成+编译通过，待补全 P1 任务+真机测试）
> 任务类型：OpenSpec 四文档之一（实施任务清单）
> 上游依赖：
> - [player-review-and-optimization](../player-review-and-optimization/tasks.md)（图片部分由本 spec 取代）
> - [thread-pool-split-config](../thread-pool-split-config/spec.md)（提供 `AppConfig.updateCacheThreadCount` 配置）
> - [rss-concurrency-and-checksource-optimization](../rss-concurrency-and-checksource-optimization/spec.md)（提供 `AppConfig.imageLoadConcurrency` 配置）

## 任务统计

| 优先级 | 任务数 | 说明 |
|--------|--------|------|
| P0 必须 | 31 项 | R1.1-R1.20（20项）+ V2 新增 6 项（0.5 上游核查 + 3.1.4 Glide.preload + 3.5.1/2/3 状态保存 + 5.1.4 清理）+ V3 新增 5 项（6.5.1~6.5.5 对应 B-6~B-10） |
| P1 应该 | 10 项 | R2.1-R2.9（9项）+ V2 新增 1 项（1.3.5 Theme.ImageDetail） |
| P2 可选 | 7 项 | R3.1-R3.7，长期建议；V3 新增 D-1~D-5 优化项可视情况纳入 |
| **合计** | **48 项** | 含文档同步与真机验证（V3 修订后） |

---

## Phase 0：准备工作（前置任务）

- [x] 0.1 用户审查并通过本设计方案（强制检查点 1：AskUserQuestion 三选项结构）
  - 验证：AskUserQuestion 响应记录写入项目记忆；用户选择"通过"
  - 文件：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`

- [x] 0.2 源码现状核查（确认 spec/design 中引用的行号和字段名准确）
  - 验证：Read 确认 ImageGalleryActivity.kt 当前持有 ImageArticlePagerAdapter；ImagePlay.kt 当前字段清单；ReadRss.kt L41-43 路由回退逻辑
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt` / `ImagePlay.kt` / `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt`

- [x] 0.3 player-review-and-optimization README.md 更新"图片部分已废弃"标记
  - 验证：Read 确认 player-review-and-optimization/README.md 含"图片部分已废弃，由 image-player-vertical-canvas-optimization 取代"声明
  - 文件：`docs/specs/player-review-and-optimization/README.md`

- [x] 0.4 docs/INDEX.md 同步添加本 spec 到"设计中"列表 + 更新 player-review-and-optimization 状态
  - 验证：Read 确认 INDEX.md "活跃 Specs" 表新增 image-player-vertical-canvas-optimization 行；player-review-and-optimization 行标注"图片部分已废弃"
  - 文件：`docs/INDEX.md`

- [x] 0.5 核查上游 spec 是否已实施（V2 O-8 新增）
  - 验证：Read `docs/specs/thread-pool-split-config/spec.md` 确认 `AppConfig.updateCacheThreadCount`（默认16）已实施或处于设计完成状态；Read `docs/specs/rss-concurrency-and-checksource-optimization/spec.md` 确认 `AppConfig.imageLoadConcurrency`（默认5）已实施或处于设计完成状态
  - 降级策略：若上游 spec 未实施，本 spec 协程池配置降级为硬编码默认值（imageLoadConcurrency=5 / updateCacheThreadCount=16），并在代码注释中标注 `// 简化说明: 上游 spec 未实施，使用硬编码默认值；已知上限: 上游 spec 实施后需替换为 AppConfig 配置；升级路径: 移除硬编码改为 AppConfig.imageLoadConcurrency/updateCacheThreadCount`
  - 文件：`docs/specs/thread-pool-split-config/spec.md` + `docs/specs/rss-concurrency-and-checksource-optimization/spec.md`

---

## Phase 1：架构重构 P0（R1.1-R1.5）

### 1.1 重写 ImageGalleryActivity 主架构（R1.1）

- [x] 1.1.1 删除 ImageGalleryActivity 中双 ViewPager2 嵌套代码（ImageArticlePagerAdapter 引用 / 内层 ViewPager2 初始化）
  - 验证：Grep 确认 ImageGalleryActivity.kt 无 ImageArticlePagerAdapter 引用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`
  - 日志模板：`AppLog.put("ImageGalleryActivity: rewrite to RecyclerView architecture")`

- [x] 1.1.2 添加 RecyclerView + LinearLayoutManager 初始化代码
  - 验证：Read 确认 ImageGalleryActivity 持有 RecyclerView 实例；含 LinearLayoutManager 初始化；setItemViewCacheSize(2)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 1.1.3 添加 ImageCanvasViewModel 初始化和绑定
  - 验证：Read 确认 ImageGalleryActivity 通过 ViewModelProvider 获取 ImageCanvasViewModel
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 1.2 新建 ImageCanvasAdapter（R1.2）

- [x] 1.2.1 新建 ImageCanvasAdapter 类骨架（继承 RecyclerView.Adapter）
  - 验证：Read 确认 ImageCanvasAdapter 继承 RecyclerView.Adapter；含 onCreateViewHolder / onBindViewHolder / getItemViewType / getItemCount
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`（新建）

- [x] 1.2.2 实现 5 种 ViewType（图片项 / 加载中 / 加载失败 / 没有更多 / 文章分隔符）
  - 验证：Read 确认 ImageCanvasAdapter 含 5 种 TYPE_* 常量；getItemViewType 按位置返回对应类型
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 1.2.3 实现 ImageViewHolder（含 PhotoView 缩略图 + 点击回调）
  - 验证：Read 确认 ImageViewHolder 含 PhotoView 绑定；含 setOnClickListener 回调
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

### 1.3 新建 ImageDetailActivity（R1.3）

- [x] 1.3.1 新建 ImageDetailActivity 类骨架（继承 BaseActivity，W1 判断：无 ViewModel 需求避免过度工程化）
  - 验证：Read 确认 ImageDetailActivity 继承 BaseActivity；含 onCreate / onDestroy 生命周期
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`（新建）
  - W1 判断理由：ImageDetailActivity 仅展示大图+旋转工具栏，无复杂业务逻辑，无需 ViewModel；改 VMBaseActivity 需新建空 ViewModel 类引入不必要抽象

- [x] 1.3.2 实现 ViewPager2 初始化 + 初始定位
  - 验证：Read 确认 ImageDetailActivity 含 ViewPager2 实例；orientation=horizontal；setCurrentItem(startIndex, false)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

- [x] 1.3.3 实现沉浸式全屏（WindowInsetsControllerCompat）
  - 验证：Grep 确认 ImageDetailActivity 含 WindowInsetsControllerCompat；无 SYSTEM_UI_FLAG 残留
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

- [x] 1.3.4 实现共享元素动画接收（ActivityOptions）
  - 验证：Read 确认 ImageDetailActivity.onCreate 含 window.sharedElementEnterTransition 配置
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`
  - W2 实施：新增 AppTheme.ImageDetail 主题启用 windowActivityTransitions + onActivityCreated 设置 ChangeBounds 过渡动画（duration=250ms）

- [x] 1.3.5 新建 Theme.ImageDetail 主题启用 windowActivityTransitions（V2 O-5 新增）
  - 验证：Read 确认 `app/src/main/res/values/styles.xml` 新增 `Theme.ImageDetail` 主题，继承 `Theme.AppCompat.NoActionBar`，含 `<item name="android:windowActivityTransitions">true</item>`；Read 确认 `AndroidManifest.xml` 中 ImageDetailActivity 注册使用 `android:theme="@style/Theme.ImageDetail"`（替换原 `@style/Theme.AppCompat.NoActionBar`）
  - 文件：`app/src/main/res/values/styles.xml` + `app/src/main/AndroidManifest.xml`
  - 注意：AppCompat 主题默认未启用 windowActivityTransitions，需显式启用才能使用共享元素动画

### 1.4 新建 ImageDetailAdapter（R1.4）

- [x] 1.4.1 新建 ImageDetailAdapter 类骨架（基于 ImagePageAdapter 精简）
  - 验证：Read 确认 ImageDetailAdapter 继承 RecyclerView.Adapter；含 PhotoView 绑定
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`（新建）

- [x] 1.4.2 迁移 PhotoView 缩放/旋转/长按保存能力
  - 验证：Read 确认 ImageDetailAdapter 含 PhotoView 缩放（双指 / 双击）/ 旋转 / 长按保存实现
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`

- [x] 1.4.3 实现 ViewPager2.OnPageChangeCallback 页码更新
  - 验证：Read 确认 ImageDetailAdapter 含 onPageSelected 回调；更新 TitleBar 页码"文章N/M 图片X/Y"
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

### 1.5 新建 ImageCanvasViewModel（R1.5）

- [x] 1.5.1 新建 ImageCanvasViewModel 类（继承 ViewModel）
  - 验证：Read 确认 ImageCanvasViewModel 继承 ViewModel；含 loadedArticleIndices 字段（allImageUrls 实际位于 ImagePlay 单例，通过 appendItems 写入，V4 B-14）
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`（新建）

- [x] 1.5.2 实现 loadInitialArticle() 协程加载首篇文章图片（V4 B-11/B-12：返回类型修正）
  - 验证：Read 确认含 loadInitialArticle 方法；调用 `Rss.getContentAwait(rssArticle, ruleContent, rssSource)` 返回 String body（非 List<RssImage>）；调用 `parseImageUrls(body, article.link, ruleImage, rssSource)` 解析为 List<String>（RssImage 类不存在）；转换为 List<ImageCanvasItem.ImageItem> 后调用 ImagePlay.appendItems
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

- [x] 1.5.3 实现 loadNextArticle() 协程分页加载
  - 验证：Read 确认含 loadNextArticle 方法；含 loadJob?.cancel() 取消机制；含 preloadedArticles 去重
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

- [x] 1.5.4 实现 onCleared() 协程取消
  - 验证：Read 确认 onCleared 含 loadJob?.cancel()
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

---

## Phase 2：列表模式能力 P0（R1.6-R1.9）

### 2.1 单 RecyclerView 垂直长画布实现（R1.6）

- [x] 2.1.1 配置 LinearLayoutManager + setItemViewCacheSize(2)
  - 验证：Read 确认 ImageGalleryActivity 含 LinearLayoutManager 初始化；含 setItemViewCacheSize(2)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 2.1.2 实现快速滚动暂停加载（Glide.pauseRequests / resumeRequests）
  - 验证：Read 确认 RecyclerView.OnScrollListener.onScrollStateChanged 含 newState == SCROLL_STATE_DRAGGING 时 pauseRequests； newState == SCROLL_STATE_IDLE 时 resumeRequests
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 2.2 多线程并行加载（R1.7）

- [x] 2.2.1 ImageCanvasAdapter 中实现 Glide 异步加载
  - 验证：Grep 确认 ImageCanvasAdapter 中含 Glide.with(itemView.context).load(url).into(imageView)
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 2.2.2 复用 AppConfig 协程池配置（V2 修订 B-1）
  - 验证：Read 确认 ImageCanvasViewModel 中使用 `AppConfig.updateCacheThreadCount`（默认16）控制 Rss.getContentAwait 协程并发数；Grep 确认 ImageCanvasAdapter 中 Glide 异步加载（由 LegadoGlideModule.setSourceExecutor 通过 `AppConfig.imageLoadConcurrency` 默认5 控制）；含 LiveEventBus 配置变更监听重建协程池
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt` + `adapter/ImageCanvasAdapter.kt`
  - 上游依赖：`thread-pool-split-config`（提供 updateCacheThreadCount）+ `rss-concurrency-and-checksource-optimization`（提供 imageLoadConcurrency）

### 2.3 图片尺寸自适应（R1.8）

- [x] 2.3.1 实现 Glide RequestListener.onResourceReady 回调
  - 验证：Read 确认 ImageCanvasAdapter.ImageViewHolder 含 RequestListener.onResourceReady 实现
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 2.3.2 实现动态高度计算（height = screenWidth * bitmap.height / bitmap.width）
  - 验证：Read 确认含动态高度计算公式；含 maxHeight 限制（4 倍屏幕高度）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 2.3.3 实现默认高度（屏幕高度 60%）+ 加载失败高度（屏幕高度 40%）
  - 验证：Read 确认含默认高度 60% 计算；含加载失败时高度 40%
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

### 2.4 缩略图模式（R1.9）

- [x] 2.4.1 实现列表模式 Glide.override 限制尺寸
  - 验证：Grep 确认 ImageCanvasAdapter 中含 Glide.override(screenWidth, screenWidth * 2)
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 2.4.2 实现大图模式加载原图（点击时）
  - 验证：Read 确认 ImageDetailAdapter 中 Glide 不含 override（加载原图）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`

---

## Phase 3：大图模式能力 P0（R1.10-R1.12）

### 3.1 点击缩略图进入大图模式（R1.10）

- [x] 3.1.1 实现 ImageViewHolder.setOnClickListener 回调
  - 验证：Read 确认 ImageCanvasAdapter 含 setOnClickListener；回调中传递 position 和 sharedElement View
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 3.1.2 实现 ActivityOptions.makeSceneTransitionAnimation 共享元素动画
  - 验证：Read 确认 ImageGalleryActivity 含 ActivityOptions.makeSceneTransitionAnimation 调用；含 transitionName 匹配
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 3.1.3 实现 startActivityForResult 启动 ImageDetailActivity
  - 验证：Read 确认含 startActivityForResult 调用；传递 imageUrls 和 startIndex
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 3.1.4 实现 Glide.preload 预热当前+相邻2张 + 共享元素动画降级（V2 B-5 新增）
  - 验证：Grep 确认 ImageCanvasAdapter.ImageViewHolder 含 Glide.preload 调用；预热当前图片 + 前后各 1 张（共 3 张）；含共享元素动画降级逻辑（图片未加载完成时降级为普通 Activity 跳转，无共享元素动画）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` + `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`
  - 降级策略：onItemClick 回调中检查 `imageView.drawable == null` 或 `imageView.drawable is PlaceholderDrawable`，若未加载完成则使用 `startActivity(intent)`（无 options.toBundle()）；若已加载完成则使用 `startActivityForResult(intent, REQUEST_DETAIL, options.toBundle())`
  - 日志模板：`AppLog.put("SharedElement: preload position=$position adjacent=${position-1},${position+1}")`

### 3.2 ViewPager2 左右滑动 + 初始定位（R1.11）

- [x] 3.2.1 配置 ViewPager2 orientation=horizontal
  - 验证：Read 确认 ImageDetailActivity 含 viewPager2.orientation = ViewPager2.ORIENTATION_HORIZONTAL
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

- [x] 3.2.2 实现 ViewPager2.setCurrentItem(startIndex, false) 初始定位
  - 验证：Read 确认含 setCurrentItem(startIndex, false)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

### 3.3 PhotoView 缩放/旋转/长按保存（R1.12）

- [x] 3.3.1 迁移 PhotoView 双指缩放能力
  - 验证：Read 确认 ImageDetailAdapter 含 PhotoView 双指缩放配置（PhotoView.attacher）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`

- [x] 3.3.2 迁移 PhotoView 双击切换能力
  - 验证：Read 确认含 PhotoView 双击切换 scale 实现
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`

- [x] 3.3.3 迁移 PhotoView 旋转能力
  - 验证：Read 确认含旋转按钮和 PhotoView.rotation 设置
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt`

- [x] 3.3.4 迁移 PhotoView 长按保存能力（含权限请求 + V2 O-1 Android 13+ 兼容）
  - 验证：Read 确认含 setOnLongClickListener；含保存图片到相册逻辑；含权限请求分支处理（`Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU` 时请求 `READ_MEDIA_IMAGES`，Android 12 及以下请求 `WRITE_EXTERNAL_STORAGE`）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt` + `app/src/main/AndroidManifest.xml`（确认含 READ_MEDIA_IMAGES 权限声明）

### 3.5 ImageDetailActivity 状态保存（V2 B-4 新增）

- [x] 3.5.1 实现 onSaveInstanceState 保存 currentIndex
  - 验证：Read 确认 ImageDetailActivity 含 `override fun onSaveInstanceState(outState: Bundle)`；含 `outState.putInt("currentIndex", viewPager2.currentItem)`
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`
  - 日志模板：`AppLog.put("ImageDetailActivity: onSaveInstanceState currentIndex=${viewPager2.currentItem}")`

- [x] 3.5.2 实现 onCreate 从 savedInstanceState 恢复 currentIndex
  - 验证：Read 确认 ImageDetailActivity.onCreate 含 `savedInstanceState?.getInt("currentIndex", 0) ?: 0` 优先恢复逻辑；含 setCurrentItem(restoredIndex, false) 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`
  - 日志模板：`AppLog.put("ImageDetailActivity: restore currentIndex=$restoredIndex")`

- [x] 3.5.3 实现 imageUrls 通过 ImagePlay 单例共享（避免 Intent 1MB 限制）
  - 验证：Read 确认 ImageDetailActivity 不再通过 `intent.getStringArrayListExtra("imageUrls")` 读取图片 URL 列表；改为 `ImagePlay.allImageUrls` 读取（与 ImageGalleryActivity 共享同一份数据）；Grep 确认无 `putStringArrayListExtra("imageUrls", ...)` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt` + `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`
  - 注意：imageUrls 数据量大时 Intent extras 受 1MB 限制（Binder 事务缓冲区），大图集（50+ 张图片 URL）会抛 TransactionTooLargeException；改用 ImagePlay 单例持有避免此问题

---

## Phase 4：分页加载 P0（R1.13-R1.15）

### 4.1 RecyclerView 滚动监听（R1.13）

- [x] 4.1.1 实现 RecyclerView.addOnScrollListener
  - 验证：Read 确认 ImageGalleryActivity 含 recyclerView.addOnScrollListener
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 4.1.2 实现 findLastVisibleItemPosition 触发条件（剩余 3 项）
  - 验证：Read 确认含 layoutManager.findLastVisibleItemPosition()；含 totalItemCount - lastVisible <= 3 判断
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 4.2 加载下一篇图片 URL 列表（R1.14）

- [x] 4.2.1 实现 ImagePlay.appendItems() 方法（V4 B-14 修订：方法名从 appendNextArticleImages 改为 appendItems）
  - 验证：Read 确认 ImagePlay 含 appendItems 方法；含 @Synchronized 保护
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [x] 4.2.2 实现 preloadedArticles 去重机制
  - 验证：Read 确认 ImagePlay 含 preloadedArticles: MutableSet<Int>（ConcurrentHashMap.newKeySet 线程安全）；含 contains 去重判断
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

### 4.3 加载状态指示器（R1.15）

- [x] 4.3.1 实现 LoadingViewHolder（ProgressBar）
  - 验证：Read 确认 ImageCanvasAdapter 含 LoadingViewHolder；含 ProgressBar 绑定
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 4.3.2 实现 ErrorViewHolder（重试按钮）
  - 验证：Read 确认 ImageCanvasAdapter 含 ErrorViewHolder；含重试按钮点击回调
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 4.3.3 实现 NoMoreViewHolder（"没有更多了"文本）
  - 验证：Read 确认 ImageCanvasAdapter 含 NoMoreViewHolder；含文本"没有更多了"
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 4.3.4 实现 LoadState → ViewType 映射
  - 验证：Read 确认 ImageCanvasViewModel 含 LoadState sealed class；含 LOADING/SUCCESS/ERROR/NO_MORE 四种状态
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

---

## Phase 5：保留能力 P0（R1.16-R1.19）

### 5.1 ImagePlay 单例扩展（R1.16，V4 B-14：字段名核实）

- [x] 5.1.1 新增 allImageUrls: MutableStateFlow<List<ImageCanvasItem>> 字段（V3 B-6 StateFlow 封装，V4 B-14：现状不存在需新增）
  - 验证：Read 确认 ImagePlay 含 `private val _allImageUrls = MutableStateFlow<List<ImageCanvasItem>>(emptyList())`；含 `val allImageUrls: StateFlow<List<ImageCanvasItem>> = _allImageUrls.asStateFlow()`
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [x] 5.1.2 新增 loadedArticleIndices: MutableSet<Int> 字段（V4 B-14：现状不存在需新增）
  - 验证：Read 确认 ImagePlay 含 loadedArticleIndices 字段
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [x] 5.1.3 新增 appendItems(items: List<ImageCanvasItem>) 方法（V4 B-14：方法名修正，原 appendNextArticleImages 改为 appendItems）
  - 验证：Read 确认 ImagePlay 含 appendItems 方法；含 @Synchronized；含 `_allImageUrls.update { current -> current + items }`
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [x] 5.1.4 新增 clearImageCanvasState() 方法 + ImageGalleryActivity.onDestroy 调用（V2 O-3 新增）
  - 验证：Read 确认 ImagePlay 含 `@Synchronized fun clearImageCanvasState()` 方法（清空 allImageUrls/loadedArticleIndices/preloadedArticles）；Read 确认 ImageGalleryActivity.onDestroy 含 `ImagePlay.clearImageCanvasState()` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt` + `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`
  - 注意：避免 Activity 销毁后再次进入图片播放器继承上次 allImageUrls 导致显示错误
  - 日志模板：`AppLog.put("ImagePlay: clearImageCanvasState allImageUrls.size=${allImageUrls.size}")`

### 5.2 WebView 预热串行修复（R1.17，Bug2）

- [x] 5.2.1 复用现有 pendingPreheatDomains 字段实现串行队列（V4 C-3：复用源码 ImageGalleryActivity.kt:59 已有字段，不新建 preheatQueue）
  - 验证：Read 确认 ImageGalleryActivity 复用 `pendingPreheatDomains: MutableSet<String>`（已存在）；改造为串行队列（onPageFinished 后 remove 当前域名，触发下一个 loadUrl）
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 5.2.2 实现 WebViewClient.onPageFinished 串行触发下一个
  - 验证：Read 确认 onPageFinished 中调用 processNextPreheat() 串行触发
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 5.2.3 实现 CookieManager.flush() 同步 cookies
  - 验证：Read 确认 onPageFinished 中调用 CookieManager.getInstance().flush()
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 5.2.4 实现 preheatedDomains 去重
  - 验证：Read 确认 preheatedDomains: MutableSet<String>；含 contains 去重
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 5.3 Cookie/Header 复用（R1.18）

- [x] 5.3.1 实现 Glide RequestOptions 注入 Referer/Cookie
  - 验证：Grep 确认 ImageCanvasAdapter 中含 Glide RequestOptions.header("Referer", ...) 注入
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 5.3.2 实现 header 从 ImagePlay.rssSource 提取跨文章复用（V4 B-14：删除 currentPlayHeaders 引用）
  - 验证：Read 确认 header 从 `ImagePlay.rssSource` 字段提取（currentPlayHeaders 字段不存在）；ImageCanvasAdapter 中通过 rssSource.header 注入
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt` + `adapter/ImageCanvasAdapter.kt`

### 5.4 type==1 路由保留（R1.19，V4 B-13：articleStyle → record.type）

- [x] 5.4.1 验证 ReadRss.kt L24-44 路由逻辑不变 + 核查"用户主动选择网页模式"判定字段（V2 O-7 补充，V4 B-13 修订）
  - 验证：Read 确认 ReadRss.kt L24-44 含 record.type 路由（type==1 走 readNoHtml 启动 ImageGalleryActivity，type==0 走 ReadRssActivity，type==2 走 VideoPlayerActivity）；V4 B-13：articleStyle==2 字段名错误，实际路由字段为 record.type
  - V2 O-7 核查项：Read 确认"用户主动选择网页模式"的判定字段来源（可能来自 AppConfig/RssSource 配置/ReadRss 局部变量）；明确字段名和读取位置；在 design.md 数据流 1 中补充判定字段说明
  - 文件：`app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt`（仅验证，不修改）

---

## Phase 6：错误降级链 P0（R1.20）

### 6.1 四级降级链实现

- [x] 6.1.1 实现降级1：Glide 重试（清空缓存）
  - 验证：Read 确认 ImageCanvasAdapter 含 retryWithFreshCookie 函数；含 Glide.skipMemoryCache(true) 重试
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 6.1.2 实现降级2：OkHttp + Cookie 兜底
  - 验证：Read 确认含 OkHttp 直接请求图片 URL；含 sourceOriginOption + refererOption + rssSource.header 注入（V4 B-14：currentPlayHeaders 字段不存在，header 从 ImagePlay.rssSource 提取）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 6.1.3 实现降级3：WebView 即时预热
  - 验证：Read 确认含 WebView 即时加载图片 URL；onPageFinished 后 CookieManager.flush() + 重试 Glide
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 6.1.4 实现降级4：网页模式回退（alert {} DSL）
  - 验证：Read 确认含 alert {} DSL；含"是否切换到网页模式"提示；含 yesButton 跳转 ReadRssActivity
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 6.1.5 实现降级链 UI 提示（当前降级级别）
  - 验证：Read 确认 ImageCanvasAdapter 含 showFallbackHint(level) 方法；triggerFallbackChain 每级降级均调用 showFallbackHint；onResourceReady 调用 hideFallbackHint
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

---

## Phase 6.5：V3 新增阻塞点修复 P0（R1.21-R1.25，对应 B-6~B-10）

### 6.5.1 allImageUrls 并发安全改造（R1.21，V3 B-6）

- [x] 6.5.1.1 ImagePlay.allImageUrls 改用 MutableStateFlow 封装
  - 验证：Read 确认 ImagePlay 含 `private val _allImageUrls = MutableStateFlow<List<ImageCanvasItem>>(emptyList())`；含 `val allImageUrls: StateFlow<List<ImageCanvasItem>> = _allImageUrls.asStateFlow()`；Grep 确认无外部直接访问 `_allImageUrls.value =`（仅 ImagePlay 内部）
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`
  - 关联 ADR：design.md AD-09
  - 永久日志：`AppLog.putInfo(AppLog.TAG_IMAGE_PLAY, "allImageUrls: stateFlow initialized size=${_allImageUrls.value.size}")`

- [x] 6.5.1.2 实现 appendItems / clearImageCanvasState / resetForNewSource 三个 @Synchronized 方法
  - 验证：Read 确认三个方法含 `@Synchronized` 注解；含 `_allImageUrls.update { current -> current + items }` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [x] 6.5.1.3 ImageCanvasAdapter 改为读取 StateFlow 快照
  - 验证：Read 确认 ImageCanvasAdapter 含 `val snapshot: List<ImageCanvasItem> = ImagePlay.allImageUrls.value`；Grep 确认无直接访问 ImagePlay._allImageUrls
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

### 6.5.2 列表 position 与大图 imageIndex 双向映射（R1.22，V3 B-7）

- [x] 6.5.2.1 实现 listPositionToImageIndex 映射方法
  - 验证：Read 确认 ImageCanvasAdapter 含 `fun listPositionToImageIndex(listPos: Int): Int`；含遍历 items 判断 ImageCanvasItem.ImageItem 的逻辑；ArticleDivider 位置返回 -1
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`
  - 关联 ADR：design.md AD-10
  - 临时日志：`Log.d("ImageCanvasDebug", "IndexMap: listPos=$listPos -> imageIdx=$imageIdx")`

- [x] 6.5.2.2 实现 imageIndexToListPosition 反向映射方法
  - 验证：Read 确认含 `fun imageIndexToListPosition(imageIdx: Int): Int`；含遍历计数 ImageItem 逻辑
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 6.5.2.3 ImageGalleryActivity 进入大图时调用 listPositionToImageIndex 转换
  - 验证：Read 确认 onItemClick 回调中调用 `adapter.listPositionToImageIndex(listPos)` 转换为 imageIdx；Intent.putExtra("startIndex", imageIdx)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 6.5.2.4 onActivityResult 调用 imageIndexToListPosition 转换回 listPos
  - 验证：Read 确认 onActivityResult 含 `adapter.imageIndexToListPosition(imageIdx)` 转换；含 `recyclerView.scrollToPosition(listPos)` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 6.5.3 协程池重建任务处理（R1.23，V3 B-8）

- [x] 6.5.3.1 实现 onCoroutinePoolConfigChanged 方法（四步流程）
  - 验证：Read 确认 ImageCanvasViewModel 含 `fun onCoroutinePoolConfigChanged(newSize: Int)`；含 loadJob?.cancel() → coroutineExecutor.shutdown() → awaitTermination(5, SECONDS) → createExecutor(newSize) → loadNextArticle() 四步
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`
  - 关联 ADR：design.md AD-11
  - 永久日志：`AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "CoroutinePool: rebuild oldSize=$oldSize newSize=$newSize source=configChanged")`

- [x] 6.5.3.2 loadNextArticle 内部添加 ensureActive() 检查
  - 验证：Grep 确认 loadNextArticle 内含 `currentCoroutineContext().ensureActive()` 调用；位于循环或耗时操作前
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

- [x] 6.5.3.3 onCleared 添加 coroutineExecutor.shutdownNow()
  - 验证：Read 确认 onCleared 含 `coroutineExecutor.shutdownNow()` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

- [x] 6.5.3.4 注册 LiveEventBus 配置变更监听
  - 验证：Grep 确认 ImageCanvasViewModel.init 或 init 块中含 LiveEventBus.observe 配置变更事件；调用 onCoroutinePoolConfigChanged
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

### 6.5.4 跨订阅源切换 allImageUrls 清理（R1.24，V3 B-9）

- [x] 6.5.4.1 ImagePlay 新增 resetForNewSource 方法
  - 验证：Read 确认 ImagePlay 含 `@Synchronized fun resetForNewSource()`；方法体清空 _allImageUrls.value + loadedArticleIndices + preloadedArticles
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`
  - 关联 ADR：design.md AD-12
  - 永久日志：`AppLog.putInfo(AppLog.TAG_IMAGE_PLAY, "resetForNewSource cleared=$clearedSize sourceId=${rssSource?.id}")`

- [x] 6.5.4.2 ImagePlay.init 首行调用 resetForNewSource
  - 验证：Read 确认 ImagePlay.init(rssSource, rssArticles, position) 方法首行调用 resetForNewSource()
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt`

- [ ] 6.5.4.3 ImageGalleryActivity 换源按钮调用 resetForNewSource
  - 验证：Read 确认 ImageGalleryActivity 含换源场景调用 ImagePlay.resetForNewSource()（若 UI 有换源入口）
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`
  - 注意：若本期无换源 UI 入口，仅保留 init() 调用即可，换源按钮任务推迟到 P2

### 6.5.5 ViewHolder 复用闪烁修复（R1.25，V3 B-10）

- [x] 6.5.5.1 onBindViewHolder 添加默认高度重置逻辑
  - 验证：Read 确认 onBindViewHolder 含 `val lp = holder.itemView.layoutParams; lp.height = defaultHeight; holder.itemView.layoutParams = lp` 重置（在 Glide.load 之前）
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`
  - 关联 ADR：design.md AD-13
  - 临时日志：`Log.d("ImageCanvasDebug", "HeightUpdate: position=$position oldH=$oldH newH=$newH bitmapW=$bw bitmapH=$bh")`

- [x] 6.5.5.2 onViewRecycled 添加 Glide.clear 调用
  - 验证：Grep 确认 ImageCanvasAdapter 含 `override fun onViewRecycled(holder: ImageViewHolder)`；含 `Glide.with(holder.itemView.context).clear(holder.imageView)` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`
  - 永久日志：`AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "onViewRecycled position=${holder.bindingAdapterPosition} hashCode=${holder.hashCode()}")`

- [x] 6.5.5.3 ImageGalleryActivity 配置 setHasFixedSize(false)
  - 验证：Read 确认 ImageGalleryActivity 含 `recyclerView.setHasFixedSize(false)` 调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 6.5.5.4 onLoadFailed 时设置错误高度（屏幕高度 40%）
  - 验证：Read 确认 RequestListener.onLoadFailed 含 `lp.height = (screenHeight * 0.4).toInt()` 设置
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

---

## Phase 7：架构风格对齐 P1（R2.1-R2.5）

### 7.1 TitleBar 颜色硬编码改主题色（R2.1）

- [x] 7.1.1 移除 ImageGalleryActivity.initTitleBar() 中硬编码颜色
  - 验证：Grep 确认 ImageGalleryActivity 无 Color.parseColor("#80000000") / Color.WHITE 硬编码
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

- [x] 7.1.2 改用 TitleBar 默认主题机制（primaryColor / primaryTextColor）
  - 验证：Read 确认 ImageGalleryActivity 使用 TitleBar 默认主题；不显式设置背景色
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 7.2 AlertDialog 改走 alert DSL（R2.2）

- [x] 7.2.1 长按菜单从 AlertDialog.Builder().setItems() 改为 alert {} DSL
  - 验证：Grep 确认 ImageDetailActivity onImageLongClick 使用 alert("图片操作") { items(...) }；无 AlertDialog.Builder 直接调用
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

- [x] 7.2.2 错误兜底从 tvError+btnRetry 改为 alert {} 四级降级
  - 验证：Read 确认 ImageGalleryActivity onWebModeFallback 使用 alert("图片加载失败") { positiveButton/negativeButton }
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 7.3 按钮背景统一 bg_overlay_button（R2.3）

- [x] 7.3.1 旋转工具栏容器和按钮改用 bg_overlay_button
  - 验证：Grep 确认 activity_image_detail.xml 无 bg_rotate_toolbar 引用；改用 bg_overlay_button
  - 文件：`app/src/main/res/layout/activity_image_detail.xml`（新建）

### 7.4 沉浸式 API 统一（R2.4）

- [x] 7.4.1 toggleImmersive() 改用 WindowInsetsControllerCompat（V2 O-4 补充 minSdk 兼容）
  - 验证：Grep 确认 ImageDetailActivity 无 window.setFlags(FLAG_LAYOUT_NO_LIMITS) / systemUiVisibility 残留
  - V2 O-4 补充：使用 `WindowCompat.setDecorFitsSystemProperties(window, false)` + `WindowInsetsControllerCompat(window, window.decorView)` 组合（API 21+ 兼容，项目 minSdk=23 满足）
  - 参考视频播放器现有实现（如有）：Grep `WindowInsetsControllerCompat` 在 VideoPlayerActivity 中的用法
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

### 7.5 圆角规范统一 12dp（R2.5）

- [x] 7.5.1 旋转工具栏圆角从 24dp 改为 12dp
  - 验证：Grep 确认图片模块内部圆角统一 12dp；bg_overlay_button.xml 含 12dp 圆角
  - 文件：`app/src/main/res/drawable/bg_overlay_button.xml`

---

## Phase 8：体验优化 P1（R2.6-R2.9）

### 8.1 大图模式返回列表保持点击位置可见（R2.6）

- [x] 8.1.1 实现 ImageDetailActivity.setResult 传递 currentIndex
  - 验证：Read 确认 ImageDetailActivity 返回时调用 setResult(RESULT_OK, Intent().putExtra("currentIndex", viewPager2.currentItem))
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

- [x] 8.1.2 实现 ImageGalleryActivity.onActivityResult 接收并 scrollToPosition
  - 验证：Read 确认 ImageGalleryActivity 含 onActivityResult；含 recyclerView.scrollToPosition(currentIndex)
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

### 8.2 文章边界分隔符（R2.7）

- [x] 8.2.1 实现 ArticleDividerViewHolder（"—— 下一篇 ——"分隔条）
  - 验证：Read 确认 ImageCanvasAdapter 含 ArticleDividerViewHolder；显示"—— 下一篇 ——"文本
  - 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

- [x] 8.2.2 实现 allImageUrls 中的文章边界标记
  - 验证：Read 确认 allImageUrls 中插入特殊标记（如 null 或 ArticleDivider 数据类）表示文章边界
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

### 8.3 大图模式 TitleBar 显示页码（R2.8）

- [x] 8.3.1 实现 TitleBar 页码显示逻辑（"文章N/M 图片X/Y"）
  - 验证：Read 确认 ImageDetailActivity 含 TitleBar 页码更新逻辑；onPageSelected 中更新文本
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt`

### 8.4 协程取消机制（R2.9）

- [x] 8.4.1 实现 loadJob?.cancel() 在新加载请求前取消
  - 验证：Read 确认 ImageCanvasViewModel.loadNextArticle() 入口含 loadJob?.cancel()
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

- [x] 8.4.2 实现 isLaunching 标志位防止重复触发
  - 验证：Read 确认 ImageCanvasViewModel 含 @Volatile var isLaunching；loadNextArticle 入口判断
  - 文件：`app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt`

---

## Phase 9：文档同步与验证

### 9.1 文档同步

- [x] 9.1.1 同步更新 docs/INDEX.md（设计状态 → 实施中 → 已完成）
  - 验证：Read 确认 INDEX.md "活跃 Specs" 表 image-player-vertical-canvas-optimization 行状态更新
  - 文件：`docs/INDEX.md`

- [x] 9.1.2 同步更新 docs/specs/image-player-vertical-canvas-optimization/README.md 状态
  - 验证：Read 确认 README.md 状态字段更新（🔄 设计中 → 🔄 实施中 → ✅ 已完成）
  - 文件：`docs/specs/image-player-vertical-canvas-optimization/README.md`

- [x] 9.1.3 同步更新 assets/updateLog.md（基于 git diff 提炼变更条目）
  - 验证：Read 确认 updateLog.md 含图片播放器垂直画布重构变更条目；面向用户语言描述
  - 文件：`assets/updateLog.md`

### 9.2 真机验证

- [ ] 9.2.1 编译安装测试包到真机
  - 验证：使用 `ai_tests/scripts/quick_build_install.py` 编译安装测试包（io.legado.miss.app.debug）
  - 文件：`ai_tests/scripts/quick_build_install.py`

- [ ] 9.2.2 验证场景1-3：列表模式（垂直滚动 / 快速滚动暂停 / 加载失败重试）
  - 验证：真机执行场景1-3；logcat Grep "ImageCanvasAdapter.*onBindViewHolder|Glide.*pauseRequests|onLoadFailed" 确认触发
  - 文件：`ai_tests/scripts/l2_verify_image_player.py`（新建）

- [ ] 9.2.3 验证场景4-6：大图模式（共享元素动画 / 左右滑动 / 返回状态同步）
  - 验证：真机执行场景4-6；logcat Grep "ImageDetailActivity.*setCurrentItem|scrollToPosition" 确认触发
  - 文件：`ai_tests/scripts/l2_verify_image_player.py`

- [ ] 9.2.4 验证场景7-9：分页加载（自动加载下一篇 / 没有更多了 / 加载失败重试）
  - 验证：真机执行场景7-9；logcat Grep "loadNextArticle|preloadNextArticleImages|NO_MORE" 确认触发
  - 文件：`ai_tests/scripts/l2_verify_image_player.py`

- [ ] 9.2.5 验证场景10-13：保留能力（多域名串行预热 / 四级降级链 / type==1 路由 / 协程取消）（V4 B-13：articleStyle==2 → type==1）
  - 验证：真机执行场景10-13；logcat Grep "preheat.*serial|retryWithFreshCookie|record.*type.*1|loadJob.*cancel" 确认触发
  - 文件：`ai_tests/scripts/l2_verify_image_player.py`

- [ ] 9.2.6 验证场景14-15：架构风格（与视频播放器视觉一致 / 主题切换）
  - 验证：真机执行场景14-15；用 dump_ui_safe_v2.py 抓取 TitleBar/按钮 DOM 对比
  - 文件：`ai_tests/scripts/dump_ui_safe_v2.py`

- [ ] 9.2.7 验证场景16-17：边界场景（超长图 / 加载中切换主题）
  - 验证：真机执行场景16-17；logcat 确认无 OOM
  - 文件：`ai_tests/scripts/l2_verify_image_player.py`

### 9.3 调试日志清理

- [x] 9.3.1 Grep 确认无 android.util.Log.d / android.util.Log.e 残留
  - 验证：Grep "android.util.Log.d|android.util.Log.e|Log.d(|Log.e(" 确认图片模块无残留；统一用 AppLog.put
  - 文件：`app/src/main/java/io/legado/app/ui/image/`

### 9.4 用户验收

- [ ] 9.4.1 强制检查点 2：AskUserQuestion 等待用户验收
  - 验证：AskUserQuestion 响应记录写入项目记忆；用户选择"通过"
  - 文件：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`

---

## R 编号 ↔ 任务编号映射表

| R 编号 | 任务编号 | 任务描述 | 优先级 |
|--------|---------|---------|--------|
| R1.1 | 1.1.1 / 1.1.2 / 1.1.3 | 重写 ImageGalleryActivity 主架构 | P0 |
| R1.2 | 1.2.1 / 1.2.2 / 1.2.3 | 新建 ImageCanvasAdapter | P0 |
| R1.3 | 1.3.1 / 1.3.2 / 1.3.3 / 1.3.4 | 新建 ImageDetailActivity | P0 |
| R1.4 | 1.4.1 / 1.4.2 / 1.4.3 | 新建 ImageDetailAdapter | P0 |
| R1.5 | 1.5.1 / 1.5.2 / 1.5.3 / 1.5.4 | 新建 ImageCanvasViewModel | P0 |
| R1.6 | 2.1.1 / 2.1.2 | 单 RecyclerView 垂直长画布 | P0 |
| R1.7 | 2.2.1 / 2.2.2 | 多线程并行加载 | P0 |
| R1.8 | 2.3.1 / 2.3.2 / 2.3.3 | 图片尺寸自适应 | P0 |
| R1.9 | 2.4.1 / 2.4.2 | 缩略图模式 | P0 |
| R1.10 | 3.1.1 / 3.1.2 / 3.1.3 | 点击缩略图进入大图模式 | P0 |
| R1.11 | 3.2.1 / 3.2.2 | ViewPager2 左右滑动 + 初始定位 | P0 |
| R1.12 | 3.3.1 / 3.3.2 / 3.3.3 / 3.3.4 | PhotoView 缩放/旋转/长按保存 | P0 |
| R1.13 | 4.1.1 / 4.1.2 | RecyclerView 滚动监听 | P0 |
| R1.14 | 4.2.1 / 4.2.2 | 加载下一篇图片 URL 列表 | P0 |
| R1.15 | 4.3.1 / 4.3.2 / 4.3.3 / 4.3.4 | 加载状态指示器 | P0 |
| R1.16 | 5.1.1 / 5.1.2 / 5.1.3 | ImagePlay 单例扩展 | P0 |
| R1.17 | 5.2.1 / 5.2.2 / 5.2.3 / 5.2.4 | WebView 预热串行修复 | P0 |
| R1.18 | 5.3.1 / 5.3.2 | Cookie/Header 复用 | P0 |
| R1.19 | 5.4.1 | type==1 路由保留（V4 B-13：articleStyle → record.type） | P0 |
| R1.20 | 6.1.1 / 6.1.2 / 6.1.3 / 6.1.4 / 6.1.5 | 图片加载失败四级降级链 | P0 |
| R1.21 | 6.5.1.1 / 6.5.1.2 / 6.5.1.3 | allImageUrls 并发安全（V3 B-6） | P0 |
| R1.22 | 6.5.2.1 / 6.5.2.2 / 6.5.2.3 / 6.5.2.4 | 列表 position 与大图 imageIndex 双向映射（V3 B-7） | P0 |
| R1.23 | 6.5.3.1 / 6.5.3.2 / 6.5.3.3 / 6.5.3.4 | 协程池重建任务处理（V3 B-8） | P0 |
| R1.24 | 6.5.4.1 / 6.5.4.2 / 6.5.4.3 | 跨订阅源切换 allImageUrls 清理（V3 B-9） | P0 |
| R1.25 | 6.5.5.1 / 6.5.5.2 / 6.5.5.3 / 6.5.5.4 | ViewHolder 复用闪烁修复（V3 B-10） | P0 |
| R2.1 | 7.1.1 / 7.1.2 | TitleBar 颜色硬编码改主题色 | P1 |
| R2.2 | 7.2.1 / 7.2.2 | AlertDialog 改走 alert DSL | P1 |
| R2.3 | 7.3.1 | 按钮背景统一 bg_overlay_button | P1 |
| R2.4 | 7.4.1 | 沉浸式 API 统一 | P1 |
| R2.5 | 7.5.1 | 圆角规范统一 12dp | P1 |
| R2.6 | 8.1.1 / 8.1.2 | 大图模式返回列表保持点击位置 | P1 |
| R2.7 | 8.2.1 / 8.2.2 | 文章边界分隔符 | P1 |
| R2.8 | 8.3.1 | 大图模式 TitleBar 显示页码 | P1 |
| R2.9 | 8.4.1 / 8.4.2 | 协程取消机制 | P1 |

---

## AOAdapt 日志模板（V3 修订：严格对照 logging-during-refactoring.md 规范 10 类必加场景）

### 模块 Tag 常量（V3 新增，对应 logging_rules.md）

| Tag 常量 | 值 | 适用模块 |
|---------|---|---------|
| `AppLog.TAG_IMAGE_CANVAS` | "ImageCanvas" | ImageGalleryActivity / ImageCanvasAdapter / ImageCanvasViewModel |
| `AppLog.TAG_IMAGE_DETAIL` | "ImageDetail" | ImageDetailActivity / ImageDetailAdapter |
| `AppLog.TAG_IMAGE_PLAY` | "ImagePlay" | ImagePlay 单例（allImageUrls/loadedArticleIndices/clearImageCanvasState） |
| `ImageCanvasDebug`（临时） | "ImageCanvasDebug" | 临时调试日志，验证后 Grep 一次性移除 |

### 永久日志（AppLog.putDebugWithTag，写入文件用户可查看，验证后保留）

> 永久日志覆盖规范 10 类场景中的：错误处理路径、状态切换、协程取消/完成、降级链触发、配置变更、生命周期关键节点、网络请求关键节点

| # | 规范场景 | 日志模板 | 触发时机 |
|---|---------|---------|---------|
| 1 | **错误处理路径**（场景2） | `AppLog.putError(AppLog.TAG_IMAGE_CANVAS, "Glide onLoadFailed position=$position reason=${e.message}\nstack=${e.stackTraceToString().take(5)}")` | ImageCanvasAdapter.RequestListener.onLoadFailed |
| 2 | **错误处理路径-降级链**（场景2） | `AppLog.putError(AppLog.TAG_IMAGE_CANVAS, "Fallback triggered level=$level position=$position url=/path/${urlHash} reason=${reason}")` | 四级降级链每级触发 |
| 3 | **错误处理路径-协程异常**（场景2） | `AppLog.putError(AppLog.TAG_IMAGE_CANVAS, "loadNextArticle failed articleIndex=$nextIndex e=${e::class.simpleName} msg=${e.message}")` | loadNextArticle catch 块 |
| 4 | **状态切换-LoadState**（场景1） | `AppLog.putWarn(AppLog.TAG_IMAGE_CANVAS, "LoadState: $oldState -> $newState articleIndex=$articleIndex")` | ImageCanvasViewModel LoadState 转换 |
| 5 | **状态切换-降级级别**（场景1） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "Fallback level: $oldLevel -> $newLevel position=$position")` | 降级链级别切换 |
| 6 | **协程取消**（场景1） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "loadNextArticle: cancel previous job articleIndex=$nextIndex")` | loadJob?.cancel() 调用 |
| 7 | **协程完成**（场景1） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "loadNextArticle: success articleIndex=$nextIndex loadedCount=${imageUrls.size} costMs=$costMs")` | loadNextArticle 加载完成 |
| 8 | **配置变更-协程池重建**（场景8） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "CoroutinePool: rebuild oldSize=$oldSize newSize=$newSize source=$eventSource")` | LiveEventBus 配置变更监听触发 |
| 9 | **配置变更-图片加载并发**（场景8） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "GlideConcurrency: rebuild oldSize=$oldSize newSize=$newSize")` | AppConfig.imageLoadConcurrency 变更 |
| 10 | **生命周期-Activity**（场景7） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "ImageGalleryActivity: onCreate hashCode=${this.hashCode()} sourceId=$sourceId articleCount=${articles.size}")` | ImageGalleryActivity.onCreate |
| 11 | **生命周期-Activity 销毁**（场景7） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "ImageGalleryActivity: onDestroy hashCode=${this.hashCode()} clearedAllImageUrls=${size}")` | ImageGalleryActivity.onDestroy + clearImageCanvasState |
| 12 | **生命周期-ViewModel**（场景7） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "ImageCanvasViewModel: onCleared hashCode=${this.hashCode()} loadJobActive=${loadJob?.isActive}")` | ImageCanvasViewModel.onCleared |
| 13 | **生命周期-Adapter**（场景7） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "ImageCanvasAdapter: onViewRecycled position=$position hashCode=${holder.hashCode()}")` | onViewRecycled |
| 14 | **网络请求关键节点-RssFetch**（场景3） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "RssFetch: start articleIndex=$idx url=/path/${urlHash}")` | Rss.getContentAwait 调用前 |
| 15 | **网络请求关键节点-RssFetch 完成**（场景3） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "RssFetch: end articleIndex=$idx costMs=$costMs code=$code imgCount=$count")` | Rss.getContentAwait 完成 |
| 16 | **网络请求-WebView 预热**（场景3） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "Preheat: start queueSize=${pendingPreheatDomains.size} currentDomain=domain_${idx}")` | startSerialPreheat 入口（V4 C-3：preheatQueue → pendingPreheatDomains） |
| 17 | **网络请求-WebView 预热完成**（场景3） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "Preheat: domain_${idx} completed remaining=${pendingPreheatDomains.size}")` | onPageFinished 单域名完成（V4 C-3：preheatQueue → pendingPreheatDomains） |
| 18 | **网络请求-WebView 全部完成**（场景3） | `AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS, "Preheat: all completed totalCount=${preheatedDomains.size}")` | 全部预热完成 |
| 19 | **状态切换-ImagePlay 重置**（场景1） | `AppLog.putInfo(AppLog.TAG_IMAGE_PLAY, "resetForNewSource cleared=${allImageUrls.size} sourceId=$newSourceId")` | 切换订阅源时调用 resetForNewSource |

### 临时日志（Log.d + ImageCanvasDebug Tag，仅 logcat，验证后 Grep 一次性移除）

> 临时日志覆盖规范 10 类场景中的：触摸事件流转、类型转换、方法入口/出口（非错误路径）

| # | 规范场景 | 日志模板 | 触发时机 |
|---|---------|---------|---------|
| T1 | **触摸事件-点击缩略图**（场景9） | `Log.d("ImageCanvasDebug", "onItemClick listPosition=$listPos imageIndex=$imageIdx articleIndex=$articleIdx")` | ImageViewHolder.setOnClickListener |
| T2 | **触摸事件-长按保存**（场景9） | `Log.d("ImageCanvasDebug", "onLongClick position=$position action=save imageIndex=$imageIdx")` | ImageDetailAdapter setOnLongClickListener |
| T3 | **触摸事件-PhotoView 缩放**（场景9） | `Log.d("ImageCanvasDebug", "PhotoView: scale=$scale rotation=$rotation position=$position")` | PhotoViewAttacher.onScaleChange |
| T4 | **触摸事件-滚动状态**（场景9） | `Log.d("ImageCanvasDebug", "Scroll: state=$newState lastVisible=$lastVisible total=$total threshold=$threshold")` | RecyclerView.OnScrollListener.onScrollStateChanged |
| T5 | **类型转换-String body→List<String>**（场景5，V4 B-11/B-12：Rss.getContentAwait 返回 String，RssImage 类不存在） | `Log.d("ImageCanvasDebug", "TypeConvert: body length=${body.length} -> List<String> size=$m articleIndex=$idx")` | parseImageUrls 解析后 |
| T6 | **类型转换-ImageCanvasItem 过滤**（场景5） | `Log.d("ImageCanvasDebug", "FilterImageItems: total=${items.size} filtered=${imageItems.size} dividers=${dividerCount}")` | ImageDetailActivity 过滤 ImageItem |
| T7 | **索引映射-双向转换**（场景5） | `Log.d("ImageCanvasDebug", "IndexMap: listPos=$listPos -> imageIdx=$imageIdx (and reverse)")` | listPositionToImageIndex / imageIndexToListPosition |
| T8 | **方法入口-bindViewHolder**（调试） | `Log.d("ImageCanvasDebug", "onBindViewHolder position=$position viewType=$viewType itemCount=$total")` | onBindViewHolder 入口 |
| T9 | **方法出口-bindViewHolder 完成**（调试） | `Log.d("ImageCanvasDebug", "onBindViewHolder done position=$position costMs=$costMs")` | onBindViewHolder 完成 |
| T10 | **方法入口-高度更新**（调试） | `Log.d("ImageCanvasDebug", "HeightUpdate: position=$position oldH=$oldH newH=$newH bitmapW=$bw bitmapH=$bh")` | RequestListener.onResourceReady 高度更新 |

### 日志内容脱敏规范（V3 强制）

| 字段类型 | 脱敏格式 | 示例 |
|---------|---------|------|
| URL | `/path/${urlHash}` 路径模式 + URL 哈希 | `/images/abc123` |
| 域名 | `domain_${idx}` 编号 | `domain_0` / `domain_1` |
| 源名称 | `sourceId=${id}` 仅 ID | `sourceId=42` |
| 文章标题 | `titleLength=${n}` 仅长度 | `titleLength=15` |
| cookie/token/key | `***` 完全隐藏 | `cookie=***` |
| 异常调用栈 | `e.stackTraceToString().take(5)` 前 5 帧 | `at foo.bar(ImageCanvasAdapter.kt:42)` |

### 日志清理流程（V3 强制，遵循 logging-during-refactoring.md §调试日志清理）

1. 实施期间：临时日志统一 Tag `ImageCanvasDebug`，使用 `Log.d`（不写入文件）
2. 真机验证通过后：
   ```bash
   # 使用 Grep 工具搜索临时日志 Tag
   # pattern: ImageCanvasDebug, type: kt, path: app/src/main/java/io/legado/app/ui/image/
   # 一次性移除所有 Log.d("ImageCanvasDebug", ...) 调用
   ```
3. 重新编译确认无残留：`Grep "ImageCanvasDebug" type:kt` 返回 0 结果
4. 永久日志（AppLog.putDebugWithTag）全部保留，不清理

### 日志验证脚本（V3 新增）

实施完成后用以下脚本验证日志覆盖度：

```bash
# 按模块 Tag 过滤 logcat
ai_tests\venv\Scripts\python.exe ai_tests/scripts/collect_app_log.py --tag ImageCanvas

# 验证 10 类场景是否全部触发
# 场景1（状态切换）: Grep "LoadState:|Fallback level:|resetForNewSource"
# 场景2（错误处理）: Grep "onLoadFailed|Fallback triggered|loadNextArticle failed"
# 场景3（网络请求）: Grep "RssFetch:|Preheat:"
# 场景7（生命周期）: Grep "onCreate|onDestroy|onCleared|onViewRecycled"
# 场景8（配置变更）: Grep "CoroutinePool:|GlideConcurrency:"
# 场景9（触摸事件）: Grep "onItemClick|onLongClick|PhotoView:|Scroll:"
# 场景5（类型转换）: Grep "TypeConvert:|FilterImageItems:|IndexMap:"
```
