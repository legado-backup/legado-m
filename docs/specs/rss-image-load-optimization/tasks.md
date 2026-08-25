# 图片订阅源加载优化 — 任务清单（tasks.md）

> 状态：🔄 设计中

## 1. 准备工作

- [ ] 1.1 复核图片订阅源加载链路现状（ImageUrlExtractor / ImagePageAdapter / Rss.getContentAwait）
- [ ] 1.2 确认书源参考机制（ImageProvider 缓存 / BookHelp.saveImages 并发 / 采样解码）
- [ ] 1.3 明确本次范围：不动书源、不动画布模式、不新增数据库表

## 2. 核心实现

### 2.1 URL 缓存层（ImageUrlCache）

- [x] 2.1.1 新增 `ImageUrlCache.kt` 单例：内存 LinkedHashMap(LRU) + ACache 磁盘双级缓存
- [x] 2.1.2 实现 TTL（24h）与容量上限（200 条）淘汰逻辑
- [x] 2.1.3 实现 `get(hash)` / `put(hash, urls)` / `clear()` 方法
- [x] 2.1.4 `ImageUrlExtractor.extractImageList` 入口接入缓存查询，解析成功后写缓存
  - Action: 接入 ImageUrlCache.get 命中直接返回；解析成功后 ImageUrlCache.put
  - Observation: 缓存命中/写入均有 AppLog（TAG_IMAGE_SNIFF）输出
  - Adapt: 缓存 key 用 article.link.hashCode（与 ImageCanvasAdapter 去重用法一致）

### 2.2 图集加载优化（ImageDetailAdapter — V4 架构实际横向浏览适配器；ImagePageAdapter 为旧架构遗留同步同款）

> 实施修正（2026-08-24）：初版设计写 ImagePageAdapter，实测确认当前 V4 架构横向浏览用
> ImageDetailAdapter（ImageGalleryActivity.setupFullscreenViewPager → ImageDetailViewPagerAdapter 继承它），
> ImagePageAdapter/ImageArticlePagerAdapter 为旧架构死代码。垂直画布 ImageCanvasAdapter 已采样（Phase 3.5）。

- [x] 2.2.1 Glide 加载添加 `.override(screenW, screenH)` 采样解码（移除 `DownsampleStrategy.NONE`，保留 dontTransform + 防盗链头）
- [x] 2.2.2 添加 `thumbnail(0.1f)` 渐进式加载
- [x] 2.2.3 首次 bind 以当前定位为起点并发 preload 3 张到磁盘缓存（`PRELOAD_COUNT = 3`）；ImagePageAdapter.updateData 前 3 张并发 preload
- [ ] 2.2.4 验证长按/旋转/缩放等 PhotoView 交互不回归

### 2.3 兼容与日志

- [x] 2.3.1 确认四级降级链（Glide 重试 / Cookie 兜底 / WebView 预热 / 网页模式）不受影响（降级链在 ImageCanvasAdapter，本次未改动；ImageDetailAdapter 无降级链，普通 Glide 加载）
- [x] 2.3.2 关键路径输出 AppLog（缓存命中/未命中、预下载数量）
- [x] 2.3.3 更新 `app/src/main/assets/updateLog.md`（基于 git diff 分析真实变更）

## 3. 验证

- [ ] 3.1 编译门禁：`./gradlew assembleAppDebug`（或 `build-legado.bat`）编译通过
- [ ] 3.2 静态验证：Grep 确认采样/预下载/缓存代码存在且无临时调试日志残留
- [ ] 3.3 真机验证（测试包 io.legado.miss.app.debug）：
  - [ ] 3.3.1 进入图片订阅源图集浏览，首图出现时间对比优化前显著缩短
  - [ ] 3.3.2 切换文章，日志确认 URL 缓存命中（跳过网络请求与 WebView 嗅探）
  - [ ] 3.3.3 图集内左右滑动，后续图片秒开（前 3 张预下载命中）
  - [ ] 3.3.4 防盗链场景（需 Referer/Cookie）加载正常，降级链不误触发
  - [ ] 3.3.5 嗅探不回归（FR-7）：L1 解析不足 3 张的图片订阅源，L2 WebView 嗅探正常触发且能取到图片列表
  - [ ] 3.3.6 翻页不回归（FR-8）：图片画布滚动到底分页加载下一篇正常、图集跨文章切换正常
- [ ] 3.4 文档同步：更新 docs/INDEX.md 状态、相关 project-flow 文档

## AOAdapt 日志

> 实施过程中遇到的问题与调整记录在此（Action / Observation / Adapt）。
