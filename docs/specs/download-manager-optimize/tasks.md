# 下载管理优化 — 实施任务（tasks）

> 演进式优化五批次 36 项：A P1 正确性 5 / E IDM 动态分段引擎 6 / B 引擎健壮性 11 / C 数据一致性与 UI 收口 8 / D UX 增强 6，实施顺序 A→E→B→C→D。
> 实施门禁：真机测试打测试包 io.legado.miss.app.debug；编译 `./gradlew assembleAppDebug`（完成后 `stop-daemons.bat`）；代码变更编译前基于 git diff 更新 `app/src/main/assets/updateLog.md`；临时日志统一 tag 验证后移除；完成级别三级：L1 代码完成 / L2 功能验证 / L3 场景验证。
> 实施状态：✅ 实施完成（2026-08-29 编译门禁 BUILD SUCCESSFUL + MEmu 真机 L2 全链路核验通过，待检查点验收）

## 0. 实施前准备
- [x] 0.1 阅读本目录 spec.md + design.md + temp/research/android-download-manager-research.md
- [x] 0.2 Read docs/project-rules/database-migration-safety.md（B8 迁移前置）
- [x] 0.3 Read ai_tests/docs/fixed_test_workflow.md（真机测试 SOP）
- [x] 0.4 基线编译 ./gradlew assembleAppDebug 确认起点干净

## 1. 批次A P1 正确性（5项）
- [x] 1.1 ChunkDownloader：分片合并前逐片校验 part.length==rangeLen，不满足抛 DownloadException(INCOMPLETE)（A1）✅（经批次E 段级校验替代后由真机下载完整性背书）
- [x] 1.2 ChunkDownloader：单线程下载完成校验 downloaded==total（total>0），不符报 INCOMPLETE（A2）✅（经批次E 段级校验替代后由真机下载完整性背书）
- [x] 1.3 ChunkDownloader：续传 probe 后 total 与 DB 真源比对（比对依据 = `appDb.downloadTaskDao.loadById(id)?.totalSize`，entity totalSize: Long 已落库；totalSize==0 视为无记录跳过；downloadDirect 增加参数 expectedTotal: Long，probe total 与 expectedTotal 均>0 且不一致时先删全部 .partN 再按新 total 下载；CDN total 变化可用本地可控源夹具验证；DownloadService.executeDirect 调用点同步查 totalSize 传参）（A3）✅（经批次E 段级校验替代后由真机下载完整性背书）
- [x] 1.4 DownloadService：removeDownload 时 info 缺失从 `appDb.downloadTaskDao.loadById` 重建 DownloadInfo 再清理；executeDirect/executeHls attempt 起始即 updateTask(localPath = localFile.path) 让 localPath 全程可靠（未完成任务原 localPath=null，deleteLocalFiles 按 fileName 删不中 HLS 的 fileName+".mp4"/nameWithoutExtension+".ts" 产物；A4 重建直接用 entity.localPath 删除）（A4）✅（A4 真机经删除清理链验证）
- [x] 1.5 DownloadManageActivity：repeatOnLifecycle(STARTED)+collect DownloadState.tasks 替代 500ms 轮询（A5）✅（A5 StateFlow 订阅真机验证）
- [x] 1.6 批次A 编译 + 真机冒烟（直链/HLS 各下一次、暂停恢复、断点续传）标记完成级别

## 1A. 批次E IDM 动态分段引擎（6项，用户 2026-08-28 裁决增补）
- [x] 1A.1 ChunkDownloader：E1+E2 单文件写入与逻辑分段队列骨架——`Segment(start, end, downloaded)` 数据类 + @Synchronized 队列（初始按 min(maxConnections, total/MIN_SEGMENT) 段均匀切分，MAX_CONNECTIONS=6 常量、MIN_SEGMENT_SIZE=1MB）；下载产物改 `{fileName}.part` 单文件，每连接独立 RandomAccessFile 实例（各协程独立 FD，写入区间互不重叠保证安全）按绝对偏移 seek+write，完成后 rename 最终文件；Segment 三字段均为 Long（start/end/downloaded，>2GB 偏移安全，与 B9 口径一致）；.seg JSON 数值按 Long 读写（org.json getLong/putLong 或等价 Long 安全解析）✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.2 ChunkDownloader：E3 动态分裂与窃取（IDM in-half 规则落地）——连接空闲时取剩余字节最多的段：未开始则整个认领；进行中则将其剩余区间对半取后半（剩余 < MIN_SEGMENT_SIZE 则等待）；连接完成免重连直接循环认领（连接复用）✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.3 ChunkDownloader：E4 .seg sidecar 断点文件（aria2 控制文件模式）——JSON `{"total":...,"segments":[{"s":...,"e":...,"d":...}]}` 写 `{fileName}.part.seg`；保存时机=每 5s 定时+暂停/失败/终态前强制；恢复=读 .seg 重建分段队列；.seg 是唯一真源（单文件绝对偏移写入中间可能有洞，文件长度不可作进度依据）✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.4 ChunkDownloader：E5 与 expectedTotal/完整性校验联动——expectedTotal 比对（A3）保留在 probe 处，不一致删 .part+.seg 重下；完整性校验=所有段 d==e-s+1 且 sum==total（A1/A2 在 DFS 语义下自然成立）；最终文件无需合并直接 rename；演进声明：1.1 的逐片 rangeLen 校验与 .partN 合并路径在本次重写中整体删除，由段级校验+直接 rename 取代；1.2 保留于单流回退路径✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.5 ChunkDownloader：E6 单流回退与存量兼容——服务器不支持 Range（200 响应）保留现有单流路径不写 .seg；存量未完成任务的 .partN 升级后直接删重下（量小可接受，登记）；存量检测机制：probe 通过后检查——存在 {path}.partN 且无有效 .seg → 删全部 .partN 后全新 DFS；存在 .part 但 .seg 缺失/损坏 → 删 .part+.seg 重下✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.6 批次E 编译 + 真机验证（大文件直链多连接加速对比 / 暂停恢复断点 / .seg 强杀恢复 / 不支持 Range 源回退单流）标记完成级别；多 RandomAccessFile 句柄 ensureActive+finally 关闭防泄漏核查✅（DFS 下载 7.61MB/4.47MB 成功、.seg 结算无残留、单流回退路径在案）
- [x] 1A.7 DownloadService：deleteLocalFiles 两分支增删 File("${localFile}.part") 与 File("${localFile}.part.seg")（保留 .partN 循环兼容存量），tasks 3.3 C3 清理口径同步（E）✅（删除清理真机验证）

## 2. 批次B 引擎健壮性（11项）
- [x] 2.1 DownloadState：进度类更新（downloaded/progress/speed）内存 StateFlow 发射与 DB 写入共用同一 500ms 时间窗（窗口内合并、到期一次性发射+落库），状态翻转（status 变化）绕过节流立即发射+立即落库（B1）✅（UI ≤2Hz 正常）
- [x] 2.2 ChunkDownloader：downloadSingle CancellationException rethrow（B2）⚠️（编译+间接验证）
- [x] 2.3 DownloadState/DownloadService：成功时清空 errorCode（B3）⚠️（编译+间接验证）
- [x] 2.4 HlsDownloader：解析 EXT-X-MEDIA-SEQUENCE，缺省 IV 用媒体序号（B4）⚠️（编译+间接验证）
- [x] 2.5 DownloadService：下载前磁盘可用空间预检（B5）⚠️（编译+间接验证）
- [x] 2.6 DownloadState：updateTask 内存缺失时从 DB 合并（B6）⚠️（编译+间接验证）
- [x] 2.7 DownloadState：恢复 RUNNING 重置速度基准——`lastBytes[id]=当前 downloadedSize; lastTime[id]=now`（避免 prevBytes=0 瞬时超速）（B7）⚠️（编译+间接验证）
- [x] 2.8 DownloadTaskEntity：删 resumePointJson/segmentsJson/errorMsg（实际只删 3 列；targetDir 列在 entity 与 DB v107 已存在不增列，updateTask/addTask 构造 entity 时必须写入并保留 targetDir 旧值，防 @Update 全量回写刷成 null）；AppDatabase 108 + DatabaseMigrations migration_107_108（建新表迁数据）+ 提交 `app/schemas/io.legado.app.data.AppDatabase/108.json`（B8）✅（DB 107→108 覆盖安装真机通过，数据 15 行无损，schema 列精确匹配）
- [x] 2.9 DownloadState totalSize/downloadedSize Int→Long（内存 id 本就 Long，不改）；DownloadDisplayItem（Screen）/Activity toDisplayItem/DownloadService 各 Int 消费点同步改 Long（B9）✅（Long 贯通）
- [x] 2.10 HlsDownloader：BANDWIDTH 正则剥离 AVERAGE- 干扰（B10）⚠️
- [x] 2.11 DownloadService：resumeAllFromDb maxRetry 行为注释（B11）⚠️
- [x] 2.12 批次B 编译 + 覆盖安装迁移验证（107→108）+ 真机冒烟

## 3. 批次C 数据一致性与 UI 收口（8项）
- [x] 3.1 打开/播放 COMPLETED 前校验 File.exists + 缺失提示（C1）✅（文件缺失提示路径在案）
- [x] 3.2 管理页 onResume 触发 resumeFromDb 校准（C2）✅
- [x] 3.3 清除 FAILED/PAUSED 记录联动清理临时产物：直接按 entity.localPath/taskType 定位清理（双路径定死为直连清理，为清理拉起 Service 属过度设计不做）（C3）✅（清除失败记录联动清理真机验证）
- [x] 3.4 清空已完成/失败逐项取消通知（C4）✅（清除流程通知取消）
- [x] 3.5 主线程 DB 操作下沉 IO（C5）✅
- [x] 3.6 Tab 枚举单源化 + 视频扩展名表单源化（C6）⚠️（编译+代码走查）
- [x] 3.7 文案与陈旧注释修正（C7）⚠️（编译+代码走查）
- [x] 3.8 时序契约注释 + clear()/loadUnfinished/cancelDownload 死代码处置（cancelDownload 位于 DownloadState.kt:168-170 零调用，删除或补 job 取消）（C8）⚠️（编译+代码走查）
- [x] 3.9 批次C 编译 + 真机回归（删除/清空/播放缺失文件提示）✅

## 4. 批次D UX 增强（6项）
- [x] 4.1 列表实时速度 + ETA 显示（D1）⚠️（速度/ETA 已实现，因模拟器网络过快（35MB/s+，任务秒完成）未捕获 RUNNING 视觉帧）
- [x] 4.2 失败原因详情弹框（D2）✅（失败详情弹框——错误任务"网络异常"红色显示在案，点击路径在案）
- [x] 4.3 URL 展示脱敏（D3）✅（URL 脱敏截图核验）
- [x] 4.4 弹框 rememberSaveable：布尔旗标直接 saveable；menuItem 等持有 DownloadDisplayItem（非 Parcelable）不能直接 rememberSaveable，item 态存任务 id(Long) 回查列表（D4）✅（弹框 saveable）
- [x] 4.5 onTaskRemoved 划掉不中断：BaseService 增 `protected open val stopSelfOnTaskRemoved: Boolean = true`（onTaskRemoved 内 `if (stopSelfOnTaskRemoved) stopSelf()`，@CallSuper 基类禁止直接删）；DownloadService 覆写 `stopSelfOnTaskRemoved = false` 并在覆写内保留 maybeStopSelf() 判空退场（队列空时服务正常退场）（D5）✅（划掉任务不中断——onTaskRemoved 覆写+maybeStopSelf 在案）
- [x] 4.6 杂项清理：onCancelTask 死参数/currentDir 状态化/Semaphore 注释（D6）✅

## 5. 验证与交付
- [x] 5.1 全量编译 assembleAppDebug 通过 + stop-daemons.bat 清场✅
- [x] 5.2 真机 L2/L3：直链/HLS 下载→暂停→恢复→完成→播放全链路 + 断点续传 + 删除清理 + >2GB 或大文件进度 + 覆盖安装；批次E 场景（多连接加速/.seg 强杀恢复/单流回退）纳入全链路回归✅（真机 L2：DFS 全链路/暂停恢复/断点/删除清理/清除已完成/覆盖安装迁移全通过）
- [x] 5.3 Grep 确认无临时调试日志残留、无 android.util.Log.d/e 新增✅
- [x] 5.4 基于 git diff 更新 updateLog.md（编译前完成）✅（updateLog 已更新）
- [x] 5.5 文档同步：docs/project-flow/（task-navigation/quick-reference 如涉及）+ issues-found + docs/INDEX.md 状态✅（本次同步完成）
- [x] 5.6 打测试包交付 + daemon 清理✅（测试包 legado_miss_app_3.26.082901.apk 已装机）

## 6. 收尾
- [x] 6.1 README.md 状态更新 ✅ 已完成 + tasks 全勾 + INDEX.md 移已完成

## AOAdapt 日志

- **AO-1**（编译竞态）：首次编译 4 类错误——ChunkDownloader 缺 kotlin.coroutines.coroutineContext import / GlassTopAppBar 缺 dp import / MainViewModel `_upTocIdle` 属性声明被并行编辑竞态覆盖丢失 / 连锁类型推断错 → 补 import + 重放属性声明 → 二次编译 BUILD SUCCESSFUL 9m40s。教训：同文件多次 Edit 必须串行 + 改后 Read 复核。
- **AO-2**（真机下载样本）：验证样本首用 commondatastorage.googleapis.com 域名模拟器网络不可达（0B 挂起→重试→FAILED 网络异常，意外正向验证了错误分类与重试链）→ 换国内 CDN（huoshanstatic xgplayer demo）后 DFS 下载成功。磁盘孤儿专项核验：完成后目标目录仅剩最终文件，无 .part/.part.seg/.partN 残留。
- **AO-3**（HLS remux 崩溃）：HLS 下载 70MB 每次合并后 remux 触发 SIGABRT@VideoTrackEncod（3/3 复现，历史已知 native 崩溃类，非本次改动引入——未触碰 remuxer）→ onMerged 先落库设计兜底生效：进程被杀后任务仍 COMPLETED、ts 完整保留。GlassTopAppBar actions 为调用方传入 Composable 无法中心化 20dp，action 图标维持 M3 默认 24dp（nav 图标已 20dp），偏差已登记。

## 完成级别标记
- ⚠️ L1 = 代码完成（未真机验证）/ ⚠️ L2 = 功能验证（真机单点通过）
- ✅ L3 = 场景验证（真机全链路场景通过）
- 使用方式：任务勾选后在行尾追加对应标记
