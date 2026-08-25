# 下载器成熟化改造规格（download-manager-maturity）

## 1. Intent

将 Legado 当前的下载能力从"能用的原型"提升为"可靠的成熟下载器"。本规格回答两个问题并落地改造：

1. **全量下载入口盘点**：除内置播放器下载按钮外，还有哪些入口发起下载 / 管理下载？
2. **成熟度缺口闭环**：对照成熟下载器（IDM、系统 DownloadManager、主流 App 下载器），当前下载器除已发现的 bug 外，还差哪些关键能力？

内核原则：**先保稳定性，再补任务能力，最后做工程健壮性**——优先根治"任务无故消失""下载中断"这类用户最痛的问题。

## 2. Scope

### In-Scope
- 全量下载入口清单整理（含入口文件/触发动作/任务类型）。
- 任务状态持久化 + 启动恢复（进程被杀/崩溃后任务不丢、可续传）。
- 断点续传（直链分片已下部分 + m3u8 已下分片在失败/暂停后复用）。
- 真实暂停/恢复单任务（补全 `PAUSED` 死分支）。
- 并发上限 + FIFO 排队。
- 失败自动重试（指数退避）。
- 错误码 + 分阶段生命周期（WAITING/RUNNING/PAUSED/COMPLETED/FAILED 状态机落到真实代码）。
- 通知 id 稳定映射修复。
- 下载目录可见性（可选，视工作量）。

### Out-of-Scope
- 已有 bug 的修复（分片覆盖、csd 校验回退 ts、下载单位、服务停止逻辑）——已在本规格前完成，不重复。
- 系统 DownloadManager 集成 / 公有 Downloads 目录权限方案（维持 app 专属目录，In-Scope 仅优化可见性）。
- HLS 加密源（AES-128 支持）改造——`UnsupportedCrypto` 现状保留，成熟化另立规格。
- 全局速度限制、仅 WiFi 下载等调度策略（列为未来项，indeterminate 优先级）。

## 3. Approach

### Selected Approach
在现有 `DownloadService`（前台服务）调度骨架之上，做**增量加固**而非重写：

- **持久化**：新增 Room 下载任务表（类比现有实体，字段全部默认值、`@Parcelize`），`DownloadState` 从纯内存改为「Room 为主存 + StateFlow 缓存」。服务启动从 Room 恢复未完成任务。
- **断点续传**：
  - 直链：`ChunkDownloader` 的 `.partN` 临时文件按已下字节推进 Range，失败/暂停后从 `partN` 现有大小继续。
  - m3u8：`HlsDownloader` 记录已下成功分片清单（`.part` 元数据），续传时跳过已下分片。
- **暂停/恢复**：任务协程持有 `Job`，暂停 = A 计 `cancel`（保留临时文件）；恢复 = 重新入队 + 续传。
- **并发/排队**：`Semaphore(MAX_CONCURRENT)` + 待执行队列，WAITING 状态驱动。
- **重试**：FAILED 状态 + 指数退避 `delay(2^n * base)`，最多 N 次。
- **错误码**：`DownloadError` 枚举（HTTP/IO/NETWORK/ENCRYPT/NATIVE_REMUX/UNSUPPORTED），失败落库。
- **通知 id**：`notificationId = id.toInt()` 直接映射，废弃 `size` 计算 + index 反查。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 重写为独立下载库（如 lib-downloader 第三方库） | 引入新依赖，与项目 CoC（无 DI、object 单例）不符；重写风险高于增量加固 |
| 回到系统 DownloadManager | 无法满足多线程分片 + m3u8 转 mp4 + 防盗链头，正是当初弃用的原因 |
| 状态只存 SharedPreferences | 不适合结构化多任务/分片进度，Room 更契合已有技术栈 |
| m3u8 断点用「记录已下 ts 数量」而非分片清单 | 分片失败需精确续传，数量不够精确 |

### Drawbacks
- 断点续传对「服务器不支持 Range」的直连源失效（单线程整段下载，无续传点）——接受，这类源占比低。
- m3u8 续传依赖分片清单持久化，极端进程强杀下清单写入间隙可能丢一两个分片——接受，可重下。
- Room 表新增 + 版本升级（`legado.db` schema 变更，当前 v89）——需按 `database-migration-safety` 走迁移验证。

### Prior Art
- 参考 `precise-manage` 规格的下载管理页 UI 与 `DownloadState` 轮询模型。
- 参照系统 `DownloadManager` 的任务队列/暂停/重试语义与 IDM 的分片续传思想。

## 4. Requirements

### 功能需求（FR）
- **FR-1 入口盘点**：维护一份全量下载入口清单（入口文件 + 触发动作 + 任务类型），供后续统一治理。
- **FR-2 持久化**：下载任务（含直链分片进度 / m3u8 分片清单）落 Room，进程重启后恢复未完成任务。
- **FR-3 断点续传**：直链与 m3u8 在失败/暂停/重试后从中断点继续，不整段重下。
- **FR-4 暂停/恢复**：下载中任务可暂停、可恢复，保留已下数据。
- **FR-5 并发控制**：同时下载任务数有上限，超出排队（WAITING），按入队顺序执行。
- **FR-6 自动重试**：网络/瞬时失败自动指数退避重试，达到阈值才 FAILED。
- **FR-7 错误码**：任务失败记录具体原因（错误码），管理页可见。
- **FR-8 通知稳定**：通知 id 与任务 id 稳定映射，多任务不错位。

### 非功能需求（NFR）
- **NFR-1 兼容**：Room 版本 v89 无损升级；`DownloadState`/`DownloadManageActivity` 调用面保持兼容。
- **NFR-2 健壮**：所有 native 边界（remux）前置校验，杜绝再次 SIGABRT 杀进程。
- **NFR-3 性能**：并发限流避免内存/带宽打爆（关联项目 32G 构建机心智，运行时同源）。

## 5. Scenarios

### 场景 1：进程被杀后任务恢复
1. 用户从播放器下载一个 m3u8，下载进行到 60%；
2. 应用在 remux 或内存压力下进程被杀；
3. 重启后进入下载管理页，任务仍存在、进度约 60%；
4. 手动重试（或恢复）后从 60% 续传，最终完成。

### 场景 2：暂停与恢复
1. 用户同时下载 2 个直链视频；
2. 对其中一个点"暂停"，其协程被安全取消、`.partN` 保留，状态变 `PAUSED`；
3. 再次点"恢复"，从暂停点续传，不影响另一个任务。

### 场景 3：并发排队
1. 用户一次添加 5 个下载任务，并发上限为 3；
2. 前 3 个进入 RUNNING，后 2 个 WAITING 排队；
3. 前序完成一个，排队者自动升入 RUNNING。

### 场景 4：失败自动重试
1. 下载中网络抖动导致一次 HTTP 404/超时；
2. 任务自动按指数退避重试（非立即 FAILED）；
3. 到阈值仍失败才置 FAILED 并展示错误码。