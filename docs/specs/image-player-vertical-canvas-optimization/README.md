# 内置图片播放器垂直画布优化方案

> 状态：🔄 实施中（V4 设计审查通过，核心 P0 代码已完成+编译通过，待补全 P1 任务+真机测试）
> 创建时间：2026-07-26
> 任务类型：OpenSpec 四文档之一（功能概述）
> 上游依赖：[player-review-and-optimization](../player-review-and-optimization/README.md)（图片播放器审查与优化整合）

## 1. 功能概述

基于用户 2026-07-26 提出的核心交互重设计诉求——"为什么不是将所有的图片按顺序在一个画布按上到下依次多线程去请求加载获取，当用户点击其中一个图片的时候，再使用现在的这种左右滚动式的播放查看呢？并且一个画布加载所有当看到最后一个用户下拉的时候开始下一个列表内容的加载"——本 spec 单独拆出图片播放器的交互架构重设计，**不再延续 player-review-and-optimization 中"修补双 ViewPager2 嵌套"的路线**，而是从根本上重构为"垂直画布 + 点击进入大图 + 下拉加载下一篇"的现代图片浏览交互模式，对齐小红书/抖音图文/漫画阅读器等主流移动端图片浏览体验。

### 1.1 核心改造一句话总结

**从"双 ViewPager2 嵌套（外层文章垂直切换 + 内层图片水平切换）"重构为"单 RecyclerView 垂直长画布（所有图片按顺序多线程加载）+ 点击进入 ViewPager2 大图模式（左右滑动）+ 滚动到底部自动加载下一篇"**。

### 1.2 现有架构痛点（基于源码与多份审查报告核查）

| # | 痛点 | 源码证据 | 影响 |
|---|------|---------|------|
| 1 | 双 ViewPager2 嵌套生命周期复杂 | ImageArticlePagerAdapter.bind if/else 两分支都新建 adapter（Bug1）；WebView 预热 forEach loadUrl 循环覆盖（Bug2）；loadArticleContent 协程未取消（Bug3） | 适配器复用失效 / 多域名预热失效 / 数据错乱 |
| 2 | 左右滑动查看图片不符合移动端阅读直觉 | ImagePageAdapter 内层 ViewPager2 orientation=horizontal | 用户必须逐张滑动，无法快速概览全部图片 |
| 3 | 跨文章切换交互维度混乱 | 外层垂直 + 内层水平，两个维度同时存在 | 用户认知负荷高，容易误操作 |
| 4 | 跨文章预加载能力薄弱 | preloadNextArticle 仅预加载下一篇 URL 列表，受 ViewPager2 缓存限制 | 上下滑动切换时下一张图片无法立即显示 |
| 5 | 图片加载失败无降级链 | 仅 tvError + btnRetry 内嵌布局 | 单点失败即整体失败，无用户决策入口 |

### 1.3 新架构核心收益

| 维度 | 现有双 ViewPager2 方案 | 本方案（垂直画布+点击大图） |
|------|---------------------|---------------------|
| 阅读直觉 | 左右滑动（西式翻页） | 上下滚动（人类自然阅读习惯，对齐小红书/抖音/漫画阅读器） |
| 快速概览 | ❌ 必须逐张滑动 | ✅ 缩略图快速浏览全部图片 |
| 大图查看 | 直接进入大图 | 点击缩略图按需进入大图（左右滑动） |
| 跨文章加载 | 上下滑动切文章（交互维度混乱） | 下拉到底部自动加载（统一垂直维度） |
| 多线程加载 | ViewPager2 预加载有限（仅相邻 2-3 张） | 全部图片并行加载（Glide 异步 + 线程池限流） |
| 架构复杂度 | 双 ViewPager2 嵌套 + 适配器复用 Bug | 单 RecyclerView + 嵌套 ViewPager2（仅大图模式） |
| 生命周期管理 | 双 ViewPager2 嵌套复杂 | RecyclerView 复用机制成熟 |
| 预加载效率 | 受限于 ViewPager2 缓存 | RecyclerView 可控缓存 + Glide.preload |

## 2. 核心能力

### 2.1 垂直画布列表浏览（List Mode）

- **单 RecyclerView 垂直长画布**：所有图片按顺序自上而下排列，支持垂直滚动浏览
- **多线程并行加载**：所有图片 Glide 异步加载 + 协程池限流（默认 4 并发），不阻塞用户滚动
- **图片尺寸自适应**：宽度填满屏幕（match_parent），高度按图片原始宽高比计算（避免布局抖动）
- **缩略图模式**：默认加载缩略图（Glide override(targetWidth, targetHeight)），点击进入大图时加载原图
- **图片占位与错误处理**：加载中显示 placeholder，加载失败显示错误图标 + 重试按钮

### 2.2 点击进入大图模式（Detail Mode）

- **ViewPager2 左右滑动查看大图**：用户点击任意图片，进入大图模式，支持左右滑动切换图片
- **PhotoView 缩放/旋转/长按**：保留现有 ImagePageAdapter 的 PhotoView 能力（双指缩放、双击切换、旋转、长按保存）
- **初始定位**：大图模式默认定位到用户点击的图片索引
- **沉浸式全屏**：进入大图模式自动隐藏 TitleBar/状态栏/导航栏，单击切换显隐
- **返回列表模式**：系统返回键或下拉手势返回列表（保持点击位置可见）

### 2.3 滚动到底部自动加载下一篇（Pagination）

- **RecyclerView 滚动监听**：监听 LinearLayoutManager 的 `findLastVisibleItemPosition`，接近底部时触发加载
- **加载下一篇图片 URL 列表**：调用 `ImagePlay.preloadNextArticleImages` 解析下一篇文章的图片 URL
- **加载状态指示器**：底部显示"加载中..." / "加载失败 重试" / "没有更多了"
- **去重机制**：`preloadedArticles: MutableSet<String>` 避免重复加载
- **多线程预加载**：加载完成后用 Glide.preload 预加载前 3 张缩略图

### 2.4 保留现有架构能力

- **ImagePlay 单例状态传递**：跨 Activity 传递 rssSource / rssArticles / rssArticleIndex 等字段（V4 B-14：position → rssArticleIndex，删除 currentPlayHeaders，header 从 rssSource 提取）
- **WebView 预热机制**：保留 initPreheatWebView / startPreheat / preheatedDomains，修复 Bug2（串行预热）
- **Cookie/Header 复用**：保留 sourceOriginOption + refererOption 注入机制
- **type==1 路由保留**：保留 ReadRss.kt L24-44 的路由逻辑（V4 B-13：articleStyle → record.type，type==1 走 ImageGalleryActivity，type==0 走 ReadRssActivity）
- **图片旋转工具栏**：保留旋转/重置按钮（仅大图模式显示）
- **图片保存/分享**：保留长按菜单（保存/分享/复制URL）
- **沉浸式 API 升级**：从 SYSTEM_UI_FLAG 升级为 WindowInsetsControllerCompat（对齐视频播放器）

### 2.5 错误降级链（对齐视频播放器）

- **降级1**：Glide 直接加载（含 Referer/Cookie 注入）
- **降级2**：OkHttp + sourceOriginOption + refererOption 兜底
- **降级3**：WebView 预热获取 Cloudflare cookies 后重试
- **降级4**：降级为网页模式（ReadRssActivity，用户主动选择）
- **降级5**：提示用户 + 复制 URL + 浏览器打开

## 3. 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| README.md | `docs/specs/image-player-vertical-canvas-optimization/README.md` | 功能概述（本文件） |
| spec.md | `docs/specs/image-player-vertical-canvas-optimization/spec.md` | 需求规约（Intent/Scope/Approach/Requirements/Scenarios） |
| design.md | `docs/specs/image-player-vertical-canvas-optimization/design.md` | 设计文档（ADR 决策 + 技术要点 + 数据流） |
| tasks.md | `docs/specs/image-player-vertical-canvas-optimization/tasks.md` | 实施任务清单（按 Phase 分层） |

## 4. 与上游 spec 的关系

| 上游 spec | 关系 | 说明 |
|----------|------|------|
| [player-review-and-optimization](../player-review-and-optimization/README.md) | **取代图片部分** | 本 spec 取代 player-review-and-optimization 中所有图片播放器相关任务（R2.1-R2.21、R4.6-R4.18、阶段 4-7、阶段 12、Phase 3-4）。player-review-and-optimization 仅保留视频播放器相关任务（R1.1-R1.9、R4.1-R4.5、R4.24-R4.38、阶段 2-3、阶段 11、Phase 1-2） |
| [image-gallery-activity](../image-gallery-activity/README.md) | **架构升级** | 本 spec 是 image-gallery-activity 的交互架构升级版，原"双 ViewPager2 嵌套"架构废弃，改为"垂直画布 + 点击大图" |
| [exoplayer-resilience](../exoplayer-resilience/README.md) | 无关 | 视频播放器独立优化线，本 spec 不涉及 |

## 5. 已知限制

- **本 spec 不涉及视频播放器**：视频播放器优化仍在 player-review-and-optimization 中进行
- **本 spec 取代 player-review-and-optimization 的图片部分**：原 P0/P1 图片相关任务（R2.x、R4.6-R4.18、阶段 4-7、阶段 12、Phase 3-4）全部废弃，由本 spec 的任务清单替代
- **垂直画布的图片高度计算**：需准确预测图片高度避免布局抖动，对未知宽高比的图片（如 WebP/GIF 动图）需特殊处理
- **大图模式与列表模式的状态同步**：用户在大图模式切换图片后返回列表，列表需滚动到对应位置
- **内存管理**：垂直画布同时加载多张图片可能内存压力大，需配合 Glide 的 lifecycle 和 RecyclerView 的回收机制
- **横屏适配**：横屏时垂直画布体验下降，需评估是否切换为左右滑动模式（保留现有横屏 centerCrop 决策）

## 6. 状态标记

🔄 设计中（V1 初稿，待用户审查）
