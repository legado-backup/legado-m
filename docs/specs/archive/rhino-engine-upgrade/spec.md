# Rhino 引擎升级方案（语法兼容 + 性能）— spec.md

> 状态：🔄 设计中

## Intent

**为什么做**：Legado 内建书源/订阅源大量依赖 Rhino 执行自定义 JS。当前锁定为 1.8.1 基于「新版本 API 33 以下不可用」的防炸约束，但从未系统评估过：最新版 Rhino 是否真的破坏 1.8.1 的语法兼容面，以及是否可利用其性能提升。本 spec 回答三个问题：(1) 可替换的最新 jar 是什么；(2) 它能否兼容现有书源/订阅源语法；(3) 能否加速解析。

**预期收益**：若可行，升级到 1.9.1 可获得 10-30% JS 解析/执行性能提升，同时让书源作者可以用到 1.8.1 不支持的新 ES6 语法（super/reflect/proxy/destructuring/spread 等）。

**产出形态**：这是一个「分析 + 决策 + 可行性 Spike」型 spec，最终交付物是**选型决策报告 + 验证通过的升级建议**（是否升、升到哪个版本、采用哪条 minSdk 路径）。

## Scope

### In scope
- 候选引擎版本横评（Rhino 1.9.1 / 1.8.0 / 1.7.15.1 主线条 + QuickJS/Graal.js 作为对照否定项）
- 1.9.x 的 `VarHandle`/API 33 障碍实证（静态字节码扫描 + 低 API 验证）
- 采样真实书源/订阅源 JS 在 1.9.1 下回归（语法兼容性）
- 同脚本 1.8.1 vs 1.9.1 解释模式性能抽样
- 升级路径决策（minSdk 门槛 / 双引擎 flavor / 保持锁定）
- 文档同步

### Out of scope
- 不切换到 QuickJS/Graal.js（Java 互操作模型差异大，属于颠覆性改造）
- 不改动 `modules/rhino` 包装层的对外接口（保持 `RhinoScriptEngine.eval/compile/run` 语义）
- 不改变现有书源的规则 JSON 结构
- 不引入 bytecode/编译模式（Android ART 无法运行时生成类，保持 `setInterpretedMode(true)`）
- 不做 1.8.1 → 1.9.1 之外长期维护（1.9.x 系列已停止前向发布可能性低而排除 2.0.0-SNAPSHOT）

## Approach

### Selected Approach：Rhino 1.9.1 项下可行性验证 → 以「minSdk 33 + 1.9.1」为主路径

以 **Rhino 1.9.1（最新稳定版）** 作为主候选，通过一个受控 Spike 验证两件事：
1. **障碍实证**：确认 1.9.1 是否真的在 class file 中引用需 API 33+ 的 `VarHandle`（若仅存在于编译模式/工具模块，说明纯解释模式下可用则不构成障碍）。
2. **收益实证**：现有书源/订阅源 JS 在 1.9.1 下语法回归 + 解释模式性能对比。

**✅ 障碍实证已完成（2026-08-03，字节码扫描 + javap + 运行时探针）**：1.9.1 中 `VarHandle`/`compareAndExchange` 唯一出处 `SlotMapOwner$ThreadedAccess`。先 javap 反汇编确认其位于 TS 槽位访问路径；再用 `-verbose:class` 运行时探针证实——因 `feature17(THREAD_SAFE_OBJECTS)` 默认 false（`useThreadSafeObjectsByDefault=false`），项目配置下 `createSlotMap()` 只走非线程安全实现，**`ThreadedAccess` 全程不加载，26/26 书源片段 parsed-ok**，运行时对 API<33 是安全的。**真正剩余障碍被收敛为构建期 D8 反糖化**（desugaring 不覆盖 `VarHandle`），需以 Spike2（`assembleDebug`）最终确认。故本 spec 主路径定为：**先以 minSdk 33 + 1.9.1 的 Spike 实测构建期 D8 是否放行；若否由 minSdk 23→33 兜底**。

因您倾向接受 minSdk 门槛，本 spec 主路径定为：**minSdk 23→33（或至少更显式），升级 Rhino 1.9.1**。语法兼容由 `RhinoScriptEngine.init` 中既已显式 `cx.languageVersion = Context.VERSION_ES6` 保证（1.9.x 以此为默认并向上超集，现有书源/订阅源 ES5/ES6 行为不回归）。若后续价值判断不愿放弃 API 23-32 用户，可退回「保持 1.8.1 锁定」基线；QuickJS/Graal.js 不入选，理由见 Alternatives 细化。

理由：1.9.1 是唯一满足「最新稳定 + ES6 语法超集 + 10-30% 性能」且**保留 `org.mozilla.javascript.*` 兼容 API** 的 drop-in jar —— 现有 `modules/rhino` 包装层（`Context/ContextFactory/Scriptable/ClassShutter/WrapFactory/ImporterTopLevel/DefiningClassLoader`）不受影响。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|----------|
| **Rhino 1.8.0** | 1.8.x 系列，与 1.8.1 差异极小 | 无性能/语法增益，且同样继续引入 VarHandle 相关改动；不如 1.9.1 直接 |
| **Rhino 1.7.15.1** | 1.7 系列补丁版（2025-12 重建） | 语法落后（无 super/reflect/proxy）且无 1.9 的性能优化；不满足"加快解析" |
| **QuickJS（Android 原生实现）** | V8-like 现代 ES、纯 JS 执行性能远超 Rhino | ① 需引入 JNI/.so；② **Java↔JS 互操作契约与现有 `RhinoWrapFactory/NativeJavaObject` 完全不同**——Legado 书源核心价值正是「JS 调用 Java（OkHttp、NativeBaseSource.map、MapAccess）」，QuickJS 的宿主桥（`JS_CNewString`+NativeObject）单对单需重写全部 WrapFactory/BaseSource/ExploreRule/BookInfoRule 调用点；③ 所有依赖 Java 互操作的既有书源行为 100% 需重测。为颠覆性改造、高风险、非 drop-in |
| **Graal.js（Polyglot）** | 性能极佳、ES 兼容度最高（ES2023） | 需要 native-image/SVM 静态镜像，**Android 不可用**（Truffle 依赖 GraalVM JVMCI）；实现巨大（数百 MB）非 drop-in；Java↔JS interop 模型亦与 Rhino 不同，需重写包装层 |
| **保持锁定 1.8.1** | 零变革 | 失去 10-30% 性能与新增 ES6 语法；仅在决定不提升 minSdk 时作为兜底路径 |
| **minSdk 整体提到 33** | 直接解锁 1.9.1 | 放弃 API<33 设备；作为主路径的前提代价，由最终决策与用户接受度决定 |

**语法兼容性对比摘要（Q：为什么不选 QuickJS/Graal 而坚持 Rhino 系列？）**：

| 维度 | QuickJS | Graal.js | Rhino 1.9.1（本项目） |
|------|---------|----------|------------------------|
| JS 语法面 | ES2020+（强） | ES2023（最强） | ES6+ 超集（现有源够用） |
| 书源核心·Java 互操作 | ✗ 需重写 WrapFactory | ✗ 需重写 interle 模型 | ✅ 原样保留 `NativeJavaObject`/`WrapFactory` |
| Android 可运行性 | 需 JNI/.so，脆弱 | ✗ 不可用 | ✅ 原生 |
| `org.mozilla.javascript.*` API | ✗ 彻底不同 | ✗ 彻底不同 | ✅ 同套、drop-in |
| 现有书源回归工作量 | 100% 重测+重写桥 | 彻底重写 | 仅语种子集回归 |

结论：书源/订阅源的价值密度在于「**JS 规则 + Java 数据读取/解析互操作**」，语法特性是次要的。QuickJS/Graal.js 在纯 JS 性能与语法全面领先，但正是互操作契约的断裂使它们从「功能与语法兼容性」角度看反而更差，非同族升级可比。

### Drawbacks

- **API 33 门槛**：若 1.9.1 确实引用 `VarHandle`，则 API 21-32 设备崩溃；解除需「minSdk 提升」或「双引擎 flavor」，两者都有成本。
- **行为漂移**：默认 ES6 语言级别在 1.9.x 已改为默认开启，若 Spike 中现有开源未显式覆盖 `languageVersion`，个别依赖 ES5 旧语义（如 `Array.prototype.concat` spreadable、保留字）的 JS 可能表现不同。本引擎已在 `RhinoScriptEngine.init` 中显式 `cx.languageVersion = Context.VERSION_ES6`，该漂移风险已被工程消除。
- **首次加载/内存**：1.9.1 jar 增大（分模块化），冷启动类加载略增。
- **生态未定**：1.9.x 改造成多模块（`rhino`/`rhino-all`），`org.mozilla:rhino` 仍发布，但需留意 module 拆分带来的传递依赖变化。

### Prior Art

- 本仓库 `docs/specs/dependency-upgrade-optimization/`（AD-15）已确认 rhino/commons-text 因 `VarHandle`（API 33）/`Arrays.setAll`（API 24）desugaring 不覆盖而锁定 —— 本 spec 在其基础上对 rhino 单独深入。
- Rhino 官方 RELEASE-NOTES（1.9.0/1.9.1）：默认 `VERSION_ES6`、性能提升 10-30%、supersed by destructuring/spread/symbol/super/reflect/proxy/global+globalThis。
- 官方「Rhino 兼容性表」（compat/engines.html）为语法子集提供参考。

## Requirements

### Functional Requirements

- FR1：明确可替换的最新 jar 候选（截至 2026-08，最新稳定版为 1.9.1）。
- FR2：验证候选 jar 与现有 `modules/rhino` 包装层 API 的源码级兼容性（编译通过）。
- FR3：验证现有用户写作的书源 JS / 订阅源 JS 在候选 jar 下回归无语法回归（至少覆盖基础 + 常用 ES6）。
- FR4：量化候选 jar 在解释模式下的性能相对 1.8.1 的变化。
- FR5：给出最终升级决策（升级到 1.9.1 + minSdk 门槛 / 双引擎 / 保持锁定）及理由。

### NFR

- NFR1：不破坏现有书源/订阅源 JSON 与规则字段结构。
- NFR2：保持 `RhinoScriptEngine` 对外接口与协程/取消/递归保护机制不变。
- NFR3：升级不得引入 `ApiToolsEloquent`（沿用 `RhinoClassShutter` 黑名单 + `NoStackTrace` 处理）。
- NFR4：性能对比需覆盖「解释模式」，因 Android 无法运行时字节编译。
- NFR5：只有 Spike 通过的结论才进入最终落地实现。

## Scenarios

### 场景 A（可行性成立，minSdk33 + 1.9.1）
- A1：Spike 证明 1.9.1 在 API 33+ 运行（`VarHandle` 唯一出处已定位并判定需 API≥33，属核心路径）。
- A2：现有书源/订阅源语法回归全通过，性能提升 ≥10%。
- 决策：**minSdk 23→33，升级 1.9.1**，进入正式实施。
- 残余行动：评估 API 23-32 用户影响面、确认 minSdk 提升是否影响其他依赖（如 commons-text 1.13.1 的 `Arrays.setAll` API24 限制并存）。

### 场景 B（障碍无法跨越或 user 放弃 minSdk）
- B1：minSdk 提升决策被否决（不愿放弃 API 23-32）。
- B2：语法回归出现破坏性差异并影响现有源。
- 决策：保持 1.8.1 锁定，文档沉淀「升级到 1.9.1 的里程碑」（待 minSdk 提升时机直接跳 1.9.1）。

### 场景 C（部分成立）
- 性能提升但语法有 minor 漂移：按漂移影响面分级协商（可升级可回滚的清单 + 影响数），由用户决策。

## 状态

🔄 设计中