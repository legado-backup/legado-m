# 下载 HLS 完成链路修复（download-hls-complete-fix）

> 🔄 设计中

## 功能概述

修复 HLS（m3u8）视频下载"下载成功但产物异常"三连问题：

1. **合并产物只有几百 KB**：HLS 下载完成后转 mp4 阶段 MediaMuxer 因视频轨 csd（SPS/PPS）不完整触发 native SIGABRT，进程被杀，mp4 残留几百 KB（只写了 moov 头没写数据），实际未合并成功。
2. **完成列表缺失**：崩溃发生在 `handleSuccess` 落库之前，任务状态停留在 RUNNING，不会出现在「已完成」Tab；且进程被杀后用户以为任务丢了。
3. **完成后无法软件内播放**：完成列表「打开文件」走系统 Intent 调外部播放器，未使用内置视频播放器页面（VideoPlayerActivity），体验割裂。

目标：HLS 视频 `mp4 合并完整` + `完成后进入完成列表` + `点击可软件内调用内置播放器播放`。

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR/数据流/文件变更） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y`） |

## 状态标记

- [x] 🔄 设计中
- [ ] ✅ 设计完成
- [ ] 🔄 开发中
- [ ] ✅ 已完成

## 根因结论（2026-08-25 logs(3) 分析）

- `logcat.txt:12349` `E Utils: csd0 too small` → `12385` `F libc: Fatal signal 6 (SIGABRT) in tid 24516 (MP4WtrVidTrkThr)`：MediaMuxer 写视频轨时 csd（codec-specific data，SPS/PPS）长度不足，native 层直接 abort 杀进程。
- 现有校验（`HlsDownloader.TsToMp4Remuxer`）只判 `csd0.remaining() >= 4`，阈值过宽——`csd-0` 有 ≥4 字节时即认为有 csd，但 native 层仍判定 `csd0 too small` 崩溃。
- 崩溃在 `handleSuccess`（`DownloadService` 落库 COMPLETED）之前 → 完成列表无此项；进程被杀 → mp4 残留几百 KB（MediaMuxer 写了 moov 头即崩）。
- 内置播放器已支持 `file://` + `singleUrl`（`VideoPlay.kt:648`），`openFileUri` 却走系统 Intent。