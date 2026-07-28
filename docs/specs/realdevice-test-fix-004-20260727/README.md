# realdevice-test-fix-004-20260727

> 004 真机测试问题修复——视频播放器初始化失败 + 嗅探超时 + 网络层冷启动问题

## 背景

用户 2026-07-27 真机测试反馈：整体视频嗅探和播放成功率有所提升，但还存在两类问题：
1. **第一个视频总是失败**：一个订阅源进去第一个视频总是失败的，下拉或切换另外一个就好了，感觉是内置视频播放器初始化有点问题
2. **部分视频嗅探失败**：还有一些视频没抓取到

## 真机日志

- 日志路径：`issues/user/temp/20260727/004/Downloadslogs(1).(4)..zip`
- 日志分析报告：`docs/temp-analysis/realdevice-004-analysis-20260727.md`

## 核心问题（5 个根因，已基于 12219 行日志逐行核实修正）

| 编号 | 问题 | 优先级 | 根因（修正后） |
|------|------|--------|------|
| V-004-P0-1 | 首帧渲染延迟 4808ms（用户感知"第一个视频失败"） | P0 | DoH 全部失败等待 DNS 解析 + 嗅探 3123ms + 子 m3u8 加载 1s |
| V-004-P0-2 | 18:48-19:16 期间 9 次 Activity 启动但播放器未初始化 | P0 | AppLog 未输出（可能 App 异常状态）+ initSource 失败无日志 + Activity 快速切换 |
| V-004-P1-1 | DoH 冷启动失败累计 6-9s 延迟 | P1 | DoH 服务器 UnknownHostException，3 次失败才熔断，每次 2-3s |
| V-004-P1-2 | Cronet Request Canceled 日志噪音 | P1 | 用户切换视频时请求被取消，日志输出 ERROR 级别干扰 |
| V-004-P2-1 | 嗅探耗时 3123ms | P2 | DoH 失败期间 Range 请求等待 DNS 解析 |

> **修正说明**：spec.md v1 中"Activity 重建/BUFFERING timeout/3003 错误"根因均未在 004 日志中发生，已全面重写。

## 文档导航

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 功能规范：问题清单 + 验收标准 |
| [design.md](./design.md) | 技术设计：架构分析 + 修复方案 |
| [tasks.md](./tasks.md) | 任务清单：Phase 分解 + 实施步骤 |

## 修复策略

### Phase A（P0 修复）
- V-004-P0-1: DoH 冷启动优化（首次失败立即走系统 DNS + 异步预热）+ 嗅探前 DNS 预解析 + 子 m3u8 预取
- V-004-P0-2: AppLog 初始化保障 + VideoPlay.initSource 失败日志记录 + Activity 快速切换保护

### Phase B（P1 修复）
- V-004-P1-1: DoH 熔断阈值优化（冷启动场景首次失败即熔断，不等 3 次）
- V-004-P1-2: Cronet Request Canceled 日志降级为 DEBUG

### Phase C（P2 优化）
- V-004-P2-1: 嗅探前 DNS 预解析（与 P0-1 合并实施）

### Phase D（验证 + 打包）
- 编译验证 + updateLog 更新 + 打包测试包

## 关键文件

| 文件 | 说明 |
|------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 视频 Activity，排查重建根因 |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | 视频 Fragment，播放器生命周期 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | ExoPlayer 封装，BUFFERING 超时 + 降级链 |
| `app/src/main/java/io/legado/app/help/exoplayer/PlayerInstancePool.kt` | 播放器实例池 |
| `app/src/main/java/io/legado/app/help/http/cronet/CronetHelper.kt` | Cronet 引擎，预热 |
| `app/src/main/java/io/legado/app/help/http/dns/DohDns.kt` | DoH DNS，回退策略 |
| `app/src/main/AndroidManifest.xml` | VideoPlayerActivity configChanges 声明 |
