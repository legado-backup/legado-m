# 需求规格 - 书源线程池拆分与自定义配置

> 修订：v2（2026-07-26）按审查报告 P0+P1 修复方案更新

## Intent（意图）

用户希望能够针对书源的"搜索"与"更新+缓存"两类业务场景，分别配置独立的线程池并发数，从而：

1. 在不同业务场景下独立调优并发数（例如搜索可用高并发 32，更新+缓存可用低并发 16 减少 CPU/内存压力）
2. 避免一类业务的高并发占用影响另一类业务的执行
3. 让用户能够根据手机性能和实际使用偏好自定义每个场景的线程数
4. 通过合理上限保护避免用户误配置导致 OOM 崩溃

## Scope（范围）

### In Scope（本次实现）

- 在 `AppConfig` 中新增 `searchThreadCount` 和 `updateCacheThreadCount` 两个独立配置项（含 `coerceIn` 上限兜底）
- 在"其他设置"中新增两个独立的线程数配置入口（带 NumberPickerDialog，搜索上限 128 / 更新+缓存上限 64）
- 兼容字段 `threadCount` 在 UI 中**默认隐藏**（仅备份/恢复时保留）
- 将 30+ 处使用 `threadCount` 的业务点按场景归类替换为对应的新配置
- 配置变更后通过 LiveEventBus 实时通知业务层重建线程池（含 Toast 提示）
- 老用户升级时通过**独立迁移标志位**触发一次性迁移（附 Toast 提示）
- 同步更新 `BackupConfig` 新增两个独立 ignore 字段
- 编写单元测试覆盖迁移/读写/备份恢复逻辑
- 编写 E2E 测试脚本覆盖 UI/配置变更/真机日志验证

### Out of Scope（不在本次实现）

- 不重构现有的 `Coroutine.async` 链式封装
- 不引入新的 DI 框架或线程池统一管理类
- 不调整 `Dispatchers.IO` / `Dispatchers.Default` / `Dispatchers.Main` 的使用
- 不修改 `AppConst.MAX_THREAD` 常量（保留作为部分场景的安全上限）
- 不改造 `globalExecutor`（单线程全局 Executor）和 `DispatchersMonitor`
- 不涉及书源/RSS 源校验的业务逻辑改造（仅替换线程数参数来源）
- 不做性能测试和压力测试（P2 项）

## Approach（方案）

### Selected Approach（选定方案）

**配置拆分 + 业务归类映射 + 事件总线通知 + 上限保护 + 标志位迁移**

1. **配置拆分**：在 `PreferKey.kt` 新增两个 key，在 `AppConfig.kt` 新增两个 var 属性，默认值分别取 32（搜索）和 16（更新+缓存）；setter 中加 `coerceIn(1, 上限)` 兜底保护
2. **业务归类映射**：根据业务语义将 30+ 处使用点归类到搜索类或更新+缓存类，逐处替换参数来源
3. **UI 自定义**：在 `pref_config_other.xml` 新增两个 `Preference` 项；旧 `threadCount` Preference **默认隐藏**（`app:isPreferenceVisible="false"`）；NumberPickerDialog 上限搜索 128 / 更新+缓存 64；summary 中列出影响范围；配置变更后 Toast 提示生效时机
4. **事件总线通知**：在 `MainActivity.kt` 新增 `observeEvent` 监听两个新 key，在 `MainViewModel.kt` 中分别重建对应的线程池
5. **兼容性**：保留 `threadCount` 字段并标记 `@Deprecated(level = WARNING)`，proguard 保留字段防止混淆；备份/恢复时同时包含三个字段，新增 `ignoreSearchThreadCount` 和 `ignoreUpdateCacheThreadCount` 独立 ignore 字段
6. **老用户迁移**：使用独立标志位 `pref_migrated_thread_count`（boolean）作为唯一判断条件——首次启动时若标志位不存在则迁移（无论 threadCount 是何值，都将其赋给两个新配置），迁移后写入 true；迁移后首次进入"其他设置"页 Toast 提示

**选定理由**：
- 改动局部、风险可控：仅替换参数来源，不改造协程架构
- 兼容现有 `Coroutine.async` 链式封装和 `ExecutorCoroutineDispatcher` 模式
- 用户体验直观：两个独立配置项 + 影响范围说明 + Toast 提示
- 上限保护：避免用户误配置 OOM
- 标志位迁移：健壮、可重复执行安全
- 兼容老用户：旧 `threadCount` 配置值不丢失，自动迁移到新配置

### Alternatives Considered（备选方案）

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| A. 统一 ThreadPoolManager 集中管理 | 创建一个 `ThreadPoolManager` object 单例，集中管理搜索池和更新+缓存池，所有业务点改为从该单例获取 Dispatcher | 改动面过大（涉及 30+ 处调用点改造为单例调用），与现有"各业务点自行创建 ExecutorCoroutineDispatcher"的模式不一致；现有模式中线程池生命周期与业务点绑定（如 SearchModel.close 会主动 close searchPool），改为单例后生命周期管理复杂；收益不明显（核心需求仅是配置拆分而非架构重构） |
| B. 保持现状仅拆分配置 | 仅在 `AppConfig` 新增两个配置项，但所有业务点继续使用 `min(threadCount, MAX_THREAD)` 公式（即不真正拆分业务使用点） | 不满足用户需求——用户明确要求"搜索的就是单独的搜索线程池，更新和缓存线程是另外一个单独的线程池"，仅拆分配置不拆分业务使用点等于没拆 |
| C. 完全分离搜索/更新/缓存三个池 | 拆分为三个独立配置：searchThreadCount、updateThreadCount、cacheThreadCount | 用户明确要求"更新和缓存线程是另外一个单独的线程池"——即将更新和缓存归为同一池；强行拆为三个违背用户意图；增加配置复杂度（用户需配置 3 个参数） |
| D. 使用 Dispatchers.IO + Semaphore 控制并发 | 不创建独立线程池，所有业务点统一使用 `Dispatchers.IO`，通过 `Semaphore(searchThreadCount)` 和 `Semaphore(updateCacheThreadCount)` 分别控制并发数 | `Dispatchers.IO` 默认最大并发 64，无法真正限制实际线程数；Semaphore 仅控制同时进入临界区的协程数，不限制底层线程数；用户配 32 时若 Dispatchers.IO 实际只有 64 线程，搜索+缓存同时进行时会相互影响，违背"独立线程池"的隔离意图 |
| E. 无上限完全尊重用户配置 | 去掉所有上限保护，用户配多少实际用多少（与 SearchModel 既有反馈完全一致） | 用户误输入 999 时每个线程约 1MB 栈空间，999 线程 ≈ 1GB 直接 OOM 崩溃；用户体验不可预期；改为保留合理上限 128/64 既满足"配多少用多少"的语义又防 OOM |

### Drawbacks（已知缺点）

1. **配置项数量增加**：从 1 个变为 2 个（外加 1 个隐藏的兼容字段），用户首次设置时需理解两个配置的区别
   - **接受理由**：通过 UI 中清晰的标题、影响范围说明和 Toast 提示可缓解；用户长期收益（独立调优）大于短期学习成本

2. **业务点改动面广**：涉及 18+ 个文件的参数来源替换
   - **接受理由**：每处改动局部且机械（仅替换 `AppConfig.threadCount` 为 `AppConfig.searchThreadCount` 或 `AppConfig.updateCacheThreadCount`），回归风险低；通过逐文件验证、单元测试和真机回归测试可保障质量

3. **保留旧 `threadCount` 兼容字段带来的认知负担**：开发者可能误用旧字段
   - **接受理由**：通过 `@Deprecated(level = WARNING)` 注解和文档说明可缓解；UI 中默认隐藏避免用户误操作；保留兼容字段是为了支持备份/恢复和老用户迁移，删除会破坏向后兼容

4. **上限保护与"完全尊重用户配置"的语义冲突**：保留 128/64 上限可能限制高性能手机用户
   - **接受理由**：128/64 已远超现有 SearchModel 反馈中的 32 配置；如用户确实需要更高值，可在未来版本中调整上限或提供"高级模式"开关

### Prior Art（参考）

- `SearchModel.kt` L44-60：已有"去掉 MAX_THREAD 硬上限，完全尊重用户配置"的设计先例（本次保留 128/64 上限是对该先例的优化）
- `RssSearchModel.kt` L95-110：同上先例在 RSS 搜索场景的复用
- `MainViewModel.kt` L82-92：已有 threadCount 变更后重建 upTocPool 的事件监听机制

## Requirements（需求）

### R1: 配置层新增

- **R1.1** 在 `PreferKey.kt` 新增 `searchThreadCount = "searchThreadCount"` 和 `updateCacheThreadCount = "updateCacheThreadCount"` 两个常量
- **R1.2** 在 `AppConfig.kt` 新增 `searchThreadCount: Int`（默认 32）和 `updateCacheThreadCount: Int`（默认 16）两个 var 属性
- **R1.3** 保留旧 `threadCount` 字段并标记 `@Deprecated("Use searchThreadCount or updateCacheThreadCount instead", level = DeprecationLevel.WARNING)`（保留可读写用于备份兼容）
- **R1.4** 在 `BackupConfig.kt` 的备份项列表中新增两个新 key；新增 `ignoreSearchThreadCount` 和 `ignoreUpdateCacheThreadCount` 两个独立 ignore 字段（与 `ignoreThreadCount` 解耦）
- **R1.5** `searchThreadCount` setter 加 `coerceIn(1, 128)` 兜底保护；`updateCacheThreadCount` setter 加 `coerceIn(1, 64)` 兜底保护
- **R1.6** 在 `app/proguard-rules.pro` 中保留 `threadCount` 字段防止 R8 混淆导致反射读取失败

### R2: UI 层新增

- **R2.1** 在 `pref_config_other.xml` 新增两个 `Preference` 项（标题/summary/key 完整）
- **R2.2** 在 `strings.xml` 新增两个配置项的标题、说明、summary 模板字符串（summary 包含影响范围说明，如"控制书源/RSS 搜索、换源换封面、书源校验等场景的并发数，当前: %s"）
- **R2.3** 在 `OtherConfigFragment.kt` 的 `onCreatePreferences` 中初始化两个新项的 summary
- **R2.4** 在 `OtherConfigFragment.kt` 的 `onPreferenceTreeClick` 中新增两个 `NumberPickerDialog` 处理：搜索类范围 1-128，更新+缓存类范围 1-64
- **R2.5** 在 `OtherConfigFragment.kt` 的 `onSharedPreferenceChanged` 中新增两个 key 的 summary 更新、postEvent 调用和 Toast 提示（搜索类提示"配置已保存，将在下次搜索时生效"，更新+缓存类提示"配置已立即生效"）
- **R2.6** 在 `OtherConfigFragment.kt` 的 `upPreferenceSummary` 中新增两个 key 的 summary 格式化
- **R2.7** 旧 `threadCount` 配置项在 UI 中**默认隐藏**（`app:isPreferenceVisible="false"`），仅备份/恢复时保留 Preference 定义
- **R2.8** 老用户迁移后首次进入"其他设置"页时弹 Toast 提示"已根据您之前的线程数配置自动迁移为搜索/更新+缓存两个独立配置"

### R3: 业务层归类替换

- **R3.1** 搜索类业务（11 个文件）替换为 `searchThreadCount`：
  - `SearchModel.kt` L33/L59/L99
  - `RssSearchModel.kt` L52/L108/L149/L158
  - `ChangeBookSourceViewModel.kt` L62/L168/L237/L386（+ 去掉 `min(..., MAX_THREAD)`）
  - `ChangeCoverViewModel.kt` L40/L102/L159（+ 去掉 `min(..., MAX_THREAD)`）
  - `ReadMangaViewModel.kt` L173
  - `ReadBookViewModel.kt` L322
  - `BookshelfViewModel.kt` L181
  - `MainViewModel.kt` L150（发现页探索，添加注释说明"归搜索类"）
  - `CheckSourceService.kt` L62/L64/L126（+ 去掉 `min(..., MAX_THREAD)`）
  - `CheckRssSourceService.kt` L62/L64/L126（+ 去掉 `min(..., MAX_THREAD)`）
  - `JsExtensions.kt` L129/L148
- **R3.2** 更新+缓存类业务（7 个文件）替换为 `updateCacheThreadCount`：
  - `MainViewModel.kt` L52/L53/L82/L86/L92（upTocPool 更新目录，添加注释说明"归更新+缓存类"）
  - `CacheBookService.kt` L44/L46（+ 去掉 `min(..., MAX_THREAD)`）
  - `CacheBook.kt` L148
  - `BookHelp.kt` L216
  - `BookChapterList.kt` L103
  - `BookContent.kt` L109
  - `WebViewPool.kt` L44（`max(AppConfig.threadCount / 10, 5)` → `max(AppConfig.updateCacheThreadCount / 10, 5)`）

### R4: 配置变更监听

- **R4.1** 在 `MainActivity.kt` 新增 `observeEvent(PreferKey.searchThreadCount)` 和 `observeEvent(PreferKey.updateCacheThreadCount)` 监听
- **R4.2** 在 `MainViewModel.kt` 中分别处理两个事件：搜索事件 → 仅记录日志（SearchModel 下次搜索自动重建），更新事件 → 立即重建 upTocPool
- **R4.3** **时序竞态说明**：配置变更后正在执行的业务不受影响（继续使用旧池），下次业务启动时使用新配置——这是现有 SearchModel 的行为，本次改造保持一致

### R5: 兼容性保障（标志位迁移）

- **R5.1** 老用户迁移使用独立标志位 `pref_migrated_thread_count`（boolean）作为唯一判断条件：
  - 首次启动时若标志位不存在（即首次升级到新版本），无论 `threadCount` 是何值，都将其同时赋给 `searchThreadCount` 和 `updateCacheThreadCount`
  - 迁移完成后写入 `pref_migrated_thread_count = true` 避免重复执行
  - 若 `threadCount` 仍为默认值 32（即用户从未修改过），迁移后两个新配置也保持默认值（32/16），不强制覆盖
- **R5.2** 备份恢复时：若备份文件只有旧 `threadCount`（旧版本备份），恢复后触发一次性迁移（同 R5.1）；若备份文件包含三个字段，按各自值恢复
- **R5.3** 老用户迁移后首次进入"其他设置"页时 Toast 提示（仅一次）

### R6: 文档同步

- **R6.1** 同步更新 `docs/project-flow/architecture/overview.md` 中线程池相关章节
- **R6.2** 同步更新 `docs/project-flow/quick-reference.md` 中配置项速查表
- **R6.3** 更新 `assets/updateLog.md` 记录本次变更（基于 git diff 分析）

### R7: 测试覆盖

- **R7.1** 单元测试：覆盖 `migrateThreadCountConfig()` 迁移逻辑（未迁移/已迁移/部分迁移/异常容错）
- **R7.2** 单元测试：覆盖 `AppConfig.searchThreadCount` 和 `updateCacheThreadCount` 读写（含 coerceIn 边界）
- **R7.3** 单元测试：覆盖 `BackupConfig` 备份恢复包含三个字段
- **R7.4** E2E 脚本：在 `ai_tests/scripts/` 新增 `verify_thread_pool_split.py`，覆盖 UI 验证 + 配置变更 + 真机日志验证
- **R7.5** 真机回归测试：30+ 业务点替换后每个业务点至少 1 个最小验证场景（详见 tasks.md 第 8 节）

## Scenarios（场景）

### Scenario 1: 老用户升级（已配置 threadCount=16）

1. 用户当前版本 threadCount=16
2. 升级到新版本，App 首次启动
3. 检测 `pref_migrated_thread_count` 标志位不存在 → 触发迁移
4. 将 threadCount=16 同时赋给 searchThreadCount 和 updateCacheThreadCount
5. 写入 `pref_migrated_thread_count = true`
6. 用户进入"其他设置"页 → Toast 提示"已根据您之前的线程数配置自动迁移为搜索/更新+缓存两个独立配置"
7. 用户看到两个配置项：搜索线程数=16、更新和缓存线程数=16（兼容字段隐藏）

### Scenario 2: 新用户首次配置

1. 用户安装新版本
2. App 首次启动，`pref_migrated_thread_count` 标志位不存在但 threadCount=32（默认值），不强制覆盖新配置默认值
3. 写入 `pref_migrated_thread_count = true`
4. 进入"其他设置"，看到"搜索线程数=32"、"更新和缓存线程数=16"
5. summary 显示影响范围说明
6. 点击"搜索线程数" → NumberPickerDialog（1-128，当前值 32）→ 调整为 48
7. Toast 提示"配置已保存，将在下次搜索时生效"
8. summary 实时更新为"控制书源/RSS 搜索、换源换封面、书源校验等场景的并发数，当前: 48"
9. 下次书源搜索时使用 48 个线程并发，同时进行中的缓存下载仍使用 16 个线程

### Scenario 3: 搜索与缓存并行不互相影响

1. 用户触发书源搜索（搜索线程数=48）
2. 同时启动书籍缓存下载（更新和缓存线程数=8）
3. 搜索使用独立的 searchPool（48 线程），缓存使用独立的 cachePool（8 线程）
4. 两个线程池互不干扰，CPU 调度由系统决定
5. 搜索完成后 searchPool 自动 close（SearchModel.close），缓存继续进行

### Scenario 4: 配置变更实时生效

1. 用户在搜索过程中修改"搜索线程数" 32 → 64
2. LiveEventBus 发送 `PreferKey.searchThreadCount` 事件
3. Toast 提示"配置已保存，将在下次搜索时生效"
4. MainViewModel 收到事件 → 记录日志
5. 当前搜索任务继续使用旧 searchPool（32 线程）完成
6. 下次搜索时 SearchModel.initSearchPool 重读 `AppConfig.searchThreadCount`，创建 64 线程的 searchPool

### Scenario 5: RSS 源搜索与书源搜索共用配置

1. 用户配置"搜索线程数=24"
2. 触发书源搜索 → SearchModel 使用 24 线程
3. 触发 RSS 源搜索 → RssSearchModel 使用 24 线程
4. 两类搜索共用同一个配置项，符合"搜索类业务统一"的设计

### Scenario 6: 备份与恢复

1. 用户在设备 A 配置：搜索线程数=48、更新和缓存线程数=8
2. 执行备份 → 备份文件包含 searchThreadCount=48、updateCacheThreadCount=8、threadCount=48（兼容字段）
3. 在设备 B 恢复 → 三个字段按各自值恢复
4. 设备 B 的搜索使用 48 线程，更新+缓存使用 8 线程

### Scenario 7: 用户配置过大触发上限保护

1. 用户尝试通过 NumberPickerDialog 将"搜索线程数"调到 200
2. NumberPickerDialog 最大值限制为 128，用户无法选 200
3. 即使用户通过 ADB 等方式直接写入 SharedPreferences 200，AppConfig.searchThreadCount setter 中 `coerceIn(1, 128)` 兜底返回 128
4. 实际生效的搜索线程数为 128，不会 OOM

### Scenario 8: 迁移标志位机制

1. 用户首次升级到新版本
2. App 启动时检查 `pref_migrated_thread_count` 标志位 → 不存在
3. 执行迁移：将 threadCount 值赋给两个新配置（若 threadCount=32 默认值则保持新配置默认值 32/16）
4. 写入 `pref_migrated_thread_count = true`
5. 后续每次启动检查标志位 → 已存在 → 跳过迁移
6. 即使用户在升级后又改了 threadCount，也不会再触发迁移（避免覆盖用户新配置）

### Scenario 9: 备份恢复触发迁移（旧版本备份文件）

1. 用户在旧版本备份配置（备份文件只有 threadCount=24）
2. 升级到新版本后恢复备份
3. 恢复后 `pref_migrated_thread_count` 标志位被清除（或不存在）
4. 触发迁移：将 threadCount=24 赋给 searchThreadCount 和 updateCacheThreadCount
5. 写入 `pref_migrated_thread_count = true`
6. Toast 提示已迁移
