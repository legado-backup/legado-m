# 内置图片播放器垂直画布优化方案 design

> 状态：🔄 设计中（V4 源码对齐修订完成，待用户审查）
> 任务类型：OpenSpec 四文档之一（技术设计 + ADR + 数据流 + 文件变更）
> 上游依赖：
> - [player-review-and-optimization](../player-review-and-optimization/design.md)（图片播放器审查与优化整合，本 spec 取代其图片部分）
> - [thread-pool-split-config](../thread-pool-split-config/spec.md)（提供 `AppConfig.updateCacheThreadCount` 配置）
> - [rss-concurrency-and-checksource-optimization](../rss-concurrency-and-checksource-optimization/spec.md)（提供 `AppConfig.imageLoadConcurrency` 配置）

## 1. 技术方案总览

### 1.1 架构演进图

```
[现有架构]                              [新架构]

ImageGalleryActivity                    ImageGalleryActivity（重写）
 ├─ ImageArticlePagerAdapter            ├─ RecyclerView（垂直长画布）
 │   └─ ViewPager2 (vertical)           │   └─ ImageCanvasAdapter（新建）
 │       └─ ImagePageAdapter            │       ├─ 图片项 ViewHolder
 │           └─ ViewPager2 (horizontal) │       ├─ 加载状态 ViewHolder
 │               └─ PhotoView           │       └─ 文章分隔符 ViewHolder
 │                                       ├─ ImageCanvasViewModel（新建）
 └─ ImagePlay 单例                      └─ ImagePlay 单例（扩展）
                                           └─ allImageUrls / loadedArticleIndices

                                       ImageDetailActivity（新建，大图模式）
                                        ├─ ViewPager2 (horizontal)
                                        │   └─ ImageDetailAdapter（新建）
                                        │       └─ PhotoView（迁移自 ImagePageAdapter）
                                        └─ ActivityOptions 共享元素动画
```

### 1.2 核心技术决策摘要

| 决策点 | 选定方案 | 否决方案 | 关键理由 |
|--------|---------|---------|---------|
| 列表容器 | 单 RecyclerView + LinearLayoutManager | 双 ViewPager2 嵌套 / LazyColumn | 完全扁平化，消除嵌套生命周期复杂度 |
| 大图容器 | 独立 ImageDetailActivity + ViewPager2 | Fragment 嵌套 / 直接复用 ImagePageAdapter | 生命周期清晰 + 共享元素动画过渡 |
| 图片加载 | Glide 异步（复用 AppConfig.imageLoadConcurrency 默认5）+ ViewModel 协程并发（复用 AppConfig.updateCacheThreadCount 默认16） | Coil / Glide 同步 / 硬编码 4 并发 | 复用现有 Glide 集成 + 上游 spec 协程池配置 + 用户可配置 |
| 分页加载 | RecyclerView.OnScrollListener + 协程 async | Paging3 | 简单可控，匹配现有 ImagePlay 单例模型 |
| 状态传递 | ImagePlay 单例扩展（allImageUrls/loadedArticleIndices） | ViewModel + SavedStateHandle | 复用现有跨 Activity 状态传递模式 |
| 模式切换 | 共享元素动画（ActivityOptions） | 无动画 / Fragment 切换 | 平滑过渡，对齐小红书/抖音体验 |

---

## 2. ADR Y-Statement 决策记录

### AD-01：列表容器架构选择

**Context（背景与驱动力）**
- 现有架构：ImageGalleryActivity 使用 ImageArticlePagerAdapter（外层 ViewPager2 vertical）+ ImagePageAdapter（内层 ViewPager2 horizontal），双 ViewPager2 嵌套
- 痛点：Bug1 适配器复用失效（if/else 两分支都新建 adapter）/ Bug2 WebView 预热 forEach loadUrl 循环覆盖 / Bug3 loadArticleContent 协程未取消
- 用户诉求："所有图片按顺序在一个画布按上到下依次多线程去请求加载"

**Decision（决策）**
采用**单 RecyclerView + LinearLayoutManager** 垂直长画布架构，所有文章的图片扁平化到同一个 RecyclerView，按"文章1图1, 文章1图2, ..., 文章2图1, ..."顺序排列。

**Consequences（结果与影响）**
- 正向：消除双 ViewPager2 嵌套的生命周期复杂度；RecyclerView 复用机制成熟；多线程并行加载所有图片
- 负向：图片高度预测复杂（需 RequestListener.onResourceReady 动态获取尺寸）；跨文章图片混排可能误导用户（用文章分隔符缓解）
- 风险：内存压力增加（同时加载多张图片），用 Glide.override + setItemViewCacheSize(2) 控制
- **协程池配置复用**：列表模式 Glide 图片加载复用 `AppConfig.imageLoadConcurrency`（默认5，已由 LegadoGlideModule.setSourceExecutor 应用到 Glide 自带线程池）；ViewModel 协程并发（Rss.getContentAwait 解析文章图片 URL）复用 `AppConfig.updateCacheThreadCount`（默认16，语义匹配：缓存文章图片 URL 列表）；监听 LiveEventBus 配置变更事件运行时重建协程池；上游依赖 `thread-pool-split-config` + `rss-concurrency-and-checksource-optimization`

**Alternatives Considered（已考虑的替代方案）**
- 方案A 保留双 ViewPager2 仅修复 Bug：否决，未满足"重构交互架构"诉求
- 方案B 外层改 RecyclerView + 内层保留 ViewPager2：否决，本质仍是嵌套
- 方案H LazyColumn（Compose）：否决，与现有 View 体系割裂

**Y-Stance（立场声明）**
我们选择 RecyclerView 而非保留 ViewPager2，因为用户的核心诉求是"画布式浏览"而非"翻页式浏览"，且 RecyclerView 在多线程并行加载 + 状态指示器 + 文章分隔符等场景下的扩展性远优于 ViewPager2。

---

### AD-02：大图模式容器选择

**Context**
- 用户诉求："当用户点击其中一个图片的时候，再使用现在的这种左右滚动式的播放查看"
- 现有 ImagePageAdapter 已实现 ViewPager2 + PhotoView 缩放/旋转/长按能力，但与 ImageArticlePagerAdapter 强耦合

**Decision**
新建**独立 ImageDetailActivity + ImageDetailAdapter**（基于现有 ImagePageAdapter 逻辑精简），剥离与 ImageArticlePagerAdapter 的耦合，保留 PhotoView 缩放/旋转/长按能力。从列表模式通过 **ActivityOptions.makeSceneTransitionAnimation** 共享元素动画过渡到大图模式。

**Consequences**
- 正向：Activity 生命周期清晰；共享元素动画平滑过渡；PhotoView 能力完整保留
- 负向：Activity 切换开销（约 50-100ms）；状态同步需通过 setResult 传递 currentIndex
- 风险：图片尚未加载完成时共享元素动画可能闪烁（用 Glide.preload 预热前 3 张缓解）

**Alternatives Considered**
- 方案D Fragment 嵌套在 ImageGalleryActivity 内：否决，Fragment 生命周期复杂
- 方案F 直接复用 ImagePageAdapter 不拆分：否决，带入双 ViewPager2 嵌套历史包袱

**Y-Stance**
我们选择独立 Activity 而非 Fragment，因为 Activity 生命周期时序清晰可控，且共享元素动画是用户体验的关键加分项，Fragment 嵌套的复杂度与本期重构范围不匹配。Fragment 方案作为 P2 长期优化保留。

---

### AD-03：图片高度自适应策略

**Context**
- 垂直画布要求每张图片在加载前已知高度，否则会布局抖动
- 部分 CDN 返回的图片无 Content-Type 中的尺寸信息，需加载后才能获取

**Decision**
采用**宽度填满 + 高度按宽高比动态计算**策略：
- 默认高度：屏幕高度的 60%（加载期间占位）
- Glide RequestListener.onResourceReady 回调获取原始 Bitmap 尺寸
- 动态计算：`height = screenWidth * bitmap.height / bitmap.width`
- 通过 ViewGroup.LayoutParams 更新 ViewHolder 高度
- 加载失败时高度固定为屏幕高度的 40%（显示错误图标 + 重试按钮）

**Consequences**
- 正向：图片宽高比正确，无变形；适配所有图片格式
- 负向：加载期间可能有轻微抖动（默认高度 → 实际高度切换）
- 风险：超长图（高度 > 5 倍屏幕高度）可能导致 RecyclerView 单个 ViewHolder 占用过高，限制最大高度为屏幕高度的 4 倍（超出部分滚动查看）

**Alternatives Considered**
- 方案I 固定高度 16:9：否决，扭曲图片宽高比
- Glide preload 先获取尺寸再加载：增加一次网络请求，性能损耗

**Y-Stance**
我们选择动态高度计算而非固定高度，因为图片订阅源的图片宽高比差异极大（漫画长图 vs 方形头像），固定高度会导致严重视觉变形，动态计算虽有轻微抖动但可通过 placeholder 缓解。

---

### AD-04：分页加载触发策略

**Context**
- 用户诉求："一个画布加载所有当看到最后一个用户下拉的时候开始下一个列表内容的加载"
- 现有 preloadNextArticle 仅预加载 URL 列表，受 ViewPager2 缓存限制

**Decision**
采用**RecyclerView.OnScrollListener + LinearLayoutManager.findLastVisibleItemPosition** 触发策略：
- 触发条件：剩余未可见项数 ≤ 3（即 `totalItemCount - lastVisibleItemPosition <= 3`）
- 调用 `ImageCanvasViewModel.loadNextArticle()` 协程加载下一篇图片 URL
- preloadedArticles: MutableSet<Int> 去重（按文章索引）
- 加载状态指示器：加载中（ProgressBar）/ 加载失败（重试按钮）/ 没有更多了（文本）
- 协程取消：loadJob?.cancel() 在新加载请求前取消上一个

**Consequences**
- 正向：用户下拉到底部自动加载，无需手动操作；协程取消避免重复加载
- 负向：触发阈值 3 项可能过早（用户尚未真正到达底部）；可配置为常量 `PAGINATION_THRESHOLD = 3`
- 风险：快速滚动时可能连续触发多次加载，用 loadJob?.cancel() + isLaunching 标志位控制

**Alternatives Considered**
- 方案G Paging3 库：否决，引入新概念与现有模型不匹配
- 滚动停止后触发：否决，用户体验差（必须停下来才加载）

**Y-Stance**
我们选择滚动监听 + 协程取消而非 Paging3，因为现有的 ImagePlay 单例 + Rss.getContentAwait 协程模型已足够支撑分页加载，引入 Paging3 反而增加学习成本和架构割裂。

---

### AD-05：WebView 预热串行化修复

**Context**
- 现有 Bug2：`preheatedDomains.forEach { preheatWebView.loadUrl(it) }` 循环覆盖，仅最后一个域名真正预热
- 多域名 CDN 场景（站点A/站点B/站点C）需逐个预热，否则 Glide 加载会失败（Cloudflare 类防护系统A）

**Decision**
采用**串行队列预热**策略（V4 C-3：复用源码现有字段 `pendingPreheatDomains: MutableSet<String>`，不新建 `preheatQueue`）：
- 维护 `pendingPreheatDomains: MutableSet<String>` 待预热队列（Set 自带去重）
- WebViewClient.onPageFinished 回调中移除当前域名，触发下一个域名 loadUrl
- CookieManager.flush() 同步 cookies 到 CookieStore 供 Glide 复用
- 全部预热完成后发送 PREHEAT_COMPLETED 事件

**Consequences**
- 正向：所有域名都被正确预热；cookies 完整同步
- 负向：预热总时长 = N * 单域名预热时长（约 N * 2-3 秒），首张图片可能延迟
- 风险：预热期间用户已开始滚动，需在图片加载失败时触发降级链降级3（WebView 即时预热）

**Alternatives Considered**
- 并行多 WebView 实例：否决，内存占用过高 + WebView 实例间 cookies 互染风险
- 不预热，仅在加载失败时降级到 WebView：否决，首张图片失败率高

**Y-Stance**
我们选择串行而非并行，因为 WebView 实例是重量级资源（每个约 30-50MB 内存），并行多个 WebView 实例会触发 OOM；串行虽慢但稳定，且通过预热队列可观察进度。

---

### AD-06：错误降级链设计

**Context**
- 用户诉求：图片加载失败需有降级机制（对齐视频播放器四级降级）
- 现有架构仅 tvError + btnRetry 内嵌布局，单点失败即整体失败

**Decision**
采用**四级降级链**：
- **降级1（Glide 直加载）**：Glide.with(ctx).load(url).listener(RequestListener).into(imageView)，含 Referer/Cookie 注入
- **降级2（OkHttp + Cookie 兜底）**：Glide 失败后用 OkHttp 直接请求图片 URL，注入 sourceOriginOption + refererOption + 从 ImagePlay.rssSource 提取的 header（V4 B-14：删除 currentPlayHeaders 引用，header 从 rssSource 字段提取）
- **降级3（WebView 即时预热）**：OkHttp 失败后启动 WebView 加载图片 URL 获取 Cloudflare cookies， CookieManager.flush() 后重试 Glide 加载
- **降级4（网页模式回退）**：通过 alert {} DSL 提示用户"是否切换到网页模式"，用户确认后跳转 ReadRssActivity

**Consequences**
- 正向：覆盖防盗链 / Cloudflare / Cookie 过期 / 跨域等典型失败场景
- 负向：降级链总耗时可能达 10-15 秒（WebView 预热最慢），需用 UI 提示用户当前降级级别
- 风险：降级3 启动 WebView 会增加内存压力，需限制并发数（最多 1 个降级3 实例）

**Alternatives Considered**
- 仅 Glide + 重试按钮：否决，未满足"对齐视频播放器"诉求
- 自动降级到网页模式：否决，用户未授权就跳转破坏体验

**Y-Stance**
我们选择四级降级链而非简单重试，因为图片订阅源的 CDN 防护多样（防盗链 / Cloudflare JS 挑战 / Cookie 过期 / 跨域重定向），单一降级无法覆盖所有场景；最后一级保留用户决策入口（alert {} DSL）符合"用户主导"原则。

---

### AD-07：状态同步与协程取消机制

**Context**
- 大图模式返回列表需保持点击位置可见
- 快速滚动可能连续触发多次 loadNextArticle，导致数据错乱
- 现有 Bug3：loadArticleContent 协程未取消，Activity 销毁后仍运行
- **V2 B-4 新增**：ImageDetailActivity 屏幕旋转/进程重建时 currentIndex 和 imageUrls 丢失
- **V2 O-6 新增**：Rss.getContentAwait 底层 OkHttp 请求是否支持协程取消（若不支持，loadJob?.cancel() 后底层请求仍继续浪费流量）

**Decision**
采用**ViewModel + loadJob 取消 + setResult 状态传递 + onSaveInstanceState + ImagePlay 单例持有 imageUrls**策略：
- `ImageCanvasViewModel.loadJob: Job?` 持有当前加载协程
- loadNextArticle() 入口 `loadJob?.cancel()` 取消上一个，新建 Job
- ImageDetailActivity 返回时通过 `setResult(RESULT_OK, Intent().putExtra("currentIndex", index))` 传递当前大图索引
- ImageGalleryActivity.onActivityResult 接收后 `recyclerView.scrollToPosition(currentIndex)`
- ImageCanvasViewModel.onCleared() 自动取消所有协程（ViewModel 生命周期绑定 Activity）
- **V2 B-4 新增**：ImageDetailActivity 状态保存策略：
  - `onSaveInstanceState(outState: Bundle)` 保存 `currentIndex = viewPager2.currentItem`
  - `onCreate(savedInstanceState: Bundle?)` 优先从 savedInstanceState 恢复 currentIndex（默认 0）
  - `imageUrls` 数据量大时不适合放 savedInstanceState（受限 1MB），改用 `ImagePlay.allImageUrls` 单例持有（跨 Activity 共享，生命周期与 ImagePlay 绑定）
  - ImageDetailActivity 通过 `ImagePlay.allImageUrls` 读取图片 URL 列表（与 ImageGalleryActivity 共享同一份数据，避免 Intent 传递 1MB 限制）
- **V2 O-6 新增**：Rss.getContentAwait 协程取消级联保障：
  - 核查 Rss.getContentAwait 内部实现，确认 OkHttp 请求是否可中断
  - 若 Rss.getContentAwait 内部使用 `withContext(Dispatchers.IO) { ensureActive() }` 或 `okhttp3.Call.cancel()` 支持协程取消，则 loadJob?.cancel() 即可终止底层请求
  - 若不支持协程取消，需在 tasks Phase 5 新增任务：核查并改造 Rss.getContentAwait 内部添加 `ensureActive()` 检查点（在每篇文章解析完成后检查协程是否已取消，已取消则抛出 CancellationException）
  - 注意：runCatching 会吞 CancellationException 导致协程取消误报，必须重新抛出（项目记忆铁律）

**Consequences**
- 正向：协程正确取消，无数据错乱；状态同步清晰；屏幕旋转/进程重建后 currentIndex 正确恢复；imageUrls 通过单例共享避免 Intent 1MB 限制
- 负向：scrollToPosition 可能因 ViewHolder 已回收而失效（用 recyclerView.post { scrollToPosition } 延迟执行缓解，或 viewTreeObserver.addOnGlobalLayoutListener 监听布局完成后再滚动——V2 U-4/U-10 优化）
- 风险：大图模式切换图片时若列表已加载新文章，索引可能错位（用 articleIndex + imageIndex 双索引定位）
- 风险：ImagePlay 单例持有 allImageUrls 在 Activity 销毁后仍残留，需在 ImageGalleryActivity.onDestroy 调用 `ImagePlay.clearImageCanvasState()` 清空（V2 O-3 修复）

**Alternatives Considered**
- SharedViewModel + LiveData：否决，跨 Activity 共享 ViewModel 需 Activity 处于同一 ViewModelStoreOwner
- EventBus 事件传递：否决，EventBus 已在项目中被弱化，新增不推荐
- SavedStateHandle 持有 imageUrls：否决，SavedStateHandle 同样受 1MB 限制，且序列化大列表性能差
- Intent extras 传递 imageUrls：否决，Intent extras 受 1MB 限制（Binder 事务缓冲区），大图集（50+ 张图片 URL）会抛 TransactionTooLargeException

**Y-Stance**
我们选择 ViewModel + setResult + onSaveInstanceState + ImagePlay 单例持有 imageUrls 而非 SharedViewModel/EventBus/SavedStateHandle/Intent extras，因为：
1. ViewModel 的 onCleared 天然绑定 Activity 生命周期解决协程取消问题
2. setResult 是 Android 标准的 Activity 间通信方式
3. onSaveInstanceState 是 Android 标准的配置变更状态保存方式（仅保存轻量 currentIndex）
4. ImagePlay 单例持有 imageUrls 避免 Intent/SavedStateHandle 的 1MB 限制，且与现有 ImagePlay 模式一致
符合项目"使用标准 API 而非引入新框架"原则。

---

### AD-08：图片缓存策略

**Context**
- 垂直画布同时加载多张图片，内存压力大
- 跨文章滚动时旧图片可能被回收，重新进入可见区域需重新加载

**Decision**
采用**Glide 三级缓存 + RecyclerView 缓存控制**策略：
- Glide 磁盘缓存：DefaultAvailableString -> InternalCacheDiskCacheFactory（默认 250MB，可配置）
- Glide 内存缓存：默认开启，使用 LRU 策略
- Glide 缩略图：列表模式 `override(screenWidth, screenWidth * 2)` 限制尺寸
- RecyclerView.setItemViewCacheSize(2)（默认 2 个 ViewHolder 离屏缓存）
- RecyclerView.setRecycledViewPool(DefaultItemAnimator()) 共享池
- 快速滚动时 Glide.with(this).pauseRequests()，停止后 resumeRequests()

**Consequences**
- 正向：内存占用可控（约 100-200MB 图片缓存 + 50-80MB WebView）
- 负向：用户回滚时图片可能需重新加载（约 200-500ms）
- 风险：缩略图模式下大图加载时质量不足，点击进入大图模式时需重新加载原图

**Alternatives Considered**
- 关闭内存缓存：否决，回滚体验极差
- 增大 RecyclerView 缓存到 5：否决，内存压力过大

**Y-Stance**
我们选择默认缓存配置 + RecyclerView 缓存控制，因为这是 Glide 与 RecyclerView 的最佳实践组合，无需额外调优即可满足性能需求；若有内存压力可后续通过 Glide 内存缓存策略调整（P2 优化）。

---

### AD-09：allImageUrls 并发安全策略（V3 B-6 新增，V4 B-14 修订）

**Context**
- V2 将 allImageUrls 改为 `MutableList<ImageCanvasItem>`（sealed class）
- 但三处并发访问未同步：Adapter 主线程读 / ViewModel 协程写 / ImageDetailActivity 主线程读
- MutableList 非线程安全，并发修改触发 `ConcurrentModificationException`
- V4 B-14 修订：现状 ImagePlay 不存在 allImageUrls 字段（仅有 currentImageUrls 单文章缓存），需新增

**Decision**
采用 **MutableStateFlow 封装 + 不可变快照读取** 策略：
```kotlin
// ImagePlay 单例
private val _allImageUrls = MutableStateFlow<List<ImageCanvasItem>>(emptyList())
val allImageUrls: StateFlow<List<ImageCanvasItem>> = _allImageUrls.asStateFlow()

@Synchronized
fun appendItems(items: List<ImageCanvasItem>) {
    _allImageUrls.update { current -> current + items }
}

@Synchronized
fun clearImageCanvasState() {
    _allImageUrls.value = emptyList()
    loadedArticleIndices.clear()
    preloadedArticles.clear()
}

@Synchronized
fun resetForNewSource() {  // V3 B-9 新增
    _allImageUrls.value = emptyList()
    loadedArticleIndices.clear()
    preloadedArticles.clear()
}

// Adapter 读取不可变快照
val snapshot: List<ImageCanvasItem> = ImagePlay.allImageUrls.value
```

**Consequences**
- 正向：Flow 天然线程安全，无需手动 synchronized；支持 Flow.collectAsState 与 Lifecycle 感知
- 负向：每次 update 创建新 List，少量 GC 压力（可忽略）
- 风险：Adapter 拿到快照后，ViewModel 追加新数据需通过 Flow.collect 自动刷新

**Alternatives Considered**
- 方案B 全 @Synchronized 方法封装：可行但繁琐，易遗漏某处直接访问 allImageUrls 字段
- CopyOnWriteArrayList：写性能差，不适合频繁追加场景

**Y-Stance**
我们选择 StateFlow 而非 @Synchronized 方法封装，因为 Flow 与 Lifecycle 感知天然契合 Android ViewModel 模式，且 collectAsState 可自动驱动 RecyclerView 更新，避免手动 notifyDataSetChanged。

---

### AD-10：列表 position 与大图 imageIndex 双向映射（V3 B-7 新增）

**Context**
- 列表模式 RecyclerView 的 position 包含 ImageItem + ArticleDivider 两类
- 大图模式 ViewPager2 的 position 是纯图片索引（0,1,2,...）
- 直接传 listPosition 给 ViewPager2.setCurrentItem 会跳到错误图片

**Decision**
ImageCanvasAdapter 提供**双向映射方法**：
```kotlin
class ImageCanvasAdapter(...) {
    private val items: MutableList<ImageCanvasItem>

    /** 列表 position → 图片索引（-1 表示该位置是 ArticleDivider） */
    fun listPositionToImageIndex(listPos: Int): Int {
        if (listPos !in items.indices) return -1
        if (items[listPos] !is ImageCanvasItem.ImageItem) return -1
        var imageIdx = -1
        for (i in 0..listPos) {
            if (items[i] is ImageCanvasItem.ImageItem) imageIdx++
        }
        return imageIdx
    }

    /** 图片索引 → 列表 position（-1 表示未找到） */
    fun imageIndexToListPosition(imageIdx: Int): Int {
        var count = -1
        for (i in items.indices) {
            if (items[i] is ImageCanvasItem.ImageItem) count++
            if (count == imageIdx) return i
        }
        return -1
    }
}
```

调用链路：
- 进入大图：`onItemClick(listPos) → imageIdx = adapter.listPositionToImageIndex(listPos) → Intent.putExtra("startIndex", imageIdx)`
- 返回列表：`onActivityResult imageIdx → listPos = adapter.imageIndexToListPosition(imageIdx) → recyclerView.scrollToPosition(listPos)`

**Consequences**
- 正向：消除列表/大图 position 混淆导致的跳转错误
- 负向：每次映射需 O(N) 遍历（N 通常 < 200，可忽略）
- 风险：ImageDetailActivity 内部图片列表需与 ImagePlay.allImageUrls 中的 ImageItem 顺序保持一致

**Alternatives Considered**
- 维护独立的 imageIndex ↔ listPos 双向 Map：内存浪费，且数据更新需同步两份
- 大图模式也使用 ImageCanvasItem 列表（保留分隔符）：大图模式不应有分隔符，破坏浏览体验

**Y-Stance**
我们选择运行时遍历映射而非预构建 Map，因为图片列表数据量通常较小（单文章 10-50 张），遍历开销可忽略，且避免了双重数据源同步问题。

---

### AD-11：协程池重建任务处理（V3 B-8 新增）

**Context**
- V2 B-1 引入「监听 LiveEventBus 配置变更事件运行时重建协程池」
- 但进行中 loadJob 仍在旧协程池上运行，重建后旧池未 shutdown 导致线程泄漏
- 旧任务结果可能仍写入 allImageUrls，与新任务数据竞争

**Decision**
采用 **「取消-关闭-重建-重启」四步流程**：
```kotlin
class ImageCanvasViewModel : ViewModel() {
    private var coroutineExecutor: ExecutorService = createExecutor(AppConfig.updateCacheThreadCount)
    private var loadJob: Job? = null

    private fun createExecutor(size: Int): ExecutorService =
        Executors.newFixedThreadPool(size.coerceAtLeast(1))

    fun onCoroutinePoolConfigChanged(newSize: Int) {
        val oldSize = (coroutineExecutor as? ThreadPoolExecutor)?.maximumPoolSize ?: -1
        // 1. 取消当前 loadJob
        loadJob?.cancel()
        // 2. 关闭旧协程池（等待 5 秒）
        coroutineExecutor.shutdown()
        coroutineExecutor.awaitTermination(5, TimeUnit.SECONDS)
        // 3. 创建新协程池
        coroutineExecutor = createExecutor(newSize)
        // 4. 重新触发加载（用户当前可见位置之后的下一篇文章）
        loadNextArticle()
        AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS,
            "CoroutinePool: rebuild oldSize=$oldSize newSize=$newSize source=configChanged")
    }

    override fun onCleared() {
        loadJob?.cancel()
        coroutineExecutor.shutdownNow()
    }
}
```

**Consequences**
- 正向：旧协程池资源释放，无线程泄漏；新配置立即生效
- 负向：重建期间约 1-5 秒无法响应新加载请求（awaitTermination 阻塞）
- 风险：awaitTermination 超时后仍有任务在旧池上运行，需在 loadJob 内部加 `ensureActive()` 检查

**Alternatives Considered**
- 不关闭旧池，让其自然空闲回收：线程泄漏，配置变更无实际效果
- 直接 shutdownNow() 中断所有任务：可能丢失已加载但未提交的数据

**Y-Stance**
我们选择「优雅关闭 + 等待 5 秒」而非 shutdownNow()，因为 Rss.getContentAwait 内部可能正在解析 HTML/JSON，强制中断会导致数据丢失；5 秒等待是性能与数据完整性的平衡点。

---

### AD-12：跨订阅源切换 allImageUrls 清理（V3 B-9 新增）

**Context**
- V2 O-3 修复了 onDestroy 时清理 allImageUrls
- 但用户在图片播放器内通过「换源」或「下一个订阅源」切换数据源时（不退出 Activity），allImageUrls 不被清理
- 旧订阅源 URL 残留 + 新订阅源 URL 追加 = 数据混合，显示错误

**Decision**
ImagePlay 新增 **`resetForNewSource()`** 方法，在以下场景调用：
1. ImagePlay.init(rssSource, rssArticles, rssArticleIndex) 初始化新订阅源时（V4 B-14：参数名已修正）
2. 用户主动切换订阅源时（通过 ImageGalleryActivity 内的换源按钮）

```kotlin
object ImagePlay {
    @Synchronized
    fun resetForNewSource() {
        val clearedSize = _allImageUrls.value.size
        _allImageUrls.value = emptyList()
        loadedArticleIndices.clear()
        preloadedArticles.clear()
        AppLog.putInfo(AppLog.TAG_IMAGE_PLAY,
            "resetForNewSource cleared=$clearedSize sourceId=${rssSource?.id}")
    }

    // V4 B-14：参数名 position → rssArticleIndex（与源码 ImagePlay.kt:16 字段名一致）
    fun init(rssSource: RssSource, rssArticles: List<RssArticle>, rssArticleIndex: Int) {
        resetForNewSource()  // V3 B-9 新增：初始化前先清理
        this.rssSource = rssSource
        this.rssArticles = rssArticles.toMutableList()
        this.rssArticleIndex = rssArticleIndex
    }
}
```

**Consequences**
- 正向：避免跨订阅源数据污染
- 负向：用户切换订阅源后已加载图片需重新加载（无可避免）
- 风险：reset 时机若与 Adapter.notifyDataSetChanged 同时执行，可能引发 IndexOutOfBoundsException

**Alternatives Considered**
- 不清理，依赖新数据覆盖：旧数据量大于新数据时残留
- 仅清理 allImageUrls 不清理 loadedArticleIndices：导致 preloadedArticles 误判已加载

**Y-Stance**
我们选择 reset 时一并清理所有相关状态（allImageUrls + loadedArticleIndices + preloadedArticles），因为这三者构成图片加载的状态闭环，任一残留都会导致数据不一致。

---

### AD-13：ViewHolder 复用闪烁修复（V3 B-10 新增）

**Context**
- design.md AD-03：默认高度 60% 屏幕高度 → onResourceReady 后动态更新实际高度
- ViewHolder 复用时，旧图片的实际高度先显示，新图片加载完成后才更新，造成「先高后矮再高」闪烁
- RecyclerView.setHasFixedSize(true) 与动态高度冲突

**Decision**
采用 **「复用时重置默认高度 + onViewRecycled 清理 Glide + setHasFixedSize(false)」** 三件套：
```kotlin
class ImageCanvasAdapter : RecyclerView.Adapter<...>() {
    private val defaultHeight: Int = ...  // 屏幕高度 60%
    private val maxLimitHeight: Int = ... // 屏幕高度 4 倍

    override fun onBindViewHolder(holder: ImageViewHolder, position: Int) {
        val item = items[position] as? ImageCanvasItem.ImageItem ?: return
        // 1. 重置为默认高度（避免旧图片高度残留）
        val lp = holder.itemView.layoutParams
        lp.height = defaultHeight
        holder.itemView.layoutParams = lp
        // 2. 清空旧图片
        Glide.with(holder.itemView.context).clear(holder.imageView)
        // 3. 加载新图片，onResourceReady 时更新实际高度
        Glide.with(holder.itemView.context)
            .load(item.url)
            .override(screenWidth, screenWidth * 2)
            .listener(object : RequestListener<Drawable> {
                override fun onResourceReady(...): Boolean {
                    val bitmap = (resource as BitmapDrawable).bitmap
                    val actualHeight = screenWidth * bitmap.height / bitmap.width
                    val limitedHeight = minOf(actualHeight, maxLimitHeight)
                    if (lp.height != limitedHeight) {
                        lp.height = limitedHeight
                        holder.itemView.layoutParams = lp
                    }
                    return false
                }
                override fun onLoadFailed(...): Boolean {
                    val errLp = holder.itemView.layoutParams
                    errLp.height = (screenHeight * 0.4).toInt()  // 加载失败高度 40%
                    holder.itemView.layoutParams = errLp
                    return false
                }
            })
            .into(holder.imageView)
    }

    override fun onViewRecycled(holder: ImageViewHolder) {
        Glide.with(holder.itemView.context).clear(holder.imageView)
        AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS,
            "onViewRecycled position=${holder.bindingAdapterPosition} hashCode=${holder.hashCode()}")
    }
}

// ImageGalleryActivity
recyclerView.setHasFixedSize(false)  // 允许动态高度
```

**Consequences**
- 正向：消除 ViewHolder 复用闪烁；onViewRecycled 及时释放图片内存
- 负向：每次 bind 多一次 LayoutParams 设置（约 0.1ms，可忽略）
- 风险：setHasFixedSize(false) 性能略低于 true，但动态高度场景必须禁用

**Alternatives Considered**
- 预加载图片尺寸（Glide.preload）：增加一次网络请求，性能损耗
- 固定高度：扭曲宽高比，违反适配性诉求

**Y-Stance**
我们选择「重置+清理+禁用固定尺寸」三件套，因为这是 RecyclerView 动态高度场景的标准最佳实践，开销极低且彻底解决闪烁问题。

---

## 3. 数据流图

### 3.1 数据流 1：垂直画布加载流（首次进入）

```
用户点击文章
    │
    ↓
ReadRss.readRss (ReadRss.kt L24-44 路由检查，V4 B-13：字段名 articleStyle → record.type)
    │
    ├─ record.type==2 → VideoPlayerActivity（不进入本流程）
    ├─ record.type==0 网页模式 → ReadRssActivity（不进入本流程）
    │
    └─ record.type==1 图片类型 → readNoHtml → 设置 ImagePlay 单例字段
        │  ImagePlay.rssSource = ...        // 含 header 信息（V4 B-14：删除 currentPlayHeaders，header 从 rssSource 提取）
        │  ImagePlay.rssArticles = ...
        │  ImagePlay.rssArticleIndex = ...  // V4 B-14：position → rssArticleIndex（与源码 ImagePlay.kt:16 字段名一致）
        │
        ↓
        启动 ImageGalleryActivity
            │
            ├─ 1. 初始化 ImageCanvasViewModel
            │   └─ allImageUrls.clear()
            │   └─ loadedArticleIndices.clear()
            │
            ├─ 2. 加载当前文章图片 URL 列表（V4 修订 B-11：Rss.getContentAwait 返回 String body，调用 parseImageUrls 解析）
            │   └─ val body: String = Rss.getContentAwait(rssArticle, ruleContent, rssSource)
            │       └─ 返回文章正文 HTML（String 类型，非 List<RssImage>）
            │   └─ val imageUrls: List<String> = parseImageUrls(body, article.link, ruleImage, rssSource)
            │       └─ 用规则解析 body 提取图片 URL 列表（List<String>，非 List<RssImage>，V4 B-12：RssImage 类不存在）
            │   └─ val imageItems: List<ImageCanvasItem.ImageItem> = imageUrls.mapIndexed { idx, url ->
            │           ImageCanvasItem.ImageItem(
            │               url = url,                          // 直接使用 String URL
            │               articleIndex = rssArticleIndex,    // 所属文章索引
            │               imageIndex = idx                   // 文章内图片索引
            │           )
            │       }
            │   └─ ImagePlay.appendItems(imageItems)  // allImageUrls: MutableStateFlow<List<ImageCanvasItem>>（V3 B-6）
            │   └─ loadedArticleIndices.add(rssArticleIndex)
            │
            ├─ 3. WebView 串行预热（AD-05，V4 C-3：复用源码 pendingPreheatDomains 字段）
            │   └─ needPreheat = ExtractDomain(allImageUrls).distinct()
            │   └─ pendingPreheatDomains.addAll(needPreheat)
            │   └─ startSerialPreheat()
            │       └─ 取 pendingPreheatDomains.first() 加载
            │       └─ onPageFinished → pendingPreheatDomains.remove(currentDomain)
            │       └─ CookieManager.flush()
            │       └─ if (pendingPreheatDomains.isNotEmpty()) startSerialPreheat() 串行触发下一个
            │
            ├─ 4. ImageCanvasAdapter.notifyDataSetChanged()
            │   └─ RecyclerView 渲染所有图片项
            │
            └─ 5. Glide 异步加载图片（AD-01/AD-03/AD-08）
                └─ Glide.with(ctx).load(url)
                    .override(screenWidth, screenWidth * 2)
                    .placeholder(R.drawable.img_placeholder)
                    .listener(RequestListener)
                    .into(imageView)
                    │
                    ├─ onResourceReady → 计算实际高度 → 更新 ViewHolder LayoutParams
                    └─ onLoadFailed → 触发降级链（AD-06）
```

### 3.2 数据流 2：大图模式切换流

```
列表模式：用户点击缩略图 (index=5)
    │
    ↓
ImageCanvasAdapter.onBindViewHolder.imageView.setOnClickListener
    │
    ├─ 1. 准备共享元素动画
    │   └─ val options = ActivityOptions.makeSceneTransitionAnimation(
    │           this, imageView, "shared_image_$index")
    │
    ├─ 2. 启动 ImageDetailActivity
    │   └─ val intent = Intent(this, ImageDetailActivity::class.java)
    │   └─ intent.putExtra("startIndex", index)
    │   └─ intent.putStringArrayListExtra("imageUrls", allImageUrls)
    │   └─ startActivityForResult(intent, REQUEST_DETAIL, options.toBundle())
    │
    ↓
ImageDetailActivity.onCreate
    │
    ├─ 1. 解析参数
    │   └─ startIndex = intent.getIntExtra("startIndex", 0)
    │   └─ imageUrls = intent.getStringArrayListExtra("imageUrls")
    │
    ├─ 2. 初始化 ViewPager2 + ImageDetailAdapter
    │   └─ binding.viewPager2.orientation = ViewPager2.ORIENTATION_HORIZONTAL
    │   └─ binding.viewPager2.adapter = ImageDetailAdapter(imageUrls)
    │   └─ binding.viewPager2.setCurrentItem(startIndex, false)
    │
    ├─ 3. PhotoView 缩放/旋转/长按保存（迁移自 ImagePageAdapter）
    │
    ├─ 4. 沉浸式全屏（WindowInsetsControllerCompat）
    │
    └─ 5. ViewPager2.OnPageChangeCallback
        └─ onPageSelected(index) → 更新 TitleBar 页码 "文章N/M 图片X/Y"
        └─ 用户左右滑动切换图片
            │
            └─ 用户按返回键
                │
                ↓
                setResult(RESULT_OK, Intent().putExtra("currentIndex", viewPager2.currentItem))
                finish()
                    │
                    ↓
ImageGalleryActivity.onActivityResult
    │
    └─ recyclerView.post { recyclerView.scrollToPosition(currentIndex) }
```

### 3.3 数据流 3：分页加载流

```
用户垂直滚动 RecyclerView
    │
    ↓
RecyclerView.OnScrollListener.onScrolled
    │
    ├─ 1. 计算位置
    │   └─ val layoutManager = recyclerView.layoutManager as LinearLayoutManager
    │   └─ val totalItemCount = layoutManager.itemCount
    │   └─ val lastVisible = layoutManager.findLastVisibleItemPosition()
    │   └─ val remaining = totalItemCount - lastVisible
    │
    ├─ 2. 判断触发条件（AD-04）
    │   └─ if (remaining <= PAGINATION_THRESHOLD && !isLoading && !isLaunching) {
    │       └─ 触发加载
    │   }
    │
    ├─ 3. ImageCanvasViewModel.loadNextArticle()
    │   └─ loadJob?.cancel()  // AD-07
    │   └─ loadJob = viewModelScope.launch {
    │       └─ isLaunching = true
    │       └─ postValue(LoadState.LOADING)
    │       │
    │       └─ val nextIndex = ImagePlay.rssArticleIndex + loadedArticleIndices.size  // V4 B-14：position → rssArticleIndex
    │       └─ if (nextIndex >= rssArticles.size) {
    │       │   └─ postValue(LoadState.NO_MORE)
    │       │   └─ return@launch
    │       │   }
    │       │
    │       └─ if (loadedArticleIndices.contains(nextIndex)) {
    │       │   └─ return@launch  // 已加载，去重
    │       │   }
    │       │
    │       └─ try {
        │       │   └─ // V4 B-11：Rss.getContentAwait 返回 String body，调用 parseImageUrls 解析
        │       │   └─ val body: String = Rss.getContentAwait(rssArticles[nextIndex], ruleContent, rssSource)
        │       │   └─ val imageUrls: List<String> = parseImageUrls(body, rssArticles[nextIndex].link, ruleImage, rssSource)
        │       │   └─ val imageItems: List<ImageCanvasItem.ImageItem> = imageUrls.mapIndexed { idx, url ->
        │       │           ImageCanvasItem.ImageItem(url, nextIndex, idx)
        │       │       }
        │       │   └─ ImagePlay.appendItems(imageItems)  // V3 B-6: StateFlow 封装
        │       │   └─ loadedArticleIndices.add(nextIndex)
        │       │   └─ postValue(LoadState.SUCCESS(imageItems))
        │       │   └─ // 触发 WebView 串行预热新域名（AD-05）
        │       │   └─ needPreheat = imageItems.map { ExtractDomain(it.url) }.distinct() - preheatedDomains
        │       │   └─ if (needPreheat.isNotEmpty()) startSerialPreheat(needPreheat)
        │       │   } catch (e: Exception) {
        │       │   └─ postValue(LoadState.ERROR(e))
        │       │   }
    │       │
    │       └─ isLaunching = false
    │   }
    │
    └─ 4. ImageCanvasAdapter 通知 UI 更新
        └─ LoadState.LOADING → 显示 ProgressBar
        └─ LoadState.SUCCESS → notifyDataSetChanged()
        └─ LoadState.ERROR → 显示重试按钮
        └─ LoadState.NO_MORE → 显示"没有更多了"
```

### 3.4 数据流 4：错误降级链

```
Glide 加载图片失败 (onLoadFailed)
    │
    ↓
触发降级1：Glide 重试（清空缓存）
    └─ Glide.with(ctx).load(url).skipMemoryCache(true).into(imageView)
        │
        ├─ 成功 → 显示图片，结束
        └─ 失败 → 进入降级2
            │
            ↓
            降级2：OkHttp + Cookie 兜底
            └─ Coroutine.async {
                └─ val request = Request.Builder().url(url)
                    .header("Referer", ImagePlay.sourceOrigin)
                    .header("Cookie", ImagePlay.rssSource?.header ?: "")  // V4 B-14：从 rssSource 提取 header（currentPlayHeaders 不存在）
                    .build()
                └─ val response = okHttpClient.newCall(request).execute()
                └─ if (response.isSuccessful) {
                    │   └─ val bitmap = BitmapFactory.decodeStream(response.body.byteStream)
                    │   └─ imageView.post { imageView.setImageBitmap(bitmap) }
                    │   └─ return@async  // 成功
                    │   }
                └─ throw IOException("OkHttp fallback failed")
            }.onError {
                └─ 进入降级3
            }
                │
                ↓
                降级3：WebView 即时预热
                └─ val preheatWebView = WebView(ctx)
                └─ preheatWebView.webViewClient = object : WebViewClient() {
                    └─ onPageFinished { view, url ->
                        └─ CookieManager.flush()
                        └─ // 重新尝试 Glide 加载
                        └─ Glide.with(ctx).load(url).skipMemoryCache(true).into(imageView)
                        └─ preheatWebView.destroy()
                    }
                }
                └─ preheatWebView.loadUrl(url)
                    │
                    ├─ 成功 → 显示图片，结束
                    └─ 超时（10s）→ 进入降级4
                        │
                        ↓
                        降级4：网页模式回退
                        └─ withContext(Dispatchers.Main) {
                            └─ alert {
                            │   └─ title = "图片加载失败"
                            │   └─ message = "是否切换到网页模式查看？"
                            │   └─ yesButton { ReadRssActivity.start(ctx, articleUrl) }
                            │   └─ noButton { /* 显示错误图标 + 复制 URL */ }
                            │   └─ applyTint()
                            }.show()
                        }
```

---

## 4. 文件变更清单

### 4.1 新建文件（5 个）

| # | 文件路径 | 类型 | 说明 |
|---|---------|------|------|
| 1 | `app/src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt` | Kotlin | 列表模式 ViewModel：管理 allImageUrls / loadedArticleIndices / loadJob / loadNextArticle() |
| 2 | `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` | Kotlin | RecyclerView 适配器：图片项 ViewHolder + 加载状态 ViewHolder + 文章分隔符 ViewHolder |
| 3 | `app/src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt` | Kotlin | 大图模式 Activity：ViewPager2 + PhotoView + 沉浸式 + 共享元素动画 |
| 4 | `app/src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt` | Kotlin | 大图模式适配器：基于 ImagePageAdapter 精简，剥离 ImageArticlePagerAdapter 耦合 |
| 5 | `app/src/main/res/layout/activity_image_detail.xml` | XML | 大图模式布局：ViewPager2 + TitleBar 页码 + 旋转工具栏 |

### 4.2 修改文件（5 个）

| # | 文件路径 | 修改范围 | 说明 |
|---|---------|---------|------|
| 1 | `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt` | 整体重写 | 废弃双 ViewPager2 嵌套，改用 RecyclerView + ImageCanvasAdapter + ImageCanvasViewModel |
| 2 | `app/src/main/java/io/legado/app/ui/image/ImagePlay.kt` | 字段扩展 | V4 B-14：现状字段 `rssArticleIndex`（设计文档原假设 `position` 不存在）/ `rssSource`（含 header 信息，原假设 `currentPlayHeaders` 不存在）/ `currentImageUrls`（单文章缓存，保留）。**新增字段**：allImageUrls: MutableStateFlow<List<ImageCanvasItem>>（V3 B-6 StateFlow 封装）/ loadedArticleIndices: MutableSet<Int> / preloadedArticles: MutableSet<Int> / appendItems() / clearImageCanvasState() / resetForNewSource() 方法 |
| 3 | `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` | 验证不变 | V4 B-13：确认 L24-44 路由逻辑 `record.type==1` 走 readNoHtml 启动 ImageGalleryActivity，`record.type==0` 走 ReadRssActivity（仅读取验证，不修改；原假设 `articleStyle==2` 字段名错误） |
| 4 | `app/src/main/AndroidManifest.xml` | 新增 Activity 注册 | 注册 ImageDetailActivity（android:theme="@style/Theme.AppCompat.NoActionBar" 共享元素动画） |
| 5 | `app/src/main/res/values/colors.xml` | 新增色阶 | 新增 transparent80 (#80000000) / transparent70 (#B3000000) 色阶（对齐 player-review-and-optimization AD-10） |

### 4.3 删除文件（2 个）

| # | 文件路径 | 删除理由 |
|---|---------|---------|
| 1 | `app/src/main/java/io/legado/app/ui/image/ImageArticlePagerAdapter.kt` | 双 ViewPager2 嵌套废弃，外层 adapter 不再需要 |
| 2 | `app/src/main/java/io/legado/app/ui/image/ImageGalleryViewModel.kt` | 由 ImageCanvasViewModel 取代（如存在） |

### 4.4 保留文件（不修改，仅引用）

| # | 文件路径 | 保留理由 |
|---|---------|---------|
| 1 | `app/src/main/java/io/legado/app/ui/image/ImagePageAdapter.kt` | 大图模式逻辑迁移到 ImageDetailAdapter 后保留作为参考（不删除，避免影响其他可能的引用） |
| 2 | `app/src/main/java/io/legado/app/help/http/OkHttpStreamFetcher.kt` | Glide 自定义数据源，保留 sourceOriginOption / refererOption 注入逻辑 |
| 3 | `app/src/main/res/drawable/bg_overlay_button.xml` | 12dp 圆角按钮背景，对齐视频播放器 |

---

## 5. 关键技术实现要点

### 5.1 ImageCanvasAdapter 多 ViewType 实现

> **V2 修订（B-3 阻塞点修复）**：将 allImageUrls 从 `MutableList<String>` 改为 `MutableList<ImageCanvasItem>` sealed class，支持图片项 + 文章分隔符混合数据结构。

```kotlin
// 数据结构定义（V2 修订 B-3）
sealed class ImageCanvasItem {
    data class ImageItem(
        val url: String,
        val articleIndex: Int,  // 所属文章索引
        val imageIndex: Int     // 文章内图片索引
    ) : ImageCanvasItem()

    data class ArticleDivider(
        val articleIndex: Int,
        val articleTitle: String  // 文章标题（可空，从 rssArticles[articleIndex].title 获取）
    ) : ImageCanvasItem()
}

class ImageCanvasAdapter(
    private val items: MutableList<ImageCanvasItem>,  // V2: 改为 ImageCanvasItem 列表
    private val onItemClick: (Int, View) -> Unit,
    private val onRetryClick: () -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    companion object {
        const val TYPE_IMAGE = 0
        const val TYPE_LOADING = 1
        const val TYPE_ERROR = 2
        const val TYPE_NO_MORE = 3
        const val TYPE_ARTICLE_DIVIDER = 4
    }

    override fun getItemViewType(position: Int): Int {
        return when {
            position >= items.size -> currentLoadState.toViewType()  // footer 区域
            items[position] is ImageCanvasItem.ImageItem -> TYPE_IMAGE
            items[position] is ImageCanvasItem.ArticleDivider -> TYPE_ARTICLE_DIVIDER
            else -> TYPE_NO_MORE
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return when (viewType) {
            TYPE_IMAGE -> ImageViewHolder.create(parent, onItemClick)
            TYPE_LOADING -> LoadingViewHolder.create(parent)
            TYPE_ERROR -> ErrorViewHolder.create(parent, onRetryClick)
            TYPE_NO_MORE -> NoMoreViewHolder.create(parent)
            TYPE_ARTICLE_DIVIDER -> ArticleDividerViewHolder.create(parent)
            else -> throw IllegalArgumentException("Unknown viewType: $viewType")
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (holder) {
            is ImageViewHolder -> {
                val item = items[position] as ImageCanvasItem.ImageItem
                holder.bind(item.url, position)
            }
            is ArticleDividerViewHolder -> {
                val item = items[position] as ImageCanvasItem.ArticleDivider
                holder.bind(item.articleTitle)
            }
            // 其他 ViewHolder 无需 bind 数据
        }
    }

    // V2 修订 B-3：items.size 已包含图片项 + 文章分隔符，+1 用于 footer（loading/error/no_more）
    override fun getItemCount(): Int = items.size + 1

    // AD-03: 图片高度自适应
    class ImageViewHolder(
        private val binding: ItemImageCanvasBinding,
        private val onItemClick: (Int, View) -> Unit
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(url: String, position: Int) {
            // 默认高度为屏幕高度的 60%
            val defaultHeight = (itemView.resources.displayMetrics.heightPixels * 0.6).toInt()
            binding.photoView.layoutParams.height = defaultHeight

            binding.photoView.transitionName = "shared_image_$position"

            Glide.with(itemView.context)
                .load(url)
                .override(itemView.width, defaultHeight * 2)  // AD-08: 缩略图模式
                .placeholder(R.drawable.img_placeholder)
                .listener(object : RequestListener<Drawable> {
                    override fun onResourceReady(
                        resource: Drawable, model: Any,
                        target: Target<Drawable>?, dataSource: DataSource, isFirstResource: Boolean
                    ): Boolean {
                        // AD-03: 动态计算实际高度
                        val bitmap = (resource as BitmapDrawable).bitmap
                        val actualHeight = itemView.width * bitmap.height / bitmap.width
                        val maxHeight = itemView.resources.displayMetrics.heightPixels * 4  // 最大 4 倍屏幕高度
                        binding.photoView.layoutParams.height = actualHeight.coerceAtMost(maxHeight)
                        binding.photoView.requestLayout()
                        return false
                    }

                    override fun onLoadFailed(
                        e: GlideException?, model: Any?,
                        target: Target<Drawable>?, isFirstResource: Boolean
                    ): Boolean {
                        // AD-06: 触发降级链
                        triggerFallbackChain(url)
                        return false
                    }
                })
                .into(binding.photoView)

            itemView.setOnClickListener { onItemClick(position, binding.photoView) }
        }
    }
}
```

### 5.2 ImageCanvasViewModel 协程管理

```kotlin
class ImageCanvasViewModel(
    private val rssSource: RssSource,
    private val rssArticles: List<RssArticle>,
    private val initialRssArticleIndex: Int  // V4 B-14：initialPosition → initialRssArticleIndex
) : ViewModel() {

    // V3 B-6: allImageUrls 改用 MutableStateFlow 封装（线程安全）
    // 实际字段位于 ImagePlay 单例，ViewModel 通过 ImagePlay.appendItems() 写入
    val loadedArticleIndices: MutableSet<Int> = mutableSetOf()

    private val _loadState = MutableLiveData<LoadState>()
    val loadState: LiveData<LoadState> = _loadState

    private var loadJob: Job? = null
    @Volatile private var isLaunching = false

    init {
        loadInitialArticle()
    }

    private fun loadInitialArticle() {
        loadJob = viewModelScope.launch(Dispatchers.IO) {
            try {
                _loadState.postValue(LoadState.LOADING)
                // V4 B-11：Rss.getContentAwait 返回 String body（非 List<RssImage>）
                val body = Rss.getContentAwait(rssArticles[initialRssArticleIndex], ruleContent, rssSource)
                // V4 B-12：调用 parseImageUrls 解析 body 为 List<String>（RssImage 类不存在）
                val imageUrls = parseImageUrls(body, rssArticles[initialRssArticleIndex].link, ruleImage, rssSource)
                val imageItems = imageUrls.mapIndexed { idx, url ->
                    ImageCanvasItem.ImageItem(url, initialRssArticleIndex, idx)
                }
                ImagePlay.appendItems(imageItems)  // V3 B-6: StateFlow 封装
                loadedArticleIndices.add(initialRssArticleIndex)
                _loadState.postValue(LoadState.SUCCESS)
            } catch (e: Exception) {
                _loadState.postValue(LoadState.ERROR(e))
            }
        }
    }

    fun loadNextArticle() {
        if (isLaunching) return
        loadJob?.cancel()  // AD-07: 取消上一个加载

        loadJob = viewModelScope.launch(Dispatchers.IO) {
            isLaunching = true
            try {
                _loadState.postValue(LoadState.LOADING)

                val nextIndex = loadedArticleIndices.maxOrNull()?.plus(1) ?: return@launch
                if (nextIndex >= rssArticles.size) {
                    _loadState.postValue(LoadState.NO_MORE)
                    return@launch
                }
                if (loadedArticleIndices.contains(nextIndex)) return@launch  // 去重

                // V4 B-11：Rss.getContentAwait 返回 String body
                val body = Rss.getContentAwait(rssArticles[nextIndex], ruleContent, rssSource)
                val imageUrls = parseImageUrls(body, rssArticles[nextIndex].link, ruleImage, rssSource)
                val imageItems = imageUrls.mapIndexed { idx, url ->
                    ImageCanvasItem.ImageItem(url, nextIndex, idx)
                }
                ImagePlay.appendItems(imageItems)
                loadedArticleIndices.add(nextIndex)

                _loadState.postValue(LoadState.SUCCESS)
            } catch (e: Exception) {
                _loadState.postValue(LoadState.ERROR(e))
            } finally {
                isLaunching = false
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        loadJob?.cancel()  // AD-07: ViewModel 销毁时取消所有协程
    }
}

sealed class LoadState {
    object LOADING : LoadState()
    object SUCCESS : LoadState()
    object NO_MORE : LoadState()
    data class ERROR(val error: Throwable) : LoadState()
}
```

### 5.3 WebView 串行预热实现

```kotlin
// ImageGalleryActivity.kt
// V4 C-3：复用现有字段名 pendingPreheatDomains（源码 ImageGalleryActivity.kt:59 已存在），不新建 preheatQueue
private val pendingPreheatDomains: MutableSet<String> = mutableSetOf()  // 待预热域名队列（Set 去重）
private val preheatedDomains: MutableSet<String> = mutableSetOf()       // 已预热完成的域名
private var preheatWebView: WebView? = null

private fun startSerialPreheat(domains: List<String>) {
    val newDomains = domains.distinct().filter { it !in preheatedDomains && it !in pendingPreheatDomains }
    if (newDomains.isEmpty()) return

    pendingPreheatDomains.addAll(newDomains)
    if (preheatWebView == null) {
        preheatWebView = initPreheatWebView()
    }
    processNextPreheat()
}

private fun processNextPreheat() {
    if (pendingPreheatDomains.isEmpty()) {
        preheatWebView?.destroy()
        preheatWebView = null
        return
    }

    val currentDomain = pendingPreheatDomains.first()
    preheatWebView?.webViewClient = object : WebViewClient() {
        override fun onPageFinished(view: WebView?, url: String?) {
            super.onPageFinished(view, url)
            CookieManager.getInstance().flush()
            preheatedDomains.add(currentDomain)
            pendingPreheatDomains.remove(currentDomain)
            AppLog.putInfo(AppLog.TAG_IMAGE_CANVAS,
                "Preheat: domain_${preheatedDomains.size} completed remaining=${pendingPreheatDomains.size}")  // 仅日志记录数量，不输出域名
            processNextPreheat()  // 串行触发下一个
        }

        override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
            super.onReceivedError(view, request, error)
            AppLog.putError(AppLog.TAG_IMAGE_CANVAS,
                "Preheat failed: errorCode=${error?.errorCode}")
            pendingPreheatDomains.remove(currentDomain)
            processNextPreheat()
        }
    }
    preheatWebView?.loadUrl("https://$currentDomain")
}
```

---

## 6. 测试策略

### 6.1 单元测试（P0）

- ImageCanvasViewModel 协程取消测试：模拟快速调用 loadNextArticle() 5 次，验证仅最后一次 loadJob 完成
- ImagePlay.appendNextArticleImages 去重测试：模拟同一 index 调用 2 次，验证 allImageUrls 不重复
- LoadState 状态转换测试：LOADING → SUCCESS / LOADING → ERROR / LOADING → NO_MORE

### 6.2 集成测试（P0）

- ImageCanvasAdapter 多 ViewType 渲染测试：构造 5 张图片 + 加载中状态，验证 6 个 ViewHolder 正确创建
- RecyclerView 滚动监听触发测试：模拟滚动到 position = totalItemCount - 3，验证 loadNextArticle() 被调用
- 共享元素动画过渡测试：点击缩略图启动 ImageDetailActivity，验证 transitionName 一致

### 6.3 端到端测试（P0，真机验证）

按 spec.md §5 的 17 个场景执行真机验证，使用 `ai_tests/scripts/l2_verify_video_player.py` 的图片扩展版本（需新建 `l2_verify_image_player.py`）：

- 场景1-3：列表模式（垂直滚动 / 快速滚动暂停 / 加载失败重试）
- 场景4-6：大图模式（共享元素动画 / 左右滑动 / 返回状态同步）
- 场景7-9：分页加载（自动加载下一篇 / 没有更多了 / 加载失败重试）
- 场景10-13：保留能力（多域名串行预热 / 四级降级链 / type==1 路由回退 / 协程取消）（V4 B-13：articleStyle==2 → type==1）
- 场景14-15：架构风格（与视频播放器视觉一致 / 主题切换）
- 场景16-17：边界场景（超长图 / 加载中切换主题）

### 6.4 性能测试（P1）

- 内存占用测试：加载 50 张图片后内存增长 ≤ 150MB（用 Android Profiler 测量）
- 滚动流畅度测试：垂直滚动 FPS ≥ 55（用 GPU 渲染分析）
- 加载耗时测试：首屏首张图片加载 ≤ 1.5s（弱网 ≤ 3s）

---

## 7. 风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 图片高度预测抖动 | 高 | 视觉抖动 | AD-03 默认高度 60% + RequestListener 动态更新 |
| 大图模式共享元素动画闪烁 | 中 | 体验下降 | Glide.preload 预热前 3 张 + transitionName 严格匹配 |
| 多域名预热延迟 | 中 | 首张图片加载慢 | AD-05 串行预热 + 加载失败降级3 即时预热 |
| 内存压力（OOM） | 中 | 应用崩溃 | AD-08 Glide 缩略图 + setItemViewCacheSize(2) + 快速滚动 pauseRequests |
| 横屏体验下降 | 低 | 用户不满 | 接受现状，P2 评估横屏切换为左右滑动 |
| 取代 player-review-and-optimization 图片部分导致文档迁移成本 | 中 | 文档混乱 | 在 player-review-and-optimization README.md 显式标记"图片部分已废弃，由 image-player-vertical-canvas-optimization 取代" |
| ImagePageAdapter 旧引用未清理 | 低 | 编译告警 | 删除前 Grep 全项目搜索 ImagePageAdapter 引用，确认无残留再删除 |

---

## 8. 与 player-review-and-optimization 的关系

### 8.1 取代关系

本 spec **取代** player-review-and-optimization 中所有图片播放器相关任务：

| player-review-and-optimization 任务 | 本 spec 对应任务 |
|-------------------------------------|-----------------|
| R2.1-R2.21（图片 P0/P1 修复） | R1.1-R1.20 + R2.1-R2.9 |
| R4.6-R4.18（图片能力提升） | R1.16-R1.20（保留能力 + 降级链） |
| 阶段 4-7（图片修复任务） | Phase 1-6 |
| 阶段 12（图片架构风格） | Phase 7 |
| Phase 3-4（图片 Phase） | Phase 1-8 |
| AD-03（header/cookie 复用） | R1.18 + AD-06 降级2 |
| AD-04（多线程预加载） | R1.7 + AD-04 分页加载 |
| AD-05（type==1 路由回退，V4 B-13：articleStyle → record.type） | R1.19 |
| AD-06（图片尺寸适配） | AD-03 图片高度自适应 |
| AD-07（多线程预缓存） | R1.7 + AD-08 缓存策略 |

### 8.2 保留关系

player-review-and-optimization **保留**所有视频播放器相关任务（R1.1-R1.9、R4.1-R4.5、R4.24-R4.38、阶段 2-3、阶段 11、Phase 1-2），本 spec 不涉及。

### 8.3 协同关系

- 架构风格对齐（R2.1-R2.5）继承自 player-review-and-optimization 的风格统一诉求
- 沉浸式 API 升级（WindowInsetsControllerCompat）对齐视频播放器
- 圆角规范 12dp 对齐视频播放器
- transparent80/transparent70 色阶新增供视频模块复用

---

## 9. 实施前置条件

- [ ] 用户审查并通过本设计方案（强制检查点 1：AskUserQuestion）
- [ ] player-review-and-optimization README.md 更新"图片部分已废弃"标记
- [ ] docs/INDEX.md 同步添加本 spec 到"设计中"列表
- [ ] docs/INDEX.md 同步更新 player-review-and-optimization 状态为"图片部分已废弃"
- [ ] 源码现状核查（ImageGalleryActivity.kt / ImagePlay.kt / ReadRss.kt）确认 spec 中引用的行号和字段名准确
