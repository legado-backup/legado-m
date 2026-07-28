# 设计文档（image-canvas-3fix-20260728）

> 图片画布（ImageCanvas）3 个问题修复设计文档四件套

## 背景

008 日志包（2801 包，2026-07-28 01:25:44 测试）通过完整日志证据链锁定图片画布模块的 3 个问题根因。本设计文档基于源码深度核实，给出源码级修复方案。

## 3 个问题概览

| 编号 | 问题 | 现象 | 根因（摘要） |
|------|------|------|-------------|
| Q1 | 加载图片仍滚动到最后一张 | 首次插入 24 项后 80ms 触发 loadNextArticle，滚动位置错乱 | defaultHeight 设置可能被覆盖 + isInitialScrollDone 的 scrollToPosition(0) 在布局完成前执行 |
| Q2 | 只有一张图（L2 超时丢弃 51 张 URL） | L2 WebView 嗅探收集 51 张 URL，但最终合并 L2=0 | extractWithWebView 外层 withTimeoutOrNull 与 sniffImageUrls 内部超时时间相同，外层先超时返回 emptyList 丢弃已收集 URL；策略2 命中 1 张后直接 return 未继续策略3 |
| Q3 | 无限刷牙（降级链循环） | 同一 URL 反复触发 fallback-1→2→3→1→2→3 循环 | markPreheatReload 触发 notifyItemChanged → 重新 bind → bind 无条件 retryCount=0 重置降级链计数器 → 加载失败重新进入降级1 → 无限循环 |

## 修复方案概览

### Q1 修复：滚动位置
1. `onCreateViewHolder` 用 `ViewGroup.LayoutParams(MATCH_PARENT, defaultHeight)` 强制创建新 layoutParams
2. `observeNewItems` 中 isInitialScrollDone 逻辑改用 `viewTreeObserver.addOnGlobalLayoutListener` 在布局完成后执行 scrollToPosition(0)
3. 首次插入时禁用 loadNextArticle 自动触发

### Q2 修复：L2 超时返回 URL + 策略2 继续策略3
1. `extractWithWebView` 移除外层 `withTimeoutOrNull` 包装（sniffImageUrls 内部已有超时机制并返回已收集 URL），改为 try-catch
2. `enhancedParseImageUrls` 策略2 命中数 < 3 时不直接 return，继续执行策略3，合并结果

### Q3 修复：降级链不重置 retryCount
1. `bind()` 方法将 `isPreheatReload` 计算前移，根据 `isPreheatReload` 决定是否重置 retryCount（预热重载场景不重置）
2. `markPreheatReload` 保留 notifyItemChanged（确保 bypass failUrl + skipMemory 生效）

## 文档导航

| 文档 | 内容 |
|------|------|
| [README.md](./README.md) | 本文档：问题概览 + 修复方案概览 + 文档导航 |
| [spec.md](./spec.md) | 问题背景 + 3 个问题详细描述 + 验收标准 + 影响范围分析 |
| [design.md](./design.md) | 根因分析（含日志证据行号）+ 源码级设计（含代码行号和修改逻辑）+ 风险评估 + 回退方案 |
| [tasks.md](./tasks.md) | 实施任务清单（分阶段）+ 每个任务的验证方法 + 编译测试包验证步骤 |

## 源码核实文件清单

以下源码文件已在 design.md 编写前完成核实：

| 文件 | 关键行段 | 核实结论 |
|------|---------|---------|
| `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt` | L120-135, L241-265, L447-501, L777-860 | Q1/Q3 修复方案可行，isPreheatReload 标志已存在 |
| `app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt` | L692-714 | Q1 isInitialScrollDone 逻辑确认 |
| `app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt` | L231-409, L565-613 | Q2 策略2 return 确认，extractWithWebView 外层 withTimeoutOrNull 确认 |
| `app/src/main/java/io/legado/app/help/image/ImageSnifferWebView.kt` | L75-119 | **sniffImageUrls 内部已实现超时返回 collectedUrls（L100-107），无需修改** |

## 重要说明

design.md 中对原始修复方案有 2 处源码核实修正：
1. **Q2 修正**：`ImageSnifferWebView.sniffImageUrls()` 内部已实现超时返回 collectedUrls（非 emptyList），真正 bug 在 `extractWithWebView` 外层 `withTimeoutOrNull` 时间相同导致外层先超时。
2. **Q3 修正**：`isPreheatReload` 标志已存在（L489），但 L454 无条件重置 retryCount 未使用此标志，修复改为根据 isPreheatReload 决定是否重置。
