# JVM 仿真服务端架构重构：从「从零仿真」到「源码抽取」

> **状态**：🔄设计中
> **创建日期**：2026-06-19
> **优先级**：P0
> **预估任务数**：~245

---

## 核心问题

当前 JVM 仿真服务端（`.trae/skills/legado-source-creator/tools/mvp1-build/`）存在根本性架构缺陷：

| 问题 | 根因 | 影响 |
|------|------|------|
| **Bug 层出不穷** | 从零重写 Legado 逻辑（MinimalMockJsExtensions/MockSymmetricCrypto），而非抽取真机源码 | ZeroPadding、`{{page}}`、相对URL 等本不该出现的问题反复出现 |
| **4 个 JAR** | MVP1-4 逐步迭代产物，未合并 | 维护复杂，用户困惑 |
| **性能慢** | 每次调用启动新 JVM（3-5秒） | 测试 7 个源需要 30+ 秒 |
| **真实源未优化** | 只做了"测试验证"，没做"优化改造" | 用户给的源有问题没修复 |
| **不看源码就动手** | 修 bug 靠猜测而非源码验证 | 修复方向偏离真机行为 |

## 核心方案

**从 Legado 真机源码直接抽取核心规则引擎，移除 Android 依赖，打包为单一 JVM JAR。**

### 抽取可行性分析

| 等级 | 类数 | 占比 | 说明 |
|------|------|------|------|
| A级（零依赖直接抽取） | 4 | 29% | RuleDataInterface, RuleAnalyzer, RuleData, CustomUrl |
| B级（仅删@Keep注解） | 4 | 29% | AnalyzeByJSoup, AnalyzeByJSonPath, AnalyzeByRegex, QueryTTF |
| C级（替换TextUtils） | 1 | 7% | AnalyzeByXPath |
| D级（重度重构） | 5 | 36% | AnalyzeRule, AnalyzeUrl, JsExtensions, BookSource, RssSource |

**64% 的核心类可低成本抽取，modules/rhino 模块已几乎 JVM 就绪。**

> **⚠️ 第三轮审查补充**：14 个核心类仅覆盖"规则引擎层"，执行流程层（WebBook/Rss/BookList 等）不抽取到新模块，但在 RssSourceDebugger/BookSourceDebugger 中需内联复现其调用链。BookSource/RssSource 通过 BaseSource 接口间接继承 JsExtensions（77 个 import），抽取时需移除继承链。

## 核心能力

1. **真机源码抽取**：直接使用 Legado 的 AnalyzeRule/AnalyzeUrl/JsExtensions 等核心类，而非从零重写
2. **单 JAR 打包**：合并 MVP1-4 为一个 fat JAR
3. **批处理模式**：一次 JVM 启动处理多个源，避免反复启动开销
4. **真实源优化**：用抽取后的 JAR 实际修复和优化用户提供的真实源

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（Intent/Scope/Requirements/Scenarios/源码参照声明/降级能力边界） |
| [design.md](./design.md) | 技术设计（抽取策略/架构决策/数据流/文件变更/JsExtensions 132方法清单/防瞎猜测机制/增量验证门禁/79条陷阱映射/Python适配差异/Skill适配差异/回滚策略） |
| [tasks.md](./tasks.md) | 任务清单（7 个阶段 245 个任务项 + 每阶段门禁引用） |

## 设计原则

1. **源码优先**：所有逻辑必须来自 Legado 真机源码，禁止臆测（见 design.md 第7节防瞎猜测机制）
2. **最小改动**：抽取时只移除 Android 依赖，不改变核心逻辑
3. **接口抽象**：JsExtensions 等平台耦合类拆分为接口+实现（见 design.md 第6节132方法清单）
4. **向后兼容**：保留现有 stdin/stdout JSON 协议，debug-source.py 无需大改
5. **实测驱动**：每个抽取阶段完成后用真实源验证（见 design.md 第8节增量验证门禁）
6. **降级透明**：Stub 降级方法的能力边界必须明确标注（见 spec.md 第3.2节降级能力边界）
7. **执行流程内联**：WebBook/Rss 等执行流程层类不抽取，在 Debugger 中内联实现（见 design.md 第1.3节）
