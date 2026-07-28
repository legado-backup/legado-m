# 图片播放器前置嗅探能力优化

> **创建日期**：2026-07-27
> **任务类型**：功能增强 + 架构对齐
> **优先级**：P0（核心能力缺陷，阻塞用户核心场景）
> **状态**：设计阶段

---

## 一、任务背景

### 1.1 用户反馈

用户反馈"图片播放器前置嗅探能力严重有缺陷"，核心诉求：
1. **用户写内容规则（ruleContent / ruleImage）场景**：按用户规则加载图片列表，处理防盗链等通用场景
2. **用户不写内容规则场景**：图片播放器需具备**嗅探图片列表能力**，参考视频播放器嗅探架构

### 1.2 问题现状

当前图片播放器前置嗅探链路：

```
ImageGalleryActivity.onCreate
  └─ ImageCanvasViewModel.loadInitialArticle()
       └─ loadArticleInternal()
            └─ Rss.getContentAwait()  ← 单次 OkHttp 同步请求
                 └─ parseImageUrls()  ← 5 级静态字符串/正则解析
                      ├─ 策略1: body 不含 < → split 换行符
                      ├─ 策略2: ruleImage 选择器（AnalyzeRule）
                      ├─ 策略3: <img> 标签正则
                      ├─ 策略4: 所有 http URL 正则
                      └─ 策略5: 单 URL 兜底
```

### 1.3 核心缺陷

| 编号 | 缺陷 | 影响 |
|------|------|------|
| P0-1 | **无 WebView 嗅探能力** | JS 渲染页面（Vue/React/Angular SPA）完全无法嗅探 |
| P0-2 | **ruleContent 为空时强制 body@html 兜底** | JS 渲染页面 body 几乎为空，无图可提取 |
| P0-3 | **无 shouldInterceptRequest 拦截** | 懒加载、AJAX 动态加载图片无法捕获 |
| P0-4 | **无 JS hook 注入** | 前端 JS 动态构造的图片 URL 无法捕获 |
| P1-1 | 缺失 `<picture>/<source>` 标签嗅探 | 响应式图片站点丢图 |
| P1-2 | 缺失 CSS background-image 嗅探 | 海报/Banner/封面图丢失 |
| P1-3 | srcset 响应式图片解析不完整 | 高分辨率设备丢图 |
| P1-4 | 缺失 og:image Meta 标签嗅探 | 社交分享缩略图丢失 |
| P1-5 | 缺失 Script JSON 提取 | 现代 SPA 站点（JSON-LD）丢图 |
| P1-6 | 缺失 JS 变量提取 | 老旧站点 JS 变量存储图片丢图 |
| P1-7 | 策略4 误匹配非图片 URL | 图片列表含 JS/CSS/API URL，Glide 加载失败 |
| P1-8 | 懒加载属性覆盖不全 | 部分懒加载站点丢图 |

### 1.4 对比视频嗅探架构

视频嗅探已有完整的「三层降级 + 五路 JS Hook」架构：

```
VideoUrlExtractor.extractVideoUrlForEpisode()
  ├─ Layer 1: DOM 静态解析（<video>/<source>/og:video/Meta）
  ├─ Layer 2: WebView 抓包（BackstageWebView + shouldInterceptRequest）
  │    └─ VIDEO_SNIFF_JS 5 路 hook（HTMLMediaElement.src/fetch/XHR/...)
  └─ Layer 3: 超时兜底（12s 总超时 + 6s 分层超时）
```

图片嗅探需对齐此架构。

---

## 二、修复策略

### Phase A: P0 修复（WebView 嗅探层 + JS hook）

- **A-1**: 新建 `ImageUrlExtractor.kt`，封装三层降级架构
- **A-2**: 设计 `IMAGE_SNIFF_JS`，hook `Image.src` setter / `fetch` / `XHR` / `IntersectionObserver` / `document.write`
- **A-3**: 复用 `BackstageWebView`，构造时传入图片扩展名正则作为 `sourceRegex`
- **A-4**: `ImageCanvasViewModel.loadArticleInternal` 集成 `ImageUrlExtractor`，静态解析失败时自动触发 WebView 嗅探

### Phase B: P1 修复（静态解析增强）

- **B-1**: 新增 `<picture>/<source>` 标签嗅探
- **B-2**: 新增 CSS `background-image` 嗅探
- **B-3**: 完善 `srcset` 多分辨率解析
- **B-4**: 新增 `og:image` Meta 标签嗅探
- **B-5**: 新增 Script JSON 提取（`"image":"url"` / `"images":["url1","url2"]`）
- **B-6**: 新增 JS 变量提取（`var images = [...]`）
- **B-7**: 引入图片扩展名白名单 + 黑名单（解决策略4 误匹配）
- **B-8**: 扩展懒加载属性覆盖

### Phase C: P2 优化（精度提升，延后）

- C-1: jsoup 解析替代正则（解决跨行/无引号问题）
- C-2: `<a href>` 链接到图片的嗅探
- C-3: 合并策略1 和策略5（消除冗余）

### Phase D: 验证与打包

- D-1: 单元测试覆盖各解析策略
- D-2: 真机测试（测试包 `io.legado.miss.app.debug`）
- D-3: updateLog.md 更新
- D-4: 项目记忆同步

---

## 三、验收标准

### 3.1 功能验收

- [ ] 用户不写 ruleContent/ruleImage 时，JS 渲染站点能嗅探到 ≥ 3 张图片
- [ ] 静态 HTML 站点能完整提取 `<img>` / `<picture>` / `<source>` / `background-image` / `og:image` / Script JSON
- [ ] WebView 嗅探总耗时 ≤ 6 秒（12s 超时兜底）
- [ ] 静态解析失败时自动降级到 WebView 嗅探
- [ ] WebView 嗅探失败时返回空列表（不阻塞 UI）

### 3.2 性能验收

- [ ] 静态解析（L1）耗时 ≤ 500ms
- [ ] WebView 嗅探（L2）耗时 ≤ 6s
- [ ] JS hook 注入不影响页面正常渲染
- [ ] 内存占用稳定（BackstageWebView 销毁后无泄漏）

### 3.3 兼容性验收

- [ ] 用户写 ruleContent/ruleImage 时优先走用户规则（不破坏现有逻辑）
- [ ] 防盗链场景：注入 Referer / Cookie 后能加载图片
- [ ] 懒加载场景：等待 IntersectionObserver 触发后能捕获真实图片 URL

---

## 四、文档导航

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 功能规范（核心问题 / 验收标准 / 非目标） |
| [design.md](./design.md) | 技术设计（架构 / 接口 / 数据流 / 风险） |
| [tasks.md](./tasks.md) | 任务清单（Phase 分解 / 检查点） |

---

## 五、参考资料

- 调研报告：[docs/temp-analysis/image-sniffer-research-20260727.md](../../temp-analysis/image-sniffer-research-20260727.md)
- 当前源码分析：[docs/temp-analysis/image-sniffer-current-analysis-20260727.md](../../temp-analysis/image-sniffer-current-analysis-20260727.md)
- 视频嗅探架构参考：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`
- BackstageWebView 基础设施：`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`
