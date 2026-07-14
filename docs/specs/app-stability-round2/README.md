# App Stability Round 2 修复

> 基于 10026 版本（07-13 编译）日志分析的残留问题修复。日志显示该版本零崩溃（R4/R5 修复生效），但残留 3 个 P1 功能异常 + 2 个 P2 体验问题。

## 功能概述

本项目针对 10026 版本日志反馈"还有好多问题"的残留问题进行第二轮稳定性修复，覆盖订阅文章加载、图片显示、视频播放三类核心场景，以及 Cronet/DNS 与协程取消两个体验问题。

## 核心能力

| 编号 | 级别 | 问题 | 影响场景 |
|------|------|------|---------|
| P1-1 | Bug#5 | Room SQLiteBlobTooBigException | 订阅文章列表加载 |
| P1-2 | Bug#3 | 图片解密 IllegalBlockSizeException | 图片显示 |
| P1-3 | Bug#4 | ExoPlayer UnrecognizedInputFormatException 3003 | 视频播放 m3u8 |
| P1-4 | - | 视频链接自动抓取正则兜底误匹配阻塞嗅探 | 视频播放（用户不填规则时自动抓取） |
| P2-1 | - | Cronet/DNS 高频失败 | 网络请求 |
| P2-2 | - | 协程取消异常 | 视频播放退出/嗅探 |

## 文档索引

- [spec.md](./spec.md) - 需求规格（Intent / Scope / Approach / Requirements / Scenarios）
- [design.md](./design.md) - 技术设计（ADR Y-Statement / Data Flow / File Changes）
- [tasks.md](./tasks.md) - 任务清单（实施步骤）

## 状态

🔄 设计中

## 关联文档

- 上一轮修复：`docs/specs/video-playback-issues-round1/`
- 日志分析报告：见 appLog 归档（07-13 编译版本）

## 关键核实结论

- **Bug#5**：`RssArticlesAdapter.convert`（L54-97）仅使用 title/pubDate/image/read/origin，**不使用 description**，原 DAO 注释为错误信息，可安全去掉 description 字段
- **Bug#3**：`ImageUtils.decode(InputStream)`（L53-87）完全无块大小校验；`decode(ByteArray)`（L24-51）块校验有漏洞（块对齐≠已加密）
- **Bug#4**：`ExoPlayerHelper.createMediaItem`（L50-54）拼接 SPLIT_TAG 到 uri 破坏类型检测；`setDefaultHeaders`（L150-152，R5 已实现）可复用
