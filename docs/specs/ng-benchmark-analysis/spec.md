# spec.md — ng-benchmark-analysis

## Intent

定位最新开源阅读延伸版本 legado_NG（阅读NG），对其源码做深度对标分析，识别其相对本项目（阅读M，fork 自 legado-E）的优势，产出可执行的"值得迁移功能清单"及优先级排序，为后续分阶段借鉴实施提供决策依据。

## Scope

**做什么**：
- 确认 NG 最新仓库/版本/活跃度（仓库可达性预检，遵循 forks_comparison_methodology.md）
- 获取 NG 完整源码并按能力域分组深度分析（AI/听书/视觉/工程安全四域并行）
- 输出四域对比分析报告（含关键类/文件路径级证据）
- 产出借鉴决策表（用户价值/风险/工作量评分）+ ADR

**不做什么**：
- 不实施任何代码迁移（本 spec 仅调研，迁移实施按用户裁决另立 spec）
- 不分析 NG 的业务数据/书源内容（仅技术架构层）
- 不覆盖 forks-reference.md 已有的通用生态对比（本 spec 专注 NG 单一版本深钻）

## Approach

### Selected Approach

zipball 快照获取源码 + 4 子代理按能力域并行深读 + 主代理交叉汇总。理由：NG 与本项目同包名同架构（io.legado.app），逐文件 diff 收益低、噪音高；按"新增能力域"分组深读更适合识别"我们缺什么"。子代理隔离大体量源码阅读，保护主上下文。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| A. 逐文件 diff（forks_comparison_methodology Phase 3 标准流程） | NG 相对 Sigma 改动 224+ 提交且横跨新增 39 文件的 AI 目录、20 文件 TTS 引擎目录、自建 ui/design 包——diff 噪音远大于信号，仅适合同域小改动对比 |
| B. 仅基于 GitHub Release 日志/网络文章做桌面调研 | 违反方法论"以实测源码为准"铁律；文章口径粗，无法给出类/文件级迁移证据 |
| C. git clone --depth 1 浅克隆 | 已尝试，GitHub 网络停滞 20 分钟未完成（AOAdapt 已记录），zipball（codeload）2 分钟内完成，内容等价（无 git 历史，分析不需要） |
| D. 不调研，凭社区口碑直接排期迁移 | 闭门造车反模式；NG 功能闭环度高（如听书 AI 分镜五级路由），不读源码无法评估真实成本 |

### Drawbacks

- zipball 无 git 历史，无法追溯提交级演进动机（接受：release 日志已足够还原演进主线）
- 子代理分析为单轮抽样，未覆盖 NG 全部 545 个 ui 文件（接受：四域核心类已定位，迁移立项时再按需精读）
- 分析快照为 2026-08-28 版本，NG 迭代快（约日更），结论有时效性（接受：权威锚点已记录，可复跑）

### Prior Art

- `docs/specs/forks-ecosystem-analysis/`（17 fork 生态分析）
- `docs/specs/legados-forks-comparison/`（逐文件对比）
- `docs/project-rules/forks_comparison_methodology.md`（五阶段方法论，本 spec 的执行依据）

## Requirements

1. R1：明确 NG 仓库身份（owner/repo、版本、活跃度、与本项目的 fork 关系）
2. R2：AI 体系分析覆盖：供应商抽象/MCP 服务（内外双通道）/上下文压缩/技能包体系/AI 净化与扫书
3. R3：听书体系分析覆盖：角色路由算法/数据实体/引擎体系/Compose UI/与本项目实现差异
4. R4：视觉体系分析覆盖：液态玻璃实现原理/材质语义角色/视觉体系切换/主题 Resolver/Compose 迁移完成度
5. R5：工程安全分析覆盖：8 项书源沙箱修补逐项实现类/CI-CD 工作流/演进主线
6. R6：输出借鉴决策表（评分矩阵：用户价值/实现复杂度/风险/架构兼容性/维护成本）
7. R7：所有关键结论必须带 NG 源码文件路径级证据

## Scenarios

- **Scenario 1（主场景）**：用户阅读 design.md 借鉴决策表 → 裁决 Top 迁移项 → 主代理按裁决生成独立实施 spec（如 ai-provider-foundation / tts-multi-role / book-source-sandbox）
- **Scenario 2**：用户认为某域分析不够深 → 针对该域追加子代理精读，更新 design.md
- **Scenario 3**：NG 后续发布重大版本 → 以本 spec 为模板复跑调研，更新快照锚点
