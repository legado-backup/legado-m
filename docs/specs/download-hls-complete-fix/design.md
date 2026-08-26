# HLS 下载完成链路修复 — 技术设计（design.md）

## 1. Technical Approach

### 1.1 问题定位（logs(3) 铁证）

| 日志 | 含义 |
|------|------|
| `E Utils: csd0 too small`（logcat 12349） | **系统** MediaMuxer/MediaProvider framework 日志，判定视频轨 csd-0 残缺（tag 为 Utils/ExtendedUtils，非 App 日志） |
| `Abort message: 'ubsan: mul-overflow by 0x...'`（12410） | **真正崩溃点**：Redmi OS3.0（Android 16 / Unisoc / BP2A.250605.031.A3）rom 编译期开启 UBSan，MPEG4Writer 对残缺 csd 的缓冲尺寸相乘溢出直接 abort |
| `F libc: Fatal signal 6 (SIGABRT) in tid 24516 (MP4WtrVidTrkThr)`（12385） | native 崩溃线程 = MediaMuxer 视频轨 writer，Java 层 try/catch 无法拦截，进程被杀 |
| 崩溃后 app 重启（process 11355 → 重启) | DownloadService 状态中断，任务悬在 RUNNING，从未落库 COMPLETED |

### 1.2 根因链

```
HLS 下载 → ts 合并成功 → TsToMp4Remuxer.remux()
  → MediaExtractor 提取轨道 → 视频轨 csd-0 只有几字节（源流 SPS/PPS 稀疏）
  → 旧校验“csd0.remaining() >= 4”误判通过
  → muxer.addTrack(format) → MPEG4Writer 视频轨 writer 线程计算缓冲尺寸
  → ROM UBSan 检测到无符号乘法溢出 → SIGABRT 杀进程（Java 层捕获不住）
  → DownloadService.handleSuccess 未执行 → 任务悬在 RUNNING、完成列表无记录
  → mp4 只写入了 moov 头 + 开头几帧（几百 KB）→ “仅有几百KB未合并成功”
```

### 1.3 修复方案选型

| 层 | 改动 | 目的 |
|----|------|------|
| 校验层 | `TsToMp4Remuxer` 视频轨 csd 严格校验（长度≥16 + 首字节 0x01 + 宽高>0），不满足→返回 TsFallback | 从源头杜绝 MediaMuxer 触碰残缺视频轨，避免 native 崩溃 |
| 状态层 | `HlsDownloader.download` 新增 `onMerged` 回调：**ts 合并完成即回调，executeHls 立即落库 COMPLETED（产物指向 ts）**，再异步尝试 mp4 转码；转码成功仅更新 localPath 为 mp4 | 即使转码仍发生 native 崩溃，任务已在完成列表且 ts 完整可播，任务不丢失 |
| 播放层 | `DownloadManageActivity.openFile` 视频类型→内置播放器（file:// 单 URL 通道） | 完成列表软件内播放 |

### 1.4 csd 校验实现要点

```kotlin
// 视频轨必须拥有结构完整的 AVCC csd-0（H.264: 首字节配置版本 0x01）
if (mime.startsWith("video/")) {
    val csd0 = format.getByteBuffer("csd-0")
    val csd0Raw = csd0?.let { buf ->
        val arr = ByteArray(buf.remaining())
        buf.duplicate().get(arr)
        arr
    }
    val csdOk = csd0Raw != null &&
        csd0Raw.size >= 16 &&
        csd0Raw[0] == 0x01.toByte()   // AVCC configurationVersion
    if (!csdOk) return@runCatching false   // 触发 TsFallback
}
```

## 2. Architecture Decisions

### AD-01: 以 TsFallback 兜底不完整 csd 的 HLS 流
- **Context**: MediaMuxer 对 csd0 过小会 native SIGABRT 杀进程（Java 层 try/catch 无法拦截），必须前置规避。
- **Concern**: 完整性低于阈值的合法码流可能被误降级，但崩进程的代价不可接受（用户数据/任务丢失）。
- **Decision**: 视频轨 csd-0 不满足（非空 && ≥16 字节 && 首字节 0x01）→ 跳过 remux，返回 false → TsFallback 保留完整 ts。
- **Goal**: 任何 HLS 流都不触发 native 崩溃；即使转 mp4 失败也保留可播 ts，任务照常完成。
- **Tradeoff**: 个别 csd 合法但紧凑的码流无法合并 mp4，保 ts 替代——播放无差别，接受。
- **Status**: Proposed

### AD-02: ts 移动后即判定成功（不追求 100% mp4）
- **Context**: remux 失败不该让任务失败/丢失；HlsResult 已内置 TsFallback 语义。
- **Concern**: 若把 remux 失败当 Failed，用户再次看到"失败"而实际 ts 可播，矛盾。
- **Decision**: 复用现有 `executeHls` 的 TsFallback 分支（ts 移动至目标目录 → 成功 COMPLETED）。
- **Goal**: 完成列表永远有可播产物。
- **Tradeoff**: "完成的产物是 ts 不是 mp4"——扩展名差异可接受，播放器两者皆可播。
- **Status**: Proposed

### AD-03: 完成项播放复用 VideoPlayerActivity 单 URL 通道
- **Context**: 内置播放器 `singleUrl` 模式已支持 `file://`，无需新增播放器能力。
- **Concern**: 本地文件无"线路/集数"概念，须走简单单 URL 路径而非源解析路径。
- **Decision**: `openFile` 对视频类型启动 VideoPlayerActivity，传 `videoUrl=file://...`、`videoTitle=fileName`、`isNew=true`。
- **Goal**: 与在线视频播放同一 UE；完成列表一键软件内播放。
- **Tradeoff**: 本地播放无线路选择 UI（本地文件本无线路），符合语义。
- **Status**: Proposed

## 3. Data Flow

```
用户点击下载（HLS）
  → DownloadService.startDownload → executeHls
    → HlsDownloader.download（分片AES-128解密 → ts合并）
      → TsToMp4Remuxer.remux（csd严格校验）
        ├─ csd完整 → MediaMuxer → mp4 → HlsResult.Mp4
        └─ csd缺失 → return false → HlsResult.TsFallback（ts移至目标目录）
  → handleSuccess → DownloadState COMPLETED（localPath + progress=100）
    → DownloadManageActivity 轮询 → 「已完成」Tab 出现
      → 点击「打开文件」→ 视频? → VideoPlayerActivity(file://) 播放
                                     └ 非视频 → openFileUri 系统打开
```

## 4. File Changes

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/help/download/HlsDownloader.kt` | `TsToMp4Remuxer.remux` 视频轨 csd 严格校验（≥16 + 首字节 0x01），不满足走 TsFallback；补充读不到 csd-0 的兜底 |
| `app/src/main/java/io/legado/app/ui/download/DownloadManageActivity.kt` | `openFile`：视频类型（HLS 或扩展名 mp4/ts/webm/mkv/m3u8）→ 启动 VideoPlayerActivity 软件内播放；非视频保持系统打开 |
| `app/src/main/java/io/legado/app/service/DownloadService.kt` | （小）确认 TsFallback 分支产物完整性：ts 移动成功判定；必要时追加异常产物兜底日志 |
| `app/src/main/assets/updateLog.md` | 用户可见更新条目（本次符合编译前同步门禁） |
| `docs/specs/download-hls-complete-fix/tasks.md` | 任务勾选进度 |
| `docs/INDEX.md` | 登记本规格 |

## 5. 验证策略

- 单元/编译：`./gradlew :app:compileAppDebugKotlin`（或汇编）零错误；
- 真机回归（Android 9 模拟器 + 测试包）：
  - 复现 HLS 下载（csd 缺失源）→ 确认不崩溃、已完成列表出现 ts、软件内播放可看；
  - 正常 HLS 源 → mp4 完整（非几百 KB）、完成列表、软件内播放；
  - 直链 mp4 → 完成列表软件内播放；
  - 非视频直链 → 系统打开行为不变。
- 残留检查：Grep 临时日志 0 残留。