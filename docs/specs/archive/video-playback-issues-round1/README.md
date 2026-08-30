# 视频播放问题修复第1轮（video-playback-issues-round1）

> 基于 2026-07-12 用户实测日志深度分析，修复订阅源视频播放的 **10 类问题**（原 5 类 + 深度扫描新发现 5 类）。

## 功能概述

用户安装最新版客户端测试订阅源视频播放时，发现"原本使用网页拼接内置 video 标签的时候可以播放，但是改为使用内置视频播放器后，有些就播放不了了"。通过深度分析 `temp\Downloadslogs.(4)..zip` 日志（67个日志文件，07-12 当天播放失败 265 次），识别出 10 类问题需要修复优化。

## 核心能力

| 编号 | 问题 | 严重程度 | 修复方向 |
|------|------|---------|---------|
| P0 | ExoPlayer 播放失败（HLS SPS 解析错误 2000 + UnrecognizedInputFormatException） | P0 | 添加 WebView 降级机制（skill V2 模板）+ 播放器类型配置 |
| P1-1 | 加密解密失败（IllegalBlockSizeException） | P1 | 增强错误提示 + 容错处理 |
| P1-2 | ClassCastException: String→List | P1 | 类型容错处理 |
| P1-3 | SQLiteBlobTooBigException（新发现） | P1 | 跳过超大记录而非崩溃 |
| P1-4 | WebView 线程违规（新发现） | P1 | 主线程包裹 WebView 调用 |
| P2-1 | 网络连接问题（Connection reset/Timeout） | P2 | 增强重试机制 |
| P2-2 | 源格式问题（JSON 格式不规范） | P2 | JSON 格式容错 |
| P2-3 | HlsPlaylistStuckException（新发现） | P2 | 触发降级提示 |
| P2-4 | Cronet 系统错误（新发现） | P2 | 回退 OkHttp 重试 |
| 兼容性 | ViewPager2 上下切换兼容性（用户反馈2） | - | Fragment 内部 View 替换，滑动机制不受影响 |

## 技术根因（P0 核心）

```
ExoPlayer HLS 播放失败调用栈：
ParsableNalUnitBitArray.assertValidOffset (L224)
  → NalUnitUtil.parseSpsNalUnitPayload (L988)
    → H264Reader.endNalUnit (L227)
      → TsExtractor.read (L524)
        → BundledHlsMediaChunkExtractor.read
          → HlsMediaChunk.load

错误码: 2000 (ERROR_CODE_IO_UNSPECIFIED)
根因: HLS TS 分片中的 H264 SPS NAL unit 数据格式异常
对比: WebView 的 Chromium 媒体引擎对格式问题更宽容，可正常播放
```

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式） |

## 状态

- **当前阶段**: 🔄 设计中（步骤3，待检查点1用户审查）
- **创建日期**: 2026-07-12
- **日志来源**: `temp\Downloadslogs.(4)..zip`（解压到 `temp\logs_analysis/`）
- **影响范围**: 订阅源视频播放（VideoPlayerActivity / VideoFragment / Exo2MediaPlayer）
