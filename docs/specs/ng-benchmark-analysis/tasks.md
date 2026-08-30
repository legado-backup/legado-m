# tasks.md — ng-benchmark-analysis

## 1. 准备工作
- [x] 1.1 需求分析（范围/边界/方案） ✅ Level 2
- [x] 1.2 加载 forks_comparison_methodology.md 对齐输出格式 ✅ Level 2

## 2. 源码获取与身份确认
- [x] 2.1 检索确认 NG 仓库身份（`joestar817/legado_NG`，fork 网络定位） ✅ Level 2
- [x] 2.2 获取 release 日志（3 个最新 release body 提取） ✅ Level 2
- [x] 2.3 获取完整源码快照（zipball → `temp\legado_NG_src\legado_NG-main`） ✅ Level 2

## 3. 并行深度分析（8 子代理两轮）
- [x] 3.1 第一轮·AI 能力域分析（供应商/MCP/压缩/技能包/净化扫书） ✅ Level 2
- [x] 3.2 第一轮·听书能力域分析（分镜/路由/实体/Compose UI） ✅ Level 2
- [x] 3.3 第一轮·视觉能力域分析（液态玻璃/材质角色/主题 Resolver/迁移度） ✅ Level 2
- [x] 3.4 第一轮·工程安全域分析（8 项沙箱修补/CI-CD/演进主线） ✅ Level 2
- [x] 3.5 第二轮·网络/协程/WebView 逐文件 diff（结论：本项目超集） ✅ Level 2
- [x] 3.6 第二轮·规则引擎/书源执行链 diff（结论：JS API 无缺口，NG 强在沙箱） ✅ Level 2
- [x] 3.7 第二轮·数据层实体/DB 演进对比（结论：v108 已分叉，迁移链须自起重编） ✅ Level 2
- [x] 3.8 第二轮·UI/服务全景清单对比（结论：NG=AI 纵深，本项目=广度+视频） ✅ Level 2

## 3A. 设计前置（回应"设计前置，禁止边学边改"审查意见）
- [x] 3A.1 沉淀统一证据包 evidence-pack.md（8 轮分析全事实源） ✅ Level 2
- [x] 3A.2 重写 design.md 为总体设计（全景矩阵/双向对比/决策表 v2/AD-01~06） ✅ Level 2
- [x] 3A.3 P0 书源安全加固实施级设计（migration-designs/P0） ✅ Level 2
- [x] 3A.4 P1 AI 地基实施级设计（migration-designs/P1） ✅ Level 2
- [x] 3A.5 P2 MCP 服务实施级设计（migration-designs/P2） ✅ Level 2
- [x] 3A.6 P3 听书多角色一期实施级设计（migration-designs/P3） ✅ Level 2
- [x] 3A.7 P5 视觉三模式实施级设计（migration-designs/P4） ✅ Level 2
- [x] 3A.8 设计期实测修正回灌决策表（#3 降为保护项/#6 改融合路线/#9 加 LocalDialogueSegmenter） ✅ Level 2

## 4. 汇总与文档生成
- [x] 4.1 生成 README.md（概述+速览+索引） ✅ Level 2
- [x] 4.2 生成 spec.md（Intent/Scope/Approach+Alternatives+Drawbacks/Requirements/Scenarios） ✅ Level 2
- [x] 4.3 生成 design.md（四域对比+借鉴决策表 13 项+实施路径+ADR×5） ✅ Level 2
- [x] 4.4 生成 tasks.md（本文件） ✅ Level 2

## 5. 文档同步
- [x] 5.1 更新 docs/INDEX.md 活跃 Specs 表 ✅ Level 2
- [ ] 5.2 追加 NG 条目到 docs/project-rules/forks-reference.md（版本清单权威源） ⏳ 待用户裁决后与实施 spec 一并处理

## 6. 验证
- [x] 6.1 二次验证：文档关键章节齐全（四文档必含章节/五份迁移设计各 10 节/决策表 v2 修订落盘） ✅ Level 2
- [x] 6.3 检查点1 用户审查意见落实：①双向客观对比 ②设计前置重构（8 轮分析+证据包+总体设计+5 份实施级设计） ✅ Level 2
- [ ] 6.2 用户审查裁决（检查点 1，二轮） ⏳

## AOAdapt 日志

- [x] 3A 设计前置轮（用户二轮审查后）
  - Action: 用户质疑"设计文档这么少，能否保证迁移交付"，裁定设计前置、禁止边学边改、先别实施
  - Observation: 初版仅四亮点域分析+决策表，缺全维度 diff 与实施级设计；且起草中发现初版三处误判（NetworkLog 已脱敏/已有 AiProviderConfig/UI/NG 兜底逻辑缺陷）
  - Adapt: ①补第二轮 4 子代理逐文件 diff（网络/规则引擎/数据层/UI 全景）②沉淀 evidence-pack.md 统一事实源 ③重写总体设计+5 份实施级分期设计（逐文件映射/DB/风险/验证）④实测修正回灌决策表——验证了"设计前置"价值：不前置就会把 3 处误判带进实施
- [x] design.md 修订期间发现同消息并行 Edit 同一文件违反串行规范
  - Action: 一次消息内 4 个并行 Edit 作用于 design.md
  - Observation: 并发文件修改规范禁止该模式；Grep 复核 4 处修订实际全部落盘，未发生竞态丢失（本次侥幸）
  - Adapt: 复核后确认无损失；后续同文件 Edit 严格串行

- [x] 6.3 检查点1 审查修订
  - Action: 初版报告以"NG 有什么"单向主线输出
  - Observation: 用户指出"不能处于恭维我的角度，实事求是分析"，单向报告易造成"NG 全面领先"误判
  - Adapt: 补入 §4 双向客观对比（含本项目对 NG 的反超项与"不该迁什么"），结论修正为"两分支分叉演化、互补而非替代"；另用户指令后半句截断，待澄清后执行

- [x] 2.3 获取完整源码快照
  - Action: 执行 `git clone --depth 1` 浅克隆 NG 仓库
  - Observation: GitHub 网络停滞，20+ 分钟 pack 未完成（tmp_pack 持续存在，无进度输出）
  - Adapt: 停止克隆，改用 codeload zipball 下载+Expand-Archive，2 分钟内完成，内容等价（无 git 历史，分析不需要）；残留半成品克隆目录 `temp\legado_NG_ref` 因沙箱 allowlist 无法删除，留待手动清理
- [x] 2.1 检索确认 NG 仓库身份
  - Action: WebSearch "legado-ng" + GitHub API 仓库名搜索
  - Observation: GitHub 仓库搜索默认排除 fork，直接搜不到 NG 官方仓库；聚合站也无条目
  - Adapt: 改用 forks API 列举 legado-E 的 fork 网络（按 stars 排序），从 fork 描述中精确定位 `joestar817/legado_NG`（65 stars，活跃推送 2026-08-28）
- [x] 1.2 加载对比方法论
  - Action: 按 AGENTS.md 子规范加载表读取 forks_comparison_methodology.md
  - Observation: 该方法论要求逐文件 diff + 引用带行号源码，但本次对象是整目录级新增能力，diff 法失配
  - Adapt: 保留方法论的核心产出要求（借鉴决策表+ADR 集成+Alternatives 引用对比结论），对比方法在 AD-01 记录为"能力域分组深读"，并已在 design.md 声明差异理由

## 完成级别说明

本 spec 为调研类任务，无代码交付，统一按 Level 2（功能验证=文档关键章节齐全+结论有源码路径级证据）标注；Level 3（真实数据回测）不适用于调研任务，迁移项的真机验证将在各实施 spec 中执行。
