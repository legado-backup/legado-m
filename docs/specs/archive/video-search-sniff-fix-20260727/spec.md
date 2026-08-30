# 功能规范：视频播放器嗅探失败 & 搜索聚合默认勾选修复

> **Spec ID**：video-search-sniff-fix-20260727
> **关联**：[README.md](./README.md) | [design.md](./design.md) | [tasks.md](./tasks.md)

---

## 一、功能规范

### 1.1 问题一：视频嗅探失败修复

#### 功能描述

修复内置视频播放器在部分站点（浏览器可播放）必然失败的问题，确保嗅探成功的视频流能够正确加载与播放。

#### 功能要求

| 编号 | 要求 | 优先级 |
|------|------|--------|
| F1.1 | ExoFallback 在 BUFFERING 超时后不得切换到不兼容的 contentType，必须保持嗅探识别的 contentType。sniff 返回 UNKNOWN（TYPE_UNKNOWN=-1）时保留现有 URL 后缀启发式逻辑（`buildFallbackTypes` 行 198-217 的 UNKNOWN 分支，按 URL 后缀启发式排序） | P0 |
| F1.2 | fallback 列表仅切换 DataSource 配置（Referer/UA/超时/DataSource 类型），不切换 contentType | P0 |
| F1.3 | 首次 BUFFERING 超时阈值提升至 25s（CDN 冷启动场景），后续 BUFFERING 保持 12s。**isFirstPlay 字段重置时机**：VideoPlay.initSource 时重置为 true，startPlay 首帧渲染成功后置 false。需在 VideoPlay 新增 `@Volatile var hasPlayedSuccessfully: Boolean = false` 字段（源码核实：当前 VideoPlay 无此字段） | P0 |
| F1.4 | fallback 决策必须输出完整日志：触发原因、前后 contentType、DataSource 配置变更 | P0 |
| F1.5 | FirstFramePreloader 缓存清理需延迟 30s，避免 Activity onPause/onStop 时立即清理 | P1 |
| F1.6 | DoH DNS 冷启动场景禁用时间 30s（✅ 已实现，`DohDns.kt` 行 79 `COLD_START_DISABLE_MS=30_000L`）；常规熔断场景（非冷启动，连续 3 次失败）禁用时间保持 5min（`DISABLE_DURATION_MS=5*60*1000L`）；冷启动 30s 后异步预热 DoH（`asyncPreheatDoh` 行 229-246）。**本任务仅验证冷启动 30s，不修改常规熔断时间**（源码核实：冷启动 30s 已实现） | P1 |
| F1.7 | 用户点击视频列表项时，预热视频流前 64KB（足够识别 moov 头） | P1 |
| F1.8 | fallback 前增加 contentType 兼容性校验（magic bytes 比对） | P2 |
| F1.9 | 同 contentType 重试机制：BUFFERING 超时后先重试同 contentType 1-2 次（不同 Referer/UA），仍失败再考虑切换 | P2 |

#### 用户场景

**场景 A：浏览器能播但内置嗅探失败（第一个视频必失败）**

- **前置条件**：用户首次打开应用，CDN 冷启动，DoH DNS 不可达
- **操作**：用户搜索视频 → 点击搜索结果 → 内置播放器尝试播放
- **预期（修复后）**：
  - 首次 BUFFERING 超时阈值 25s，覆盖 CDN 冷启动延迟
  - 即使 BUFFERING 超时，ExoFallback 保持原 contentType，仅切换 DataSource 配置
  - 视频流解析器与流格式匹配，不再抛出 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED`
  - 播放成功，或经过同 contentType 重试后成功
- **预期（修复前）**：BUFFERING 12s 超时 → fallback 切换 contentType → 解析器不匹配 → 播放失败

**场景 B：切换/下拉后第二个视频可成功**

- **前置条件**：第一个视频失败后，CDN 已缓存首帧，DoH 已禁用并回退系统 DNS
- **操作**：用户下拉或切换到下一个视频
- **预期（修复后）**：首帧 < 12s，不触发超时，保持原 contentType，播放成功
- **预期（修复前）**：同样成功（此场景本就正常）

---

### 1.2 问题二：搜索聚合默认勾选修复

#### 功能描述

修复订阅源搜索聚合后，点击"阅读"按钮必然播放失败的问题，确保默认选中源与 `rssArticles[0]` 一致，且 `switchToArticle` 同步更新 `source` 字段。

#### 功能要求

| 编号 | 要求 | 优先级 |
|------|------|--------|
| F2.1 | `RssArticleInfoActivity` 默认选中源必须使用 `searchArticle.origins.firstOrNull()`（LinkedHashSet 顺序），不得使用 `HashMap.keys.firstOrNull()` | P0 |
| F2.2 | `VideoPlay.switchToArticle(index)` 加载 `rssArticles[index]` 时，必须同步更新 `source` 字段为 `article.origin` 对应的源。**source 字段必须加 `@Volatile` 注解**（源码核实：`VideoPlay.kt:152` `var source: BaseSource?` 当前无 @Volatile，switchToArticle 在 IO 线程写、startPlay 在 Main 线程读，存在可见性风险）。**`appDb.rssSourceDao.getByKey(article.origin)` 返回 null 时输出 ERROR 日志并 return false**（避免 startPlay 用 null source 崩溃） | P0 |
| F2.3 | `switchToArticle` 更新 source 时必须输出日志（前 2 字符 + ***） | P0 |
| F2.4 | `ReadRss.readRss` 增加 source 兜底校验：当 `rssArticle` 不在 `rssArticles` 中时，记录 WARN 日志但不改变列表语义 | P1 |
| F2.5 | 用户主动选择非第一个源时，`switchToArticle` 仍能正确加载该源的文章（source 同步更新） | P0 |

#### 用户场景

**场景 C：搜索聚合后默认点击"阅读"按钮必失败**

- **前置条件**：订阅源顶部搜索关键字，多个源返回相同视频被聚合显示
- **操作**：用户点击聚合项 → 详情页 → 点击"阅读"按钮（不手动选源）
- **预期（修复后）**：
  - 默认选中源 = `origins.firstOrNull()`（与 `rssArticles[0]` 一致）
  - `source` 字段 = 默认选中源
  - `switchToArticle(0)` 加载 `rssArticles[0]`，`source` 与 `rssArticle` 匹配
  - `ruleContent` 解析成功，播放成功
- **预期（修复前）**：默认选中源 = `HashMap.keys.firstOrNull()`（可能与 origins[0] 不一致）→ source 与 rssArticle 不匹配 → 解析失败 → 播放失败

**场景 D：搜索聚合后用户手动点击源列表第一项可成功**

- **前置条件**：同场景 C
- **操作**：用户点击聚合项 → 详情页 → 手动点击源列表第一项 → 点击"阅读"按钮
- **预期（修复后）**：选中源 = origins[0]，source 同步更新，播放成功
- **预期（修复前）**：同样成功（此场景本就正常）

**场景 E：搜索聚合后用户手动点击源列表第 N 项（非第一个）**

- **前置条件**：同场景 C
- **操作**：用户点击聚合项 → 详情页 → 手动点击源列表第 N 项 → 点击"阅读"按钮
- **预期（修复后）**：
  - 选中源 = origins[N]
  - `ReadRss.readRss` 传递 `rssArticle`（origins[N] 的文章）
  - `VideoPlay.rssArticleIndex` = 0（`indexOfFirst` 找不到，兜底为 0）
  - `switchToArticle(0)` 加载 `rssArticles[0]`（origins[0] 的文章），但 `source` 同步更新为 origins[0] 对应的源
  - 播放成功（但播放的是 origins[0] 的文章，而非用户选的 origins[N] 的文章）
- **预期（修复前）**：source 仍为 origins[N]，与 rssArticles[0] 不匹配 → 播放失败
- **说明**：此场景修复后虽能播放，但播放的文章可能与用户选择不一致（因 `rssArticleIndex` 兜底为 0）。完整修复需配合 F2.4 兜底校验，但本期不改变 `rssArticles` 列表语义。

**场景 F：搜索聚合后点击"阅读"按钮播放，上下滑动切换文章**

- **前置条件**：同场景 C
- **操作**：用户点击聚合项 → 详情页 → 点击"阅读"按钮 → 播放成功后上下滑动切换文章
- **预期（修复后）**：每次切换文章，`switchToArticle` 同步更新 `source` 为新文章的源，每篇文章都能正确加载对应源
- **预期（修复前）**：切换文章后 `source` 不更新，与 `rssArticles[index]` 不匹配 → 播放失败

---

## 二、验收标准

### 2.1 P0 验收标准（必须通过）

#### 问题一：视频嗅探失败

| 编号 | 验收项 | 验证方法 | 通过标准 |
|------|--------|----------|----------|
| AC1.1 | ExoFallback 不切换 contentType | 日志检查 `ExoFallback: try contentType=` 序列 | fallback 全程 contentType 保持不变（如始终为 2 或始终为 4） |
| AC1.2 | 首次 BUFFERING 超时阈值 25s | 日志检查 `BUFFERING timeout` 触发时间 | 首次 BUFFERING 超时时间 ≥ 25s，后续 ≥ 12s |
| AC1.3 | fallback 决策日志完整 | 日志检查 `ExoFallback:` 关键字 | 包含：触发原因、前后 contentType、DataSource 配置变更 |
| AC1.4 | 浏览器可播放站点内置播放成功 | 真机测试 5 个浏览器可播放的站点 | 首次播放成功率 ≥ 95%（至少 5/5 成功） |
| AC1.5 | 不再出现错误 contentType 切换导致的解析失败 | 日志检查 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED` / `ERROR_CODE_PARSING_MANIFEST_MALFORMED` | 出现次数为 0（修复前 30 次） |

#### 问题二：搜索聚合默认勾选

| 编号 | 验收项 | 验证方法 | 通过标准 |
|------|--------|----------|----------|
| AC2.1 | 默认选中源与 rssArticles[0] 一致 | 源码审查 + 日志检查 | `selectedOrigin` = `searchArticle.origins.firstOrNull()`，与 `rssArticles[0].origin` 一致 |
| AC2.2 | 默认点击"阅读"按钮播放成功 | 真机测试搜索聚合场景 10 次 | 10/10 成功播放 |
| AC2.3 | 手动点击源列表任意一项播放成功 | 真机测试点击第 1/2/3 项各 5 次 | 15/15 成功播放 |
| AC2.4 | 上下滑动切换文章播放成功 | 真机测试切换 5 次文章 | 5/5 成功加载对应源 |
| AC2.5 | switchToArticle 更新 source 日志 | 日志检查 `switchToArticle: source 更新为` | 每次切换文章都输出日志（前 2 字符 + ***） |

### 2.2 P1 验收标准（应通过）

| 编号 | 验收项 | 验证方法 | 通过标准 |
|------|--------|----------|----------|
| AC3.1 | 首次播放首帧延迟 < 25s | 日志检查 `ExoPlayer first frame rendered: latency=` | 首次播放首帧延迟 < 25s |
| AC3.2 | FirstFramePreloader 缓存延迟清理 | 日志检查 `FirstFramePreloader: cache cleared` 触发时机 | Activity onPause 后 30s 才清理，而非立即清理 |
| AC3.3 | DoH DNS 禁用时间缩短 | 日志检查 `disable DoH` 关键字 | 禁用时间 ≤ 30s（原 5min） |
| AC3.4 | ReadRss.readRss source 兜底校验 | 日志检查 `ReadRss: source mismatch WARN` | 用户选的源不在 rssArticles 中时输出 WARN 日志 |

---

## 三、非目标

本期修复**不包含**以下内容，避免范围蔓延：

| 编号 | 非目标项 | 原因 |
|------|----------|------|
| NG1 | 不修改 `Rss.getContentAwait` 核心逻辑 | RSS 内容解析逻辑独立，不在本期范围 |
| NG2 | 不修改 `RssSearchModel.mergeItems` 聚合规则 | 聚合规则本身正确，问题在于默认选中与 source 同步 |
| NG3 | 不修改 `SearchRssArticle` 数据结构（origins/originArticles 类型） | 改动数据结构影响面过大，通过使用方修复更安全 |
| NG4 | 不改变 `rssArticles` 列表语义（不插入用户选的源的文章到列表头） | 避免影响上下滑动切换文章的体验 |
| NG5 | 不修改 R5 网络抓包嗅探的核心逻辑 | R5 嗅探独立模块，问题根因在 ExoFallback 而非 R5 |
| NG6 | 不修改视频型订阅源正文为空（T4.4）的降级逻辑 | T4.4 降级逻辑正确，问题根因在 ExoFallback |
| NG7 | 不修改 cookie 为 null 的获取逻辑 | cookie 问题间接影响，非本期核心根因 |
| NG8 | 不修改图片防盗链/URL 拼接 bug | 图片问题与视频播放无关 |
| NG9 | 不升级 jsoup/rhino/hutool 依赖版本 | 依赖锁定，破坏性变更风险高 |
| NG10 | 不修改 ExoPlayer/Cronet 版本 | 版本升级风险高，本期通过应用层逻辑修复 |

---

## 四、用户场景汇总

| 场景 | 描述 | 修复前 | 修复后 |
|------|------|--------|--------|
| A | 浏览器能播但内置嗅探失败（第一个视频） | 必失败 | 成功（≥95%） |
| B | 切换/下拉后第二个视频 | 成功 | 成功（保持） |
| C | 搜索聚合后默认点击"阅读"按钮 | 必失败 | 成功（100%） |
| D | 搜索聚合后手动点击源列表第一项 | 成功 | 成功（保持） |
| E | 搜索聚合后手动点击源列表第 N 项 | 必失败 | 成功（100%，但播放 origins[0] 的文章） |
| F | 搜索聚合后点击"阅读"播放，上下滑动切换文章 | 切换后失败 | 成功（每次切换同步 source） |

---

## 五、输出安全声明

本文档所有 URL 已路径模式化（`/path/{id}`），所有域名已代号化（`站点A/B/C` 或 `***`），所有源名称已代号化（`源[N]`），所有 cookie/token 内容已隐藏为 `***`。文档仅输出技术结论（错误码/异常类型/调用栈/根因/修复方案）。
