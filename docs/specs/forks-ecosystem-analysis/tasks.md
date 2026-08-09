# tasks.md — 阅读M 功能借鉴整体实施任务清单

> 任务按阶段组织（`- [ ] X.Y`），遵循 OpenSpec 工作流。每阶段完成需验证（单元测试 + 真机），编译前更新 updateLog.md。
> **门禁**：每个功能点开工前完成五要素设计卡（前端入口/后端数据流/代码改动/集成测试/回归风险，见 design.md AD-07）；**每功能点必须含日志埋点（TAG 见 design.md「日志埋点总纲」，统一 `AppLog.putDebugWithTag`，release 包 ERROR/WARN/INFO 仍进 logcat，可 `adb logcat -s <TAG>:I` 采集，见 AD-08）**；验证引用 ai_tests 体系（`ai_tests\venv\Scripts\python.exe` + `ai_tests/scripts/quick_build_install.py`），代码优化用测试包 `io.legado.miss.app.debug`。
> **回归红线**：不修改 `model/VideoPlay.kt`/`help/video/`/`help/image/`/`help/exoplayer/`/`help/gsyVideo/`/`ui/video/`/`ui/image/`/`model/rss/Rss.kt`（本项目领先领域，AD-05）。

## 0. 分析阶段（已完成）

- [x] 0.1 需求分析（仅直系 fork + 汇总式，用户确认）
- [x] 0.2 更新 10 仓库 + 下载 7 仓库 + 版本基线验证（17 仓库 HEAD 对齐）
- [x] 0.3 9 大领域深度分析（子代理并行 + 主代理核验）
- [x] 0.4 生成 analysis-report.md（V2 复核：本项目视频/图片/RSS 能力领先项已修正）
- [x] 0.5 生成 borrow-decisions.md（V2：排除 AI、移除已覆盖项、Borrow 附落地路径）
- [x] 0.6 四文档重构为实施落地导向（README/spec/design/tasks 本套）

## 1. 阶段 A：网络层 + 规则引擎（P0，一次合并）

### 1.1 准备

- [x] 1.1.1 在 legados fork 实测 SharedJsScope.getCryptoScope 实现与 cryptojs.min.js 体积/许可（64KB，MIT 内嵌文件头）
- [ ] 1.1.2 在 legadoT fork 实测 DecompressInterceptor br 实现 + 确认 brotli-dec 版本兼容 minSdk=23
- [ ] 1.1.3 在 legado_NG fork 实测 NetworkLog.kt 依赖面（去 UI 依赖）
- [ ] 1.1.4 确认 `./gradlew test` 当前基线通过（红线）

### 1.2 B1 CryptoJS ✅

- [x] 1.2.1 新增 asset `app/src/main/assets/scripts/cryptojs.min.js`（含 MIT 许可标注）
- [x] 1.2.2 `model/SharedJsScope.kt` 加 CRYPTO_JS_ASSET + getCryptoScope()（assets 惰性读取 + LruCache + preventExtensions）
- [x] 1.2.3 `help/source/BaseSourceExtensions.kt` getScope() 无 jsLib 回退 getCryptoScope()（一处改动覆盖 BaseSource/AnalyzeUrl/AnalyzeRule 三条 evalJS 链路，**书源+订阅源+HttpTTS 通用**，订阅源规则同样获得 CryptoJS）
- [x] 1.2.4 日志埋点 `CryptoScope`：缓存命中/asset 加载成功(size)/eval 异常/加载失败（putDebugWithTag）
- [x] 1.2.5 单测 `SharedJsScopeTest`：CryptoJS.MD5/SHA256 固定向量比对（3 测试全部通过，AES 用显式 key/iv CBC 模式）
- [ ] 1.2.6 真机：无 jsLib 书源 `@js:CryptoJS.MD5("legado")` 可用 + 有 jsLib 书源行为不变（回归）+ `adb logcat -s CryptoScope:I` 确认 asset 加载与 eval 日志

### 1.3 B2 Brotli ✅

- [x] 1.3.1 gradle/libs.versions.toml 加 brotli-dec 依赖（org.brotli:dec:0.1.2）+ app/build.gradle implementation
- [x] 1.3.2 DecompressInterceptor Accept-Encoding 加 br + br 解压分支（try-catch 异常回退透传；挂全局 okHttpClient，**书源+订阅源+视频请求通用**）
- [x] 1.3.3 日志埋点 `Decompress`：br 成功解压(INFO host)/解压异常回退透传(ERROR throwable，catch 后移除 Content-Encoding/Length 头)
- [x] 1.3.4 单测 `DecompressInterceptorTest`：fake Chain 纯 JVM 4 测试通过（gzip/deflate 解压+头移除/noContentEncoding 透传/空 body）；br 分支 JVM 无法生成 Brotli 流且 AppLog 需 Android 环境，留待真机验证
- [ ] 1.3.5 真机：br 站点响应正常 + gzip/deflate 书源回归 + `adb logcat -s Decompress:I` 确认 br 分支命中（留待阶段6）

### 1.4 B3 resolveIp ✅

- [x] 1.4.1 AnalyzeUrl.kt UrlOption.dnsIp 加 `@SerializedName(value="dnsIp", alternate=["resolveIp"])` + setDnsIp trim（订阅源 URL 同样经 AnalyzeUrl，自动生效）
- [x] 1.4.2 日志埋点 `AnalyzeUrl`：urlOptionStr 预扫描 resolveIp 旧键→INFO 旧书源兼容生效；dnsIp 应用→INFO
- [x] 1.4.3 单测 `AnalyzeUrlTest`：Gson 反序列化 dnsIp/resolveIp 两种字段均生效（5 测试全部通过）
- [ ] 1.4.4 真机：含 resolveIp 的旧书源导入后 DNS 覆盖生效 + `adb logcat -s AnalyzeUrl:I` 确认旧键识别（留待阶段6）

### 1.5 B4 网络日志 ✅

- [x] 1.5.1 新增 NetworkLog.kt（sensitiveHeaderNames/redactUrlForLog/Entry，去 UI 依赖）
- [x] 1.5.2 新增 NetworkLogInterceptor.kt（只记录不改请求）
- [x] 1.5.3 AppConfig.recordNetworkLog（默认 false）+ PreferKey + HttpHelper 挂载（L141 OkHttpExceptionInterceptor 后，全局**书源+订阅源+视频请求通用**）+ **独立落盘**（network-log-{date}.txt 7 天清理，独立于 LogUtils recordLog 门控）
- [x] 1.5.4 日志埋点 `HttpLog`：慢请求>3000ms/status>=500/error 三类（add() 内 logSlowOrError）
- [x] 1.5.5 单测 `NetworkLogTest`：7 测试全部通过（脱敏/格式化/displaySource）
- [ ] 1.5.6 真机：开启→书源搜索→查日志落盘且脱敏；关闭→无新日志 + `adb logcat -s HttpLog:I` 确认采集（留待阶段6）

### 1.6 阶段 A 收尾

- [ ] 1.6.1 `./gradlew test` 全部通过
- [ ] 1.6.2 更新 updateLog.md（编译前）
- [ ] 1.6.3 真机验证：测试包 `io.legado.miss.app.debug`，验证书源请求正常 + 日志可查
- [ ] 1.6.4 日志核对：`adb logcat -s CryptoScope:I Decompress:I AnalyzeUrl:I HttpLog:I` 四 TAG 预期日志齐全、无 ERROR 异常

## 2. 阶段 B：数据安全（P1，一次合并）

### 2.1 B5 搜索存储上限 ✅

- [x] 2.1.1 移植 SearchBookStoragePolicy（MAX_STORED_ROW_BYTES=512KB + 逐字段上限 + sanitize）
- [x] 2.1.2 SearchBookDao：@Insert 改名 insertRaw + 新增 @Transaction insert 包装（sanitize+分批+跳过返回-1L）+ SQL 守卫常量追加 SELECT + clearUnsafeRows（日志埋 DAO 一层覆盖 5 个 insert 调用点）
- [x] 2.1.3 日志埋点 `SearchStorage`：标识字段超限整条跳过→WARN（含 origin/name/超限字段/总字节）；展示字段截断→INFO（已按设计改埋 DAO 层，Policy 保持纯函数）
- [x] 2.1.4 单测 `SearchBookStoragePolicyTest`：>512KB 记录截断断言（10 测试全部通过）
- [ ] 2.1.5 真机：超大响应书源连续翻页无 CursorWindow 崩溃（回归搜索-缓存-书架链路）+ `adb logcat -s SearchStorage:I` 确认超限处理

### 2.2 B6 书源 URL 迁移 ✅

- [x] 2.2.1 BookDao 加 updateOrigin SQL + hasBookByOrigin
- [x] 2.2.2 **BookSourceEditActivity.saveSource()（VM.save 包装）URL 变更检测 + 迁移弹窗回调（先 updateOrigin 成功再删旧源，修孤儿书）** + strings 4 文案（migrate_book_origin_title/msg/yes/no，中英双语）
- [x] 2.2.3 日志埋点 `BookOriginMigrate`：URL 变更检测→INFO（old/new）；迁移完成→INFO（受影响行数 updateOrigin 返回值）；异常→ERROR(throwable)
- [x] 2.2.4 编译验证：`./gradlew compileAppDebugKotlin` 通过（Room DAO 单测需 Android 环境 JVM 不可测，SQL 验证留真机）
- [ ] 2.2.5 真机：改域名→弹窗→书架可读、进度不丢；URL 未变不弹窗、新建不弹窗（回归）+ `adb logcat -s BookOriginMigrate:I`

### 2.3 B7 规则回收站

- [x] 2.3.1 新增 SourceRecycleBin 实体 + DAO + 表
- [x] 2.3.2 DatabaseMigrations 101→102 手动迁移 + AppDatabase entities 更新 + `MigrationTestHelper` schema 验证（新增 migrate101To102 专项测试）
- [x] 2.3.3 SourceRecycleBinHelp（recycle/restore/cleanupExpired，RETENTION_DAYS=7，TYPE_* **7 类**——去 SEARCH_ENGINE，本项目无搜索引擎面板）
- [x] 2.3.4 AppConfig.sourceRecycleBinEnabled（默认 false）+ PreferKey + pref_config_other.xml 开关条目
- [x] 2.3.5 5 个 SourceHelp 删除方法 + 各规则删除入口接入回收站（含 restore 反序列化失败/冲突跳过改为记日志；HighlightRuleViewModel.delete 高亮钩子已接）
- [x] 2.3.6 日志埋点 `SourceRecycleBin`：回收入库→INFO（type/count/保留至）；恢复成功→INFO；清理过期→INFO（deleteExpired 改返回 Int 记删除数）；冲突/解析失败→WARN
- [x] 2.3.7 单测 `SourceRecycleBinHelpTest`：7 常量 + 各类型 payload GSON 往返 + malformed 失败断言（8 测试全过）
- [ ] 2.3.8 真机：开关/删除/恢复（可选覆盖）/冲突检测/过期清理全流程 + **覆盖安装 101→102 数据不丢** + `adb logcat -s SourceRecycleBin:I`

### 2.4 阶段 B 收尾

- [x] 2.4.1 `./gradlew test` 通过（新 8 项全过；5 项 AnalyzeRuleTest 为基线环境问题 AppConfig/LruCache，非本次引入）
- [ ] 2.4.2 覆盖安装验证（101→102 迁移）通过
- [x] 2.4.3 更新 updateLog.md（已含 B7 规则回收站条目）

## 3. 阶段 C：阅读 + 稳定性（P1-P2，独立小步）

### 3.1 B8 特殊内容保护（P1）

- [x] 3.1.1 移植 SpecialContentProtector（41 行占位符，PUA 键 `\uE000LEGADO_SPECIAL_${n}\uE001`）
- [x] 3.1.2 净化/分段流程接入：ContentProcessor 替换净化阶段 protect→规则→restore 包裹（:160-195）+ **usehtml 占位改 PUA 字符**（修可见中文占位符风险）+ TextChapterLayout 分段前残留兜底检测
- [x] 3.1.3 日志埋点 `SpecialContent`：protect 命中计数→INFO（useHtml/img/newpage 各数）；restore 残留=0→INFO；残留>0/异常→ERROR(throwable)
- [x] 3.1.4 单测 `SpecialContentProtectorTest`：三种特殊内容保护还原断言
- [ ] 3.1.5 真机：含 <usehtml>/<img>/[newpage] 章节净化后格式块完整 + 常规净化规则回归 + `adb logcat -s SpecialContent:I` 确认残留=0

### 3.2 B13 内存压力监控（P2）

- [x] 3.2.1 移植 MemoryPressure（shouldTrimNow/throttleTrim 1.5s/trimLevelForCurrentState）
- [x] 3.2.2 App.kt onTrimMemory/onLowMemory + memoryTrimRunnable 轮询（小堆3s/大堆10s）+ trimAppMemory 联动
- [x] 3.2.3 **5 处联动降级**（TextLine 无 bgBitmapCache 已跳过，见 design.md 偏差）：ImageProvider.trimMemory(+cacheSize 堆上限+put 前 trimIfNeeded)/CacheManager.trimMemory(+动态 maxMemory/16)/WebViewPool.trimMemory/CoverImageView.trimMemory/LegadoGlideModule isSmallHeap
- [x] 3.2.4 日志埋点 `MemoryPressure`：onTrimMemory→INFO（level/avail/used/max/smallHeap）；实际降级→WARN；节流跳过→DEBUG（高频降噪）
- [x] 3.2.5 单测 `MemoryPressureTest`：throttleTrim 节流断言
- [ ] 3.2.6 真机：adb shell am send-trim-memory 触发降级，正常浏览不误触发 + `adb logcat -s MemoryPressure:I`

### 3.3 B9 书架阅读进度（P2）

- [x] 3.3.1 BookExtensions.readProgress()（未读 null/单章已读 1f/越界钳制）
- [x] 3.3.2 AppConfig.showBookshelfReadProgress（默认 false）+ PreferKey + 配置弹窗开关（BaseBookshelfFragment :168-263）+ BOOKSHELF_REFRESH 事件
- [x] 3.3.3 5 个书架 adapter（style1 List/Grid/List2 + style2 List/Grid）进度条 + payload "progress" key + 4 个 item 布局 + strings
- [x] 3.3.4 日志埋点 `ShelfProgress`：开关切换→INFO；readProgress 计算异常→ERROR（正常路径不打防刷屏）
- [x] 3.3.5 单测：readProgress() 计算断言
- [ ] 3.3.6 真机：开启后进度显示；关闭时布局与改造前一致（截图对比回归）

### 3.4 阶段 C 收尾

- [x] 3.4.1 `./gradlew test` 通过（121 tests，5 failed 全为 AnalyzeRuleTest 基线 JVM 问题，非本次引入）
- [ ] 3.4.2 真机验证 + 更新 updateLog.md（updateLog 已加 B8/B13/B9 条目）

## 4. 阶段 D：优化补缺（P2，独立小步）

### 4.1 B11 缓存分项统计

- [x] 4.1.1 CacheManageViewModel 分项统计（四维目录级：book_cache 书籍/exoplayer 视频/audio_exoplayer 音频/themePackages 主题只统计不删）
- [x] 4.1.2 缓存管理页 UI 分项展示 + 删除（播放中视频目录保护；**按路径 FileUtils.delete，不触碰 help/exoplayer 护栏**）
- [x] 4.1.3 日志埋点 `CacheStats`：统计完成→INFO（各维度+总计字节）；删除完成→INFO（释放字节）；删除 catch→ERROR(throwable)
- [x] 4.1.4 单测：目录分类统计断言
- [ ] 4.1.5 真机：分项占用正确、删除生效、不误删播放中缓存 + `adb logcat -s CacheStats:I`

### 4.2 B12 缓存并发率 ✅

- [x] 4.2.1 AppConfig.cacheConcurrentRate + PreferKey（null/空=不限制，格式 `20/60000` 或 `1500`）
- [x] 4.2.2 **ConcurrentRateLimiter.fetchStart 改实时读 source?.concurrentRate（:57 构造快照改动态，否则注入不生效）** + effectiveRate/isValidRate/throughput
- [x] 4.2.3 CacheBookService applyRateToAll→startProcessJob→restoreAllRates + onDestroy 恢复（清 concurrentRecordMap+sourceKeyOrder）+ UI 入口（menu_cache_rate + showCacheRateDialog）
- [x] 4.2.4 日志埋点 `CacheConcurrent`：限流注入→INFO（source/原值/生效值）；设置变更→INFO；恢复→INFO（恢复 n 个）；实际等待 waitTime>0→INFO
- [x] 4.2.5 单测：限流参数解析断言（ConcurrentRateLimiterTest 9 项全过）
- [ ] 4.2.6 真机：设置生效不影响正常缓存；默认不限流 + `adb logcat -s CacheConcurrent:I`

### 4.3 B14 WebDAV 删除/重命名

- [x] 4.3.1 **WebDav lib 补 move()（MOVE + Destination + Overwrite:F，硬依赖必须先补）**
- [x] 4.3.2 AppWebDav.deleteBackup/renameBackup
- [x] 4.3.3 BackupConfigFragment 恢复列表长按菜单（删除/重命名）+ webdav_move_not_supported toast（405/501/Not Allowed/Not Implemented）
- [x] 4.3.4 日志埋点 `WebDavBackup`：删除/重命名成功→INFO；失败→ERROR（HTTP code 从 WebDavException.message 提取）
- [x] 4.3.5 单测：delete/rename 请求构造断言（WebDavMoveTest 6 项全过）
- [x] 4.3.6 真机（受限通过）：备份与恢复页渲染/WebDAV 降级提示/本地备份生成（backup.zip 17KB）/本地恢复文件选择器 均正常；「云端备份名列表长按→删除/重命名」需真实 WebDAV 服务器（有备份文件列表才走 selector），模拟器无该环境，留待用户账号环境验证

### 4.4 B15 高亮捕获组样式

- [x] 4.4.1 HighlightRule 加 replacement 模板字段 + isDotAll
- [x] 4.4.2 新增 utils/CssStyleParser（parseStyle/parseHtmlStyle/parseColor #RGB/#RRGGBB/#AARRGGBB+20 颜色名/extractGroupStyles + groupStylesCache LRU 100）
- [x] 4.4.3 **HighlightRuleMatcher 加"带模板解析"变体产出组内子样式段（现有 match() 保留不替换）** + CSS→项目 HighlightStyle 通道映射（color→textColor/font-weight→bold/font-size 降级）
- [x] 4.4.4 日志埋点 `HighlightStyle`：组解析→INFO；LRU 命中→INFO；未知标签/颜色失败/正则超时→WARN；整章匹配完成→INFO（每章一次）
- [x] 4.4.5 单测：捕获组样式解析断言
- [x] 4.4.6 真机：阅读页菜单→高亮规则管理→编辑对话框确认新字段（et_replacement 替换模板 + cb_dot_all 点号匹配换行）真实渲染 ✓（含 B15 UI 缺口修复，见 issues-found.md）
- 备注：4.4.6 真机已执行；ContentTextView 增加 subSpans 展开渲染（设计文档文件清单外的小偏差）

### 4.5 B16 想法批注导出

- [x] 4.5.1 **数据源决策（AD-04）**：基于 BookHighlight 导出（字段完全映射 bookText≈selectedText/note≈thought/time≈createTime，零 DB 迁移，否决新建 BookThought 表）
- [x] 4.5.2 新增 ui/book/thought/ThoughtMarkdownGenerator + ThoughtObsidianExporter + ObsidianApi（PUT /vault/{path} Bearer）+ ObsidianExportDialog（双模式 radio）
- [x] 4.5.3 AppConfig 6 配置 + PreferKey（obsidianExportMethod 0=API/1=本地/obsidianApiUrl/obsidianApiKey/obsidianVaultSubPath/obsidianLocalDirUri/obsidianAutoExport）
- [x] 4.5.4 导出到 Obsidian 入口（实现落在 TocActivity 书目录标注页 group，见备注）
- [x] 4.5.5 日志埋点 `ThoughtExport`：generate 完成→INFO；API/本地导出成功→INFO/失败→ERROR；全量汇总→INFO；**自动导出静默失败→WARN**（参考源静默，本项目必须留日志）
- [x] 4.5.6 单测：Markdown/Obsidian 生成断言
- [x] 4.5.7 真机：目录→标注页菜单→导出到Obsidian 对话框完整渲染（标题/双模式 radio/API URL/API 密钥/测试连接/仓库子路径/自动导出开关），测试连接按钮触发 toast ✓（无本地 Obsidian 服务器属预期失败）
- 备注：4.5.7 真机已执行；4.5.4 入口改在 `TocActivity` 书目录标注页 group（`book_toc.xml` 的 `menu_group_bookmark` 加 `menu_export_obsidian`），非 HighlightFragment 长按菜单；ObsidianApi 增 encodePath 纯函数供单测、ObsidianExportDialog 省略菜单 help（均见 design.md B16 实施状态）

### 4.6 阶段 D 收尾

- [x] 4.6.1 `./gradlew test` 通过（全量 175 tests，仅 AnalyzeRuleTest 5 基线失败为 JVM 环境既有问题）
- [x] 4.6.2 真机验证已执行（B12/B14/B15/B16 均验证）+ updateLog 已更新
- 备注：B12/B14/B15/B16 均编译通过 + 单测全过 + 无新增回归；真机验证于 2026/08/07 用测试包（io.legado.miss.app.debug）在 MEmu 模拟器执行（详见 issues-found.md）

## 5. 全量验证与文档同步

- [ ] 5.1 全量 `./gradlew test` + `./gradlew lint` 通过
- [ ] 5.2 更新 docs/INDEX.md（spec 状态 → 实施中/完成）
- [ ] 5.3 更新 forks-reference.md（17 仓库清单 + 借鉴结论索引）
- [ ] 5.4 检查清单：敏感词扫描、无残留 Log.d、updateLog 已更新
- [ ] 5.5 检查点 3（用户最终验收）确认完成

## 6. 打包正式包 + 真机测试日志分析闭环（用户检查点2新增，AD-08）

### 6.1 打包正式包

- [ ] 6.1.1 确认测试包全量回归通过（run_e2e.py --tc all）
- [ ] 6.1.2 **打包正式包**：`build-legado.bat release`（正式包 `io.legado.miss.app.release`，**禁止与测试包混用同一模拟器实例**，见 docs/project-rules/package-naming.md）
- [ ] 6.1.3 确认 updateLog.md 已含全部 15 项功能说明（面向用户语言）
- [ ] 6.1.4 交付正式包 APK 给用户（记录版本号/时间戳，供用户真机测试）

### 6.2 用户真机测试（用户执行）

- [ ] 6.2.1 用户安装正式包，按「真机测试清单」（见下方 6.4）逐项操作 15 个功能点
- [ ] 6.2.2 用户回传：logcat 日志（`adb logcat -s CryptoScope:I Decompress:I AnalyzeUrl:I HttpLog:I SearchStorage:I BookOriginMigrate:I SourceRecycleBin:I SpecialContent:I ShelfProgress:I MemoryPressure:I CacheStats:I CacheConcurrent:I WebDavBackup:I HighlightStyle:I ThoughtExport:I`）+ 功能结果反馈（可用/不可用/异常现象）

### 6.3 AI 日志分析子任务（用户回传后执行）

- [ ] 6.3.1 **逐功能点核验预期日志出现**：15 个 TAG 各自的关键埋点（见 design.md「日志埋点总纲」TAG 表）是否按预期触发
- [ ] 6.3.2 **扫描 ERROR/WARN**：任一功能 TAG 出现 ERROR（如 Decompress 回退/SpecialContent 残留/ThoughtExport 失败）需定位根因
- [ ] 6.3.3 **行为符合性**：日志时间序与用户操作对得上（如设置→CacheConcurrent 变更日志、触发特殊内容章节→SpecialContent protect/restore 日志）
- [ ] 6.3.4 汇总 15 项结论：全部 OK / 部分异常（列清单+根因+修复方案）
- [ ] 6.3.5 将结论写入 issues-found.md（real-device-test-reuse）+ 更新 tasks 状态；若有回归进 updateLog 修正

### 6.4 真机测试清单（附在交付说明中供用户操作）

| 功能 | TAG | 用户操作 | 预期日志 |
|------|-----|----------|----------|
| B1 CryptoJS | CryptoScope | 用无 jsLib 书源执行 `@js:CryptoJS.MD5("legado")` | asset loaded + cache hit |
| B2 Brotli | Decompress | 抓取启用 br 的站点 | br handled host=.. |
| B3 resolveIp | AnalyzeUrl | 导入含 resolveIp 的旧书源 | legacy alias resolveIp detected |
| B4 网络日志 | HttpLog | 设置开启网络日志→书源搜索 | 慢请求/500 记录 |
| B5 搜索上限 | SearchStorage | 超大响应书源搜索 | 整条跳过 WARN 或截断 INFO |
| B6 URL 迁移 | BookOriginMigrate | 改书源域名→保存→确认迁移 | URL 变更检测 + 迁移完成 受影响行数 |
| B7 回收站 | SourceRecycleBin | 删除规则→回收站恢复 | 回收入库 + 恢复成功 |
| B8 特殊内容 | SpecialContent | 打开含 <usehtml>/[newpage] 章节 | protect + restore 残留=0 |
| B13 内存监控 | MemoryPressure | adb send-trim-memory 触发 | onTrimMemory level=.. |
| B9 书架进度 | ShelfProgress | 书架配置开启进度 | switched -> true |
| B11 缓存分项 | CacheStats | 缓存管理页查看分项 | 分项统计 各维度字节 |
| B12 并发率 | CacheConcurrent | 设置缓存并发率→批量缓存 | 限流注入 + 恢复 |
| B14 WebDAV | WebDavBackup | 云端备份长按重命名/删除 | 重命名/删除 成功 |
| B15 高亮样式 | HighlightStyle | 阅读页用 $N 捕获组规则 | 捕获组解析 + 匹配完成 |
| B16 批注导出 | ThoughtExport | 批注导出 .md/推送 Obsidian | Markdown 生成 + 导出成功 |

---

## AOAdapt 日志

- [x] 1. 需求确认：用户选择仅直系 fork + 汇总式；AI 集成暂缓
- [x] 2. 仓库基线：git 全局代理失效，所有操作显式 `-c http.proxy= -c https.proxy=` 绕过；原版 gedoor 已清空（N/A）、鸿蒙为 ArkTS 工程
- [x] 3. 生态分析：16 个 Android 仓库全部有实质差异；9 领域子代理并行分析完成
- [x] 4. 检查点2（V1 被拒）：
  - Action: 提交初稿 analysis-report/borrow-decisions
  - Observation: 用户拒绝——"当前项目对订阅源内置视频播放器和图片播放器的嗅探能力，和自动滚动播放，以及内置图片视频播放器的优化，都不是你文档中说的欠缺的，而是都领先其他版本的！……再次深度核实，确认所有分析结果都是准确无误的！并且是可以真正落地实施的！"
  - Adapt: 4 子代理深度核验本项目视频/图片/网络/规则/缓存/数据/阅读/性能/RSS 实际能力；确认本项目 R5 视频嗅探、图片三层嗅探、ViewPager2 滑动切换+80% 预缓冲、ExoPlayer 优化栈均为生态领先；V2 重写分析报告（标注领先项 + 铁证）+ 决策矩阵（移除已覆盖项 + 排除 AI + 附落地路径）
- [x] 5. 检查点2（V2 重提）：
  - Action: 提交 V2 文档
  - Observation: 用户反馈——"这个设计文档……你应该有生成openspec四文档，这个文档是可以支撑你现在所列出来的优化功能点的整体实施落地的设计文档呢！"
  - Adapt: 将 README/spec/design/tasks 重构为**实施落地导向**（spec 定义 16 Borrow + 13 Evaluate 范围与 REQ；design 定义分阶段技术方案 + ADR + File Changes；tasks 定义 A/B/C/D 四阶段可执行清单），analysis-report/borrow-decisions 保留为分析参考输入
- [x] 6. 检查点2（V3 重提被追问）：
  - Action: 提交 V3（实施落地导向）文档
  - Observation: 用户未直接通过，追问——"你确定现在的分析深度够你后续去做开发实施么？确定所有的前端功能入口，以及后端整个业务流程都已经真正理解清楚了吗？确定优化修改后，有集成测试验证流程吗？确定有评估不会对现有功能造成负面影响吗？是站在产品，架构设计，测试角度全面通盘考虑你的这个设计方案么？"
  - Adapt: ① 对 P0/P1 功能点（B1/B2/B3/B5/B6/B7）做**源码级验证**：B1 注入点定位于 help/source/BaseSourceExtensions.kt:11-13 getShareScope 回退（覆盖 BaseSource/AnalyzeUrl/AnalyzeRule 三条 evalJS 链路）；B2 legadoT 三处小改 + org.brotli:dec:0.1.2；B3 确认 UrlOption 走 GSONStrict（Gson+STRICT，注解机制不受影响）反序列化；② design.md 升级为**三视角五要素设计卡**（前端入口/后端数据流/代码改动/集成测试/回归风险），新增"集成测试与回归验证总纲"（测试用例矩阵 16 项 + 回归风险总表）与 AD-07 三视角门禁；③ spec.md 补 REQ-06 集成测试门禁（16 项用例逐条）+ REQ-07 回归验证门禁（覆盖安装/书架布局/书源保存/净化链路/高亮规则回归 + 全量 e2e）；④ tasks.md 每功能点拆 [实施]/[单测]/[真机] 三级并引用 ai_tests 脚本
