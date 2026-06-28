# Spec: Legado Skill V2 重建方案

## 1. Intent

### 1.1 核心目标

让 AI/Agent 使用 legado-source-creator Skill 时，能够通过"经验大脑 + 测试双手 + 仿真底座"三件套，端到端完成书源订阅源的创建、优化、测试、进化，减少对开源阅读源码的依赖。

### 1.2 终极愿景

- **经验知识是理解大脑**：Skill 参考文档 + basic-memory 经验索引，让 AI 快速理解如何创建/优化源
- **Python 客户端是测试双手**：工程化的 Python 客户端，像手机客户端一样操作仿真服务端
- **JAR 仿真服务端是核心能力底座**：复刻开源阅读核心逻辑的单 JAR 文件，与真机行为一致
- **开源阅读源码是兜底保障**：仅在仿真端无法解决时才回源码分析

### 1.3 成功标准

| 维度 | 当前状态 | V2 目标 | 验证方式 |
|------|---------|---------|---------|
| 真机书源兼容率 | ~55%（简单源） | **95%+**（含复杂源） | 50+ 真实书源端到端测试 |
| 真机订阅源兼容率 | ~60%（简单源） | **95%+**（含复杂源） | 50+ 真实订阅源端到端测试 |
| Python 客户端工程化 | 无虚拟环境、双客户端 | **完整工程化** | venv + 单入口 + 层级设计 |
| JAR 仿真端架构 | 4 个 JAR + runBlocking | **单 JAR + async** | 构建验证 + 性能测试 |
| 经验闭环 | pending.json 无人消费 | **自动反哺** | 端到端经验写入验证 |
| 测试覆盖率 | 仅 2 个文件有内联测试 | **核心模块 80%+** | pytest 覆盖率报告 |
| OkHttp 版本 | 5.3.2（已确认与真机一致） | **5.3.2 锁定** | build.gradle.kts 版本号一致 |

## 2. Scope

### 2.1 In Scope

#### A. JAR 仿真服务端重建（核心）

基于开源阅读源码逐行对比，**源码核实后实际需修复的 Bug 仅 2 个**（原 7 个 Bug 中 5 个已修复或误判）：

| 修复项 | 优先级 | 源码核实结论 | 说明 |
|--------|--------|------------|------|
| ~~BUG-01: assessConfidence 正则错误~~ | ~~P0~~ | **误判**：Kotlin 字符串转义正确，正则有效 | 无需修复 |
| BUG-02: debugExplore 日志误写 | P0 | **未修复** | 发现页日志仍输出"搜索页"标签 |
| ~~BUG-03: debugSortWithEmptyKey 忽略 URL~~ | ~~P0~~ | **已修复** | 完整降级链 sortUrl→searchUrl→sourceUrl |
| ~~BUG-04: getElements NativeArray 转换~~ | ~~P0~~ | **已修复** | convertJsResultToList() 三层防护 |
| ~~BUG-05: ajax 防递归逻辑~~ | ~~P0~~ | **已修复** | ajaxRecursionGuard 标志位 + finally 重置 |
| BUG-06: JsoupResponseAdapter.cookies() | **P0** | **确认存在** | 返回 emptyMap()，JS 获取 Cookie 失败 |
| ~~BUG-07: 正文分页 nextChapterUrl 缺失~~ | ~~P1~~ | **已修复** | toc→content 完整传递链路 |
| ~~GAP-44: followRedirects 未移除~~ | ~~P0~~ | **正常工作** | AnalyzeUrl.kt 中完整实现，与真机一致 |
| GAP-22: ruleDescription 逻辑 | P1 | 待对齐 | 规则描述解析不完整 |
| GAP-07: ajaxAll 无并发 | P2 | 待优化 | 并发请求退化为串行 |
| GAP-10: replaceFont 多字节 | P2 | 降级处理 | 多字节字符字体替换错误 |
| 合并为单 JAR | P0 | 已确认 | gradlew fatJar 产出单个 legado-jvm.jar |

#### B. Python 客户端工程化重建

| 修复项 | 优先级 | 说明 |
|--------|--------|------|
| PY-01: 虚拟环境管理 | P0 | requirements.txt + venv + setup.py |
| PY-02: 双客户端整合 | P0 | tools/ 与 legado_client/ 合并，单入口 |
| PY-03: auto_fixer 接入主流程 | P0 | debug_runner 调用 auto_fixer.auto_fix_error() |
| PY-04: verify_fix 真正验证 | P0 | 执行实际规则验证，不仅 ping |
| PY-05: 经验闭环修复 | P0 | pending.json → AI agent 消费 → basic-memory |
| PY-06: 3 个不存在模块处理 | P1 | 实现 cookie_manager/smart_http_client/knowledge_matcher 或移除导入 |
| PY-07: RuleEngineClient 超时保护 | P1 | readline() 阻塞 → 超时机制 |
| PY-08: 7 个弃用方法清理 | P2 | 移除或归档 eval_js/eval_css 等 |

#### C. Skill 工作流优化

| 修复项 | 优先级 | 说明 |
|--------|--------|------|
| SK-01: Phase 2 预校验集成 | P0 | source_validator + rule_precheck 真正接入 |
| SK-02: Phase 3 降级路径 | P0 | JVM 不可用时自动降级到 Python 模式 |
| SK-03: Phase 5 经验反哺 | P0 | 自动提取经验 + 写入 basic-memory |
| SK-04: 测试脚本整合 | P1 | 14 个独立脚本 → 统一 CLI 入口 |
| SK-05: SKILL.md 实现状态标注修正 | P0 | 4 处过时标注更新为"已实现" |
| SK-06: AD-04/05/06/07/09 决策补录 | P1 | 5 个缺失决策编号补入设计文档 |

#### D. 目录结构清理

| 修复项 | 优先级 | 说明 |
|--------|--------|------|
| CL-01: __pycache__ 清理 | P0 | 删除 5 个 .pyc 文件 |
| CL-02: build/ 产物清理 | P0 | 删除 100+ 构建产物 |
| CL-03: .gradle 缓存清理 | P0 | 删除 17 个缓存文件 |
| CL-04: 废弃脚本清理 | P1 | 删除 6 个废弃脚本 |
| CL-05: 孤立文件处理 | P1 | experience-pending.json 移入正确位置 |

#### E. 真实源端到端测试验证

| 修复项 | 优先级 | 说明 |
|--------|--------|------|
| TEST-01: 50+ 真实书源测试 | P0 | 每个源搜索→详情→目录→正文 |
| TEST-02: 50+ 真实订阅源测试 | P0 | 每个源分类→列表→正文 |
| TEST-03: 测试结果详细报告 | P0 | 失败原因 + skill 修复建议 |
| TEST-04: 经验反哺验证 | P1 | 测试中触发经验写入 |

### 2.2 Out of Scope

| 项目 | 原因 |
|------|------|
| WebView 完整仿真 | 需要 Playwright/JCEF，是独立大项目 |
| 登录流程仿真 | 需要用户手动导入 Cookie |
| 验证码自动处理 | 需要 OCR 服务 |
| ExoPlayer 音视频 | 纯 Android 功能 |
| Glide 图片加载 | 纯 Android 功能 |
| Cronet 网络加速 | 纯 Android 功能 |
| Rar/7z 解压（GAP-05/06） | 复杂度高，返回空降级 |
| ocr_delegate.py 实现 | 依赖外部 OCR 服务，暂不实现 |

### 2.3 Known Limitations（已知限制，文档化）

| 限制 | 影响范围 | 降级策略 |
|------|---------|---------|
| WebView 渲染 | 需要 JS 渲染的页面 | Python Playwright 委托 |
| 登录流程 | 需要登录的源 | 用户手动导入 Cookie |
| 验证码 | 需要验证码的源 | 用户手动输入 |
| CF 防护 | Cloudflare 防护的源 | Python cloudscraper/Playwright |
| Rar/7z 解压 | 压缩包源 | 返回空 |
| Android 平台 API | androidId/Toast/Intent | 固定值/stdout/UnsupportedOperationException |
| replaceFont 多字节 | 多字节字符字体替换 | GAP-10 暂不修复，记录已知限制 |

## 3. Requirements

### 3.1 JAR 仿真服务端需求

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-J01 | 修复 BUG-02 和 BUG-06（源码核实后仅 2 个需修复） | 每个修复有对应测试用例 |
| REQ-J02 | OkHttp 版本与真机锁定（5.3.2） | build.gradle.kts 版本号一致 |
| REQ-J03 | 合并为单 JAR | gradlew fatJar 产出单个 legado-jvm.jar |
| REQ-J04 | 移除 runBlocking | 全部替换为 suspend 函数或 withTimeout |
| REQ-J05 | 诊断日志条件化 | 环境变量 LEGADO_DEBUG=true 时输出 |
| REQ-J06 | 50+ 真实书源兼容 | 端到端测试通过率 ≥ 95% |
| REQ-J07 | 50+ 真实订阅源兼容 | 端到端测试通过率 ≥ 95% |
| ~~REQ-J08~~ | ~~GAP-44 followRedirects 移除~~ | **取消**：源码核实确认 followRedirects 已正常实现，与真机一致 |
| REQ-J09 | GAP-22 ruleDescription 逻辑修复 | 规则描述解析正确 |
| REQ-J10 | Bug 修复逐行源码对比 | 每个修复附源码对比记录 |

### 3.2 Python 客户端需求

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-P01 | 虚拟环境管理 | requirements.txt + setup_venv.bat/sh |
| REQ-P02 | 单入口 CLI | python -m legado_client <command> |
| REQ-P03 | auto_fixer 接入主流程 | debug_runner 调用 auto_fixer.auto_fix_error() |
| REQ-P04 | verify_fix 真正验证 | 执行实际规则验证 |
| REQ-P05 | 经验闭环完整 | pending → AI agent → basic-memory |
| REQ-P06 | 3 个不存在模块处理 | 实现或移除 |
| REQ-P07 | 超时保护 | readline() 30s 超时 |
| REQ-P08 | 核心模块 80%+ 测试覆盖 | pytest --cov 报告 |
| REQ-P09 | 7 个弃用方法清理 | 移除或归档 |
| REQ-P10 | 双客户端合并 | tools/ 与 legado_client/ 统一 |

### 3.3 Skill 工作流需求

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-S01 | Phase 2 预校验集成 | source_validator + rule_precheck 在 debug-source.py 中调用 |
| REQ-S02 | Phase 3 降级路径 | JVM 不可用时自动降级到 Python verify-source.py |
| REQ-S03 | Phase 5 经验反哺 | 测试完成后自动提取经验写入 basic-memory |
| REQ-S04 | 14 个脚本整合为统一 CLI | python -m legado_client debug/verify/batch |
| REQ-S05 | SKILL.md 实现状态标注修正 | 4 处过时标注更新 |
| REQ-S06 | 5 个缺失决策编号补录 | AD-04/05/06/07/09 补入设计文档 |
| REQ-S07 | 预校验失败返回 Phase 2 | 不再 sys.exit(1)，返回 Phase 2 重新构建规则 |

### 3.4 目录结构需求

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-C01 | 无 __pycache__ | .gitignore + 清理 |
| REQ-C02 | 无 build/ 产物 | .gitignore + 清理 |
| REQ-C03 | 无 .gradle 缓存 | .gitignore + 清理 |
| REQ-C04 | 无废弃脚本 | 6 个废弃脚本删除 |
| REQ-C05 | 无孤立文件 | experience-pending.json 移入正确位置 |
| REQ-C06 | .gitignore 完整 | 覆盖所有缓存/产物类型 |

## 4. Scenarios

### S1: 书源端到端调试

```
输入：真实书源 JSON（来自开源阅读社区，合法授权）
流程：source_validator → rule_precheck → JAR debugBookSource → error_diagnoser → auto_fixer → 验证 → 经验反哺
输出：调试报告 + 修复建议 + 经验记录
验证：50+ 真实书源通过率 ≥ 95%
```

### S2: 订阅源端到端调试

```
输入：真实订阅源 JSON（合法授权）
流程：source_validator → rule_precheck → JAR debugRssSource → error_diagnoser → auto_fixer → 验证 → 经验反哺
输出：调试报告 + 修复建议 + 经验记录
验证：50+ 真实订阅源通过率 ≥ 95%
```

### S3: Python 客户端工程化使用

```
输入：pip install -e . 安装客户端
流程：python -m legado_client debug --source book_source.json
输出：调试报告
验证：无需手动设置 PYTHONPATH，虚拟环境自动管理
```

### S4: 经验闭环验证

```
输入：调试失败的书源
流程：error_diagnoser 诊断 → auto_fixer 修复 → 验证 → experience_manager 提取 → AI agent 写入 basic-memory
输出：basic-memory 中新增经验记录
验证：经验记录可被后续 Phase 1 检索到
```

### S5: JAR 仿真服务端性能

```
输入：50+ 书源批量调试
流程：batch 命令执行
输出：汇总报告
验证：单源调试 ≤ 30s，50 源批量 ≤ 5min
```

### S6: 降级路径验证

```
输入：JAR 不可用场景
流程：debug_runner 检测 JAR 不可用 → 自动降级到 Python verify-source.py
输出：降级调试报告
验证：降级后仍能完成基本校验
```

### S7: 目录结构清洁度

```
输入：git status
流程：检查 .gitignore 覆盖 + 无构建产物 + 无缓存文件
输出：干净的工作区
验证：git status 无意外文件
```

### S8: 子代理输出交叉验证

```
输入：子代理报告"已完成"的修复项
流程：代码库核实 → tasks.md 对比 → 实际运行验证
输出：交叉验证报告
验证：标记完成项必须有代码证据 + 运行通过
```

## 5. Constraints

### 5.1 版本锁定

| 约束 | 值 | 说明 |
|------|-----|------|
| jsoup 版本锁定 | 1.16.2 | 破坏性变更 jsoup#2017，不可升级 |
| Rhino 版本锁定 | 1.8.1 | Android 6 以下兼容，不可升级 |
| hutool 版本锁定 | 5.8.22 | 书源加解密依赖，不可升级 |
| OkHttp 版本锁定 | **5.3.2** | 与真机版本一致（已确认，非 4.x） |
| Python 版本 | 3.10+ | 类型提示兼容 |
| JVM 通信协议 | stdin/stdout JSON | 保持向后兼容 |

### 5.2 架构约束

| 约束 | 说明 |
|------|------|
| 单 JAR 架构 | legado-jvm.jar，fatJar 构建 |
| Python 单入口 | python -m legado_client <command> |
| 经验权威源 | Skill 文档为准，basic-memory 为索引层 |
| ReadBook 全局单例 | 多 Activity 共享，改状态需 @Synchronized 或 Mutex 保护 |
| NoStackTraceException | 所有业务异常继承此类，覆写 fillInStackTrace() |

### 5.3 合规约束

| 约束 | 说明 |
|------|------|
| 著作权合规 | 所有开发与测试遵守著作权法律法规，仅使用合法授权的内容源 |
| 测试样本合规 | 选取合法合规、真机可正常运行的真实书源/订阅源 |
| 不得侵权 | 不得用于侵犯他人著作权的行为 |

## 6. 强制验证闭环要求

### 6.1 真实源端到端测试

| 测试类型 | 数量要求 | 测试流程 | 通过标准 |
|---------|---------|---------|---------|
| 真实书源 | **50+** | 搜索 → 详情 → 目录 → 正文 | 通过率 ≥ 95% |
| 真实订阅源 | **50+** | 分类 → 列表 → 正文 | 通过率 ≥ 95% |

### 6.2 全流程闭环验证

```
Phase 1: 经验搜索 → Phase 2: 构建规则 → Phase 3: 测试驱动 → Phase 4: 源码深挖 → Phase 5: 经验反哺
   ↓                    ↓                    ↓                  ↓                  ↓
basic-memory      source_validator     JVM/Python验证      失败时源码分析    experience_manager
                  rule_precheck        auto_fixer                           → basic-memory
                                       verify_fix
```

**闭环要求**：
- 每个 Phase 完成后必须输出 `[PHASEX_COMPLETE]` 标志
- Phase 1/3/5 完成后必须将执行证据写入 basic-memory (project=legado)
- 未输出 `[PHASEX_COMPLETE]` 标志，禁止进入下一 Phase

### 6.3 经验反哺验证

| 环节 | 要求 | 验证标准 |
|------|------|---------|
| 经验提取 | experience_manager.extract() 自动提取 | 提取结果非空 |
| 经验写入 | write_to_basic_memory() 写入索引层 | basic-memory 可检索 |
| 经验检索 | 后续 Phase 1 可检索到新经验 | search_notes 命中 |
| 权威源同步 | Skill 文档同步更新 | references/ 文档更新 |

### 6.4 端到端一致性验证

| 验证项 | 要求 |
|--------|------|
| JAR 仿真端 vs 真机 | 同一书源在 JAR 和真机行为一致 |
| Python 客户端 vs JAR | 客户端调用 JAR 结果与直接调用一致 |
| auto_fixer 修复验证 | 修复后重新执行规则验证通过 |
| 子代理输出交叉验证 | 标记完成项必须有代码证据 + 运行通过 |

## 7. 执行约束规则

### 7.1 懒原则边界重定义

> **懒原则 ≠ 跳过必要实现**。V1 方案将"减少过度工程"曲解为"跳过必要实现"，导致 170+ 任务仅完成 8.8%。

| 允许（懒原则适用） | 禁止（懒原则滥用） |
|------------------|------------------|
| 不做用户未要求的"灵活性"扩展 | 跳过入参合法性校验 |
| 不为一次性代码创建抽象 | 省略异常捕获与错误反馈 |
| 不引入无用依赖 | 跳过资源自动释放 |
| 不写推测性错误处理 | 以"简化"为由跳过核心流程实现 |
| YAGNI 裁剪增值扩展功能 | 将一级门禁必做逻辑判定为可裁剪项 |

### 7.2 源码对标要求

> **所有实现必须先看源码逻辑再动手，不臆测。**

| 场景 | 要求 |
|------|------|
| JAR 仿真端实现 | 逐行对比开源阅读源码 |
| Bug 修复 | 附源码对比记录 |
| 版本锁定 | 与真机版本逐项核实（如 OkHttp 5.3.2） |
| 经验写入 | 必须经过源码深度分析核实 |

### 7.3 质量保障

| 保障项 | 要求 |
|--------|------|
| 子代理输出交叉验证 | 不信任单一来源，代码库核实 + 运行验证 |
| 测试覆盖率 | 核心模块 80%+（pytest --cov） |
| 测试结果详情 | 失败原因 + 修复建议，不仅"成功/失败" |
| 真实源测试 | 50+ 书源 + 50+ 订阅源端到端测试 |
| 文档同步 | 实施决策同步到设计文档，tasks.md 实时更新 |
| Phase 完成标志 | 每个 Phase 输出 `[PHASEX_COMPLETE]` 标志 |
| 任务后审计 | 书源/订阅源任务完成后调用 legado-workflow-auditor 审计 |
