# tasks.md - 精准管理（网址记录/存储管理/下载管理/文件管理聚合入口）

> **状态**：✅ 任务全部完成（2026/08/08 真机验证通过：L2 6/6 + 采集链路验证，全部勾选）
> **创建日期**：2026-08-07
> **格式**：`- [x] X.Y` 任务清单 + AOAdapt 日志
> **核心定位**：借鉴 Legado_Max「精准管理」（我的页→聚合 4 项：网址记录/存储管理/下载管理/文件管理），用项目自有 View 体系（BaseActivity/BaseViewModel/RecyclerAdapter/viewBinding）重写，不引入 Compose
> **参考文档**：
> - `docs/specs/precise-manage/spec.md`（需求背景与范围）
> - `docs/specs/precise-manage/design.md`（方案设计 / ADR 决策，本清单权威对齐源）
> - `docs/specs/precise-manage/README.md`（文档索引）
> - 项目规范：`docs/project-rules/`（版本交付同步 / AI 端到端测试 / 包名选择）

---

## 1. 数据层

> **目标**：新增 `url_records` 表（Room 实体 + DAO + migration），DB version 102→103；开关走 `PreferKey.recordUrl` + `AppConfig.recordUrl`。

- [x] 1.1 新增 `data/entities/UrlRecord.kt`
  - `@Entity(tableName = "url_records", indices = [Index("timestamp"), Index("domain")])` + `@Parcelize`
  - 字段：`id:Long=0` PK autoGenerate / `url:String` / `domain:String` / `method:String` / `sourceName:String?=null` / `sourceUrl:String?=null` / `timestamp:Long=now` / `responseCode:Int=0` / `duration:Long=0` / `requestBody:String?=null` / `errorMsg:String?=null`
- [x] 1.2 新增 `data/dao/UrlRecordDao.kt`
  - 方法全量：`flowAll` / `flowSearch` / `flowByDomain` / `flowBySourceName` / `flowByMethod` / `flowByStatus` / `flowAllDomains` / `flowAllSourceNames` / `flowAllMethods` / `flowFilter`（组合筛选）/ `getAll` / `getByDomain` / `getBySourceName` / `search` / `getCount` / `delete` / `deleteAll` / `deleteOldRecords` / `insert(vararg)`
  - 查询按 `timestamp DESC` 排序，数量上限参考 design.md 常量（建议 LIMIT 2000）
- [x] 1.3 AppDatabase `version = 102→103` + entities 加 `UrlRecord::class` + `abstract val urlRecordDao: UrlRecordDao`
- [x] 1.4 `DatabaseMigrations.migrations` 加 `migration_102_103`（仿 migration_101_102 模板）
  - `migration_101_102` 位于 `DatabaseMigrations.kt:763`，模板：`kotlin.runCatching { CREATE TABLE IF NOT EXISTS url_records(...) + CREATE INDEX IF NOT EXISTS index_url_records_timestamp / index_url_records_domain + AppLog.put }`，`.onFailure { e -> AppLog.put(...) }`
  - 记得在 `migrations` 数组（L27 `migration_101_102` 之后）追加
- [x] 1.5 `PreferKey.recordUrl` + `AppConfig.recordUrl`
  - `recordUrl` 默认 `true`（采集开关，随书源请求全局生效）
- [x] 1.6 编译验证 `./gradlew compileAppDebugKotlin`（勿 `--offline`）+ 确认 `app/schemas/io.legado.app.data.AppDatabase/103.json` 生成

## 2. URL 采集

> **目标**：OkHttp 拦截器链采集请求/响应元数据，异步写库，开关关闭零开销直通。

- [x] 2.1 新增 `help/http/UrlRecordInterceptor.kt`
  - `object UrlRecordInterceptor : Interceptor`：开关（`AppConfig.recordUrl`）关闭直接 `chain.proceed(request)`
  - 采集：`url` / `domain` / `method` / `responseCode` / `duration` / `requestBody`（POST 时截断，上限 1000 字符）/ `errorMsg`
  - 脱敏：URL 中 query 参数里的 token/key/password/sign 值打码（对齐 design.md）
  - 级别映射：`responseCode >= 400` 或异常映射为错误记录，记录 `errorMsg`
  - 异步写入：`scope.launch { runCatching { appDb.urlRecordDao.insert(record) } }`，不阻塞请求线程
  - `sourceName`/`sourceUrl` 透传：经请求 header（`X-Source-Name` / `X-Source-Url`）注入后剥除
- [x] 2.2 `HttpHelper.kt` 拦截器链挂载（L190 `DecompressInterceptor` 之后）
  - 仅挂载一次（构建 OkHttpClient 处），不随每次请求重复挂
- [x] 2.3 单测 `UrlRecordInterceptorTest`
  - 用例：脱敏生效（token/password/key/无效 URL/无 = 查询）——采集链路依赖 AppConfig(appCtx)/appDb(Room)，纯 JVM 留真机（同 DecompressInterceptorTest 已知上限）

## 3. 网址记录 UI

> **目标**：列表 + 搜索 + 域名/书源/方式/状态筛选 + 清除（7 天/30 天/全部）+ 采集开关，详情对话框展示原始字段。

- [x] 3.1 布局：`activity_url_record.xml` + `item_url_record.xml`（详情对话框用 MaterialAlertDialog 展示完整字段）
- [x] 3.2 新增 `ui/urlRecord/UrlRecordAdapter.kt`
  - 继承 `RecyclerAdapter<UrlRecord, ItemUrlRecordBinding>`（viewBinding 委托），点击弹详情对话框
- [x] 3.3 新增 `ui/urlRecord/UrlRecordViewModel.kt`
  - 继承 `BaseViewModel`：搜索关键字 / 筛选条件（domain/sourceName/method/status）/ 清除 7 天/30 天/全部 / 采集开关切换（`AppConfig.recordUrl`）
  - 组合筛选走 `UrlRecordDao.flowFilter`，避免多次 Diff 通知
- [x] 3.4 新增 `ui/urlRecord/UrlRecordActivity.kt`
  - 继承 `BaseActivity`，菜单项：清除 7 天 / 清除 30 天 / 清除全部 + 采集开关（菜单开关）
  - 清空需确认对话框（防误删）
- [x] 3.5 strings en/zh 文案（`url_record` 前缀，含筛选标题/清除动作/确认文案/空列表提示）

## 4. 存储管理

> **目标**：复用 `CacheManageViewModel` 的统计逻辑（`buildStorageBreakdown`/`directorySize`/`formatBytes`），单项与一键清理 + 打开路径。

- [x] 4.1 新增 `ui/book/storage/StorageManageViewModel.kt`
  - `buildCacheItems` 复用 `CacheManageViewModel.buildStorageBreakdown`（`CacheManageViewModel.kt:29`）/ `directorySize`（`:100`）/ `formatBytes`（`:108`）
- [x] 4.2 布局：`activity_storage_manage.xml` + `item_cache_item.xml`
  - 每项显示分类名/路径/大小/占用占比，头部总占用统计
- [x] 4.3 新增 `ui/book/storage/StorageManageAdapter.kt`
  - 继承 `RecyclerAdapter`（大小排序变化时刷新）
- [x] 4.4 新增 `ui/book/storage/StorageManageActivity.kt`
  - 继承 `BaseActivity`：单项清理 / 一键清理（确认对话框 + 逐个删除 + 进度反馈）/ 打开路径（Intent ACTION_VIEW 目录）
  - 清理后 `buildCacheItems` 刷新，异步删除用 `Coroutine.async` 避免 ANR
- [x] 4.5 strings en/zh 文案（`storage_manage` 前缀，确认清理文案必须明确删除目标）

## 5. 下载管理

> **目标**：`DownloadService` 最小侵入接入统一状态源 `DownloadState`（保留现有广播/通知），UI 列表 500ms 轮询刷新，操作齐全。

- [x] 5.1 新增 `service/DownloadState.kt`
  - `DownloadTask`（id/url/fileName/startTime/status/progress/totalSize/downloadedSize/speed）+ `DownloadStatus` 枚举（WAITING/RUNNING/PAUSED/COMPLETED/FAILED）
  - `StateFlow<Map<Long, DownloadTask>>` + 方法：`addTask` / `updateTask`（含速度计算）/ `removeTask` / `clear` / `cancelDownload` / `queryAllTaskStatus`
- [x] 5.2 改造 `service/DownloadService.kt` 接入 `DownloadState`
  - 保留现有 `downloads = hashMapOf<Long, DownloadInfo>()`（`:37`）与 `completeDownloads = hashSetOf<Long>()`（`:38`）及广播/通知逻辑
  - `onDownloadComplete` / enqueue 成功 同步 `DownloadState.addTask`；每次 query 后 `DownloadState.updateTask`/`removeTask`
  - 最小侵入：仅加数据源桥接，不改下载核心流程
- [x] 5.3 新增 `ui/download/DownloadManageViewModel.kt`
  - 继承 `BaseViewModel`，500ms 轮询 `DownloadState.queryAllTaskStatus()` + 收集 `DownloadState.tasks` flow 刷新列表
- [x] 5.4 布局：`activity_download_manage.xml`（Tab 切换：全部/下载中/已暂停/已完成/失败）+ `item_download_task.xml`（文件名/状态/进度条/大小/速度/操作按钮区）+ `menu/download_manage.xml`
- [x] 5.5 新增 `ui/download/DownloadManageAdapter.kt`
  - 继承 `RecyclerAdapter`，按任务 id 做 Diff，操作按钮回调 Activity
- [x] 5.6 新增 `ui/download/DownloadManageActivity.kt`
  - 继承 `BaseActivity`：暂停 / 继续 / 重试 / 打开文件 / 打开文件夹 / 复制路径 / 删除 / 清除已完成
  - 打开文件用系统 `ACTION_VIEW` + FileProvider，复制路径用 `ClipboardManager`
- [x] 5.7 单测 `DownloadStateTest`
  - 用例：`addTask` / `updateTask`（progress/bytes/status）/ `removeTask` / `clear` ——`cancelDownload`/`queryAllTaskStatus` 依赖系统 DownloadManager，留真机
- [x] 5.8 strings en/zh 文案（`download_manage` 前缀，操作动作/状态文案/Tab 标题）

## 6. 聚合入口

> **目标**：我的页「其他」组入口 → 精准管理页（4 导航：网址记录/存储管理/下载管理/文件管理）；文件管理复用现有 `FileManageActivity`，不新写。

- [x] 6.1 新增 `res/xml/pref_precise_manage.xml`
  - 4 个导航 `Preference`（`io.legado.app.lib.prefs.Preference`），标题图标对应 4 项
- [x] 6.2 新增 `ui/config/PreciseManageFragment.kt`
  - 继承 `PreferenceFragment`，加载 `pref_precise_manage.xml`，`onPreferenceTreeClick` 跳转 4 个目标 Activity
- [x] 6.3 `ConfigTag.PRECISE_MANAGE = "preciseManage"`（`ConfigTag.kt` 追加）+ `ConfigActivity` 分支加载 `PreciseManageFragment`
- [x] 6.4 `pref_main.xml`「其他」组加 `preciseManage` Preference + `MyFragment` 跳转分支
  - `MyFragment` 当前跳转方式沿用 `OTHER_CONFIG` 模式（ConfigActivity + ConfigTag）
- [x] 6.5 `AndroidManifest.xml` 注册 3 个新 Activity：`UrlRecordActivity` / `StorageManageActivity` / `DownloadManageActivity`（`FileManageActivity` 已注册）
- [x] 6.6 strings en/zh（`precise_manage` 分组名/4 项标题与摘要）

## 7. 验证与文档

> **强制规范**：按 AGENTS.md §强制规则（updateLog 编译前更新 / AI 端到端测试 / 真机测试包选择）。

- [x] 7.1 编译验证 `./gradlew compileAppDebugKotlin`（勿 `--offline`）
- [x] 7.2 全量单测 `./gradlew test --no-parallel`（需 `--no-parallel`；结果 **186 完成 / 5 失败**，失败均为既有基线失败：jsonPath 系 `AppConfig` 初始化失败、regex 系 `LruCache not mocked`，与本功能无关；新增 UrlRecordInterceptorTest 5 例 + DownloadStateTest 6 例全部通过）
- [x] 7.3 `app/src/main/assets/updateLog.md` 更新（追加在 `cronet版本:` 之后、已有条目之前；面向用户语言；基于 `git diff` 逐文件审计）
- [x] 7.4 本 `tasks.md` 勾选 + `design.md` 实施状态块 + `docs/INDEX.md` 状态更新
- [x] 7.5 真机验证（模拟器测试包 `io.legado.miss.app.debug`：精准管理入口 / 网址记录开关+采集+列表 / 存储管理统计+清理 / 下载管理列表）——✅ 2026/08/08 完成：L2 6/6 场景通过（entry/url_record/storage_manage/download_manage/file_manage/crash_check）；采集链路独立验证 WAL 合并后 `url_records` 真实录入 4 条（RSS 源网络请求，含 HTTPS 200）；真机发现并修复 DownloadManageActivity `<init>` 期构造 Adapter 崩溃（`by lazy`），无 FATAL）

---

## 关键实施事实速查（写代码时参考）

| 事实 | 值 |
|------|-----|
| UrlRecord 实体字段 | `id:Long=0` PK autoGenerate / `url:String` / `domain:String` / `method:String` / `sourceName:String?=null` / `sourceUrl:String?=null` / `timestamp:Long=now` / `responseCode:Int=0` / `duration:Long=0` / `requestBody:String?=null` / `errorMsg:String?=null`；`indices=[timestamp,domain]` |
| 拦截器挂载点 | `HttpHelper.kt:190` `builder.addInterceptor(DecompressInterceptor)` 之后 |
| migration_102_103 模板 | `DatabaseMigrations.kt:763` migration_101_102：`kotlin.runCatching { CREATE TABLE IF NOT EXISTS url_records(...) + CREATE INDEX IF NOT EXISTS index_url_records_timestamp / index_url_records_domain + AppLog.put }.onFailure { AppLog.put }`；数组 L27 追加 |
| 迁移注释习惯 | `AppDatabase.kt` L138-144 每个手写 migration 均有注释行（如 `// precise-manage: 102→103 ...`） |
| 日志 | 本项目用 `AppLog.put()`（包 `kotlin.runCatching`），禁用 Timber |
| gradle 约束 | 勿 `--offline`；单测/构建需 `--no-parallel` |
| DownloadService 现状 | `downloads = hashMapOf<Long, DownloadInfo>()`（:37）+ `completeDownloads = hashSetOf<Long>()`（:38），改造需最小侵入，保留广播/通知 |
| View 体系 | `BaseActivity` / `VMBaseActivity` / `BaseViewModel` / `RecyclerAdapter` / `DiffRecyclerAdapter` / viewBinding 委托 |
| 存储统计复用 | `CacheManageViewModel.buildStorageBreakdown`（:29）/ `directorySize`（:100）/ `formatBytes`（:108） |
| 文件管理 | 复用现有 `FileManageActivity`，tasks 不列其实现 |
| 配置 Tag | `ConfigTag.kt` `object ConfigTag`，追加 `PRECISE_MANAGE` |

---

## AOAdapt 日志

| 时间 | 任务 | Action | Observation | Adapt |
|------|------|--------|--------------|-------|
| 2026/08/08 | 全景 | 完成数据层/拦截器/网址记录UI/存储管理/下载管理/聚合入口全部代码 | 编译全通过；单测 186 完成（175 基线 + 11 新增全过，5 失败为既有基线：jsonPath 系 AppConfig 初始化失败、regex 系 LruCache not mocked） | 写单测时发现 UrlRecordInterceptor 采集链路依赖 Android context，参照 DecompressInterceptorTest/NetworkLogTest 先例只测纯函数 sanitizeUrl（private→internal），字段采集留真机 |
| 2026/08/08 | 文档 | git status 核对实际改动文件清单 | git 工作区既有多任务遗留 diff（webdav/obsidian/加密/缓存并发等），precise-manage 新增文件均未跟踪 | updateLog 面向用户只列本功能 4 条增量；tasks/design/INDEX 状态同步 |

---

## 任务完成级别说明

- **L1 代码完成**：对应任务代码编写完成并通过编译（`compileAppDebugKotlin`），不含验证。
- **L2 功能验证**：功能在真机/模拟器可操作可用（本清单 7.5 真机项），新增单测通过（2.3/5.7）。
- **L3 场景验证**：真实使用场景验证通过（网址记录随搜索/阅读真实采集、存储清理前后占用变化、下载全流程暂停/续传/完成），回归基线单测不退化。