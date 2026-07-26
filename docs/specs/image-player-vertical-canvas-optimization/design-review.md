# 图片播放器垂直画布优化方案 V1 设计审查报告

> 审查时间：2026-07-26
> 审查范围：README.md / spec.md / design.md / tasks.md（V1 初稿）
> 审查方法：主代理深度审查 + 子代理代码引用核查
> 审查结论：**需调整**（5 个阻塞点 + 8 个遗漏点 + 10 个待优化事项）

---

## §1 阻塞点（必须修复才能实施，5 项）

### B-1：协程池硬编码 4 并发未复用 AppConfig 配置（用户已指出）

**问题**：
- spec.md L18/L148/L242：协程池限流（默认 4 并发）
- design.md AD-01 Consequences、tasks.md 2.2.2：硬编码 Semaphore(4)
- 项目已存在 `AppConfig.imageLoadConcurrency`（默认5，Glide 图片加载并发，用户可配置）
- 项目已存在 `AppConfig.updateCacheThreadCount`（默认16，更新+缓存场景，用户可配置）
- 项目已存在 `AppConfig.searchThreadCount`（默认32，搜索场景，用户可配置）

**证据**：
- `app/src/main/java/io/legado/app/help/config/AppConfig.kt:472-475`：`var imageLoadConcurrency: Int`（默认5）
- `app/src/main/java/io/legado/app/help/config/AppConfig.kt:453-456`：`var updateCacheThreadCount: Int`（默认16）
- 上游 spec `thread-pool-split-config/spec.md` R1.2：明确 `updateCacheThreadCount` 默认16
- 上游 spec `rss-concurrency-and-checksource-optimization/spec.md` F1.4：明确 `imageLoadConcurrency` 默认5

**建议修复**：
- 列表模式 Glide 图片加载：直接复用 `AppConfig.imageLoadConcurrency`（Glide 自带线程池，无需手动 Semaphore）
- ViewModel 协程并发（Rss.getContentAwait 解析文章图片 URL）：复用 `AppConfig.updateCacheThreadCount`（语义匹配：缓存文章图片 URL 列表）
- 监听 LiveEventBus 配置变更事件，运行时重建协程池

---

### B-2：Rss.getContentAwait 返回类型不一致

**问题**：
- design.md L289：`val imageUrls = Rss.getContentAwait(rssSource, rssArticles[position])` 注释「解析返回 List<RssImage>」
- 但 `allImageUrls: MutableList<String>` 类型为 String 列表
- 存在类型不匹配，实施时需明确转换逻辑

**证据**：
- design.md §3.1 数据流 1 L289：「解析返回 List<RssImage>」
- design.md §4.2 修改文件 L501：`allImageUrls: MutableList<String>`

**建议修复**：
- 明确 Rss.getContentAwait 返回 `List<RssImage>`，需提取 `imageUrls.map { it.url }` 转换为 `List<String>` 后再加入 allImageUrls
- 或者将 allImageUrls 类型改为 `MutableList<RssImage>`，保留更多元信息（如图片宽高、原始 headers）

---

### B-3：文章分隔符与 allImageUrls: MutableList<String> 数据结构冲突

**问题**：
- tasks.md 8.2.2：「实现 allImageUrls 中的文章边界标记（如 null 或 ArticleDivider 数据类）」
- 但 allImageUrls 类型是 `MutableList<String>`，不支持插入 null 或 ArticleDivider 数据类（运行时 ClassCastException）
- design.md §5.1 ImageCanvasAdapter.getItemCount L568：`allImageUrls.size + 1` 未考虑文章分隔符 ViewType 的额外项数

**证据**：
- design.md §4.2 修改文件 L501：`allImageUrls: MutableList<String>`
- design.md §5.1 L568：`override fun getItemCount(): Int = allImageUrls.size + 1`

**建议修复**：
- 将 allImageUrls 改为 sealed class 数据结构：
  ```kotlin
  sealed class ImageCanvasItem {
      data class ImageItem(val url: String, val articleIndex: Int, val imageIndex: Int) : ImageCanvasItem()
      data class ArticleDivider(val articleIndex: Int, val articleTitle: String) : ImageCanvasItem()
  }
  val allImageUrls: MutableList<ImageCanvasItem> = mutableListOf()
  ```
- getItemCount 改为 `allImageUrls.size + 1`（已包含分隔符）
- getItemViewType 按 ImageCanvasItem 类型分发

---

### B-4：ImageDetailActivity 状态保存缺失（屏幕旋转/进程重建）

**问题**：
- design.md AD-07 仅说明用 setResult 传递 currentIndex 返回列表
- 未说明 ImageDetailActivity 自身在屏幕旋转/进程重建时如何恢复 imageUrls 和 currentIndex
- ViewPager2 默认在配置变更时保持状态，但 Intent extras 在进程重建后丢失

**证据**：
- design.md AD-07 Decision：仅 setResult，未 onSaveInstanceState
- design.md §3.2 数据流 2 L337-338：通过 intent.getStringExtra/IntExtra 解析参数

**建议修复**：
- ImageDetailActivity.onCreate 检查 savedInstanceState，优先从 savedInstanceState 恢复 currentIndex
- onSaveInstanceState 保存 currentIndex：`outState.putInt("currentIndex", viewPager2.currentItem)`
- imageUrls 数据量大时不适合放 savedInstanceState（受限 1MB），改用 ImagePlay 单例或 ViewModel 持有

---

### B-5：共享元素动画在图片未加载完成时的降级未在 tasks 体现

**问题**：
- design.md AD-02 Consequences 风险：「图片尚未加载完成时共享元素动画可能闪烁（用 Glide.preload 预热前 3 张缓解）」
- 但 tasks.md Phase 3 大图模式能力中未体现"Glide.preload 预热前 3 张"任务
- 实施时若图片尚未加载完成，共享元素动画会显示 placeholder 导致闪烁

**证据**：
- design.md AD-02 Consequences：风险描述
- tasks.md 3.1.x：仅 setOnClickListener / ActivityOptions / startActivityForResult，无 preload 任务

**建议修复**：
- tasks.md Phase 3 新增 3.1.4 任务：「实现 Glide.preload 预热当前图片 + 相邻 2 张（前后各 1 张）」
- 共享元素动画 fallback：若图片未加载完成，自动降级为普通 Activity 跳转（无共享元素动画）

---

## §2 遗漏点（应覆盖但未覆盖，8 项）

### O-1：图片保存权限处理（Android 13+ 兼容）

**问题**：
- tasks.md 3.3.4 「迁移 PhotoView 长按保存能力（含权限请求）」未说明 Android 13+ 的 `READ_MEDIA_IMAGES` 权限兼容
- 现有 ImagePageAdapter 可能用旧 `WRITE_EXTERNAL_STORAGE`，在 Android 13+ 上无效

**建议**：
- tasks 3.3.4 明确：Android 13+ 用 `READ_MEDIA_IMAGES`，Android 12 及以下用 `WRITE_EXTERNAL_STORAGE`
- 用 `Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU` 分支处理

### O-2：大图模式横屏适配未明确

**问题**：
- spec.md §2.2 排除「横屏适配完整重写」
- 但大图模式横屏时 ViewPager2 orientation 是否切换为垂直滚动未明确
- 现有 ImagePageAdapter 横屏可能是 horizontal，需评估用户体验

**建议**：
- spec.md §2.1 在范围内补充「大图模式横屏保留 horizontal（与竖屏一致）」
- 或新增 P2 R3.8「大图模式横屏切换为垂直滚动」

### O-3：ImagePlay 单例字段在 Activity 销毁后的清理

**问题**：
- spec.md R1.16 新增 allImageUrls/loadedArticleIndices
- 但未说明 ImageGalleryActivity.onDestroy 时是否清空（避免脏数据残留影响下次进入）
- 用户退出后再次进入图片播放器，可能继承上次的 allImageUrls 导致显示错误

**建议**：
- tasks.md Phase 5 新增 5.1.4 任务：「ImageGalleryActivity.onDestroy 调用 ImagePlay.clearImageCanvasState() 清空 allImageUrls/loadedArticleIndices」
- ImagePlay 新增 `@Synchronized fun clearImageCanvasState()` 方法

### O-4：WindowInsetsControllerCompat 的 minSdk 兼容

**问题**：
- tasks.md 7.4.1 用 `WindowInsetsControllerCompat`
- 但该 API 在 API 21+ 需通过 `WindowCompat.setDecorFitsSystemProperties(window, false)` 包装
- 项目 minSdk 已提升至 23（依赖升级 spec），但需确认是否需要 ViewCompat

**建议**：
- tasks 7.4.1 补充：使用 `WindowCompat.setDecorFitsSystemProperties(window, false)` + `WindowInsetsControllerCompat(window, window.decorView)`
- 参考视频播放器现有实现（如有）

### O-5：activity_image_detail.xml 共享元素动画 theme 配置

**问题**：
- tasks 4.2 修改 AndroidManifest 注册 ImageDetailActivity 含 `android:theme="@style/Theme.AppCompat.NoActionBar"`
- 但未说明是否需要启用 `android:windowActivityTransitions` 才能使用共享元素动画
- AppCompat 主题默认未启用 windowActivityTransitions

**建议**：
- tasks 4.2 补充：在 styles.xml 新增 `Theme.ImageDetail` 主题，继承 NoActionBar，启用 `<item name="android:windowActivityTransitions">true</item>`
- 或在 ImageDetailActivity.onCreate 调用 `requestWindowFeature(FEATURE_ACTIVITY_TRANSITIONS)`

### O-6：Rss.getContentAwait 协程取消的级联影响

**问题**：
- design.md AD-07 loadJob?.cancel() 取消协程
- 但未说明 Rss.getContentAwait 底层是否支持协程取消（OkHttp 请求是否可中断）
- 若不支持取消，loadJob?.cancel() 后底层 OkHttp 请求仍会继续，浪费流量

**建议**：
- design.md AD-07 补充：Rss.getContentAwait 内部使用 `okhttp3.Call.cancel()` 或 `withContext(Dispatchers.IO) { ensureActive() }` 支持协程取消
- 或在 tasks Phase 5 新增任务：核查 Rss.getContentAwait 是否支持协程取消

### O-7：articleStyle==2 路由回退的"用户主动选择网页模式"判定字段

**问题**：
- spec.md R1.19 / design.md 数据流 1 L272：「articleStyle==2 且用户选网页模式 → ReadRssActivity」
- 但未说明"用户主动选择网页模式"的存储字段
- 实施时需明确从哪里读取用户选择

**建议**：
- tasks 5.4.1 补充：核查 ReadRss.kt L41-43 的具体实现，明确"用户主动选择网页模式"的判定字段（可能来自 AppConfig 或 RssSource 配置）

### O-8：与上游 spec 协同关系未明确

**问题**：
- 本 spec 与 `thread-pool-split-config`、`rss-concurrency-and-checksource-optimization` 存在配置依赖
- 但 spec.md/design.md 未明确说明依赖关系
- 实施时若上游 spec 未先实施，本 spec 的协程池配置将无法复用

**建议**：
- spec.md §1 Intent 补充上游依赖：`thread-pool-split-config`（提供 updateCacheThreadCount 配置）、`rss-concurrency-and-checksource-optimization`（提供 imageLoadConcurrency 配置）
- tasks.md Phase 0 新增 0.5 任务：核查上游 spec 是否已实施，若未实施则降级为硬编码默认值（5/16）

---

## §3 待优化事项（可优化但不阻塞，10 项）

### U-1：PAGINATION_THRESHOLD 常量化

**问题**：design.md AD-04 提到「可配置为常量 `PAGINATION_THRESHOLD = 3`」但未在 tasks 体现。

**建议**：tasks.md Phase 4 新增 4.1.3 任务：将触发阈值抽取为 companion object 常量 `PAGINATION_THRESHOLD = 3`，便于后续调整。

### U-2：大图模式预加载策略

**问题**：design.md AD-02 提到「Glide.preload 预热前 3 张」但未在 tasks 体现。

**建议**：与 B-5 合并修复。

### U-3：图片高度预测的预加载机制

**问题**：design.md AD-03 提到动态高度计算，但未考虑用 Glide preload 先获取尺寸再加载（避免布局抖动）。

**建议**：P2 优化项，评估用 Glide `.listener(onResourceReady)` 先获取 Bitmap 尺寸占位，再加载完整图片。

### U-4：scrollToPosition 延迟执行方式

**问题**：design.md AD-07 Consequences：「用 recyclerView.post { scrollToPosition } 延迟执行缓解」。

**建议**：改用 `viewTreeObserver.addOnGlobalLayoutListener` 更可靠，避免 post 时序不确定。

### U-5：WebView 预热进度提示

**问题**：design.md AD-05 提到「通过预热队列可观察进度」但未在 UI 上体现。

**建议**：P2 优化项，在 TitleBar 显示预热进度（如「预热中 2/5」）。

### U-6：降级链 UI 提示的具体实现

**问题**：tasks.md 6.1.5 提到「正在尝试备用方案 1/4...」但未指定 UI 元素。

**建议**：明确用 Snackbar 显示降级级别，用户可点击「取消」中止降级链。

### U-7：tasks 9.2.x 真机验证粒度过粗

**问题**：17 个场景合并为 6 个验证任务（9.2.2-9.2.7），每个任务覆盖 3-4 个场景，不利于精确定位失败。

**建议**：拆分为 17 个验证任务（9.2.1-9.2.17），每个场景一个任务。

### U-8：articleStyle==2 路由回退的回归测试

**问题**：tasks 5.4.1 仅「验证不变」，未说明回归测试方法。

**建议**：tasks 9.2.5 真机验证场景 12「articleStyle==2 路由回退」时，需准备 articleStyle==2 的订阅源测试数据。

### U-9：图片高度限制（4 倍屏幕高度）的边界处理

**问题**：design.md AD-03 Decision：「最大高度为屏幕高度的 4 倍（超出部分滚动查看）」。

**建议**：补充说明超长图（> 4 倍）时如何处理——是裁剪显示还是允许在 ViewHolder 内部滚动？建议允许在 ViewHolder 内部滚动（PhotoView 已支持）。

### U-10：协程取消的延迟执行时序

**问题**：design.md AD-07 Consequences：「scrollToPosition 可能因 ViewHolder 已回收而失效」。

**建议**：补充说明 ViewHolder 已回收时的 fallback——用 `recyclerView.layoutManager?.scrollToPosition(currentIndex)` + `recyclerView.viewTreeObserver.addOnPreDrawListener` 监听布局完成后再滚动。

---

## §4 修复优先级与建议执行顺序

| 优先级 | 项目 | 修复方式 | 影响范围 |
|--------|------|---------|---------|
| **P0 阻塞** | B-1 协程池配置复用 | 修订 spec/design/tasks 中协程池限流描述 | spec L18/L148/L242 + design AD-01/AD-04 + tasks 2.2.2 |
| **P0 阻塞** | B-2 Rss.getContentAwait 类型一致性 | 修订 design.md 数据流 1 | design §3.1 L289 |
| **P0 阻塞** | B-3 文章分隔符数据结构 | 修订 design §5.1 + tasks 8.2.2 | allImageUrls 改为 sealed class |
| **P0 阻塞** | B-4 ImageDetailActivity 状态保存 | 补充 design AD-07 + tasks 3.5 任务 | design §2 AD-07 + tasks Phase 3 |
| **P0 阻塞** | B-5 共享元素动画降级 | 补充 tasks 3.1.4 preload 任务 | tasks Phase 3 |
| **P1 遗漏** | O-1~O-8 | 补充 tasks 对应任务 | tasks 多处 |
| **P2 优化** | U-1~U-10 | 评估后纳入或推迟到 P2 | 视情况 |

---

## §5 修订建议

1. **立即修订**（B-1~B-5）：在用户审查通过前，必须修订 5 个阻塞点
2. **补充任务**（O-1~O-8）：在 tasks.md 新增对应任务，确保实施时不遗漏
3. **优化建议**（U-1~U-10）：作为 P2 长期建议保留，不阻塞 V1 实施

修订后重新提交 V2 设计方案，再次用 AskUserQuestion 询问用户审查。

---

# V3 二次深度审查报告（V2 修订后）

> 审查时间：2026-07-26（V2 修订完成后）
> 审查触发：用户反馈"确定全面审查分析完善了？没有任何阻塞点，或者是设计不合理的地方？并且必要的调试日志都已经添加了？"
> 审查方法：主代理对照 `logging-during-refactoring.md` 规范 10 类必加日志场景 + 并发安全/索引映射/内存/协程四维度交叉验证
> 审查结论：**需调整**（5 个新阻塞点 + 5 个设计不合理点 + 日志模板与规范差距）

---

## §6 V3 新增阻塞点（B-6~B-10，必须修复）

### B-6：ImagePlay.allImageUrls 多线程并发访问未保护（V3 新增）

**问题**：
- V2 将 allImageUrls 改为 `MutableList<ImageCanvasItem>`（sealed class）
- 但三处并发访问未同步：
  1. ImageCanvasAdapter.onBindViewHolder（主线程读）
  2. ImageCanvasViewModel.loadNextArticle（协程写）
  3. ImageDetailActivity.onCreate（主线程读，过滤 ImageItem 提取 url）
- MutableList 非线程安全，并发修改触发 `ConcurrentModificationException` 或 `IndexOutOfBoundsException`

**证据**：
- design.md AD-01 Consequences：「协程池配置复用」但未提及 allImageUrls 同步保护
- design.md §4.2 修改文件：`allImageUrls: MutableList<ImageCanvasItem>`
- tasks.md 5.1.3：「appendNextArticleImages() 含 @Synchronized」——仅方法级同步，但外部读取未保护

**建议修复**：
- 方案A（推荐）：改用 `MutableStateFlow<List<ImageCanvasItem>>` 替代 MutableList，Flow 天然线程安全
  ```kotlin
  private val _allImageUrls = MutableStateFlow<List<ImageCanvasItem>>(emptyList())
  val allImageUrls: StateFlow<List<ImageCanvasItem>> = _allImageUrls.asStateFlow()
  fun appendItems(items: List<ImageCanvasItem>) { _allImageUrls.update { it + items } }
  ```
- 方案B：保留 MutableList，但所有读写都通过 `@Synchronized` 方法封装
  ```kotlin
  @Synchronized fun getAllItems(): List<ImageCanvasItem> = allImageUrls.toList()
  @Synchronized fun appendItems(items: List<ImageCanvasItem>) { allImageUrls.addAll(items) }
  @Synchronized fun clearAll() { allImageUrls.clear() }
  ```
- Adapter 读取时先 `val snapshot = ImagePlay.getAllItems()` 拿到不可变副本

---

### B-7：列表 position 与大图 imageIndex 索引映射缺失（V3 新增）

**问题**：
- 列表模式 RecyclerView 的 position 包含图片项 + 文章分隔符（ImageCanvasItem.ImageItem + ArticleDivider）
- 大图模式 ViewPager2 的 position 是纯图片索引（0,1,2,3...）
- design.md AD-02 仅说「初始定位到用户点击的图片索引」，未说明 position 如何转换
- 实施时直接传 listPosition 给 ViewPager2.setCurrentItem 会跳到错误的图片

**证据**：
- design.md AD-02 Decision：「从列表模式通过 ActivityOptions.makeSceneTransitionAnimation 共享元素动画过渡到大图模式」
- design.md §3.2 数据流 2：未提及索引映射
- tasks.md 3.1.3：「传递 imageUrls 和 startIndex」——startIndex 是列表 position 还是图片索引未明确

**建议修复**：
- ImageCanvasAdapter 提供双向映射方法：
  ```kotlin
  // 列表 position → 图片索引
  fun listPositionToImageIndex(listPos: Int): Int {
      var imageIdx = -1
      for (i in 0..listPos) {
          if (items[i] is ImageCanvasItem.ImageItem) imageIdx++
      }
      return imageIdx  // 若 items[listPos] 是 ArticleDivider 返回 -1
  }
  // 图片索引 → 列表 position
  fun imageIndexToListPosition(imageIdx: Int): Int {
      var count = -1
      for (i in items.indices) {
          if (items[i] is ImageCanvasItem.ImageItem) count++
          if (count == imageIdx) return i
      }
      return -1
  }
  ```
- ImageGalleryActivity 调用 onItemClick(listPos) → 转换为 imageIdx 传给 ImageDetailActivity
- ImageDetailActivity.setResult 传回 imageIdx → ImageGalleryActivity.onActivityResult 转换回 listPos 调用 scrollToPosition

---

### B-8：协程池重建时进行中任务的处理未定义（V3 新增）

**问题**：
- V2 修订 B-1 引入「监听 LiveEventBus 配置变更事件运行时重建协程池」
- 但进行中的 loadJob 仍在旧协程池上运行，重建后新旧协程池共存
- 旧协程池未 shutdown，导致线程泄漏
- 新请求在新协程池上运行，但旧请求结果可能仍写入 allImageUrls，造成数据竞争

**证据**：
- design.md AD-01 Consequences：「监听 LiveEventBus 配置变更事件运行时重建协程池」
- tasks.md 2.2.2：「含 LiveEventBus 配置变更监听重建协程池」
- 均未说明旧协程池处理方式

**建议修复**：
- 重建流程：
  1. 收到配置变更事件 → `loadJob?.cancel()` 取消当前加载
  2. `oldExecutor.shutdown()` 关闭旧协程池（等待进行中任务最多 5 秒）
  3. `newExecutor = Executors.newFixedThreadPool(AppConfig.updateCacheThreadCount)`
  4. `loadNextArticle()` 用新协程池重新触发加载
- 日志：`AppLog.put("CoroutinePool: rebuild oldSize=${oldSize} newSize=${newSize}")`

---

### B-9：ImagePlay 单例 allImageUrls 跨订阅源切换未清理（V3 新增）

**问题**：
- V2 O-3 修复了「ImageGalleryActivity.onDestroy 清理 allImageUrls」
- 但用户在图片播放器内切换到另一个图片订阅源（不退出 Activity，仅刷新数据）时，allImageUrls 不会被清理
- 旧订阅源的图片 URL 残留，新订阅源加载后两份 URL 混合，导致显示错误

**证据**：
- tasks.md 5.1.4：「ImageGalleryActivity.onDestroy 调用 clearImageCanvasState()」——仅 onDestroy 触发
- 未覆盖场景：用户在图片播放器内通过「换源」或「下一个订阅源」切换数据源

**建议修复**：
- ImagePlay 新增 `@Synchronized fun resetForNewSource()` 方法
- 在以下场景调用：
  1. ImagePlay.init(rssSource, rssArticles, position) 初始化新订阅源时
  2. 用户主动切换订阅源时
- 日志：`AppLog.put("ImagePlay: resetForNewSource cleared=${allImageUrls.size}")`

---

### B-10：图片高度动态更新导致 ViewHolder 闪烁（V3 新增）

**问题**：
- design.md AD-03：「默认高度 60% 屏幕高度 → RequestListener.onResourceReady 后动态计算实际高度」
- 但 ViewHolder 复用时，旧图片的实际高度会先显示，新图片加载完成后才更新，造成「先高后矮再高」的闪烁
- RecyclerView 的 setHasFixedSize(true) 与动态高度冲突

**证据**：
- design.md AD-03 Decision：「通过 ViewGroup.LayoutParams 更新 ViewHolder 高度」
- tasks.md 2.3.2：「实现动态高度计算（height = screenWidth * bitmap.height / bitmap.width）」
- 未提及 ViewHolder 复用时的清空策略

**建议修复**：
- onBindViewHolder 中先重置高度为默认值（屏幕高度 60%）：
  ```kotlin
  val lp = itemView.layoutParams
  lp.height = defaultHeight  // 屏幕高度 60%
  itemView.layoutParams = lp
  Glide.with(...).load(url).listener(object : RequestListener {
      override fun onResourceReady(...) {
          // 计算实际高度后更新
          val actualHeight = screenWidth * bitmap.height / bitmap.width
          val limitedHeight = minOf(actualHeight, maxLimitHeight)
          if (lp.height != limitedHeight) {
              lp.height = limitedHeight
              itemView.layoutParams = lp
          }
      }
  }).into(imageView)
  ```
- 设置 `recyclerView.setHasFixedSize(false)` 允许动态高度
- onViewRecycled 中调用 `Glide.with(imageView).clear(imageView)` 释放图片资源
- 日志：`AppLog.put("ImageCanvasAdapter: onViewRecycled position=$position")`

---

## §7 V3 新增设计不合理点（D-1~D-5，建议优化）

### D-1：分页加载触发阈值 3 项可能过早

**问题**：
- design.md AD-04：「触发条件：剩余未可见项数 ≤ 3」
- 但图片高度默认 = 屏幕高度 60%，3 项 = 1.8 倍屏幕高度
- 用户刚滚动约 2 屏就触发加载，可能体验过早（用户尚未真正到达底部）

**建议**：
- 改为阈值 1 项（即 lastVisibleItemPosition >= totalItemCount - 2）
- 或抽取为常量 `PAGINATION_THRESHOLD = 2`，便于后续调整
- 配合 U-1（PAGINATION_THRESHOLD 常量化）合并修复

### D-2：横屏默认高度 60% 屏幕高度过小

**问题**：
- design.md AD-03：「默认高度：屏幕高度的 60%」
- 横屏时屏幕高度 = 竖屏屏幕宽度，60% 横屏高度 ≈ 60% 竖屏宽度，图片显示面积过小
- 用户横屏浏览时图片几乎只占屏幕一小块

**建议**：
- 横屏时默认高度改为屏幕高度的 80%（即屏幕宽度 * 0.8）
- 通过 `resources.configuration.orientation == Configuration.ORIENTATION_LANDSCAPE` 判断
- 竖屏保持 60%

### D-3：缺少低内存场景处理

**问题**：
- 垂直画布同时加载多张图片，低内存场景下可能 OOM
- design.md AD-01 Consequences 仅提「Glide.override + setItemViewCacheSize(2) 控制缓存项数」
- 未提及 onTrimMemory 回调时的处理

**建议**：
- ImageGalleryActivity 重写 onTrimMemory：
  ```kotlin
  override fun onTrimMemory(level: Int) {
      super.onTrimMemory(level)
      if (level >= TRIM_MEMORY_RUNNING_LOW) {
          Glide.get(this).trimMemory(level)
          recyclerView.recycledViewPool.clear()
          AppLog.put("ImageGallery: onTrimMemory level=$level cleared")
      }
  }
  ```

### D-4：缺少无障碍支持（contentDescription）

**问题**：
- PhotoView 缩略图未设置 contentDescription
- TalkBack 用户无法获知当前图片位置

**建议**：
- onBindViewHolder 中 `imageView.contentDescription = "图片 ${imageIndex + 1}/${totalImageCount}"`
- 大图模式 ImageDetailAdapter 同样设置

### D-5：缺少大图模式加载进度提示

**问题**：
- design.md AD-02 Consequences：「图片尚未加载完成时共享元素动画可能闪烁」
- 但大图模式加载原图期间未显示加载进度
- 用户从缩略图点击进入大图，看到空白屏幕可能误以为卡死

**建议**：
- ImageDetailAdapter 中显示 ProgressBar（覆盖在 PhotoView 上）
- Glide RequestListener.onResourceReady 时隐藏 ProgressBar
- 加载超过 2 秒显示「加载中...」文字提示

---

## §8 日志模板与规范差距分析（V3 新增）

### 对照 `logging-during-refactoring.md` 规范 10 类必加场景

| # | 规范要求场景 | 当前 tasks.md V2 模板 | 差距 | V3 修复 |
|---|------------|---------------------|------|---------|
| 1 | 播放器状态切换 | 「状态变更 LoadState oldState→newState」 | ✅ 覆盖 | 保留 |
| 2 | 错误处理路径 | 「异常捕获 onLoadFailed e=${e.message}」 | ⚠️ 缺调用栈关键帧 | 补充 `e.stackTraceToString().take(5)` |
| 3 | 网络请求关键节点 | ❌ 缺失 | Rss.getContentAwait 请求发起/成功/失败未记录 | 新增 `RssFetch: start/end url=/path/${id} cost=${ms} code=${code}` |
| 4 | 数据库异常 | ❌ 缺失 | 本场景无数据库操作 | N/A（本 spec 不涉及） |
| 5 | 类型转换 | ❌ 缺失 | List<RssImage> → List<String> 转换未记录 | 新增 `TypeConvert: List<RssImage> size=${n} → List<String> size=${m}` |
| 6 | 加密解密 | ❌ 缺失 | 本场景无加密操作 | N/A（本 spec 不涉及） |
| 7 | 生命周期关键节点 | ❌ 缺失 | Activity/ViewModel/Adapter 创建销毁未记录 | 新增 `onCreate/onDestroy/onCleared hashCode=${hashCode}` |
| 8 | 配置变更 | ❌ 缺失 | 协程池重建未记录 | 新增 `CoroutinePool: rebuild oldSize=${old} newSize=${new} source=${eventSource}` |
| 9 | 触摸事件流转 | ❌ 缺失 | 点击/长按事件未记录 | 新增 `Touch: onItemClick position=${pos} imageIdx=${idx}` + `onLongClick position=${pos} action=save` |
| 10 | JS 交互 | ❌ 缺失 | 本场景无 JS 交互 | N/A（本 spec 不涉及） |

### 当前模板未区分永久日志 vs 临时日志

**问题**：V2 模板全部用 `AppLog.put`，未区分：
- 永久日志（错误处理/状态切换/协程取消）→ 用 AppLog.put（写入文件，用户可查看）
- 临时日志（方法入口/出口/触摸事件）→ 用 Log.d（仅 logcat，验证后移除）

**修复**：
- 永久日志（保留）：错误处理、状态切换、协程取消/完成、降级链触发、配置变更、生命周期关键节点
- 临时日志（验证后移除）：方法入口/出口、触摸事件流转、类型转换
- 临时日志统一 Tag：`ImageCanvasDebug`（便于 Grep 一次性移除）

### 当前模板未对应模块 Tag 常量

**问题**：V2 模板用 `ImageCanvasAdapter`/`loadNextArticle` 等，未对应 `logging_rules.md` 模块 Tag 常量

**修复**：本 spec 新增模块 Tag 常量：
- `AppLog.TAG_IMAGE_CANVAS` = "ImageCanvas"
- `AppLog.TAG_IMAGE_DETAIL` = "ImageDetail"
- `AppLog.TAG_IMAGE_PLAY` = "ImagePlay"
- 所有日志使用 `AppLog.putDebugWithTag(TAG_IMAGE_CANVAS, "...")` 形式

### 缺少日志内容脱敏验证

**问题**：V2 模板注「禁止输出域名/URL/源名称」，但未在模板中体现脱敏后的具体格式

**修复**：所有日志模板统一格式：
- URL：`/path/${id}`（路径模式，不含域名和查询参数）
- 源名称：`source=${sourceId}`（仅记录源 ID 编号）
- cookie/token：`***`（完全隐藏）
- 文章标题：`titleLength=${n}`（仅记录长度）

---

## §9 V3 修复优先级与执行顺序

| 优先级 | 项目 | 修复方式 | 影响范围 |
|--------|------|---------|---------|
| **P0 阻塞** | B-6 allImageUrls 并发安全 | 改用 MutableStateFlow 或 @Synchronized 封装 | design.md AD-01 + tasks 5.1.1~5.1.4 |
| **P0 阻塞** | B-7 索引映射 | ImageCanvasAdapter 新增双向映射方法 | design.md AD-02 + tasks 3.1.x + 8.1.x |
| **P0 阻塞** | B-8 协程池重建任务处理 | 重建时取消 loadJob + shutdown 旧池 | design.md AD-01 + tasks 2.2.2 |
| **P0 阻塞** | B-9 跨订阅源切换清理 | ImagePlay 新增 resetForNewSource() | design.md §4.2 + tasks 5.1.x |
| **P0 阻塞** | B-10 ViewHolder 闪烁 | onBindViewHolder 重置高度 + onViewRecycled 清理 | design.md AD-03 + tasks 2.3.x |
| **P1 优化** | D-1~D-5 | 优化项纳入 V3 tasks | tasks 多处 |
| **P0 阻塞** | 日志模板对照规范 10 类 | 重写 AOAdapt 日志模板 | tasks.md 末尾 |

---

## §10 V3 修订结论

V2 修订已完成 B-1~B-5 + O-1~O-8 修复，但深度审查发现：
1. **5 个新阻塞点**（B-6~B-10）：并发安全/索引映射/协程池/内存泄漏/ViewHolder 闪烁
2. **5 个设计不合理点**（D-1~D-5）：分页阈值/横屏高度/低内存/无障碍/加载进度
3. **日志模板差距**：未对照规范 10 类必加场景，缺网络请求/生命周期/配置变更/类型转换/触摸事件等关键场景，未区分永久vs临时日志

V3 修订将在 design.md / spec.md / tasks.md 中补充上述修复，确保：
- 所有阻塞点均有明确修复方案和任务编号
- 日志模板严格对照规范 10 类场景，区分永久/临时日志
- 实施时可精准定位问题（开启调试日志时所有关键路径均有日志覆盖）

---

# V4 源码深度审查报告（V3 修订后）

> 审查时间：2026-07-26（V3 修订完成后）
> 审查触发：用户反馈"再次全面审查你的设计文档是否有阻塞点，设计不合理的地方，尤其是要结合项目当前源码深入分析，并且要符合当前项目的整体架构！"
> 审查方法：主代理直接 Read 真实源码（ImageGalleryActivity / ImagePlay / ReadRss / AppConfig / AppLog / Rss.kt / ImageGalleryViewModel / ImageArticlePagerAdapter），逐一核实设计文档中的字段名/方法名/类名/调用链
> 审查结论：**需调整**（4 个新阻塞点 B-11~B-14，均为设计文档与源码不符）

---

## §11 V4 源码审查发现的阻塞点（B-11~B-14，必须修复）

### B-11：Rss.getContentAwait 返回类型错误（V4 新增，严重）

**源码事实**：
- 文件：`app/src/main/java/io/legado/app/model/rss/Rss.kt:123-127`
- 真实签名：`suspend fun getContentAwait(rssArticle: RssArticle, ruleContent: String, rssSource: RssSource): String`
- **返回类型是 `String`（文章正文 HTML），不是 `List<RssImage>`**

**设计文档错误**：
- design.md AD-01 / AD-09：假设 Rss.getContentAwait 返回 List<RssImage>
- V2 B-2 修复方案：「Rss.getContentAwait 返回 List<RssImage>，需提取 imageUrls.map { it.url }」——错误
- V3 日志模板 T5：「类型转换-List<RssImage>→List<String>」——错误
- tasks.md 1.5.2：「实现 loadInitialArticle() 协程加载首篇文章图片」中调用 Rss.getContentAwait——返回类型错误

**实际数据流**（来自 ImageGalleryViewModel.kt:57-95 真实实现）：
```
1. loadArticleContent(article) 调用 Rss.getContentAwait 获取 body: String
2. parseImageUrls(body, article.link, ruleImage, rssSource) 解析为 List<String>
3. imageUrlsLiveData.postValue(urls)
```

**修复方案**：
- design.md AD-01 / AD-09：将「Rss.getContentAwait 返回 List<RssImage>」改为「Rss.getContentAwait 返回 String body，调用 parseImageUrls(body, ...) 解析为 List<String>」
- V3 日志模板 T5：改为「TypeConvert: body String -> List<String> urlList via parseImageUrls size=$n」
- tasks.md 1.5.2：明确调用 Rss.getContentAwait 后必须调用 parseImageUrls 解析

---

### B-12：RssImage 数据类不存在（V4 新增，严重）

**源码事实**：
- Grep `data class RssImage|class RssImage` 在 `app/src/main/java/io/legado/app/model/rss/` 返回 **No matches found**
- 项目中不存在 RssImage 数据类

**设计文档错误**：
- V2 B-2 修复方案明确引用「List<RssImage>」类型
- V3 AD-09 中 allImageUrls 改为 `MutableList<ImageCanvasItem>`（正确），但仍残留 RssImage 引用

**修复方案**：
- 删除所有 RssImage 引用
- 统一使用 `List<String>` 作为图片 URL 列表类型
- ImageCanvasItem.ImageItem.url 字段类型保持 String

---

### B-13：ReadRss 路由回退字段名错误（V4 新增，严重）

**源码事实**：
- 文件：`app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt:24-44`
- 真实路由逻辑：
  ```kotlin
  val type = record.type
  if (type == 2) { → VideoPlayerActivity }
  if (type == 1) { → readNoHtml → ImageGalleryActivity }
  // type=0 → ReadRssActivity（网页模式）
  ```
- **路由判断字段是 `type`，不是 `articleStyle`**

**设计文档错误**：
- spec.md R1.19：「articleStyle==2 路由回退保留」——字段名错误
- design.md 数据流 1 L272：「articleStyle==2 且用户选网页模式 → ReadRssActivity」——错误
- tasks.md 5.4.1：「验证 ReadRss.kt L41-43 路由回退逻辑不变（articleStyle==2）」——验证方法错误
- spec.md §2.1：「articleStyle==2 路由回退（ReadRss.kt L41-43）」——字段名错误

**实际逻辑说明**（ReadRss.kt:41-43 注释）：
```
// 回退说明（用户2026-07-26 10:09 反馈）：
// 即使订阅源 articleStyle=2（图片列表样式），用户主动选择网页模式就必须走网页模式
// 禁止"自动识别为图片就转为图片查看器"，图片查看器入口改为用户主动选择
```
- `type` 字段来自 `RssReadRecord.type`，由用户在 RssArticlesFragment 主动选择（图片/视频/网页）
- `articleStyle` 是 RssSource 的字段（订阅源样式配置），但路由判断用的是 `record.type`

**修复方案**：
- spec.md R1.19：将「articleStyle==2 路由回退」改为「type==1 路由到 ImageGalleryActivity，type==0 路由到 ReadRssActivity」
- design.md 数据流 1：修正字段名为 `record.type`
- tasks.md 5.4.1：验证方法改为「Read 确认 ReadRss.kt L24-44 中 type==1 走 readNoHtml，type==0 走 ReadRssActivity」

---

### B-14：ImagePlay 现有字段与设计文档假设不符（V4 新增，严重）

**源码事实**：
- 文件：`app/src/main/java/io/legado/app/ui/image/ImagePlay.kt:14-46`
- 真实字段清单：
  ```kotlin
  object ImagePlay {
      var rssArticles: List<RssArticle>?
      var rssArticleIndex: Int              // 设计文档假设的 "position" 实际是 rssArticleIndex
      var rssSource: RssSource?
      var rssSortName: String?
      var rssSortUrl: String?
      var rssNextPageUrl: String?
      var rssArticlePage: Int
      var rssArticlesHasMore: Boolean
      var lastPlayedArticleLink: String?
      var currentImageUrls: List<String>?  // 现有字段，单文章缓存
      fun clear() { ... }
  }
  ```
- **不存在的字段**：
  - `position`（设计文档假设）→ 实际是 `rssArticleIndex`
  - `currentPlayHeaders`（design.md AD-09 假设）→ 不存在，需要从 `rssSource` 中获取 header
  - `allImageUrls`（V2/V3 假设新增）→ 不存在，需要新增
  - `loadedArticleIndices`（V2/V3 假设新增）→ 不存在，需要新增
  - `preloadedArticles`（V2/V3 假设新增）→ 不存在，需要新增

**设计文档错误**：
- design.md AD-09：「ImagePlay.currentPlayHeaders 跨文章复用」——字段不存在
- design.md AD-09：「`ImagePlay.allImageUrls`」——字段不存在，需明确为新增
- spec.md R1.18：「Cookie/Header 复用（ImagePlay.currentPlayHeaders）」——字段不存在
- V3 AD-12 resetForNewSource 引用 `_allImageUrls.value`——前提是 allImageUrls 是 StateFlow，但现状是没有该字段

**修复方案**：
- 设计文档中所有 `position` 改为 `rssArticleIndex`
- 删除 `currentPlayHeaders` 引用，改为「从 `rssSource` 中提取 header」或新增 `currentPlayHeaders: Map<String, String>?` 字段
- 明确 allImageUrls / loadedArticleIndices / preloadedArticles 为新增字段（V3 已说明，但需强调现状不存在）
- 保留现有 `currentImageUrls` 字段（单文章缓存），新增 `allImageUrls`（跨文章累积），两者用途不同

---

## §12 V4 源码审查确认的正确点（设计文档与源码一致）

### C-1：ImageGalleryActivity 双 ViewPager2 嵌套架构 ✅
- 源码：`ImageGalleryActivity.kt:45-46` 继承 `VMBaseActivity<ActivityImageGalleryBinding, ImageGalleryViewModel>()` + `ImageArticlePagerAdapter.OnArticleCallback`
- 设计文档 AD-01 描述的「双 ViewPager2 嵌套」真实存在

### C-2：Bug2 WebView 预热 forEach 覆盖问题 ✅
- 源码：`ImageGalleryActivity.kt:169-173`
  ```kotlin
  needPreheat.forEach { domain ->
      val preheatUrl = "https://$domain/"
      binding.webviewPreheat.loadUrl(preheatUrl)
  }
  ```
- 设计文档 AD-05 描述的 Bug2 真实存在，forEach 同步调用 loadUrl 导致循环覆盖
- 修复方案（串行队列）合理

### C-3：WebView 预热现有字段名 ✅
- 源码：`pendingPreheatDomains: mutableSetOf<String>()` / `preheatedDomains: mutableSetOf<String>()` / `isFirstPreheatCompleted` / `pendingImageUrls`
- 设计文档 V3 AD-05 假设的 `preheatQueue: MutableList<String>` 应改用现有字段 `pendingPreheatDomains`（复用而非新建）

### C-4：AppConfig 配置项默认值 ✅
- 源码：`AppConfig.kt:443-476`
  - `searchThreadCount` 默认 32 ✅
  - `updateCacheThreadCount` 默认 16 ✅
  - `imageLoadConcurrency` 默认 5 ✅
  - 还有 `rssParseConcurrency` 默认 3（设计文档未提及，可作为 P2 优化）
- 设计文档 V3 B-1 修复方案引用的默认值全部正确

### C-5：AppLog 模块 Tag 常量现状 ✅
- 源码：`app/src/main/java/io/legado/app/constant/AppLog.kt:13-19`（路径不是 help/http/）
- 现有 Tag：`TAG_WEB_BOOK` / `TAG_ANALYZE` / `TAG_HTTP` / `TAG_WEB_VIEW` / `TAG_DATA` / `TAG_RSS` / `TAG_CONTENT`
- **不存在** `TAG_IMAGE_CANVAS` / `TAG_IMAGE_DETAIL` / `TAG_IMAGE_PLAY`（需新增，V3 设计正确）
- AppLog API：`put` / `putError` / `putWarn` / `putInfo` / `putDebug` / `putDebugWithTag` 全部存在 ✅

### C-6：ImageGalleryViewModel 现有架构 ✅
- 源码：`ImageGalleryViewModel.kt:39-41` 含 `imageUrlsLiveData: MutableLiveData<List<String>>` / `loadingLiveData: MutableLiveData(false)`
- 源码：`ImageGalleryViewModel.kt:57` 含 `loadArticleContent(article: RssArticle)` 方法
- 内部调用 `Rss.getContentAwait` 获取 body，然后用 `parseImageUrls(body, ...)` 解析
- **设计文档建议**：V3 设计的 ImageCanvasViewModel 应保留 LiveData 模式，可扩展而非完全重写

### C-7：ImageArticlePagerAdapter 现有架构 ✅
- 源码：`ImageArticlePagerAdapter.kt:24` 类签名 `class ImageArticlePagerAdapter(private val context: Context, ...)`
- 含 `updateCurrentArticle(urls: List<String>)` / `OnArticleCallback` 接口
- 含 `onArticleBind(article, position)` 回调
- 设计文档 AD-01 描述的「ImageArticlePagerAdapter 与 ImagePageAdapter 耦合」真实存在

### C-8：VMBaseActivity 基类 ✅
- 源码：`ImageGalleryActivity.kt:45` 继承 `VMBaseActivity<ActivityImageGalleryBinding, ImageGalleryViewModel>()`
- 设计文档 R1.3 假设 ImageDetailActivity 继承 VMBaseActivity 正确

---

## §13 V4 修订项汇总

### 修订项 1：Rss.getContentAwait 返回类型修正（B-11）
- design.md AD-01 / AD-09：将「Rss.getContentAwait 返回 List<RssImage>」改为「返回 String body，调用 parseImageUrls 解析为 List<String>」
- tasks.md 1.5.2：明确调用 Rss.getContentAwait 后调用 parseImageUrls
- V3 日志模板 T5：改为「TypeConvert: body String -> List<String> urlList via parseImageUrls size=$n」

### 修订项 2：删除 RssImage 引用（B-12）
- 全文搜索 `RssImage` 并删除/替换为 `String`
- ImageCanvasItem.ImageItem.url 保持 String 类型

### 修订项 3：ReadRss 路由字段名修正（B-13）
- spec.md R1.19：articleStyle==2 → type==1
- design.md 数据流 1：articleStyle==2 → record.type==1
- tasks.md 5.4.1：验证方法中 articleStyle==2 → type==1

### 修订项 4：ImagePlay 字段名修正（B-14）
- design.md / spec.md / tasks.md 中所有 `position` 改为 `rssArticleIndex`
- 删除 `currentPlayHeaders` 引用，改为「从 rssSource 中提取 header」
- 明确 allImageUrls / loadedArticleIndices / preloadedArticles 为新增字段
- 保留现有 `currentImageUrls` 字段

### 修订项 5：WebView 预热字段名复用（C-3）
- design.md AD-05：`preheatQueue: MutableList<String>` 改为复用现有 `pendingPreheatDomains: MutableSet<String>`

---

## §14 V4 修订结论

V3 修订完成了规范层面的对照（10 类日志场景、协程池配置复用、阻塞点修复），但未深度核实源码事实。V4 通过直接 Read 真实源码发现：

1. **4 个新阻塞点**（B-11~B-14）：均为设计文档与源码不符（返回类型/数据类不存在/字段名错误/字段不存在）
2. **8 个正确点**（C-1~C-8）：双 ViewPager2 架构/Bug2/AppConfig/AppLog/ViewModel/Adapter/VMBaseActivity 与设计文档一致
3. **5 个修订项**：需在 design.md / spec.md / tasks.md 中修正字段名/返回类型/引用

V4 修订后将确保设计文档 100% 基于真实源码，符合项目当前整体架构，可进入实施阶段。
