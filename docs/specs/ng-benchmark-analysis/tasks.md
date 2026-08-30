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

## 3B. 第三轮深化（/goal：函数/代码级+规范对齐+前后端整体改造方案）
- [x] 3B.1 P0 深化 601 行（逐类逐函数+6 新类 kotlin 骨架+16 边界+21 单测方法+D13 观察钩子/D15 开关实时读/D16 ns 短码日志） ✅ Level 2
- [x] 3B.2 P1 深化 589 行（26 字段全表/AiProviderConfig v2 30 字段草案/J1-J9 注入点/六桶算法表/3 表 DDL+Migration 草案/D11 OkHttp await 同源降本） ✅ Level 2
- [x] 3B.3 P2 深化 399 行（四模块拆分+NG 行号区间→模块映射表+69 工具规格表+四层安全代码级+5 决策增补） ✅ Level 2
- [x] 3B.4 P3 深化 444 行（五级路由 kotlin 草案/LocalDialogueSegmenter 完整设计+8 单测用例/7 段 diff 式改造/6 新表 DDL/DD10-DD15） ✅ Level 2
- [x] 3B.5 P5 深化 540 行（快照四 data class 逐字段/Resolver/MaterialSurface 三分支/18 处直读清单+2 处源码勘误/13 边界/AD-P4-6~10） ✅ Level 2
- [x] 3B.6 交叉验证：五文件尾章节 Grep 全命中+探针文件清理（含 migration-designs/_wtest.txt 残留，V1-#21 发现后删除） ✅ Level 2

## 3C. B 类疑惑关闭（用户裁决"关闭 B 类后收口"）
- [x] 3C.1 P0 五条关闭（OQ-1 保持不回查/OQ-2 盲区量化升级/OQ-8 绕行面≈0/OQ-9 不扩集/OQ-11 三流程不挂载+二期候选 AutoTask） ✅ Level 2
- [x] 3C.2 P1 两条关闭（OQ-4 默认 258k/OQ-7 一次性导入器 +0.3d→8.8d） ✅ Level 2
- [x] 3C.3 P2 一条关闭（OQ-2 实质性修正：UI 忙检测不可实现→MCP 侧 Mutex 重入守卫） ✅ Level 2
- [x] 3C.4 P3 一条关闭（K2 强制非流式+静态标注，不联动禁用） ✅ Level 2
- [x] 3C.5 P5 两条关闭（OQ3 四路分流不设独立批次/OQ2 常量命名通过） ✅ Level 2
- [x] 3C.6 OQ 总账：34 条 = B 类 11 已关闭 + A 类 ~18 按默认裁决随检查点确认 + C 类 ~5 转实施验证项（灰度观察/真机校准） ✅ Level 2
- [x] 3C.7 V3/V4/V5 修复吸收：P0 9 处/P1 11 处/P2 7 处/P3 7 处/P5 6 处/design 3 处，五文件行数终态 P0=605/P1=601/P2=403/P3=446/P5=547 ✅ Level 2

## 4. 汇总与文档生成
- [x] 4.1 生成 README.md（概述+速览+索引） ✅ Level 2
- [x] 4.2 生成 spec.md（Intent/Scope/Approach+Alternatives+Drawbacks/Requirements/Scenarios） ✅ Level 2
- [x] 4.3 生成 design.md（四域对比+借鉴决策表 v2 15 项+实施路径+AD-01~06） ✅ Level 2
- [x] 4.4 生成 tasks.md（本文件） ✅ Level 2

## 5. 文档同步
- [x] 5.1 更新 docs/INDEX.md 活跃 Specs 表 ✅ Level 2
- [ ] 5.2 追加 NG 条目到 docs/project-rules/forks-reference.md（版本清单权威源） ⏳ 待用户裁决后与实施 spec 一并处理

## 6. 验证
- [x] 6.1 二次验证：文档关键章节齐全（四文档必含章节/五份迁移设计各 10 节/决策表 v2 修订落盘） ✅ Level 2
- [x] 6.3 检查点1 用户审查意见落实：①双向客观对比 ②设计前置重构（8 轮分析+证据包+总体设计+5 份实施级设计） ✅ Level 2
- [x] 6.2 用户审查裁决（检查点 1，共五轮：①通过②补双向对比③设计前置重构④函数级深化+环境故障恢复⑤B 类疑惑关闭 11 条+自评验收+裁决 P0 先行）✅ Level 2

## AOAdapt 日志

- [x] 五轮交叉验证（/goal 要求≥5 次，全程自主无询问）
  - V1 文档一致性：22 发现（行数声明 4/5 失准、P2 计数链算术矛盾等）→ 主文档+5 分期修复代理全闭环
  - V2 源码锚点回验：NG 侧 129/131 命中（99%）、本项目侧 ~96%（±1 漂移 11 处+失效引用 1 处）→ 5 修复代理勘误
  - V3 规范符合性：后端 4 实质（F1 全默认值/F2 @Synchronized 写路径/F3 CancellationException 吞噬/F4 Tag 计数滞后）+前端 4 轻微+规范提升点 15 条 → 6 修复代理收编 design.md 提升清单 14 条
  - V4 可实施性：数据层零阻断（F1 AiChatSession 撞名等 7 条）+实施链零阻断（F1-F12）→ 6 修复代理吸收
  - V5 终审：Tag 计数勘误（权威 26）+修复落盘复验全 ✅+/goal 八条审计总评 4.6/5
- [x] 3B 第三轮深化期间遭遇 IDE 写通道环境故障（重大）
  - Action: 4 个深化子代理并行执行，全部完成分析但 Write/Edit/RunCommand 全超时（仅 P2 在回复中带回全文）
  - Observation: 写通道分级故障——大负载 Write 假超时实际截断（P2 340 行仅落盘 56 行）、Edit 参数注入缺陷（old_string 被强制前置 ": "）、RunCommand 全超时；读通道（Read/Grep/Glob）始终正常
  - Adapt: ①立即停止盲试，AskUserQuestion 向用户报告并获"立即重试"授权 ②小负载探针定位（5 行/小字节 OK→大负载截断阈值存在）③重试 P2 全文成功落盘 396 行（通道恢复）④重派 P0/P1/P3 时注入"前轮结论种子+写失败全文回传兜底"指令，4/4 成功且行数达标 ⑤教训沉淀：并行子代理批量写文件时必须带"写后 Grep 自校验+失败全文回传"双兜底
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
