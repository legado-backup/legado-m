# spec — quality-check-unify

## Intent
让源质量体检具备"校验所选"的结果落库能力（失效分组/weight/注释回填），实现检测能力单源化收编；体检为主入口，校验所选保留过渡期。

## Scope
**做**：
1. `QualityReportApplier`（model 包）：report → 旧分组/weight/注释映射回填（书源+订阅源）
2. 体检结果页底栏"应用结果"动作（确认框 + 执行反馈）
3. 单元测试（映射正确性：分组名与 CheckSourceService 逐字一致）

**不做**：
- 不删 CheckSourceService/CheckRssSourceService（下一版本清理）
- 不回填 lastHost/respondTime（report 无 realHost/耗时字段，Drawbacks 登记）
- 不动管理页菜单入口

## Approach（三要素）

### Selected Approach
桥接层纯映射（零网络）：`SourceQualityReport.dimensions` → `BookCheckResult`/`RssCheckResult` → 复用 `SourceWeightCalculator.calculate*FromResult` 计算 weight → 按维度状态 add/remove 旧分组名（与 CheckSourceService 逐字一致）→ `bookSourceDao.update`。理由：分组名/weight 判定核心不重写，复用既有权威源（AD-08 延续），映射层薄且可单测。

### Alternatives Considered
| 备选 | 否决理由 |
|------|---------|
| 体检直接写分组（在 Scorer/Session 内落库） | 破坏体检零写库契约（AD-01），导入校验复用会被污染 |
| 管理页批量"校验所选"改调体检会话+桥接 | 入口行为突变（通知栏进度消失），风险大且本期目标只是能力补齐 |

### Drawbacks
- report 无 realHost/respondTime：桥接不回填 lastHost/respondTime（旧服务有）→ 接受：weight 判定不依赖二者；后续 report 加字段再补
- RUNNING 中"应用结果"：仅对已完成 results 可用（按钮在 running 时禁用）
- 订阅源旧分组名体系与书源不同（CheckRssSourceService）→ 按各自服务逐字映射
- 通知栏进度能力缺失（体检无前台服务）→ 接受：万条体检有暂停续跑+里程碑日志

## Requirements
- R1 桥接映射：report 四态/维度 → 旧分组名与 CheckSourceService/CheckRssSourceService 逐字一致；USABLE 源 removeInvalidGroups 后不加失效组
- R2 weight 回填：映射 BookCheckResult/RssCheckResult 后走 SourceWeightCalculator.calculate*FromResult（domainCheckEnabled 取 options.checkDomain）
- R3 注释回填：CheckSource.wSourceComment 开启时失败源写错误注释
- R4 结果页"应用结果"：底栏新增动作；RUNNING 中禁用；确认框明示影响数量；完成后 toast"已应用 N 条"
- R5 空集防呆：无选中/筛选结果时动作不可用

## Scenarios
- WHEN 用户在体检结果页筛选"失效"并全选，点"应用结果" THEN 选中源按维度写入旧失效分组+weight 回填落库，管理页按分组筛选立即可见
- WHEN 选中含 USABLE 源 THEN 该源清除历史失效分组并回填正向 weight
- WHEN 体检 RUNNING 中 THEN "应用结果"按钮禁用
- WHEN 断网体检产生的"存疑放行"（suspect）源被应用 THEN 不写失效分组（宽松档不误伤）
