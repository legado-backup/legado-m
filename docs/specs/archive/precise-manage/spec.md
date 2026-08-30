# 精准管理（Precise Manage）规格说明

> **Spec ID**：precise-manage
> **生成时间**：2026-08-07
> **状态**：✅ 已实施
> **参考实现**：Legado_Max fork 的 precise_manage 聚合菜单（Compose 体系）
> **本项目路线**：View 体系重写（项目无 Compose 基础设施），数据层复用参考源设计

---

## 1. Intent（意图）

借鉴 Legado_Max fork 的「精准管理」聚合菜单，在「我的」页新增统一入口，将四类零散/缺失的管理能力聚合到一处：

1. **网址记录（UrlRecord）**：目前项目没有任何请求历史可视化能力，源开发者与高级用户排查书源问题时只能靠网络日志翻找。新增全局 OkHttp 拦截器采集请求元数据（URL/域名/方法/状态码/耗时/来源名/请求体≤1000 字符/错误），落库新表 `url_records`（Migration 102→103），提供搜索、筛选、按日期分组、详情对话框与批量清除。
2. **存储管理（StorageManage）**：项目已有 CacheActivity/CacheManageViewModel 分项统计能力，但仅覆盖书籍/视频/音频三项，未覆盖临时/Epub/TTS/ACache/数据库/日志/WebView 等缓存，且入口藏在书详情页。聚合页将 8 类缓存统一展示与清理，复用现成 API。
3. **下载管理（DownloadManage）**：项目现有 DownloadService 基于系统 DownloadManager 下载，任务存内存 `downloads`/`completeDownloads` 但**无任何列表界面**，用户无法查看进度、暂停、重试或定位已下载文件。新增列表页补全该闭环。
4. **文件管理（FileManage）**：直接复用现有 FileManageActivity，零成本纳入聚合。

核心价值：把「请求排查」「空间清理」「下载追踪」三类高频操作从分散入口收敛为「我的页 → 精准管理」一步可达，且全部用本项目 View 体系落地，不引入 Compose。

## 2. Scope（范围）

### 2.1 In Scope（包含）

| # | 范围 | 说明 |
|---|------|------|
| 1 | 网址记录（UrlRecord）全新功能 | 全局 OkHttp 拦截器采集 + Room 新表 `url_records`（Migration 102→103）+ View 列表页（搜索/筛选/日期分组/详情/批量清除/采集开关） |
| 2 | 存储管理（StorageManage）聚合统计页 | 分类缓存大小展示 + 单项/展开逐项/一键清理 + 打开路径 |
| 3 | 下载管理（DownloadManage）列表页 | Tab 分类 + 暂停/继续/重试/打开文件/打开文件夹/复制路径/删除/清除已完成 |
| 4 | 我的页入口 + 聚合页 | `pref_main.xml` 加「精准管理」入口 → 聚合页（`ConfigTag.PRECISE_MANAGE` + ConfigActivity 分支 + PreciseManageFragment） |
| 5 | 文件管理复用 | 直接复用现有 FileManageActivity，不新增实现 |

### 2.2 Out of Scope（明确不做）

| # | 排除项 | 否决理由 |
|---|--------|---------|
| 1 | 引入 Compose UI | 项目无 Compose 基础设施，统一 View 体系 |
| 2 | WebView 层 URL 采集 | 仅 OkHttp 拦截器，与参考源一致；改 12 处 WebViewClient 成本高且收益低 |
| 3 | 设置 X-Source-Name / X-Source-Url 请求头 | 本项目请求方不设该头，来源名 v1 留空，可后续增强 |
| 4 | URL 记录单条删除 | 参考源也只有批量清除 |
| 5 | 下载任务 Room 持久化 | 复杂度高，参考源同样未做（内存单例，进程重启丢失） |
| 6 | 新增底部导航 Tab | 入口放我的页，不改变主界面导航结构 |
| 7 | DebugEventCenter 网络调试事件联动 | 项目无该事件中心，不引入参考源联动 |

## 3. Approach（方案）

### 3.1 Selected Approach（选定方案）

**View 体系重写 + 数据层复用参考源设计 + 内存单例下载状态 + 聚合页导航模式**，分四层落地：

```mermaid
flowchart TD
    subgraph Entry["入口层"]
        E[我的页 pref_main.xml<br/>「其他」分组新增精准管理] --> H[ConfigActivity<br/>configTag=PRECISE_MANAGE]
        H --> F[PreciseManageFragment<br/>聚合页]
    end

    subgraph UrlLayer["网址记录（全新）"]
        I[UrlRecordInterceptor<br/>OkHttp 全局拦截器<br/>挂 DecompressInterceptor 之后] --> R[(Room url_records<br/>Migration 102→103)]
        R --> UA[UrlRecordActivity<br/>搜索/筛选/日期分组/详情/批量清除]
        S[AppConfig.recordUrl 开关<br/>PreferKey 新键] -.控制采集.-> I
    end

    subgraph StorageLayer["存储管理"]
        V[StorageManageViewModel<br/>复用 directorySize/formatBytes] --> SA[StorageManageActivity<br/>8 类缓存 + 展开/单项/一键清理 + 打开路径]
        V -.复用.-> CM[CacheManageViewModel<br/>buildStorageBreakdown]
        V -.复用.-> BH[BookHelp.clearCache / clearCache(book)]
        V -.复用.-> CV[ConfigViewModel.clearCache / clearWebViewData]
    end

    subgraph DownloadLayer["下载管理"]
        DS[DownloadState 内存单例<br/>StateFlow&lt;List&lt;DownloadTask&gt;&gt;] --> DA[DownloadManageActivity<br/>5 Tab + 任务操作]
        DS -.500ms 轮询同步.-> DM[系统 DownloadManager]
        DM -.任务来源.-> SV[现有 DownloadService<br/>downloads / completeDownloads]
    end

    F --> UA
    F --> SA
    F --> DA
    F --> FM[FileManageActivity<br/>直接复用现有实现]

    style UA fill:#e8f0fe
    style SA fill:#e8f0fe
    style DA fill:#e8f0fe
```

**关键决策点**：

1. **数据层照搬参考源设计，改写为本项目风格**：`UrlRecord` 实体（`@Entity` + `@Parcelize` + 字段全默认值）与 `UrlRecordDao` 双套 API（`flow*` 响应式 + 一次性 `get*`），拦截器逻辑复用参考源「startTime + try/catch/finally + scope.launch{insert}」结构，但请求体采集限制 ≤1000 字符。
2. **拦截器挂载点**：`HttpHelper.kt` L190 `builder.addInterceptor(DecompressInterceptor)` 之后新增 `UrlRecordInterceptor`（L195 StreamResetRetryInterceptor 之前），保证解压后链上能拿到真实响应。
3. **采集开关**：仿 `AppConfig.enableReadRecord` 模式新增 `AppConfig.recordUrl`（`getPrefBoolean(PreferKey.recordUrl, true)` + `putPrefBoolean`），关闭时拦截器直接 `proceed()` 零开销。
4. **DB 迁移**：`AppDatabase.kt` version 102→103，`DatabaseMigrations.kt` migrations 数组追加 `migration_102_103`，完全仿 `migration_101_102` 模板（`kotlin.runCatching { CREATE TABLE IF NOT EXISTS + CREATE INDEX + AppLog.put }`），索引对齐实体 `indices=[timestamp, domain]`。
5. **下载管理数据源**：仿参考源 `DownloadState` 内存单例（`StateFlow<List<DownloadTask>>`），500ms 轮询系统 `DownloadManager`（`DownloadManager.Query().setFilterById`）同步状态到 StateFlow，列表页 StateFlow 驱动刷新。任务来源沿用现有 `DownloadService` 的 `downloads`/`completeDownloads` 内存集合。
6. **聚合页导航模式**：复用项目现有 ConfigActivity 分发模式（新增 `ConfigTag.PRECISE_MANAGE` 常量 + `when(configTag)` 分支 + `PreciseManageFragment`），我的页 `onPreferenceTreeClick` 跳转表新增入口；`pref_main.xml`「其他」PreferenceCategory 内新增 `Preference`（`iconSpaceReserved=false`，同 bookmark/fileManage 风格）。
7. **存储统计复用优先**：聚合页内展开书籍/Epub 等分类时，复用 `CacheManageViewModel.buildStorageBreakdown()` 与 `internal directorySize/formatBytes`（扩展为 8 类时新增私有包装，不破坏现有 CacheActivity 调用方），清理复用 `BookHelp.clearCache()` / `ConfigViewModel.clearCache()` / `clearWebViewData()`。

### 3.2 Alternatives Considered（备选方案）

| # | 方案 | 否决理由 |
|---|------|---------|
| A | Compose 重写（照搬参考源 precise_manage UI） | 本项目无 Compose 基础设施（无相关依赖、无 Compose 组件库、无 Compose 页面先例），引入需同时改造构建配置/主题/列表体系，成本与回归面远超收益；View 体系已有 BaseActivity/RecyclerAdapter/DiffUtil 全套能力，功能等价可实现 |
| B | 只做入口聚合，不实现三页面 | 入口指向空聚合页无实际价值，网址记录/下载列表是本功能核心增量，砍掉后等同"无功能空壳"，用户无感知 |
| C | URL 采集走 WebView 层（WebViewClient 拦截） | 项目有 12 处 WebViewClient 需逐个埋点，覆盖不全（OkHttp 直连请求不经过 WebView）；参考源同样只用 OkHttp 拦截器；采集完整性与成本双重不利 |
| D | 下载任务 Room 持久化 | 需新增实体/Dao/迁移 + 与系统 DownloadManager 状态双写一致性处理，复杂度高；参考源未做（进程重启丢失是其已知局限），本项目跟随该取舍 |
| E | 来源名走自定义请求头增强（X-Source-Name/X-Source-Url） | 本项目请求方当前不设这两个请求头，v1 落地后来源名恒为空；需改 WebBook/HttpHelper 多处请求构造才有效，收益后置，留待 v2 增强 |

### 3.3 Drawbacks（已知缺点）

| # | 缺点 | 接受理由 |
|---|------|---------|
| 1 | 下载任务进程重启后丢失 | 与参考源一致的内存单例取舍；本项目下载本体走系统 DownloadManager，系统侧记录仍在，任务列表仅展示层丢失，风险可接受 |
| 2 | 来源名（sourceName）v1 为空 | 请求方不设 X-Source-Name 头，字段空置；表结构与 Dao（`flowBySourceName`/`getAllSourceNames`）已预留，v2 增强即可生效 |
| 3 | OkHttp 拦截器只覆盖 HTTP 客户端请求，不覆盖 WebView 请求 | 与参考源一致；WebView 请求采集需改 12 处 WebViewClient，已明确 Out of Scope |
| 4 | DB 迁移风险（102→103 新增表） | 采用 `CREATE TABLE IF NOT EXISTS` + `kotlin.runCatching` + `AppLog.put` 模板，仿已上线稳定的 migration_101_102；失败仅影响网址记录功能，不影响既有表；schema 同步更新至 `app/schemas/` 且经覆盖安装回归 |
| 5 | 拦截器存在采集性能开销 | 开关默认关闭后直接 `proceed()` 零开销；开启时仅字符串截取 + 异步 insert（scope.launch），不阻塞请求线程 |

### 3.4 Prior Art（既有先例）

1. **参考源 Legado_Max**：`UrlRecord` 实体（`url_records` 表，`indices=[timestamp,domain]`）、`UrlRecordDao`（flow 系列 + 一次性查询 + `onConflict=REPLACE` + `deleteOldRecords`）、`UrlRecordInterceptor`（全局拦截器 + `recordUrl` 开关 + 错误分级 + `sanitizeUrl`）、`StorageManage`（8 类缓存 + 展开清理）、`DownloadManage`（5 Tab + 内存单例 `DownloadState` + 500ms 轮询）、`pref_precise_manage.xml`（4 导航项）。本 spec 的数据模型/Dao 签名/状态机/缓存分类全部对齐参考源，仅 UI 层改为 View 体系。
2. **本项目 CacheActivity/CacheManageViewModel**：`buildStorageBreakdown(): Coroutine<List<CacheStorageDetail>>`（书籍/视频/音频三项）+ `internal directorySize/formatBytes` + `deleteStorageTarget`，为 StorageManage 的 8 类扩展提供可复用计算与清理基建。
3. **本项目 ConfigActivity + ConfigTag 导航模式**：`when(configTag)` 5 分支分发 Fragment，精准管理聚合页复用该模式新增第 6 分支，符合既有「我的页 → 配置页 → Fragment」导航惯例。
4. **本项目 DownloadService**：`downloads = hashMapOf<Long, DownloadInfo>` + `completeDownloads = hashSetOf<Long>` + 系统 DownloadManager 轮询（现有 `checkDownloadState` 已 1000ms 轮询），DownloadManage 数据源可直接对接。

## 4. Requirements（需求）

### 4.1 聚合入口（Aggregation）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-01 | 「我的」页「其他」分组新增「精准管理」入口 Preference（`iconSpaceReserved=false`） | - [ ] `pref_main.xml`「其他」分组出现该入口，title/summary 文案来自 `strings.xml` |
| FR-02 | 点击入口跳转 ConfigActivity，`configTag=ConfigTag.PRECISE_MANAGE` | - [ ] `ConfigTag.kt` 新增 `PRECISE_MANAGE` 常量；`ConfigActivity.onActivityCreated` 新增分支；MyFragment 跳转表新增 key 分支 |
| FR-03 | 聚合页展示 4 个导航项：网址记录 / 存储管理 / 下载管理 / 文件管理 | - [ ] PreciseManageFragment 4 项均可见可点击，分别跳转对应 Activity/复用 FileManageActivity |

### 4.2 网址记录（UrlRecord）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-10 | 新增 `UrlRecord` 实体，`@Entity(tableName="url_records")`，`indices=[timestamp, domain]`，字段含 id(PK autoGenerate)/url/domain/method/sourceName?/sourceUrl?/timestamp/responseCode/duration/requestBody?/errorMsg?，全部有默认值 | - [ ] 实体文件存在，`@Parcelize` 生效，字段默认值完整 |
| FR-11 | 新增 `UrlRecordDao`，含 flow 系列（flowAll/flowSearch/flowByDomain/flowBySourceName/flowByMethod/flowByStatus/flowFilter）+ 一次性（getAll/getByDomain/getBySourceName/search/getCount/getOldRecordsCount/getCountSince）+ 写删（insert vararg onConflict=REPLACE/delete(id)/deleteAll():Int/deleteOldRecords(timestamp):Int） | - [ ] Dao 接口方法齐全，`@Insert(onConflict=REPLACE)` 与 `@Query` 注解正确，编译通过 |
| FR-12 | 新增 Migration 102→103 创建 `url_records` 表 + timestamp/domain 索引，模板仿 migration_101_102 | - [ ] `AppDatabase.kt` version=103；`DatabaseMigrations.kt` migrations 数组追加 `migration_102_103`；`app/schemas/` 含 103 版 schema |
| FR-13 | 新增 `UrlRecordInterceptor`（OkHttp Interceptor），`recordUrl` 关闭时直接 `chain.proceed()` 零开销 | - [ ] 关闭开关后无任何 insert 行为 |
| FR-14 | 拦截器 finally 中采集 url/domain/method/requestBody(≤1000字符)/responseCode/duration，错误场景采集 errorMsg，`scope.launch{insert}` 异步入库 | - [ ] 开启开关后发起一次请求，数据库出现对应记录；请求体超 1000 字符被截断 |
| FR-15 | 错误分级：errorMsg→ERROR / 4xx→WARN / 5xx→ERROR / 其余→INFO；URL 经 `sanitizeUrl` 脱敏 | - [ ] 4xx/5xx/网络异常分别落入对应级别；脱敏逻辑对查询串等敏感部分生效 |
| FR-16 | `AppConfig.recordUrl` 采集开关（`PreferKey.recordUrl`，默认 true） | - [ ] `AppConfig.kt` 新增 `recordUrl` 属性，读写 SharedPreferences 与现有 boolean 模式一致 |
| FR-17 | `UrlRecordActivity` 列表页：Room `flow*` 驱动 DiffUtil 刷新，支持关键字搜索、域名/来源/方法/状态多条件筛选 | - [ ] 搜索/筛选后列表实时变化，filter 组合正确 |
| FR-18 | 列表按日期分组展示（按 timestamp 归组） | - [ ] 同一天记录归为一组，分组标题显示日期 |
| FR-19 | 点击单条弹出详情对话框（完整 URL/方法/状态码/耗时/请求体/错误信息） | - [ ] 详情对话框字段完整展示 |
| FR-20 | 批量清除：7 天 / 30 天 / 全部三档（`deleteOldRecords(timestamp)` / `deleteAll()`），清除前二次确认 | - [ ] 三档清除后对应记录消失，计数正确；有确认弹窗 |

### 4.3 存储管理（StorageManage）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-30 | 聚合页展示 8 类缓存占用：BOOK_CACHE/EPUB_CACHE/TEMP_CACHE/TTS_CACHE/ACACHE_DISK/DB_CACHE/LOG_CACHE/WEBVIEW_CACHE，大小复用 `directorySize` 计算 | - [ ] 8 类均显示大小，路径映射正确（externalFiles/cacheDir/getDatabasePath/getDir） |
| FR-31 | 单项清理（不可展开分类直接清该项） | - [ ] 单项清理后大小归零或刷新，结果提示释放空间 |
| FR-32 | 可展开分类（书籍按本 / TTS 按引擎 / ACache 按前缀 / DB 按前缀 / WebView 按目录）支持逐项清理 | - [ ] 展开后子项可单独清理，子项大小合计=父项大小（误差内） |
| FR-33 | 一键清理全部缓存 | - [ ] 一键清理后所有分类大小归零；视频类在播放中时加锁拒绝（复用现有 isVideoPlaying 逻辑） |
| FR-34 | 每项提供「打开路径」操作 | - [ ] 点击打开对应目录（FileManageActivity 或系统文件选择器定位） |

### 4.4 下载管理（DownloadManage）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-40 | `DownloadTask` 数据模型 + 任务状态枚举 PENDING/RUNNING/PAUSED/SUCCESSFUL/FAILED | - [ ] 枚举与模型存在，状态字段正确 |
| FR-41 | `DownloadState` 内存单例持有 `StateFlow<List<DownloadTask>>`，500ms 轮询系统 DownloadManager 同步状态 | - [ ] 开启下载后 ≤1s 内列表出现任务，进度/状态随轮询更新 |
| FR-42 | `DownloadManageActivity` 5 Tab：全部 / 下载中 / 已暂停 / 已完成 / 失败 | - [ ] 5 Tab 切换过滤正确，计数与列表一致 |
| FR-43 | 任务操作：暂停 / 继续 / 重试 / 打开文件 / 打开文件夹 / 复制路径 / 删除 | - [ ] 各操作按钮对应当前状态可用；暂停/继续改变系统下载状态；重试重建任务；打开文件走系统 intent；删除从单例与系统队列移除 |
| FR-44 | 清除已完成：一键移除 SUCCESSFUL 任务 | - [ ] 清除后「已完成」Tab 为空 |
| FR-45 | 下载任务来源与现有 DownloadService 打通 | - [ ] 现有下载入口（书/文件下载）触发后任务出现在列表页 |

### 4.5 文件管理（复用）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-50 | 聚合页「文件管理」直接跳转现有 `FileManageActivity` | - [ ] 跳转成功，功能与旧入口一致，无新增代码 |

### 4.6 非功能需求

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-60 | 全部 UI 用 View 体系（BaseActivity/VMBaseActivity/RecyclerAdapter/viewBinding 委托），不引入 Compose | - [ ] 无新增 Compose 依赖；新增页面均继承既有基类 |
| FR-61 | 日志统一 AppLog（禁 Timber），AppLog 调用包 `kotlin.runCatching` | - [ ] 新增代码无 `android.util.Log`/Timber；JVM 单元测试可运行 |
| FR-62 | 数据库变更经覆盖安装回归验证 | - [ ] 102→103 升级路径真机通过，旧数据完好 |
| FR-63 | 编译通过（`./gradlew assembleAppDebug`）且 Lint 无新增阻塞项 | - [ ] 编译成功，lint 通过 |

## 5. Scenarios（场景）

### 5.1 正常场景

#### SC-01 源开发者排查请求失败
- **前置**：已开启网址记录开关，App 正在使用某书源
- **步骤**：我的页 → 精准管理 → 网址记录；搜索域名关键字 → 选中 5xx 记录 → 查看详情对话框
- **预期**：记录含 url/域名/方法/状态码/耗时/错误信息；筛选 5xx 可快速定位异常源
- **关联**：FR-13/14/15/17/19

#### SC-02 空间紧张一键清理
- **前置**：设备存储告急
- **步骤**：精准管理 → 存储管理 → 查看 8 类占用 → 一键清理（或对 WEBVIEW_CACHE 单项清理）
- **预期**：各分类大小展示正确，清理后释放空间并刷新；书籍缓存若正在播放中被拒绝有提示
- **关联**：FR-30/31/33/34

#### SC-03 下载进度跟踪与文件定位
- **前置**：已通过书/文件入口发起下载
- **步骤**：精准管理 → 下载管理 → 「下载中」Tab 查看进度 → 完成后切「已完成」Tab → 打开文件/打开文件夹/复制路径
- **预期**：任务列表 500ms 内同步系统下载状态；操作按钮按状态可用
- **关联**：FR-40/41/42/43/44/45

### 5.2 边界场景

#### SC-04 网址记录采集开关关闭
- **前置**：`AppConfig.recordUrl=false`
- **步骤**：正常使用 App 后进入网址记录
- **预期**：拦截器直接 `proceed()`，无新记录产生，历史记录仍可查询/清除；再次开启后恢复采集
- **关联**：FR-13/16

#### SC-05 超大请求体
- **前置**：请求 POST body >1000 字符
- **步骤**：发起请求后查看详情
- **预期**：requestBody 截断为前 1000 字符，不崩溃、不落全量敏感内容
- **关联**：FR-14

#### SC-06 无记录 / 全量清除后空态
- **前置**：网址记录表为空（或刚执行「全部」清除）
- **步骤**：进入网址记录列表
- **预期**：显示空态提示，不崩溃；清除计数正确（0 条）
- **关联**：FR-20

#### SC-07 下载任务进程重启后
- **前置**：App 进程被系统杀死，系统 DownloadManager 中任务仍在
- **步骤**：重启 App 进入下载管理
- **预期**：内存单例重建为空，列表可能不显示历史任务（已知局限 Drawback #1），不崩溃
- **关联**：FR-41

#### SC-08 覆盖安装数据库迁移
- **前置**：设备上安装 version=102 旧包
- **步骤**：覆盖安装新包
- **预期**：DB 迁移 102→103 成功，旧数据完好，网址记录功能可用
- **关联**：FR-12/62

### 5.3 异常场景

#### SC-10 迁移失败
- **前置**：`migration_102_103` 执行抛异常
- **步骤**：启动 App
- **预期**：`kotlin.runCatching` 捕获并 `AppLog.put` 失败日志，App 不崩溃；网址记录功能降级（查询报错不阻断主流程）
- **关联**：FR-12

#### SC-11 拦截器采集异常
- **前置**：请求过程中 URL 解析/数据库 insert 抛异常
- **步骤**：发起任意请求
- **预期**：try/catch/finally 保证原始请求结果不受影响，insert 失败仅记日志，不污染响应
- **关联**：FR-14

#### SC-12 存储清理目标被占用
- **前置**：视频正在播放，用户执行一键清理
- **步骤**：触发包含 exoplayer 目录的清理
- **预期**：拒绝清理并提示（复用现有 isVideoPlaying 加锁），其余分类不受影响
- **关联**：FR-33

#### SC-13 下载任务系统级失败
- **前置**：下载 URL 失效或网络中断
- **步骤**：观察下载管理列表
- **预期**：任务进入 FAILED 状态，可点击重试重建任务
- **关联**：FR-43

---

## 附录

### A. 参考源关键实现（Legado_Max）

- **UrlRecord 实体**：`tableName=url_records`，`indices=[timestamp,domain]`；字段 id(Long PK autoGenerate)/url/domain/method/sourceName?/sourceUrl?/timestamp/responseCode/duration/requestBody?/errorMsg?
- **UrlRecordDao**：`flowAll`/`flowSearch`(LIKE url|domain|sourceName)/`flowByDomain`/`flowBySourceName`/`flowByMethod`/`flowByStatus`(success: code 200..299)/`flowAllDomains`/`flowAllSourceNames`/`flowAllMethods`/`flowFilter`(五条件动态拼接 ORDER BY timestamp DESC)；一次性 `getAll`/`getAll(limit,offset)`/`getByDomain`/`getBySourceName`/`search`/`getAllDomains`/`getAllSourceNames`/`getCount`/`getOldRecordsCount`/`getCountSince`；写删 `insert(vararg,onConflict=REPLACE)`/`delete(id)`/`deleteAll():Int`/`deleteOldRecords(timestamp):Int`
- **UrlRecordInterceptor**：`AppConfig.recordUrl` 开关关闭直接 proceed；startTime；try/catch/finally；finally 采集 url/domain/`request.header("X-Source-Name")`/`request.header("X-Source-Url")`/POST body≤1000 字符；`scope.launch{insert+可选事件}`；错误分级 errorMsg→ERROR/4xx→WARN/5xx→ERROR/else INFO；`sanitizeUrl` 脱敏
- **StorageManage 8 类缓存**：BOOK_CACHE(externalFiles/book_cache)/EPUB_CACHE(externalFiles/epub)/TEMP_CACHE(externalCache)/TTS_CACHE(cacheDir/httpTTS)/ACACHE_DISK(cacheDir/ACache)/DB_CACHE(getDatabasePath(legado.db))/LOG_CACHE(externalCache/log)/WEBVIEW_CACHE(getDir(webview)+getDir(hws_webview))；可展开的（书籍按本/TTS 按引擎/ACache 按前缀/DB 按前缀/WebView 按目录）
- **DownloadManage**：5 Tab；任务状态枚举 PENDING/RUNNING/PAUSED/SUCCESSFUL/FAILED；内存单例 `DownloadState`(StateFlow<List<DownloadTask>>)；500ms 轮询系统 DownloadManager 同步；按状态操作
- **pref_precise_manage.xml**：4 个导航 Preference（urlRecord/storageManage/downloadManage/fileManage），`iconSpaceReserved=false`

### B. 本项目现状关键事实（已验证）

- DB version=102，28 个 @Entity；`DatabaseMigrations.kt` migrations 数组当前以 `migration_101_102` 结尾；迁移模板：`kotlin.runCatching{CREATE TABLE IF NOT EXISTS + CREATE INDEX + AppLog.put}`
- View 体系：`BaseActivity<VB>`/`VMBaseActivity<VB,VM>`/`BaseViewModel(execute{}.onSuccess{}.onError{})`/`RecyclerAdapter<ITEM,VB>(DiffUtil)`；viewBinding 委托 `by viewBinding(XxxBinding::inflate)`
- 现成 API：`CacheManageViewModel.buildStorageBreakdown(): Coroutine<List<CacheStorageDetail>>` + `internal directorySize/formatBytes`；`BookHelp.clearCache()`/`clearCache(book)`；`ConfigViewModel.clearCache()`/`clearWebViewData()`
- DownloadService 用系统 DownloadManager：`downloads=hashMapOf<Long,DownloadInfo>` + `completeDownloads=hashSetOf<Long>`，任务不落库、无列表界面，现有轮询 1000ms
- `HttpHelper.kt`：L190 `builder.addInterceptor(DecompressInterceptor)`、L195 `builder.addInterceptor(StreamResetRetryInterceptor)`——UrlRecordInterceptor 挂 Decompress 之后
- 入口现状：`ConfigTag.kt` 5 常量；`ConfigActivity when(configTag)` 5 分支；`MyFragment.onPreferenceTreeClick` 跳转表；`pref_main.xml`「其他」PreferenceCategory 含 bookmark/readRecord/fileManage

### C. 实施约束

1. 源码修改串行化；同文件 Edit 必须串行执行
2. 日志规范遵循 `logging-during-refactoring.md`，AppLog 调用包 `kotlin.runCatching`
3. 编译前更新 `app/src/main/assets/updateLog.md`（`version-delivery-sync.md`）
4. DB 变更遵循 `database-migration-safety.md`；`app/schemas/` 同步 103 版 schema
5. 真机/模拟器验证遵循 `ai_e2e_testing_workflow.md`（`ai_tests/venv/Scripts/python.exe`）
6. minSdk=23，所有新增代码需兼容
7. 包选择：项目代码优化/开发用测试包 `io.legado.miss.app.debug`（`package-naming.md`）
