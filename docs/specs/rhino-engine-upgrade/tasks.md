# Rhino 引擎升级方案 — tasks.md

> 状态：✅ 已完成（最终决策：**路径 B — 保持 1.8.1 锁定**，沉淀待升级里程碑）

## 1. 现状与锁定梳理
- [x] 1.1 确认当前 rhino 版本（`libs.versions.toml`: `rhino=1.8.1`，模块坐标 `org.mozilla:rhino`）与 `modules/rhino/build.gradle`（`api libs.mozilla.rhino`）
- [x] 1.2 阅读 `modules/rhino` 包装层并确认：`RhinoScriptEngine.init` 显式 `VERSION_ES6` + `setInterpretedMode(true)`；`ContextFactory.hasFeature` feature17 默认 false（未启用线程安全对象）
- [x] 1.3 记录 app 侧 Rhino 调用点清单（`App.initRhino`/`BaseSource.338,344`/`AnalyzeUrl.386,392`/`AnalyzeRule.854,967`/`SharedJsScope.37,65,69`/`BookExtensions` 等）

## 2. 候选引擎横评
- [x] 2.1 列出候选版本时间线（1.7.15.1=2025-12 / 1.8.0=2025-01 / 1.8.1=2025-12[当前] / 1.9.0=2025-12 / 1.9.1=2026-02[最新]）
- [x] 2.2 记录 1.9.x 增强（默认 VERSION_ES6、性能 10-30%、super/reflect/proxy/global、模块化拆分）
- [x] 2.3 记录 QuickJS / Graal.js 作为对照否定项及否决理由
- [x] 2.4 输出候选对比表（spec.md Approach）

## 3. 障碍实证（Spike 1/2）
- [x] 3.1 下载 1.9.1 jar，zipfile 常量池扫描 → `java/lang/invoke` 1.9.1=166 类 / 1.8.1=132 类
- [x] 3.2 `javap -c` 定位 → `VarHandle`/`compareAndExchange` 唯一出处 `SlotMapOwner$ThreadedAccess`
- [x] 3.3 判定属于 TS 槽位访问路径（非仅 Codegen）
- [x] 3.4 结合解释模式判定运行时是否触及 → **运行时探针证明不触及**（feature17=false，`ThreadedAccess` 永不加载）
- [x] 3.5 AOAdapt：见日志（运行时"必崩"结论被探针推翻，收敛为构建期 D8 反糖化）

## 4. 语法回归（Spike 3）
- [x] 4.1 抽取真实源 JS 片段 26 段（`bookSources.json`/`rssSources.json`/`coverRule`/`httpTTS`/`dictRules` 等）
- [x] 4.2 最小复现：桩宿主后 1.8.1 与 1.9.1 各求值一次
- [x] 4.3 比对输出与异常：**两引擎完全一致（26/26 parsed-ok）**
- [x] 4.4 结论：ES6 超集，无回归（唯一 `Empty JSON string` 为数据问题，两引擎同现）

## 5. 性能对比（Spike 4）
- [x] 5.1 设计同脚本同输入基准（RhinoBench/RhinoBench2）
- [x] 5.2 1.8.1 vs 1.9.1 解释模式各执行取均值
- [x] 5.3 记录耗时：计算密集 1.9.1 ≈175ms vs 1.8.1 ≈181ms；书源型 1.9.1=4.67ms vs 1.8.1=6.76ms
- [x] 5.4 输出百分比：书源型负载 **≈+31%**，纯算术 ≈+3%

## 6. 决策输出（🛑 已与用户确认，定案 **路径 B**）
- [x] 6.1 依据 Spike 门禁生成结论 → 用户选定**路径 B：保持 1.8.1 锁定**
- [ ] 6.2 若路径A/B：改 `libs.versions.toml` 编译 —— **N/A（本次走路径 B，不改依赖）**
- [x] 6.3 沉淀「待 minSdk≥33 直跳 1.9.1」里程碑（见下方”M.milestone“）
- [x] 6.4 `quick-reference.md` 锁定行复核：版本不变（仍 1.8.1），补注"运行时已实证安全，可升 1.9.1 的门槛=构建期 D8 反糖化"

## 7. 文档同步与交付
- [ ] 7.1 更新 updateLog.md —— **N/A：本次为纯分析/决策，无产品版本变更**
- [x] 7.2 更新 `docs/INDEX.md` 本 spec 状态（移动到已完成区）
- [x] 7.3 回填本文件 AOAdapt 日志与完成级别

## M.milestone（沉淀）
> **里程碑：minSdk 提升 ≥33 时直跳 Rhino 1.9.1**
> - 触发条件：minSdk 23→33（或放弃 API<33 用户）
> - 已实证收益：书源型 +31% 性能、ES6 超集、`VAR_ES6` 下 26/26 语法零回归
> - 已实证风险收敛：运行时安全（`ThreadedAccess` 永不加载），唯一门槛为构建期 D8 反糖化（desugar 不覆盖 VarHandle）
> - 附带解锁：commons-text `Arrays.setAll`（API24）锁定一并解除
> - 动作：改 `libs.versions.toml` `rhino=1.9.1` + `assembleAppDebug` 验证 D8 → 跑 Spike4 留痕

## AOAdapt 日志
- **3.5 障碍定性反转**：初判字节码（javap）认为 `ThreadedAccess` 属核心路径、API<33 必崩。深入看 `createSlotMap()` 发现 `hasFeature(17)` 分支后，用 `-verbose:class` 运行时探针证实该项目配置下 `ThreadedAccess` **永不加载**、26/26 通过。→ 结论修正为：运行时安全，唯一障碍=构建期 D8 反糖化。已同步 README/spec/design。
- **6.1 决策路径重命名**：tasks 初稿将"路径B=双引擎 flavor"，后按其定义修正为"路径B=保持锁定+里程碑"（对应 spec 场景 B）。用户最终选择旨在保持锁定，与 milestone 对齐。

## 完成级别
- **Level 3（场景验证）✅**：真实书源 26 段回测、运行时探针、性能基准、构建期 D8 定性——本次"分析型 spec"全部实证得成立，交付为**决策报告**（路径 B + milestone）而非代码变更。