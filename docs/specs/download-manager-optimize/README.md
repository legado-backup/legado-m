# 下载管理优化

> **状态**：✅ 实施完成（2026-08-29 编译门禁+真机核验通过，待验收）

## 功能概述

阅读M（Legado fork）精准管理面内置"下载管理"能力，以视频下载为主，支持 HLS / 直链双引擎。现有架构为：`model/Download.kt` 入口 → `DownloadService.kt` 前台服务（Semaphore(3) 任务并发 + 指数退避重试）→ `DownloadState.kt`（Room `download_tasks` 表主存 + StateFlow 展示缓存），底层由 `ChunkDownloader`（直链 3 分片 Range 断点续传）与 `HlsDownloader`（m3u8 解析 + AES-128 解密 + ts 合并 + remux mp4）承载，错误模型为 `DownloadError` 七码。UI 侧为 `DownloadManageActivity`（500ms 轮询）+ `DownloadManageScreen`（无状态 Compose，5 Tab 分组）。当前数据库版本 107。

经全面深度分析，共识别 42 项待优化问题。其中 P1 级五项直接关乎正确性：直链分片完整性校验缺失（2 处）、续传 total 一致性缺失、Service 重建后删除任务遗留孤儿文件、UI 未订阅已有 StateFlow 改用轮询。

本次改造目标为**演进式优化**：不引入第三方下载库、不重写双引擎，在现有架构上分五批次收敛正确性、健壮性、数据一致性与 UX 问题，最终达到可信、可恢复、可观测的下载管理体验。

## 核心能力 / 改造点

改造分五批次推进（详见 [tasks.md](./tasks.md)）：

- **批次 A — P1 正确性修复（5 项）**：分片完整性校验（2 处）、续传 total 一致性校验、Service 重建后删除任务清理孤儿文件、UI 改订阅已有 StateFlow 去除 500ms 轮询。
- **批次 B — 引擎健壮性（约 11 项）**：进度落库节流（进度类更新内存发射与 DB 写入共用 500ms 时间窗，状态翻转立即发射+落库）、CancellationException 处理、errorCode 清理、HLS 缺省 IV 回退 MEDIA-SEQUENCE、磁盘空间预检、updateTask 合并恢复、速度基准重置、僵尸字段清理（实际只删 3 列；targetDir 列 v107 已存在，updateTask/addTask 写入并保留旧值；DB 107→108 迁移）、totalSize/downloadedSize Int→Long 等。
- **批次 C — 数据一致性与 UI 收口（约 8 项）**：COMPLETED 文件存在校验、RUNNING 残留校准、清除记录联动清理临时产物、通知取消、主线程 DB 下沉、Tab 与扩展名单源化、文案修正等。
- **批次 D — UX 增强（可选）**：速度 + ETA 显示、失败详情、URL 脱敏、旋转态保存、划掉任务不中断下载等。
- **批次E — IDM 动态分段引擎（P2，用户 2026-08-28 裁决增补）**：直链引擎从静态物理 3 分片升级为真 IDM 动态文件分段（DFS）——单文件绝对偏移写入（每连接独立 RandomAccessFile FD）、逻辑分段队列、空闲连接对最大剩余段对半分裂/认领（IDM in-half，连接复用免重连）、.seg sidecar 断点文件（JSON，每 5s 定时+终态强制落盘，恢复读 .seg 重建队列）、不支持 Range 回退单流；不引入 Room chunk 表，HLS 引擎不动。

## 调研参考

成熟方案调研报告：`temp/research/android-download-manager-research.md`（覆盖 Media3 / OkDownload / Fetch / WorkManager / aria2 / OkHttp Range 实践）。核心结论：

- **不引入停更库**：OkDownload、FileDownloader 维护停滞，排除。
- **借鉴思想而非代码**：Media3 的 stopReason 语义与进度节流思想、OkHttp Range 三件套（Range 头 / 206 响应 / ETag-Last-Modified 一致性）、aria2 三级并发（现有 Semaphore(3) 架构已天然符合）。
- 采用演进式路线，改造聚焦在既有双引擎的修复与收口，不重写。
- **IDM DFS（动态文件分段）/ NDM（IDM 平替，同算法 32 连接）/ KDownloader（Kotlin 生态，IDM-style dynamic range theft）/ Downpour（2026 活跃，自适应并发）查证结论**：动态分段仍是直链最优解，现有静态 3 分片为伪 IDM——据此用户 2026-08-28 裁决增补批次E，将直链引擎升级为真 IDM 动态分段。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格 |
| [design.md](./design.md) | 技术设计 |
| [tasks.md](./tasks.md) | 任务清单 |

## 关键指标

| 指标 | 数值 |
|------|------|
| 待优化总数 | 48 项（原 42 项 + 批次E 6 项，用户 2026-08-28 裁决增补） |
| 批次说明 | 批次 A P1 正确性 / B 引擎健壮性 / C 一致性收口 / D UX 增强 + 批次E IDM 动态分段引擎 |
| P1（正确性） | 5 项 |
| P2 | 约 27 项 |
| P3 | 约 16 项 |
| DB 迁移 | 107 → 108 |
| 涉及文件 | 约 13 个（不变） |

## 风险提示

- **DB 迁移（107→108）**：覆盖安装场景需保证 `download_tasks` 表既有数据无损迁移，重点验证迁移路径与 fallback 行为（实际仅删 resumePointJson/segmentsJson/errorMsg 3 个零写入列，targetDir 列 v107 已存在不增列，迁移产物 108.json 需提交）。
- **进度节流**：进度落库节流意味着进程被杀时最多丢失最后 ≤1s 的进度，属于可接受折中；节流后 UI ≤2Hz 刷新，与现状 500ms 轮询相当，无体验回退。
- **D5 划掉最近任务**：stopSelf 由 BaseService.stopSelfOnTaskRemoved 开关控制（DownloadService 覆写为 false），划掉后任务继续后台下载；划掉最近任务后若队列空服务仍正常退场（maybeStopSelf 判空），任务级通知 deleteIntent 与前台 summary 通知语义不变。
- **批次E .seg 断点丢失窗口**：.seg 每 5s 定时+暂停/失败/终态前强制落盘，两次落盘间进程被强杀会回退到最后落盘点，丢 ≤5s 数据（可接受）；.seg 为唯一进度真源——单文件绝对偏移写入中间可能有洞，文件长度不可作进度依据。
