# 视频播放器主题统一（video-player-theme-unify）

> 消除内置视频播放器 UI 的"孤儿样式"，全面接入 ThemeStore 主题体系，使播放器控制条、倍速/选集/画面比例/音轨弹框与整体主题风格统一。

## 功能概述

内置视频播放器（GSYVideoPlayer）的 UI 当前是孤立的孤儿样式：控制条硬编码深色与白色文字、倍速/选集弹框硬编码深色背景、画面比例/音轨走原生未主题化 AlertDialog、旧模式功能区与调试面板硬编码颜色，且播放器页面 `recreateOnThemeChange=false` 导致 View 侧静态颜色不随主题刷新——"主题设置完全管不到"。

本次改造按**「深色悬浮层 + 主题高亮」**策略统一主题化：控制条保持视频站标准深色半透明悬浮层（日夜间可读），进度条/选中高亮跟随主题强调色；弹框动态设色接入 ThemeStore 背景/文字色 + UiCorner 圆角。

## 核心能力

- 播放器控制条（底部进度条/时间/倍速/静音/弹幕开关）主题化
- 倍速弹框（ChoiceSpeedDialog）动态设色
- 选集弹框（ChoiceEpisodeDialog）动态设色
- 画面比例/音轨原生 AlertDialog 接入项目主题
- 旧模式功能区/调试面板硬编码色清理
- 硬编码中文文案迁移 strings.xml

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 状态标记

- [x] 🔄 设计中（四文档已生成，待用户审查）
- [x] ✅ 设计完成（用户 2026-08-24 检查点1 通过）
- [x] 🔄 开发中
- [x] ✅ 本轮静态收尾（2026-08-24：编译门禁+updateLog+文档同步闭环；真机验证 3.3-3.5 延后，待有视频源数据/真机时补做）

## 变更记录

- 2026-08-24：初始建立。需求分析确认策略：控制条深色悬浮层+主题高亮；弹框优化现有 View 弹框（动态设色）。
- 2026-08-24：实施完成（编译门禁通过）。VideoPlayer 新增 applyThemeColors()（进度条/缓冲/圆点取 accentColor）+ init/RECREATE/onConfigurationChanged 触发；倍速/选集弹框容器动态设 ThemeStore.backgroundColor+UiCorner.panelRadius、选中高亮 accentColor；画面比例/音轨走 alert() 主题化；删除旧模式功能区与调试面板；硬编码中文迁移 strings.xml。待真机验证。
