# 视频播放器优化：默认静音 + 高倍速支持

> **状态**：✅ 已实施（待真机验证）
> **创建日期**：2026-07-08
> **优先级**：P2（体验增强）
> **核心原则**：复用已有底层 API（setNeedMute / PlaybackParameters），最小改动

---

## 一、功能概述

1. **默认静音**：视频播放默认关闭声音，用户可手动开启。避免在公共场合突然外放声音的尴尬。
2. **高倍速支持**：倍速选择对话框新增 5X/10X/15X 选项，满足快速浏览视频内容的需求。

## 二、现状锚点

| 文件 | 行号 | 现状 |
|------|------|------|
| ExoPlayerManager.kt | L122-130 | 已有 `setNeedMute(Boolean)` 接口，调用 `mediaPlayer.setVolume(0f,0f)` |
| ExoPlayerManager.kt | L110-120 | 已有 `setSpeed(speed, soundTouch)` 接口 |
| VideoPlayer.kt | L404 | 倍速列表 `listOf(0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f)` 最高 3X |
| VideoPlay.kt | L89-94 | 已有 cachePlay 属性可仿照新增 muteOnStart |

## 三、文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 实施任务清单 |
