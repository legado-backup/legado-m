# 视频播放器嗅探失败 & 搜索聚合默认勾选修复

> **Spec ID**：video-search-sniff-fix-20260727
> **创建日期**：2026-07-27
> **类型**：Bug 修复（双问题）
> **状态**：待实施
> **测试包**：`io.legado.miss.app.debug`（代码优化任务专用）

---

## 一、任务背景

用户反馈两个独立的视频播放问题，经日志分析与源码根因分析，定位为两个独立的 Bug，需在一次交付中合并修复：

### 问题一：视频嗅探失败（浏览器能播但内置嗅探失败）

- **现象**：部分站点在系统浏览器中可正常播放视频，但应用内置嗅探播放必然失败；典型表现为"第一个视频必失败"，切换或下拉后第二个视频可成功。
- **日志证据**：8428 条错误日志交叉分析，11 次 BUFFERING 12s 超时触发错误 fallback，30 次 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED`。
- **根因**：`Exo2MediaPlayer.kt` 内的 ExoFallback fallback 链路在 BUFFERING 12s 超时后，将已嗅探成功的 contentType 错误切换到不兼容的 contentType（如 HLS→MP4 或 MP4→HLS），导致解析器与视频流格式不匹配，必然抛出解析失败异常。浏览器（WebView）直接根据 mimeType 选择解码器，跳过此 fallback 链路，因此不受影响。**注**：项目无独立 `ExoFallback.kt` 文件，fallback 逻辑内聚在 `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` 的 `prepareAsyncInternal` 及其内部回调中。

### 问题二：搜索聚合默认勾选问题（多视频整合后点击阅读必失败）

- **现象**：订阅源顶部搜索关键字，多个源返回相同视频被整合显示在一个聚合项中，点击"阅读"按钮必然播放失败；用户必须手动点击源列表的第一项才能成功播放。
- **根因（双重）**：
  1. `RssArticleInfoActivity` 默认选中源使用 `HashMap.keys.firstOrNull()`（顺序不保证），与 `rssArticles` 列表的 `getDefaultArticle()`（取 `origins.firstOrNull()`，顺序固定）可能不一致，导致默认选中源与 `rssArticles[0]` 的源不匹配。
  2. `VideoPlay.switchToArticle(index)` 加载 `rssArticles[index]` 的文章时，更新了 `rssStar`/`rssRecord`，但**未更新 `source` 字段**。`source` 仍为 `initSource` 中通过 Intent `sourceKey` 加载的源（用户选的源），与实际加载的 `rssArticle` 不匹配时，`ruleContent` 解析失败。

---

## 二、修复策略概述

### 问题一修复策略（ExoFallback 链路 + 预热机制）

| 优先级 | 修复项 | 目标 |
|--------|--------|------|
| P0 | 修复 ExoFallback 错误 contentType 切换 | fallback 列表保持相同 contentType，仅切换 DataSource 配置 |
| P0 | 延长首次 BUFFERING 超时时间 | 首次 BUFFERING 超时改为 25s（CDN 冷启动），后续保持 12s |
| P1 | 修复 FirstFramePreloader 缓存频繁清理 | 延迟清理预热缓存，避免首帧必须从 CDN 实时拉取 |
| P1 | DoH DNS 失败时立即降级到系统 DNS（✅ 已实现） | 冷启动 30s 熔断已交付（DohDns.kt 行 79/111/201-209/229-246），本次仅验证 |
| P1 | 增加"首个视频"预热机制 | 用户点击视频前预加载视频流前 64KB（识别 moov 头） |
| P2 | fallback 前增加 contentType 兼容性校验 | 切换 contentType 前校验流头部 magic bytes |
| P2 | 增加 fallback 决策日志 | 记录每次 fallback 的原因+前后 contentType |

### 问题二修复策略（默认选中源 + source 同步）

| 优先级 | 修复项 | 目标 |
|--------|--------|------|
| P0 | 统一默认选中源 | `RssArticleInfoActivity` 用 `origins.firstOrNull()` 替代 `HashMap.keys.firstOrNull()` |
| P0 | `switchToArticle` 同步更新 source | 加载 `rssArticles[index]` 时同步更新 `source` 为 `article.origin` 对应的源 |
| P1 | `ReadRss.readRss` 增加 source 兜底校验 | 即使用户选的源不在 `rssArticles` 中，也确保 `source` 与 `rssArticle` 匹配 |

---

## 三、验收标准概述

### P0 验收标准（必须通过）

1. **问题一场景**：在浏览器可播放的站点，内置嗅探播放首次成功率 ≥ 95%（原 ~0%）
2. **问题一场景**：BUFFERING 12s 超时不再触发错误 contentType 切换；首次 BUFFERING 超时阈值提升至 25s
3. **问题一场景**：fallback 决策日志输出完整（原因+前后 contentType+DataSource 配置）
4. **问题二场景**：搜索聚合后默认点击"阅读"按钮，播放成功率 100%
5. **问题二场景**：搜索聚合后点击源列表任意一项（非第一个），播放成功率 100%
6. **问题二场景**：搜索聚合后点击"阅读"按钮播放，上下滑动切换文章，每篇文章都能正确加载对应源

### P1 验收标准（应通过）

1. 首次播放首帧延迟 < 25s（原部分场景 >12s 触发错误 fallback）
2. FirstFramePreloader 缓存清理频率降低，预热机制生效
3. DoH DNS 失败后 30s 内重试，不再长时间禁用

---

## 四、关联文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 功能规范 | [spec.md](./spec.md) | 功能规范 + P0/P1 验收标准 + 非目标 + 用户场景 |
| 技术设计 | [design.md](./design.md) | 技术架构 + 根因分析 + 修复方案 + 接口设计 + 风险与缓解 + 日志设计 |
| 任务清单 | [tasks.md](./tasks.md) | Phase A/B/C 任务分解 + 检查点 + 依赖关系 + 风险点 + 反模式 |
| 视频嗅探失败分析报告 | [../../temp-analysis/005-video-sniff-fail-analysis-20260727.md](../../temp-analysis/005-video-sniff-fail-analysis-20260727.md) | 问题一日志分析与根因定位 |
| 搜索聚合默认勾选分析报告 | [../../temp-analysis/search-aggregate-default-select-analysis-20260727.md](../../temp-analysis/search-aggregate-default-select-analysis-20260727.md) | 问题二源码根因分析 |

---

## 五、输出安全声明

本文档所有 URL 已路径模式化（`/path/{id}`），所有域名已代号化（`站点A/B/C` 或 `***`），所有源名称已代号化（`源[N]`），所有 cookie/token 内容已隐藏为 `***`。文档仅输出技术结论（错误码/异常类型/调用栈/根因/修复方案）。
