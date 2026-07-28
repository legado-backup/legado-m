# 任务清单：视频播放器嗅探失败 & 搜索聚合默认勾选修复

> **Spec ID**：video-search-sniff-fix-20260727
> **关联**：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)

---

## 一、任务分解

### Phase A：视频嗅探失败修复（问题一）

#### A1：修复 ExoFallback 错误 contentType 切换（P0）

- **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（fallback 逻辑实际所在文件，`ExoFallback.kt` 不存在）
- **任务**：
  - [ ] A1.1 Read `Exo2MediaPlayer.kt` 定位 fallback 列表构建逻辑（在 `prepareAsyncInternal` 及其内部回调中）
  - [ ] A1.2 修改 fallback 列表：保持相同 contentType，仅切换 DataSource 配置
  - [ ] A1.3 实现三种 DataSource 配置：Cronet 默认 / OkHttp + altReferer / Cronet + altUA
  - [ ] A1.4 增加 fallback 决策日志（reason + before/after contentType + dataSourceConfig）
  - [ ] A1.5 编译验证无报错
- **验收**：AC1.1, AC1.3
- **预估**：4 小时

#### A2：延长首次 BUFFERING 超时时间（P0）

- **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（BUFFERING 超时检测在同文件的 `bufferingTimeoutHandler` 行 120-128，硬编码 `postDelayed(12000L)`）+ `VideoPlay.kt`（新增 isFirstPlay 字段）
- **任务**：
  - [ ] A2.1 Read `Exo2MediaPlayer.kt` 行 120-128 定位 BUFFERING 超时阈值（硬编码 12000L，无常量）
  - [ ] A2.2 在 `VideoPlay.kt` 新增 `@Volatile var hasPlayedSuccessfully: Boolean = false` 字段（源码核实：当前无此字段）
  - [ ] A2.3 `VideoPlay.initSource`（行 665-719）入口处重置 `hasPlayedSuccessfully = false`（新源加载视为首次）
  - [ ] A2.4 `VideoPlay.startPlay` 首帧渲染成功回调（ExoPlayer onPlayerStateChanged state==READY）置 `hasPlayedSuccessfully = true`
  - [ ] A2.5 Exo2MediaPlayer 通过参数或接口获取 `isFirstPlay = !hasPlayedSuccessfully`，不直接访问 VideoPlay 字段
  - [ ] A2.6 修改超时阈值：`if (isFirstPlay) 25_000 else 12_000`
  - [ ] A2.7 增加超时触发日志（timeoutMs + isFirstPlay + urlPath 路径模式化）
  - [ ] A2.8 编译验证无报错
- **验收**：AC1.2
- **预估**：3 小时

#### A3：修复 FirstFramePreloader 缓存频繁清理（P1）

- **文件**：`app/src/main/java/io/legado/app/help/exoplayer/FirstFramePreloader.kt`（行 139 仅有 `clearCache()`，无 `delayedClearCache`）+ 3 处调用方（源码核实）：
  - `VideoPlay.kt:155`（onPause）— 改为延迟清理
  - `VideoPlayerActivity.kt:342`（onDestroy）— 保持立即清理
  - `VideoPlayService.kt:45`（onDestroy）— 保持立即清理
- **任务**：
  - [ ] A3.1 Read `FirstFramePreloader.kt` 行 30-42, 112-142 确认 `clearCache()` 当前实现（仅清理 preloadCache 时间戳映射，不清理 ExoPlayer SimpleCache 预加载数据）
  - [ ] A3.2 实现 `delayedClearCache(delayMs: Long = 30_000)` 方法（含 handler.removeCallbacksAndMessages 防重复）
  - [ ] A3.3 实现 `cancelDelayedClear()` 方法（Activity onResume 时取消延迟清理）
  - [ ] A3.4 修改 `VideoPlay.kt:155`（onPause）：`clearCache()` → `delayedClearCache()`
  - [ ] A3.5 新增 `VideoPlayerActivity` onResume 调用 `cancelDelayedClear()`
  - [ ] A3.6 `VideoPlayerActivity.kt:342`（onDestroy）+ `VideoPlayService.kt:45`（onDestroy）保持 `clearCache()` 不变（立即清理避免泄漏）
  - [ ] A3.7 缓存大小由源码常量限制（`MAX_CACHE_SIZE=10` 行 31 + `PRELOAD_BYTES=1048575`≈1MB 行 30，无需新增限制）
  - [ ] A3.8 增加缓存清理日志（trigger=onPause/onDestroy/manual + delayMs）
  - [ ] A3.9 编译验证无报错
- **验收**：AC3.2
- **预估**：3 小时

#### A4：DoH DNS 冷启动 30s 熔断（P1，已实现，仅验证）

- **文件**：`app/src/main/java/io/legado/app/help/http/DohDns.kt`
- **状态**：✅ 已实现（2026-07-27 交付），无需重复实施
- **源码核实**：
  - 行 79：`COLD_START_DISABLE_MS = 30_000L`
  - 行 111：`isColdStart` 标志位
  - 行 201-209：冷启动首次失败立即熔断 30s + 异步预热
  - 行 229-246：`asyncPreheatDoh()` 30s 后探测恢复
- **任务**（仅验证，不修改代码）：
  - [ ] A4.1 Phase C 真机测试时验证日志：`DohDns: cold start DoH failure, disable DoH 30s, async preheat`
  - [ ] A4.2 Phase C 真机测试时验证日志：`DohDns: asyncPreheat success/fail`
  - [ ] A4.3 Phase C 真机测试时验证行为：首个视频首帧延迟 < 25s
- **验收**：AC3.3
- **预估**：0 小时（仅验证）

#### A5：增加"首个视频"预热机制（P1）

- **文件**：`VideoPlay.kt` 或新增 `VideoPreloader.kt`
- **任务**：
  - [ ] A5.1 设计预热数据结构（url + 前 64KB 数据）
  - [ ] A5.2 实现用户点击视频列表项时异步预加载前 64KB
  - [ ] A5.3 预热数据缓存到 FirstFramePreloader
  - [ ] A5.4 实际播放时优先使用预热数据
  - [ ] A5.5 增加预热日志（url 路径模式化 + dataLen + cacheHit/miss）
  - [ ] A5.6 编译验证无报错
- **验收**：AC3.1
- **预估**：4 小时

#### A6：fallback 前 contentType 兼容性校验（P2）

- **文件**：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（与 A1 同文件）
- **任务**：
  - [ ] A6.1 实现流头部 magic bytes 读取（前 16 字节）
  - [ ] A6.2 实现 contentType 兼容性校验函数（`#EXTM3U` → HLS，`ftyp` → MP4）
  - [ ] A6.3 fallback 切换 contentType 前调用校验函数
  - [ ] A6.4 不匹配则跳过该 fallback 项，记录日志
  - [ ] A6.5 编译验证无报错
- **验收**：AC1.5
- **预估**：3 小时

---

### Phase B：搜索聚合默认勾选修复（问题二）

#### B1：统一默认选中源（P0，快速修复）

- **文件**：`app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt` 行 215
- **任务**：
  - [ ] B1.1 Read `RssArticleInfoActivity.kt` 行 200-230 确认上下文
  - [ ] B1.2 修改 `selectedOrigin` 赋值逻辑：`searchArticle?.origins?.firstOrNull() ?: articlesMap.keys.firstOrNull()`
  - [ ] B1.3 确认 `RssSearchSourceHolder.searchArticle` 可访问
  - [ ] B1.4 增加 `selectedOrigin =` 日志（origin 前 2 字符 + *** + source: origins/HashMap）
  - [ ] B1.5 编译验证无报错
- **验收**：AC2.1
- **预估**：1 小时

#### B2：switchToArticle 同步更新 source（P0，根本修复）

- **文件**：`app/src/main/java/io/legado/app/model/VideoPlay.kt` 行 967-992（switchToArticle）+ 行 152（source 字段定义，需加 @Volatile）
- **任务**：
  - [ ] B2.1 Read `VideoPlay.kt` 行 960-1000 确认上下文
  - [ ] B2.2 在 `switchToArticle` 的 `Coroutine.async` 块内增加 source 同步更新逻辑
  - [ ] B2.3 实现 source 匹配判断：`currentRssSource.sourceUrl != article.origin`
  - [ ] B2.4 不匹配时查询数据库：`val newSource = appDb.rssSourceDao.getByKey(article.origin)`
  - [ ] B2.5 **null 处理**：`newSource == null` 时输出 ERROR 日志 `AppLog.put("switchToArticle: source not found, origin=${article.origin.take(2)}***", isError = true)` 并 `return@async`（避免 startPlay 用 null source 崩溃）
  - [ ] B2.6 `source = newSource` 赋值
  - [ ] B2.7 增加 source 更新日志：`AppLog.put("switchToArticle: source 更新为 ${article.origin.take(2)}***")`
  - [ ] B2.8 **并发保护**：`VideoPlay.kt:152` source 字段加 `@Volatile` 注解（IO 线程写、Main 线程读的可见性保护，源码核实：当前无 @Volatile）
  - [ ] B2.9 确认 `source` 字段类型（BaseSource?）与 `RssSource` 兼容（RssSource 继承 BaseSource）
  - [ ] B2.10 确认 `appDb.rssSourceDao.getByKey` 返回类型（RssSource?）可赋值给 `BaseSource?`
  - [ ] B2.11 编译验证无报错
- **验收**：AC2.5
- **预估**：3 小时

#### B3：ReadRss.readRss 增加 source 兜底校验（P1，增强修复）

- **文件**：`app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` 行 58-104
- **任务**：
  - [ ] B3.1 Read `ReadRss.kt` 行 50-110 确认上下文
  - [ ] B3.2 修改 `indexOfFirst` 逻辑，保留 index = -1 而非 `?: 0` 兜底
  - [ ] B3.3 增加 WARN 日志：`ReadRss: source mismatch WARN, rssArticle.origin=***, rssArticles[0].origin=***`
  - [ ] B3.4 `rssArticleIndex` 兜底为 0（配合 B2 的 source 同步更新）
  - [ ] B3.5 编译验证无报错
- **验收**：AC3.4
- **预估**：1 小时

---

### Phase C：验证与打包

#### C1：编译与静态检查

- **任务**：
  - [ ] C1.1 全量编译 debug 包：`./gradlew assembleDebug`
  - [ ] C1.2 检查编译警告（特别是 source 类型转换相关）
  - [ ] C1.3 静态代码审查：确认所有修改点符合设计文档
  - [ ] C1.4 检查调试日志无残留：Grep `android.util.Log.d|android.util.Log.e` 确认无残留（按 output-safety.md 规范）

#### C2：真机测试 - 问题一（视频嗅探失败）

- **测试包**：`io.legado.miss.app.debug`（代码优化任务专用，按 AGENTS.md 真机测试包选择规范）
- **测试脚本**：`ai_tests/scripts/l2_verify_video_player.py`
- **任务**：
  - [ ] C2.1 使用 `quick_build_install.py` 编译安装 debug 包
  - [ ] C2.2 测试场景 A：浏览器可播放站点，内置播放首次成功率 ≥ 95%（5 个站点）
  - [ ] C2.3 测试场景 B：切换/下拉后第二个视频成功（保持不回归）
  - [ ] C2.4 日志检查 AC1.1：ExoFallback 不切换 contentType
  - [ ] C2.5 日志检查 AC1.2：首次 BUFFERING 超时 ≥ 25s
  - [ ] C2.6 日志检查 AC1.3：fallback 决策日志完整
  - [ ] C2.7 日志检查 AC1.5：不再出现 `ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED`
  - [ ] C2.8 日志检查 AC3.1：首次播放首帧延迟 < 25s
  - [ ] C2.9 日志检查 AC3.2：FirstFramePreloader 缓存延迟清理
  - [ ] C2.10 日志检查 AC3.3：DoH DNS 禁用时间 ≤ 30s

#### C3：真机测试 - 问题二（搜索聚合默认勾选）

- **测试包**：`io.legado.miss.app.debug`
- **任务**：
  - [ ] C3.1 测试场景 C：搜索聚合后默认点击"阅读"按钮，10 次全部成功（AC2.2）
  - [ ] C3.2 测试场景 D：搜索聚合后手动点击源列表第一项，5 次全部成功（AC2.3）
  - [ ] C3.3 测试场景 E：搜索聚合后手动点击源列表第 N 项（非第一个），5 次全部成功（AC2.3）
  - [ ] C3.4 测试场景 F：搜索聚合后点击"阅读"播放，上下滑动切换文章 5 次，全部成功（AC2.4）
  - [ ] C3.5 日志检查 AC2.1：默认选中源 = `searchArticle.origins.firstOrNull()`
  - [ ] C3.6 日志检查 AC2.5：switchToArticle 更新 source 日志输出
  - [ ] C3.7 日志检查 AC3.4：ReadRss source mismatch WARN 日志（场景 E）

#### C4：问题清单记录与回归测试

- **任务**：
  - [ ] C4.1 记录所有测试中发现的问题到 `issues-found.md`
  - [ ] C4.2 修复发现的问题
  - [ ] C4.3 回归测试：确认修复问题后不引入新问题
  - [ ] C4.4 全量 E2E 测试：`run_e2e.py --tc all`

#### C5：版本交付同步

- **任务**：
  - [ ] C5.1 用 `git diff` 分析真实代码变更
  - [ ] C5.2 更新 `assets/updateLog.md`（基于代码分析，非文字合并）
  - [ ] C5.3 逐文件审计：对照变更文件列表确认每个变更都有对应日志条目
  - [ ] C5.4 更新 `docs/INDEX.md`（如需）
  - [ ] C5.5 更新项目记忆 `project_memory.md`

---

## 二、检查点

### 检查点 1：Phase A 完成后（问题一修复完成）

- **触发条件**：A1, A2 完成（P0 项）
- **检查项**：
  - [ ] ExoFallback 修改是否符合 design.md 设计
  - [ ] BUFFERING 超时逻辑是否正确（首次 25s，后续 12s）
  - [ ] 编译是否通过
- **决策**：通过 → 进入 Phase B / 需调整 → 修订后重新确认 / 拒绝 → 回退

### 检查点 2：Phase B 完成后（问题二修复完成）

- **触发条件**：B1, B2 完成（P0 项）
- **检查项**：
  - [ ] RssArticleInfoActivity 默认选中源修改是否正确
  - [ ] VideoPlay.switchToArticle source 同步更新是否正确
  - [ ] 编译是否通过
- **决策**：通过 → 进入 Phase C / 需调整 → 修订后重新确认 / 拒绝 → 回退

### 检查点 3：Phase C 完成后（验证与打包完成）

- **触发条件**：C1-C5 完成
- **检查项**：
  - [ ] 所有 P0 验收标准通过
  - [ ] 所有 P1 验收标准通过（或已记录问题清单）
  - [ ] updateLog.md 已更新
  - [ ] 问题清单已记录
- **决策**：通过 → 任务完成 / 需调整 → 修订后重新确认 / 拒绝 → 回退

---

## 三、依赖关系

```
Phase A（问题一）           Phase B（问题二）
  ├─ A1: ExoFallback          ├─ B1: 默认选中源（独立）
  ├─ A2: BUFFERING 超时       ├─ B2: switchToArticle source（独立）
  ├─ A3: 缓存延迟清理         └─ B3: ReadRss 兜底（依赖 B2）
  ├─ A4: DoH DNS（仅验证）
  ├─ A5: 预热机制（依赖 A3）
  └─ A6: contentType 校验
        │
        └──→ Phase C（验证与打包）
              ├─ C1: 编译
              ├─ C2: 真机测试问题一
              ├─ C3: 真机测试问题二
              ├─ C4: 问题清单
              └─ C5: 版本交付
```

**依赖说明**：
- Phase A 与 Phase B **相互独立**，可并行实施
- B3 依赖 B2（ReadRss 兜底校验依赖 switchToArticle source 同步更新）
- **A5 依赖 A3**（预热机制复用 FirstFramePreloader.preloadUrl，A3 修改 FirstFramePreloader，必须先完成 A3）
- Phase C 依赖 Phase A + Phase B 全部完成
- C2 与 C3 可并行测试（不同场景）

---

## 四、风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| R1：ExoFallback.kt 实际结构与 design.md 假设不一致 | 实施延期 | A1.1 先 Read 源码确认结构，如不一致则更新 design.md |
| R2：source 字段类型与 RssSource 不兼容 | 编译失败 | B2.6/B2.7 先确认类型兼容性 |
| R3：真机测试环境无法复现"第一个视频必失败" | 验收无法通过 | 使用日志中记录的站点（路径模式化）测试；如无法复现则基于日志分析验收 |
| R4：DoH DNS 模块路径未确认 | A4 实施延期 | A4.1 先 Grep `DohDns` 定位模块路径 |
| R5：预热机制引入内存泄漏 | OOM 风险 | A3.5 限制缓存大小；A3.6 onDestroy 立即清理 |
| R6：source 更新影响 source 相关的其他逻辑 | 播放链路异常 | B2 实施后全量回归测试（C4） |

---

## 五、反模式

| 反模式 | 说明 | 正确做法 |
|--------|------|----------|
| AP1：未 Read 源码直接修改 | 实际结构与假设不符导致编译失败 | 每个 Task 第一步先 Read 源码确认上下文 |
| AP2：修改 Rss.getContentAwait 核心逻辑 | 违反非目标 NG1 | 仅修改 RssArticleInfoActivity 和 VideoPlay.switchToArticle |
| AP3：改变 rssArticles 列表语义 | 违反非目标 NG4 | 不插入用户选的源的文章到列表头 |
| AP4：升级 jsoup/rhino/hutool 依赖 | 违反非目标 NG9 | 仅应用层逻辑修复 |
| AP5：用文字总结代替 AskUserQuestion 验收 | 违反 AGENTS.md 强制规则 | 每个检查点必须用 AskUserQuestion 三选项结构 |
| AP6：日志输出完整 URL/域名/源名称 | 违反 output-safety.md | 路径模式化 + 代号化 + 前 2 字符 + *** |
| AP7：跳过真机测试直接交付 | 违反 AGENTS.md 强制规则 | 必须用 debug 包真机测试（C2/C3） |
| AP8：只改代码不更新 updateLog.md | 违反 version-delivery-sync.md | C5 必须基于 git diff 更新 updateLog.md |
| AP9：调试日志残留 | 违反 logging-during-refactoring.md | C1.4 Grep 确认无 `android.util.Log.d/e` 残留 |
| AP10：用正式包测试代码优化 | 违反真机测试包选择规范 | 必须用 `io.legado.miss.app.debug` 测试包 |

---

## 六、输出安全声明

本文档所有 URL 已路径模式化（`/path/{id}`），所有域名已代号化（`站点A/B/C` 或 `***`），所有源名称已代号化（`源[N]`），所有 cookie/token 内容已隐藏为 `***`。文档仅输出技术结论（错误码/异常类型/调用栈/根因/修复方案）。
