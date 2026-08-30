# 图片播放器前置嗅探能力优化 - 功能规范

> **版本**：v1
> **创建日期**：2026-07-27
> **状态**：待审查

---

## 一、核心问题

### 1.1 问题概述

图片播放器前置嗅探能力严重缺陷：用户不写内容规则（ruleContent）和图片规则（ruleImage）时，无法嗅探图片列表，导致图片播放器无图可显。

### 1.2 用户场景

#### 场景1：用户写内容规则（ruleContent / ruleImage）

**当前行为**：按用户规则加载图片列表，调用 `Rss.getContentAwait(article, ruleContent, rssSource)` 获取 body，再用 `ruleImage` 选择器提取图片 URL。

**问题**：
- 防盗链场景支持不足（Referer/Cookie 注入依赖源码硬编码）
- 部分站点 JS 渲染导致 ruleContent 取不到正确内容

**期望**：
- 优先按用户规则加载（不破坏现有逻辑）
- 增强防盗链通用处理（注入 Referer/Cookie/User-Agent）
- 用户规则失败时降级到无规则嗅探

#### 场景2：用户不写内容规则

**当前行为**：强制用 `body@html` 兜底，调用 `Rss.getContentAwait(article, "body@html", rssSource)` 获取整个 body HTML，再用 5 级静态策略解析。

**问题**：
- JS 渲染页面（Vue/React/Angular SPA）body 几乎为空，无图可提取
- 静态 HTML 站点丢失 `<picture>/<source>` / CSS background-image / og:image / Script JSON 等格式图片
- 懒加载属性覆盖不全
- 策略4 误匹配非图片 URL（JS/CSS/API）

**期望**：
- 静态解析增强：补充 `<picture>/<source>` / CSS background-image / og:image / Script JSON / JS 变量 / srcset 多分辨率
- WebView 嗅探层：JS 渲染页面通过 BackstageWebView 加载，拦截 shouldInterceptRequest 中的图片资源
- JS hook 注入：hook `Image.src` setter / `fetch` / `XHR` / `IntersectionObserver` 捕获动态图片 URL

### 1.3 日志证据

来自 `docs/temp-analysis/image-sniffer-current-analysis-20260727.md` 的源码分析：
- `ImageCanvasViewModel.kt:278` 强制 `body@html` 兜底
- `ImageCanvasViewModel.kt:287` 单次 `Rss.getContentAwait` 调用，无 WebView 渲染能力
- `parseImageUrls` 5 级策略全部基于字符串/正则，无 JS hook
- `BackstageWebView.kt:328-364` 已实现 `shouldInterceptRequest` 但图片嗅探未调用

---

## 二、验收标准

### 2.1 P0 验收（必须达到）

#### AC-P0-1: WebView 嗅探能力

- **场景**：用户不写 ruleContent/ruleImage，访问 JS 渲染的图片站点
- **预期**：通过 BackstageWebView 加载页面，拦截 shouldInterceptRequest 中的图片请求，返回 ≥ 3 张图片 URL
- **验证**：logcat 输出 `ImageUrlExtractor: WebView sniff success, count=N`，N ≥ 3

#### AC-P0-2: ruleContent 为空时的降级链路

- **场景**：用户不写 ruleContent，访问 JS 渲染站点
- **预期**：
  1. 先尝试 `body@html` 静态解析（L1）
  2. 静态解析结果 < 3 张时自动触发 WebView 嗅探（L2）
  3. WebView 嗅探超时（6s）后返回已捕获的图片（L3 兜底）
- **验证**：logcat 输出降级链路日志 `L1 static parse: count=X` → `L2 webview sniff: count=Y` → `L3 timeout fallback: count=Z`

#### AC-P0-3: shouldInterceptRequest 拦截

- **场景**：WebView 嗅探过程中，页面发起图片请求
- **预期**：SnifferWebClient.shouldInterceptRequest 拦截 Content-Type: image/* 的资源，记录 URL
- **验证**：logcat 输出 `SnifferWebClient: intercept image url=/path/{id}`（路径模式，不含真实域名）

#### AC-P0-4: JS hook 注入

- **场景**：前端 JS 通过 `new Image().src = url` / `fetch()` / `IntersectionObserver` 动态加载图片
- **预期**：IMAGE_SNIFF_JS hook 这些 API，捕获图片 URL 并回传 Native
- **验证**：logcat 输出 `IMAGE_SNIFF_JS: hook Image.src setter, url=/path/{id}`

### 2.2 P1 验收（静态解析增强）

#### AC-P1-1: `<picture>/<source>` 标签嗅探

- **场景**：HTML5 响应式图片 `<picture><source srcset="..."><img src="..."></picture>`
- **预期**：提取 `<source>` 的 srcset 和 `<img>` 的 src
- **验证**：单元测试覆盖

#### AC-P1-2: CSS background-image 嗅探

- **场景**：`<div style="background-image: url(...)">` 或 `<div class="hero" style="background: url(...)">`
- **预期**：正则提取 `url(...)` 中的图片地址
- **验证**：单元测试覆盖

#### AC-P1-3: srcset 多分辨率解析

- **场景**：`srcset="url1 480w, url2 800w, url3 2x"`
- **预期**：按逗号分割，每段取第一个空格前的 URL，收集所有 URL
- **验证**：单元测试覆盖

#### AC-P1-4: og:image Meta 标签嗅探

- **场景**：`<meta property="og:image" content="...">`
- **预期**：提取 content 属性值
- **验证**：单元测试覆盖

#### AC-P1-5: Script JSON 提取

- **场景**：`<script>{"image":"url"}</script>` 或 `<script>{"images":["url1","url2"]}</script>`
- **预期**：提取 JSON 中的图片 URL
- **验证**：单元测试覆盖

#### AC-P1-6: JS 变量提取

- **场景**：`var images = ["url1","url2"]` 或 `const imgs = ["url1","url2"]`
- **预期**：提取数组中的图片 URL
- **验证**：单元测试覆盖

#### AC-P1-7: 图片扩展名白名单/黑名单

- **场景**：策略4 提取所有 http URL 时
- **预期**：
  - 白名单：`.jpg` / `.jpeg` / `.png` / `.webp` / `.gif` / `.svg` / `.avif` / `.bmp`
  - 黑名单：`.js` / `.css` / `.html` / `.json` / `.woff` / `.ttf`
  - 无法判断扩展名时（如 `/path/{id}`）：保留并尝试 Content-Type 校验
- **验证**：单元测试覆盖

#### AC-P1-8: 懒加载属性扩展

- **场景**：`data-url` / `data-img` / `data-lazy-srcset` / `data-original-src` / `data-echo` / `data-img-src`
- **预期**：扩展正则属性列表覆盖上述懒加载属性
- **验证**：单元测试覆盖

### 2.3 性能验收

- **AC-PERF-1**: 静态解析（L1）耗时 ≤ 500ms
- **AC-PERF-2**: WebView 嗅探（L2）总耗时 ≤ 6s（含页面加载 + JS hook + 资源拦截）
- **AC-PERF-3**: JS hook 注入不影响页面正常渲染（页面可交互）
- **AC-PERF-4**: BackstageWebView 销毁后无内存泄漏（WeakReference + onDestroy 释放）

### 2.4 兼容性验收

- **AC-COMPAT-1**: 用户写 ruleContent/ruleImage 时优先走用户规则（不破坏现有逻辑）
- **AC-COMPAT-2**: 防盗链场景：注入 Referer / Cookie 后能加载图片
- **AC-COMPAT-3**: 懒加载场景：等待 IntersectionObserver 触发后能捕获真实图片 URL
- **AC-COMPAT-4**: 现有 5 级策略保留（向后兼容）

---

## 三、非目标（Non-Goals）

### 3.1 不做的事

1. **不修改 `Rss.getContentAwait` 的核心逻辑**：仅在外部包装降级链路
2. **不修改 `BackstageWebView` 的核心实现**：仅复用其 `sourceRegex` / `interceptAllRequests` / `videoSniffJs` 三参数能力
3. **不实现图片下载**：图片下载仍由 Glide 负责（`ImageCanvasAdapter` 现有逻辑）
4. **不实现图片缓存**：图片缓存仍由 Glide + OkHttp 缓存负责
5. **不修改 `ImageCanvasAdapter`**：UI 层不变，仅数据源（`parseImageUrls` 返回值）变化
6. **不修改 `RssSource` 实体**：不新增字段（如 `ruleImageSniff` 等），全部走自动嗅探
7. **不实现视频嗅探的能力对齐**：仅复用架构，不修改视频嗅探代码

### 3.2 边界外场景

1. **付费墙 / 登录墙**：不处理需要登录才能查看的图片站点
2. **Cloudflare JS Challenge**：不处理需要 JS Challenge 验证的站点（已有 WebView 预热机制，不在本 spec 范围）
3. **图片加密**：不处理图片本身加密（如 Base64 编码、AES 加密）的场景
4. **动态分页**：不处理滚动到底部自动加载下一页的场景（已有 `loadNextArticle` 分页机制）

---

## 四、约束

### 4.1 技术约束

- **Kotlin 协程**：使用项目自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装
- **JS 引擎**：WebView JS hook 通过 `evaluateJavascript` 注入
- **依赖锁定**：jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22 不可升级
- **错误处理**：`kotlin.runCatching`（带 `kotlin.` 前缀），异常继承 `NoStackTraceException`
- **日志**：`AppLog.putDebugWithTag` + `AppLog.TAG_IMAGE_SNIFFER`（新增 tag）

### 4.2 性能约束

- **总超时**：12s（L1 静态解析 500ms + L2 WebView 嗅探 6s + L3 兜底 5.5s）
- **并发**：单次嗅探仅 1 个 BackstageWebView 实例（避免内存压力）
- **内存**：BackstageWebView 用完即销毁（`onDestroy` 调用 `webview.destroy()`）

### 4.3 安全约束

- **URL 脱敏**：日志中 URL 用路径模式 `/path/{id}` 替代，不输出真实域名
- **Cookie 隐藏**：日志中 Cookie 用 `***` 替代，仅记录长度
- **Referer 注入**：从 `rssSource.sourceUrl` 提取域名作为 Referer，不硬编码
