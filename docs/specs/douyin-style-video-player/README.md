# 抖音风格沉浸式竖屏视频播放器重设计

> **状态**：✅ 设计通过（OpenSpec 检查点1 第5次通过）
> **创建日期**：2026-07-10
> **依赖**：R2 日志分析结论（3003 Bug 修复）

## 功能概述

将当前传统竖屏 LinearLayout 布局的 VideoPlayerActivity 重构为抖音/红果短视频风格的沉浸式竖屏视频播放器，支持垂直滑动切换视频、悬浮控件叠加、三种播放状态切换。

## 核心能力

1. **沉浸式竖屏全屏**：视频画面铺满整个屏幕，沉浸式体验
2. **ViewPager2 垂直滑动切换**：上下滑动切换播放列表中的视频
3. **三种播放状态**：纯净播放态 / 竖屏常态 / 横屏全屏态
4. **悬浮控件叠加**：左下角标题 + 右侧功能按钮（静音/收藏/倍速/设置）
5. **横屏适配**：等比缩放居中 + 全屏按钮 + 双指缩放手势
6. **100%功能保留**：当前所有功能重新组织到设置面板
7. **3003 Bug 修复**：R5 识别播放器页面 URL 并提取实际视频流
8. **多线路支持**：视频详情页多播放线路（RssRoute 二级数据结构 + 左下方线路选择器 + 集数选择器 + 兼容单集/多集无线路场景）
9. **ruleContent JS 标准规范**：三种标准数据格式（嵌套JSON/扁平JSON/多行URL）+ MacCMS/80s/嵌套三种 ruleContent 模板 + R5 MacCMS指纹自动识别（5站点验证覆盖率60%+20%+20%）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |

## 与现有 spec 的关系

| 关联 spec | 关系 |
|-----------|------|
| `rss-video-player-enhancement` | 前置 spec（R1-R5 + 3.17 Bug修复已完成），本 spec 在其基础上重构 UI 层 |
| `video-player-optimization` | 历史 spec（P0-1/2/3 + P1-1/2/4 完成），本 spec 整合其已完成功能 |
