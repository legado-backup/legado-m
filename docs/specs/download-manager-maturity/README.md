# 下载器成熟化改造（download-manager-maturity）

## 功能概述

Legado 当前的下载能力是 `video-download-manager` 引入的自研引擎（`DownloadService` + `ChunkDownloader` + `HlsDownloader` + `DownloadState`），在"能下载、能转 mp4、有管理页"层面已可用，但离一个**成熟的通用下载器**仍有明显差距：任务只存内存、无断点续传、无真实暂停、无并发上限、无失败自动重试、通知 id 不稳定、remux 曾触发 native 崩溃杀进程导致任务消失。

本规格先**盘点全量下载入口**（回应"除播放器外还有哪些入口"），再按严重度**分级补齐缺口**（稳定性 → 任务能力 → 工程健壮性），把"能用"推进到"可靠、可续、可控"。

## 全量下载入口（真实盘点 = 6 个发起点 + 1 个管理页入口）

本题有两种入口：**发起下载**（调用 `Download.start`）与 **打开下载管理页**。

| # | 入口场景 | 入口文件 | 触发动作 | 任务类型 | 防盗链头 |
|---|---------|---------|---------|---------|---------|
| 1 | 内置视频播放器 | `VideoFragment.kt:787` | 播放器下载按钮 | 显式 HLS/DIRECT | ✅ 播放头 |
| 2 | 应用 / 书源更新 | `UpdateDialog.kt:128` | 更新弹窗"下载" | URL 自动判断 | ❌ 默认 UA |
| 3 | 网页浏览器 | `WebViewActivity.kt:358` | 长按下载链接 | URL 自动判断 | ❌ 默认 UA |
| 4 | RSS 阅读器 | `ReadRssActivity.kt:448` | 长按下载链接 | URL 自动判断 | ❌ 默认 UA |
| 5 | 底部 WebView 弹窗 | `BottomWebViewDialog.kt:404` | 长按下载链接 | URL 自动判断 | ❌ 默认 UA |
| 6 | 下载管理页重试 | `DownloadManageActivity.kt:119` | 管理页重新下载 | 按原任务 | 按原任务 |
| M | 打开下载管理页 | `PreciseManageFragment.kt:33` | 精准管理 → 下载管理 | — | — |

> 结论：除播放器外，Web/RSS/BottomWebView/Update 四类是**同一个 WebView 下载监听摸板**（均 `Download.start` + URL 后缀判断），无防盗链头，m3u8 自动走 HLS 引擎，但都不传播放头（防盗链源需逐个补齐）。统一治理入口时优先在这 4 处收敛为共用下载行为。

## 核心缺口（对照成熟下载器）

| 级别 | 缺口 | 现状 | 目标 |
|------|------|------|------|
| 稳定性 | 任务不持久化，进程被杀即丢 | `DownloadState` 纯内存 | Room 持久化任务 + 断点续传 |
| 稳定性 | remux native SIGABRT 杀进程 | csd 缺失时崩溃 | 已加 csd 校验回退 ts（本次闭环） |
| 任务能力 | 无真实暂停 / 恢复 | `PAUSED` 是死分支 | 可暂停/恢复单任务 |
| 任务能力 | 并发无上限 + 无排队 | 每次 start 直接 launch | 并发上限 + FIFO 排队 |
| 任务能力 | 失败无自动重试 | 一次失败即 FAILED | 指数退避自动重试 |
| 工程健壮性 | 通知 id 用 size 计算、反查按 index | 多任务会错位 | 稳定 id 映射 |
| 工程健壮性 | 无错误码/分阶段状态 | 失败原因不明 | 错误码 + 分阶段生命周期 |
| 工程健壮性 | 无网络策略入口 / 完整性校验 | 无条件直下、下完不校验 | 右上角设置『仅WiFi/任意网络』(无限速，默认全可下) + size 校验 |
| 目录生产级 | 下载产物藏 app 私有目录，用户找不到 | `getExternalFilesDir` 私有目录 | 默认公有 Downloads/Legado，可配置 + 权限流程 |
| 管理页 | 删除语义不清、无二选；样式/提示语弱 | 仅清记录/连删文件混用 | 删任务保留文件 + 删任务清文件、二次确认；UI/提示语进 strings.xml |

## 成熟方案调研（2026-08，网上核实）

| 候选 | 结论 |
|------|------|
| Aria2Android（aria2 引擎） | 需打包多 ABI 原生二进制显著增大 APK；**不支持 m3u8→mp4 转码**（核心缺失）；无 UI 仍要自包 RPC 服务，复杂度不降反升 → 否决 |
| 开源 Kotlin 下载器（AndroidFrok/Downloader 类） | 自带断点续传/网络监控/校验，但 m3u8 转 mp4 与防盗链头仍需自研，引入依赖违背版本锁定基因 → 不引入，改为复刻其成熟功能点 |
| **自研增量加固（选定）** | 在现有 `DownloadService` 骨架补齐 Room 持久化/断点续传/暂停/并发/重试/错误码/通知稳定/网络感知/完整性校验 → 与本项目 CoC 契合、无新依赖、APK 不变大 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式） |

## 状态标记

🔄 **设计中**（需求分析完成，待用户审查检查点 1）