# 审查报告：视频播放器嗅探失败 & 搜索聚合默认勾选修复

> **审查日期**：2026-07-27
> **审查对象**：`docs/specs/video-search-sniff-fix-20260727/` 四文档（README.md / spec.md / design.md / tasks.md）
> **对照参考**：`docs/temp-analysis/005-video-sniff-fail-analysis-20260727.md` + `docs/temp-analysis/search-aggregate-default-select-analysis-20260727.md`
> **审查方法**：源码静态验证 + 文档完整性核对 + 修复方案合理性评估

---

## 一、文档完整性审查结果

### 1.1 README.md ✅ 通过

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 任务背景 | ✅ | 包含问题一/问题二的根因摘要与日志证据量级 |
| 修复策略概述 | ✅ | P0/P1/P2 分级表格清晰，区分 ExoFallback 链路与默认选中源链路 |
| 验收标准概述 | ✅ | P0 6 项 + P1 3 项，与 spec.md 对齐 |
| 关联文档链接 | ✅ | 5 个相对路径链接全部有效（含两份分析报告） |
| 输出安全声明 | ✅ | URL 路径模式化、域名代号化、源名称代号化、cookie 隐藏 |

### 1.2 spec.md ✅ 通过

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 功能规范 | ✅ | F1.1-F1.9（问题一 9 项）+ F2.1-F2.5（问题二 5 项），分级合理 |
| P0/P1 验收标准 | ✅ | AC1.1-AC1.5 + AC2.1-AC2.5 + AC3.1-AC3.4，每项含验证方法与通过标准 |
| 非目标 | ✅ | NG1-NG10 共 10 项，覆盖 Rss.getContentAwait / mergeItems / 数据结构 / 依赖版本等边界 |
| 用户场景 | ✅ | 场景 A-F 共 6 个，含修复前后对比，场景 E 含"播放 origins[0] 而非用户选源"的局限说明 |

### 1.3 design.md ⚠️ 基本通过（修复方案源码位置错误）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 技术架构 | ✅ | 视频播放链路 + 搜索聚合跳转链路两张时序图清晰 |
| 根因分析 | ✅ | 引用日志行号证据链（HLS 案例 + MP4 案例），根因矩阵覆盖 4 场景 |
| 修复方案 | ⚠️ | 7 个修复方案中 1.1/1.2/1.3/1.4 的源码位置错误（详见第二节） |
| 关键接口 | ⚠️ | 4.1 ExoFallback 接口为"假设性设计"，实际类名与文件路径不符 |
| 风险缓解 | ✅ | R1-R8 共 8 项风险，每项含影响+缓解措施 |
| 日志设计 | ✅ | 日志关键字、级别、触发时机、内容齐全，含安全要求 |

### 1.4 tasks.md ✅ 通过

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Phase 划分 | ✅ | Phase A（问题一 6 任务）+ Phase B（问题二 3 任务）+ Phase C（验证 5 任务） |
| 任务清单 | ✅ | 每个任务含文件路径、子任务、验收标准、预估时间 |
| 检查点 | ✅ | 3 个检查点（Phase A/B/C 完成后），含触发条件+检查项+决策三选项 |
| 依赖关系 | ✅ | ASCII 依赖图清晰，Phase A/B 独立可并行，B3 依赖 B2 |
| 风险点 | ✅ | R1-R6 共 6 项，含缓解措施 |
| 反模式 | ✅ | AP1-AP10 共 10 项，覆盖未 Read 源码/违反非目标/日志残留/包选择等 |

---

## 二、修复方案源码一致性验证（核心审查点）

### 2.1 问题一修复方案验证

#### 修复点 1.1：ExoFallback 保持 contentType

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | `app/src/main/java/io/legado/app/ui/video/ExoFallback.kt` | **该文件不存在**，实际为 `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | ❌ 不一致 |
| 类名 | `ExoFallback` | `Exo2MediaPlayer`（继承自 `IjkExo2MediaPlayer`） | ❌ 不一致 |
| fallback 列表构建函数 | `buildFallbackList()` | `buildFallbackTypes(sniff: SniffResult): List<Int>`（行 198-217） | ⚠️ 函数名不符 |
| fallback 列表内容 | `[sniffedContentType, otherContentType, ContentType.OTHER]` | 实际：`[HLS, DASH]` / `[DASH, HLS]` / `[SS, HLS, DASH]` / `[Progressive, HLS, DASH]` | ⚠️ 描述不准确（无 ContentType.OTHER 概念，C.TYPE_OTHER 即 Progressive） |
| contentType 切换逻辑 | BUFFERING 超时后切换到下一个 contentType | ✅ 一致（`tryNextFallback` 行 316-336 + `applyMediaSourceByType` 行 232-305） | ✅ 一致 |
| BUFFERING 超时触发 fallback | ✅ | `bufferingTimeoutRunnable`（行 120-128）postDelayed 12000L → `tryNextFallback()` | ✅ 一致 |

**关键差异**：
- design.md 与 tasks.md 中**所有引用 `ExoFallback.kt` 的位置都错误**，实际文件为 `Exo2MediaPlayer.kt`，路径在 `help/gsyVideo/` 而非 `ui/video/`
- design.md 4.1 节给出的 `ExoFallback` 类与 `FallbackItem` / `DataSourceConfig` / `FallbackReason` 等数据类是**全新设计**，源码中不存在这些类型，需要从零实现

#### 修复点 1.2：延长首次 BUFFERING 超时

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 超时常量 | `val BUFFERING_TIMEOUT_MS = 12_000` | **无此常量**，硬编码 `12000L` 在行 121 的 `postDelayed(12000L)` | ❌ 不一致 |
| setBufferingTimeoutMs 方法 | design.md 暗示存在 | **不存在**，需新增 | ❌ 不一致 |
| 超时位置 | `ExoFallback.kt` 或 `VideoPlayerActivity.kt` | 实际在 `Exo2MediaPlayer.kt` 行 120-128 | ❌ 路径错误 |
| isFirstPlay 判断逻辑 | `VideoPlay.rssArticleIndex == 0 且未成功播放过` | **VideoPlay 无此字段**，需新增 `hasPlayedSuccessfully` 标志位 | ⚠️ 需新增字段 |

#### 修复点 1.3：FirstFramePreloader 缓存延迟清理

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | `app/src/main/java/io/legado/app/ui/video/FirstFramePreloader.kt` | 实际为 `app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt` | ❌ 路径错误 |
| Activity onPause/onStop 立即清理 | design.md 声称"Activity onPause/onStop 时立即清理缓存" | **FirstFramePreloader 无 Activity 生命周期绑定**，由 `VideoPlay.clearPlayData`（行 1100）调用 `FirstFramePreloader.clearCache()` | ❌ 前提描述错误 |
| clearCache 实现 | 延迟 30s 清理 | 当前 `clearCache()`（行 139-142）立即清理 `preloadCache`（ConcurrentHashMap<String, Long>），**不清理预加载数据本身**（预加载数据写入 ExoPlayer SimpleCache，行 112-118） | ⚠️ 描述含糊 |
| 预热缓存大小限制 | design.md R4 说"最多 5 个视频 × 64KB = 320KB" | 当前 `MAX_CACHE_SIZE = 10`（行 37）+ `PRELOAD_BYTES = 1MB-1`（行 31），实际最多 10 个 × 1MB = 10MB | ❌ 数值不符 |
| cache cleared 日志 | ✅ 存在（行 141 `AppLog.putDebug("FirstFramePreloader: cache cleared")`） | ✅ 一致 | ✅ 一致 |

**关键差异**：
- FirstFramePreloader 是 `object` 单例，无 Activity 生命周期感知
- 预加载数据**实际写入 ExoPlayer 的 SimpleCache**（行 112-118），不是 FirstFramePreloader 自己的缓存
- design.md 修复方案 1.3 的"延迟清理"含义需要重新评估：延迟清理 `preloadCache`（URL→时间戳映射）意义不大，应该延迟清理 ExoPlayer SimpleCache 中的预热分片
- 但 ExoPlayer SimpleCache 由 `cache` 字段管理（`ExoPlayerHelper.kt` 行 892-903），Activity onDestroy 时是否清理需进一步确认

#### 修复点 1.4：DoH DNS 禁用时间缩短

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | `app/src/main/java/io/legado/app/help/.../DohDns.kt` | `app/src/main/java/io/legado/app/help/http/DohDns.kt` | ✅ 路径匹配 |
| 当前禁用时间 | design.md 说"5min" | **冷启动场景已为 30s**（行 79 `COLD_START_DISABLE_MS = 30_000L`），常规熔断仍为 5min（行 66 `DISABLE_DURATION_MS = 5 * 60 * 1000L`） | ❌ 描述不准确 |
| 冷启动熔断 30s | design.md 说是修复目标 | **已实现**（行 111 `isColdStart = true` + 行 201-209 冷启动分支） | ❌ 修复内容已存在 |
| 异步预热 DoH | design.md 未提及 | **已实现**（行 229-246 `asyncPreheatDoh`，30s 后探测 cloudflare-dns.com 恢复） | ❌ 修复内容已存在 |
| 重试失败 3 次延长至 5min | design.md A4.4 任务 | 源码行 210-213 `else if (globalFailCount.incrementAndGet() >= GLOBAL_FAIL_THRESHOLD)`，**GLOBAL_FAIL_THRESHOLD = 3**（行 63），常规熔断 5min 已实现 | ✅ 已实现 |

**关键差异**：
- **design.md 修复方案 1.4 描述的修复内容已部分实现**：冷启动 30s + 异步预热已存在
- analysis report 005 提到的"disable DoH 5min"日志多次出现，说明**冷启动熔断未覆盖所有失败场景**（如非冷启动场景仍走 5min 熔断）
- design.md 修复方案 1.4 过于简化，实际应分析"为何冷启动 30s 仍出现 5min 禁用日志"——可能是 `isColdStart` 标志位被提前置 false（如首次 lookup 成功后置 false，后续失败走常规熔断）

### 2.2 问题二修复方案验证

#### 修复点 2.1：统一默认选中源

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | design.md/tasks.md 说 `app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt` 行 215 | ✅ 一致（`RssArticleInfoActivity.kt` 位于 `ui/rss/search/`，行 215 确认 `selectedOrigin = articlesMap.keys.firstOrNull()`） | ✅ 一致 |
| 任务描述路径 | 任务描述说 `app/src/main/java/io/legado/app/ui/rss/read/RssArticleInfoActivity.kt` | 实际为 `ui/rss/search/`，任务描述有误（与文档不符） | ⚠️ 任务描述有误 |
| 修复后代码 | `selectedOrigin = searchArticle?.origins?.firstOrNull() ?: articlesMap.keys.firstOrNull()` | 需新增 `RssSearchSourceHolder.searchArticle` 引用（已确认 Holder 有此字段） | ✅ 可实施 |
| RssSearchSourceHolder 可访问 | design.md B1.3 任务确认 | `RssSearchSourceHolder.searchArticle` 在 `RssSearchActivity.showArticleInfo`（行 399-407）赋值，详情页可读 | ✅ 一致 |

#### 修复点 2.2：switchToArticle 同步更新 source

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | `app/src/main/java/io/legado/app/model/VideoPlay.kt` 行 967-992 | ✅ 一致（行号匹配，函数签名匹配） | ✅ 一致 |
| 当前代码不更新 source | design.md 描述准确 | ✅ 一致（行 978-987 `Coroutine.async` 块内只更新 rssStar/rssRecord，不更新 source） | ✅ 一致 |
| source 字段类型 | design.md B2.6/B2.7 需确认与 RssSource 兼容 | `var source: BaseSource? = null`（行 152），RssSource 继承 BaseSource，**类型兼容** | ✅ 兼容 |
| appDb.rssSourceDao.getByKey 返回类型 | design.md B2.7 需确认 | 返回 `RssSource?`，可赋值给 `BaseSource?` | ✅ 兼容 |
| source 字段并发保护 | design.md 未提及 | **source 字段无 @Volatile 注解**（行 152），switchToArticle 在 IO 线程写、startPlay 在 Main 线程读，**存在可见性风险** | ❌ 未识别并发问题 |
| article.origin 字段 | design.md 用 `article.origin` 查询源 | RssArticle.origin 是 String（源 URL），与 `RssSource.sourceUrl` 对应，`getByKey(origin)` 查询正确 | ✅ 一致 |

#### 修复点 2.3：ReadRss.readRss source 兜底校验

| 验证项 | 文档描述 | 源码实际 | 一致性 |
|--------|----------|----------|--------|
| 文件路径 | `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` 行 58-104 | ✅ 一致（行号匹配，函数签名匹配） | ✅ 一致 |
| 当前代码 `?: 0` 兜底 | design.md 描述准确 | ✅ 一致（行 75 `VideoPlay.rssArticleIndex = rssArticles?.indexOfFirst { it.link == rssArticle.link } ?: 0`） | ✅ 一致 |
| 修复后保留 index = -1 + WARN 日志 | design.md 描述准确 | ✅ 可实施（需注意：`?: 0` 改为 `if (index == -1) 0 else index` 后，rssArticleIndex 仍兜底为 0） | ✅ 一致 |

---

## 三、修复方案合理性评估

### 3.1 修复点 1.1：ExoFallback 保持 contentType

| 维度 | 评估 |
|------|------|
| 合理性评分 | **4/5** |
| 方案核心 | fallback 列表全部使用 sniffedContentType，仅切换 DataSource 配置 |
| 优点 | 直接解决根因（contentType 不匹配导致解析失败），实现路径清晰 |
| 风险点 | **R1：嗅探识别错误时无法通过 fallback 恢复**（如 sniff 误判 MP4 为 HLS，保持 HLS 后永远失败） |
| 边界情况 | 1. sniff 返回 UNKNOWN（TYPE_UNKNOWN=-1）时如何处理？当前 `buildFallbackTypes` 有 UNKNOWN 分支（按 URL 后缀启发式），修复后应保留此分支<br>2. 同 contentType 重试 1-2 次仍失败时，是否允许切换 contentType？design.md R1 缓解措施提到"允许切换"，但未在修复方案中明确 |
| 改进建议 | 1. 保留 contentType 切换作为**最后兜底**（同 contentType 重试 2 次失败后切换）<br>2. UNKNOWN 分支保留现有逻辑（已按 URL 后缀启发式排序）<br>3. 修复方案应明确：fallback 列表前 2 项保持同 contentType，第 3 项允许切换到兼容 contentType（如 HLS→DASH，但禁止 HLS→Progressive） |

### 3.2 修复点 1.2：BUFFERING 25s 超时

| 维度 | 评估 |
|------|------|
| 合理性评分 | **3/5** |
| 方案核心 | 首次播放 25s，后续 12s |
| 优点 | 覆盖 CDN 冷启动场景，降低误触发 fallback 概率 |
| 风险点 | **R2：25s 用户感知卡顿**，且 isFirstPlay 判断逻辑不清晰 |
| 边界情况 | 1. 用户切换视频后再次回到第一个视频，是否仍算"首次"？<br>2. 多个视频列表（如搜索结果）切换时，每个列表的第一个是否都算"首次"？<br>3. isFirstPlay 字段何时重置？design.md 说"未成功播放过"，但未定义重置时机 |
| 改进建议 | 1. 改为**动态超时**：基于网络类型（WiFi 15s / 4G 25s / 3G 35s）<br>2. 或改为**渐进超时**：首次 25s，第二次 18s，第三次 12s（避免长期 25s 影响体验）<br>3. 明确 isFirstPlay 重置时机：`VideoPlay.initSource` 时重置为 true，`startPlay` 成功后置 false<br>4. 25s 期间显示加载进度条 + "CDN 冷启动中"提示（design.md R2 已提及但未细化） |

### 3.3 修复点 1.3：FirstFramePreloader 缓存延迟清理

| 维度 | 评估 |
|------|------|
| 合理性评分 | **2/5** |
| 方案核心 | Activity onPause 时延迟 30s 清理，而非立即清理 |
| 优点 | 避免快速切回时缓存已清理需重新预热 |
| 风险点 | **方案前提错误**：FirstFramePreloader 无 Activity 生命周期绑定，由 VideoPlay.clearPlayData 调用清理 |
| 边界情况 | 1. VideoPlay.clearPlayData 何时调用？需确认（可能在 VideoPlayerActivity.onDestroy）<br>2. 预加载数据写入 ExoPlayer SimpleCache，延迟清理 FirstFramePreloader.preloadCache（URL→时间戳）意义不大<br>3. ExoPlayer SimpleCache 的清理时机需单独评估 |
| 改进建议 | 1. **重新评估修复目标**：是延迟清理 `preloadCache`（URL→时间戳映射）还是延迟清理 ExoPlayer SimpleCache 中的预热分片？<br>2. 若为前者，意义不大（preloadCache 仅存时间戳，不占内存）<br>3. 若为后者，需修改 `VideoPlay.clearPlayData` 行 1100 的调用逻辑，而非 FirstFramePreloader 自身<br>4. 缓存大小限制数值需修正：design.md 说 5×64KB=320KB，实际 10×1MB=10MB |

### 3.4 修复点 1.4：DoH DNS 禁用时间缩短

| 维度 | 评估 |
|------|------|
| 合理性评分 | **2/5** |
| 方案核心 | 禁用时间 5min → 30s |
| 优点 | 缩短 DoH 不可用时间，提升 DNS 解析成功率 |
| 风险点 | **修复内容已部分实现**：冷启动 30s + 异步预热已存在 |
| 边界情况 | 1. 常规熔断（非冷启动）仍为 5min，是否需要也改为 30s？<br>2. isColdStart 标志位何时置 false？若首次 lookup 成功即置 false，后续失败走常规熔断 5min，仍会出现"disable DoH 5min"日志 |
| 改进建议 | 1. **先分析为何冷启动 30s 已实现仍出现 5min 日志**（可能是 isColdStart 提前置 false）<br>2. 评估是否将常规熔断也改为 30s（或缩短为 1min）<br>3. design.md 修复方案 1.4 需重写：明确"已实现冷启动 30s，本期改为优化常规熔断时间"或"维持现状，仅增加日志" |

### 3.5 修复点 2.1：统一默认选中源

| 维度 | 评估 |
|------|------|
| 合理性评分 | **5/5** |
| 方案核心 | 用 `searchArticle.origins.firstOrNull()` 替代 `articlesMap.keys.firstOrNull()` |
| 优点 | 最小改动，直接对齐 rssArticles[0] 的源选择逻辑 |
| 风险点 | R6：UI 高亮状态需刷新（已识别） |
| 边界情况 | 1. searchArticle 为 null 时兜底 `articlesMap.keys.firstOrNull()`（保留原逻辑）<br>2. origins 为空时兜底 `articlesMap.keys.firstOrNull()` |
| 改进建议 | 无需改进，方案完善 |

### 3.6 修复点 2.2：switchToArticle 同步更新 source

| 维度 | 评估 |
|------|------|
| 合理性评分 | **4/5** |
| 方案核心 | 加载 rssArticles[index] 时同步更新 source 为 article.origin 对应的源 |
| 优点 | 根本修复，覆盖所有场景（默认选中+用户选其他源+上下滑动切换） |
| 风险点 | **R7：source 字段并发可见性问题**（design.md 未识别） |
| 边界情况 | 1. source 字段无 @Volatile，IO 线程写、Main 线程读存在可见性风险<br>2. appDb.rssSourceDao.getByKey 返回 null 时如何处理？（design.md 未明确）<br>3. source 更新后，rssStar/rssRecord 是否需要重新加载？（当前代码已加载，但顺序需确认） |
| 改进建议 | 1. **source 字段加 @Volatile**（或用 Mutex 保护读写）<br>2. source 为 null 时输出 ERROR 日志并 return false（避免 startPlay 用 null source）<br>3. 明确 source 更新顺序：先更新 source → 再加载 rssStar/rssRecord → 最后 startPlay（design.md 代码示例顺序正确） |

### 3.7 修复点 2.3：ReadRss.readRss source 兜底校验

| 维度 | 评估 |
|------|------|
| 合理性评分 | **4/5** |
| 方案核心 | 保留 index = -1 + WARN 日志，rssArticleIndex 兜底为 0 |
| 优点 | 不改变 rssArticles 列表语义，配合 2.2 确保 source 同步 |
| 风险点 | 场景 E 修复后播放 origins[0] 的文章而非用户选的 origins[N] 的文章 |
| 边界情况 | 1. rssArticles 为 null 时 indexOfFirst 返回 -1，兜底为 0（当前 `?: 0` 已处理）<br>2. rssArticle.link 与 rssArticles 中所有文章的 link 都不匹配时，WARN 日志需输出双端 origin |
| 改进建议 | 1. WARN 日志格式需符合输出安全规范（origin 前 2 字符 + ***）<br>2. 后续可考虑独立 spec 改变 rssArticles 列表语义（插入用户选的源的文章到列表头） |

---

## 四、验收标准可行性评估

### 4.1 P0 验收标准

| 编号 | 验收项 | 可验证性 | 改进建议 |
|------|--------|----------|----------|
| AC1.1 | ExoFallback 不切换 contentType | ✅ 可验证（日志 `ExoFallback: try contentType=` 序列保持不变） | 明确日志关键字为 `try contentType=` 而非 `switch to next MediaSource` |
| AC1.2 | 首次 BUFFERING 超时阈值 25s | ⚠️ 可验证但需明确 isFirstPlay 判断 | 需先定义 isFirstPlay 字段重置时机，否则"首次"语义模糊 |
| AC1.3 | fallback 决策日志完整 | ✅ 可验证（新增日志关键字 `ExoFallback: trigger reason=` + `before contentType=` + `dataSource changed:`） | 日志关键字与 design.md 6.1 节一致 |
| AC1.4 | 浏览器可播放站点内置播放成功 ≥ 95% | ⚠️ 真机测试可能无法复现"第一个视频必失败" | tasks.md R3 已识别：使用日志中记录的站点测试，如无法复现则基于日志分析验收 |
| AC1.5 | 不再出现错误 contentType 切换导致的解析失败 | ✅ 可验证（日志检查 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED` / `ERROR_CODE_PARSING_MANIFEST_MALFORMED` 出现次数为 0） | 明确"修复前 30 次"的对比基线 |
| AC2.1 | 默认选中源与 rssArticles[0] 一致 | ✅ 可验证（源码审查 + 日志 `selectedOrigin =`） | 日志需输出 origin 前 2 字符 + *** |
| AC2.2 | 默认点击"阅读"按钮播放成功 10/10 | ✅ 可验证（真机测试 10 次） | 明确测试站点与搜索关键字 |
| AC2.3 | 手动点击源列表任意一项播放成功 15/15 | ✅ 可验证（真机测试第 1/2/3 项各 5 次） | 同上 |
| AC2.4 | 上下滑动切换文章播放成功 5/5 | ✅ 可验证（真机测试切换 5 次） | 同上 |
| AC2.5 | switchToArticle 更新 source 日志 | ✅ 可验证（日志 `switchToArticle: source 更新为`） | 日志格式符合输出安全规范 |

### 4.2 P1 验收标准

| 编号 | 验收项 | 可验证性 | 改进建议 |
|------|--------|----------|----------|
| AC3.1 | 首次播放首帧延迟 < 25s | ✅ 可验证（日志 `ExoPlayer first frame rendered: latency=`） | 明确"首次"定义与 isFirstPlay 一致 |
| AC3.2 | FirstFramePreloader 缓存延迟清理 | ⚠️ 可验证但前提需重新评估 | 需先确认 FirstFramePreloader.clearCache 调用方（VideoPlay.clearPlayData 行 1100），再决定日志触发时机 |
| AC3.3 | DoH DNS 禁用时间 ≤ 30s | ⚠️ 可验证但需区分冷启动 vs 常规熔断 | 冷启动 30s 已实现，常规熔断仍为 5min；需明确验收目标是哪个场景 |
| AC3.4 | ReadRss.readRss source 兜底校验 | ✅ 可验证（日志 `ReadRss: source mismatch WARN`） | 日志格式符合输出安全规范 |

### 4.3 遗漏的边界场景

| 编号 | 遗漏场景 | 建议补充 |
|------|----------|----------|
| MS1 | sniff 返回 UNKNOWN（TYPE_UNKNOWN=-1）时 fallback 列表如何构建？ | spec.md F1.1 应明确 UNKNOWN 分支处理 |
| MS2 | source 字段并发可见性问题（无 @Volatile） | spec.md F2.2 应增加并发保护要求 |
| MS3 | appDb.rssSourceDao.getByKey 返回 null 时 switchToArticle 如何处理？ | spec.md F2.2 应增加 null 处理 |
| MS4 | isFirstPlay 字段重置时机不明确 | spec.md F1.3 应明确重置时机（initSource 时重置） |
| MS5 | 常规 DoH 熔断（非冷启动）是否也改为 30s？ | spec.md F1.6 应明确常规熔断时间 |
| MS6 | FirstFramePreloader 预加载数据写入 ExoPlayer SimpleCache，延迟清理的对象是哪个？ | spec.md F1.5 应明确清理对象 |

---

## 五、任务清单完整性评估

### 5.1 遗漏任务

| 编号 | 遗漏任务 | 建议补充 |
|------|----------|----------|
| MT1 | **修正 ExoFallback.kt 文件路径错误** | tasks.md A1/A2/A6 的文件路径需改为 `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` |
| MT2 | **新增 isFirstPlay 字段到 VideoPlay** | tasks.md A2 需增加"在 VideoPlay 新增 `var hasPlayedSuccessfully: Boolean = false` 字段"子任务 |
| MT3 | **确认 DoH DNS 30s 冷启动已实现** | tasks.md A4 需改为"评估常规熔断是否改为 30s，或仅增加日志" |
| MT4 | **重新评估 FirstFramePreloader 修复目标** | tasks.md A3 需改为"修改 VideoPlay.clearPlayData 行 1100 调用逻辑"或"修改 ExoPlayer SimpleCache 清理时机" |
| MT5 | **source 字段加 @Volatile** | tasks.md B2 需增加"source 字段加 @Volatile 注解"子任务 |
| MT6 | **appDb.rssSourceDao.getByKey 返回 null 处理** | tasks.md B2 需增加"source 为 null 时输出 ERROR 日志并 return false"子任务 |
| MT7 | **修正 FirstFramePreloader.kt 文件路径** | tasks.md A3 的文件路径需改为 `app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt` |
| MT8 | **修正 FirstFramePreloader 缓存大小数值** | tasks.md A3.5 的"5 个视频 × 64KB = 320KB"需改为实际数值或重新定义 |

### 5.2 任务粒度问题

| 任务 | 预估 | 粒度评估 | 建议 |
|------|------|----------|------|
| A1（ExoFallback 修复） | 4h | ⚠️ 偏小 | 实际涉及 Exo2MediaPlayer.kt 大改（buildFallbackTypes 重写 + DataSourceConfig 新增 + 日志），建议拆为 A1a（重构 buildFallbackTypes）+ A1b（实现 DataSourceConfig 切换）+ A1c（日志），各 2h |
| A2（BUFFERING 超时） | 2h | ✅ 合理 | 但需新增 isFirstPlay 字段，可能需 3h |
| A3（缓存延迟清理） | 3h | ⚠️ 前提需重新评估 | 需先确认修复目标（FirstFramePreloader.preloadCache vs ExoPlayer SimpleCache），再评估粒度 |
| A4（DoH DNS） | 2h | ⚠️ 前提需重新评估 | 30s 冷启动已实现，可能需改为"评估+日志增强"，1h |
| A5（预热机制） | 4h | ✅ 合理 | 涉及新文件 VideoPreloader.kt 或 VideoPlay.kt 扩展 |
| A6（contentType 校验） | 3h | ✅ 合理 | magic bytes 校验逻辑清晰 |
| B1（默认选中源） | 1h | ✅ 合理 | 单行修改 + 日志 |
| B2（switchToArticle source） | 2h | ⚠️ 偏小 | 需新增 @Volatile + null 处理 + 日志，建议 3h |
| B3（ReadRss 兜底） | 1h | ✅ 合理 | 单函数修改 + 日志 |

### 5.3 依赖关系问题

| 问题 | 说明 | 建议 |
|------|------|------|
| A4 依赖关系不清晰 | A4 修改 DohDns.kt，但 DohDns 已有 30s 冷启动，A4 实际工作不明确 | 需先完成 MT3（确认修复目标）再确定依赖 |
| A3 依赖关系不清晰 | A3 修改 FirstFramePreloader，但实际清理逻辑在 VideoPlay.clearPlayData | 需先完成 MT4（重新评估修复目标）再确定依赖 |
| A5 与 A3 关系 | A5 预热机制依赖 FirstFramePreloader，A3 修改 FirstFramePreloader | A5 应依赖 A3，但 tasks.md 未标注 |
| B3 依赖 B2 | ✅ 正确 | 已标注 |

---

## 六、总体审查结论

### 6.1 结论：⚠️ 需调整

### 6.2 理由

**通过的方面**：
1. 文档结构完整，符合 OpenSpec 规范（README/spec/design/tasks 四文档齐全）
2. 问题二修复方案（2.1/2.2/2.3）源码一致性高，可直接实施
3. 根因分析准确，引用日志行号证据链完整
4. 风险识别全面（R1-R8 + AP1-AP10）
5. 验收标准可验证性较高（P0 10 项中 7 项可验证）

**需调整的方面**：
1. **问题一修复方案源码位置错误**：design.md 与 tasks.md 中所有引用 `ExoFallback.kt` 的位置都错误，实际文件为 `Exo2MediaPlayer.kt`（路径 `help/gsyVideo/`，类名 `Exo2MediaPlayer`），需全部修正
2. **修复方案 1.4（DoH DNS）描述不准确**：冷启动 30s + 异步预热已实现，design.md 说的"修改禁用时间 5min → 30s"已部分实现，需重新评估修复目标
3. **修复方案 1.3（FirstFramePreloader）前提描述错误**：FirstFramePreloader 无 Activity 生命周期绑定，由 VideoPlay.clearPlayData 调用清理；预加载数据写入 ExoPlayer SimpleCache 而非 preloadCache，需重新评估修复目标
4. **source 字段并发可见性问题未识别**：source 无 @Volatile，IO 线程写、Main 线程读存在可见性风险
5. **isFirstPlay 字段重置时机不明确**：需明确在 VideoPlay.initSource 时重置
6. **缓存大小数值不符**：design.md R4 说 5×64KB=320KB，实际 10×1MB=10MB

### 6.3 阻塞性问题

| 编号 | 阻塞问题 | 阻塞范围 |
|------|----------|----------|
| BL1 | ExoFallback.kt 文件路径错误 | 阻塞 A1/A2/A6 全部任务，必须先修正路径 |
| BL2 | DoH DNS 30s 冷启动已实现 | 阻塞 A4 任务，必须先确认修复目标 |
| BL3 | FirstFramePreloader 修复目标不明确 | 阻塞 A3 任务，必须先确认清理对象 |

---

## 七、修改建议清单

### 7.1 高优先级（阻塞实施，必须先修正）

| 编号 | 修改项 | 修改位置 | 修改内容 |
|------|--------|----------|----------|
| FIX1 | 修正 ExoFallback.kt 文件路径 | design.md 2.3/4.1 + tasks.md A1/A2/A6 | 全部替换为 `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`，类名改为 `Exo2MediaPlayer` |
| FIX2 | 修正 fallback 列表内容描述 | design.md 2.3 修复方案 1.1 | 改为：实际列表为 `[HLS, DASH]` / `[Progressive, HLS, DASH]`，无 `ContentType.OTHER` 概念 |
| FIX3 | 重新评估 DoH DNS 修复方案 | design.md 2.3 修复方案 1.4 + tasks.md A4 | 明确"冷启动 30s 已实现"，修复目标改为"优化常规熔断时间"或"增加日志" |
| FIX4 | 重新评估 FirstFramePreloader 修复方案 | design.md 2.3 修复方案 1.3 + tasks.md A3 | 明确清理对象是 `preloadCache`（URL→时间戳）还是 ExoPlayer SimpleCache 中的预热分片 |
| FIX5 | 修正 FirstFramePreloader.kt 文件路径 | tasks.md A3 | 改为 `app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt` |
| FIX6 | 修正 BUFFERING 超时常量描述 | design.md 2.3 修复方案 1.2 | 改为：当前硬编码 `12000L`（行 121），无 `BUFFERING_TIMEOUT_MS` 常量，需新增 |

### 7.2 中优先级（影响实施质量，建议修正）

| 编号 | 修改项 | 修改位置 | 修改内容 |
|------|--------|----------|----------|
| FIX7 | 增加 source 字段并发保护 | spec.md F2.2 + design.md 4.2 + tasks.md B2 | source 字段加 @Volatile 注解，或用 Mutex 保护读写 |
| FIX8 | 明确 isFirstPlay 重置时机 | spec.md F1.3 + design.md 2.3 修复方案 1.2 | 在 VideoPlay.initSource 时重置为 true，startPlay 成功后置 false |
| FIX9 | 增加 appDb.rssSourceDao.getByKey null 处理 | spec.md F2.2 + design.md 4.2 | source 为 null 时输出 ERROR 日志并 return false |
| FIX10 | 修正缓存大小数值 | design.md R4 + tasks.md A3.5 | 改为实际数值 `10 个视频 × 1MB = 10MB` 或重新定义为 `5 × 64KB` |
| FIX11 | 补充 sniff UNKNOWN 分支处理 | spec.md F1.1 | 明确 sniff 返回 UNKNOWN 时 fallback 列表构建逻辑（保留现有 URL 后缀启发式） |
| FIX12 | 细化 fallback 切换策略 | design.md 2.3 修复方案 1.1 | 明确：同 contentType 重试 2 次失败后允许切换到兼容 contentType（禁止 HLS→Progressive） |

### 7.3 低优先级（文档完善，可后续补充）

| 编号 | 修改项 | 修改位置 | 修改内容 |
|------|--------|----------|----------|
| FIX13 | 补充 A5 与 A3 依赖关系 | tasks.md 三、依赖关系 | A5 预热机制依赖 A3 缓存延迟清理 |
| FIX14 | 调整任务粒度 | tasks.md A1/A2/B2 | A1 拆为 3 个子任务各 2h，A2 增至 3h，B2 增至 3h |
| FIX15 | 明确常规 DoH 熔断时间 | spec.md F1.6 | 明确常规熔断（非冷启动）是否改为 30s 或 1min |
| FIX16 | 补充任务描述路径错误说明 | 审查报告 | 任务描述说 `ui/rss/read/RssArticleInfoActivity.kt`，实际为 `ui/rss/search/RssArticleInfoActivity.kt`（文档正确，任务描述有误） |

---

## 八、输出安全声明

本审查报告所有 URL 已路径模式化（`/path/{id}`），所有域名已代号化（`站点A/B/C` 或 `***`），所有源名称已代号化（`源[N]`），所有 cookie/token 内容已隐藏为 `***`。报告仅输出技术结论（错误码/异常类型/调用栈/根因/修复方案/源码位置/行号）。

源码引用统一使用相对路径 + 行号格式（如 `Exo2MediaPlayer.kt 行 120-128`），不输出完整绝对路径中的业务信息。
