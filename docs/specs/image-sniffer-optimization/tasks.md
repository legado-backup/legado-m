# 图片播放器前置嗅探能力优化 - 任务清单

> **版本**：v1
> **创建日期**：2026-07-27
> **状态**：待审查
> **关联文档**：[spec.md](./spec.md) / [design.md](./design.md)

---

## Phase A: P0 修复（WebView 嗅探层 + JS hook）

### A-1: 新建 ImageUrlExtractor.kt 基础架构

- [x] A-1.1: 创建 `app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt`
- [x] A-1.2: 定义 `object ImageUrlExtractor` + 常量（`TAG` / `TOTAL_TIMEOUT_MS=12000` / `L1_STATIC_TIMEOUT_MS=500` / `L2_WEBVIEW_TIMEOUT_MS=6000`）
- [x] A-1.3: 实现 `extractImageList(article, rssSource, ruleContent, ruleImage)` 公共接口
- [x] A-1.4: 实现 `extractWithStatic()` 私有方法（L1 静态解析入口）
- [x] A-1.5: 实现 `extractWithWebView()` 私有方法（L2 WebView 嗅探入口，先留桩返回 emptyList）
- [x] A-1.6: 实现三层降级链路调度逻辑（L1 → if size<3 → L2 → L3 兜底）
- [x] A-1.7: 编译验证

### A-2: 设计 IMAGE_SNIFF_JS（5 路 hook）

- [x] A-2.1: 在 `ImageUrlExtractor.kt` 定义 `IMAGE_SNIFF_JS` 常量
- [x] A-2.2: 实现 hook 1：`HTMLImageElement.prototype.src` setter
- [x] A-2.3: 实现 hook 2：`window.fetch`
- [x] A-2.4: 实现 hook 3：`XMLHttpRequest.prototype.open`
- [x] A-2.5: 实现 hook 4：`window.IntersectionObserver`
- [x] A-2.6: 实现 hook 5：`document.write`
- [x] A-2.7: JS 中收集 URL 到 `window._imageSnifferUrls` 数组（去重）
- [x] A-2.8: JS 添加 try-catch 保护（hook 异常不影响原逻辑）
- [x] A-2.9: 编译验证

### A-3: 实现 L2 WebView 嗅探（extractWithWebView）

- [x] A-3.1: 调用 `BackstageWebView` 构造，传入参数：
  - `sourceRegex` = 图片扩展名正则 `\.(jpg|jpeg|png|webp|gif|svg|avif|bmp)(\?|$)`
  - `interceptAllRequests` = false（仅拦截不修改）
  - `videoSniffJs` = `IMAGE_SNIFF_JS`
- [x] A-3.2: 加载 `article.link`（用户规则场景）/ `rssSource.sourceUrl + article.link`（无规则场景）
- [x] A-3.3: 实现页面加载完成回调（`onPageFinished`）触发 JS hook 结果收集
- [x] A-3.4: 实现 `shouldInterceptRequest` 拦截图片资源（Content-Type: image/*）
- [x] A-3.5: 实现 6s 超时兜底（`withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS)`）
- [x] A-3.6: 合并 `window._imageSnifferUrls`（JS hook）+ `interceptedUrls`（shouldInterceptRequest）结果
- [x] A-3.7: 实现 WebView 销毁（`onDestroy` / `webview.destroy()` / `WeakReference` 清理）
- [x] A-3.8: 实现协程取消时 WebView 同步销毁（`tryFinally` / `onCancel`）
- [x] A-3.9: 实现 `Mutex` 并发守卫（同一时间仅 1 个 WebView 嗅探实例）
- [x] A-3.10: 编译验证

### A-4: ImageCanvasViewModel 集成 ImageUrlExtractor

- [x] A-4.1: `AppLog.kt` 新增 `TAG_IMAGE_SNIFFER = "ImageSniffer"` 常量
- [x] A-4.2: `ImageCanvasViewModel.loadArticleInternal` 替换 `parseImageUrls` 调用为 `ImageUrlExtractor.extractImageList`
- [x] A-4.3: 移除 `loadArticleInternal` 中的 `Rss.getContentAwait` 直接调用（已封装在 `ImageUrlExtractor` 内）
- [x] A-4.4: 保留 `parseImageUrls` 方法（被 `ImageUrlExtractor.extractWithStatic` 调用）
- [x] A-4.5: 调整日志输出（使用 `TAG_IMAGE_SNIFFER`）
- [x] A-4.6: 编译验证

---

## Phase B: P1 修复（静态解析增强）

### B-1: 策略3.5 - `<picture>/<source>` 标签嗅探

- [x] B-1.1: 在 `ImageUrlExtractor.kt`（或 `ImageCanvasViewModel.kt`）新增 `parsePictureSource(body, baseUrl)` 方法
- [x] B-1.2: 实现 `<source srcset="url1 480w, url2 800w">` 提取（srcset 多分辨率按逗号分割）
- [x] B-1.3: 在 `enhancedParseImageUrls` 策略3 之后调用 `parsePictureSource`
- [x] B-1.4: 单元测试覆盖
- [x] B-1.5: 编译验证

### B-2: 策略3.6 - CSS background-image 嗅探

- [x] B-2.1: 新增 `parseBackgroundImage(body, baseUrl)` 方法
- [x] B-2.2: 实现正则 `background(?:-image)?\s*:\s*url\(["']?([^"')]+)["']?\)`
- [x] B-2.3: 在 `enhancedParseImageUrls` 策略3.5 之后调用 `parseBackgroundImage`
- [x] B-2.4: 单元测试覆盖
- [x] B-2.5: 编译验证

### B-3: 策略3.7 - og:image Meta 标签嗅探

- [x] B-3.1: 新增 `parseOgImage(body, baseUrl)` 方法
- [x] B-3.2: 实现正则 `<meta[^>]+property\s*=\s*["']og:image(?:url)?["'][^>]+content\s*=\s*["']([^"']+)["']`
- [x] B-3.3: 在 `enhancedParseImageUrls` 策略3.6 之后调用 `parseOgImage`
- [x] B-3.4: 单元测试覆盖
- [x] B-3.5: 编译验证

### B-4: 策略3.8 - Script JSON 提取

- [x] B-4.1: 新增 `parseScriptJson(body, baseUrl)` 方法
- [x] B-4.2: 实现 `<script>` 标签内容提取
- [x] B-4.3: 实现 JSON 中 `image` / `images` / `image_url` / `image_list` / `url` / `@id` 字段提取
- [x] B-4.4: 在 `enhancedParseImageUrls` 策略3.7 之后调用 `parseScriptJson`
- [x] B-4.5: 单元测试覆盖
- [x] B-4.6: 编译验证

### B-5: 策略3.9 - JS 变量提取

- [x] B-5.1: 新增 `parseJsVariables(body, baseUrl)` 方法
- [x] B-5.2: 实现正则 `(?:var|let|const)\s+\w*(?:image|img|pic|photo)s?\w*\s*=\s*\[([^\]]+)\]`
- [x] B-5.3: 实现数组内 URL 提取（双引号/单引号包裹）
- [x] B-5.4: 在 `enhancedParseImageUrls` 策略3.8 之后调用 `parseJsVariables`
- [x] B-5.5: 单元测试覆盖
- [x] B-5.6: 编译验证

### B-6: 策略4 增强 - 图片扩展名白/黑名单

- [x] B-6.1: 定义 `IMAGE_EXTENSION_WHITELIST = setOf("jpg","jpeg","png","webp","gif","svg","avif","bmp")`
- [x] B-6.2: 定义 `URL_EXTENSION_BLACKLIST = setOf("js","css","html","htm","json","woff","woff2","ttf","eot","ico")`
- [x] B-6.3: 实现 `filterImageUrls(urls)` 方法（白名单优先，黑名单过滤，未知保留）
- [x] B-6.4: 在策略4 后调用 `filterImageUrls`
- [x] B-6.5: 单元测试覆盖
- [x] B-6.6: 编译验证

### B-7: 策略3 增强 - 懒加载属性扩展

- [x] B-7.1: 定义 `LAZY_LOAD_ATTRS` 列表（扩展 `data-url` / `data-img` / `data-lazy-srcset` / `data-original-src` / `data-echo` / `data-img-src` / `data-delay` / `data-lazy`）
- [x] B-7.2: 修改策略3 正则，动态拼接属性列表
- [x] B-7.3: 单元测试覆盖
- [x] B-7.4: 编译验证

### B-8: srcset 多分辨率解析完善

- [x] B-8.1: 修改策略3 中 srcset 处理逻辑，按逗号分割后每段取第一个空格前的 URL
- [x] B-8.2: 收集所有分辨率的 URL（不仅取第一个）
- [x] B-8.3: 单元测试覆盖
- [x] B-8.4: 编译验证

---

## Phase C: P2 优化（延后，不阻塞本次交付）

### C-1: jsoup 解析替代正则

- [x] C-1.1: 评估 jsoup 解析性能开销
- [x] C-1.2: 用 jsoup 重写策略3 / 3.5 / 3.6 / 3.7（解决跨行/无引号问题）
- [x] C-1.3: 单元测试覆盖
- [x] C-1.4: 编译验证

### C-2: `<a href>` 链接到图片的嗅探

- [x] C-2.1: 新增 `parseAnchorImageLinks(body, baseUrl)` 方法
- [x] C-2.2: 实现 jsoup `select("a[href$=.jpg], a[href$=.png], ...")` 提取
- [x] C-2.3: 单元测试覆盖
- [x] C-2.4: 编译验证

### C-3: 合并策略1 和策略5

- [x] C-3.1: 评估策略1 和策略5 合并的可行性
- [x] C-3.2: 合并后单 URL 场景由策略1 自然处理
- [x] C-3.3: 单元测试覆盖
- [x] C-3.4: 编译验证

---

## Phase D: 验证与打包

### D-1: 单元测试

- [x] D-1.1: 编写 `ImageUrlExtractorTest.kt`
- [x] D-1.2: 测试 L1 静态解析各策略
- [x] D-1.3: 测试 L2 WebView 嗅探（mock BackstageWebView）
- [x] D-1.4: 测试三层降级链路（L1 失败 → L2 → L3）
- [x] D-1.5: 测试图片扩展名白/黑名单过滤
- [x] D-1.6: 测试超时控制

### D-2: 真机测试（测试包 `io.legado.miss.app.debug`）

- [x] D-2.1: 编译生成测试包
- [x] D-2.2: 安装到模拟器/真机
- [x] D-2.3: 测试用户写 ruleContent/ruleImage 场景（兼容性验证）
- [x] D-2.4: 测试用户不写规则场景（JS 渲染站点嗅探验证）
- [x] D-2.5: 测试懒加载场景（IntersectionObserver 触发）
- [x] D-2.6: 测试防盗链场景（Referer/Cookie 注入）
- [x] D-2.7: 收集 logcat 日志验证三层降级链路
- [x] D-2.8: 性能验证（L1 ≤ 500ms / L2 ≤ 6s / 总 ≤ 12s）

### D-3: 文档同步

- [x] D-3.1: 更新 `assets/updateLog.md`（基于 git diff 分析真实代码变更）
- [x] D-3.2: 更新 `docs/INDEX.md`（新增 spec 条目）
- [x] D-3.3: 更新项目记忆（当前任务状态 + 用户反馈记录）

### D-4: 交付

- [x] D-4.1: 编译最终测试包
- [x] D-4.2: 提交 AskUserQuestion 验收
- [x] D-4.3: 用户真机测试反馈收集

---

## 检查点

### 检查点 1: Phase A 完成（P0 修复）

- 验收标准：
  - A-1 ~ A-4 全部完成
  - 编译通过
  - 单元测试覆盖 L1/L2/L3 链路
  - 真机测试 JS 渲染站点能嗅探到 ≥ 3 张图片

### 检查点 2: Phase B 完成（P1 修复）

- 验收标准：
  - B-1 ~ B-8 全部完成
  - 编译通过
  - 单元测试覆盖各新增策略
  - 真机测试静态 HTML 站点能完整提取各格式图片

### 检查点 3: Phase D 完成（验证与打包）

- 验收标准：
  - D-1 ~ D-4 全部完成
  - 真机测试通过
  - updateLog.md 已更新
  - AskUserQuestion 验收通过

---

## 依赖关系

```
A-1 (基础架构) → A-2 (JS hook) → A-3 (WebView 嗅探) → A-4 (集成)
                                                          ↓
B-1 ~ B-8 (静态解析增强，独立于 A，可并行)
                                                          ↓
                                                    D-1 (单元测试)
                                                          ↓
                                                    D-2 (真机测试)
                                                          ↓
                                                    D-3 (文档同步)
                                                          ↓
                                                    D-4 (交付)
```

---

## 风险点

1. **BackstageWebView 复用风险**：现有 `videoSniffJs` 参数名是否通用？若不通用需新增 `imageSniffJs` 参数
2. **JS hook 兼容性风险**：不同 Android 版本（API 23+）的 WebView JS 引擎差异
3. **协程取消风险**：WebView 销毁必须在协程取消时同步执行
4. **性能风险**：WebView 嗅探 6s 超时可能影响用户体验（需 UI 提示"正在嗅探图片..."）

---

## 反模式（禁止）

1. ❌ 修改 `Rss.getContentAwait` 核心逻辑
2. ❌ 修改 `BackstageWebView` 核心实现（仅复用参数）
3. ❌ 修改 `ImageCanvasAdapter` UI 层
4. ❌ 修改 `RssSource` 实体新增字段
5. ❌ 引入新依赖（jsoup 升级 / rhino 升级）
6. ❌ 删除现有 5 级策略（保持向后兼容）
7. ❌ 跳过单元测试直接真机测试
8. ❌ 跳过 updateLog.md 更新
