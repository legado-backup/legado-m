# 视频播放器 UI 去重与布局调整

> **状态**：🔄设计中
> **创建日期**：2026-07-12
> **所属父任务**：R3 抖音风格沉浸式竖屏视频播放器重设计（Task #39）

## 功能概述

订阅源内置视频播放器（type=2）的右侧功能区与 GSY 底部原始控件存在功能重叠，且左下角名称区域遮挡 GSY 底部播放条。本 spec 旨在去除重叠功能、调整布局位置，提升用户体验。

## 核心能力

1. **功能去重**：去掉右侧功能区的静音(btn_mute)和倍速(btn_speed)按钮，这两个功能由 GSY 底部原始控件提供
2. **布局调整**：左下角名称区域(left_bottom_container)和全屏按钮(btn_fullscreen)上移 32dp，避免遮挡 GSY 底部播放条（高 50dp）
3. **代码清理**：移除 btnMute/btnSpeed 相关的变量声明、findViewById、点击事件、updateMuteButtonState()、showSpeedMenu() 等死代码

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（按 tasks.md 实施） |

## 背景

### 问题来源

用户实测最新安装包（071210）后反馈：

> "订阅源内置视频播放器的功能重合了，右侧功能区的静音和倍速功能和内置视频播放器的底部的功能重叠，需要去掉右侧功能区的这两个功能，还有就是左下角名称可以稍微网上移一点点么？遮挡住内置视频播放器底部播放条和倍速静音等其他按钮了呀"

### 当前状态

- **右侧功能区**（6按钮）：快退 / 静音 / 收藏 / 倍速 / 设置 / 快进
- **GSY 底部控件**（mBottomContainer，高 50dp）：进度条 / 当前时间 / 总时间 / 静音(ivMute) / 倍速(playbackSpeed) / 弹幕开关 / 设置按钮
- **左下角区域**：marginBottom=24dp，与 GSY 底部控件重叠 26dp

### 修复后状态

- **右侧功能区**（4按钮）：快退 / 收藏 / 设置 / 快进
- **左下角区域**：marginBottom=56dp，不遮挡 GSY 底部控件
- **全屏按钮**：marginBottom=56dp，同步上移
