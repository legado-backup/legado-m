# Skill Trio 优化：三个 Legado Skill 的 AI 友好度提升

> **状态**：🔄 设计中
> **创建日期**：2026-06-18
> **最后更新**：2026-06-18

---

## 功能概述

对项目中的三个核心 Skill（`legado-source-creator`、`legado-skill-auditor`、`legado-workflow-auditor`）进行深度分析与系统性优化，解决 AI 在使用这些 Skill 时遇到的关键痛点，确保 AI 能更高效、准确地生成高质量的书源/订阅源。

### 背景

在 `skill-architecture-optimization`（v2）完成后，三个 Skill 已具备基础架构：
- 金字塔知识体系（L1-L4）
- JVM 规则引擎仿真器（MVP1-4）
- basic-memory 经验引擎
- 审计闭环

但在实际使用中发现，**AI 作为执行者而非人类开发者**，面临独特的障碍。且更关键的是：**当前 skill 缺少自进化闭环和零人工干预能力**。

### 终极目标

用户给一个网站 URL，AI 立即通过 `legado-source-creator` skill：
1. **快速生成**书源/订阅源 JSON
2. **通过内置测试脚本 + 内置服务端**，模拟真实 Legado 导入和使用全流程
3. **不需要用户在手机开源阅读客户端来回调试**
4. AI 直接输出"已验证可用"的完美书源/订阅源
5. 每次 AI 使用 skill 时，skill **自动进化**（经验 + 客户端 + 服务端），越来越精准、越来越快

### 三层进化对象

| 进化层 | 内容 | 当前状态 | 优化目标 |
|--------|------|---------|---------|
| **经验层** | basic-memory 中的经验/陷阱/模式 | 有基础但写入复杂 | 自动沉淀，3 步完成 |
| **客户端层** | Python 测试脚本（verify-*.py, rule_engine_client.py） | 仅语法验证 | 升级为全流程模拟器 |
| **服务端层** | JVM 仿真器（MinimalMockJsExtensions.kt, AnalyzeRule.kt） | 签名不一致+缺 80+ 函数 | 自动检测缺失并进化 |

### 进化收敛机制（防止无限进化）

| 机制 | 说明 | 目标 |
|------|------|------|
| **进化次数上限** | 同一问题最多进化 3 次，超过则标记"需人工介入" | 避免死循环 |
| **进化收敛判断** | 精准度 >90% 后降低进化频率，>95% 后仅记录不自动进化 | 避免过度进化 |
| **进化冲突检测** | 同一函数被多次进化时，保留最新版本+版本号追溯 | 避免版本混乱 |
| **进化死循环检测** | 相同错误在 24 小时内重复出现 3 次时终止进化 | 避免资源浪费 |

### 必须人工干预边界（明确零干预的极限）

| 场景 | 可否零干预 | 说明 |
|------|-----------|------|
| 普通 CSS/XPath 规则网站 | ✅ 可零干预 | 全流程模拟器可覆盖 |
| 含 JS 但无加密的网站 | ✅ 可零干预 | JVM 仿真器可执行 |
| 含 AES/DES 加密的网站 | ✅ 可零干预 | hutool 加密可仿真 |
| CloudFlare 保护（JS Challenge） | ⚠️ 需配置 | 检测后提示配置 loginUrl，非自动通过 |
| 需要账号密码登录的网站 | ❌ 必须人工 | AI 无法获取用户凭证 |
| 需要人工过验证码的网站 | ❌ 必须人工 | AI 无法识别图形验证码 |
| 网站结构变化导致规则失效 | ⚠️ 需确认 | AI 检测到失效后提示用户确认新结构 |

---

## 核心问题总览（三 Skill 联合分析发现）

| 维度 | source-creator | skill-auditor | workflow-auditor |
|------|---------------|--------------|------------------|
| **P0 问题数** | 3 | 3 | 2 |
| **P1 问题数** | 6 | 5 | 4 |
| **P2 问题数** | 6 | 4 | 3 |
| **P3 问题数** | 5 | 4 | 3 |
| **合计** | **20** | **16** | **12** |

### Top 10 跨 Skill 共性问题

| 排名 | 问题 | 影响 Skill | 根因 |
|------|------|-----------|------|
| 1 | 检查点/流程步骤超出 AI 单次上下文能力 | 三者皆是 | 未考虑 AI token 预算限制 |
| 2 | 字段定义/检查项跨文件不一致 | source-creator + workflow-auditor | 独立维护，未统一数据模型 |
| 3 | basic-memory 操作复杂度过高 | 三者皆是 | 7步双写流程对 AI 过于繁琐 |
| 4 | 缺少自动化检测/决策辅助工具 | skill-auditor + source-creator | 全手动操作，效率低且易遗漏 |
| 5 | 降级路径不统一 | 三者皆是 | 各自设计，无通用模式 |
| 6 | 文档数量描述与实际不符 | source-creator + skill-auditor | 增量修改后未同步数字 |
| 7 | 审查框架自身存在它要检查的问题 | skill-auditor | 元问题：A3 数量标注错误 |
| 8 | MockJsExtensions 函数签名与源码不一致 | source-creator | 增量开发时未同步最新签名 |
| 9 | Phase 切换条件/测试失败标准模糊 | source-creator + workflow-auditor | 依赖 AI 自行判断，无明确阈值 |
| 10 | Skill 间协作边界不清，触发词重叠 | 三者皆是 | 无全局触发词表和调用链路图 |

---

## 核心能力（优化后预期）

> **注**：标记 `[test-infra-upgrade]` 的能力由 test-infra-upgrade Spec 提供，本 Spec 依赖但不重复实现。

| 能力 | 当前状态 | 优化后目标 | 归属 |
|------|---------|-----------|------|
| **AI 单次任务完成率** | ~60%（上下文溢出导致跳步） | >90%（分层+精简） | 本 Spec |
| **JVM 测试误判率** | ~15%（签名不一致导致） | <3%（修复签名+明确未实现清单） | [test-infra-upgrade] L5/L6 |
| **审计可执行性** | ~40%（42项过多+字段缺失） | >80%（分层审查+字段对齐） | 本 Spec |
| **basic-memory 写入合规率** | ~50%（模板复杂） | >85%（简化模板+自动校验） | 本 Spec |
| **Skill 间协作清晰度** | 低（边界模糊+触发词重叠） | 高（全局调用链路图+去重触发词） | 本 Spec |
| **端到端调试覆盖率** | ~30%（Python 仿真） | >85%（JVM 真机级） | [test-infra-upgrade] L1/L2/L7 |
| **AnalyzeUrl 覆盖率** | 0% | 90% | [test-infra-upgrade] L0 |
| **Cookie/Header 持久化** | 不支持 | 支持（内存版） | [test-infra-upgrade] L4 |
| **JsExtensions API 覆盖率** | 20% | 70%+ | [test-infra-upgrade] L5 |
| **调试日志与真机一致性** | 0%（无日志） | 100%（格式完全一致） | [test-infra-upgrade] L3 |
| **全流程模拟覆盖率** | ~35% | >85% | [test-infra-upgrade] L1+本 Spec 进化增强 |
| **零人工干预率** | ~20% | >80% | 本 Spec（依赖 test-infra-upgrade 基础设施） |
| **自进化触发率** | ~10% | >90% | 本 Spec FR-7 |
| **精准度（真机一致率）** | ~60% | >90% | 本 Spec FR-7.6 |
| **进化响应时间** | N/A | <5分钟 | 本 Spec FR-11.1 |
| **AI 执行效率** | ~30分钟 | <10分钟 | 本 Spec FR-11.2 |
| **首次通过率** | ~20% | >60% | 本 Spec FR-11.3 |
| **进化收敛率** | N/A | >95% | 本 Spec FR-9 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 分组任务清单（含优先级和验收标准） |

---

## 与已有 Spec 的关系

| 已有 Spec | 关系 | 本 Spec 定位 |
|----------|------|-------------|
| `skill-architecture-optimization` (v2) | 前置基础 | 在其成果上做 **AI 友好度优化**，非推翻重来 |
| `skill-html-fetch-enhancement` | 并行独立 | HTML 获取能力增强，与本 Spec 的 Skill 流程优化互补 |
| **`test-infra-upgrade`** | **底层依赖** | test-infra-upgrade 提供**端到端调试基础设施**（AnalyzeUrl 移植、BookSourceDebugger、CookieStore、MockJsExtensions 扩展、debug-source.py），本 Spec 在此基础上构建**自进化闭环**和**零人工干预上层能力** |
| `skill-improvement` | 可能重叠 | 需确认是否已覆盖本 Spec 的部分内容 |

### 与 test-infra-upgrade 的分工边界

| 能力 | 归属 | 说明 |
|------|------|------|
| AnalyzeUrl 移植 | test-infra-upgrade L0 | URL 解析三步流水线 |
| 端到端 debugBookSource/debugRssSource | test-infra-upgrade L1/L2 | search→detail→toc→content 全链路 |
| CookieStore 内存实现 | test-infra-upgrade L4 | 二级域名 Cookie 管理 |
| MockJsExtensions 扩展（ajax/connect/加密） | test-infra-upgrade L5 | 网络类+加密类函数补齐 |
| Book/BookSource 上下文注入 | test-infra-upgrade L6 | evalJS 注入 13 个变量 |
| 增量日志输出（真机级格式） | test-infra-upgrade L3 | `[mm:ss.SSS] ︾︽⇒┌└≡◇` 格式 |
| deep-verify.py 改用 JVM | test-infra-upgrade L7 | 废弃 Python 仿真 |
| **自进化闭环** | **本 Spec FR-7** | 测试失败→自动分析根因→分类进化→重新验证 |
| **进化收敛机制** | **本 Spec FR-9** | 防止无限进化（次数上限+收敛判断+冲突检测） |
| **必须人工干预边界** | **本 Spec FR-10** | 明确零干预极限（登录/验证码/CF） |
| **速度度量** | **本 Spec FR-11** | 进化响应时间+AI执行效率+首次通过率 |
| **网络请求安全机制** | **本 Spec FR-8.9** | 频率控制+UA伪装+超时重试（test-infra-upgrade 未覆盖） |
| **进化反馈循环** | **本 Spec FR-8.6** | 用户手机端反馈→进化→下次更精准 |

---

## 分析方法说明

本次优化基于以下分析方法：

1. **源码对比法**：逐文件对比 Skill 文档与 Legado 项目源码（JsExtensions.kt / BookSource.kt / RssSource.kt / AnalyzeRule.kt / RssParserByRule.kt）
2. **AI 模拟执行法**：模拟全新 AI agent 仅凭 SKILL.md 执行完整工作流，记录每个歧义点和阻塞点
3. **交叉验证法**：三个 Skill 两两对比，识别不一致和冲突
4. **历史经验法**：参考 skill-auditor 的 25 个高频问题和 7 轮审查经验
