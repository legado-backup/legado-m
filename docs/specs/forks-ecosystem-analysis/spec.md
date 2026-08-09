# spec.md — 阅读M 功能借鉴与整体实施（OpenSpec）

## Intent

本 spec 的目标是：将 `borrow-decisions.md` 决策矩阵中筛选出的 **15 项 Borrow 优化功能点（另含 4 项 P0 优先路线）** 整体落地到本项目（阅读M，私有 fork 自 legado-E）源码，并产出可实施的设计（design.md）与任务清单（tasks.md）。

具体意图：
1. **阶段 A（P0）**：网络层 + 规则引擎 4 项低风险纯增量（CryptoJS 内置 / Brotli OkHttp 通道 / resolveIp 兼容 / 网络日志），**书源+订阅源双链路通用**
2. **阶段 B（P1）**：数据安全 3 项（搜索存储上限 / 书源 URL 迁移 / 规则回收站）
3. **阶段 C（P1-P2）**：阅读与稳定性 3 项（特殊内容保护 / 内存压力监控 / 书架进度）
4. **阶段 D（P2）**：优化补缺 5 项（缓存分项统计 / 缓存并发率 / WebDAV 删除重命名 / 高亮捕获组样式 / 想法批注导出）
5. **Evaluate 项**：列为评估清单（E1-E13），不纳入本次实施，但记录评估要点供后续立项

**不是做什么**：
- ❌ 不接入 AI 集成（用户明确指示暂不考虑：Rimchars Agent / Jingshiro 助手 / NG MCP / HapeLee 云TTS / 章节翻译）
- ❌ 不移植已被本项目覆盖/领先的功能（307/308、Bitmap 内存估算、WebDAV 进度、备份按需选择、视频预加载/嗅探体系，见 borrow-decisions Not 区）
- ❌ 不进行 UI/主题/视觉改造（分析阶段已排除，实施阶段同样排除）
- ❌ 不引入 S3/Relay/epubcore/domain 层/MD3 Compose 等架构级改动（Not 区）

## Scope

### In Scope（本次实施落地的功能点）

| # | 功能项 | 来源 fork | 优先级 | 所属阶段 |
|---|--------|-----------|--------|----------|
| B1 | 内置 CryptoJS（无 jsLib 自动回退加密作用域，书源+订阅源+HttpTTS 通用） | legados | P0 | A |
| B2 | Brotli 解压（OkHttp 通道补全，书源+订阅源通用） | legadoT | P0 | A |
| B3 | 旧书源/订阅源 dnsIp/resolveIp 兼容 | LegadoTeam | P0 | A |
| B4 | 网络日志（敏感头脱敏，书源+订阅源通用） | legado_NG | P1 | A |
| B5 | 搜索结果存储字节上限 | Rimchars | P1 | B |
| B6 | 书源 URL 变更迁移书架书籍 | Suml-1 | P1 | B |
| B7 | 规则回收站（7 类规则 7 天保留） | youfengknight | P1 | B |
| B8 | 特殊内容保护 | legados | P1 | C |
| B9 | 书架显示阅读进度 | legados | P2 | C |
| B11 | 缓存分项统计与删除 | refgd | P2 | D |
| B12 | 缓存并发率设置 | youfengknight | P2 | D |
| B13 | 运行时内存压力监控 | legados | P2 | C |
| B14 | WebDAV 备份删除/重命名 | Jingshiro | P2 | D |
| B15 | 高亮规则捕获组样式（$N）解析 | Jingshiro | P2 | D |
| B16 | 想法批注分享/导出（Obsidian 双模式） | Jingshiro | P2 | D |

### Evaluate 清单（本 spec 只记录评估要点，不实施）

| # | 功能项 | 来源 fork | 评估要点 |
|---|--------|-----------|----------|
| E1 | 视频无缝过渡队列 | refgd | 本项目已自动连播+预加载，仅切集黑屏值得评估 |
| E2 | 纯 JS 单文件书源引擎 | legados | 架构级扩展，最高价值但需专项任务 |
| E3 | 智能分组（在读/未读/已读） | HapeLee | 需 DB 虚拟分组改造 |
| E4 | 详细阅读记录（会话级+Web 可视化） | Jingshiro | 新表+采集器+2565 行前端，中等规模 |
| E5 | TTS 路由器体系 | legado_NG | 需与现有引擎选择重构 |
| E6 | 云 TTS Provider（7 家） | HapeLee | 依赖云 API Key+计费 |
| E7 | 章节翻译 | HapeLee | 依赖翻译 API Key |
| E8 | RSS 书籍化阅读 | huajideshutiao | 独立使用模式，产品契合度确认 |
| E9 | 朗读会话+TTS 队列窗口 | Rimchars | 队列窗口可拆，角色缓存依赖 AI |
| E10 | 阅读书票 | Jingshiro | 产品化评估 |
| E11 | 阅读轮次标签 | Jingshiro | 价值中等 |
| E12 | 主题导出 | Jingshiro | 补导出 zip 即可 |
| E13 | 阅读成就（21 档） | legados | 与 E4 联动才有意义 |

### Out of Scope

- AI 集成全套（用户指示暂缓）
- Not 区 15 项（S3/Relay/JS 编辑器/Max 口令/epubcore/domain 层/鸿蒙/MD3 Compose/已被本项目覆盖项/订阅内容搜索已覆盖）
- 独立阅读项目（墨水/Kototoro 等 13 个）与 release-only 仓库（墨听/书享/Tauri）
- 所有 UI/主题/视觉/Material 相关功能

## Approach

### Selected Approach

**分阶段落地 + 每功能点独立小步提交**：

1. **阶段 A（P0，网络层+规则引擎）**：B1→B2→B3→B4 一次合并实施，全部为纯增量低风险（新增依赖/新文件/注解/拦截器），可合并为一次"网络层+规则引擎优化"任务，遵循 `forks-reference.md` 方法论
2. **阶段 B（P1，数据安全）**：B5→B6→B7 一次合并实施（防崩溃+防数据丢失），B5 涉及 Room 无迁移（纯工具类），B6 加 BookDao SQL，B7 需 Room 迁移 +1 版本
3. **阶段 C（P1-P2，阅读/稳定性）**：B8→B13→B9 独立小步，B8/B13 为工具类低侵入，B9 涉及书架 adapter
4. **阶段 D（P2，优化补缺）**：B11→B12→B14→B15→B16，B15/B16 基于本项目已有基础（HighlightRuleMatcher/BookHighlight）增量移植
5. **验证**：每阶段完成需单元测试通过（`./gradlew test`）+ 真机验证（按 `ai_e2e_testing_workflow.md`），涉及 Room 迁移的需验证覆盖安装升级
6. **借鉴依据**：每项实施前跳转 borrow-decisions.md 对应条目 → analysis-report.md 对应领域章节获取源码引用 → 在 `temp/forks-comparison/{fork}/` 实测源码 → 移植

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| A. 15 项一次性全部实施 | 单次大 PR 落地全部功能 | ❌ 改动面过大难以验证，且 B15/B16 需先评估本项目基础；分阶段可逐项验收 |
| B. 每功能点独立 spec | 每个 Borrow 项单独一个 spec 目录 | ❌ 过度拆分，P0 阶段 4 项同属网络层可合并；阶段化分组更高效 |
| C. 直接抄源码替换 | 从 fork 复制文件覆盖本项目 | ❌ 本项目基线与 fork 差异大（Room 版本、架构），需按落地路径适配，禁止整文件覆盖 |
| D. 本次仅出设计不实施 | 只产出设计文档 | ❌ 用户明确要求"支撑整体实施落地"，须含可执行任务清单 |

### Drawbacks

1. **Room 迁移风险**：B7 规则回收站需新增 `sourceRecycleBin` 表，迁移升级路径必须用 `DatabaseMigrations` 手动迁移（本项目 89→101 已是手动 Migration），避免 AutoMigration 破坏旧数据
2. **依赖新增**：B2 需引入 `org.brotli:dec` 依赖，需确认与 minSdk=23 兼容（brotli-dec 无最低版本限制，风险低）
3. **加密资产合规**：B1 需引入 `cryptojs.min.js` asset（MIT 许可），需确认许可标注
4. **书架 adapter 改动**：B9 涉及多个书架 adapter（style1/style2 的 Grid/List），改动面分散，需逐步验证
5. **fork 差异适配**：每项移植均需先读 fork 源码再适配本项目结构，禁止整文件覆盖（见 Alternatives C）

### Prior Art

- [forks-archive-comparison](../forks-archive-comparison/)：Archive 私仓对比（12 借鉴/8 不借鉴/9 待评估），B5/B7/E10 同源
- [legados-forks-comparison](../legados-forks-comparison/)：GEd520 集成方案（10 项），B1/B2/B8/E2 同源
- [forks-reference.md](../../project-rules/forks-reference.md)：组件优化方法论（实施阶段的执行规范）
- 本项目既有 spec：`app-stability-round2`（B5 关联 SQLiteBlobTooBig）、`exoplayer-resilience`/`rss-video-player-enhancement`/`image-sniffer-optimization` 等（视频/图片领先能力沉淀，实施时不触碰）

## Requirements

### REQ-01 阶段 A：网络层+规则引擎（强制）

- **R-A1**：B1 内置 CryptoJS——`SharedJsScope` 提供 `getCryptoScope()`，无 jsLib 时自动回退注入；JS 侧可直接 `CryptoJS.MD5/SHA/AES` 等；验证：无 jsLib 书源中 `@js:CryptoJS.MD5(...)` 可用
- **R-A2**：B2 Brotli——`DecompressInterceptor` 声明 `Accept-Encoding: gzip, deflate, br` 且 `when(encoding)` 增加 `"br"` 分支；验证：请求 br 站点响应正常解压
- **R-A3**：B3 resolveIp——`AnalyzeUrl.dnsIp` 字段加 `@SerializedName(value="dnsIp", alternate=["resolveIp"])`；验证：旧书源 `resolveIp` 字段能被反序列化
- **R-A4**：B4 网络日志——新增日志拦截器（敏感头脱敏 `sensitiveHeaderNames`/`redactUrlForLog`）+ `AppConfig.recordHttpLog` 开关（默认关），接入 `LogUtils` 落盘；验证：开启后请求/响应摘要可查，敏感头不落盘

### REQ-02 阶段 B：数据安全（强制）

- **R-B1**：B5 搜索存储上限——`SearchBookStoragePolicy` 工具类 + `SearchModel` 保存/解析前逐条字节校验（512KB 上限，超限截断/跳过）；验证：超大搜索结果不触发 CursorWindow 崩溃
- **R-B2**：B6 书源 URL 迁移——`BookDao.updateOrigin` SQL + `BookSourceEditActivity` 保存时检测 URL 变更且有书时弹窗询问迁移；验证：改域名后书架书籍 origin 批量更新
- **R-B3**：B7 规则回收站——`sourceRecycleBin` 表（Room 手动迁移 +1）+ `SourceRecycleBinHelp`（recycle/restore/cleanupExpired，7 天保留，默认关开关）+ 7 类规则删除入口接入（书源/订阅源/替换规则/目录规则/朗读引擎/净化规则/高亮规则，去 SEARCH_ENGINE）；验证：删除书源后可恢复（可选覆盖/冲突检测）

### REQ-03 阶段 C：阅读与稳定性（强制）

- **R-C1**：B8 特殊内容保护——`SpecialContentProtector` 工具类（`<usehtml>`/`<img>`/`[newpage]` 占位符保护+还原）接入净化/分段流程；验证：含特殊内容的正文不被净化破坏
- **R-C2**：B13 内存压力监控——`MemoryPressure`（shouldTrimNow/throttleTrim 1.5s 节流）+ Application `onTrimMemory` 回调降 Glide/BitmapLruCache；验证：低内存模拟下图片缓存被降级
- **R-C3**：B9 书架阅读进度——`BookExtensions.readProgress()` + 书架 adapter 进度条 + `AppConfig.showBookshelfReadProgress`（默认关）；验证：开启后列表/网格显示进度

### REQ-04 阶段 D：优化补缺（强制）

- **R-D1**：B11 缓存分项统计——缓存管理页按 书籍/音频/视频/主题 分类统计 + 分项删除；验证：各分类占用正确、删除生效
- **R-D2**：B12 缓存并发率——`AppConfig.cacheConcurrentRate` + `CacheBookService` 按比例限流；验证：设置生效且不影响正常缓存
- **R-D3**：B14 WebDAV 删除/重命名——`AppWebDav.deleteBackup/renameBackup` + `BackupConfigFragment` 长按菜单接线；验证：坚果云等 WebDAV 备份可删除/重命名
- **R-D4**：B15 高亮捕获组样式——`applyHighlightRule` 捕获组（$N）样式解析 + LRU 缓存，接入现有 HighlightRuleMatcher；验证：`规则1|规则2` 分组样式正确
- **R-D5**：B16 想法批注导出——Markdown 生成 + Obsidian REST/本地双模式导出（复用 BookHighlight 数据）；验证：导出文件/推送 Obsidian 成功

### REQ-05 工程约束（强制）

- R-5.1 每阶段完成必须 `./gradlew test` 通过；Room 迁移必须验证覆盖安装升级（89→新版本链）
- R-5.2 每项实施前必须读 fork 源码适配（禁止整文件覆盖），遵循 forks-reference.md
- R-5.3 涉及真机验证的按 ai_e2e_testing_workflow.md 执行，代码优化用测试包 `io.legado.miss.app.debug`
- R-5.4 不修改视频/图片嗅探与播放器相关代码（本项目领先领域）
- R-5.5 编译前必须更新 updateLog.md（version-delivery-sync 规则）
- R-5.6 每个 Borrow 功能点开工前必须完成五要素设计卡（前端入口/后端数据流/代码改动/集成测试/回归风险，见 design.md AD-07），缺任一要素不得开工

### REQ-06 集成测试门禁（强制）

每个功能点除单元测试外，必须按下表完成集成验证（测试体系：`ai_tests/docs/fixed_test_workflow.md`，脚本用 `ai_tests/scripts/quick_build_install.py`，解释器必须用 `ai_tests\venv\Scripts\python.exe`）：

- **R-6.1 B1 CryptoJS**：`SharedJsScopeTest`（MD5/SHA256 固定向量比对）+ 真机无 jsLib 书源 `@js:CryptoJS.MD5` 可用、有 jsLib 书源行为不变
- **R-6.2 B2 Brotli**：MockWebServer br 响应解压断言 + 真机 br 站点抓取正常；gzip/deflate 书源回归
- **R-6.3 B3 resolveIp**：Gson 反序列化 alternate 断言 + 真机旧书源导入生效
- **R-6.4 B4 网络日志**：脱敏断言（Authorization/Cookie/token 不落盘）+ 真机开启/关闭开关验证
- **R-6.5 B5 搜索上限**：超大记录截断断言 + 真机超大响应书源连续翻页无崩溃（关联 app-stability-round2 P1-1）
- **R-6.6 B6 URL 迁移**：updateOrigin SQL 断言 + 真机改域名→弹窗→书架可读、阅读进度不丢
- **R-6.7 B7 回收站**：RecycleBinHelp 单测 + **MigrationTestHelper 验证 101→102 schema** + 真机覆盖安装升级数据不丢 + 开关/删除/恢复/过期清理全流程
- **R-6.8 B8 特殊内容**：占位符保护还原断言 + 真机含 `<usehtml>`/`<img>`/`[newpage]` 章节净化后格式完整
- **R-6.9 B13 内存监控**：throttleTrim 节流断言 + 真机 `adb shell am send-trim-memory` 触发降级
- **R-6.10 B9 书架进度**：readProgress() 断言 + 真机 4 种书架样式显示、关闭时布局零变化
- **R-6.11 B11 缓存分项**：分类统计断言 + 真机分项占用/删除正确、不误删播放中视频缓存
- **R-6.12 B12 并发率**：限流参数断言 + 真机设置生效、默认不限流
- **R-6.13 B14 WebDAV**：delete/rename 请求构造断言 + 真机坚果云删除/重命名成功
- **R-6.14 B15 高亮样式**：捕获组样式解析断言 + 真机 `规则1|规则2` 分组样式正确、现有规则不回归
- **R-6.15 B16 批注导出**：Markdown/Obsidian 生成断言 + 真机导出 .md / 推送 Obsidian 成功

### REQ-07 回归验证门禁（强制）

- **R-7.1** 涉及 Room 迁移（B7）必须在测试包上执行**覆盖安装回归**（旧版 APK → 新版 APK，验证书架/书源/订阅源/高亮/阅读记录全部不丢、表结构正确）
- **R-7.2** 涉及书架 adapter（B9）必须验证开关关闭时布局与改造前像素级一致（截图对比）
- **R-7.3** 涉及书源保存主流程（B6）必须覆盖：URL 未变不弹窗、新建书源不弹窗、迁移后书籍可读三分支
- **R-7.4** 涉及正文净化主链路（B8）必须覆盖常规净化/替换规则不回归（保护仅在命中特殊标签时启用）
- **R-7.5** 涉及高亮引擎（B15）必须逐条回归现有高亮规则
- **R-7.6** 每阶段收尾执行 `./gradlew test` + 真机 L1 冒烟（quick_build_install.py）；检查点3 前执行 `python ai_tests/run_e2e.py --tc all` 全量回归
- **R-7.7** 回归风险缓解措施见 design.md「回归风险总表」；任何一条未通过即视为该功能点未完成，不得进入下一阶段

### REQ-08 日志埋点门禁 + 正式包交付（强制）

**日志埋点**（B1-B16 全 15 项，见 design.md「日志埋点总纲」+ AD-08）：

- **R-8.1** 每个功能点必须含日志埋点，统一走 `AppLog.putDebugWithTag(tag, message, throwable, level)`（`constant/AppLog.kt:123`），TAG 用新常量（15 个：CryptoScope/Decompress/AnalyzeUrl/HttpLog/SearchStorage/BookOriginMigrate/SourceRecycleBin/SpecialContent/ShelfProgress/MemoryPressure/CacheStats/CacheConcurrent/WebDavBackup/HighlightStyle/ThoughtExport），❌ 禁用 Timber/android.util.Log
- **R-8.2** release 正式包中 ERROR/WARN/INFO 级埋点必须仍输出 logcat（`putDebugWithTag` 特性），保证真机可用 `adb logcat -s <TAG>:I` 采集；DEBUG 级仅限高频降噪场景（如节流跳过）
- **R-8.3** 每功能点实现后必须核对预期日志出现且无 ERROR/WARN 残留（无日志=功能未完成）

**正式包交付与真机验证闭环**（tasks.md 阶段 6，AD-08）：

- **R-8.4** 全部 15 项实施完成并全量回归后，打包**正式包** `build-legado.bat release`（正式包名 `io.legado.miss.app.release`，禁止与测试包混用同一模拟器，见 package-naming.md）
- **R-8.5** 用户按真机测试清单（tasks.md 6.4）逐项操作 15 功能点，回传 logcat（15 TAG 全列命令）+ 功能结果反馈
- **R-8.6** AI 收到日志后执行**日志分析子任务**（tasks.md 6.3）：逐项核验预期日志出现 → 扫描 ERROR/WARN 定位根因 → 行为符合性（日志时间序 vs 用户操作）→ 输出 15 项结论（全 OK / 部分异常+根因+修复）→ 结果写入 issues-found.md 并更新 tasks/updateLog

## Scenarios

### 场景 1：书源规则需要加密算法
用户使用无 jsLib 的 JSON 书源，规则里需要 MD5/AES 加密 → 阶段 A 完成后 `@js:CryptoJS.MD5(...)` 直接可用，不再需要网络下载 jsLib。→ 验证 B1 完成（REQ R-A1）。

### 场景 2：旧版书源 DNS 字段
用户导入老书源（字段为 `resolveIp` 而非 `dnsIp`）→ 阶段 A 完成后自动反序列化生效，无需手动改书源。→ 验证 B3（R-A3）。

### 场景 3：书源域名变更导致书架变无源
用户修改书源 URL（如换了镜像域名）→ 阶段 B 完成后保存时弹窗询问是否批量迁移书架书籍 origin，避免全部变无源。→ 验证 B6（R-B2）。

### 场景 4：误删书源规则
用户误删一个书源 → 阶段 B 完成后进入回收站（7 天），可在回收站恢复（可选覆盖）。→ 验证 B7（R-B3）。

### 场景 5：搜索超大数据源崩溃
用户搜索一个返回超大结果的坏书源 → 阶段 B 完成后单行超过 512KB 被截断，不再触发 CursorWindow 崩溃。→ 验证 B5（R-B1）。

### 场景 6：低内存设备闪退
低内存设备上浏览大量图片 → 阶段 C 完成后 onTrimMemory 触发内存压力监控降级 Glide 缓存，减少闪退。→ 验证 B13（R-C2）。

### 场景 7：调试网络问题
用户反馈某书源无法解析 → 阶段 A 完成后可在设置开启网络日志，查看脱敏的请求/响应摘要辅助定位。→ 验证 B4（R-A4）。
