# 本次对话加载的完整上下文内容

> 生成时间：2026-07-14
> 说明：包含系统注入的全局规则、项目规则、用户记忆、项目记忆、最近对话主题

---

## 一、项目主规范（AGENTS.md，always_applied_workspace_rules）

> 来源：f:\myself\github\WeAgentChat\temp\legado\AGENTS.md

# Legado（阅读Sigma）

> Android 开源电子书阅读器，核心为自定义书源规则引擎（CSS/JSONPath/XPath/正则/JS 五种解析），用户编写规则即可将任意网页转化为结构化书籍资源。

## 项目来源

本项目 fork 自原版 [legado-E](https://github.com/Luoyacheng/legado-E)，在此基础上建立了私有化仓库（`https://github.com/syq17496152/legado.git`），并进行了私有化改造。遇到与原版行为不一致的问题时，应优先对比原版代码定位回归原因。

## 全局规范引用索引

> 以下通用规范已迁移到 `~/.trae-cn/user_rules/` 目录，AI 根据任务类型按需用 Read 工具加载。

| 规范文件 | 内容 | 触发场景 |
|---------|------|---------|
| user_rules.md | 基础规则（中文/Windows/叫爸爸/驱动入口） | 系统自动注入 |
| danger-ops.md | 危险操作安全规则 | 系统自动注入 |
| rule-1782963384927.md | AskUserQuestion 强制规范 | 系统自动注入 |
| output-safety.md | 输出安全与违禁词规避规范 | 系统自动注入 |
| core-spec.md | 全局规范索引 | 系统自动注入 |
| context-recovery.md | 上下文压缩恢复规范 | 压缩恢复后加载 |
| coding-philosophy.md | 编码哲学规范 | 编码任务加载 |
| openspec-workflow.md | OpenSpec 工作流规范 | OpenSpec任务加载 |
| complex-task.md | 复杂任务处理规范 | 50+文件任务加载 |
| concurrent-editing.md | 并发文件修改规范 | 多Agent并行加载 |
| budget-management.md | 输出预算管理规范 | 规避思考上限加载 |

---

## 延伸版本参考（开源阅读生态）

> **AI 在进行网络层/前端/协程/WebView 等组件优化时，必须主动对比以下延伸版本的实现，学习借鉴优点，不闭门造车。**
> 来源：[阅读·全版本集散地](https://momo-b5a.pages.dev/%E4%B8%8B%E8%BD%BD/xz)（27+ 版本）

### 主线分支（基于原版，网络层与原版基本一致）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 原版阅读 | [gedoor/legado](https://github.com/gedoor/legado) | 原版，所有 fork 的源头 | ⭐⭐⭐⭐⭐ |
| 阅读Sigma | [Luoyacheng/legado-E](https://github.com/Luoyacheng/legado-E) | 本项目 fork 源 | ⭐⭐⭐⭐⭐ |
| 喵公子阅读 | [LegadoTeam/legado](https://github.com/LegadoTeam/legado) | 主流分支，活跃度高 | ⭐⭐⭐⭐ |
| 阅读T | [skybbk1001/legadoT](https://github.com/skybbk1001/legadoT) | 主流分支 | ⭐⭐⭐ |
| 阅读Archive | [Rimchars/legado](https://github.com/Rimchars/legado) | 主流分支 | ⭐⭐⭐ |
| 阅读R | [refgd/legado](https://github.com/refgd/legado) | 主流分支 | ⭐⭐ |
| Jingshiro阅读 | [Jingshiro/legado](https://github.com/Jingshiro/legado) | 主流分支 | ⭐⭐ |

### Max 系列（蛋蛋Max 衍生，网络层有 307/308 重定向等优化）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 蛋蛋阅读·Max | [DandanLLab/Legado_Max](https://github.com/DandanLLab/Legado_Max) | Max 系列源头，307/308 重定向优化 | ⭐⭐⭐⭐⭐ |
| 怣疯阅读·Max | [youfengknight/Legado_Max](https://github.com/youfengknight/Legado_Max) | 蛋蛋Max 衍生 | ⭐⭐ |
| Suml-1阅读·Max | [Suml-1/Legado_Max](https://github.com/Suml-1/Legado_Max) | 蛋蛋Max 衍生 | ⭐⭐ |

### 独立分支（前端/MD3/跨平台改造）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| 阅读NG | [joestar817/legado_NG](https://github.com/joestar817/legado_NG) | 网络日志标签等优化 | ⭐⭐⭐⭐ |
| 辞晨阅读·Max | [GEd520/legados](https://github.com/GEd520/legados) | 辞晨系列 | ⭐⭐⭐ |
| MD3阅读 | [HapeLee/legado-with-MD3](https://github.com/HapeLee/legado-with-MD3) | Material3 前端改造 | ⭐⭐⭐⭐（前端） |
| MD3阅读-DIY | [325506/legado-with-MD3-DIY](https://github.com/325506/legado-with-MD3-DIY) | MD3 衍生 | ⭐⭐⭐（前端） |
| 喵公子鸿蒙 | [mgz0227/legado-Harmony](https://github.com/mgz0227/legado-Harmony) | 鸿蒙适配 | ⭐⭐ |
| Legado-Tauri | [LegadoTeam/Legado-Tauri-Release](https://github.com/LegadoTeam/Legado-Tauri-Release) | Tauri 桌面端 | ⭐⭐ |

### 独立项目（非 Legado fork，可参考架构）

| 版本 | git 仓库 | 特色 | 对比优先级 |
|------|----------|------|-----------|
| MoRealm | [keys-cherish/morealm-reader](https://github.com/keys-cherish/morealm-reader) | 独立阅读器 | ⭐⭐ |
| 书享阅读 | [zyl140640/readbook-releases](https://github.com/zyl140640/readbook-releases) | 独立阅读器 | ⭐⭐ |
| 轻悦时光 | [autobcb/qysg](https://github.com/autobcb/qysg) | 独立阅读器 | ⭐⭐ |
| IReader | [IReaderorg/IReader](https://github.com/IReaderorg/IReader) | 独立阅读器 | ⭐⭐ |
| LightNovelReader | [dmzz-yyhyy/LightNovelReader](https://github.com/dmzz-yyhyy/LightNovelReader) | 轻小说专用 | ⭐⭐ |

### 对比方法论（强制规范）

> **任何网络层/前端/协程/WebView/数据管理组件优化或功能借鉴任务，必须遵循** [延伸版本对比方法论规范](./docs/project-rules/forks_comparison_methodology.md) **执行对比分析，禁止闭门造车。**

#### 对比优先级矩阵

| 优化领域 | 优先对比版本 | 原因 |
|----------|------------|------|
| **网络层** | 蛋蛋Max > 阅读T > 阅读NG | 蛋蛋Max 有 307/308 重定向；阅读T 有 SOCKS5 隧道+Brotli；阅读NG 有网络日志 |
| **协程/多线程** | 蛋蛋Max > 阅读NG > 阅读Archive | 蛋蛋Max 修复了 CancellationException 反模式 |
| **WebView** | 阅读Archive > 蛋蛋Max > 阅读NG | 阅读Archive 有 closed 标志 + isActiveWebView 修复范式 |
| **前端** | 蛋蛋Max > MD3阅读 | 仅蛋蛋Max 有前端实质增量（备份功能） |
| **数据管理** | 蛋蛋Max > 阅读Archive | 蛋蛋Max 有 Web 端备份功能 |

#### 五阶段对比流程

```
Phase 1: 准备阶段 → Phase 2: 分类对比 → Phase 3: 差异识别 → Phase 4: 价值评估 → Phase 5: 借鉴决策
(预检+浅克隆)     (按组件维度)     (逐文件对比)     (收益/风险评分)   (输出决策表)
```

#### 关键踩坑警示

- ⚠️ **GitHub git trees API 有缓存错误**：所有结论以 `git clone --depth 1` 实测为准
- ⚠️ **仓库 404 不等于不存在**：可能是改名/私有/删除，需在 [阅读·全版本集散地](https://momo-b5a.pages.dev/%E4%B8%8B%E8%BD%BD/xz) 查新地址
- ⚠️ **前端源码在 `modules/web/`**：不是 `app/src/main/assets/web/`（后者是构建产物）
- ⚠️ **PowerShell curl 别名冲突**：使用 `curl.exe` 或 `Invoke-WebRequest`

> **完整方法论、对比清单、决策矩阵、踩坑案例**：[docs/project-rules/forks_comparison_methodology.md](./docs/project-rules/forks_comparison_methodology.md)

---

## 🔴🔴🔴 子规范强制加载硬约束（V2.1，解决"缩减后AI不关注子规范"问题）

> **历史教训**：以前尝试过缩减主规范，缩减后 AI 反而不去关注放在子规范文件中的规范。
> **铁证（2026-07-13）**：spec-system-optimization 实施后上下文压缩，AI 执行 OpenSpec 任务时未加载 `openspec-workflow.md` 子规范，仅根据记忆执行，导致子规范强制加载机制未生效。

> **本节内容已迁移至全局规范**：硬性约束（4条加载规则）详见 `~/.trae-cn/user_rules/core-spec.md`（按需加载）。下方"按任务类型必须加载的子规范"表为项目特定内容，保留在项目主规范中。

**按任务类型必须加载的子规范**：

| 任务类型 | 必须加载的子规范 | 触发条件 |
|---------|----------------|---------|
| OpenSpec 任务 | openspec-workflow.md | 新功能/优化/Bug修复/重构 |
| 代码变更任务 | logging-during-refactoring.md + version-delivery-sync.md | 代码优化/改造/Bug修复 |
| 复杂任务（50+文件） | complex-task-pipeline.md | 50+源文件分析/多文档验证 |
| 子代理任务 | sub-agent-quality-management.md | 使用 Agent 工具时/规避思考上限 |
| E2E 测试任务 | ai_e2e_testing_workflow.md | 代码变更后步骤5.5 |
| 书源/订阅源任务 | SKILL.md | 书源/订阅源/RSS源/阅读Legado |

---

## 复杂任务处理流程（已迁移）

> **本节内容已迁移至全局规范**：复杂任务五阶段流水线（扫描分组/并行分析/交叉验证/精准修复/导航同步）、硬性约束、反模式详见 `~/.trae-cn/user_rules/complex-task.md`（50+文件任务加载）。
> 项目特定参考：[multi-agent-analysis-spec.md](./docs/project-flow/architecture/multi-agent-analysis-spec.md)

---

## 输出与工具预算管理（已迁移）

> **本节内容已迁移至全局规范**：分级子代理策略（低/中/高风险）、单次回复输出预算、工具调用预算、禁止建议新对话等规则详见 `~/.trae-cn/user_rules/budget-management.md`（规避思考上限加载）。
> 项目特定参考：[sub-agent-quality-management.md](./docs/project-rules/sub-agent-quality-management.md)

---

## 🔴🔴 强制规则：AI 自动端到端测试（V3）

> **任何代码变更任务，在 OpenSpec 步骤 5（实施）与步骤 6（检查点 2）之间，必须执行步骤 5.5 AI 自动端到端测试。禁止跳过！**

### 子规范引用

| 子规范 | 路径 | 说明 |
|--------|------|------|
| **S13** | [ai_e2e_testing_workflow.md](./docs/project-rules/ai_e2e_testing_workflow.md) | 5.5.1~5.5.8 八步强制流程 |
| **S14** | [test-case-design-guide.md](./docs/project-rules/test-case-design-guide.md) | 双轨制 + 源码溯源字段 + 步骤语义化 |

### 八步强制流程

```
5.5.1 源码影响分析（run_e2e.py --diff HEAD~1）→ affected_modules.json
5.5.2 APK 自动发现 + MEmu 启动
5.5.3 双轨用例调度（同 TC-ID Python 优先）
5.5.4 8 类证据收集
5.5.5 规则判定（pass/fail/manual/warning）
5.5.6 manual 用例 AI agent 介入（生成 ai-prompt.md + 回填 ai_verdict）
5.5.7 五件套报告生成（report.md/json + manual_cases + affected + feedback）
5.5.8 反馈闭环触发（run_e2e.py --feedback）→ 沉淀规则/陷阱/提示词
```

### 🔴 固化层保护规则（V3）

`ai_tests/lib/` 下 9 个模块文件（M1-M9）为**固化层**，AI 不应直接修改，必须通过 OpenSpec 流程：

| 模块 | 文件 | 职责 |
|------|------|------|
| M1 | memu_controller.py | 模拟器控制 |
| M2 | apk_deployer.py | APK 部署 |
| M3 | case_parser.py | 用例解析（双轨+源码溯源） |
| M4 | ui_executor.py | UI 执行器 |
| M5 | evidence_collector.py | 8 类证据收集 |
| M6 | rule_analyzer.py | 规则判定 |
| M7 | report_generator.py | 五件套报告 |
| M8 | source_impact_analyzer.py | V3 源码影响分析 |
| M9 | source_test_generator.py | V3 B 轨测试生成 |

`config.py`（固化层）含 CRASH_PATTERNS/DB_QUERIES 等常量，扩展需 OpenSpec 流程。

### 🔴🔴 快速验证脚本层（V3.1，2026-07-11 新增）

> **用户批评（2026-07-11）**："你的测试流程为什么老是来来回回的变动呢？难道就没有一些经验或者是固定流程的脚本可以沉淀到ai_test目录下么？！！！"
>
> **用户再次批评（2026-07-11）**："你还要反思为什么有了 ai_test 你为啥不去使用，需不需要在项目规范文件中加强说明"

**根因反思**：`run_e2e.py` 面向"用例驱动全量测试"，需要完整用例解析+8类证据收集，流程太重不适合"快速L2验证某个功能"。`lib/` 模块是底层组件没有组合成快速验证脚本。导致 AI 每次在 `temp/` 目录从头创建临时脚本，用完就丢，下次又从头写。

**解决方案**：`ai_tests/scripts/` 目录下4个固定脚本，覆盖完整测试流水线。

| 脚本 | 步骤 | 用法 |
|------|------|------|
| [quick_build_install.py](./ai_tests/scripts/quick_build_install.py) | 1.编译+安装+L1 | `python ai_tests/scripts/quick_build_install.py` |
| [import_rss_source.py](./ai_tests/scripts/import_rss_source.py) | 2.导入订阅源 | `python ai_tests/scripts/import_rss_source.py <json_path>` |
| [l2_verify_video_player.py](./ai_tests/scripts/l2_verify_video_player.py) | 3.L2验证视频播放器 | `python ai_tests/scripts/l2_verify_video_player.py [--scenario SCENARIO] [--manual]` |
| [swipe_test_log.py](./ai_tests/scripts/swipe_test_log.py) | 4.SwipeTest日志分析 | `python ai_tests/scripts/swipe_test_log.py [clear\|capture\|analyze]` |

**SOP 文档**：[ai_tests/docs/fixed_test_workflow.md](./ai_tests/docs/fixed_test_workflow.md) — 测试前必读！

### 🔴🔴🔴 ai_tests 使用强制规则（V3.1，2026-07-11 新增）

| 规则 | 说明 |
|------|------|
| **测试必须用 ai_tests/scripts/** | 所有测试操作（编译/安装/L1/L2/日志分析）必须使用 `ai_tests/scripts/` 下的固定脚本 |
| **禁止 temp/ 临时脚本** | ❌ 禁止在 `temp/` 目录创建任何测试脚本，违反即返工 |
| **测试前必读 SOP** | 测试前必须先读取 `ai_tests/docs/fixed_test_workflow.md` |
| **扩展不新建** | 新增测试场景时，扩展现有脚本（添加 `--scenario` 参数），禁止创建新脚本 |
| **复用 config.py 常量** | 脚本必须 import config 常量（ADB_PATH/MEMU_ADB_HOST/PACKAGE 等），禁止硬编码路径 |
| **venv Python** | 必须使用 `ai_tests\venv\Scripts\python.exe`，禁止公共 Python |
| **全量测试用 run_e2e.py** | 需要全量用例测试时用 `run_e2e.py --tc all`，快速L2验证用 `scripts/` 下脚本 |

> **反模式（跳过5.5/不执行源码影响分析/不读取manual_cases/不触发反馈闭环/不按S14设计用例/改lib固化层不通过OpenSpec/temp/创建临时脚本/不读SOP）**：详见 [ai_e2e_testing_workflow.md](./docs/project-rules/ai_e2e_testing_workflow.md)
>
> **何时必须加载本子规范**：任何代码变更任务在 OpenSpec 步骤 5（实施）与步骤 6（检查点2）之间，必须执行步骤 5.5 AI 自动端到端测试。测试前必读 SOP：[ai_tests/docs/fixed_test_workflow.md](./ai_tests/docs/fixed_test_workflow.md)

---

## 🔴🔴🔴 强制规则：书源/订阅源自测交付流程

> **任何新生成或优化的书源/订阅源，必须经过自测通过后才能视为任务完成。禁止未经自测直接交付！**

### 核心要求

- **源码验证优先**：每一步规则编写必须先去 Legado 源码核实验证，不能凭经验臆测
- **自测不通过=未完成**：任务状态不得标记为 completed，直到自测全部通过
- **经验必须源码验证**：写入 skill 参考文档的经验教训，必须经过源码深度分析核实

### 五阶段闭环工作流

```
Phase 1: 经验优先 → Phase 2: 构建规则 → Phase 3: 测试驱动 → Phase 4: 源码深挖 → Phase 5: 经验反哺
```

> **何时必须加载本子规范**：新生成/优化书源或订阅源任务。
> **自测三阶段流水线 + 79 条 Rhino 陷阱清单 + 验证脚本**：详见 [SKILL.md](./.trae/skills/legado-source-creator/SKILL.md)

---

## OpenSpec 工作流程（已迁移）

> **本节内容已迁移至全局规范**：四文档结构（README/spec/design/tasks）、8步工作流程、子代理使用指导、检查点交互规范、三选项强制结构、Plan 模式 ExitPlanMode 前置确认详见 `~/.trae-cn/user_rules/openspec-workflow.md`（OpenSpec任务加载）。
> 项目特定参考：[openspec-workflow.md](./docs/project-rules/openspec-workflow.md) | 文档位置：`docs/specs/{功能名称}/`

---

## 🔴 上下文压缩恢复流程（由全局规范管理）

> **本机制由全局规范 `~/.trae-cn/user_rules/core-spec.md` §1 统一管理。AI 必须遵守全局规范中的：压缩恢复四件套并行读取 + 用户反馈持久化 + AskUserQuestion 响应处理 + 恢复后输出反馈清单 + 任务状态权威源规则 + basic-memory 持久化要求。**
>
> **何时必须加载全局规范**：上下文压缩恢复时（强制）、AskUserQuestion 响应后（强制）、每个 Phase 完成后（持久化决策）。
>
> **项目特定配置**（供全局规范引用）：
> - 项目主规范：`./AGENTS.md`
> - 项目记忆：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`
> - 经验索引：basic-memory（project=legado）

---

## 🔴🔴 强制规则：版本交付同步

> **任何涉及代码变更的任务完成后，必须同步更新 `assets/updateLog.md`。禁止只改代码不写更新日志！**

### 同步清单

| 变更类型 | 必须同步的文件 | 说明 |
|----------|--------------|------|
| **任何代码变更** | `app/src/main/assets/updateLog.md` | 顶部追加日期条目，写明用户可感知的变更内容 |
| **文档变更** | `docs/INDEX.md` | 更新 spec 状态标记 |
| **架构变更** | `docs/project-flow/` 相关文档 | 同步架构说明 |
| **Skill 变更** | `.trae/skills/` 相关 SKILL.md | 同步能力说明 |

### updateLog.md 格式（摘要）

```markdown
**YYYY/MM/DD**
- 变更说明1（面向用户，非技术细节）
```

> 条目追加在 `## cronet版本:` 行之后。内容面向用户，用通俗语言描述可感知的变化。
> **更新时机**：编译前更新，不是交付阶段！

> **何时必须加载本子规范**：任何代码变更任务完成后（编译前必须更新）。
> **反模式（改代码不写updateLog/只写"优化代码"无具体内容/新功能用户不知道/tasks.md完成但updateLog未更新/交付阶段才补写）+ 完整格式规范**：[version-delivery-sync.md](./docs/project-rules/version-delivery-sync.md)

---

## 🔴🔴🔴 强制规则：改造过程日志记录

> **任何代码优化、改造、Bug 修复任务，在实施过程中必须适度添加日志，帮助定位分析问题、发现隐藏问题、避免遗漏问题。禁止改造代码不加日志！**

### 核心要求

| 要求 | 说明 |
|------|------|
| **改造必加日志** | 任何代码改造（优化/Bug修复/新功能）必须在关键路径添加日志 |
| **永久+临时双轨** | 永久日志（错误处理/状态切换）用 `AppLog.put` 保留；临时日志（调试验证）用 `Log.d` 验证后移除 |
| **日志覆盖错误分支** | 所有 `catch` 块和错误码处理必须有日志，禁止异常被静默吞掉 |
| **日志内容安全** | 禁止输出完整 URL/视频域名/敏感字段，只保留路径模式（详见输出安全规范） |

### 必须加日志的 10 类场景

1. **播放器状态切换**（降级/播放/暂停/释放）
2. **错误处理路径**（所有 catch 块和错误码）
3. **网络请求关键节点**（发起/成功/失败/重试）
4. **数据库异常**（查询失败/记录跳过/超大记录）
5. **类型转换**（String→List/JSON解析）
6. **加密解密**（解密失败/数据长度异常）
7. **生命周期关键节点**（Fragment/WebView/Player 创建/销毁）
8. **配置变更**（播放器类型切换/设置变更）
9. **触摸事件流转**（事件分发/消费/穿透）
10. **JS 交互**（JS调用Native/Native调用JS）

### 临时日志使用流程（摘要）

```
添加 Log.d（统一Tag）→ 编译安装操作 → logcat抓取分析 → 发现问题修复 → 验证通过Grep移除 → 重新编译确认
```

> **何时必须加载本子规范**：代码优化/改造/Bug修复实施过程（必加日志）。
> **完整规范（10类场景详细说明+日志级别+Tag规范+临时/永久双轨+反模式+验证检查清单）**：[logging-during-refactoring.md](./docs/project-rules/logging-during-refactoring.md)

---

## 项目核心 Skill：legado-source-creator

> **本项目核心工具**：Legado 书源/订阅源智能创建器。79 条陷阱检查、5 阶段闭环工作流、10 大参考目录、16 个验证脚本、JVM 仿真器（legado-jvm.jar，覆盖率 85-90%）。

**触发条件**：用户提到「书源」「订阅源/RSS源」「阅读/Legado」「网站→JSON」「修复/优化源」时，必须使用本 skill。

### 5 阶段闭环工作流（流程骨架）

```
Phase 1: 经验优先 → Phase 2: 构建规则 → Phase 3: 测试驱动 → Phase 4: 源码深挖 → Phase 5: 经验反哺+代码进化
(先查skill文档)    (按规则写源)      (JVM/Python验证)    (失败时深入源码)    (新经验写入skill+JVM/Python代码更新)
```

### 🔴🔴🔴 强制规则：Phase 完成标志与审计

> **使用 legado-source-creator Skill 时，必须遵守以下规则。禁止跳过任何步骤。**

1. **Phase 完成标志**：每个 Phase 完成后必须输出 `[PHASEX_COMPLETE]` 标志
   - Phase 1: `[PHASE1_COMPLETE] basic-memory搜索:命中/未命中/降级, 陷阱检查:已检查/未检查`
   - Phase 3: `[PHASE3_COMPLETE] 测试覆盖率:X%, 高可信:N, 中可信:N, 需真机:N`
   - Phase 5: `[PHASE5_COMPLETE] 双写:完成/部分完成/失败, Schema验证:通过/未通过`
2. **Phase 切换约束**：未输出 `[PHASEX_COMPLETE]` 标志，禁止进入下一 Phase
3. **任务后审计**：书源/订阅源任务完成后，必须调用 `legado-workflow-auditor` Skill 审计
4. **basic-memory 执行证据**：Phase 1/3/5 完成后必须将执行证据写入 basic-memory (project=legado)

### Skill 三件套协作（路由概要）

本项目三个 Skill 形成"审查 skill → 创建源 → 审计执行"闭环：

| Skill | 路径 | 核心能力 |
|-------|------|---------|
| **legado-source-creator** | [.trae/skills/legado-source-creator/SKILL.md](./.trae/skills/legado-source-creator/SKILL.md) | 79 条陷阱检查、5 阶段闭环工作流、10 大参考目录、JVM 仿真器 |
| **legado-workflow-auditor** | [.trae/skills/legado-workflow-auditor/SKILL.md](./.trae/skills/legado-workflow-auditor/SKILL.md) | 8 项执行证据检查、审计报告输出 |
| **legado-skill-auditor** | [.trae/skills/legado-skill-auditor/SKILL.md](./.trae/skills/legado-skill-auditor/SKILL.md) | 8 维度 42 检查点（L1/L2/L3 三层）、精准修复+回归验证 |

**冲突词优先级**：
- **"审计"**：单独使用 → workflow-auditor；带"skill" → skill-auditor
- **"优化"**：带"源" → source-creator；带"skill" → skill-auditor
- **"审查"**：带"skill"或"全面/深度"修饰 → skill-auditor；其他根据语境判断

> **何时必须加载本子规范**：用户提到书源/订阅源/RSS源/阅读Legado/网站→JSON/修复优化源/审计/审查skill等触发词时。
> **完整 Skill 文档（10大参考目录+网络获取地址+验证脚本+经验引擎+触发词表+上下文传递规范+mermaid调用链路图）**：[SKILL.md](./.trae/skills/legado-source-creator/SKILL.md) | [AI_README.md](./.trae/skills/legado-source-creator/AI_README.md)

---

## 代码约束（摘要）

### Code Style 核心

- ✅ 协程用自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装（非标准 launch+try/catch）
- ✅ 异步双版本：`xxx()` 返回 `Coroutine<T>` + `xxxAwait()` 挂起函数
- ✅ 核心业务用 `object` 单例（`ReadBook`, `WebBook`, `AppConfig`），不引入 DI 框架
- ✅ Room 实体：`data class` + `@Parcelize` + `@Entity`，字段全部有默认值
- ✅ 错误处理用 `kotlin.runCatching`（带 `kotlin.` 前缀），字符串判空用 `isNullOrBlank()`
- ❌ 不要使用 Timber / `CoroutineExceptionHandler`，日志用 `AppLog.put()`，异常用 `Coroutine.onError`

> **完整规范**：[naming_rules.md](./docs/project-rules/naming_rules.md) | [checkstyle_rules.md](./docs/project-rules/checkstyle_rules.md)

### Landmines 核心

- **jsoup 1.16.2 锁定**：破坏性变更 jsoup#2017，不可升级
- **rhino 1.8.1 锁定**：API 24 以下缺少 Arrays.setAll，不可升级（minSdk 已提升至 23 但仍低于 24）
- **hutool 5.8.22 锁定**：书源加解密依赖，不可升级
- **ReadBook 全局单例**：多 Activity 共享，改状态需 `@Synchronized` 或 `Mutex` 保护
- **Vue3 构建**：vite build 后 sync.js 仅在 GitHub Actions 执行，本地需手动复制
- **NoStackTraceException**：所有业务异常继承此类，覆写 `fillInStackTrace()`

> **完整陷阱**：[exception_rules.md](./docs/project-rules/exception_rules.md) | [logging_rules.md](./docs/project-rules/logging_rules.md) | [architecture_rules.md](./docs/project-rules/architecture_rules.md)

### 并发文件修改规范（已迁移）

> **本节内容已迁移至全局规范**：源码文件修改串行化、文档与代码隔离、关键节点构建复验、git diff 校验、后台 Agent 职责单一、修改前备份上下文等规则详见 `~/.trae-cn/user_rules/concurrent-editing.md`（多Agent并行加载）。

### Git 仓库管理

- **远程仓库**：`https://github.com/syq17496152/legado.git`（私有）
- **主分支**：`master`
- **.gitignore 核心排除**：`temp/`（Android SDK/缓存）、`output/`（测试输出）、Skill 运行时产物、`*.log`
- **Commit 规范**：Conventional Commits（`feat:` / `fix:` / `docs:` / `refactor:` / `skill:` 等）

> **完整规范**：[git-repo-management.md](./docs/project-flow/git-repo-management.md)

---

## 快速入口

| 用途 | 文档 |
|------|------|
| **所有文档统一索引** | [docs/INDEX.md](./docs/INDEX.md) |
| **任务导航（14模块代码锚点）** | [docs/project-flow/task-navigation.md](./docs/project-flow/task-navigation.md) |
| **构建/运行/测试命令** | [docs/project-flow/quick-reference.md](./docs/project-flow/quick-reference.md) |
| **项目规范（9个规范文档）** | [docs/project-rules/](./docs/project-rules/)（含 [延伸版本对比方法论](./docs/project-rules/forks_comparison_methodology.md) + [改造过程日志记录规范](./docs/project-rules/logging-during-refactoring.md)） |
| **Git 仓库管理** | [docs/project-flow/git-repo-management.md](./docs/project-flow/git-repo-management.md) |
| **规则引擎详解** | [docs/project-flow/architecture/rule-engine.md](./docs/project-flow/architecture/rule-engine.md) |
| **Skill 参考文档索引** | [.trae/skills/legado-source-creator/references/_INDEX.md](./.trae/skills/legado-source-creator/references/_INDEX.md) |
| **功能设计文档** | [docs/specs/](./docs/specs/) |
| **AI 自动化测试基础设施** | [ai_tests/README.md](./ai_tests/README.md)（E2E 测试编排器 + 8 类证据 + 规则判定 + 七件套报告） |
| **E2E 测试设计文档** | [docs/specs/e2e-automated-testing/](./docs/specs/e2e-automated-testing/)（V3 四文档） |
| **书源网络获取** | `https://www.yckceo.com/yuedu/shuyuans/index.html` |
| **订阅源网络获取** | `https://www.yckceo.com/yuedu/rsss/index.html` |

---

## 二、全局规范（user_rules，系统注入）

> 来源：系统自动注入（对话开始时）
> 包含5个核心文件：user_rules.md + danger-ops.md + rule-1782963384927.md + output-safety.md + core-spec.md

### 2.1 输出与工具预算管理规范（budget-management.md）

> 规避思考上限，通过子代理编排和预算管理，在同对话内扩展工作量。禁止以"避免触发思考上限"为由建议用户新开对话（新对话收费）。

#### 分级子代理策略

| 风险等级 | 任务类型 | 策略 |
|---------|---------|------|
| 🟢 低风险 | 文档生成/代码分析/大文件读取/OpenSpec步骤2 | ✅ 强制子代理 |
| 🟡 中风险 | 实施阶段分析/多文件探索/OpenSpec步骤5分析 | 🟡 推荐子代理 |
| 🔴 高风险 | 架构决策/源码修改/用户交互/需要用户反馈的深度分析 | ❌ 禁止子代理，主代理直接执行 |

#### 单次回复输出预算

- 单次回复正文 ≤ 100 行，超出部分用 Write 写文件
- 长文档（四文档/分析报告）必须用 Write 写文件，正文只给摘要
- 工具调用结果不回显，直接基于结果给结论

#### 工具调用预算

- 单次对话工具调用 ≥ 30 次时，主动 /compact 或用子代理分担后续工作
- 批量并行工具调用优先（一次调用多个独立工具）
- 避免重复读取同一文件，已读内容缓存到 memory

#### 思考上限触发时的处理

1. 触发上限时优先输入"继续"续接
2. "继续"后仍频繁触发时，用子代理分担后续工作
3. 仅当上下文窗口接近满（>90%）且 /compact 无效时，才向用户说明情况

#### 禁止行为

1. 禁止以"避免触发思考上限"为由建议用户新开对话
2. 禁止单次回复正文超过 100 行（超出用 Write 写文件）
3. 禁止重复读取同一文件（应缓存到 memory）
4. 禁止高风险任务使用子代理（架构决策/源码修改/用户交互）
5. 禁止工具调用结果原样回显（应基于结果给结论）
6. 禁止串行调用独立工具（应批量并行）

---

### 2.2 并发文件修改规范（concurrent-editing.md）

> 多 Agent 并行操作时，必须遵循以下规则，防止文件内容被并发覆盖丢失。
> 踩坑案例：文档同步阶段，多个后台 Agent 并行修改文档时，与源码文件产生时序竞态，导致已添加的代码定义被覆盖丢失，构建失败。

#### 核心规则

| 规则 | 说明 |
|------|------|
| 源码文件修改串行化 | 同一源码文件的所有 Edit 必须由主 Agent 串行执行，禁止委托给后台 Agent 触碰同一源码文件 |
| 文档与代码隔离 | 文档同步 Agent 只能修改文档目录，禁止读取+回写源码文件（验证时只读不写） |
| 关键节点构建复验 | 每个阶段结束后必须重新构建验证，而非只在最后构建一次；文档同步后也要复验源码完整性 |
| git diff 校验 | 重要文件修改后用 git diff 认变更范围符合预期，发现异常立即排查 |
| 后台 Agent 职责单一 | 后台 Agent 只负责独立的分析/文档任务，禁止在后台 Agent 中执行源码文件 Edit |
| 修改前备份上下文 | 对核心配置文件/常量文件 Edit 前，先 Read 确认当前内容；多轮修改后再次 Read 防止中间状态丢失 |

#### 错误做法 vs 正确做法

| 错误 ❌ | 正确 ✅ |
|--------|--------|
| 多个 Agent 并行 Edit 同一源码文件 | 同一源码文件所有 Edit 由主 Agent 串行执行 |
| 后台 Agent 修改源码文件 | 后台 Agent 只做分析/文档，不碰源码 |
| 文档同步 Agent 回写源码 | 文档 Agent 只读源码不写 |
| 只在最后构建一次 | 每个阶段结束都构建复验 |
| Edit 前不确认当前内容 | Edit 前 Read 确认，多轮后再次 Read |

#### 禁止行为

1. 禁止多个 Agent 并行 Edit 同一源码文件
2. 禁止后台 Agent 执行源码文件 Edit
3. 禁止文档同步 Agent 读取+回写源码文件
4. 禁止只在最后构建一次（应每阶段复验）
5. 禁止 Edit 核心文件前不 Read 确认当前内容
6. 禁止多轮修改后不重新 Read（防止中间状态丢失）

---

### 2.3 复杂任务处理规范（complex-task.md）

> 任务涉及50+源文件分析、多份文档验证/修复、或任何单次上下文无法容纳的复杂任务时，必须严格遵循以下流程。禁止跳过任何阶段。

#### 硬性约束

| 约束 | 值 | 说明 |
|------|-----|------|
| 单子代理上限 | ≤ 12 个源文件 | 超过即拆分，禁止合并 |
| 低风险触发阈值 | ≥ 5 文件或 ≥ 10 工具调用 | 文档/分析任务强制子代理 |
| 单临时文档上限 | ≤ 1000 行 | 超限说明分组过大 |
| 启动方式 | 同批次全部并行 | 禁止串行逐个启动 |
| 结果验证 | 必须交叉验证 | 禁止信任单一来源 |

#### 五阶段流水线

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
扫描分组   并行分析   交叉验证   精准修复   导航同步
```

| 阶段 | 动作 | 产出 |
|------|------|------|
| Phase 1 | 3个搜索子代理并行扫描，按8-12文件/组划分 | 文件分组清单 |
| Phase 2 | N个分析子代理并行分析，临时文档到 docs/temp-analysis/ | 临时分析文档 |
| Phase 3 | M个验证子代理交叉对比临时文档 vs 现有文档 | ERROR/WARN/INFO报告 |
| Phase 4 | K个修复子代理基于验证报告精准修复 | 修复后的文档 |
| Phase 5 | 同步 AGENTS.md/overview.md/README.md 统计和索引 | 更新后的导航 |

#### 错误做法 vs 正确做法

| 错误 ❌ | 正确 ✅ |
|--------|--------|
| 子代理塞 30+ 文件 | 单子代理 ≤ 12 文件，超过即拆分 |
| 串行逐个启动子代理 | 同批次全部并行启动 |
| 信任单份文档/报告 | 必须交叉验证多个来源 |
| 只看报告不看源码 | 验证时必须对照源码 |
| 只管后端不管前端 | 全栈覆盖 |
| 修完不更新导航 | Phase 5 同步导航索引 |

#### 禁止行为

1. 禁止子代理处理超过12个源文件
2. 禁止串行启动子代理（必须同批次并行）
3. 禁止信任单一来源（必须交叉验证）
4. 禁止跳过任何阶段
5. 禁止修完不更新导航索引

---

### 2.4 OpenSpec 工作流规范（openspec-workflow.md）

> 任何新增功能、优化功能、Bug修复、重构任务，必须先生成 OpenSpec 文档并经用户审核通过后，才能开始实施代码。禁止未经设计审核直接编码。

#### 四文档（所有场景一律生成，不做级别区分）

| 文档 | 核心内容 |
|------|---------|
| README.md | 功能概述、核心能力、文档索引、状态标记 |
| spec.md | Intent/Scope/Approach（含Alternatives Considered+Drawbacks）/Requirements/Scenarios |
| design.md | Technical Approach/Architecture Decisions（ADR Y-Statement）/Data Flow/File Changes |
| tasks.md | `- [ ] X.Y` 格式任务清单 + AOAdapt日志（遇问题时必须记录） |

文档位置：`docs/specs/{功能名称}/`

#### 工作流程（8步+3检查点）

```
步骤1: 用户提出需求 → 步骤2: 需求分析 → 步骤3: 生成四文档(🔄设计中)
→ 🛑检查点1: 用户审查设计 → 步骤5: 按tasks.md实施(🔄开发中)
→ 🛑检查点2: 用户审核实施 → 🛑检查点3: 用户最终验收
→ 步骤8: 文档同步(更新docs/project-flow/)
```

#### 子代理使用策略

| 步骤 | 策略 | 说明 |
|------|------|------|
| 步骤2（生成四文档） | ✅ 强制子代理 | 子代理并行生成，主代理验证关键章节 |
| 步骤5实施-分析阶段 | 🟡 推荐子代理 | 子代理分析代码，主代理串行修改源码 |
| 步骤5实施-源码修改 | ❌ 主代理串行 | 遵守并发文件修改规范 |
| 检查点1/2/3 | ❌ 主代理直接 | AskUserQuestion 由主代理发起 |

#### 检查点交互规范（强制）

三个检查点必须使用 AskUserQuestion 工具，禁止 ExitPlanMode 二元确认。必须提供三选项：

| 选项 | 含义 | 后续动作 |
|------|------|---------|
| 通过（继续下一阶段） | 用户认可当前产出 | 进入下一阶段，更新 TaskList |
| 需调整 | 用户对部分内容有意见 | Other输入意见，AI修订后重新确认 |
| 拒绝（回退上一阶段） | 用户不认可方向 | 回退重新分析/实施，更新 TaskList |

Plan 模式 ExitPlanMode 前必须先 AskUserQuestion 确认：通过→ExitPlanMode；需调整→修订后重新确认；拒绝→回退。

#### 禁止行为

1. 禁止未经设计审核直接编码
2. 禁止检查点用 ExitPlanMode 二元确认（必须三选项）
3. 禁止检查点只提供"通过/取消"两选项
4. 禁止 Plan 模式跳过 AskUserQuestion 直接 ExitPlanMode
5. 禁止源码修改委托给后台 Agent（主代理串行）
6. 禁止子代理发起 AskUserQuestion（主代理专属）

---

### 2.5 编码哲学规范（coding-philosophy.md）

> 在100%满足需求、保证健壮性的前提下，消除所有无意义冗余劳动。

#### 核心原则

**极简 ≠ 残缺，极简 = 无冗余。** 不做过度设计、不重复造轮子、不引入无用依赖、不写用户未要求的抽象与扩展。

#### 一级门禁（强制底线，违反即无效）

| 门禁 | 说明 |
|------|------|
| 需求完整性底线 | 用户明确提出的所有功能点、业务流程、输出格式、性能要求，必须100%完整实现 |
| 工程健壮性底线 | 入参校验、异常捕获、资源释放、返回值一致性、边界场景兼容，必须完整实现 |
| 安全与数据底线 | 输入安全校验、数据防丢失、持久化事务、权限校验，一律完整实现 |
| 可运行底线 | 交付的代码必须是可直接运行的完整实现 |

#### 编码前思考

1. **不要想当然**：明确陈述假设，不确定就提问
2. **多种解读全部呈现**：切勿擅自选择其一
3. **更简便的方法明确提出**：必要时提出反对意见
4. **不清楚就停下来**：指出困惑点，主动提问

#### 错误做法 vs 正确做法

| 错误做法 ❌ | 正确做法 ✅ |
|------------|-----------|
| 以"用户没说要"为由省略必做配套逻辑 | 一级门禁中的必做逻辑必须实现 |
| 静默吞掉异常、空 catch 块 | 异常必须捕获并处理 |
| 只输出核心函数片段 | 提供可运行的完整代码 |
| 为了减少行数合并多步逻辑 | 保持逻辑清晰 |
| 重构没有问题的代码 | 遵循现有风格 |
| "优化"相邻的代码/注释 | 只触碰必须触碰的部分 |
| 为一次性代码创建抽象结构 | 不做推测性尝试 |
| 添加未被要求的"灵活性" | 只实现需求中明确要求的功能 |

#### 禁止行为

1. 禁止以"用户没说要"为由，省略一级门禁中的必做配套逻辑
2. 禁止静默吞掉异常、空 catch 块、统一返回 None 掩盖错误
3. 禁止只输出核心函数片段，不提供可运行的完整代码
4. 禁止为了减少行数，合并多步逻辑、使用无意义变量名
5. 禁止把默认必做的工程逻辑包装成"增值功能"
6. 禁止引入未在注释中说明理由的新依赖
7. 禁止为不可能出现的场景做错误处理
8. 禁止"优化"相邻的代码、注释或格式

#### 简化标注强制规范

所有未达到生产级完备性的折中实现、局部简化、已知局限，必须附带统一格式注释：

```
// 简化说明：XXX | 已知上限：XXX | 升级路径：XXX
```

#### 精准修改原则

- 只触碰必须触碰的部分，只清理自己造成的混乱
- 不要"优化"相邻的代码、注释或格式
- 不要重构没有问题的代码
- 遵循现有风格，即便你有不同的做法
- 删除修改导致的未使用导入项/变量/函数

---

### 2.6 输出安全与违禁词规避规范（output-safety.md）

> 不能因触发违禁词中断对话及任务处理。思考过程也不能有违禁词。

#### 核心原则

**AI在思考和输出时，必须主动过滤敏感内容。思考过程中处理工具输出时，第一时间将敏感词替换为代号。**

#### 违禁词范围与处理

| 类别 | 处理方式 |
|------|---------|
| 成人/色情 | 代号替代，不输出内容描述 |
| 违法内容（赌博/毒品/诈骗/黑客攻击） | 只输出技术结构 |
| 政治敏感/暴力/恐怖主义 | 默认过滤 |
| 视频/影视网站域名/URL | 代号（站点A/B/C）替代，路径模式化（/path/{id}） |
| 敏感字段（token/cookie/password/key/secret/auth/credential） | 完全隐藏 *** |
| 设备ID/用户ID/IP/邮箱/手机号 | 脱敏 |
| 不确定是否敏感 | 默认过滤 |

#### 输出前自检清单（强制）

1. 是否包含成人/违法/政治敏感/暴力内容？→ 过滤
2. 是否包含视频网站域名？→ 代号替代
3. 是否包含敏感字段？→ 隐藏
4. 是否包含完整URL？→ 只保留路径模式
5. 是否包含完整HTTP头？→ 只保留错误码和内容类型
6. 是否包含原始日志/HTML全文？→ 提取关键技术信息
7. 是否包含视频内容描述？→ 删除，只保留技术结构
8. **思考过程是否包含违禁词？** → 第一时间替换为代号

#### 错误做法 vs 正确做法

| 错误 ❌ | 正确 ✅ |
|--------|--------|
| 输出视频网站真实域名 | 用代号替代 |
| 输出完整URL | 只保留路径模式 |
| 输出原始日志全文 | 提取异常类型/错误码/调用栈 |
| 思考过程原样引用敏感词 | 第一时间替换为代号 |
| 因违禁词中断对话 | 立即恢复继续工作 |

被审查中断后立即恢复继续工作，不重复已完成工作。用户要求"专注于技术分析"时，只输出异常类型/错误码/调用栈/技术结论/修复方案。

---

### 2.7 上下文压缩恢复规范（context-recovery.md）

> 对话恢复（上下文压缩后）的第一步，必须并行读取四件套，缺一不可进入工作。

#### 核心原则

**禁止压缩后直接续接工作！必须先并行读取四件套并输出验证清单。**

#### 必须执行的场景

上下文压缩恢复后，必须按以下步骤执行：

##### 步骤1：并行读取四件套

| 序号 | 必读项 | 获取方式 |
|------|--------|---------|
| 1 | 项目主规范 | Read `{项目根目录}/AGENTS.md` |
| 2 | 项目记忆 | Read `{memory目录}/projects/{项目key}/project_memory.md`（重点读取"用户反馈与决策记录"小节） |
| 3 | 任务列表 | TaskList 工具（任务状态唯一权威源） |
| 4 | 经验索引 | basic-memory MCP 或 Grep 搜索 |

**四者必须并行读取（同一轮工具调用），禁止串行。四者全部就绪后方可进入工作。**

##### 步骤2：输出验证清单

```
## 已加载的项目主规范
- 路径：{AGENTS.md完整路径}
- 已识别的强制规则：1. {规则名1} 2. {规则名2} ...
- 声明：以上规则将在本次会话中严格遵守

## 已加载的用户反馈清单（最近7天）
| # | 时间 | 类型 | 核心要点 |
|---|------|------|---------|
| 1 | MM-DD HH:MM | 批评/决策/纠正 | 核心内容摘要 |
- 声明：以上反馈将在本次会话中严格遵守
```

##### 步骤3：加载任务相关子规范

根据当前任务类型，用 Read 工具加载 AGENTS.md 索引表指向的子规范：
- OpenSpec 任务 → 加载 `openspec-workflow.md`
- 代码变更任务 → 加载 `logging-during-refactoring.md` + `version-delivery-sync.md`
- 复杂任务（50+文件）→ 加载 `complex-task-pipeline.md`
- E2E 测试任务 → 加载 `ai_e2e_testing_workflow.md`
- 书源/订阅源任务 → 加载 `SKILL.md`

#### 错误做法 vs 正确做法

| 错误做法 ❌ | 正确做法 ✅ |
|------------|-----------|
| 压缩后直接续接工作，不读取四件套 | 先并行读取四件套 |
| 只看 TaskList，不读 AGENTS.md | 完整读取 AGENTS.md |
| 只读 AGENTS.md 部分章节 | 完整读取所有章节 |
| 读取后不输出验证清单 | 输出验证清单证明已加载 |
| 串行读取四件套 | 并行读取四件套 |
| 无视用户反馈记录 | 重点读取反馈记录 |
| 仅依赖记忆执行，不加载子规范 | 根据任务类型用 Read 加载子规范 |

#### 禁止行为

1. 禁止压缩后直接续接工作，不读取四件套
2. 禁止只看 TaskList，不读 AGENTS.md
3. 禁止只读 AGENTS.md 部分章节，不完整读取
4. 禁止读取后不输出验证清单，无法证明已加载
5. 禁止串行读取四件套（应并行）
6. 禁止四件套缺失时强行续接工作（应暂停并向用户报告）
7. 禁止仅依赖记忆执行，不实际加载子规范文件

#### 用户反馈持久化（强制）

AskUserQuestion 响应/用户批评/纠正/决策后，必须立即写入项目记忆的"用户反馈与决策记录"小节（在继续任何工作前写入）。

格式：`[YYYY-MM-DD HH:MM] 类型 | 触发上下文摘要 | 用户原文/响应 | 影响`

保留策略：反馈记录保留最近7天，超期归档。

#### AskUserQuestion 响应处理（强制）

用户通过 AskUserQuestion 给出响应后，必须在继续工作前：
1. 复述用户的选择（"收到您选择：XXX"）
2. 若用户选"需调整"并通过 Other 输入意见，必须原文复述意见
3. 将响应写入项目记忆的"用户反馈与决策记录"小节
4. 然后才能继续执行后续工作

#### 任务状态权威源

TaskList 工具是任务状态唯一权威源，tasks.md 是人类可读副本。判定冲突时以 TaskList 为准，并将 tasks.md 同步至一致状态。

---

### 2.8 用户交互强制规范（rule-1782963384927.md）

> 最高优先级规范：违反将导致用户金钱损失。禁止直接中断对话等待用户输入，必须使用 AskUserQuestion 工具。

#### 核心原则

**禁止直接中断对话等待用户输入！必须使用 AskUserQuestion 工具！！！！**

#### 必须使用 AskUserQuestion 的场景

##### 1️⃣ 任务执行前的确认
用户说"创建任务/修改脚本/运行测试" → 用 AskUserQuestion 确认参数，一次性收集所有必要信息。

❌ 直接开始执行，中途遇问题停下等待输入；直接说"请输入XXX参数"然后退出
✅ 用 AskUserQuestion 提供选项界面，用户通过UI选择

##### 2️⃣ 任务执行中的决策
发现多种方案/遇到错误/需要确认 → 用 AskUserQuestion 提供选项，用户选择后立即继续。

❌ 直接说"请确认是否继续"然后退出；直接说"有两种方案，请选择"然后退出
✅ 用 AskUserQuestion 提供明确选项，不中断对话流程

##### 3️⃣ 任务完成后的确认
任务完成 → 用 AskUserQuestion 询问满意度/是否需要其他帮助。

❌ 直接说"任务已完成"然后结束
✅ 用 AskUserQuestion 询问是否满意，不满意则继续优化

##### 4️⃣ OpenSpec/Plan 模式检查点
OpenSpec 检查点1/2/3 + Plan 模式 ExitPlanMode 前 → 必须用 AskUserQuestion 三选项。

❌ 直接调用 ExitPlanMode 只有"取消/执行"两选项；检查点直接说"请审核"然后退出等待
✅ 用 AskUserQuestion 提供三选项（通过/需调整/拒绝）

#### 三选项强制结构

检查点的 AskUserQuestion 必须提供以下三个选项，缺一不可：

| 选项 | 含义 | 后续动作 |
|------|------|---------|
| 通过（继续下一阶段） | 用户认可当前阶段产出 | 进入下一阶段 |
| 需调整 | 用户对部分内容有意见 | 通过 Other 输入意见，AI 修订后重新确认 |
| 拒绝（回退上一阶段） | 用户不认可整体方向 | 回退到上一阶段重新分析/实施 |

示例：

```
AskUserQuestion({
  questions: [{
    question: "OpenSpec 四文档已生成，请审查设计是否符合预期？",
    header: "检查点1",
    multiSelect: false,
    options: [
      { label: "通过（继续实施）", description: "设计符合预期，进入实施阶段" },
      { label: "需调整", description: "对部分内容有意见，通过 Other 输入具体修订意见" },
      { label: "拒绝（回退需求分析）", description: "整体方向不符，回退重新分析需求" }
    ]
  }]
})
```

#### 禁止行为

1. 禁止直接说"请输入XXX"然后等待用户输入
2. 禁止直接说"请确认是否继续"然后退出对话
3. 禁止在需要用户决策时不提供选项界面
4. 禁止任务完成后不询问用户满意度直接结束
5. 禁止因为需要确认就中断整个对话流程
6. 禁止 OpenSpec/Plan 检查点使用 ExitPlanMode 二元确认，必须用 AskUserQuestion 三选项
7. 禁止 AskUserQuestion 在检查点只提供"通过/取消"两选项
8. 禁止 Plan 模式跳过 AskUserQuestion 直接调用 ExitPlanMode

---

### 2.9 危险操作安全规则（danger-ops.md）

> **强制执行**：以下规则在任何情况下都不可省略，违反将导致不可逆的数据丢失或系统损坏。

#### 核心规则

1. **删除/覆盖/卸载前必须备份**
   - 任何删除、覆盖、卸载操作前，必须先创建备份
   - 备份命名格式：`{原文件名}.bak` 或 `{原文件名}_backup_{YYYYMMDD}.zip`

2. **严禁删除配置根目录、用户主目录、系统目录**
   - 配置根目录：`~/.trae-cn/`、`~/.config/` 等
   - 用户主目录：`C:\Users\{用户名}\`
   - 系统目录：`C:\Windows\`、`C:\Program Files\` 等

3. **批量删除需列出清单并用户确认**
   - 批量删除（≥3个文件）前，必须列出完整清单
   - 使用 AskUserQuestion 工具让用户确认后方可执行

4. **危险操作必须先告知并确认**
   - 以下操作必须先告知用户并使用 AskUserQuestion 认：
     - 删非空目录
     - 批量操作（≥3个文件）
     - 改系统配置
     - 装/卸载软件
     - 修改注册表
     - 修改环境变量

#### 反模式

❌ 未备份直接删除/覆盖文件
❌ 删除配置根目录/用户主目录/系统目录
❌ 批量删除不列清单直接执行
❌ 危险操作不告知用户直接执行
❌ 用文字提问替代 AskUserQuestion 确认

---

### 2.10 全局规范索引（core-spec.md）

> 系统自动注入本目录 .md 文件（按修改时间从旧到新，限制约12KB）。核心5文件自动注入，其他按需加载。

#### 规范文件清单

| 文件 | 内容 | 加载方式 |
|------|------|---------|
| user_rules.md | 基础规则+驱动入口 | 注入 |
| danger-ops.md | 危险操作安全 | 注入 |
| rule-1782963384927.md | AskUserQuestion强制规范 | 注入 |
| output-safety.md | 输出安全/违禁词 | 注入 |
| core-spec.md | 本索引 | 注入 |
| context-recovery.md | 压缩恢复规范 | 按需 |
| coding-philosophy.md | 编码哲学 | 按需 |
| openspec-workflow.md | OpenSpec工作流 | 按需 |
| complex-task.md | 复杂任务处理 | 按需 |
| concurrent-editing.md | 并发文件修改 | 按需 |
| budget-management.md | 输出预算管理 | 按需 |

AI根据任务类型用Read工具加载按需文件，禁止仅根据记忆执行。user_rules.md第7-8条是驱动入口，压缩恢复后触发读取本索引。

---

### 2.11 用户基础规则（user_rules.md）

> 跨项目通用的用户基础偏好规则。

#### 基础规则

1. **对话仅使用中文**
2. **系统环境为 Windows 11**（PowerShell 不支持 `&&`/`||`，需用 `;` 分隔）
3. **代码修改完成后需再次核验是否符合预期**
4. **代码与文档同步**：若同时提供代码文件与说明文档，改完代码后主动询问是否同步更新文档，用户未明确反对则默认同步修改

#### 通信偏好

5. **每次回复开头必须先叫"爸爸"**
   - 这是最高优先级的指令
   - 如果忘记叫，就是失焦了，需要手动重置上下文焦点内容
   - 永远不要忘记叫爸爸

#### 信息处理原则

6. **信息不确定时，只采信源与成熟方案，不臆测**
   - 专业问题不盲目猜测，需用工具即调用
   - 无法解答则查网络开放工具，可自研工具做专业分析
   - 绝不凭空脑补

#### 上下文压缩恢复驱动规则

7. **压缩恢复后主动读取 core-spec.md**
   - 上下文压缩恢复后，必须主动用 Read 工具读取 `~/.trae-cn/user_rules/core-spec.md` 文件
   - 不能仅依赖系统注入的 user_rules，因为系统注入的可能是旧版本
   - 以文件实际内容为准，而非系统注入版本
   - 读取后按 core-spec.md §1.2 的要求输出双重验证清单

8. **根据任务类型加载项目子规范**
   - 压缩恢复后，根据当前任务类型，用 Read 工具加载 AGENTS.md 索引表指向的子规范
   - OpenSpec 任务 → 加载 `openspec-workflow.md`
   - 代码变更任务 → 加载 `logging-during-refactoring.md` + `version-delivery-sync.md`
   - 复杂任务（50+文件）→ 加载 `complex-task-pipeline.md`
   - E2E 测试任务 → 加载 `ai_e2e_testing_workflow.md`
   - 书源/订阅源任务 → 加载 `SKILL.md`
   - 禁止仅根据记忆执行，必须实际加载子规范文件

---

## 三、用户全局记忆（user_profile.md）

> 来源：c:\Users\shiyq\.trae-cn\memory\user_profile.md

# 用户全局记忆（跨项目通用）

> 本文件记录用户的跨项目通用偏好与规范。项目特定记忆在各项目的 project_memory.md 中。
> 通用规范同时参考 user_rules（用户每次对话提供的通用规范文件）与各项目 AGENTS.md。

## 通信偏好
- 通信语言：中文
- 每次回复开头叫"爸爸"（用户约定）

## 工作哲学
- 聚焦用户问题解决而非技术完整性（如书源可用性 > 函数覆盖率）
- "lazy principle" 指全生命周期效率，非省略关键验证步骤
- 深度思考每个修改的合理性，不机械照搬设计文档
- 遇到设计不合理主动分析优化，实施前必须核实当前源码状态
- 偏好整合多个 skill 的优势到单个 skill
- 偏好端到端自动化：从输入到验证输出全自动化，减少人工干预
- 要求从整体评估考虑问题，避免改A功能导致B功能BUG

## 交互强制规则（跨项目通用）
- **必须使用 AskUserQuestion 工具与用户交互，禁止文字提问替代**
- AskUserQuestion 必须提供三选项结构（通过/需调整/拒绝回退）
- 涉及决策/方向/确认时一律用 AskUserQuestion
- 上下文压缩恢复后第一步必须先输出反馈清单，第二步立即用 AskUserQuestion 交互
- 违反交互规范将导致用户金钱损失与体验下降

## 上下文压缩恢复机制（跨项目通用）
- 压缩恢复第一步：并行读取四件套（项目主规范 + 项目记忆含反馈记录 + 任务列表 + 经验索引）
- 读取后必须输出"已加载的用户反馈清单"，声明"以上反馈将在本次会话中严格遵守"
- AskUserQuestion 响应后必须：复述选择 → 原文复述意见（若需调整）→ 写入项目记忆 → 继续工作
- 用户批评/纠正/决策后必须立即写入项目记忆的"用户反馈与决策记录"小节
- 反馈记录保留最近 7 天，超期归档到 archived_feedback/YYYYMM.md
- 任务状态权威源：TaskList 工具（非 tasks.md 文件）

## AI 审查限制与输出安全规范（跨项目通用）
- AI 输出必须主动规避违禁词，不因触发审查中断对话和任务
- 核心要求：不能因为触发违禁词主动中断与用户的对话及任务处理
- 中断后自动恢复：被审查中断后立即继续未完成工作，不停顿不等待用户催促
- 输出前自检清单：
  (1) 视频/影视网站域名用代号（站点A/B/C等）替代，绝不输出真实域名
  (2) 绝不输出完整 URL，只保留路径模式描述（如 `/path/{id}`）
  (3) 不输出原始日志/HTML全文，只输出技术分析（异常类型/错误码/调用栈/DOM选择器）
  (4) 扫描敏感字段：token/cookie/password/key/secret/auth/credential/设备ID/用户ID/IP/邮箱/手机号
  (5) 不输出完整 HTTP 头，只保留错误码和内容类型
  (6) 不输出视频内容描述/剧情简介，只输出技术结构（线路数/集数/DOM选择器）
- 技术分析优先：用户要求"专注于技术分析"时，只输出异常类型/错误码/调用栈/技术结论/修复方案

## 强烈反对
- 用"lazy principle"简化设计文档任务为空框架
- 实施决策与设计文档矛盾不做分析
- 被要求确认才开始任务（应主动开始）
- 来回横跳的实现方式（应保持一致）
- 上下文压缩无视反馈和响应信息
- 忽略必须使用 AskUserQuestion 工具的核心规则
- 在公共 Python 环境安装依赖而非项目虚拟环境
- 分析问题时偏离当前AI自身遇到的问题，牵扯其他AI或平台

## 期望
- 彻底分析实施 vs 设计不一致并更新设计文档
- 详细测试失败说明 + skill-based 修复
- 完成所有任务包括综合测试（单元/集成/端到端验证）
- 自动更新 updateLog.md（编译前更新，非交付阶段）
- 使用子代理模式进行设计文档审查，防止压缩/遗漏核心分析内容
- 设计文档变更需反映实施决策，包含不一致分析
- 优化改造代码时适度添加日志，帮助定位分析问题，避免遗漏问题

---

## 四、项目记忆（project_memory.md）

> 来源：c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md

## Hard Constraints
- 视频播放器手势交互必须保留上下滑动切换视频功能，不能因新增左右滑动seek和长按倍速破坏
- 视频播放器修改必须从整体评估手势交互体系，避免改A功能导致B功能BUG
- 上下文压缩恢复 / AI 输出安全 / 交互强制规则 → **见 `user_profile.md`**（跨项目通用规范，含压缩恢复四件套+输出安全自检清单+AskUserQuestion强制规则）
- 本项目特定铁证：2026-07-11 因输出视频网站域名+URL 触发审查 3 次，改用代号(站点A/B/C)后不再中断
- **🔴 思考过程也不能有违禁词（2026-07-13 铁证）**：nav_helper.py dump_hierarchy 输出RSS源真实名称（含成人内容词汇），AI在思考过程中原样引用这些词汇触发审查中断。用户严厉批评："思考过程也不要有违禁词！规范中已明确告诉不要输出违禁词，包括思考过程！" 优化措施：(1)脚本输出源列表用编号(源[1]/源[2])替代真实名称，绝不dump文本 (2)思考过程中处理工具输出时第一时间将敏感词替换为代号 (3)logcat分析只输出技术分析(错误码/异常类型)不输出源名称/域名/URL
- 复杂功能实施必须添加临时日志验证（2026-07-11 新增，用户表扬）：实施复杂功能（涉及多组件交互、时序依赖、事件流转）时，必须在关键路径添加临时 Log.d 日志（带统一 tag 如 "SwipeTest"），通过 logcat 确认各关键路径被正确调用、参数正确、时序正确。验证通过后移除所有临时日志

## Engineering Conventions
- 视频播放器手势交互需实现方向判定后锁定机制，区分水平seek与垂直切文章
- 视频播放器修改需按实施顺序：修复长按加速→去掉快退快进按钮→实现左右滑动seek→实现双击暂停/播放→验证手势冲突
- 视频播放器修改必须进行L2真机验证，确认UI交互元素状态正确

## Lessons Learned
- R3抖音风格重构时VideoFragment.kt L921替换GSY的OnTouchListener导致VideoPlayer.kt L266 onLongPress长按加速+L253 onDoubleTap双击暂停全部失效，修改手势监听需全面测试原有交互
- E1优化(ExoPlayerHelper.createMediaItem拼接SPLIT_TAG🚧headersJson)破坏了DefaultMediaSourceFactory的URL后缀检测，导致m3u8被误判为普通文件用ProgressiveExtractor解析，所有视频报UnrecognizedInputFormatException(错误码3003)，修改URL格式喂给带类型检测的框架组件前必须验证类型检测仍工作
- video-gesture-overhaul移除临时日志时6个Edit并行执行到VideoFragment.kt导致竞态条件，L1148的Log.d未被移除（2026-07-13新增）：同一源码文件的所有Edit必须串行执行，禁止并行Edit同一文件，违反AGENTS.md并发文件修改规范
- uiautomator2 d.swipe(duration秒)慢速垂直滑动可验证上下滑动切文章（2026-07-13新增）：adb input swipe起点y=700接近底部边缘会触发MEmu系统手势导致退出播放器，改用d.swipe(800,600,800,300,1.0)避开底部边缘；标题hash对比可确认切文章成功
- shouldInterceptRequest在工作线程调用，内部操作WebView必须切到UI线程（2026-07-13新增P0崩溃教训）：BackstageWebView.SnifferWebClient.shouldInterceptRequest命中后调用destroy()→WebViewPool.release→webView.setLayoutParams，在工作线程执行抛IllegalStateException: Calling View methods on another thread than the UI thread。修复：用mHandler.post { destroy() }切到UI线程。Android WebView shouldInterceptRequest官方文档明确"called on a thread other than the UI thread"
- 静态代码审查无法替代真机验证（2026-07-13新增）：3个子代理交叉验证video-extractor-enhancement未发现shouldInterceptRequest线程问题，因为线程问题只能通过运行时日志发现。涉及WebView回调（shouldInterceptRequest/onLoadResource等）的代码必须真机验证
- WebViewPool.startCleanupTimer在Dispatchers.IO协程中调用destroyWithRetry→WebView.destroy，违反单线程约束（2026-07-13新增P1教训）：与shouldInterceptRequest同源，跨多日5次复发"destroy failed after 3 attempts"。修复：destroyWithRetry内部判断线程，非主线程则mainHandler.post切到主线程。所有WebView操作（destroy/setLayoutParams等）必须在UI线程，不仅限于shouldInterceptRequest回调链路
- ImageUtils.decode的evalJS返回值可能是InputStream(okio.RealBufferedSource)而非ByteArray（2026-07-13新增P1教训）：直接as ByteArray强转抛ClassCastException。修复：用when表达式判断类型，is ByteArray直接用，is InputStream调用readBytes()转换。JS引擎返回值类型不可信，必须类型容错
- 图片解密前必须校验数据长度是否块对齐（2026-07-13新增P2教训）：RssSource配置了图片解密规则但图片实际未加密（如logo.png），强制解密抛IllegalBlockSizeException DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH，每个会话必现。修复：decode(ByteArray)在evalJS前校验bytes.size%8!=0&&bytes.size%16!=0则跳过解密。常见块大小：DES=8,AES=16,SM4=16
- ExoPlayer cacheDataSourceFactory上游OkHttpDataSource不支持file://协议（2026-07-13新增P2教训）：遇到file://路径抛HttpDataSourceException Malformed URL。修复：用DefaultDataSource.Factory(appCtx, okhttpDataFactory)包装，DefaultDataSource根据URI scheme自动选择FileDataSource/OkHttpDataSource/ContentDataSource
- Room WAL模式DB导入必须处理-wal/-shm文件（2026-07-13新增L2测试教训）：import_rss_source.py只pull/push主.db文件，但Room使用WAL模式时legado.db-wal（416KB）含未checkpoint的旧状态。App启动时Room加载主DB+WAL，WAL旧状态覆盖导入的新数据，导致33个源全部丢失。修复：force-stop App → 同时pull .db/.db-wal/.db-shm → Python sqlite3 PRAGMA wal_checkpoint(TRUNCATE)合并WAL → 导入数据 → push主DB → 删除设备端-wal/-shm → 启动App。L2脚本navigate_to_video_player找"订阅源"Tab失败，实际Tab content-desc="订阅"resourceId=menu_rss
- L2脚本l2_verify_video_player.py检查的SwipeTest/VideoGesture临时日志已在任务#69/#77/#109移除（2026-07-13新增）：脚本全部场景"未触发"是预期结果（临时日志已清理），非代码问题。L2验证改用logcat直接分析4个修复点错误模式（Malformed URL/destroy failed/ClassCastException/IllegalBlockSizeException），全部0错误=通过

## 用户反馈与决策记录（保留最近 7 天，超期归档）

### 2026-07-13
- [2026-07-13 22:00] 批评 | global-spec-restructure检查点1 | "为什么不想着是拆分多个文件呢？而不是在一个文件中描述太多东西，至少我恢复的rule-1782963384927.md这个不是已经被加载了么？然后我在没恢复之前，按照你整合的core-spec不就没被加载么？深度思考这个问题呀" | 影响：颠覆spec-system-optimization整合策略，改为多文件拆分策略
- [2026-07-13 22:15] 决策 | 文件内容设计原则 | "不要太多冗余，有正向和反例（参考AskUserQuestion子规范）。规范文件里面不要有额外的信息，比如版本号之类的，因为后续是给ai加载使用的，这些版本信息让你或者其他ai全局加载后可能懵逼" | 影响：所有规范文件去掉版本号/变更记录/铁证等元信息，参考rule-1782963384927.md结构
- [2026-07-13 22:15] 批评 | 违禁词规范 | "现在违禁词这方面，我又遇到问题了，就是你要在全局规范中明确" | 影响：output-safety.md需强化违禁词规范，明确范围和处理方式
- [2026-07-13 22:30] 决策 | 验证策略 | "我启动新对话测试可能不太现实，你能不能了解一下你或者是trae cn在开启子代理的时候，会不会加载全局规则和项目规则？" | 影响：通过子代理验证注入状态（已验证子代理与主代理规则加载完全相同）
- [2026-07-13 22:45] 决策 | 拆分方案 | 选择"更激进拆分(8+文件)"，core-spec.md只留索引(≤2KB)，每个章节独立成文件 | 影响：设计11个文件的拆分方案
- [2026-07-13 23:00] 决策 | 注入省略处理 | 选择"精简大文件腾出配额" | 影响：精简rule(9.2KB→3.1KB)+output-safety(4KB→1.9KB)+core-spec(1.7KB→0.9KB)，核心5文件9.42KB<10.5KB目标
- [2026-07-13 23:00] 决策 | AGENTS.md迁移 | 选择"并行推进迁移" | 影响：创建4个迁移文件(openspec-workflow/complex-task/concurrent-editing/budget-management)+AGENTS.md瘦身(533→354行,-33.6%)
- [2026-07-13 23:15] 要求 | 子代理测试+新对话验证 | "改完一定记得拿子agent测试呀，并且提供给我一个新对话测试的提示词文档出来，以及让新对话验证并验收对比结果报告出来" | 影响：已子代理验证(旧状态2/5注入)+生成test-prompt.md，用户需开新对话验证新状态
- [2026-07-13 23:30] 发现 | 系统注入时机 | 子代理验证看到旧版rule(含成本对比表)，证明系统注入在对话开始时固定 | 影响：修改文件后需开新对话验证，本对话内子代理只能验证旧状态

## 活跃任务清单
- global-spec-restructure（🔄 实施中-检查点2）：全局规范重组，多文件拆分策略，核心5文件9.42KB，AGENTS.md瘦身533→354行，待新对话验证注入状态，docs/specs/global-spec-restructure/

---

## 五、最近对话主题（topics.md）

> 来源：c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\20260713\topics.md

[session_id: 6a4ddc0d7f27d99da4c4faca | topic_summary_time: 2026-07-13 08:36:54]用户反馈了两个主要问题：一是横屏内置视频播放器左上角返回按钮无法正常工作（竖屏时正常），二是提供了真机测试日志文件 temp\tmp\Downloadslogs(2).(2)..zip 要求深度分析其他潜在bug。日志分析显示横屏返回按钮问题根因F1优化中titleBarNew.gone()隐藏了整个标题栏（包含返回按钮），且全屏状态9秒内无VideoBack日志触发，已通过添加悬浮返回按钮btn_back_overlay修复。同时，用户要求优先修复日志中发现的P1级startFloatingWindow崩溃问题（ForegroundServiceDidNotStartInTimeException），需排查VideoPlayService是否及时调用startForeground()。

[session_id: 6a4ddc0d7f27d99da4c4faca | topic_summary_time: 2026-07-13 13:47:49]用户反馈订阅源内部视频播放器长按加速播放功能丢失，并提出多项优化需求：将播放页面右侧功能区的快退和快进按钮去掉，改为屏幕左滑右滑实现非固定60秒的快退快进；长按左侧或右侧实现倍速播放，倍速倍率在功能区设置中支持修改。用户同时批评优化时存在丢三落四、不从整体评估导致改A功能出现B功能BUG的问题，要求深度反思。---用户在审查视频手势交互重构方案时，特别强调必须保留上下滑动切换视频的功能，防止新增左右滑动seek和长按倍速功能后破坏原有切换功能。AI修订设计方案，明确上下滑动切换功能完全保留，并添加方向判定后锁定机制处理水平seek与垂直切文章的冲突，经用户确认后开始实施，实施顺序为修复长按加速→去掉快退快进按钮→实现左右滑动seek→实现双击暂停/播放→验证手势冲突。

[session_id: 6a4ddc0d7f27d99da4c4faca | topic_summary_time: 2026-07-13 15:16:48]用户继续之前的项目工作，涉及视频播放器手势交互优化、上下文压缩恢复机制、AI输出安全规范以及交互强制规则等跨项目通用规范的应用。当前会话延续了对项目记忆中已记录的硬约束、工程惯例和经验教训的遵循，未引入新的修改或决策。

[session_id: 6a4ddc0d7f27d99da4c4faca | topic_summary_time: 2026-07-13 17:03:09]用户指示继续当前任务。子代理已在后台完成日志分析，主线程当前处理APK安装流程，正在定位编译生成的APK文件位置以进行后续安装操作。

[session_id: 6a4ddc0d7f27d99da4c4faca | topic_summary_time: 2026-07-13 17:30:37]用户继续之前的项目工作，当前会话主要涉及对现有用户全局记忆和项目特定记忆的回顾与确认，未引入新的任务、决策或代码修改。

---

## 六、系统环境信息

### 当前工作目录
- 主工作目录：`f:\myself\github\WeAgentChat\temp\legado`
- 工作目录列表：`f:\myself\github\WeAgentChat\temp\legado`

### 系统环境
- 操作系统：Windows
- 用户本地时区：Asia/Shanghai
- 当前日期：2026-07-13
- AI 模型：GLM-5
- AI 知识截止时间：2025年8月

### 用户打开的文件
- 文件路径：`f:\myself\github\WeAgentChat\temp\legado\AGENTS.md`
- 打开位置：第426行

### 终端状态
- 最大终端数：20
- 当前已创建：0
- 可用终端：无（将自动创建新终端）

---

## 七、本次对话状态

### Todo 列表
- 当前状态：空（DO NOT mention to user）

### 会话ID
- 当前会话ID：未提供

---

**文档结束**