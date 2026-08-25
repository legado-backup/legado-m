# 图片订阅源加载优化（参考书源加载机制）

> 功能名称：图片订阅源加载优化（RSS Image Load Optimization）
> 状态：🔄 开发中（实施完成，编译验证中）

## 功能概述

图片类型订阅源（type=1 / 图片浏览）在进入图集浏览、切换文章、左右滑动图片时，加载速度明显慢于图片类型书源。本功能通过参考图片类型书源的加载机制（本地磁盘缓存 + 内存 LRU + 采样解码 + 并发批量下载），对订阅源图片的「URL 解析链路」与「图片加载链路」进行针对性优化，目标是让图片订阅源的首图出现速度、切图流畅度达到与书源图片接近的体验。

## 核心能力

1. **URL 解析结果缓存**：缓存「文章 → 图片 URL 列表」解析结果，避免每次切换文章重复网络请求文章页 + 触发 WebView 嗅探（最大 6s 延迟）。
2. **图集采样解码**：图集模式（ImagePageAdapter）从「全尺寸解码」改为「按屏幕尺寸采样解码」，显著降低大图解码耗时与内存压力。
3. **多图并发预下载**：进入文章时对图片列表前 N 张并发预下载到磁盘缓存，滑动时秒开。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach（含 Alternatives Considered + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：Technical Approach / ADR Y-Statement / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 实施任务清单（`- [ ] X.Y` 格式）+ AOAdapt 日志 |

## 状态标记

- [x] 🔄 设计中（四文档已生成，待用户审查）
- [x] ✅ 设计完成（2026-08-24 用户确认方案；附加硬约束：嗅探不回归 FR-7、翻页不回归 FR-8）
- [ ] 🔄 开发中
- [ ] ✅ 已完成

## 相关文档

- 图片订阅源链路分析：[rss-image-type-analysis.md](../../project-flow/modules/rss-image-type-analysis.md)
- 图片画布优化：[image-player-vertical-canvas-optimization](../image-player-vertical-canvas-optimization/README.md)
- 图片嗅探优化：[image-sniffer-optimization](../image-sniffer-optimization/README.md)
- 图集浏览：[image-gallery-activity](../image-gallery-activity/README.md)
