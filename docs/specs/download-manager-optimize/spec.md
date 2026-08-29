# download-manager-optimize — 下载管理优化（OpenSpec Spec）

> 日期：2026-08-28 ｜ 依据调研：`temp/research/android-download-manager-research.md` ｜ 涉及：视频 HLS/直链下载引擎 + 下载管理页

## Intent

在不引入第三方库、不重写引擎的前提下，演进式修复下载管理正确性缺陷（P1）、补齐健壮性与数据一致性（P2）、增强管理页 UX（P3），消除"下载成功但文件损坏 / 孤儿文件 / 状态不一致"三类核心问题。

## Scope

### In Scope

#### 批次A P1 正确性（5项）

| # | 条目 | 现状锚点 |
|---|------|---------|
| A1 | 分片合并前校验 `part.length == rangeLen`，不满足抛 INCOMPLETE 重试 | ChunkDownloader.kt:135-140 现状只查存在非空 |
| A2 | 单线程下载完成后校验 `downloaded == total`（total>0 时），提前 EOF 报 INCOMPLETE | ChunkDownloader.kt:206-226 |
| A3 | 续传恢复时 probe 的 total 与 DB 真源比对（比对依据 = `appDb.downloadTaskDao.loadById(id)?.totalSize`，entity totalSize: Long 已落库；`totalSize==0` 视为无记录跳过；`downloadDirect` 增加 `expectedTotal: Long` 参数，probe total 与 expectedTotal 均>0 且不一致时先删全部 .partN 再按新 total 下载），消除 CDN total 变化导致错位拼接坏文件 | ChunkDownloader.kt:104-131 |
| A4 | removeDownload 时内存 downloadInfos 缺失则从 DB entity 重建 DownloadInfo 再清理文件（`executeDirect`/`executeHls` attempt 起始即 `updateTask(localPath = localFile.path)` 让 localPath 全程可靠；未完成任务原 localPath 为 null，deleteLocalFiles 按 fileName 删不中 HLS 的 fileName+".mp4"/nameWithoutExtension+".ts" 产物，重建后直接用 entity.localPath 删除），消除 Service 重建后"删记录留孤儿文件"；批次窗口说明：A4（批次1）先于 B8（批次2），targetDir 落库前 A4 重建清理只能落 resolveTargetDir 当前配置目录，改过目录的存量任务存在漏删窗口（正确性大头已修，可接受） | DownloadService.kt:450-456 |
| A5 | 管理页改订阅 DownloadState.tasks StateFlow（collectAsStateWithLifecycle + repeatOnLifecycle），删除 500ms 轮询循环，解决后台不暂停/进度不实时 | DownloadManageActivity.kt:108-126 |

#### 批次B 引擎健壮性（P2，11项）

| # | 条目 | 现状锚点 |
|---|------|---------|
| B1 | 进度落库节流：进度类更新（downloaded/progress/speed）的内存 StateFlow 发射与 DB 写入共用同一 500ms 时间窗（窗口内合并、到期一次性发射+落库），状态翻转（status 变化）绕过节流立即发射+立即落库，大文件消除数万次同步写库 | DownloadState.kt:127-143 |
| B2 | downloadSingle 的 runCatching 对 CancellationException 直接 rethrow（对齐 downloadChunked/HlsDownloader 行为） | — |
| B3 | 任务成功时清空 errorCode（当前 `?: old.errorCode` 永不清理） | — |
| B4 | HLS AES-128 缺省 IV 改用媒体序号（解析 #EXT-X-MEDIA-SEQUENCE，IV=seq+i），修复非 0 起始清单解密乱码 | — |
| B5 | 下载前磁盘可用空间预检（直链 total 与 HLS 分片+目标双份空间），不足报 IO 错误 | — |
| B6 | updateTask 内存缺失时从 DB `appDb.downloadTaskDao.loadById` 合并后再更新，消除静默丢状态 | — |
| B7 | 恢复 RUNNING 时重置速度计算时间基准（`lastBytes[id]=当前 downloadedSize; lastTime[id]=now`，避免 prevBytes=0 瞬时超速） | — |
| B8 | 僵尸字段处置：删除 resumePointJson/segmentsJson/errorMsg（零写入，实际只删 3 列；targetDir 列在 entity 与 DB v107 已存在，"落库"是 updateTask/addTask 代码写入行为，构造 entity 时必须写入并保留 targetDir 旧值，防 @Update 全量回写刷成 null）；DB 107→108 手动 Migration（按 database-migration-safety.md 规范，迁移产物 app/schemas/io.legado.app.data.AppDatabase/108.json 需提交） | — |
| B9 | 内存 DownloadTask totalSize/downloadedSize Int→Long（>2GB 截断） | — |
| B10 | BANDWIDTH 正则修复：剥离 AVERAGE-BANDWIDTH 干扰 | HlsDownloader.kt:339 |
| B11 | resumeAllFromDb 丢失 maxRetry 行为补注释说明 | — |

#### 批次C 数据一致性与 UI 收口（P2，8项）

| # | 条目 |
|---|------|
| C1 | COMPLETED 任务打开/播放/resumeFromDb 恢复时校验 File.exists()，缺失提示并可清理记录 |
| C2 | 管理页 onResume 触发 resumeFromDb 校准（补 RUNNING 残留恢复触发点） |
| C3 | 清除 FAILED/PAUSED 记录时联动清理 .part/.seg/.partN/HLS tempDir 临时产物 |
| C4 | 清空已完成/失败时逐项取消通知 |
| C5 | 主线程 DB 操作下沉 IO（resumeFromDb/deleteTask/clearCompletedTasks） |
| C6 | Tab 枚举单源化（Activity 与 Screen 双份裸 Int 对齐）；视频扩展名表单源化（双份维护） |
| C7 | 文案修正"清除已完成"→"清除已完成/失败"；clearCompletedTasks 陈旧注释更新 |
| C8 | 删除进行中任务"先 pause 后 remove"时序契约补注释；clear() 死代码处置（删除或补 job 取消）；loadUnfinished 死方法删除 |

#### 批次D UX 增强（P3，可选项，6项）

| # | 条目 |
|---|------|
| D1 | 列表显示实时速度 + 剩余时间（ETA） |
| D2 | 失败原因点击查看完整错误详情弹框 |
| D3 | 任务 URL 展示脱敏（域名保留、路径参数隐藏） |
| D4 | 弹框状态 remember→rememberSaveable（旋转屏保持） |
| D5 | onTaskRemoved 划掉最近任务不再中断下载（移除 stopSelf，任务落库自动恢复） |
| D6 | 死参数/杂项清理（onCancelTask 死参数、currentDir 每次重组重读、Semaphore FIFO 注释失实） |

#### 批次E IDM 动态分段引擎（P2，用户 2026-08-28 裁决增补）

> 背景：现有 ChunkDownloader 是静态物理 3 分片（probe 后固定切 3 段 Range 各写 .partN），段间负载不均、连接不复用。IDM 核心=动态文件分段（DFS）：新连接空闲时找最大段对半分裂、完成的连接免重连认领剩余区间。业界印证：NDM（IDM 平替）同算法 32 连接；Kotlin 生态 KDownloader 实现"IDM-style dynamic range theft"；Downpour（2026 活跃）自适应并发。本批次将直链引擎升级为真 IDM 动态分段（ChunkDownloader 内重写直链路径，约 300 行）。

| # | 条目 |
|---|------|
| E1 | 单文件+绝对偏移写入：下载产物 `{fileName}.part`，每连接独立 RandomAccessFile 实例（各协程独立 FD，写入区间互不重叠保证安全）按绝对偏移 seek+write，完成后 rename 最终文件 |
| E2 | 逻辑分段队列：内存 `Segment(start, end, downloaded)` 队列（@Synchronized 保护）；初始按 min(maxConnections, total/MIN_SEGMENT) 段均匀切分；`MAX_CONNECTIONS = 6` 常量、`MIN_SEGMENT_SIZE = 1MB`（小于不分裂，连接数设置项列 P3）；Segment 三字段均为 Long（start/end/downloaded，>2GB 偏移安全，与 B9 口径一致）；.seg JSON 数值按 Long 读写（org.json getLong/putLong 或等价 Long 安全解析） |
| E3 | 动态分裂与窃取（IDM in-half 规则落地）：连接空闲时取剩余字节最多的段——未开始则整个认领；进行中则将其**剩余区间对半**取后半（剩余 < MIN_SEGMENT_SIZE 则等待）；连接完成免重连直接循环认领（连接复用） |
| E4 | .seg sidecar 断点文件（aria2 控制文件模式）：JSON `{"total":..., "segments":[{"s":...,"e":...,"d":...}]}` 写 `{fileName}.part.seg`；保存时机=每 5s 定时+暂停/失败/终态前强制；恢复=读 .seg 重建队列；.seg 是唯一真源（单文件绝对偏移写入中间可能有洞，文件长度不可作进度依据） |
| E5 | 与批次A 校验联动：expectedTotal 比对（A3）保留在 probe 处，不一致删 .part+.seg 重下；完整性校验=所有段 d==e-s+1 且 sum==total（A1/A2 在 DFS 语义下自然成立，最终文件无需合并直接 rename） |
| E6 | 单流回退与存量兼容：probe 后仅当 range==true 且 total>0 时进入 DFS；以下情形一律回退单流且不写 .seg：(1) 200 响应（不支持 Range）；(2) 206 但 Content-Range 无有效总长（如 bytes 0-0/*）或 total≤0（chunked/未知长度）。E2 初始切分前置门禁：total>0 才切分，保证 min(maxConnections, total/MIN_SEGMENT_SIZE) ≥ 1。存量未完成任务的 .partN 升级后直接删重下（量小可接受，登记） |

不做：不引入 Room chunk 表（aria2 双表模式仍 Out of Scope）；HLS 引擎不动（m3u8 分片天然并行）；自适应并发（Downpour 式吞吐监测调连接数）列远期 Out of Scope；连接数设置项列 P3 远期。

### Out of Scope（明确不做+理由）

| 不做项 | 理由 |
|--------|------|
| 引入第三方下载库（OkDownload/FileDownloader） | 停更 2019/2018，引入回归风险与依赖债 |
| 引入 Fetch | 已知速度回退（#690），需自测成本高 |
| 迁移 Media3 DownloadManager | 面向流媒体离线缓存，与任意文件+自管存储定位不符 |
| aria2 式 chunk 双表重构（task+chunk 双表） | 现有磁盘真源续传已闭环，重构收益<风险，列远期 |
| 限速/多镜像/endgame/下载后处理钩子 | P3 远期，当前无用户诉求 |
| 批量操作（多选/全部暂停恢复） | 列待扩展不实施 |
| 书籍下载 CacheBook 体系 | 不在本特性范围，不动 |
| Media3 播放链路 | file:// 修复已闭环，不动 |
| O-ENG-14 多 #EXT-X-KEY 换 key 清单 | 当前仅取首个 KEY，分段换 key 解密失败，列远期 |
| O-ENG-18 HLS 分片 403 无二级回退 | 备用头重试，列远期 |
| 自适应并发（Downpour 式吞吐监测动态调连接数） | 列远期 |

## Approach

### Selected Approach

演进式优化现有自研引擎：批次A→E→B→C→D 顺序实施（A 先堵正确性漏洞，E IDM 动态分段引擎，B 引擎健壮性，C 一致性收口，D UX 增强）。

理由：现有架构（Room 主存 + StateFlow 缓存 + 磁盘真源续传 + 错误码驱动重试）经深度分析整体成熟度良好、历史铁证坑已闭环，48 项（批次内 36 项：A5/E6/B11/C8/D6）待优化中无一项需要推翻架构；演进式改动可控、可逐批验证、DB 仅一次迁移（107→108）。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 引入 Fetch/OkDownload/FileDownloader | 停更或已知 bug（Fetch #690 速度回退、OkDownload/FileDownloader 停更 2019/2018），引入回归风险与依赖债 |
| 迁移 Media3 DownloadManager | 定位是流媒体离线缓存（数据进 Cache），任意文件下载/HLS 任意源解密/自管存储不适用，重写成本巨大 |
| aria2 式 chunk(task+chunk) 双表重构 | 改动 10+ 文件 + DB 双表迁移，现有磁盘真源方案已闭环，违反极简哲学 |
| 仅修 P1 不做 P2/P3 | P2 中进度高频写库、僵尸字段、主线程 DB 均为实际运行风险；用户要求全面完善 |

### Drawbacks

- B1 节流后进程被杀丢最后 ≤1s 进度（重启从分片文件续传，实际无损，可接受）。
- B8 DB 迁移有覆盖安装风险，须按 database-migration-safety.md 验证（schema 导出 + 真机覆盖安装测试）。
- A5 改订阅后进度刷新粒度由 StateFlow 发射节奏决定，需配合 B1 节流确保流畅（500ms 节流即 UI 刷新频率，与现状轮询相当）。
- D5 改 stopSelfOnTaskRemoved 开关后用户划掉最近任务下载仍在后台跑（Media3/常见下载器默认行为），通知常驻可感知；队列空时服务经 maybeStopSelf 正常退场，任务级通知 deleteIntent 与前台 summary 通知语义不变。
- 批次E .seg 断点文件在两次落盘间进程被强杀丢失，恢复回退到最后落盘点，丢 ≤5s 数据（可接受）。
- 批次E 直链引擎从静态 3 分片重写为 IDM 动态分段（约 300 行），实现复杂度上升且需真机多场景验证（多连接加速/暂停恢复/.seg 强杀恢复/单流回退）；多 RandomAccessFile 句柄需 ensureActive+finally 关闭防泄漏。

### Prior Art

- Media3 stopReason 持久化与启动扫描重排队（现有 resumeAllFromDb 已符合，C2 补触发点）。
- OkHttp Range 三件套：206/Content-Range 校验、200 不支持则重写、416 视为完成（A3 采纳）。
- aria2 三级并发模型（全局任务/单任务分片/最小分片大小）——现有 Semaphore(3)+3~4 分片已符合，不调整。
- 详见 `temp/research/android-download-manager-research.md`。

## Requirements

- R1 分片合并前校验每片长度等于预期 rangeLen，不满足抛 INCOMPLETE（R1 适用批次A 静态分片阶段；批次E 落地后被 R17/E5 段级校验取代，演进关系见 tasks 1A.4）
- R2 单线程下载 total>0 时校验 downloaded==total，不符报 INCOMPLETE
- R3 续传 probe total 与 DB 真源（`appDb.downloadTaskDao.loadById(id)?.totalSize`，Long 已落库，0 视为无记录跳过）不一致时清空分片重下（`downloadDirect` 经 `expectedTotal: Long` 参数传入）
- R4 Service 重建后删除任意状态任务均清理磁盘产物（从 DB 重建 info）
- R5 管理页实时反映进度（订阅 StateFlow，刷新延迟 ≤500ms），后台时停止收集
- R6 进度写库 ≤2Hz；完成/失败/暂停等状态变更立即落库
- R7 CancellationException 全链路 rethrow，用户取消不计为失败
- R8 任务成功后 errorCode 为空
- R9 HLS 非 0 MEDIA-SEQUENCE 清单缺省 IV 解密正确
- R10 磁盘空间不足时任务报错暂停而非产生坏文件
- R11 内存缺失的任务 id 状态更新不丢失
- R12 >2GB 文件大小显示正确
- R13 COMPLETED 记录对应文件不存在时点击播放给出明确提示
- R14 清除失败记录后 .part/.seg/.partN/tempDir 不残留
- R15 DB 107→108 迁移覆盖安装不丢数据（实际只删 resumePointJson/segmentsJson/errorMsg 3 列；targetDir 列在 entity 与 DB v107 已存在不增列，updateTask/addTask 写入并保留旧值；迁移产物 app/schemas/io.legado.app.data.AppDatabase/108.json 需提交）
- R16 全部改动编译通过 + 现有下载链路（直链/HLS/暂停恢复/断点续传/删除）真机回归通过
- R17 直链大文件下载中空闲连接自动认领/分裂最大剩余段（连接复用免重连，IDM 动态分段 DFS）
- R18 暂停/进程死亡后从 .seg 恢复分段进度（.seg 落盘 ≤5s 粒度，.seg 为唯一进度真源）
- R19 probe 后仅当 range==true 且 total>0 时进入 DFS；200 响应（不支持 Range）或 206 但 Content-Range 无有效总长（如 bytes 0-0/*）或 total≤0（chunked/未知长度）时一律回退单流且不写 .seg（E2 初始切分前置门禁：total>0 才切分，保证 min(maxConnections, total/MIN_SEGMENT_SIZE) ≥ 1）

## Scenarios

> Gherkin 关键词：假设（Given）/ 当（When）/ 那么（Then）/ 并且（And）

```gherkin
功能: 下载管理演进式优化

  背景:
    假设 用户已通过订阅源添加视频下载任务
    并且 下载引擎为自研直链/HLS 引擎（前台服务承载）

  场景1: 分片下载中服务器提前断流自动重试成功
    假设 任务采用分片下载模式
    当 某分片下载过程中服务器提前断流
    那么 引擎按错误码驱动自动重试该分片
    当 重试合并前发现 part.length 不等于预期 rangeLen
    那么 抛出 INCOMPLETE 触发再次重试
    当 某次重试后分片长度校验通过
    那么 分片合并成功且任务进入 COMPLETED
    并且 最终文件可正常播放

  场景2: CDN 续传时 total 变化清空分片重新下载
    假设 任务已完成部分分片并暂停
    当 恢复时 probe 得到的 total 与 DB 已落库 totalSize 不一致（totalSize==0 视为无记录跳过比对）
    那么 清空全部 .partN 分片从零重新下载
    并且 不产生错位拼接的坏文件

  场景3: Service 重建后删除任务文件与记录同步清理
    假设 下载服务曾被系统重建（内存 downloadInfos 已丢失）
    当 用户删除一个已完成任务
    那么 引擎从 DB entity 重建 DownloadInfo
    并且 记录与磁盘产物同步删除
    并且 不留下孤儿文件

  场景4: 大文件下载进度显示正确且写库受控
    假设 用户下载一个大于 2GB 的视频文件
    当 下载进行中
    那么 进度大小计算无 Int 溢出（内存任务模型使用 Long）
    并且 进度写库频率不超过 2Hz（500ms 节流）
    并且 管理页 UI 实时反映进度（刷新延迟不超过 500ms）
    当 任务进入 COMPLETED
    那么 进度与状态变更立即落库且 errorCode 为空

  场景5: 进程被杀重启后残留任务自动校准恢复
    假设 进程被系统杀死时存在 RUNNING 状态的下载任务
    当 用户重新打开下载管理页
    那么 管理页 onResume 触发 resumeFromDb 校准
    并且 RUNNING 残留任务被自动恢复续传
    并且 恢复时速度计算时间基准被重置（无瞬时超高速假象）

  场景6: 用户清除失败记录后无临时产物残留
    假设 存在 FAILED 状态的任务且磁盘上有 .part 单文件、.part.seg 断点文件、存量 .partN 分片或 HLS tempDir
    当 用户点击清除已完成/失败记录
    那么 记录被删除且逐项取消对应通知
    并且 Service 联动清理 .part/.seg/.partN/HLS tempDir 临时产物
    并且 存储中无孤儿文件

  场景7: DB 107 老版本覆盖安装 108 任务记录完整保留
    假设 设备上安装有 DB 版本 107 的应用且已有下载任务记录
    当 覆盖安装升级到 DB 版本 108（手动 Migration：仅删 resumePointJson/segmentsJson/errorMsg 3 列，targetDir 列 v107 已存在不增列）
    那么 原有任务记录完整保留不丢失
    并且 暂停/失败任务可正常恢复续传
    并且 后续 updateTask/addTask 写入并保留 targetDir 旧值（防 @Update 全量回写刷成 null）

  场景8: 用户划掉最近任务下载继续
    假设 任务正在前台服务中下载（批次D 已实施）
    当 用户在最近任务列表划掉应用
    那么 下载不被中断继续后台执行
    并且 常驻通知可感知任务仍在进行
    并且 任务状态落库，即使后续被杀也可自动恢复

  场景9: 快慢连接场景空闲连接分裂最大段加速
    假设 直链任务采用 IDM 动态分段多连接下载（批次E）且各连接带宽不均
    当 慢连接拖尾成为瓶颈而其他连接已完成各自区间转入空闲
    那么 空闲连接取剩余字节最多的段：未开始则整个认领，进行中则将其剩余区间对半认领后半
    并且 已完成连接免重连直接循环认领剩余区间（连接复用）
    并且 总耗时接近最快连接的吞吐上限而非被慢连接拖尾
    并且 剩余区间小于 MIN_SEGMENT_SIZE 时不硬拆、空闲连接等待

  场景10: 暂停或进程强杀后从 .seg 恢复继续下载不重头
    假设 直链任务正在多连接下载且 .seg 断点文件按 ≤5s 粒度落盘（每 5s 定时+终态前强制）
    当 用户暂停任务或进程被系统杀死
    那么 恢复时读 {fileName}.part.seg 重建分段队列（.seg 为唯一进度真源）
    并且 各连接从各自段断点偏移继续下载不重头
    并且 强杀丢失的数据不超过最后一次 .seg 落盘点（≤5s，可接受）
    并且 若 probe total 与 expectedTotal 不一致则删 .part+.seg 重下（A3 联动）

  场景11: 206 无有效总长或 total 未知时回退单流且不写 .seg
    假设 直链任务 probe 收到 206 但 Content-Range 无有效总长（如 bytes 0-0/*）或 total<=0
    当 引擎判定不满足 range && total>0 的 DFS 进入条件
    那么 自动回退单流下载且不写 .seg
    并且 完成时不做 total 比对（total 未知跳过，对齐 A2 total>0 前置）
```
