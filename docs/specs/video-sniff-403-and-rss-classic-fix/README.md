# 视频嗅探引擎架构级重构（统一播放/下载嗅探）+ 订阅经典模式布局修复 + 线程数上限提升

> 状态：✅ 已完成（2026-08-31，Phase 0-4 全实施+L2 真机验收+083121 闪退修复闭环，用户检查点3 待最终确认）

## 功能概述

本任务在 v2"对标 M 浏览器直连播放"基础上，经用户二轮裁决升级为**架构级整体规划**：①历史回归根因分析（嗅探曾有巅峰期后三波衰退）②目标超越 M 浏览器 ③嗅探能力抽象复用统一播放/下载 ④删除 WebView 播放器遗留债务 ⑤生产级无死角。按四层架构分五阶段（Phase 0~4）交付：

1. **视频嗅探引擎架构级重构**：统一播放/下载嗅探 + 历史回归根治 + 删除遗留债务 + 超越 M 浏览器（Phase 1~4 主体）。
2. **R2 订阅经典模式布局修复**：新版订阅模式残留 recyclerView topPadding 未在切回经典模式时重置，导致头部标签与列表间大块空白，杀进程才恢复（Phase 0 独立快修，可先行交付）。
3. **R3 更新和缓存线程数上限提升**：64→256，配套 WebView 缓存/固定线程池/HTTP 连接池钳制防护，支持高端手机（Phase 0 独立快修，可先行交付）。

**核心指标**：403 防盗链站点直连播放成功率最大化（核心判据）+ 防盗链源下载分片成功率（Phase 3 后判据）。

> **设计目标声明**：内置 WebView 播放页为历史遗留产物，整体删除而非兜底保留（摆设实锤见三大排查结论 C）；核心指标 = 直连播放成功率，WebView 降级提示不再是备选路径。

## 设计方向变更记录

| 版本 | 方向 | 结局与说明 |
|------|------|-----------|
| v1（已否决） | 403 快速降级 WebView | 预检 403/410 确定性拒绝 → 快速重嗅或直接降级 WebView 播放。**用户裁决否决**：WebView 播放页是遗留产物将废弃。 |
| v2（被升级） | SniffCandidate 上下文回传 + auth-retry-first 对标 M 浏览器 | 嗅探上下文端到端回传 + 补头重试 + 拦截面扩展 + 多候选选优。**用户二轮裁决升级**：点状修补不足以根治，升级为架构级整体规划。 |
| v3（当前） | 架构级统一引擎 + 分阶段交付 | 三大排查定根因 → 止血恢复巅峰 → 删 WebView 播放器 → SniffEngine 抽象统一 → 超越 M 浏览器，每 Phase 独立门禁。 |

## 三大排查结论摘要

### A. 历史回归根因（巅峰 → 三波衰退）

- **巅峰期（07-13~18）四支柱**：15s/3s 超时 + 直连兜底 + OkHttp Cookie 闭环 + 单层嗅探。
- **第一波衰退（07-26）**：超时砍半 + 删直连兜底 + 双层嗅探。
- **第二波衰退（07-31）**：Cronet Cookie 断链 + 预检静默回退。
- **第三波衰退（08-19）**：WebView 池误冻结（已修复）。
- **先天缺陷**：shouldInterceptRequest 丢 headers 自诞生即有——嗅探命中只回传 URL，WebView 真实请求头（Cookie/Referer/UA）全部丢弃。

### B. 下载链路分叉

- 下载无独立嗅探：100% 复用播放断链头，恢复场景二次丢失，防盗链源下载分片必然失败。
- HlsDownloader 自研 m3u8 解析与播放侧分叉：能力无法复用，双轨维护。

### C. WebView 删除可行（摆设实锤）

- 模板 setRequestHeader('Referer') 被 Chromium forbidden header 规范静默忽略——WebView 播放页从未真正解决防盗链，属遗留债务。
- 依赖面收敛为 10 文件清单，可安全整体删除（Phase 2 执行）。

**小结**：A 决定 Phase 1 止血方向（回传上下文+恢复直连兜底语义），B 决定 Phase 3 统一方向（引擎+共享解析），C 决定 Phase 2 删除动作。

## 现状能力全景盘点（四轮反馈补强）

针对四轮用户反馈"对现状能力了解不全面"，补充三份现状盘点报告：

- [video-sniff-capability-inventory.md](../../temp-analysis/video-sniff-capability-inventory.md)
- [video-play-capability-inventory.md](../../temp-analysis/video-play-capability-inventory.md)
- [video-scenario-network-inventory.md](../../temp-analysis/video-scenario-network-inventory.md)

共沉淀 **13 条关键结论（Z1-Z13）**，已全部纳入 [design.md](./design.md)「零章：现状能力全景」+ AD-12，并同步到 spec.md（R-P1-8/9、R-P3-7/8/9、Out of Scope）。最重要的 5 条：

| # | 结论 | 影响 |
|---|------|------|
| Z1 | **视频级预加载整体禁用态**（旧预加载 NPE 未修） | Phase 3 预加载重设计（R-P3-7，AD-12）替代 |
| Z2 | **DataSource 头全局互覆盖**（多工厂共享全局头槽位） | HeaderResolver 统一下发的直接动因 |
| Z3 | **AES key 双路径漂移**（HlsKeyDataSourceFactory 仅接旧入口，主链路未覆盖） | R-P1-8 接入主链路 applyMediaSourceByType |
| Z4 | **SimpleCache 缓存键不一致**（原始 URL 与嗅探后地址混用） | R-P3-7/8 统一 finalUrl |
| Z6 | **Cronet + DoH 唯一结合点 = 错误回退链**（无用户配置项，现状无"Cronet 换 DoH"设置） | AD-11 保持隐式协作，不做配置化，customHost 注入评估登记 Phase 4 |

> 其余 8 条（Z5/Z7-Z13：isPreparing 死代码、cronet 开关双逻辑、书源空正文降级、播放历史字段缺失、SSL 校验旁路等）详见 design.md 零章与三份盘点报告原文。

## v3 核心架构（四层）

- **SniffEngine 统一嗅探引擎**：四层发现流水线（复用 playerPageCache / r5InProgress / VIDEO_SNIFF_JS 资产）+ 上下文回传 + auth-retry + 多候选评分。
- **HeaderResolver 统一头组装**：播放/下载/预检共用，嗅探上下文优先 → 源配置兜底 → Cookie 兜底注入；headersJson 持久化。
- **M3u8Parser 共享解析模块**：下沉 HlsDownloader 自研 m3u8 解析能力，播放/下载共用，消除分叉。
- **调用方**：播放（全量嗅探）/ 下载（按需嗅探：播放地址未就绪时）/ 预检（probe 并入引擎）。

调用链（文字箭头链）：

播放/下载/预检 调用方 → SniffEngine 四层发现 → 上下文回传（SniffCandidate：URL+Referer+UA+Cookie） → 多候选评分 → HeaderResolver 头组装 → 播放器 CronetDataSource / HlsDownloader 分片请求

解析链（文字箭头链）：

m3u8 master 地址 → M3u8Parser（variant 感知） → 媒体分片列表 → 播放 / 下载共用

网络栈定位（AD-11，用户三轮追问澄清）：**Cronet 保留为主网络栈不回退 OkHttp**（默认启用是爬取优化决策：QUIC/h3/连接复用/TLS 指纹接近浏览器；历史"Cronet Cookie 断链"是注入机制未跟上而非 Cronet 缺陷，修复=Cronet 链路补注入）；**DoH（DohDns 双国内服务器）保留不废弃**，播放预解析 preResolveDns 一致化改走 DohDns（现状系统 DNS 不一致），Cronet 内置 resolver 因平台限制保持现状靠预热弥补。

## 核心能力清单（按 Phase 组织）

1. **Phase 0**：经典模式标签布局恢复——applyClassicRssMode 显式重置 recyclerView padding + folderComposeView 防御性重置。
2. **Phase 0**：线程数上限 256 + 三重钳制——WebViewPool 缓存 coerceAtMost(15)、固定线程池 min(n,128)、ConnectionPool 128 扩容。
3. **Phase 1**：SniffCandidate 嗅探上下文端到端回传——BackstageWebView 四路命中点回传 URL+Referer+UA+Cookie（对齐 design F-02 四路捕获清点）。
4. **Phase 1**：止血恢复巅峰——buildPlayHeaders 收口 5 处组装点 + M3u8PreCheck auth-retry 补头重试 + Rejected 重嗅 + switchToken 守卫 + onPlayerError 403 快速重试 + R5 窗口恢复 15s/3s + 命中即收口（R-P1-10）。
5. **Phase 2**：删除 WebView 播放器（10 文件清单）——失败三通道（预检拒绝/播放错误/嗅探失败）统一提示，无 WebView 入口残留。
6. **Phase 3**：SniffEngine 抽象统一——四层发现迁移 + HeaderResolver 独立模块 + M3u8Parser 共享 + 播放/下载/预检三调用方接入 + 下载按需嗅探。
7. **Phase 3**：预加载重设计（预嗅探下一集 + 缓存键统一 finalUrl）——替代整体禁用的旧预加载（AD-12/Z1/Z4），同步清理失效配置项与修复播放历史字段（Z9）+ PlayHistory 主键方案 plan 裁决（A 改主键 + Room v109 迁移 / B 查询层去重不改 schema）。
8. **Phase 4**：超越 M 浏览器——Content-Type 拦截面扩展 + URL 模式扩展（.flv/.ts/.mpd）+ 多候选评分选优 + 播放侧 variant 感知。
9. **生产级无死角**：每 Phase 编译+L2 真机+阶段复验构建门禁，Grep 无调试日志残留，文档同步与架构守则回灌子规范。

Out of Scope（P2 登记）：AES-128 key 自解密 / DASH 完整支持（variant 感知仅播放侧基础选优）。

## 红队审查与修订记录

- **2026-08-31 双红队审查**（七攻击面逐项审查 + 源码锚点实锤抽查）：
  - design 红队：**0 BLOCKER / 8 MAJOR** → 报告 `docs/temp-analysis/video-design-redteam-20260831.md`（F-01~F-12 编号）；
  - spec/tasks 红队：**1 BLOCKER（R-07 窗口恢复传递断链）/ 18 MAJOR** → 报告 `docs/temp-analysis/video-spec-tasks-redteam-20260831.md`（R-01~R-34 编号）。
  - **处置结论：全部发现已修复或登记**——R-P1-10 窗口恢复+命中即收口补录（spec/tasks 2.3a）、R-P1-3 auth-retry 预算语义修正（F-05）、PlayHistory 主键 plan 裁决项（4.8e，A 迁移/B 查询去重）、单测任务 4.9 补齐（R-05）、S5/S9 续传/S11/S12 验证任务补齐（2.8e/4.10）、四阶段 stop-daemons 清场补齐（R-21）、样本基线任务 6.9 补齐（R-28）、固化用例沉淀强制化（R-30）；其余（R-P1-1 四路命中点、备份导入校验 3.6a、playerType 持久化迁移 3.8a、预填独立工厂 4.8d、.html 排除规则 5.5b 等）逐项落到对应任务编号。修订后可进入 plan 阶段。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（问题定义、目标、非目标、验收标准） |
| [design.md](./design.md) | 技术设计（四层架构、Phase 划分、代码改动点、风险分析） |
| [tasks.md](./tasks.md) | 实施任务清单（Phase 0~4 分阶段任务、验收标注与验证项） |

## 验证策略

- **每 Phase 门禁**：编译（`./gradlew compileAppDebugKotlin` → `build-legado.bat` 测试包）+ updateLog 基于 git diff 同步 + L2 真机场景验证 + 阶段复验构建（构建后 `stop-daemons.bat` 清场）。
- **核心判据**：403 站点直连播放成功（无 WebView 降级、无黑屏）+ 防盗链源下载分片成功（Phase 3 后）。
- **场景清单**：
  1. **R1 主场景**：403 防盗链源直连播放成功 + 连滑 ≥3 个视频无黑屏（迟到回调被 switchToken 守卫丢弃）；
  2. **回归保护**：正常直连源播放不误伤；
  3. **R2 场景**：经典 + 标签展示 ↔ 新版订阅往返切换，头部标签与列表间无空白残留；
  4. **R3 场景**：线程数调至 256 生效，三重钳制防护生效，旧配置 64 兼容无 OOM；
  5. **失败通道（Phase 2 验收）**：预检拒绝/播放错误/嗅探失败三通道统一提示，无 WebView 入口；
  6. **下载场景（Phase 3 验收）**：防盗链源下载分片成功（HeaderResolver 统一头贯通 + 按需嗅探生效）。
- **日志验收**：L2 验证以日志关键字为准（SniffCandidate 命中 / auth-retry / Rejected / VIDEO_PLAY_ERROR），禁止输出含域名/源名称的原始日志行。
