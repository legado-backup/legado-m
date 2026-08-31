# master-track-orchestration — 三轨总线任务编排（Compose 化 × legadoc 对标 × ng 对标）

> 状态：🔄 开发中（检查点 1 通过，W0 执行中）｜ 创建：2026-08-31 ｜ 方法：3 子代理并行深度分析三 spec 全量文档 → 主代理汇总波次编排 → 七轮审核闭环（规范性/事实核对/遗漏排查/打架推演/矩阵式冲突扫描/内部一致性回归/可执行性演练）

## 功能概述

对当前三条任务轨进行统一总线编排：归类排序、待优化项先后顺序裁决、共性问题整合、冲突热点治理，形成可执行的单线推进波次计划。

| 轨 | spec | 状态 | 分期体系 | 未完成量 |
|----|------|------|---------|---------|
| A 前端 Compose 化 | compose-migration-status-audit | ✅ 设计完成 | B0→B5 严格串行（轨 A AD-07 禁跳批） | 47 项 |
| B legadoc 对标 | legadoc-benchmark-analysis | 🔄 设计中（实况：tasks 全勾，仅缺检查点裁决 AD-03~06 + README 状态转正） | C0→C5 | 检查点未过 |
| C ng 对标 | ng-benchmark-analysis | ✅ 设计完成（用户已裁决 P0 先行） | P0→P1→P2/P3→P5（P5 视觉载体文件名 P4-visual-patterns.md；P4=AI 应用层二期暂缓） | 1 项（5.2 登记） |
| V 视频域（挂靠轨） | video-sniff-403-and-rss-classic-fix 等 14 个活跃 spec | 🔄 并行会话执行中（Phase 3 已落地 4.8e 方案 A，083119 待用户 L2 验收） | Phase 0/1/2/4.1-4.9 已完，剩 4.10 复验 + Phase 4 | 总线只做协调不接管 |

## 核心结论速览

| 结论 | 内容 |
|------|------|
| 唯一真 bug | legadoc C0-F1（AnalyzeRule 缓存污染）是三轨全部任务中唯一缺陷修复项，**最高优先且零依赖可立即开工**（三向量已源码逐点核实命中） |
| 公共闸门 | ui-style-unify-deep-fix 剩余收口（实况：Phase1/2/S/H/T/X 已完成，剩 Phase3 D1/D2 复杂弹框 + Phase4 防回潮 + R3 终测）是轨 A（B0）与轨 C（P5 视觉）的共同前置，必须 W0 优先收口 |
| 检查点合并 | legadoc AD-03~06 裁决并入本总线检查点 1，一次用户审查同时解锁两 spec |
| 波次编排 | W0 公共闸门 → W1 安全与基线 → W2 地基与样板 → W3 旗舰攻坚 → W4 长尾与听书 → W5 收官与视觉（详见 design.md） |
| 共性整合 | 6 大整合点：DB 版本链占号（video-sniff 4.8e 已实占 v109，P1/P3 自适应顺延）/ 文件级串行热点 14 对 / deep-fix 公共闸门 / B2 测试基建复用 / ui-standards 唯一基线 / 缺口补登 3 处；另设外部活跃任务协调面（V 轨挂靠，详见 design.md §4） |
| 验证与交付 | 四层验证体系（design §6）：L1 分期级沿用各轨原分册验证设计 / L2 波次级（整包编译+全量单测+E2E 冒烟+热点 diff 审计）/ L3 里程碑级（W2 基线包/W4 三热点域走查/W5 全量 E2E）/ L4 交付级（publish.bat 五阶段）；回退=bak 备份+观察开关+按分期 revert；提交=一期一提交单元+前置五门禁 |
| 全面审核 | 七轮审核子代理闭环：规范性（3 P1+6 P2 全修）/ 事实核对（10/10 一致含源码抽查）/ 遗漏排查（视频/下载/网络域 18 实质协调面 spec 挂靠）/ 打架推演（§5/§5.1 X1-X14）/ 内部一致性回归 / 可执行性演练 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 调研 Intent/Scope/Approach（含 Alternatives+Drawbacks+Prior Art）/Requirements R1-R11/Scenarios S1-S5 |
| [design.md](./design.md) | 三轨分析汇总 + 优先级分级 + 波次编排 W0-W5（mermaid+波次表）+ 共性整合矩阵 6 项 + §4 V 轨挂靠 + §5 打架推演 + §5.1 全覆盖扫描 X1-X14 + AD-01~07 + §6 四层验证交付策略 + File Changes |
| [tasks.md](./tasks.md) | W0-W5 波次执行清单 + AOAdapt 日志 |

## 边界声明（本 spec 不做什么）

- 不重复三 spec 内部已定稿的函数级设计，只做轨间编排；各分期实施仍按原 spec 另立实施 spec 推进
- 不改变各 spec 内部已定稿的批次顺序约束（如轨 A 禁跳批、轨 C P0 先行裁决）
- ui-style-unify-deep-fix 的剩余实施（Phase3 D1/D2 + Phase4 防回潮，R3 终测由 B0 代执行）不在本 spec 范围，但作为公共闸门纳入编排
- ng P4（AI 应用层二期）按轨 C 决策表 #15 暂缓，仅登记暂缓清单落点（tasks 3.7.2）
