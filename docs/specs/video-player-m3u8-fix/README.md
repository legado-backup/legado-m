# 视频播放器 m3u8 播放修复

> 🔄 设计中

## 功能概述

深度分析并修复内置视频播放器无法播放 m3u8 格式在线视频地址的问题。

## 核心能力

| 能力 | 说明 |
|------|------|
| **m3u8/HLS 视频流嗅探优化** | 优化嗅探策略，避免 Range 请求消耗 CDN 一次性 token 导致后续播放 URL 失效 |
| **HLS MediaSource 创建增强** | 修复 fallback 链重复构造相同 HLS MediaSource 的问题，构建有意义的降级链 |
| **HLS 分片加载容错** | 增强分片加载的错误恢复机制，提升慢速 CDN / 不稳定网络下的播放成功率 |

## 根因方向

1. **嗅探 Range 请求消耗 CDN token** — Range 请求可能消耗 CDN 一次性 token，导致实际播放时 URL 失效
2. **HLS fallback 链重复** — 当前降级链形如 `[HLS, HLS, DASH]`，重复相同 MediaSource 无实际降级意义
3. **Cache-Control 请求头干扰** — 可能干扰 CDN 行为，导致分片加载异常
4. **嗅探超时不足** — 当前 3s 超时对慢速 CDN 不够
5. **HLS 分片加载缺乏错误恢复** — 分片加载失败后无重试/降级机制

## 涉及核心文件

| 文件 | 职责 |
|------|------|
| `ExoPlayerHelper.kt` | 嗅探 + MediaSource 创建 |
| `Exo2MediaPlayer.kt` | 播放器核心 |
| `MimeSniffer.kt` | MIME 嗅探 |

> 基础依赖：`androidx.media3` ExoPlayer

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格 |
| [design.md](./design.md) | 技术设计 |
| [tasks.md](./tasks.md) | 任务分解 |
| [checklist.md](./checklist.md) | 验收清单 |
