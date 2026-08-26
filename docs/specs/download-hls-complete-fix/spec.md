# HLS 下载完成链路修复 — 需求规格（spec.md）

## 1. Intent

HLS（m3u8）视频下载成功后，必须交付**可播放的完整产物**，且**进入完成列表**、**可在软件内用内置播放器播放**。本次修复三个相互关联的缺陷：

1. ts→mp4 重封装阶段 MediaMuxer native 崩溃（csd 不完整），导致产出几百 KB 的空壳 mp4 且进程被杀；
2. 崩溃使任务状态停在 RUNNING，完成列表看不到已完成项（或用户以为任务丢失）；
3. 完成列表「打开文件」未接入内置播放器，跳系统 Intent 播放，体验与"软件内播放"诉求不符。

## 2. Scope

### 2.1 包含（In）

- HLS（m3u8）下载链路中 ts→mp4 重封装的 csd 完整性校验与兜底；
- 下载任务在任务完成后正确落库 COMPLETED 并出现在「已完成」Tab；
- 完成列表项「打开文件」（含 CONPOMLETED 状态菜单）改为软件内调用内置视频播放器（VideoPlayerActivity）播放本地 mp4/ts；
- 对非 HLS 直链下载（mp4 直链等）的完成项同样支持内置播放器打开（体验统一）；
- 必要的崩溃日志/兜底日志输出（无关内容脱敏，只输出技术标记）。

### 2.2 不包含（Out）

- 不扩大范围修复其他下载类型（音频/文档直链的非视频播放，仍走系统打开）；
- 不重写 HLS 分段下载/解密逻辑（只改重封装与状态/打开链路）；
- 不做下载并发调度调整。

## 3. Approach

### 3.1 Selected Approach

**A. 重封装 csd 加固（根因 1）**

`HlsDownloader.TsToMp4Remuxer.remux()` 增加严格的 csd 完整性校验：

- 视频轨 `csd-0` 必须同时满足：
  - 非空且 `remaining() >= 16`（H.264 AVCC 头 + SPS/PPS 最小合理长度）；
  - 首字节 `0x01`（AVCC configurationVersion 标记）。
- `csd-1`（如存在）允许为空，但 `csd-0` 不完整时：
  - **不再直接 remux**（避免 native SIGABRT 杀进程）；
  - **标记 TsFallback**：保留合并后的 `.ts` 文件（用户已有 HlsResult.TsFallback 通道，`DownloadService.executeHls` 会移动 ts 至目标目录并完成），保证"下载成功不丢数据、有可播产物"。
- 补充：`MediaExtractor` 读取不了 `csd-0`（null）时同样走 TsFallback。

**B. 完成状态落库保障（根因 2）**

- 崩溃修复后，`handleSuccess`（COMPLETED + localPath + progress=100）即可正常执行；
- 追加兜底：`DownloadService` 若捕获到**未预料异常/检测到产物异常**（mp4 长度 < 阈值如 1KB 且 ts 存在），先落 `TsFallback` 结果而非让任务悬在 RUNNING；
- 保留 `DownloadState.resumeFromDb()` 对上次崩溃残留 RUNNING 任务的重置（当前已存在 RUNNING→PAUSED），确保完成列表语义正确。

**C. 软件内播放（根因 3）**

- `DownloadManageActivity.openFile`：当任务类型为 HLS 或本地文件扩展名为视频（mp4/ts/webm/mkv/m3u8）时：
  - 启动 `VideoPlayerActivity`，传 `videoUrl = Uri.fromFile(file)`（file://）、`videoTitle = fileName`、`isNew = true`（单 URL 模式）；
  - 复用内置播放器 `singleUrl` 通道（`VideoPlay` 已支持 `file://` 嗅探跳过，见 `VideoPlay.kt:648`）。
- 非视频文件仍走系统 `openFileUri`。

### 3.2 Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 用 MediaCodec 解码注入 csd（Encoder 修复） | 依赖解码器实现，复杂且不通用；本例只需"缺 csd 时保 ts"，无需强行造 csd |
| 放大 csd 阈值到 ≥32/64 | 治标不治本，不同编码器 csd 长度不定，仍可能误判 |
| 崩溃后用 tombstone 恢复任务 | 进程已死，状态不可信，且 mp4 已残；不如源头避免崩溃 |
| 打开文件继续走系统 Intent | 用户明确要求软件内播放，且内置播放器已具备 file:// 能力，改动成本低 |

### 3.3 Drawbacks

- HLS 视频若源流 csd 缺失（极端个例），会降级保留 `.ts` 而非 mp4——符合"不丢数据优先"原则，播放体验无损（内置播放器可播 ts）；
- `csd-0.remaining()>=16 + 首字节 0x01` 是经验阈值，若个别合法码流 csd < 16 字节会误降级——发生率极低（AVCC 头本身就 ≥6 字节 + SPS ≥3 字节），可接受；
- 内置播放器打开本地文件复用 singleUrl 通道，无线路选择 UI——完成列表语境本就单文件，符合预期。

### 3.4 Prior Art

- `HlsDownloader.kt` 已有 `HlsResult.TsFallback` 兜底通道与 `DownloadService.executeHls` ts 移动逻辑（迁移自 download-manager-maturity 规格）；
- `VideoPlay.startPlay` 单 URL 模式已支持 `file://`（`VideoPlay.kt:648` 嗅探分支跳过）；
- 内置播放器入口参数：`VideoPlayerActivity.onActivityCreated`（`videoUrl`/`videoTitle`/`isNew`）。

## 4. Requirements

- R1: HLS 转 mp4 时视频轨 csd 不完整 → 不崩溃，降级保留 ts 并完成任务（COMPLETED）。
- R2: 正常 HLS 下载完成后任务进入「已完成」Tab，显示 100% 进度与产物路径。
- R3: 完成列表项「打开文件」→ 启动内置视频播放器（VideoPlayerActivity）播放本地 mp4/ts，标题为文件名。
- R4: 直链 mp4 等视频文件完成项同样走内置播放器。
- R5: crash/兜底路径输出技术日志（AppLog），脱敏。

## 5. Scenarios

### 5.1 HLS csd 缺失（复现用户问题）

1. 用户下载 HLS 视频（m3u8，csd 不足）；
2. 分片下载/合并 ts 成功；
3. 转 mp4 前校验 csd-0 不足 → 不触发 MediaMuxer；
4. ts 移动至目标目录，任务 COMPLETED，出现于「已完成」；
5. 点击该项 → 内置播放器播放 ts。

### 5.2 正常 HLS 完整合并

1. csd-0 完整 → remux 成功 → 干净 mp4；
2. 任务 COMPLETED，位于「已完成」，打开走内置播放器。

### 5.3 直链 mp4 完成项播放

1. 直链下载完成 → COMPLETED；
2. 打开文件 → 扩展名 mp4 → 内置播放器。

### 5.4 非视频文件

1. 直链下载 txt/zip → 打开走系统 Intent（行为不变）。