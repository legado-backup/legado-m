# legados Forks Comparison & Integration

## Intent

分析 GEd520/legados fork（来自 Gitee）与本项目之间的差异，基于逐文件源码深度阅读而非文件名推测，识别值得集成的功能特性，并设计集成方案。目标是通过有策略地吸收 fork 的优秀设计，提升本项目的用户体验、稳定性和可维护性，同时避免引入不必要的复杂度和风险。

## Scope

### IN SCOPE

- 分析 legados fork 与本项目的代码差异，梳理 fork 独有的功能模块
- **逐文件深度阅读** fork 源码，理解每个候选功能的真实实现（而非仅凭文件名推断）
- 按价值/风险评估对差异项进行分级，识别集成候选
- 为每个集成候选设计完整集成方案（代码移植方式、UI 入口、依赖链、适配点、测试方法）
- 制定优先级排期和集成路线图

### OUT OF SCOPE

- 实际修改源代码（本任务为纯设计阶段，不涉及代码变更）
- 与其他 fork（Archive 等）的对比分析（已有 `forks-archive-comparison`）
- 数据库迁移设计
- 集成后的真机测试（属于后续实施阶段的任务）

## Approach

### Selected Approach

**分层集成策略**：基于源码深度阅读后的真实价值/风险评估对 fork 独有功能进行分级，高价值低风险功能优先集成，中价值中风险功能计划集成，低价值或需深度改造的功能仅记录暂不集成。

核心原则：
- **源码验证优先**：所有集成候选必须经过源码逐行阅读验证，不得仅凭文件名推断功能
- **最小侵入**：优先移植独立类，减少对现有代码的修改
- **依赖链完整**：移植前分析完整依赖，确保不遗漏配套修改
- **风格适配**：移植代码需符合本项目编码规范（Coroutine 链式封装、runCatching 错误处理、AppLog 日志等）
- **增量验证**：每个集成项独立可测试，不批量堆积

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 全量集成 | 把 fork 所有独有功能全部迁移 | 部分功能价值低（liquidglass UI 库增加体积、DictDebugConfig 仅调试用、JsCacheManager 只是调试包装层）；维护成本高；两个项目演进方向不同 |
| 仅凭文件名推断移植 | 不读源码，直接按文件名推测功能并移植 | 已被证明会导致严重误判（JsCacheManager/BubblePackageManager/BackupFileValidator 三项判断均错误）；功能理解偏差会导致集成方向错误 |
| 基于 fork 重构 | 直接以 legados 为基础重新 fork | fork 的代码质量和维护活跃度不如本项目；本项目有大量独有功能（Highlight、CoverGallery、RSS增强、AudioSkipCredits）对方没有；AudioPlay.kt 差异147行需逐行适配 |
| 仅参考设计思路 | 不移植代码，仅参考设计理念自行实现 | 实现周期长；对大功能（StorageCalculator 782行、BackupFileValidator 597行）直接移植更高效 |

### Drawbacks

1. 部分移植可能导致依赖链不完整（如 BackupFileValidator 依赖 fork 的 BackupConfig 221行版本，而本项目是 147行版本，字段差异需要适配）
2. fork 的代码风格可能与本项目不一致（如 AudioPlay.kt fork 635行 vs 本项目 488行，需要逐行对比后选择性合并而非整体替换）
3. 不引入 liquidglass 等第三方库意味着缺少视觉增强，用户界面无玻璃效果
4. 不同步 fork 的后续更新，需要自行维护移植代码
5. AudioPlay.kt 的差异合并是高风险操作（147行差异涉及歌词回调、状态管理等核心逻辑），可能引入运行时不一致
6. MemoryPressure 需要为 PaintPool 新增 `clear()` 方法（当前 ObjectPool 接口只有 obtain/recycle/create，无清理方法），属于对现有接口的扩展
7. UrlRecordInterceptor 对普通用户无感知价值，仅服务高级用户/源开发者群体

### Prior Art

本项目已有 `forks-archive-comparison` 和 `forks-archive-borrow-implementation` 的类似对比流程和规范，可复用以下经验：
- 差异分析的子代理并行扫描方法
- 集成候选的价值/风险评估框架
- 依赖链分析流程
- 代码移植后的适配检查清单
- **教训**：文件名推断会导致误判，必须逐文件读源码验证

## Requirements

### P0 - 高价值低风险（立即集成，7项）

> 经产品/架构/测试三维度审查后调整：UrlRecordInterceptor 从 P0 降至 P1（主要服务高级用户/源开发者，普通用户无感知价值）

| # | 功能 | 源码行数 | 集成价值（源码验证） | 风险评估 | 本项目是否有替代 | UI 入口 |
|---|------|---------|-------------------|---------|---------------|--------|
| 1 | HelpDoc + HelpDocManager | 68+68=136行 | 从 assets 加载 Markdown 文件并在对话框展示，支持显隐切换。用户无需联网即可查看功能说明 | 低：独立模块，无外部依赖 | 无 | 在 AboutActivity 或 MainFragment 中添加"帮助文档"入口按钮，点击后打开 HelpDocActivity |
| 2 | MemoryPressure | 90行 | 基于 `onTrimMemory`，提供 `maxMemory`/`availableMemory`/`isSmallHeap` 属性和 `trimIfNeeded`/`trimNow` 方法。减少 OOM 崩溃 | 低+微调：独立工具类 + 需为 PaintPool 新增 clear() 方法 | 无（AppFreezeMonitor 功能不同） | 无 UI 入口（后台自动运行），日志可在 DebugFloatBallManager 中查看 |
| 3 | InnerBrowserUrlSpan + InnerBrowserLinkResolver | 24+24=48行 | 基于 `AppConfig.mdLinkInnerBrowser` 设置决定链接在应用内/外部浏览器打开，使用 Markwon 链接解析（本项目已有 Markwon 依赖） | 低：URLSpan 替换 | 无 | 在 SettingsActivity → 阅读设置中添加"Markdown 链接使用内置浏览器"开关 |
| 4 | BackupFileValidator | 597行 | 验证 JSON/XML 格式正确性，检查必需字段，处理加密服务器配置文件。防止恢复损坏备份导致数据丢失 | 低：独立验证工具 | 无（Restore.kt 无验证逻辑） | 在 RestoreActivity 恢复流程中自动触发；验证失败弹出 AlertDialog 提示具体原因，按钮：[取消恢复] [查看详情] |
| 5 | BackupInfoHelper | 324行 | 统计备份数据概况和分类信息，无需解析 ZIP。增强用户对备份内容的了解 | 低：独立信息展示 | 无 | 在 BackupActivity 备份前展示备份概况信息卡片（书源数、订阅源数等） |
| 6 | StorageCalculator | 782行 | 计算 6 种缓存大小（书籍/EPUB/临时/TTS/ACache/数据库/日志），提供详情列表和清理操作 | 低：纯工具类 | 无 | 在 SettingsActivity → 其他设置中添加"存储管理"入口，点击后打开 StorageManageActivity |
| 7 | SpecialContentProtector | 41行 | 用正则替换 HTML 标签和特殊标记，防止 HTML 解析破坏特殊内容 | 低：独立工具类 | 部分（ContentProcessor 有类似但不专门保护 HTML 标签） | 无 UI 入口（后台自动运行，集成到 ContentProcessor 处理管线） |

### P1 - 中价值中风险（5项，含从P0降级的UrlRecordInterceptor）

| # | 功能 | 源码行数 | 集成价值 | 风险评估 | 本项目是否有替代 | UI 入口 |
|---|------|---------|---------|---------|---------------|--------|
| 8 | UrlRecordInterceptor | 201行 | OkHttp Interceptor 记录请求 URL/域名/HTTP 方法/响应状态/耗时。主要服务高级用户/源开发者调试书源 | 低+性能：可插拔 Interceptor + 需评估性能开销 | 无 | 在 SettingsActivity → 开发者选项中添加"URL 记录"开关，日志在 AppLog 中查看 |
| 9 | CoverHtmlTemplateConfig | 189行 | HTML 封面模板 CRUD + 默认模板 + 持久化 | 中：需与 BookCover 集成 | 无 | 在 SettingsActivity → 封面设置中添加"模板管理"入口 |
| 10 | BackupConfig 差异合并 | 221行 vs 147行 | fork 版本多出 bookCacheKey 和 ignoreBookCache 属性，注释更完整 | 中：需对比字段差异 | 有（但功能更少） | 在备份恢复设置页面添加"书籍缓存备份"开关 |
| 11 | BubblePackageManager | 287行 | 段评/内容评注气泡包的导入导出和应用管理 | 中：需理解段评机制 | 无 | 在段评设置页面添加"气泡包管理"入口 |
| 12 | AudioPlay.kt 差异合并 | fork 635行 vs 488行（差147行） | fork 多出歌词回调、更多状态管理 | 高：核心模块差异大 | 有但功能少 | 无新入口，需逐行合并 |

### P2 - 低价值或需深度改造（仅记录，暂不集成）

| # | 功能 | 暂不集成原因 |
|---|------|-------------|
| 13 | JsCacheManager（244行） | 只是 CacheManager 的 JS 调试包装层，无编译缓存功能，本项目已有 CacheManager |
| 14 | liquidglass | 玻璃效果 UI 库，增加 APK 体积且本项目已有主题系统 |
| 15 | DictDebugConfig | 仅调试用，不面向最终用户 |
| 16 | ApplicationThemeManager（566行） | 主题包管理，本项目已有 ThemeConfig（557行），功能重叠度高 |
| 17 | NavigationBarConfig + TopBarConfig | UI 配置，与本项目布局系统差异大 |
| 18 | ReadAloudActivity（169行）/ ReadAloudHelper（214行） | 朗读功能，本项目已有 AudioPlayActivity 替代 |

### 内部链接定义规则（InnerBrowserLink）

"内部链接"的判定逻辑：
1. URL 的 host 部分与当前书源的 `bookSourceUrl` 的 host 相同 → 内部链接
2. URL 以 `http://` 或 `https://` 开头且属于已知书源域名 → 内部链接
3. URL 以 `file:///` 或 `content://` 开头（本地资源）→ 内部链接
4. 以上条件都不满足 → 外部链接（交由系统浏览器）
5. 用户可通过 `AppConfig.mdLinkInnerBrowser` 开关禁用内部浏览器功能（默认启用）

### BackupConfig 字段差异清单

| 差异项 | fork（221行） | 本项目（147行） | 集成建议 |
|--------|-------------|---------------|---------|
| `bookCacheKey = "bookCache"` | 有 | 无 | 合并：书籍缓存备份是有价值的功能 |
| `ignoreBookCache` 属性 | 有 | 无 | 合并：配套 bookCacheKey |
| `getString(R.string.book_cache)` | 有 | 无 | 合并：需要新增 strings.xml 条目 |
| 注释/Javadoc | 完整分区注释 | 简洁无注释 | 参考：改进本项目 BackupConfig 注释但不整体替换 |
| `ignoreKeys` 数组 | 包含 bookCacheKey（9项） | 8项 | 合并：新增 bookCacheKey 项 |
| `ignoreTitle` 数组 | 包含 book_cache（9项） | 8项 | 合并：新增 book_cache 项 |
| `keyIsNotIgnore` 方法 | 使用 if-return 风格 | 使用 when 表达式 | 保留本项目风格（when 更 Kotlinic） |

## Scenarios

### Scenario 1: HelpDoc 查看
- **Given**: 用户在阅读设置中找不到某功能说明（如书源规则语法）
- **When**: 用户在 AboutActivity 点击"帮助文档"按钮
- **Expected**: 打开 HelpDocActivity，左侧显示文档列表（书源制作教程/js变量和函数/订阅源规则帮助等），右侧显示 Markdown 渲染内容；点击切换列表中的其他文档可快速跳转

### Scenario 2: MemoryPressure 响应
- **Given**: 设备内存紧张（低内存设备或长时间使用后），应用占用 150MB+
- **When**: 系统发出 `onTrimMemory` 回调（level ≥ TRIM_MEMORY_RUNNING_LOW=10）
- **Expected**: `MemoryPressure.trimIfNeeded()` 自动释放：CacheManager.memoryLruCache.evictAll()（50MB缓存全清）+ PaintPool.clear()（8个Paint对象回收）；AppLog.put() 记录"MemoryPressure: level=X, released CacheManager+PaintPool"；应用不崩溃

### Scenario 3: BackupFileValidator 验证成功
- **Given**: 用户从正常备份文件恢复数据
- **When**: 在 RestoreActivity 选择备份文件后
- **Expected**: BackupFileValidator.validate() 通过（JSON 格式正确、必需字段齐全），正常进入恢复流程

### Scenario 4: BackupFileValidator 验证失败
- **Given**: 用户从损坏备份文件恢复数据
- **When**: 在 RestoreActivity 选择备份文件后
- **Expected**: BackupFileValidator.validate() 失败，弹出 AlertDialog：标题"备份文件验证失败"，内容"原因：JSON 格式错误/缺少必需字段(bookSources)/加密配置无法解密"，按钮[取消恢复][查看详情（展开完整验证报告）]

### Scenario 5: BackupInfoHelper 展示
- **Given**: 用户准备备份数据
- **When**: 在 BackupActivity 点击备份前
- **Expected**: 在备份按钮上方展示信息卡片："本次将备份：书源(XX个)、订阅源(XX个)、替换规则(XX条)、阅读配置、主题配置等"；用户确认后再执行备份

### Scenario 6: InnerBrowserLink 内部跳转
- **Given**: 阅读内容中包含链接，且用户启用了 `AppConfig.mdLinkInnerBrowser`（默认启用）
- **When**: 用户点击内容中的链接
- **Expected**: InnerBrowserLinkResolver 判定链接 host 与书源 host 相同 → 在应用内 WebView Activity 打开，阅读体验不中断；按返回键回到阅读页

### Scenario 7: InnerBrowserLink 外部跳转
- **Given**: 阅读内容中包含外部链接（host 与书源不同）
- **When**: 用户点击该链接
- **Expected**: InnerBrowserLinkResolver 判定为外部链接 → Intent.ACTION_VIEW 交由系统浏览器打开

### Scenario 8: StorageCalculator 使用
- **Given**: 用户想了解应用占用了多少存储空间
- **When**: 在 SettingsActivity → 其他设置 → "存储管理"入口点击
- **Expected**: 打开 StorageManageActivity，显示 6 种缓存类型的详情列表（名称+大小+路径），底部有"一键清理"按钮；点击某项可单独清理

### Scenario 9: UrlRecordInterceptor 调试（P1）
- **Given**: 高级用户/源开发者调试某书源的网络请求
- **When**: 在 SettingsActivity → 开发者选项启用"URL 记录"开关后发起请求
- **Expected**: UrlRecordInterceptor 在 AppLog 中记录完整请求链路（URL/域名/方法/状态/耗时/POST body），开发者可通过 DebugFloatBallManager 或 logcat 查看
