# ExoPlayer 韧性优化（两层防护）

> 状态标记：🔄 设计中（R1 修订：去除 videoType 字段，纯运行时自动判断）
> 创建时间：2026-07-26
> 任务来源：用户反馈 3002 错误码 + "浏览器能播放但内置播放器报错"痛点

## 功能概述

针对内置视频播放器（ExoPlayer）在视频网站规则千差万别场景下频繁报错的问题，设计两层防护机制：

1. **内容嗅探层**：读取 HTTP 响应前 1KB，按 magic number 判断真实格式（mp4/m3u8/flv/ts），覆盖 URL 后缀不可靠场景
2. **自动降级层**：ExoPlayer 失败次数累计达阈值 + 不可恢复错误类型时，自动切换到 WebView 播放模式（复用现有 `switchToWebViewMode` 机制）

## R1 修订记录（2026-07-26 用户反馈）

**去除 videoType 字段设计**。原方案 Layer 3"源规则声明"被否决，原因：

> "为什么要加字段，让原作者声明呢？声明只能声明一个，一个网站如果列表的视频是多种类型呢？声明个屁"

核心痛点：
- 一个源列表中视频可能是 m3u8 + mp4 混合，单字段无法表达
- 让源作者声明是负担，源作者不应该被强制要求
- 显式声明会误判多类型混合源

新方向：**纯运行时自动判断**，每个视频 URL 独立嗅探，无需源作者介入。

## 核心能力

| 防护层 | 解决的问题 | 触发条件 | 兜底方案 |
|--------|-----------|---------|---------|
| 内容嗅探 | URL 后缀不可靠、动态 URL 无后缀、多类型混合源 | OkHttp 拦截器层自动执行（每个视频请求独立嗅探） | 嗅探失败回退到 URL 后缀检测 |
| 自动 WebView 降级 | ExoPlayer 严格解析失败 | 失败次数≥3 + 不可恢复错误（3002/3003/3005/decoder类） | 自动调 `switchToWebViewMode` |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（按 `- [ ] X.Y` 格式） |

## 影响范围

- **源码修改**：`ExoPlayerHelper.kt`、`Exo2MediaPlayer.kt`、`VideoPlayerActivity.kt`、`VideoFragment.kt`、`EventBus.kt`
- **新增文件**：`SniffingMimeTypeInterceptor.kt`、`MimeSniffer.kt`
- **网络层**：注册嗅探拦截器到 okHttpClient 链
- **不涉及**：ExoPlayer 核心库、视频缓存架构、Cronet/OkHttp 降级机制、RssSource 实体、数据库迁移

## 已知上限

- 内容嗅探增加 1KB 首次请求开销（仅首次，后续命中缓存无开销）
- 自动 WebView 降级会切换播放器，用户感知"播放器闪烁"
- 嗅探对 302 重定向场景需特殊处理（读最终响应）
