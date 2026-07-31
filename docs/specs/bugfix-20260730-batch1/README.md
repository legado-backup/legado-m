# Bug修复批次1 - 2026-07-30 真机测试问题修复

> 状态: ✅ 分析完成

## 功能概述

基于用户2026-07-30真机测试（正式包 v3.26.072917，Redmi 23078RKD5C，Android 16）发现的5个表面BUG + 3个日志深度分析发现的隐藏BUG + 7-30日志深度分析新发现的4个隐藏BUG，共12个问题的修复方案。

## 修复状态总览

| BUG | 描述 | 严重度 | 状态 |
|-----|------|--------|------|
| BUG1 | 图片播放器第一张图被头部遮挡 | P0 | ⚠️ 代码已修复，用户仍报出，需验证优化 |
| BUG2 | 播放器优化功能5项无UI入口 | P1 | ⚠️ 代码已修复，用户仍报出，需验证控件ID |
| BUG3 | CDN 530错误缓存清除不生效 | P0 | ✅ 已修复验证通过 |
| BUG4 | "未找到订阅"提示语需隐藏 | P1 | ✅ 已修复验证通过 |
| BUG5 | ExoPlayer LoadControl共享线程错误 | P0 | ✅ 已修复验证通过 |
| BUG6 | DoH DNS冷启动全链路失败 | P1 | ✅ 机制已完善，无需额外修改 |
| BUG7 | Cronet协议错误降级不彻底 | P1 | ✅ 机制已完善（新发现BUG6-V2需优化） |
| BUG8 | InsetsSource警告 | P2 | ⏭️ Android 16系统问题，维持不处理 |
| BUG6-V2 | Cronet恢复探测误判导致降级震荡 | P1 | 🆕 待修复 |
| BUG7-V2 | DNS negative cache导致已失败host不重试 | P1 | 🆕 待修复 |
| BUG8-V2 | rssRoutes为空解析遗漏 | P2 | 🆕 待修复 |
| BUG9-V2 | DNS解析到0.0.0.0回环超时 | P1 | 🆕 待修复 |

## 核心能力

- 修复图片播放器第一张图被头部遮挡（需验证优化）
- 补齐播放器优化功能的UI入口（5项功能，需验证控件ID匹配）
- 修复CDN 530错误后清除缓存不彻底（✅已修复）
- 隐藏"未找到订阅"多余提示（✅已修复）
- 修复ExoPlayer LoadControl共享线程错误（✅已修复）
- 修复Cronet恢复探测误判导致降级震荡（🆕待修复）
- 修复DNS negative cache导致已失败host不重试（🆕待修复）
- 修复rssRoutes为空解析遗漏（🆕待修复）
- 修复DNS解析到回环地址超时（🆕待修复）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：12个BUG的Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：架构决策ADR(AD-01~AD-08) + 数据流 + 文件变更 |
| [tasks.md](./tasks.md) | 任务清单：按优先级排列的实施任务 |

## 问题来源

- 用户测试报告：`docs/issues/user/temp/20260730/001/bug.md`
- 日志包：`docs/issues/user/temp/20260730/001/Downloadslogs.(7)..zip`
- 正式包版本：v3.26.072917（io.legado.miss.app.release）
- 测试设备：Redmi 23078RKD5C，Android 16，SDK 36

## 新发现隐藏BUG摘要（7-30日志深度分析）

| BUG | 根因 | 证据 | 修复方案概要 |
|-----|------|------|-------------|
| BUG6-V2 | 恢复探测用可达host而非失败host | 5轮降级-恢复-再降级震荡 | 改用失败host+观察窗口期+指数退避 |
| BUG7-V2 | DNS negative cache TTL过长 | 多次negative cache hit不重试 | 失败TTL上限30秒+网络恢复清除缓存 |
| BUG8-V2 | ruleRoutes空字符串!=null判断 | routesNull=true, routesSize=0 | isNullOrBlank()替代!=null |
| BUG9-V2 | DNS劫持解析到0.0.0.0 | Failed to connect to [::]:443 15s超时 | 过滤回环/不可路由地址 |
