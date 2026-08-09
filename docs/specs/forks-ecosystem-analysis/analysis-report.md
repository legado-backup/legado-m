# analysis-report.md — Legado 直系 fork 生态功能深度分析报告

> **分析对象**：17 个 Legado 直系源码 fork（原版已清空标记 N/A，鸿蒙为跨平台工程单独说明）
> **方法**：git clone 实测源码为准（AD-04），按 9 大功能领域横向对比，明确排除 UI/主题/视觉
> **基线**：本项目（阅读M = legado-E fork）作为"本项目现状"对照，**每个领域均以实际源码核验本项目能力，非经验假设**
> **版本**：V2（2026-08-05）— 按检查点2用户反馈深度复核重写，修正本项目视频/图片/RSS 能力误判

---

## 一、版本基线（2026-08-05 快照）

| 本地目录 | remote | 分支 | HEAD | 最后提交 | 状态 |
|----------|--------|------|------|----------|------|
| legado-E | Luoyacheng/legado-E | main | 8b87c5a | 2026-08-01 | ✅ 本项目 fork 源 |
| LegadoTeam_legado | LegadoTeam/legado（喵公子） | master | 1370e7440 | 2026-08-04 | ✅ 主流分支 |
| legadoT | skybbk1001/legadoT（阅读T） | master | 529442a83 | 2026-08-02 | ✅ 主流分支 |
| Rimchars_legado | Rimchars/legado（阅读Archive） | main | 1505c1d5 | 2026-07-18 | ✅ 主流分支 |
| refgd_legado | refgd/legado（阅读R） | own | accef33 | 2026-06-21 | ✅ Rimchars 分支化衍生 |
| Jingshiro_legado | Jingshiro/legado | main | 9ec5921 | 2026-07-13 | ✅ 自用增强分支 |
| Legado_Max | DandanLLab/Legado_Max（蛋蛋Max） | main | 8d066e5 | 2026-06-01 | ✅ Max 系列源头 |
| legado_NG | joestar817/legado_NG（阅读NG） | main | 4e0bb0b | 2026-08-04 | ✅ 独立包名/NG 体系 |
| legados | GEd520/legados（辞晨Max，gitee） | main | a5ab6dab | 2026-07-31 | ✅ 功能最密集 |
| youfengknight_Legado_Max | youfengknight/Legado_Max（怣疯Max） | main | 2026-06-05 | 2026-06-05 | ✅ 蛋蛋Max 衍生 |
| Suml-1_Legado_Max | Suml-1/Legado_Max | main | 2026-08-04 | 2026-08-04 | ✅ 蛋蛋Max 衍生 |
| HapeLee_legado-with-MD3 | HapeLee/legado-with-MD3 | main | 2026-08-04 | 2026-08-04 | ✅ MD3 重构 |
| 325506_legado-with-MD3-DIY | 325506/legado-with-MD3-DIY | main | 2026-05-05 | 2026-05-05 | ✅ MD3 衍生 |
| huajideshutiao_legado | huajideshutiao/legado（🍟） | main | 2026-06-26 | 2026-06-26 | ✅ 喵公子衍生 |
| mgz0227_legado-Harmony | mgz0227/legado-Harmony（鸿蒙） | main | 2025-11-25 | 2025-11-25 | ⚠️ ArkTS 工程 |
| gedoor_legado | gedoor/legado（原版） | master | 9bb0569 | 2026-05-27 | ❌ **源码已清空**（仅侵权公告 README） |
| legado-archive | Rimchars/legado-private-armv8-release | - | - | - | ⚠️ 私仓 release-only，仅记录不分析 |

**关键发现**：
1. **原版 gedoor/legado 已清空源码**（2026-05-27 起仅保留侵权公告），后续分析以"本项目 fork 源 legado-E + 主流 fork"为事实基线
2. **mgz0227_legado-Harmony 是 ArkTS/HarmonyOS 工程**（AppScope/hvigor/oh-package.json5），非 Android `app/` 结构，且 README 声明不再开源仅发布 HAP → 仅做工程级说明，不纳入功能对比
3. 全部 16 个 Android 仓库 HEAD == remote HEAD 验证通过

---

## 二、9 大功能领域分析

> **重要更正（V2）**：初稿曾把本项目视频/图片能力误判为"欠缺"。经逐文件源码核验，本项目在**订阅源内嵌视频/图片播放器嗅探、自动滚动/连续播放、内置播放器优化**三方面已**领先所有 fork**。以下各领域"本项目现状"均以实际源码为准。

### 领域 1：网络层

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| legadoT | **Brotli 解压**：`Accept-Encoding: gzip, deflate, br` + `BrotliInputStream` | `help/http/DecompressInterceptor.kt` |
| legadoT | **网络日志**：`HttpLogger.nextId()/HttpRecord`，`MAX_BODY_SIZE=4096L`，`AppConfig.recordHttpLog` 开关 | `help/http/HttpLogInterceptor.kt` |
| LegadoTeam | **旧书源 DNS 兼容**：`@SerializedName("dnsIp", alternate=["resolveIp"])`（commit 1370e7440 #573） | `model/analyzeRule/AnalyzeUrl.kt` |
| LegadoTeam | Web 旧评论空响应修复 + 外部资源阻塞修复（#571/#572） | `model/webBook/` 相关 |
| Suml-1 | SSL 校验失败专门提示拦截器（40 行独有文件） | `OkHttpExceptionInterceptor.kt` |
| legado_NG | **网络日志**：`sensitiveHeaderNames` L21 / `redactUrlForLog` L214 / `Entry` L255，敏感头脱敏 | `help/http/NetworkLog.kt` + NetworkLogInterceptor.kt |
| Rimchars | **WebView 池化按作用域**（`Scope.GLOBAL/DISCOVERY/RSS`、acquire/release/scheduleDestroyScope） | `help/webView/WebViewPool.kt` |
| Rimchars | HTTP 捕获 + WebSocket 管理（`MAX_CONNECTIONS=16`） | `help/HttpCaptureHelper.kt` / `help/JsWebSocketManager.kt` |
| Rimchars | Relay 隧道服务（公开 Web 中继/息屏保活） | `service/relay/`（10 文件） |

**本项目现状（源码核验）**：
- **307/308 重定向跟随：已有**（`help/http/OkHttpUtils.kt:42-57` 手动取 Location 重发 + `HttpHelper.kt:106-107` followRedirects(true) + `RedirectCacheInterceptor` 302 缓存 500 条/10 分钟）——Max 系该能力本项目已覆盖
- **Cronet 集成：完整**（`lib/cronet/` 12 文件，`CronetLoader` 动态下载 so + md5 校验，`CronetHelper.kt:76` **enableBrotli(true)**，`CronetInterceptor` 协议错误熔断/半开恢复）——Cronet 通道已支持 Brotli
- **Brotli（OkHttp 通道）：无**（`DecompressInterceptor.kt:21` 仅 gzip/deflate）——唯一缺口
- **网络日志：无完整请求/响应拦截器**（仅 `AppLog` TAG_HTTP 摘要埋点 `AnalyzeUrl.kt:448`，`LogUtils.kt:29-88` 落盘 7 天，不记录正文）——缺口
- **resolveIp 旧书源兼容：无**（`AnalyzeUrl.kt:858` `dnsIp` 无 `@SerializedName` alternate）——缺口
- WebView 池化：本项目 `BackstageWebView` 已被嗅探体系大量复用（见领域 6），无 Scope 划分

**差异分析**：Brotli（OkHttp 通道）、网络日志、resolveIp 兼容是三个直接可借鉴的低风险增量；307/308 已覆盖无需引入。

### 领域 2：规则引擎

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| legados | **纯 JS 单文件书源引擎**：一个 `.js` 文件即完整书源（`config` 对象 + `search/getChapters/getContent` 函数），每次调用新建 scope 并发隔离，`LruCache(64)` 编译缓存 | `model/jsSource/JsSourceEngine.kt`（120行）+ JsSourceConfig/JsSourceBook/JsSourceMarshaller；`BookSource.mainJs` 字段 v99→100 加列；`WebBook.kt` 8 处分派点 |
| legados | **内置 CryptoJS**：`CRYPTO_JS_ASSET="scripts/cryptojs.min.js"`，无 jsLib 的 JSON 书源自动回退 CryptoJS 作用域（MD5/SHA/HMAC/AES/DES/RC4/PBKDF2） | `model/SharedJsScope.kt:32-73` |
| legados | **按书源隔离缓存 sourceCache**：`cache`/`globalCache` 保持全局，新增 `sourceCache` 按当前书源/订阅源隔离 | `model/analyzeRule/AnalyzeRule.kt:1081` + `BaseSource.kt:393` `bindings["sourceCache"]=JsCacheManager(source)` |
| Rimchars | **段落规则引擎** + JS 扩展（`showBrowser(url, html, preloadJs, config)` L111）+ App 链接导入（`legado://`/`yuedu://` `/paragraphrule` 路径）+ 气泡包系统 | `help/book/ParagraphRuleProcessor.kt` / `ParagraphRuleJsExtensions.kt` / `ui/association/OnlinePackageImportRoute.kt` / `help/config/BubblePackageManager.kt` |
| Legado_Max | 书源下一页懒加载（可选字段，不开启不导出） | `model/analyzeRule/` + `BookSource.kt` |
| huajideshutiao | RSS 书籍化 JS 桥（`searchBook(key)`/`addBook(bookUrl)`） | `ui/book/rss/RssJsExtensions.kt` |

**本项目现状（源码核验）**：
- 规则解析五种模式齐全：**CSS/XPath/JSONPath/正则/JS（含 `@webjs:`）**（`AnalyzeRule.kt:795-797` Mode 枚举 + `AnalyzeByJSoup/AnalyzeByXPath/AnalyzeByJSonPath/AnalyzeByRegex` 全部存在）
- **无 webJSDir**（仅单条 `@webjs:` + jsLib）
- **无内置 CryptoJS**（全库源码 0 匹配 `cryptojs`，无 `scripts/cryptojs.min.js` asset；`SharedJsScope.kt:23-80` 仅做 jsLib 远程加载，加密靠 JS 侧 `md5Encode`/`base64Encode`/hutool AES）
- **无纯 JS 单文件书源**（`mainJs`/`JsSourceEngine` 仅 docs 提及）
- **无 sourceCache 绑定注入**；但缓存键已按源隔离（`BaseSource.kt:142,278` `v_${getKey()}_${key}` 前缀），缓存本体全局共享（内存 50MB Lru + Room `cache` 表）
- **JS 扩展 API 丰富**：`JsExtensions.kt`（1199 行）含 ajax/connect/webView(4种)/importScript/downloadFile/getTxtInFolder/unzip/un7z/unrar/queryTTF/replaceFont/base64/hex/时间/简繁转换/字体等

**差异分析**：CryptoJS 内置是**最高价值**（解决无网络/jsLib 时加密缺失，纯增量）；JS 书源引擎是架构级扩展（突破声明式）；段落规则是独立新体系，价值低于前两者。

### 领域 3：缓存策略

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| refgd | **缓存统计分项删除**：按书籍/音频/视频/主题细分占用，支持删除临时缓存 | `ui/book/cache/CacheManageViewModel.kt`（`loadStats` L148 / `buildStorageBreakdown` L677 / `deleteStorageDetail` L164） |
| Legado_Max | **小说缓存备份**（含目录与章节），恢复后直接读备份无需重新抓取 | `help/CacheManager.kt` |
| LegadoTeam | 漫画模式离线缓存 + 保存图片（#550） | `model/webBook/` 相关 |
| youfengknight | 缓存并发率设置（格式同书源 concurrentRate） | `AppConfig.cacheConcurrentRate` |
| Rimchars | **Bitmap 内存估算**：按位深与集合大小估算缓存内存 | `help/CacheManager.kt` `estimatedMemorySize()` L25 |
| HapeLee | **缓存下载队列**：`addRange/removeRange/countInRange` 区间化管理 | `CacheDownloadQueue.kt` L3-73 |

**本项目现状（源码核验）**：
- **两级缓存**：内存 50MB Lru（`CacheManager.kt:19-25`）+ Room `cache` 表（`:60-72`）；文件型走 ACache + 书籍 `externalFiles/book_cache/*.nb`（`BookHelp.kt:59`）
- **Bitmap 内存估算：已有等价实现**（`help/glide/ImageProvider.kt:50-60` `BitmapLruCache` 用 `value.byteCount` 计内存，容量 `AppConfig.bitmapCacheSize` 默认 50MB，超限动态 resize）——Rimchars `estimatedMemorySize` 思路本项目已覆盖
- **视频缓存：统一 SimpleCache**（`ExoPlayerHelper.kt:1132-1143`，容量 `videoCacheSize` 50-2048MB 默认 100MB，LeastRecentlyUsedCacheEvictor）
- **HTTP 缓存 50MB** + jsLib 缓存 + 日志缓存（分目录管理）
- **无缓存分项统计/删除 UI**（无按书籍/音频/视频/主题细分）——缺口
- **无 cacheConcurrentRate**（缓存下载并发是固定 `updateCacheThreadCount` 默认 16，`AppConfig.kt:460-463`）——缺口
- 漫画离线缓存：本项目漫画章节有 `preDownloadNum` 双向预下载（`ReadManga.kt:380-409`）

**差异分析**：缓存分项统计（refgd）与缓存并发率（youfengknight）可借鉴；Bitmap 内存估算已覆盖无需引入；小说缓存备份（Max）与缓存下载队列（HapeLee）价值中等。

### 领域 4：AI 功能

> **V2 范围调整**：按用户检查点2明确指示"**暂不考虑接入 AI 集成**"，本章仅作事实记录（fork 能力盘点），**不进入借鉴决策矩阵**。

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| Rimchars | **完整 AI Agent 运行时**：规划/中断/状态/校验/工具执行五件套，`runToolLoop` L17；工具含角色/有声/世界书/工作区/记忆/图片/章节总结（AiToolRegistry 500 行） | `help/ai/`（33 文件） |
| Jingshiro | **AI 助手**：`requestWithTools` 工具调用循环，`MAX_TOOL_ROUNDS` 90 轮上限，BatchConfirmation 批量确认；30+ OpenAI tools（书架/书源/订阅/统计/高亮/主题/WebDAV/Obsidian）；ToolRouter 读写分离/删除保护 | `ui/book/read/ai/AiChatViewModel.kt` L387-582 + `tool/AiToolDef.kt` L6-429 + `tool/ToolRouter.kt` L41-800 + `help/config/AiConfig.kt` |
| HapeLee | **章节翻译**：分块翻译+缓存+重试（`translateAndCacheChunk` L209 / `translateChunkWithRetry` L259） | `domain/usecase/TranslateChapterUseCase.kt` |
| HapeLee | 7 家云 TTS Provider（阿里/AWS/Azure/Gemini/MiMo/OpenAI/火山） | `help/tts/` provider 目录 |
| legado_NG | **MCP 服务**（NanoHTTPD JSON-RPC，`serve()` L84 / `handleJsonRpc` L125；含 BookshelfMcpTools/SettingsMcpTools/AgentMemoryMcpTools） | `web/mcp/McpServer.kt` |

**本项目现状（源码核验）**：无任何 AI 对话/Agent/翻译/MCP 功能；TTS 仅系统引擎 + 用户自定义 HTTP TTS 表（`data/entities/HttpTTS.kt`，`model/ReadAloud.kt:29-41` 简单引擎选择），**无内置云 Provider、无路由器**。

**差异分析**：AI 是各 fork 最大创新密集区但实现成本最高。按用户指示暂缓；若未来启动，Jingshiro 的**批量确认机制**（写操作合并一次弹窗）与 Rimchars 的 **朗读会话/角色缓存**可作无 AI 依赖的独立片段先行评估。

### 领域 5：数据管理

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| Jingshiro | **WebDAV 增强**：备份列表/删除/重命名/恢复 | `help/AppWebDav.kt` L126-170 + `ui/config/CloudBackupActivity.kt` |
| Rimchars | **S3 云存储**（签名请求+容器管理+容量上限异常） | `lib/cloud/`（S3CloudStorageBackend/S3Signer/S3ContainerManager） |
| Rimchars | 顶栏/封面合集独立 WebDav URL | `help/AppWebDav.kt`（569 行） |
| refgd | **备份按需选项目**（`Set<String>?.shouldBackupTarget(target)` 子集备份） | `help/storage/Backup.kt` L314 |
| refgd | 备份主题包字体去重（manifest `themePackageFontDedupe.json`） | `help/storage/BackupThemePackageDedupe.kt` |
| youfengknight | **规则回收站**：8 类规则删除进回收站，`RETENTION_DAYS=7`，恢复可选覆盖/冲突检测/过期清理，默认关闭 | `help/source/SourceRecycleBinHelp.kt` + SourceRecycleBinDao |
| Suml-1 | **书源 URL 变更迁移书架书籍**：改域名弹窗询问 `update books set origin=:newUrl where origin=:oldUrl` | `data/dao/BookDao.kt:119` + `BookSourceEditActivity.kt` L655-678 |
| legados | Max 口令分享（链接转口令/读口令自动导入）+ 超大备份流式校验防 OOM | `utils/StringUtils.kt` L407-442 / `help/storage/Restore.kt` |

**本项目现状（源码核验）**：
- **备份按需选项目：已有且更完善**（`help/storage/BackupSelectorConfig.kt:18-55` **30 个 BackupItem** 分组"配置/数据库/其他"，`Backup.kt:415-588` 逐项勾选打包；书籍缓存还有独立 `BookCacheSelectorConfig.kt` 按书勾选）——refgd `shouldBackupTarget` 思路本项目已超集
- **备份流式读写：部分**（备份 `GSON.writeToOutputStream` 流式写 `Backup.kt:641-655`；恢复 `GSON.fromJsonArray(FileInputStream)` 流式读 `Restore.kt:321-339`；`ZipUtils.unZipToPath` 用 ZipInputStream 逐条写出防路径穿越 `:242-276`）；**无逐文件 CRC 校验/分片解压**
- **WebDAV：有备份/恢复/进度同步**（`AppWebDav.kt`：106-121 列备份、124-132 restoreWebDav、165-171 上传、244-278 **uploadBookProgress 阅读进度上传**、291-306 拉取、308-338 downloadAllBookProgress 批量合并）；**无删除/重命名**
- **无规则回收站**——缺口
- **书源 URL 变更迁移：无批量 SQL**；本项目是**逐本换源**（`ReadBookViewModel.kt:287-305 changeTo()` + `Book.kt:400-420 migrateTo()` 按章节标题/序号映射进度）——Suml-1 的批量方案可借鉴
- **无 S3、无主题字体去重、无口令分享**

**差异分析**：规则回收站（youfengknight）与书源 URL 批量迁移（Suml-1）是低风险高价值的数据安全增强；WebDAV 删除/重命名（Jingshiro）低成本可补；S3 引入 AWS SDK 依赖收益/成本不匹配。

### 领域 6：视频能力

> **V2 重点更正**：初稿误判本项目"无无缝切换/预加载"。经核验，本项目在订阅源视频嗅探、自动滚动/连续播放、播放器优化三方面**领先所有 fork**。下表先列本项目领先能力，再列 fork 侧可参考增量。

**本项目领先能力（源码核验，全部已在生产运行）**：

| 能力 | 说明 | 源码引用 |
|------|------|----------|
| **R5 WebView 嗅探** | `VIDEO_SNIFF_JS` **5 路 hook**（fetch/XHR/HTMLMediaElement.src/URL.createObjectURL/MediaSource.addSourceBuffer）+ Performance API 兜底；`VIDEO_SOURCE_REGEX` 覆盖 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd/video-tos/rtmp；shouldInterceptRequest 拦截动态请求 | `help/video/VideoUrlExtractor.kt:103,96,320` |
| **静态 5 法提取** | video/source 标签 → OG/Meta → script JSON → JS 变量 → 正则兜底，按精确度降序；含 MacCMS 指纹 + `player_aaaa` 变量识别、播放器页 URL 解析 `resolvePlayerPageUrl` | `VideoUrlExtractor.kt:354-372,378-391,397-414,420-429,436-445,550-565` |
| **FR-1 嗅探去重锁** | 同 URL 并发 WebView 嗅探复用 Deferred（ConcurrentHashMap），消除 41% 重复浪费 | `VideoUrlExtractor.kt:63-64,250-282` |
| **FR-8 play.php 预解析缓存** | play.php 类 URL 解析结果缓存 5 分钟，降低首帧延迟方差 7.5 倍 | `VideoUrlExtractor.kt:604-611,640` |
| **三层降级采集链** | 直通判断 → MacCMS 播放页解析（6s）→ DOM 复用 → WebView 抓包 → null（不把非视频 URL 传给播放器） | `VideoUrlExtractor.kt:529-539,627-671` |
| **ExoPlayer mimeType 嗅探** | `sniffVideoType` 三级证据（Probe > Magic > Content-Type），8KB Range 请求 + 重定向感知；**MimeSniffer 17 项 Magic Number 签名表** + LRU 缓存；m3u8 URL 短路跳过 Range | `help/exoplayer/ExoPlayerHelper.kt:333,422,489,553` + `help/exoplayer/MimeSniffer.kt:26,100` |
| **降级链 buildFallbackTypes** | 按嗅探结果排序（HLS/DASH/SS/Progressive 互降 + MP4 直链优先 Progressive），HTML mimeType 直接转 WebView | `help/gsyVideo/Exo2MediaPlayer.kt:221-269` |
| **指数退避重试** | 1s/2s/4s/8s/16s 最多 5 次；BUFFERING 超时降级（首 25s/续 12s）；不可恢复错误 ≥3 自动 WebView 降级；SSL 握手错误直降 WebView | `Exo2MediaPlayer.kt:784-810,1047-1064,851-945` |
| **FR-5 TTFB 自动降档** | 连续 3 次 >1000ms 自动降带宽档，<500ms 恢复，30s 防抖 | `Exo2MediaPlayer.kt:1119-1209` |
| **自动连播** | `onAutoCompletion → upDurIndex(1)` 播完自动下一集，边界检查+进度保存 | `help/gsyVideo/VideoPlayer.kt:360-363` + `VideoPlay.kt:916-932` |
| **上下滑动切换文章（自动滚动播放）** | ViewPager2 垂直布局，每 Fragment 一篇文章，`onPageSelected` 旧播器 deactivate/新 activate；触控判定优先于 GSY 手势 | `ui/video/VideoPlayerActivity.kt:429-450` + `ui/video/VideoFragment.kt:1141-1151` |
| **下一文章 HTML 预缓冲** | 播放进度 **80%** 自动预加载下一文章 HTML（`prebufferNextArticleHTML`） | `VideoPlay.kt:1263-1290` + `VideoFragment.kt:421-440` |
| **首帧/下一集预加载** | FirstFramePreloader（64KB 预热 + ±1 首帧，HIGH=10MB/MID=5MB 动态字节）；VideoPreloader（DataSpec 限量防 OOM） | `help/exoplayer/FirstFramePreloader.kt:36,172-212` + `VideoPreloader.kt:42,92-135` |
| **播放器实例池** | PlayerInstancePool（MAX_POOL_SIZE=3，acquire/recycle/clear，生命周期=Activity），快速滑动不重建 | `help/exoplayer/PlayerInstancePool.kt:44,122,168` |
| **统一视频缓存** | ExoPlayer SimpleCache 边下边播，容量可配（50-2048MB 默认 100），HTTP 416 清缓存重试 | `ExoPlayerHelper.kt:973-997,1132-1143` + `Exo2MediaPlayer.kt:754-777` |
| **防盗链与网络层** | Cronet 数据源（TLS 指纹对齐 Chrome）+ OkHttp 强制 HTTP/1.1 防 StreamReset + 浏览器 UA + 默认防盗链头 | `ExoPlayerHelper.kt:1009-1054,1075-1108` |
| **播放器全功能** | 悬浮窗（状态克隆转移）/全屏/0.5-15x 倍速/长按倍速/静音/±10-30s 快进/音轨选择/**Bili 弹幕**（seek+倍速联动）/**PiP**/四级降级链（Exo→重试→WebView+HLS.js→系统浏览器） | `FloatingPlayer.kt` + `VideoPlayer.kt:267-672` + `VideoPlayerActivity.kt:1431-1516,1637-1643` |
| **RSS 多线路/多集** | `ruleRoutes` 多线路 + `ruleEpisodes` 多集按需采集（`getRoutesContentAwait`），阅读页书籍视频同样走 `getDanmaku` | `model/rss/Rss.kt:153-236` + `VideoPlay.kt:607-670` |

**fork 侧功能（相对本项目缺口/差异）**：

| fork | 功能优点 | 源码引用 | 与本项目对比 |
|------|----------|----------|--------------|
| refgd | 视频无缝切换：预载下一集窗口 `preloadNextEpisode` L352 / `setupSeamlessTransitionListener` L794 | `model/VideoPlay.kt`（1038 行） | 本项目已实现"自动连播+下一集预加载（VideoPreloader）+80% 下一文章预缓冲"，连续播放体验同等级或更优；refgd 强调播放队列无缝过渡（无黑屏），本项目是整集切换+预加载，**无缝过渡体验可作 Evaluate 参考** |
| refgd | ExoPlayer 预加载：`preloadVideoWindow` L353 / `isVideoCached` L417 | `help/exoplayer/ExoPlayerHelper.kt`（639 行） | 本项目 FirstFramePreloader/VideoPreloader 已覆盖预加载思路，refgd 增加了"缓存命中判断"维度，**可 Evaluate** |
| Rimchars | 视频书籍预加载器（Semaphore 4 + 运行键去重） | `ui/video/VideoBookPreloader.kt` | 本项目视频书籍模式已走 ReadManga/VideoPlay 预加载链，思路重合 |
| Legado_Max | 视频悬浮窗系统媒体通知 | `ui/video/` | 本项目有悬浮窗但媒体通知实现独立，**可低成本 Evaluate** |

**结论**：本项目订阅源视频播放是**生态最强**（嗅探 5+5 路、降级链、自动连播、滑动切换、预缓冲、实例池、缓存、防盗链、弹幕、PiP 全栈自研并有 7 个 spec 沉淀）；fork 侧仅有 refgd 的"无缝过渡队列"与 Max 的"媒体通知"是相对增量。

### 领域 7：RSS 能力

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| huajideshutiao | **RSS 书籍化阅读**：RSS 文章按书阅读，JS 桥 `searchBook(key)`/`addBook(bookUrl)` | `ui/book/rss/ReadRssActivity.kt` + `ReadRssViewModel.kt` + `RssJsExtensions.kt` |
| Rimchars | **订阅搜索（单源）**：按 `searchUrl` 远程搜索（需源配置 searchUrl），`ui/rss/article/` 下独立入口 | `ui/rss/article/RssSearchActivity.kt` + `RssSortViewModel` |

**本项目现状（源码核验，视频/图片订阅源处理领先）**：
- **type 分发体系**：`ui/rss/read/ReadRss.kt:25-100` 按 `RssArticle.type`（**0 网页/1 图片/2 视频**）分发 → ReadRssActivity（WebView）/ ImageGalleryActivity（图片播放器）/ VideoPlayerActivity（视频播放器）；`readNoHtml` 直达播放器
- **视频源多线路/多集**：`RssSource.ruleRoutes` 多线路 + `ruleEpisodes` 多集 + 按需采集（`model/rss/Rss.kt:153-236`），配 `RssRouteAdapter`/`RssEpisodeAdapter`
- **图片源三层嗅探** + 垂直画布连续浏览（见领域 6/7 图片部分）
- **订阅源自动校验**：`service/CheckRssSourceService.kt`（5 维 + weight 回填）
- **跨源搜索（已领先）**：`model/rss/RssSearchModel.kt:46-319`（并发调度、30s 超时、去重、type 过滤）+ `ui/rss/search/RssSearchActivity.kt`（`docs/specs/rss-unified-search/` 已实施）——并发调所有源的 `searchUrl` 远程检索，聚合去重+换源，**功能为 Rimchars 单源搜索的超集**
- **无本地文章全文检索**（无 FTS）——非缺失项，Rimchars 的 RssSearchActivity 同样是 `searchUrl` 远程搜索（非本地全文），本项目跨源版已覆盖
- **无 RSS 书籍化阅读**（huajideshutiao 独有）——独立使用模式

**差异分析**：订阅搜索本项目已有跨源超集（Rimchars 单源搜索无需引入）；RSS 书籍化是独立使用模式需评估产品契合度。

### 领域 8：阅读功能

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| Jingshiro | **详细阅读记录**：会话级 startTime/endTime/readIteration，2 分钟最短会话/3 分钟合并窗口/N+1 优化，内置 WebView 可视化 + Web API | `data/entities/DetailedReadRecord.kt` + `help/readrecord/DetailedReadRecordHelper.kt` L14-177 + `ui/about/ReadRecordActivity.kt` + `ReadRecordWebActivity.kt` |
| Jingshiro | **想法批注**：长按选文创建 BookThought（下划线样式按列绘制），分享卡片/图片导出/**Obsidian 导出**（REST API+本地双模式） | `data/entities/BookThought.kt` + `TextLine.kt` L259-344 + `ThoughtObsidianExporter.kt` |
| Jingshiro | **阅读书票**：尾页完读自动弹藏书票/收据（评分+时长+笔记数+完读评价） | `ui/book/read/page/provider/BookplateDrawer.kt` L36-531 + `TextPageFactory.kt` 状态机 |
| Jingshiro | **高亮规则引擎**：捕获组样式解析 + 400 万字符 LRU 缓存 + CSS 解析器 + `<fontsize_N>` 字号 span 修复 | `help/book/ContentProcessor.kt` L348-413 + `utils/CssStyleParser.kt` + `TextChapterLayout.kt` L1571-1610 |
| Jingshiro | 阅读轮次标签（读完/N 刷 readIteration）+ 主题导出（FullTheme JSON+资源 zip） | `help/book/ReadIterationHelper.kt` + `help/config/ThemeExportHelper.kt` |
| legados | **书架显示阅读进度**（`readProgress()` 进度条+百分比，默认关）+ 阅读成就 21 档 + 特殊内容保护（`<usehtml>`/`<img>`/`[newpage]` 占位符）+ 阅读时间"X天Y小时" | `help/book/BookExtensions.kt` L389 + `ui/book/readRecord/ReadAchievementActivity.kt` + `help/book/SpecialContentProtector.kt` |
| HapeLee | **智能分组**：在读-20/未读-21/已读-22 自动插入（`IdReading`/`IdUnread`/`IdReadFinished`）+ `Book.remark` 字段 + DPAD 键盘映射 + 阅读会话统计 | `data/AppDatabase.kt` L284-313 + `BookGroup.kt` L40-42 + `ReadBookController.kt` L1389-1397 |
| 325506 | **WebDav 阅读进度同步** | `WebDavReadingProgressRepository.kt` L8-26 |
| legado_NG | **TTS 路由器体系**：能力注册/引擎存储/脚本引擎/WebSocket 引擎/HTTP 转发/流式音频/SoundTouch 变速/引擎模型选择 | `help/tts/ReadAloudTtsRouter.kt`（`route()` L36 / `globalScriptNarratorEngine()` L238） |
| Rimchars | 朗读会话 + TTS 队列窗口 + 角色缓存预热 | `service/BaseReadAloudService.kt`（`beginReadAloudSession` L200 / `prewarmNextChapterRoleCache` L735）+ `service/TtsQueueWindow.kt` |
| Legado_Max | 阅读记录四视图+热力图日历 + 目录渐进/不完全加载 | `ui/book/readRecord/` + `model/webBook/BookChapterList.kt` |

**本项目现状（源码核验）**：
- **划线/批注：已有基础体系**（实体 `BookHighlight` 表 `highlights`，`data/entities/BookHighlight.kt:20-55`；长按选文菜单 `HighlightActionMenu.kt`/`TextActionMenu.kt`；**下划线 5 种渲染** SOLID/DOUBLE/DASHED/DOTTED/WAVY + 着重号/删除线/方框，`ui/book/read/page/HighlightDraw.kt:63-117`）——Jingshiro 想法批注的**分享卡片/图片导出/Obsidian 导出**是相对增量
- **高亮规则引擎：已有独立实现**（`help/HighlightRuleMatcher.kt:8-64` + `ui/book/read/config/HighlightRule.kt` + `ReadBook.kt:272-306 ruleMatchesOfChapter` 整章排版后匹配 + `help/HighlightStyle.kt`）——与 Jingshiro 的 ContentProcessor/CssStyleParser 实现不同但能力等价；Jingshiro 的**捕获组样式（$N）解析**是相对增量
- **阅读记录：按日聚合 + 按书汇总**（`readRecordDetail` 表按 (deviceId,bookName,bookAuthor,date) 聚合，`ReadRecord.kt:10-31`；`ui/about/ReadRecordActivity.kt` 列表展示）——**无会话级 startTime-endTime、无图表/热力图可视化**（Jingshiro 相对增量）
- **目录渐进加载/懒加载：已有**（`BookChapterList.kt:69-121` 多页抓取+并发解析；`ReadBook.kt:630-655` 前后章懒加载；书源下一页 `ReadBookViewModel.kt:331-338`）——Max 该能力已覆盖
- **WebDAV 阅读进度：已有**（`AppWebDav.kt:244-338` uploadBookProgress/downloadAllBookProgress 批量合并）——325506 该能力已覆盖
- **无阅读书票、无阅读轮次标签、无智能分组、无书架阅读进度条、无 TTS 路由器、无云 TTS Provider、无章节翻译、无阅读成就**——以上为缺口
- 自动翻页/滚屏：**已有**（`page/AutoPager.kt` + 7 种翻页动画 delegate + TTS 双引擎）

**差异分析**：特殊内容保护（legados，41 行）与书架阅读进度（legados）是低成本高价值；智能分组（HapeLee）涉及 DB 迁移+书架联查；高亮规则引擎/想法批注本项目已有基础，可只借鉴增量（捕获组样式/Obsidian 导出）；详细阅读记录会话级是中等规模（新表+采集器）。

### 领域 9：性能稳定性

| fork | 功能优点 | 源码引用 |
|------|----------|----------|
| Rimchars | **搜索结果存储字节上限**：`MAX_STORED_ROW_BYTES=512KB` 防 CursorWindow 单行超限崩溃 + 各字段逐项上限 | `data/entities/SearchBookStoragePolicy.kt` |
| Rimchars | WebView 池化（作用域化复用）+ 同步进度/安全封面（relay 系） | `help/webView/WebViewPool.kt` |
| legados | **运行时内存压力监控**：`shouldTrimNow()`/`throttleTrim()`（1.5s 节流），低内存降 Glide 缓存 | `help/MemoryPressure.kt`（90 行） |
| legados | 超大备份流式校验/分批导入防 OOM | `help/storage/Restore.kt` |
| Suml-1 | SQL 聚合重构消除全量加载 + 滚动翻页跳变修复 + OPPO ColorOS AlertDialog 修复 | `data/dao/ReadRecordDao.kt` |
| HapeLee/325506 | search page 正则崩溃修复（顶层 regex 保护） | `SearchBooksUseCase.kt` L382-399 / L302-319 |

**本项目现状（源码核验）**：
- **无搜索存储字节上限**（`SearchBookStoragePolicy` 不存在；搜索结果全量驻内存 `SearchModel.kt:32-234`）——缺口
- **无内存压力监控**（无 `MemoryPressure`，无 App 级 `onTrimMemory`）——缺口
- **备份流式：有**（`ZipUtils.unZipToPath` ZipInputStream 逐条 + 路径穿越防护 `:242-276`；JSON 流式读写 `Restore.kt:321-339`）；**无逐文件 CRC/条目上限**——部分
- **稳定性 spec 体系强**：`app-stability-round2`（SQLiteBlobTooBig/P1-1 等）、`exoplayer-resilience`（MimeSniffer+≥3 自动降级）、`network-perf-stability`（22 项优化/190 勾选）、`thread-pool-audit`/`thread-pool-split-config`（线程池审查+拆分配置）、`rss-cache-first`/`rss-parse-optimization`/`rss-concurrency-and-checksource-optimization`、`bugfix-20260730-batch1` 等
- 搜索正则崩溃：本项目无 `SearchBooksUseCase` 分页结构，搜索走 `SearchModel`，无同类正则问题

**差异分析**：搜索存储字节上限（Rimchars，防 CursorWindow 崩溃）与内存压力监控（legados，90 行低侵入）是防崩溃型低风险改进；两者均已有生产验证可直接移植思路。

---

## 三、特殊仓库专项说明

### gedoor_legado（原版）— N/A
- 2026-05-27 起仓库仅保留 README 侵权公告，**无任何源码**（HEAD 9bb0569）。原版能力以本项目 fork 源 legado-E 及主流 fork 共同代表，无需也无法单独分析。

### mgz0227_legado-Harmony（鸿蒙）— 跨平台工程
- 为 ArkTS/HarmonyOS 工程（AppScope/hvigor/oh-package.json5），非 Android `app/` 结构；README 声明**不再开源仅发布 HAP**。与 Android 生态无代码级可比性，**不纳入 9 领域对比**，仅作工程形态记录。

### legado-archive（私仓 release-only）— 仅记录
- Rimchars/legado-private-armv8-release，无源码，不在分析范围（此前 forks-archive-comparison 已深度分析 Archive 本体）。

---

## 四、核心结论

1. **功能密度排序**：legados（辞晨Max）> Rimchars（Archive）> Jingshiro > legado_NG/MD3 系 > Max 系（蛋蛋/怣疯/Suml-1）> 主流系（喵公子/阅读T/🍟）
2. **本项目生态定位：视频/图片播放与嗅探最强**——R5+静态双嗅探、三层降级、mimeType 嗅探、自动连播+滑动切换+80% 预缓冲、实例池、缓存、防盗链、弹幕、PiP 全栈自研；**订阅源内嵌播放器方向无需借鉴任何 fork**
3. **AI 是各 fork 最大创新密集区**（Rimchars Agent / Jingshiro 助手 / NG MCP / HapeLee 翻译+云TTS），按用户指示暂不接入，仅存档事实
4. **网络层增量集中在 4 个 fork**：legadoT（Brotli+日志）、legado_NG（日志脱敏）、LegadoTeam（resolveIp）、Suml-1（SSL 提示）；其中 307/308 本项目已覆盖
5. **规则引擎突破仅 legados**：JS 单文件书源 + CryptoJS 内置是唯一突破声明式限制的实现；CryptoJS 是纯增量最高价值项
6. **性能稳定性增量分散**：Rimchars（存储上限）、legados（内存压力监控）、Suml-1（SQL 聚合）互为补充，均为低风险
7. **阅读功能本项目已有强基础**（划线 5 种渲染/高亮规则引擎/阅读记录/目录渐进加载/WebDAV 进度），借鉴应聚焦增量（捕获组样式、Obsidian 导出、会话级记录、书架进度、智能分组）
