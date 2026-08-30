# sniff-stability-enhance-20260731（嗅探稳定性增强）

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 🔄 部分实施（9 项 FR 大体已落地；FR-3 路径直通部分，走 videoStreamClient 路线）

## 功能概述

针对真机测试 sniff-result-pipeline-fix 正式包后用户反馈"整体效果比之前好多了，但我期望更好"，深度分析新日志识别出 9 个仍需优化的稳定性问题，通过 R5 嗅探去重锁、DoH 负缓存优化、视频流强制 HTTP/1.1、favicon.ico 缓存、StreamReset 重用 NonCancellable、Cronet 探测日志采样、证书错误记忆缓存、play.php 类 URL 预解析、window.__videoUrls__ 解析容错等手段，系统性消除嗅探浪费、协议错误、日志噪声与首帧延迟方差，全面提升嗅探稳定性。

## 核心能力

| 编号 | 优先级 | 名称 | 目标 |
|------|--------|------|------|
| FR-1 | P0 | R5 嗅探去重锁 | VideoUrlExtractor 层对同一 path 的 R5 嗅探请求加内存锁，消除 41% 浪费率（41 次启动 17 次重复） |
| FR-2 | P1 | DoH 负缓存时长优化 + 健康检查 | 负缓存 30s → 10s，启动时探测 DoH 服务器（21 条 DoH 失败日志，1 次熔断） |
| FR-3 | P1 | 视频流强制 HTTP/1.1 | 对视频流域名禁用 h2，消除 ERR_HTTP2_PROTOCOL_ERROR（3 次协议错误） |
| FR-4 | P1 | favicon.ico 缓存 | 内存 + 磁盘缓存 24 小时，消除 137 次网络请求 |
| FR-5 | P2 | StreamReset 重用 NonCancellable | 避免 Activity 切换取消重试（1 次重试失败因 Canceled） |
| FR-6 | P2 | Cronet 探测跳过日志采样 | 152 次噪声降为汇总输出 |
| FR-7 | P2 | 证书错误记忆缓存 | 5 分钟内同 host 不重复 Cronet 尝试（约 10 次 ERR_CERT_AUTHORITY_INVALID） |
| FR-8 | P3 | play.php 类 URL 预解析 | 降低首帧延迟方差（701~5309ms，7.5 倍差距） |
| FR-9 | P3 | window.__videoUrls__ 解析容错 | JSON.parse 失败时正则提取（1 次解析失败） |

## 修复目标

- R5 嗅探浪费率从 41% 降到 < 5%
- DoH 失败率显著降低
- HTTP/2 协议错误归零
- favicon.ico 网络请求降到 0（命中缓存）
- StreamReset 重试成功率提升
- 日志噪声减少 90%
- 首帧延迟方差降低

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 功能规格说明（需求与验收标准） |
| [design.md](./design.md) | 技术设计（实现方案与架构） |
| [tasks.md](./tasks.md) | 任务分解（实施清单与进度） |

## 测试包配置

| 包类型 | 包名 | 用途 |
|--------|------|------|
| 测试包 | `io.legado.miss.app.debug` | 代码优化用测试包（debug 构建，含调试日志，未混淆） |
| 正式包 | `io.legado.miss.app.release` | 交付用正式包（release 构建，验证生产环境真实行为） |

## 任务背景

- **触发时间**：2026-07-31 19:41
- **触发来源**：用户真机测试 sniff-result-pipeline-fix 正式包（legado_miss_app_3.26.073118.apk）后反馈
- **用户原话**：整体效果比之前好多了，但是我期望更好
- **分析依据**：深度分析新日志 logs(8)..zip（解压到 extracted_8/）生成分析报告，识别 9 个仍需优化的问题
- **日志分析报告**：`docs/issues/user/temp/20260731/002/extracted_8/log_analysis_report.md`
