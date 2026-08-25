# 图片订阅源加载优化 — 需求规格（spec.md）

> 状态：🔄 设计中

## Intent

用户反馈：图片类型订阅源加载图片明显比图片类型书源慢，希望参考图片类型书源的页面及加载方式做优化。

本 spec 的目标是：**定位并消除图片订阅源在「URL 解析」与「图片加载」两个环节相对于书源的性能差距**，在不重写订阅源页面架构的前提下，借鉴书源加载机制（本地磁盘缓存 + 内存 LRU + 采样解码 + 并发批量下载）的可复用部分，让图片订阅源的加载体验接近书源图片。

## Scope

### In（本次实现）

1. **图片 URL 解析结果缓存**：将「文章 → 图片 URL 列表」的解析结果缓存（内存 + 磁盘），命中缓存时跳过网络请求与 WebView 嗅探。
2. **图集模式采样解码**：`ImagePageAdapter` 的 Glide 加载由全尺寸解码（`DownsampleStrategy.NONE` + `dontTransform()`）改为按目标显示尺寸采样解码，保留渐进式加载能力。
3. **图集内多图并发预下载**：当前仅预加载「下一张」，改为进入文章后对图片列表前 N 张并发预下载到磁盘缓存。
4. **兼容性保障**：防盗链（Referer/Cookie 注入）、降级链（Glide 重试 / Cookie 兜底 / WebView 预热 / 网页模式回退）在优化后保持可用。

### Out（本次不实现）

1. **不重写订阅源页面为书源阅读页架构**：书源是「章节制 + 本地缓存」架构，订阅源是「流式实时浏览」架构，两者结构差异大，重写风险高、收益不确定。
2. **不改动书源加载机制**（`ImageProvider` / `BookHelp` / `ImageColumn` 保持现状）。
3. **不新增数据库表**：URL 缓存复用现有 `ACache` / Glide 磁盘缓存，不引入新表。
4. **不做全量文章预加载**：仅预下载当前文章图片列表的前 N 张，不预取所有文章。

## Approach

### Selected Approach

采用「**借鉴书源机制、适配订阅源架构**」的分层优化方案：

| 优化点 | 参考书源机制 | 订阅源落地方式 |
|--------|-------------|---------------|
| URL 解析慢（每次切文章网络请求 + WebView 嗅探） | 书源章节内容有缓存归属，不重复解析 | 新增 `ImageUrlCache`：以 article.link hash 为 key 缓存「图片 URL 列表」（内存 + ACache 磁盘），TTL + 容量上限控制 |
| 图集模式全尺寸解码慢 | 书源 `BitmapUtils.decodeBitmap(本地文件, width, height)` 按目标尺寸采样 | `ImagePageAdapter` Glide 加载改为 `.override(screenW, screenH)`（触发采样），保留 `.thumbnail()` 渐进式，放大能力由 PhotoView 基于加载分辨率支撑 |
| 单张预加载带宽利用率低 | 书源 `BookHelp.saveImages` 用 `onEachParallel(concurrency)` 并发下载整章 | 进入文章后对图片列表前 N 张（默认 3）并发 `preload()` 到 Glide 磁盘缓存 |

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 完全照搬书源「下载到本地 book_cache + BitmapLruCache」架构 | 订阅源没有「书籍/章节」的持久化归属概念，URL 缓存无处挂载；与 Glide 磁盘缓存功能重复，且需额外维护路径/清理逻辑，复杂度高 |
| 仅调整 Glide 配置（采样解码 + 多预加载），不加 URL 缓存 | 未解决「URL 解析慢」这一首要瓶颈（文章页网络请求 + 最多 6s WebView 嗅探），效果有限 |
| 预加载所有文章图片 | 网络与内存开销过大，用户不一定会浏览所有文章，浪费资源 |
| 用 Coil / 其他图片库替换 Glide | 项目统一使用 Glide + 自定义 OkHttpModelLoader（防盗链注入），替换成本高、回归风险大，收益不明确 |

### Drawbacks

| 缺点 | 影响 | 接受理由 |
|------|------|---------|
| URL 缓存可能缓存过期导致图片失效 | 需 TTL（建议 24h）与容量上限，并提供「无缓存」开关/清理入口 | 相比每次解析节省 0.5~6s 的收益，过期概率低，可接受 |
| 采样解码后放大查看可能不清晰 | 用渐进式（先采样图后原图）缓解；PhotoView 基于已加载分辨率，常规查看无感 | 换取了首图秒开 + 内存降低，收益大于放大画质损失 |
| 并发预下载增加带宽消耗 | 控制并发数（前 3 张）与总量，仅当前文章内 | 图片通常较小，且磁盘缓存可复用，可接受 |
| 图集模式与画布模式加载策略不完全一致 | 两套 Adapter 分别适配，维护成本略增 | 画布模式（ImageCanvasAdapter）已有采样 + 金字塔路由，本次仅统一策略不强行合并代码 |

### Prior Art

- 书源图片加载机制：`ImageProvider`（BitmapLruCache + 本地磁盘缓存 + 采样解码 + `cacheImageAsync` 预加载）、`BookHelp.saveImages`（`onEachParallel` 并发下载）。
- 订阅源现有优化：`ImageUrlExtractor` 三层降级链路（L1 静态解析 / L2 WebView 嗅探 / L3 合并）、`ImageCanvasAdapter` 图片金字塔 + 渐进式加载、`preloadAround` 前后各 1 张预加载。
- 现有 spec：`image-sniffer-optimization`、`image-canvas-3fix-20260728`、`image-player-vertical-canvas-optimization`、`image-gallery-activity`。

## Requirements

### 功能需求

| 编号 | 需求 | 验收标准 |
|------|------|---------|
| FR-1 | 文章图片 URL 解析结果可缓存 | 首次解析后，二次进入同一文章命中缓存，日志显示跳过网络请求与 WebView 嗅探 |
| FR-2 | URL 缓存带 TTL 与容量上限 | 超过 TTL 或容量上限自动清理，不无限膨胀 |
| FR-3 | 图集模式采样解码 | 进入图集浏览，大图按屏幕尺寸解码，首图出现时间显著缩短，无 OOM |
| FR-4 | 图集内多图并发预下载 | 进入文章后前 3 张图片预下载到磁盘缓存，滑动到后续图片秒开 |
| FR-5 | 防盗链与降级链不回归 | 采样解码/预下载后，Referer/Cookie 注入、四级降级链仍正常工作 |
| FR-6 | 不破坏画布模式现有能力 | ImageCanvasAdapter 的长图金字塔、渐进式加载行为不变 |
| FR-7 | 图片订阅源嗅探不回归（用户硬约束） | 优化后 `ImageUrlExtractor` L2 WebView 嗅探链路仍正常触发：L1 静态解析 < 3 张时，嗅探能获取图片 URL 列表，日志确认 L2 正常执行 |
| FR-8 | 下一页翻页不回归（用户硬约束） | 优化后图片画布分页加载 / 图集跨文章切换仍正常：滚动到底触发 `loadNextArticle`，下一文章图片正常加载展示 |

### 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-1 | 兼容性 | 不新增数据库表；不改变 `RssSource`/`RssArticle` 实体结构 |
| NFR-2 | 内存安全 | 采样解码 + LRU 上限受 `MemoryPressure` / Glide 内存缓存约束，无 OOM |
| NFR-3 | 可观测性 | 关键路径（缓存命中/未命中、并发预下载数）输出 `AppLog`，便于定位 |
| NFR-4 | 遵循项目规范 | 协程用 `Coroutine.async{}.onError{}.onSuccess{}`；日志用 `AppLog.put()`；不引入新依赖 |

## Scenarios

### SC-1 进入图集浏览（首图秒开）

用户点击图片类型订阅源的一篇文章 → 命中 URL 缓存 → 跳过网络请求与 WebView 嗅探 → 首图按屏幕尺寸采样解码快速显示。

### SC-2 切换文章（无需重新解析）

用户上下滑动切换文章 → `ImageUrlExtractor` 命中该文章 URL 缓存 → 直接返回图片列表 → 无需等待文章页请求 + 最多 6s 的 WebView 嗅探。

### SC-3 图集内左右滑动（秒开）

用户左右滑动图集内图片 → 前 3 张已并发预下载到磁盘缓存 → Glide 从磁盘缓存解码显示，接近秒开。

### SC-4 缓存过期（自动回源）

缓存超过 TTL（24h）后 → 自动失效 → 重新走原有 L1/L2/L3 解析链路 → 功能不退化。

### SC-5 防盗链场景不回归

图片站有防盗链（需 Referer/Cookie）→ 采样解码与预下载仍通过 `OkHttpModelLoader.sourceOriginOption/refererOption` 注入请求头 → 加载成功，四级降级链在失败时正常触发。
