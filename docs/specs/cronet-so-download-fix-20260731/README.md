# Cronet SO 下载修复 + 嗅探能力恢复

> **状态**: ✅ 已实施（CronetLoader md5 重下/DoH 国内源/新类接线源码实证，勾选已同步）
> **创建时间**: 2026-07-31
> **功能名称**: cronet-so-download-fix-20260731
> **优先级**: P0（用户反馈"嗅探能力明显减弱"+"好多地方都闪退"）

## 功能概述

基于真机日志（Downloadslogs(4).(2)..zip）深度分析发现：V3 ProGuard 修复后真机不崩溃了，Cronet native engine 也成功加载，**嗅探能力减弱的真正根因**是：

1. **DoH（加密 DNS）3 个服务器全部失败**：cloudflare/google/quad9 的 bootstrap IP 在国内网络环境不可达，导致 UnknownHostException，连续失败后禁用 DoH 5 分钟，期间所有新域名走系统 DNS（可能被污染）
2. **Cronet HTTP/2 协议错误**：部分 CDN 站点与 Cronet 的 HTTP/2 实现不兼容（ERR_HTTP2_PROTOCOL_ERROR），累计 5 次后降级到 OkHttp，OkHttp 的 Conscrypt TLS 指纹被部分 CDN 拒绝
3. **Cronet 连接被拒绝**：ERR_CONNECTION_REFUSED，部分域名因 DoH negative cache 而无法解析

同时，虽然当前 Cronet SO 动态下载从 Google Storage 成功完成（md5=ec7fafb9 匹配），但 Google Storage 在国内网络环境不稳定，未来可能出现下载失败导致 Cronet 降级 JavaCronetEngine（TLS 指纹被 CDN 拒绝）。用户决策要求"修复下载逻辑 + 换下载源"以提升长期稳定性。

## 核心能力

| 能力 | 描述 |
|------|------|
| **DoH 服务器配置修复** | 替换国内不可达的 bootstrap IP，增加国内可用的 DoH 服务器（阿里/腾讯） |
| **HTTP/2 协议错误优化** | 优化 Cronet HTTP/2 错误的降级策略，避免过度降级 OkHttp |
| **SO 下载源切换** | 从 Google Storage 切换到 GitHub Releases（国内可访问） |
| **下载逻辑修复** | 修复 `downloadFileIfNotExist` 已损坏文件处理逻辑 |
| **嗅探超时恢复** | 从 3s 恢复到 5s，改善弱网场景嗅探成功率 |

## 文档索引

| 文档 | 描述 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（按 `- [ ] X.Y` 格式） |

## 真机日志关键发现

基于 `docs/issues/user/temp/20260731/001/extracted_v4/logs/appLog-26-07-31_09-12-34.018.txt` 深度分析：

### ✅ 已修复（V3 ProGuard 修复成果）
- Cronet native engine 成功加载：`engine=CronetUrlRequestContext, costMs=165`
- SO 文件 md5 匹配：`md5=ec7fafb9`
- manualLoad 成功：`loaded /data/user/0/io.legado.miss.app.release/app_cronet/arm64-v8a/libcronet.150.0.7871.128.so`
- 无 SIGABRT 崩溃（V3 修复 internal.org.jni_zero.GEN_JNI 被移除问题）
- 嗅探成功：`sniffVideoType: success, contentType=2, elapsed=984-1319ms`
- 视频播放成功：`ExoPlayer play success (STATE_READY), first frame rendered 577ms/1812ms`

### ❌ 真正问题（本次要修复）
- **DoH 全失败**：3 个服务器（cloudflare-dns.com/dns.google/dns.quad9.net）bootstrap IP 全部 UnknownHostException
  - 冷启动熔断 30s + 连续失败熔断 5min
  - 期间所有新域名走系统 DNS（可能被污染）
- **Cronet HTTP/2 协议错误**：`net::ERR_HTTP2_PROTOCOL_ERROR, ErrorCode=11, InternalErrorCode=-337`
  - 累计 5 次后降级 OkHttp 5 分钟
  - OkHttp 的 Conscrypt TLS 指纹被部分 CDN 拒绝
- **Cronet 连接被拒绝**：`net::ERR_CONNECTION_REFUSED, ErrorCode=7, InternalErrorCode=-102`
  - 部分域名因 DoH negative cache 而无法解析
- **HttpHelper 预连接失败**：`stream was reset: PROTOCOL_ERROR`

## 关联文档

- 前序任务：[cronet-proguard-fix-20260731](../cronet-proguard-fix-20260731/README.md)（V3 ProGuard 修复 SIGABRT 崩溃）
- 打包规范：[docs/project-rules/package-naming.md](../../project-rules/package-naming.md)
- ProGuard 规则：[app/proguard-rules.pro](../../../app/proguard-rules.pro)
- 真机测试流程：[docs/project-rules/real-device-test-reuse.md](../../project-rules/real-device-test-reuse.md)
