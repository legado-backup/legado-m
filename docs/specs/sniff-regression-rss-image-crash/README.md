# 嗅探回归与图片订阅源崩溃取证修复

## 状态

✅ 全闭环（2026-08-30）
- 嗅探回归：WebView 池全局互斥修复，真机 L2 3/3 PASS
- 图片订阅源崩溃：**根因模拟器真实复现并修复**（ImageCanvasViewModel 后台 appendItems vs 主线程 notify 竞态 → RecyclerView Inconsistency FATAL；修复后连续 3 轮 L2 全绿）+ Phase B 定向防御 4 项（H4/H6/H1/H3）
- 取证链路：真实崩溃栈回灌实证（12:08 真实崩溃 → 下次启动 appLog 携带 CrashReport 分块真实栈）

## 功能概述

本次修复包含两个用户反馈问题：

1. **视频嗅探能力下降**：系统浏览器打开链接可正常播放视频，但 App 内置嗅探失败（以前可用，疑似近期回归）。
   - 根因已定位（源码核实）：`bbc9d0a89`（08-19）WebView 池按场景分层（GLOBAL/DISCOVERY/RSS）后，`release()`/`acquire()` 中的 `pauseTimers()`/`resumeTimers()` 是**进程级 API**，却只按**单一 scope** 的 `inUsePool.isEmpty()` 判断。发现页/订阅页 WebView 释放时会误冻结 GLOBAL 池中正在嗅探的 WebView JS，导致嗅探 6 秒窗口内 JS hook 全部失效而超时。
2. **浏览图片订阅源崩溃**：本次日志包（logs.zip）**未捕获崩溃时刻**（无 FATAL/crash buffer，7 份 appLog 均不含崩溃栈）。App 已有 CrashHandler 兜底，崩溃栈会落盘到 `外部缓存/crash/crash-*.log`，但该文件不在用户提供的日志包内。
   - 本次策略：**取证优先 + 取证链路增强**（日志导出附带 crash 文件），拿到真实崩溃栈后二次修复；同时不排除图片浏览栈（ImageGalleryActivity/ImageCanvasViewModel 等有 crash-2026-07-26 前科）的已知防护遗漏。

## 核心能力

- 修复进程级 `pauseTimers`/`resumeTimers` 的 scope 隔离误判，恢复视频嗅探能力
- 增强日志导出取证能力：导出内容附带 crash 目录最近崩溃文件
- 为图片订阅源崩溃建立取证闭环（用户复现 → crash 文件自动随日志导出 → 精准修复）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（含 ADR Y-Statement） |
| [tasks.md](./tasks.md) | 任务清单 |

## 证据索引

- 崩溃日志分析结论：logs.zip 无崩溃栈（0 个 FATAL/AndroidRuntime 命中），仅 2 次疑似静默进程死亡会话，均与图片订阅源浏览界面无直接关联
- 嗅探回归证据：[WebViewPool.kt](../../../app/src/main/java/io/legado/app/help/webView/WebViewPool.kt) L98-100 / L168-170 仅按 scope 判断进程级 API
- 回归引入提交：`bbc9d0a89`（08-19，WebViewPool 288 行分层重构）
