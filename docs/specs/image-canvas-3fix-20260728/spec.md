# 设计文档（image-canvas-3fix-20260728）

> spec.md — 问题规格说明

## 1. 问题背景

### 1.1 测试包信息

| 项 | 值 |
|----|-----|
| 日志包编号 | 008（2801 包） |
| 测试时间 | 2026-07-28 01:25:44 |
| 日志文件 | appLog-26-07-28_01-25-44.495.txt |
| 测试包类型 | 测试包（debug 构建） |
| 测试模块 | 图片画布（ImageCanvas） |

### 1.2 问题发现过程

通过 008 日志包的完整日志证据链，锁定图片画布模块 3 个独立但相互关联的问题：
- Q1 滚动位置异常（用户可感知：进入图片画布后滚动到最后一张而非第一张）
- Q2 图片数量缺失（用户可感知：本应显示 52 张图片，实际只显示 1 张）
- Q3 无限降级循环（用户可感知：图片反复闪烁加载，无法稳定显示）

3 个问题均通过日志行号铁证定位，并经源码深度核实确认根因。

---

## 2. 问题详细描述

### 2.1 Q1：加载图片仍滚动到最后一张

#### 现象
进入图片画布后，RecyclerView 滚动到最后一张图片而非第一张，用户需手动向上滚动才能看到第一张。

#### 日志证据
| 日志行 | 内容（脱敏） | 说明 |
|--------|-------------|------|
| L106 | `observeNewItems: notifyItemRangeInserted startPos=0 itemCount=24` | 首次插入 24 项 |
| L107 | 80ms 后 `Scroll: trigger loadNextArticle remaining=1 total=25 lastVisible=24` | 80ms 后触发 loadNextArticle，lastVisible=24（最后一张） |
| - | 无 isInitialScrollDone 日志 | isInitialScrollDone 的 scrollToPosition(0) 未生效或被覆盖 |

#### 根因（摘要）
1. `onCreateViewHolder` 设置 defaultHeight 时使用 `binding.root.layoutParams.apply { height = defaultHeight }`，可能因 layoutParams 为 null 或被后续布局覆盖导致默认高度未生效，所有图片项高度为 0 全部布局在一屏内，lastVisible=24
2. `observeNewItems` 中 isInitialScrollDone 逻辑使用 `binding.recyclerView.post { scrollToPosition(0) }`，post 在 UI 队列执行时布局可能未完成，scrollToPosition(0) 被后续布局覆盖
3. 首次插入第 2 篇文章时自动触发 loadNextArticle，滚动位置被覆盖

#### 源码位置
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L241-265（onCreateViewHolder）
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L449-500（bind 重置 defaultHeight）
- `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt` L692-714（observeNewItems）

---

### 2.2 Q2：只有一张图（L2 超时丢弃 51 张 URL）

#### 现象
某文章本应包含 52 张图片（L1 策略2 命中 1 张 + L2 WebView 嗅探收集 51 张），但最终只显示 1 张。

#### 日志证据
| 日志行 | 内容（脱敏） | 说明 |
|--------|-------------|------|
| L2480 | HTTP 429 限流 | 源站点限流，ruleContent 从错误页面解析 |
| L2493 | `strategy 2 (ruleImage selector) success: count=1` | 策略2 只命中 1 张 |
| L2553 | `sniffImageUrls timeout: collected=51` | L2 WebView 嗅探超时，但已收集 51 张 URL |
| L2555 | `extractImageList done(L1+L2 merged): l1=1 l2=0 merged=1` | L2=0！51 张被丢弃 |

#### 根因（摘要）
1. HTTP 429 限流导致 ruleContent 从错误页面解析，策略2 仅命中 1 张
2. 策略2 命中 1 张后直接 `return filterImageUrls(imgUrls)`，未继续执行策略3（regex img tag）
3. **关键 bug**：`extractWithWebView` 外层 `withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS)` 与 `sniffImageUrls` 内部 `withTimeoutOrNull(timeout)` 超时时间相同（均为 6s）。当 sniffImageUrls 内部超时返回已收集的 51 张 URL 时，外层 withTimeoutOrNull 也到达超时阈值，直接返回 emptyList 丢弃 sniffImageUrls 的返回值。

#### 源码位置
- `app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt` L231-409（enhancedParseImageUrls 策略1-5）
- `app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt` L565-613（extractWithWebView 外层 withTimeoutOrNull）
- `app/src/main/java/io/legado/app/help/image/ImageSnifferWebView.kt` L75-119（sniffImageUrls 内部已实现超时返回 collectedUrls）

#### 源码核实修正
原始修复方案提出"ImageSnifferWebView.sniffImageUrls() 改为超时后返回已收集 URL"，经源码核实**该逻辑已实现**（L100-107 `?: run { ... synchronized(collectedUrls) { collectedUrls.toList() } }`）。真正 bug 在 extractWithWebView 外层 withTimeoutOrNull，修复方案已修正为移除外层 withTimeoutOrNull 包装。

---

### 2.3 Q3：无限刷牙（降级链循环）

#### 现象
同一图片 URL 反复触发降级链 fallback-1→2→3→1→2→3→1... 无限循环，图片反复闪烁加载无法稳定显示。

#### 日志证据
| 日志行范围 | 现象（脱敏） |
|-----------|-------------|
| L2584-2696 | 同一 URL（/path/-205780509）反复触发 fallback-1→2→3→1→2→3→1... |

#### 根因（摘要）
1. 降级3 WebView 预热完成 → `markPreheatReload` → `notifyItemChanged`
2. `notifyItemChanged` 触发重新 `bind`
3. `bind` 方法 L454: `retryCount = 0` 无条件重置降级链计数器
4. 重新 bind 后图片再次加载失败 → 从降级1重新开始 → 无限循环

#### 源码位置
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L449-453（bind 无条件 retryCount=0）
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L125-134（markPreheatReload notifyItemChanged）
- `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` L777-860（triggerFallbackChain 降级链 when retryCount）

#### 源码核实修正
原始修复方案提出"新增 isPreheatReload 参数标记预热后重载场景"，经源码核实 **isPreheatReload 标志已存在**（L489 `val isPreheatReload = preheatReloadPositions.remove(position)`），但 L454 无条件 `retryCount = 0` 未使用此标志。修复方案已修正为调整代码顺序，根据 isPreheatReload 决定是否重置 retryCount。

---

## 3. 验收标准

### 3.1 Q1 验收标准

| 编号 | 验收条件 | 验证方法 |
|------|---------|---------|
| Q1-AC1 | 进入图片画布后，RecyclerView 定位在第一张图片 | 真机测试：打开含图片的 RSS 文章，进入图片画布，观察初始滚动位置 |
| Q1-AC2 | 日志输出 `observeNewItems: initial scroll to position 0` | 抓取 appLog，Grep "initial scroll to position 0" |
| Q1-AC3 | 首次插入第 2 篇文章时不自动触发 loadNextArticle 滚动覆盖 | 抓取 appLog，确认首次插入后无 `Scroll: trigger loadNextArticle` 日志 |
| Q1-AC4 | 图片项 defaultHeight 生效，lastVisible ≠ 总数-1 | 抓取 appLog，确认 notifyItemRangeInserted 后 lastVisible < itemCount |

### 3.2 Q2 验收标准

| 编号 | 验收条件 | 验证方法 |
|------|---------|---------|
| Q2-AC1 | L2 WebView 嗅探超时后，已收集的 URL 被正确合并到最终结果 | 抓取 appLog，确认 `extractImageList done` 日志中 l2 > 0 |
| Q2-AC2 | 策略2 命中数 < 3 时继续执行策略3，合并结果 | 抓取 appLog，确认 strategy 2 success 后存在 strategy 3 success 日志 |
| Q2-AC3 | 文章图片数量 ≥ L1 + L2 收集总数（去重后） | 对比日志中 collected=N 与最终显示图片数 |
| Q2-AC4 | HTTP 429 限流场景下仍能通过 L2 嗅探获取完整图片列表 | 模拟限流场景测试 |

### 3.3 Q3 验收标准

| 编号 | 验收条件 | 验证方法 |
|------|---------|---------|
| Q3-AC1 | 同一 URL 的降级链不出现 fallback-1→2→3→1 循环 | 抓取 appLog，Grep "fallback-" 确认同一 urlHash 的降级链单调递增 |
| Q3-AC2 | 预热重载场景下 retryCount 不被重置为 0 | 抓取 appLog，确认 preheat reload 后 fallback 级别续接而非重置 |
| Q3-AC3 | 预热重载后图片成功加载或进入降级4（而非无限循环） | 真机测试：触发降级3 预热场景，观察图片最终状态 |
| Q3-AC4 | 正常首次绑定场景 retryCount 仍重置为 0（非预热场景） | 抓取 appLog，确认非预热场景降级链从 fallback-1 开始 |

---

## 4. 影响范围分析

### 4.1 代码影响范围

| 文件 | 修改范围 | 影响功能 |
|------|---------|---------|
| `ImageCanvasAdapter.kt` | L241-265（onCreateViewHolder）、L449-501（bind）、L125-134（markPreheatReload） | 图片画布列表显示、降级链 |
| `ImageGalleryActivity.kt` | L692-714（observeNewItems）、loadNextArticle 触发逻辑 | 图片画布滚动行为 |
| `ImageUrlExtractor.kt` | L231-289（策略2 return 逻辑）、L565-613（extractWithWebView） | 图片 URL 提取 |
| `ImageSnifferWebView.kt` | 无需修改（源码核实后确认） | - |

### 4.2 功能影响范围

| 功能模块 | 影响程度 | 说明 |
|---------|---------|------|
| 图片画布（ImageCanvas） | 高 | 3 个问题均在此模块 |
| RSS 文章图片阅读 | 高 | 图片画布是 RSS 图片阅读的核心入口 |
| 图片嗅探（ImageSniffer） | 中 | Q2 涉及 L2 WebView 嗅探逻辑 |
| 降级链机制 | 中 | Q3 涉及降级链计数器重置逻辑 |
| 其他模块（书架/书源/正文阅读） | 无 | 修改范围隔离在图片画布模块 |

### 4.3 兼容性影响

- **数据库**：无变更（无实体字段修改、无 migration）
- **API**：无变更（无接口签名修改）
- **配置**：无变更（无 BuildConfig / ProGuard 规则修改）
- **依赖**：无新增/升级依赖

### 4.4 回归风险

| 风险点 | 风险等级 | 缓解措施 |
|--------|---------|---------|
| Q1 修复后 loadNextArticle 禁用导致无法加载下一篇 | 中 | 仅首次插入时禁用，后续正常触发 |
| Q2 策略2 不 return 导致策略3 重复提取相同 URL | 低 | distinct() 去重 + filterImageUrls 过滤 |
| Q3 retryCount 不重置导致正常场景降级链异常 | 中 | 仅预热重载场景不重置，正常 bind 仍重置 |
| extractWithWebView 移除外层超时导致 L2 卡死 | 中 | sniffImageUrls 内部超时仍生效 + try-catch 兜底 |
