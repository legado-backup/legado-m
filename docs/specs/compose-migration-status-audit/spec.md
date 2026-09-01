# spec.md — compose-migration-status-audit

## Intent

用户要求深度分析：除阅读器核心页面外，项目全部前端页面的 Compose 化到底进展到哪一步，以及是否可以继续增进。要解决的问题：

1. **进度不可见**：多份文档口径互相矛盾（pages-inventory 总览表 10.7% vs migration-registry 源码核验回填的更高进度），无法基于可信基线决策。
2. **继续性未知**：需要基于基建成熟度、风险清单、NG 对标差距给出"能否继续、怎么继续"的工程判断。

## Scope

**做**：

- 全页面（~97 Activity + ~23 页面级 Fragment + ~95 Dialog）Compose 形态盘点（全 Compose / 桥接 / 纯 XML / 永久原生）
- 文档口径冲突清单与权威源校准（design.md 页级 69 类总表为裁决）
- 继续性评估（基建成熟度 + 风险定稿对策 AD-08）
- **推进设计全量落盘**：B0-B5 批次计划，逐页任务+验收标准（tasks.md），不留"另立 spec/待校准"悬空项

**不做**：

- 不在本 spec 会话内一次性实施全部 19 项页面迁移（按 B0→B5 批次执行，每批设检查点，任务与验收标准已全部落盘于 tasks.md）
- 不迁移阅读器正文/漫画内核/WebView 画布（红线，AD-05）
- 不打断 ui-style-unify-deep-fix 待收口项（B0 优先）

**影响模块**：文档（docs/specs/、INDEX、pages-inventory、registry）+ 后续批次源码（19 项 🔨 对应页面，逐批实施）。

## Approach

### Selected Approach

三路并行子代理扫描 + 主代理交叉验证：

1. **文档记录路**：ui-redesign-m3 三件套 + migration-registry + ui-style-unify-deep-fix，提取权威进度记录
2. **源码实况路**：以代码为准统计 Fragment/Activity/Dialog 形态分布与 Compose 组件库存（457 处 @Composable / 120+ 文件）
3. **基建风险路**：LegadoTheme/Token/弹层/桥接设施成熟度 + gradle 依赖 + 重度自定义 View 难点 + NG 对标结论

理由：50+ 文件盘点任务，单代理串行会耗尽上下文预算；文档与源码双源交叉可暴露口径漂移（实测发现 5 处冲突）。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 仅读文档得出进度 | pages-inventory 总览表停留在 08-11（10.7%），与 migration-registry（08-25）矛盾，会得出严重低估的错误结论 |
| 仅源码 Grep 统计 | 缺历史脉络（何时迁的、为何暂停、回执缺失背景），无法解释"完成但未验收"状态 |
| 单代理全量顺序读 | 145KB tasks.md 等大文件会击穿上下文预算，且违反复杂任务流水线规范（单子代理≤12 文件） |
| 直接开工迁移新页面 | 违反 AD-24"样板先行"纪律，S2-S6 样板未冻结就铺枝叶会造成返工 |

### Drawbacks

- 子代理统计为静态分析粗估，桥接页面（代码创建 ComposeView 注入容器）与全 Compose 的边界判定存在少量歧义（如 BookshelfScreen 双栈共存）
- 未做运行时验证（编译/真机），因为本 spec 不改代码，静态盘点足够支撑路线决策；运行时验证留给后续迁移 spec 的步骤 5.5
- 口径冲突的最终裁决依赖 migration-registry 补登记，本轮只能标记不能消除

### Prior Art

- `docs/specs/ng-benchmark-analysis/design.md`：NG 对标 8 维全景，其中"Compose 化进度落后"已被列为劣势项，本轮为其提供精确刻度
- `docs/specs/ui-redesign-m3/ui-standards.md` §9 主干-支干-枝叶策略（AD-24）：本轮路线沿用其"样板→支干→枝叶"纪律

## Requirements

- R1：输出全页面四分层状态表（永久原生 / 全 Compose / 桥接过渡 / 纯 XML），以源码为准
- R2：输出文档口径冲突清单（≥5 处）并指定唯一权威源
- R3：输出继续性结论 + 风险清单及定稿对策（AD-01~08 全部 Accepted）
- R4：输出批次推进计划，**逐页任务+验收标准全量落盘，无阻塞点/待细化点**（B0-B5，tasks.md）
- R5：页级 69 类总表：每页含当前实况（源码+registry 双源）、目标形态、归属批次、任务类型、验收标准（design.md）
- R6：每批固定验证链（编译门禁+5.5 E2E+registry 回执+检查点）

## Scenarios

- **正常**：三路报告交叉一致（如 Dialog 层迁移率、基建可用性）→ 直接进入结论
- **边界（双栈页面）**：BookInfoActivity 双栈运行时分派、RssFragment classic/modern 双形态 → 按"以现代形态为准 + 显式标注双栈"归类，不简单二分
- **异常（文档与源码矛盾）**：以源码 + migration-registry（时间更新的源码核验记录）为准，矛盾项进 R2 清单，禁止以过期文档否定实况

## X2 互斥门禁：B4 待迁页 × subpage-topbar-unify（2026-09-01 核查）

总线 master-track-orchestration tasks 2.14 交叉核查结论：compose B4 待迁页 7 项（B5 AllBookmarkActivity / B14 ExploreShowActivity / B15 StorageManageActivity / D2 RssSourceEditActivity / D3 RssSourceDebugActivity / D5 RssSearchActivity+RssArticleInfoActivity / D7 RssFavoritesActivity+RssFavoritesFragment）与顶栏 spec（`docs/specs/subpage-topbar-unify`）批次 A/B/C 页名单 17 项求交集，**唯一命中 B14 ExploreShowActivity**（`activity_explore_show`，顶栏批次 C 4.2）。

易混淆排除（已核验源码宿主）：顶栏 4.6 `activity_source_debug` = BookSourceDebugActivity ≠ D3 RssSourceDebugActivity（布局为 `activity_rss_source_debug`）；顶栏 2.2 `activity_rss_source` = RSS 管理列表页 ≠ D2 RssSourceEditActivity；顶栏 2.3 `activity_cache_manage` ≠ B15 StorageManageActivity（`activity_storage_manage`）。D5/D7/B5 三页布局名均不在顶栏名单。

**门禁声明（B14 ExploreShowActivity）**：该页列入 compose 整页迁移名单（B4-c），禁止对其实施独立的 View 顶栏改动（避免双改冲突），顶栏改造随整页 Compose 迁移一并落地。实况注记：顶栏批次 C 4.2 的 MainTopBarView(Mode.SUB) 替换已先期完成（编译通过，真机回归待设备），故本门禁落地口径为——B4-c 实施时以 MainTopBarView 现状为输入，整页迁移时顶栏一次性收敛为 Compose 头部（S2 样板/D4 组件自带头部），禁止迁后回退 View 顶栏或形成未登记的双栈并存；顶栏 4.2 真机回归结论应作为 B14 迁移输入基线。
