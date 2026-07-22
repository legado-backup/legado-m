# TVBox 优化方案（借鉴影视仓 FongMi/TV 优化 legado）

> **状态**：🔄 设计中
> **创建日期**：2026-07-22
> **目标版本**：legado 后续迭代
> **参考实现**：影视仓（FongMi/TV）项目架构

## 功能概述

本方案通过借鉴影视仓（FongMi/TV）项目的优秀架构设计，对 legado（阅读M）项目进行四个方向的优化升级。影视仓作为成熟的影视聚合播放器，在播放器引擎、网络爬虫、投屏、本地服务等方面有诸多可借鉴之处，本方案在保留 legado 阅读器核心定位的前提下，针对性引入影视仓的技术亮点。

## 核心能力（四个优化方向）

| 方向 | 目标 | 借鉴点 |
|------|------|--------|
| **1. 播放器优化** | 双引擎架构 + 弹幕/字幕/嗅探/预加载完整化 | ExoPlayer + MPV 双引擎、DanmakuSetting、TrackUtil、Sniffer、PreloadSetting |
| **2. 网络层优化** | 多引擎脚本 + 爬虫框架抽象 | catvod Spider 抽象、Chaquopy Python 嵌入、QuickJS |
| **3. DLNA 投屏** | 新增完整 DLNA 投屏能力 | jupnp 完整 DLNA 模块（Search/Control/Render） |
| **4. 本地服务器** | 远程控制 API 增强 | NanoHTTPD 远程控制 API 设计 |

## 现状对比

### legado 现状
- 播放器：GSYVideoPlayer + ExoPlayer（`help/gsyVideo/` + `help/exoplayer/ExoPlayerHelper.kt`），无双引擎切换
- 弹幕：仅有 `DanmakuAdapter.kt` + `BiliDanmukuParser.kt`，无完整弹幕设置系统
- 嗅探：`help/video/VideoUrlExtractor.kt`，功能较基础
- 字幕：缺失
- 预加载：`VideoPlay.kt` 中有简单配置
- 网络层：OkHttp + Cronet + Rhino JS 引擎
- DLNA：**完全缺失**
- 本地服务器：`web/HttpServer.kt`（NanoHTTPD），仅支持书源/书籍/RSS CRUD

### 影视仓参考点
- 双引擎：ExoPlayer（硬解）+ MPV（软解）切换，`PlayerEngineFactory` 工厂模式
- 弹幕系统：`Danmaku` + `DanmakuSetting` 完整设置
- 字幕管理：`Track` + `TrackUtil` 多轨道选择
- 嗅探：`Sniffer` 智能嗅探
- 预加载：`PreloadSetting` 完整预加载策略
- 爬虫框架：catvod `Spider` 抽象 + Chaquopy Python + QuickJS
- DLNA：jupnp 完整实现
- 本地服务器：`Nano.java` 远程控制 API

## 文档索引

| 文档 | 内容 |
|------|------|
| [README.md](./README.md) | 本文档：功能概述与索引 |
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：技术方案/ADR 决策/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单：按四个方向分组的具体任务 |

## 实施原则

1. **阅读器定位不变**：legado 核心是电子书阅读器，优化不改变主定位
2. **渐进式引入**：四个方向可独立实施，互不阻塞
3. **最小侵入**：优先扩展而非重写现有模块
4. **源码核实**：每个借鉴点需对比影视仓源码与 legado 现状，禁止凭经验臆测
5. **真机验证**：所有变更必须真机测试通过

## 风险与约束

- **依赖体积**：MPV/Chaquopy/jupnp 均会增加 APK 体积，需评估必要性
- **兼容性**：legado minSdk 低于影视仓（minSdk 24），部分 API 需降级处理
- **维护成本**：双引擎/多脚本引擎增加长期维护负担
- **性能影响**：Python 嵌入会增加启动时间和内存占用

## 相关规范

- 项目主规范：`AGENTS.md`
- 编码哲学：`docs/project-rules/coding-philosophy.md`（极简≠残缺）
- 改造日志：`docs/project-rules/logging-during-refactoring.md`
- 版本交付同步：`docs/project-rules/version-delivery-sync.md`
- 真机测试流程：`docs/project-rules/real-device-test-reuse.md`
