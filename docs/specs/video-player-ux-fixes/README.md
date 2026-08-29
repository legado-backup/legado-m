# 视频播放器体验五项修复

## 状态

🔄 开发中 → ✅ 实施完成（编译门禁 BUILD SUCCESSFUL 2026-08-29；L2 真机/模拟器验证待执行）

## 功能概述

针对内置视频播放器（`ui/video/` 模块）用户反馈的 5 个体验问题进行集中修复：

1. **下载按钮隐藏**：播放本地已下载视频（`file://` 直连）时，右侧"下载"按钮应隐藏（对本地文件再次下载无意义）
2. **滑动快进灵敏度可配置**：左右滑动 seek 当前为比例式（滑满全屏宽≈全片长），用户感知"太快"；新增设置项调整灵敏度（0.5x~2x 档位）
3. **配置弹框透明修复**：右上角"配置设置"弹出的 `SettingsDialog` 背景透明（window 透明 + 内容无壳），且内部取色未遵循 ui-standards 弹框规范，需对齐 `AppDialogFrame` 规范壳
4. **全屏标题移位**：全屏播放时视频标题从左下角移到左上角返回图标右侧
5. **全屏返回按钮对齐规范**：`btn_back_overlay` 图标净尺寸 24dp 偏大，收敛到 20dp 对齐 GlassTopAppBar R4 档

## 核心能力

- 播放器按播放源类型（本地文件 / 在线流）自适应显隐下载入口
- 滑动 seek 灵敏度用户可配置，持久化到 `video_config` SharedPreferences
- 设置弹框（Dialog 壳）与 BottomSheet 壳双入口视觉统一，符合 ui-standards/dialog-shell.md
- 全屏态信息层级优化：标题归位顶栏，左下角保留线路/集数选择器

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：架构决策（ADR）/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式）+ AOAdapt 日志 |

## 关联规范

- `docs/project-flow/ui-standards/dialog-shell.md`（弹框壳规范）
- `docs/project-flow/ui-standards/color.md`（取色门禁：禁 `colorScheme.surface` 族）
- 硬约束：视频播放器手势体系整体评估（上下滑切视频/左右滑 seek/长按倍速/双击暂停 保留不动）
