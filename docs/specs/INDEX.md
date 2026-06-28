# 项目状态面板

> 最后更新：2026-06-22

## 项目概况

| 项目 | 值 |
|------|------|
| 名称 | Legado（阅读Sigma） |
| 类型 | Android 应用 |
| 语言 | Kotlin + Java |
| 最低SDK | 21 |
| 目标SDK | 36 |
| 数据库版本 | 89 |

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| app（主应用） | 🟢 稳定 | 核心功能完整 |
| modules/rhino | 🟢 稳定 | JS 引擎封装 |
| modules/book | 🟢 稳定 | 书籍解析基础库 |
| modules/web | 🟢 稳定 | Vue3 Web 管理界面 |

## 功能状态

| 功能 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| 书源搜索 | 🟢 完成 | P0 | 多书源并发搜索 |
| 书籍阅读 | 🟢 完成 | P0 | 文本/音频/漫画/视频 |
| 规则引擎 | 🟢 完成 | P0 | CSS/JSONPath/XPath/正则/JS |
| 本地书籍 | 🟢 完成 | P1 | EPUB/TXT/PDF/MOBI/UMD |
| RSS 订阅 | 🟢 完成 | P1 | RSS 源管理与阅读 |
| Web 管理 | 🟢 完成 | P1 | NanoHTTPD + Vue3 |
| WebDAV 同步 | 🟢 完成 | P2 | 多设备同步 |
| 替换净化 | 🟢 完成 | P2 | 正则替换规则 |
| TTS 朗读 | 🟢 完成 | P2 | 系统 TTS + HTTP TTS |

## 🔴 进行中的工作

### 设计中

| 功能 | 优先级 | 说明 | 文档 |
|------|--------|------|------|
| **Legado Skill 统一优化重设计** | P0 | **新版统一 OpenSpec**：基于全面审计的优化重设计，合并6套历史OpenSpec未完成项。9方向3阶段任务清单，目标保真度≥95%/自动化率>70%/端到端准确性100% | [legado-skill-unified-redesign/](./legado-skill-unified-redesign/) |
| **Legado Skill 整体优化方案** | P0 | 统一 OpenSpec（旧版）：三层协作架构，27方向268项任务，完成率5.6%，已被统一优化重设计替代 | [legado-skill-optimization/](./legado-skill-optimization/) |
| Skill 可用性优化 | P1 | SKILL.md精简+分级工作流+降级策略+触发词统一，71项0%完成率 | [skill-usability-optimization/](./skill-usability-optimization/) |
| JVM 仿真服务端 WebView 支持+测试修复 | P0 | DebugResult数据结构+WebView委托+经验提取，解决测试假通过率问题 | [jvm-webview-and-test-fix/](./jvm-webview-and-test-fix/) |
| 源修复闭环优化 | P0 | 仿真保真度+可观测性+经验闭环+文档治理（16方向），基于源码深度分析发现80+个真实痛点 | [source-repair-loop-optimization/](./source-repair-loop-optimization/) |

### 已完成

| 功能 | 优先级 | 说明 | 文档 |
|------|--------|------|------|
| 测试基础设施升级 | P0 | 端到端真机级调试（AnalyzeUrl移植+BookSourceDebugger+RssSourceDebugger+流式日志+debug-source.py），代码实现完成，测试验证缺失 ⚠️ | [test-infra-upgrade/](./test-infra-upgrade/)（已归档） |
| Skill HTML 获取能力增强 | P0 | HTML获取回退链+CMS样本库+Playwright集成+CF绕过三级策略 | [skill-html-fetch-enhancement/](./skill-html-fetch-enhancement/)（已归档） |
| Skill 架构优化 | P0 | basic-memory经验引擎+JVM仿真器MVP1-3+固化脚本+权威源双写+审计者 | [skill-architecture-optimization/](./skill-architecture-optimization/)（已归档） |
| Skill 改进 | P0 | legado-source-creator Skill 对标阅读Skill 补齐 Default 语法/全局对象 API/高级技巧 | [skill-improvement/](./skill-improvement/)（已归档） |

## 待处理

| 项目 | 类型 | 优先级 | 说明 |
|------|------|--------|------|
| OpenSpec 目录清理 | 文档治理 | P1 | 10 套旧 OpenSpec 待归档到 archive/（见下方清单） |

## 归档

已完成的功能和修复记录在 `archive/` 目录。

### 待归档清单（10 套旧 OpenSpec）

以下目录已完成使命或已被统一文档合并，建议归档到 `archive/`：

| # | 目录 | 归档原因 |
|---|------|---------|
| 1 | skill-improvement | 已完成且已实施 |
| 2 | skill-architecture-optimization | 已完成且已实施 |
| 3 | skill-html-fetch-enhancement | 已完成且已实施 |
| 4 | test-infra-upgrade | 已完成且已实施 |
| 5 | jvm-extract-refactor | 已完成且已实施 |
| 6 | skill-trio-optimization | 已完成且已实施 |
| 7 | simulation-fidelity-95 | 已被 legado-skill-optimization 合并 |
| 8 | python-client-optimization | 已被 legado-skill-optimization 合并 |
| 9 | skill-deep-optimization-v2 | 重叠/被覆盖 |
| 10 | pageindex-local-experience-engine | 孤立无引用 |

### 保留的活跃目录（5 套）

| # | 目录 | 保留原因 |
|---|------|---------|
| 1 | legado-skill-unified-redesign | **最新统一 OpenSpec**（合并6套历史spec） |
| 2 | legado-skill-optimization | 旧版统一 OpenSpec（已被unified-redesign替代，保留供参考） |
| 3 | jvm-webview-and-test-fix | WebView 委托+测试修复（已完成，待归档） |
| 4 | source-repair-loop-optimization | 源修复闭环（已完成，待归档） |
| 5 | skill-core-capability-rebuild | 差距报告来源（simulation-gap-report.md 被统一文档引用） |
