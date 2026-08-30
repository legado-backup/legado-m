# 真机测试问题修复 - 技术设计

> **创建时间**：2026-07-27
> **依据**：spec.md（根因均经源码+07-27 真机日志交叉验证）
> **架构原则**：精准修改（只触碰必须触碰的部分）/ 协程链式封装 / AppLog.put 关键日志（release 可输出）/ URL 全程 sanitizeUrl 脱敏 / WebView 操作必在 UI 线程

---

## 1. V-P0-1：PlayerInstancePool 并发崩溃

### 根因锚点
- `PlayerInstancePool.kt:54-56` `sharedTrackSelector` app 级 lazy 单例；`:104` 构建时 `.setTrackSelector(sharedTrackSelector)`
- `DefaultTrackSelector.init()` 的 `checkState`：一个 TrackSelector 同一时刻只能绑定一个存活 Player。并发 acquire（R5 双命中 / ViewPager2 双 Fragment 并发 prepare）→ 二次 init → `IllegalStateException`（FATAL ×5 实证）
- `Exo2MediaPlayer.kt:455-457` `mTrackSelector = PlayerInstancePool.sharedTrackSelector` 同样引用单例

### 修复方案
1. **每实例独立 TrackSelector**：删除 `sharedTrackSelector` 单例，新增 `createTrackSelector(): DefaultTrackSelector` 工厂方法；`acquire` 新建实例时各建各的
2. **复用实例处理**：池化回收的实例已持有自己的 TrackSelector，`recycle` 时清除 `TrackSelectionOverride`（现有逻辑保留），不跨实例共享
3. **Exo2MediaPlayer 侧**：`mTrackSelector == null` 时改为 `PlayerInstancePool.createTrackSelector()`（新实例）或沿用池实例自带 selector
4. **共享保留项**：`sharedRendererFactory`（无状态）+ `DefaultAllocator` 内存池（线程安全）继续共享，不受影响

### 成熟方案参考
ExoPlayer 官方多实例场景（如 ExoPlayer 多窗口 demo）均为每 player 独立 TrackSelector；共享仅限无状态组件。

### 日志设计
- `PlayerPool: acquire hit/miss, poolSize=N, selector=${hashCode}`（验证每实例 selector 不同）
- recycle 时 `PlayerPool: recycled, override cleared`

### 验证
并发 prepare 场景（快速上下滑切视频）0 FATAL；日志确认各实例 selector hash 不同。

---

## 2. I-P0-1：图片详情全量 403

### 根因锚点
- `ImageCanvasAdapter.kt:199-209 / :403-415`：防盗链头注入依赖 `ImagePlay.rssSource?.sourceUrl`（sourceOriginOption）+ `ImagePlay.rssArticles?.getOrNull(articleIndex)?.link`（refererOption）
- 任一值为 null → 请求无 Referer/Origin → 图床 403（09:41 会话 86+ 次实证；数据层 12/12 成功非空，URL 解析正常）
- 旧路径 `ImagePageAdapter.kt:97-100` 由 Activity 构造参数显式传入，不依赖全局态

### 修复方案
1. **显式传参替代全局态**：`ImageGalleryActivity` 启动时将 `sourceOrigin`（源 URL）与每图 `referer`（文章 link）通过 ViewModel/Intent 显式持有并传入 Adapter，与 `ImagePlay` 全局态解耦（保留全局态作兜底，不删除以免影响其他入口）
2. **加载前校验**：bind 时若 origin/referer 均缺失 → `AppLog.put` WARN（含 position、articleIndex、字段缺失项），并尝试从 ImagePlay 兜底回填一次
3. **articleIndex 映射核查**：确认 V4 数据流中 item.articleIndex 与 ImagePlay.rssArticles 下标一致性（实施时首查项；若错位则修正映射而非兜底）

### 成熟方案参考
Glide 官方推荐 per-request `RequestOptions` 注入（项目已有 `OkHttpModelLoader.sourceOriginOption/refererOption` 机制），问题在于取值来源的可靠性而非机制本身。

### 日志设计
- headers 缺失 WARN：`ImageLoad: headers missing, pos=N, articleIndex=M, hasSource=X, hasArticles=Y`
- 403 计数：`ImageLoad: 403 count=N, pos=M`（同 URL 去重，避免 86 行刷屏）

### 验证
站点E 场景连续滑动加载成功率 ≥95%；logcat 无明文域名（urlPath 脱敏）。

---

## 3. I-P0-2：图片降级链断裂

### 根因锚点
- `ImageGalleryActivity.kt:182-205` `onWebViewFallback` 从 Glide RequestListener（工作线程）触发，内部 `webviewPreheat.loadUrl()` 须在 UI 线程 → 异常被吞、预热失效
- 降级阶段无每图独立计数：86 张失败仅 1 张走入降级链

### 修复方案
1. **回调切主线程**：`onWebViewFallback` 内 WebView 相关操作全部 `withContext(Dispatchers.Main)` 包裹（runCatching 不得吞 CancellationException）
2. **每图独立降级状态机**：Adapter 内按 position 维护 `fallbackStage: IntArray/稀疏数组`（0=原始加载 → 1=skipMemory 重试 → 2=换 UA/加头重试 → 3=WebView 预热 → 4=网页模式入口），每次 onLoadFailed 推进一级并日志
3. **预热去重**：`preheatedDomains` 判断保留，但预热完成（onPageFinished/超时 5s）后自动触发该域名下失败图重载

### 日志设计
- `ImageFallback: pos=N stage=X→Y, domain=***`
- `ImageFallback: webview preheat start/done, domain=***`（UI 线程确认）

### 验证
人为断网/改 hosts 制造 403 → 四级降级逐级触发、日志齐全、无异常吞没；预热后重载成功。

---

## 4. V-P1-1：直链后缀识别 + 启发式降级链

### 根因锚点
- `ExoPlayerHelper.kt:430-438` `inferContentTypeByExtension` 仅 `.m3u8/.mpd/.ism`
- `Exo2MediaPlayer.kt:193` UNKNOWN 分支固定 `[HLS, DASH, OTHER]`

### 修复方案
1. **后缀表补齐**：`inferContentTypeByExtension` 增加直链后缀（`.mp4/.mkv/.webm/.flv/.avi/.mov/.ts/.m2ts/.mp3/.m4a/.aac/.flac`）→ `C.TYPE_OTHER`
2. **UNKNOWN 降级链启发式**：`buildFallbackTypes` 的 else 分支改为按 URL 后缀特征排序——直链后缀命中 → `[OTHER, HLS, DASH]`；否则维持 `[HLS, DASH, OTHER]`
3. **统一入口**：启发式判断抽为 `ExoPlayerHelper.guessTypeByUrl(url): Int?`，buildFallbackTypes 与 sniffByExtensionFallback 共用，避免两处后缀逻辑漂移

### 成熟方案参考
ExoPlayer `DefaultMediaSourceFactory` 的 `inferContentType` 同款后缀表（`Util.inferContentType`），本项目与其对齐并扩展。

### 日志设计
- 现有 `ExoFallback: try contentType=$type (#i/n)` 已满足统计；新增 `sniffVideoType: extension fallback hit` 已有

### 验证
.mp4 直链首试即 Progressive（无 MANIFEST_MALFORMED 试错）；m3u8 场景首选 HLS 不回退。

---

## 5. V-P1-2：3003 白名单 + 末端兜底 + 手动入口

### 根因锚点
- `Exo2MediaPlayer.kt:709-712` 白名单缺 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED(3003)`
- `:728-740` isParsingError 嵌套在 isUnrecoverableError 块内 → 3003 整块跳过（死代码）
- `:732` 末端失败时 `currentFallbackIndex < size-1` 为 false → 不发 VIDEO_FALLBACK_WEBVIEW

### 修复方案
1. **白名单补 3003**：`isUnrecoverableError` 增加 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED`
2. **末端兜底直触发**：解析错误分支改为——`currentFallbackIndex < size-1` → tryNextFallback；否则（末端失败）直接 `postEvent(VIDEO_FALLBACK_WEBVIEW)` + `VIDEO_PLAY_ERROR` 提示，不等计数阈值
3. **手动入口**：`VIDEO_PLAY_ERROR` 弹框增加"用 WebView 播放"按钮（VideoPlayerActivity 错误弹框处），点击后发同一事件
4. **保留阈值路径**：decoder 类错误的累计阈值降级逻辑不变

### 日志设计
- 末端触发：`ExoFallback: terminal fallback failed (3003), trigger WebView, urlPath=***`
- 现有 `all fallback exhausted` 保留

### 验证
构造必定 3003 的 URL → 自动切 WebView 一次到位；弹框手动入口可用；`unrecoverable error` 日志含 3003。

---

## 6. N-P1-1：Cronet 恢复迟滞

### 根因锚点
- `CronetInterceptor.kt:107-111` 恢复探测一次成功即切回（2 分钟 6 轮乒乓实证）

### 修复方案
1. **连续成功门槛**：恢复需连续 2 次探测成功（`recoverySuccessCount >= 2` 才切回，失败即清零）
2. **最短降级保持**：降级后 60s 内不探测（`degradedAt` 时间戳 + `RECOVERY_PROBE_INTERVAL_MS` 已有，取 max(60s, 现有间隔)）
3. 探测请求本身超时收紧（≤3s），避免探测阻塞正常请求

### 日志设计
- `CronetInterceptor: recovery probe success 1/2`、`recovered after Ns degraded`（AppLog.put，60s 去重保留）

### 验证
弱网抖动场景（模拟器限速/断网切换）每会话降级 ≤1 次，无 1 分钟内反复切换。

---

## 7. N-P1-2：DohDns IDN 旁路 + 并行 + 负缓存

### 根因锚点
- `DohDns.kt:110-122` 三服务器串行各 3s；IDN（`xn--`）公共 DoH 不收录 → 0/249、avg 244s

### 修复方案
1. **IDN 旁路**：hostname 含 `xn--` 或 `IDN.toASCII` 转换后与原文不同 → 直接 `Dns.SYSTEM.lookup`，跳过 DoH（含日志）
2. **并行查询**：三服务器 `async` 并发 + 首个成功返回（`coroutineScope { select/async }`），单服务器超时 2s，整体 ≤3s
3. **负缓存**：失败结果缓存 30s，期间直接走系统 DNS
4. **成功优先**：最近一次成功服务器置顶（AtomicReference 索引）
5. **缓存键含记录类型**（现有缓存 put/get 处补 type 维度）

### 成熟方案参考
Chromium HostResolver 的 negative caching + OkHttp `Dns` 组合 fallback 惯例。

### 日志设计
- `DohDns: IDN bypass, host=***`、`parallel success server#N, elapsed=Mms`、`negative cache hit, host=***`

### 验证
IDN 域名解析 <500ms；非 IDN 域名 DoH 成功率 >0；无 9s 级阻塞（systrace/日志 elapsed 统计）。

---

## 8. I-P1-1/I-P1-2：图片播放器 UX 对齐

### 设计
1. **工具栏**（对齐 VideoPlayerActivity）：右上角收藏按钮 + 三点菜单（刷新 / 配置 / 浏览器打开原始详情页 / 查看日志）
   - 收藏：复用现有收藏逻辑（RssFavorites），按当前文章 link 收藏
   - 刷新：重新加载当前页全部图片（清 Glide 内存缓存该批 key）
   - 浏览器打开：`openUrl` 当前文章 link
   - 日志：跳转日志查看页（复用视频播放器同入口）
2. **占位底图**：统一 placeholder（灰色底+图标）→ 加载完成 crossfade 替换；失败显示错误占位 + 点击重试
3. **进度指示**：顶部 `第 X/共 Y 张` + 每图加载状态点（加载中/成功/失败），ViewPager2 `onPageSelected` 联动

### 锚点
- `ImageGalleryActivity.kt`（工具栏/menu 注入）、`activity_image_gallery.xml`（布局）、`ImageCanvasAdapter.kt`（placeholder/error 选项）

### 验证
菜单四项功能可用；占位→替换无闪烁；进度指示与滑动联动准确。

---

## 9. P2 收尾项

| 编号 | 设计 | 锚点 |
|------|------|------|
| N-P2-1 | AnalyzeUrl.kt:448 附近 URL 日志改 `sanitizeUrl`；VideoSubTitle 事件源标题脱敏 | AnalyzeUrl.kt / VideoSubTitle 相关 198 行 |
| N-P2-2 | RedirectCache 命中时若跨域名则按目标域修正 Referer；LRU 淘汰加 `synchronized` | RedirectCacheInterceptor.kt:54/:95 |
| I-P2-1 | 大图 `.thumbnail(0.1f)` 渐进加载（先模糊后清晰） | ImageCanvasAdapter RequestOptions 链 |
| T-P2 | ai_test 脚本统计：播放成功率/首帧 READY 率/3003 计数/图片 403 率/降级触发率 | ai_tests/scripts/ 新增 analyze 脚本（复用 review2 分析器改造） |

---

## 10. 全局约束（所有修复必须遵守）

1. 日志一律 `AppLog.put`（release 可输出）+ `sanitizeUrl` 脱敏，禁止明文域名/cookie
2. WebView 操作必在 UI 线程；runCatching 不吞 CancellationException
3. 协程用项目 `Coroutine.async{}...onError{}` 链式封装风格；Glide 异步回调必须 `isGlideUsable()` 守卫
4. 每 Phase 完成后：编译验证 → Grep 临时日志 0 残留 → updateLog.md 基于 git diff 更新
5. R-P1 高亮问题不在本 spec 实施范围，见 `docs/specs/highlight-rule-fix-20260727/`
