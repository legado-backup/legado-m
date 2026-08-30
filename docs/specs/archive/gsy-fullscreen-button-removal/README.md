# GSY 全屏按钮去重

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

## 功能概述

移除 GSY 视频播放器内置的右下角全屏按钮（`@+id/fullscreen`），消除与自定义中部全屏按钮（`btn_fullscreen`）的功能冗余。

## 背景

video-ui-dedup-layout-adjust OpenSpec 检查点3 最终验收时，用户反馈：
> "现在既然我们已经有了视频中部的全屏缩放，视频播放器内置自带的右下角的全屏缩放按钮是不是可以去掉了呢？"

经调查确认：
- GSY 内置全屏按钮位于 `video_layout_controller.xml` L102-108（id=fullscreen），右下角
- 自定义全屏按钮位于 `fragment_video.xml`（btn_fullscreen），底部中央
- 全屏模式布局 `video_layout_controller_full.xml` 中无 fullscreen 按钮（退出全屏靠系统返回键）
- 两个按钮功能完全重叠，存在 UI 冗余

## 核心能力

- 消除 GSY 内置全屏按钮与自定义全屏按钮的冗余
- 保持全屏功能完整性（自定义 btn_fullscreen + 系统返回键退出全屏）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 |

## 状态

🔄 设计中（待检查点1 用户审查）
