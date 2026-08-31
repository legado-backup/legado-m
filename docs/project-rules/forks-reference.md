# 延伸版本参考与对比方法论（forks-reference）

> **AI 在进行网络层/前端/协程/WebView 等组件优化时，必须主动对比以下延伸版本的实现，学习借鉴优点，不闭门造车。**
> 来源：[阅读·全版本集散地](https://momoa.cc.cd/%E4%B8%8B%E8%BD%BD/xz)（41+ 版本；旧地址 momo-b5a.pages.dev 已失效，2026-08-16 更新）
> 上游活跃度快照（2026-07-16 ~ 2026-08-16 实测）：**原版 gedoor 已停更**（最后推送 2026-05-27）；活跃上游依次为 喵公子（14 release）、阅读T（30 提交）、MD3（27 提交）、阅读Archive（46 提交，relay 子系统）、阅读NG（Compose 迁移）、legado-E（仅 EPUB 修复 PR#451）；蛋蛋Max/阅读R/辞晨 零提交。详见 `docs/specs/archive/sync-upstream-optimizations-20260816/README.md` §1.1。

## 主线分支（基于原版，网络层与原版基本一致）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 原版阅读 | [gedoor/legado](https://github.com/gedoor/legado) | 所有 fork 的源头；**2026-05 起停更，仅作历史基线** | ⭐⭐⭐（回归对照） |
| 阅读Sigma | [Luoyacheng/legado-E](https://github.com/Luoyacheng/legado-E) | 本项目 fork 源 | ⭐⭐⭐⭐⭐ |
| 喵公子阅读 | [LegadoTeam/legado](https://github.com/LegadoTeam/legado) | **事实上的活跃上游**（release 最频繁） | ⭐⭐⭐⭐⭐ |
| 阅读T | [skybbk1001/legadoT](https://github.com/skybbk1001/legadoT) | 主流分支；活跃（TextDialog 搜索/HttpTTS 字段/原生加密替代 hutool——解锁 hutool 地雷的参考路径） | ⭐⭐⭐⭐ |
| 阅读Archive | [Rimchars/legado](https://github.com/Rimchars/legado) | 主流分支 | ⭐⭐⭐ |
| 阅读R | [refgd/legado](https://github.com/refgd/legado) | 主流分支 | ⭐⭐ |
| Jingshiro阅读 | [Jingshiro/legado](https://github.com/Jingshiro/legado) | 主流分支 | ⭐⭐ |

## Max 系列（蛋蛋Max 衍生，网络层有 307/308 重定向等优化）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 蛋蛋阅读·Max | [DandanLLab/Legado_Max](https://github.com/DandanLLab/Legado_Max) | Max 系列源头，307/308 重定向优化 | ⭐⭐⭐⭐⭐ |
| 怣疯阅读·Max | [youfengknight/Legado_Max](https://github.com/youfengknight/Legado_Max) | 蛋蛋Max 衍生 | ⭐⭐ |
| Suml-1阅读·Max | [Suml-1/Legado_Max](https://github.com/Suml-1/Legado_Max) | 蛋蛋Max 衍生 | ⭐⭐ |

## 独立分支（前端/MD3/跨平台改造）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 阅读NG | [joestar817/legado_NG](https://github.com/joestar817/legado_NG) | 网络日志标签等优化 | ⭐⭐⭐⭐ |
| 阅读C | [CCSSNE/legadoC](https://github.com/CCSSNE/legadoC) | **阅读R/Archive 系兄弟分支（own 分支，约周更）**：朗读架构原语化重构（全 fork 独有：发布层原语/纯函数跟随/绘制期投影/EMA 预测换页）、正文多媒体插入体系、AI 净化规则沉淀、合集书架虚拟 Book、用户日志勾选；⚠️ 0 Compose/无 CI 无 E2E 无沙箱；深度对标完成见 specs/legadoc-benchmark-analysis/ | ⭐⭐⭐⭐⭐（朗读/阅读体验域） |
| 辞晨阅读·Max | [GEd520/legados](https://github.com/GEd520/legados) | 辞晨系列 | ⭐⭐⭐ |
| MD3阅读 | [HapeLee/legado-with-MD3](https://github.com/HapeLee/legado-with-MD3) | Material3 前端改造 | ⭐⭐⭐⭐（前端） |
| MD3阅读-DIY | [325506/legado-with-MD3-DIY](https://github.com/325506/legado-with-MD3-DIY) | MD3 衍生 | ⭐⭐⭐（前端） |
| 喵公子鸿蒙 | [mgz0227/legado-Harmony](https://github.com/mgz0227/legado-Harmony) | 鸿蒙适配 | ⭐⭐ |
| Legado-Tauri | [LegadoTeam/Legado-Tauri-Release](https://github.com/LegadoTeam/Legado-Tauri-Release) | Tauri 桌面端 | ⭐⭐ |

## 独立项目（非 Legado fork，可参考架构）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| MoRealm | [keys-cherish/morealm-reader](https://github.com/keys-cherish/morealm-reader) | 独立阅读器 | ⭐⭐ |
| 书享阅读 | [zyl140640/readbook-releases](https://github.com/zyl140640/readbook-releases) | 独立阅读器 | ⭐⭐ |
| 轻悦时光 | [autobcb/qysg](https://github.com/autobcb/qysg) | 独立阅读器 | ⭐⭐ |
| IReader | [IReaderorg/IReader](https://github.com/IReaderorg/IReader) | 独立阅读器 | ⭐⭐ |
| LightNovelReader | [dmzz-yyhyy/LightNovelReader](https://github.com/dmzz-yyhyy/LightNovelReader) | 轻小说专用 | ⭐⭐ |

## 对比优先级矩阵

| 优化领域 | 优先对比版本 | 原因 |
|----------|------------|------|
| **网络层** | 蛋蛋Max > 阅读T > 阅读Archive | 蛋蛋Max 有 307/308 重定向；阅读T 有 SOCKS5 隧道+Brotli；⚠️ 阅读NG 网络层经 2026-08-30 逐文件 diff 实测为本项目超集（本项目有熔断降级/DoH/Brotli 等），不再列为网络层对比对象 |
| **AI 能力** | 阅读NG（唯一） | 全 fork 生态唯一具备完整 AI 体系（供应商抽象/MCP 服务端/上下文压缩/技能包），已完成深度对标与迁移设计（specs/ng-benchmark-analysis/） |
| **听书/TTS** | 阅读NG（唯一） | 唯一具备多角色 AI 演播（五级路由+分镜），本项目单音色 |
| **书源安全** | 阅读NG（唯一） | 唯一成体系的书源安全沙箱（文件命名空间/Cookie 隔离/类策略/弹窗拦截 8 项） |
| **协程/多线程** | 蛋蛋Max > 阅读Archive | 蛋蛋Max 修复了 CancellationException 反模式（阅读NG 该项与本项目同为超集关系，无增量） |
| **WebView** | 阅读Archive > 蛋蛋Max > 阅读NG | 阅读Archive 有 closed 标志 + isActiveWebView 修复范式 |
| **前端** | 蛋蛋Max > MD3阅读 | 仅蛋蛋Max 有前端实质增量（备份功能） |
| **数据管理** | 蛋蛋Max > 阅读Archive | 蛋蛋Max 有 Web 端备份功能 |

## 五阶段对比流程

```
Phase 1: 准备阶段 → Phase 2: 分类对比 → Phase 3: 差异识别 → Phase 4: 价值评估 → Phase 5: 借鉴决策
(预检+浅克隆)     (按组件维度)     (逐文件对比)     (收益/风险评分)   (输出决策表)
```

## 关键踩坑警示

- ⚠️ **GitHub git trees API 有缓存错误**：所有结论以 `git clone --depth 1` 实测为准
- ⚠️ **仓库 404 不等于不存在**：可能是改名/私有/删除，需在 [阅读·全版本集散地](https://momoa.cc.cd/%E4%B8%8B%E8%BD%BD/xz) 查新地址（旧地址 momo-b5a.pages.dev 已失效）
- ⚠️ **前端源码在 `modules/web/`**：不是 `app/src/main/assets/web/`（后者是构建产物）
- ⚠️ **PowerShell curl 别名冲突**：使用 `curl.exe` 或 `Invoke-WebRequest`
