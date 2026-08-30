# 视频播放器手势交互重构

> 状态：✅ 已完成（L2真机验证全部通过，2026-07-13）

## 功能概述

修复长按加速播放功能丢失的Bug，同时重构内置视频播放器的手势交互体系，从整体评估确保所有手势不冲突。

## 核心能力

1. **修复长按加速**：长按屏幕倍速播放，松手恢复原速（根因：R3重构替换GSY OnTouchListener导致VideoPlayer.kt内部onLongPress失效）
2. **左右滑动快退快进**：去掉右侧快退/快进按钮，改为常规手势（基于滑动距离连续seek，非固定60秒）
3. **双击暂停/播放**：附带修复（GSY onDoubleTap同样失效）
4. **倍率可配置**：长按倍速倍率在设置弹窗中可修改（已有功能保留）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 |

## 根因分析

R3抖音风格重构时，VideoFragment.kt L921 将自定义 OnTouchListener 设到 `surface_container` 上，**替换了GSY内部OnTouchListener**，导致：
- VideoPlayer.kt L266 `onLongPress`（长按加速）→ 失效
- VideoPlayer.kt L253 `onDoubleTap`（双击暂停）→ 失效
- VideoPlayer.kt L282 `touchSurfaceUp`（松手恢复倍速）→ 失效

这是"改了A功能（R3重构）破坏B功能（长按加速+双击暂停）"的典型案例。
