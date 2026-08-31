# design.md — compose-migration-status-audit（设计先行定稿版·交叉审核轮 1-2 修订后）

> 本文档为"完全支撑实施"级设计：页级 69 类全量落盘 + 4 份实施级设计分册（合计 2905 行）。状态：🔄 设计中（交叉审核 2/5 轮完成+修订闭环）。
> **实施优先级口径**：页级总表与本册分册冲突处，**以分册勘误为准**（分册基于逐文件源码核验，本表为批次规划口径）。

## 分册索引（实施级设计，每册含 kotlin 骨架/边界枚举/6 维门禁/用例级测试/依赖图）

| 分册 | 覆盖 | 行数 |
|---|---|---|
| [design-b1-b2-baseline-freeze.md](./design-b1-b2-baseline-freeze.md) | B1 校准四产物成品（新总览表 55% 行口径/§G 校正 X-01~22/registry 登记块 aq~bn/冻结标注）+ B2 样板 35 检查点 + AppPageSpacing token + L2 脚本模板 | 463 |
| [design-b3-d4-flagship.md](./design-b3-d4-flagship.md) | D4 旗舰：五代 Adapter 差异对照+收敛策略、RssArticleListScreen（含可选 onItemLongClick）/state holder/ArticleItem 三形态骨架、双模式分派、embeddedInModernRss 兼容层、10 项边界、12 场景测试 | 767 |
| [design-b3-pages.md](./design-b3-pages.md) | B3 其余 9 页 mini-design（§1 A7/§2 A8/§3 B2/§4 B8/§5 B11/§6 C3/§7 C13/§8 D1/§9 E2）+ 复用矩阵 + 9 个 L2 脚本 | 971 |
| [design-b4-b5-pages.md](./design-b4-b5-pages.md) | B4 十三节（§B4-1~13，含源码实况勘误表）+ B5 收官可执行清单（§B5-1~4） | 704 |

## Architecture Decisions（全部定稿 Accepted）

### AD-01: 进度权威源收敛
- **Context**: ui-redesign-m3 三件套（08-16 冻结）与 migration-registry（08-25 源码核验）及源码实况三方口径漂移，pages-inventory 总览 10.7% 与 §G 技术标注双双过期
- **Concern**: 后续迁移基于过期基线导致重复迁移/漏迁
- **Decision**: 进度以 migration-registry 为唯一权威；pages-inventory §0 总览与 §G 技术标注按 design-b1-b2 分册成品表一次性校准（B1 批次）；ui-redesign-m3 三件套冻结为历史参考
- **Goal**: 单一可信基线
- **Tradeoff**: pages-inventory 明细与总览存在过渡期不一致，以总表+分册为裁决
- **Status**: Accepted

### AD-02: 继续性判定与总路线
- **Context**: 基建全可用（LegadoTheme/ThemeSync/AppShapes/AppUiTokens/ComposeDialogFragment 族/桥接设施）；deep-fix 缺 R3 终测；样板 S1-S6 大多已接线缺验收回执
- **Concern**: 直接铺量 vs 先收口纪律
- **Decision**: **可以继续增进**。路线：B0 deep-fix 收口 → B1 基线校准 → B2 样板冻结验收 → B3 P2 残余页 → B4 P3 长尾 → B5 收官巡检
- **Goal**: 每批有回执，零悬空推进
- **Tradeoff**: B0/B1/B2 为非页面产出批次，短期迁移数字不动
- **Status**: Accepted

### AD-03: D4 Rss 文章列表族从 P3 提级为 B3 旗舰
- **Context**: §G 未将 D4 点名入 P2，但源码实况确认 RssArticlesFragment 纯 XML 且 Adapter 5 代并存（轮 2 审核实证：6 文件包内互相引用、包外 0 引用），是最大技术债；RssFragment 08-29/08-30 刚完成 classic/modern 切换修复
- **Concern**: 改动影响面大（多页共用 Adapter 族+embeddedInModernRss 嵌入复用）
- **Decision**: D4 提级至 B3 首位；五代收敛为单一 Compose 列表组件（design-b3-d4-flagship.md），classic/modern 共享；紧跟订阅切换专项回归
- **Goal**: 消除最大债，双模式列表统一
- **Tradeoff**: 与刚完成的切换修复存在回归耦合，必须排在 B0 R3（4.1 订阅切换专项）通过之后
- **Status**: Accepted

### AD-04: 双组件体系治理
- **Context**: miuix 0.8.8（Archive 对齐）与 M3 六族并存，另有 AiComposeTheme 独立主题
- **Decision**: 新迁移页面一律 M3 六族+LegadoTheme；miuix 限既有用途不扩散；AiComposeTheme 在 B5 按五维评分框架（design-b4-b5 分册 §B5-4）评估，≥7 分启动收敛 spec
- **Goal**: 单一组件来源（对齐 deep-fix FR-9）
- **Tradeoff**: 接受局部双轨存量
- **Status**: Accepted

### AD-05: 阅读器边界（红线重申）
- **Context**: 正文（ReadView/PageDelegate×7）、漫画内核、WebView 播放内核为命令式深度定制
- **Decision**: 维持壳-核分离：内核永久原生；浮层/壳层 Compose 化继续（S5 已接线，B2 补回执）；B12/B13 仅壳层/主题对齐
- **Tradeoff**: 与 NG 的占比差距永久存在
- **Status**: Accepted

### AD-06: 样板冻结 = 验收回执而非重写
- **Context**: §10.2 实况：S1 底栏✅接线、S2 管理列表✅v2 已接线、S3 表单编辑器✅v2 待接线、S4 详情✅已接线、S5 全屏沉浸✅Phase4 已接线、S6 弹窗族✅v2（P8 浮层族）
- **Concern**: "样板先行"是否意味着重做样板
- **Decision**: S1/S2/S4/S5/S6 冻结=补真机功能点覆盖（35 检查点见 design-b1-b2 分册 §2，S5-7 书签/高亮入口已增补）+§7 检查清单+§3.3 回执；S3 额外完成接线后同流程冻结
- **Goal**: 样板可被 P2/P3 直接照抄
- **Tradeoff**: 验收占用一轮真机批次
- **Status**: Accepted

### AD-07: 批次划分与依赖
- **Context**: deep-fix R3 未过则 B3（含 D4 提级）有回归耦合风险；基线未校准则页级任务无法验收
- **Decision**: B0→B1→B2→B3→B4→B5 严格串行；B3 内部按"低耦合先行"排序（D4 排 B0 之后首位）；B4 依赖 B3 产出的同型样板复用（分册内再分 B4-a 登记/B4-b 收口/B4-c 迁移三波）；B5 收官含销号/巡检/KPI 复盘/AiComposeTheme 评估
- **Goal**: 依赖显式化，禁止跳批
- **Tradeoff**: 串行牺牲并行度换取回执链完整
- **Status**: Accepted

### AD-08: 风险加固定稿
- **Context**: 强跳过陷阱已沉淀（frontend-ui-standards §4 红线5+§5 清单第8项，2026-08-30）；测试盲区（ai_tests 无 Compose 专项脚本）；AppUiTokens 仅列表场景；glide-compose beta08
- **Decision**: ①强跳过：转为每批改造门禁执行项（检查清单第8项，入 S2 验收）②测试：l2_verify_compose_{page}.py 模板+断言函数库（design-b1-b2 分册 §4，B2 首批 7 脚本+B3 9+B4 17 场景）③Token：AppPageSpacing 7 token 4dp grid（design-b1-b2 分册 §3，与 AppListSpacing 边界=页面级 vs 列表级）④glide-compose：观察项，图片异常优先排查
- **Tradeoff**: 测试基建投入为前置成本
- **Status**: Accepted

## 页级迁移总表（69 类，批次规划口径；实施细节以分册为准）

图例：🔁=已迁移待登记/回执 ｜ 🔨=待迁移/收尾 ｜ ✅回=待补验收回执 ｜ 🧱=红线/N 不迁移 ｜ 🗑=清理销号
（标 ◆ 行 = 分册源码核验已修正口径）

### A 主框架/我的（8）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| A1 MainActivity | PillNav 桥接已落地（S1 接线） | S1 冻结 | B2 | ✅回 | 分册 §2 S1 检查点全过+回执 |
| A2 MyFragment | XML 壳+ProfileScreen3Level（Phase2 真机过 08-10） | 维持 | B2 | ✅回 | 同上 |
| A3/A4 书架 style1/2 | BookshelfScreen 共用（Phase3 真机过 08-11）；Fragment 内 RecyclerView 引用归 12 菜单 View 红线 | 维持 | B2 | ✅回 | 功能点覆盖+菜单红线登记说明 |
| A5 BaseBookshelfFragment | View 基类（12 菜单+configBookshelf 红线） | 红线保留 | — | 🧱 | — |
| A6 BooksFragment ◆ | 全仓 0 引用且源文件已不存在（轮 2 审核实证） | 销号 | B5 | 🗑 | 分册 §B5-1 销号清单 |
| A7 ExploreFragment ◆ | modern 瀑布已实现（ExploreModernListScreen StaggeredGrid）；残余=classic rvFind 源行列表（7.11aj） | classic 列表收敛 | B3 | 🔨 | 分册 design-b3-pages §1 |
| A8 RssFragment | classic/modern 双形态；modern 列表桥接；classic 活跃维护区 | modern 全 Compose+classic 收敛 | B3（D4 后） | 🔨 | 分册 §2+订阅切换回归 0 残留 |

### B 阅读器/书籍（16）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| B1 ReadBookActivity | 正文原生红线；浮层 MenuLayer 等已 Compose（S5 已接线 Phase4） | S5 冻结 | B2 | ✅回 | 分册 §2 S5 检查点+手势 R0-R4 真机 |
| B2 TocActivity+ChapterList ◆ | activity_chapter_list.xml 已单 ComposeView（轮 2 实证），接线就位；收尾=rememberSaveable 补齐 | 接线收尾 | B3 | 🔨 | 分册 §3+万章长列表性能抽查 |
| B3/B4 书签/高亮 Tab | 属阅读器浮层族（S5 范围），非独立页面 | 随 S5 冻结验收覆盖 | B2 | ✅回 | S5 检查点含书签/高亮入口 |
| B5 AllBookmarkActivity | View | Compose 列表 | B4-c | 🔨 | 分册 §B4-4 三连模板 |
| B6 BookInfoActivity | 双栈运行时分派（新栈 39 composable；X4 裁决禁止回退） | 双栈维持 | B2 | ✅回 | 双栈分支各过+登记 |
| B7 BookInfoEditActivity ◆ | 壳接线已完成（composeHost.setContent{LegadoTheme{BookInfoEditScreen}}，轮 2 实证 :54-56） | 登记核对+验收 | B4-a | 🔁 | 分册 §B4-1 |
| B8 BookshelfManageActivity | View | 复用 S2 管理页样板整页化 | B3 | 🔨 | 分册 §4（主题包裹层级按 §B4-4 边界 5 统一裁决） |
| B9 导入族 ◆ | ImportBookActivity 已桥接（ImportBookScreen+View SelectActionBar 底栏混合，轮 2 实证 :106-108） | 底栏收尾裁决 | B4-b | 🔨（收尾） | 分册 §B4-2 |
| B10 CacheActivity | CacheScreen 纯 Compose（Adapter 已删）；缺真机回归 | 真机回归 | B0 | 🔁 | 真机回归报告（registry 7.11ai 销项） |
| B11 Search/SearchContent | 结果列表已 Compose（7.11ah）；残余=searchView/btnMenu/源分组标签条 | 残余收敛 | B3 | 🔨 | 分册 §5（复用 PrimaryTagRow） |
| B12 ReadMangaActivity | 渲染内核红线 | 壳层/浮层对齐 S5 模式 | B4-c | 🔨（壳） | 分册 §B4-13；内核零改动断言+壳层真机 |
| B13 AudioPlayActivity | View+LyricViewX 第三方；NG #14 裁定面板形态暂缓重设计 | 仅主题/顶栏 M3 对齐，不重写 | B4-a | 🔨（对齐） | 分册 §B4-13；取色走 ThemeSpec 断言 |
| B14 ExploreShowActivity | View | Compose 列表 | B4-c | 🔨 | 分册 §B4-4 三连模板 |
| B15 StorageManageActivity | View | Compose | B4-c | 🔨 | 分册 §B4-4 三连模板 |
| B16 TxtTocRuleActivity ◆ | composeItems/composeSelectionCount 桥接态已存在+Edit ComposeDialog Callback 已实现 | 核对销号 | B4-a | 🔁 | 分册 §B4-3 |

### C 书源/规则/工具（20）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| C1 BookSourceActivity | S2 样板页已接线（BookSourceScreen 1006 行双轨） | S2 冻结 | B2 | ✅回 | 分册 §2 S2 检查点（含 copy() 强跳过验收） |
| C2 BookSourceEditActivity | S3 样板 v2 待接线（5 处 Compose 接线=轮 2 实证 :31/:32/:301/:678/:788 均 dialog 级，View 内核保留） | 接线+S3 冻结 | B2 | 🔨+✅回 | 未保存拦截/CodeView 真机 |
| C3 BookSourceDebugActivity | 纯 View（VMBaseActivity） | BookSourceDebugScreen 整页迁移 | B3 | 🔨 | 分册 §6（ERROR 短路/前缀补全逐条保留） |
| C4 ReplaceRule+ReplaceEdit | 列表已 AppManagementScaffold 全 Compose（7.11ag）；Edit 已 Compose 桥接 | 核对登记 | B1 | 🔁 | registry 登记块（分册 §1.3） |
| C5 HighlightRuleActivity | 全 Compose；强跳过修复已完成（fix spec ✅） | 登记 | B1 | 🔁 | registry 登记块 |
| C6 DictRuleActivity | 源码全 Compose；inventory 标 View 滞后 | 登记 | B1 | 🔁 | registry 登记块 |
| C7 CodeEditActivity | sora 内核 N | 壳保留 | — | 🧱 | — |
| C8 WebViewActivity | WebView 池 N | 保留 | — | 🧱 | — |
| C9 FileManageActivity | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| C10 DownloadManageActivity | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| C11 UrlRecordActivity | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| C12 RecycleBinActivity | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| C13 SourceLoginActivity | 壳内 SourceLoginDialog 已全 Compose（分册实证）；壳瘦身收尾 | 壳瘦身+核对 | B3 | 🔨（收尾） | 分册 §7（S6 L1/L2/L3 核对） |
| C14/F5 QrCode | camera-scan N | 保留 | — | 🧱 | — |
| C15 ImageGallery/ImageDetail | 源码全 Compose；inventory 滞后 | 登记 | B1 | 🔁 | registry 登记块 |
| C16 AutoTask+Edit | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| C17 WelcomeActivity ◆ | 已桥接（WelcomeScreen+composeHost，4 项 mutableStateOf，轮 2 实证 :45-68） | 登记核对 | B4-a | 🔁 | 分册 §B4-10 |
| C18 association 透明窗系 | 协议分发 N | 保留 | — | 🧱 | — |
| C19 debug 7 工具 ◆ | 纯 Compose；硬编码色仅剩 1 处且已带豁免登记（RegexTestScreen.kt:210，轮 2 实证） | 巡检确认豁免 | B5 | 🔁 | 分册 §B5-2 |
| C20 AboutActivity+AboutFragment | About View（唯一全新迁移）；ReadRecord 源码全 Compose | About 迁移（AnnotatedString 替代 Spannable）+ReadRecord 登记 | B4-c | 🔨+🔁 | 分册 §B4-11 |

### D RSS/订阅（9 组）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| D1 RssSourceActivity ◆ | 源码已全量 AppManagementScaffold 接线（轮 2 实证 :117-118；旧 RecyclerView removeView 桥接为死代码） | 收尾清理（死代码+menu 逐项核对） | B3 | 🔁 | 分册 §8 |
| D2 RssSourceEditActivity | View | 复用 S3 表单样板（B4 最重结构迁移） | B4-b | 🔨 | 分册 §B4-5 |
| D3 RssSourceDebugActivity | View | 复用 C3 调试样板（日志列表） | B4-b | 🔨 | 分册 §B4-6 |
| D4 RssArticlesFragment+RssSortActivity | 纯 XML；Adapter 5 代并存；顶栏已 Compose（12.40）；embeddedInModernRss 定义于 RssArticlesFragment.kt:84 | **B3 旗舰**（专册） | B3（首位，B0 之后） | 🔨 | design-b3-d4-flagship 全章+12 场景 L2 |
| D5 RssSearch+RssArticleInfo | View | 结果列表复用 D4 组件 | B4-b | 🔨 | 分册 §B4-7（换源长按经 onItemLongClick 注入） |
| D6 ReadRssActivity | WebView 载体 N | 保留 | — | 🧱 | — |
| D7 RssFavoritesActivity+Fragment | View；ViewPager 收敛 HorizontalPager | 复用 D4 列表组件 | B4-b | 🔨 | 分册 §B4-8 |
| D8 RuleSubActivity | Compose 桥接已有（RuleSubScreen） | 收尾核对 | B4-a | 🔁 | 分册 §B4-9 |
| D9 VideoPlayer+VideoFragment | 顶栏+设置面板 Compose；播放内核红线 | 残余浮层核对+S5 模式回执 | B2 | ✅回 | 手势四件套真机（R3 4.2 复用） |

### E 配置子页（6）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| E1/E3/E6 Backup/Cover/WelcomeConfig | ComposeSettingFragment（7.11ak/al） | 登记 | B1 | 🔁 | registry 登记块 |
| E2 ThemeConfigFragment | 已 ComposeSettingFragment；遗留 15 项 UI 违例（V2/V3 自动销号候选重判）+V13 内置 4 套主题待裁决 | 违例修复+ThemeSpecPresets 落点 | B3 | 🔨（UI 修复非迁移） | 分册 §9 |
| E4 OtherConfig | ComposeSettingFragment（7.11al） | 登记 | B1 | 🔁 | registry 登记块 |
| E5 PreciseManageFragment ◆ | 已完成（ComposeView+PreciseManageScreen+LegadoTheme，轮 2 实证 :50-53） | 登记核对 | B4-a | 🔁 | 分册 §B4-12 |

### F 其它（6）
| 页面 | 当前实况 | 目标 | 批次 | 任务 | 验收 |
|---|---|---|---|---|---|
| F1/F2 About | =C20 | 同 C20 | B4-c | 🔨 | 同 C20 |
| F3 ReadRecord | 源码全 Compose | 登记 | B1 | 🔁 | registry 登记块 |
| F4 WebViewLoginFragment | WebView N | 保留 | — | 🧱 | — |
| F6 VideoFragment | =D9 族 | 同 D9 | B2 | ✅回 | 同 D9 |

**统计定稿（轮 1-4 修订后，行口径自洽闭合）**：总表字面 59 行（69 类，共享行 A3/A4、C14/F5、F6/D9、F1/F2、E1/E3/E6）；**分母 60 = 59 + B3/B4 书签/高亮 Tab 拆 2 类计 1 行的还原拆分**（该行为 ✅回 覆盖说明行，不计入任务项）。
- 结构口径：**已 Compose 33/60 行（55%）**（含 B2/B9/B11/B16 已接线留收尾）
- 任务口径：🔁+✅回 **30 项**（24 登记块 + D1/C19/B13 追加，B7/B16/C17/E5/D8 复核归并）｜ 🔨 **20 行**（结构性迁移 14：D4/A7/A8/B8/C3/C13 瘦身/B5/B14/B15/D2/D3/D5/D7/C20；轻量收尾 6：B2/B11/E2/B9/B12/B13）｜ 🧱 9 组 ｜ 🗑 1 项
- 口径注：①双主题包裹统一按分册 §B4-4 边界 5 裁决（实施时登记最终包裹层级，禁两页口径不一）②骨架排版值一律 AppPageSpacing token（轮 3 修订已落盘）③L2 场景名统一前缀 l2_verify_compose_*

## Data Flow（批次执行流，每批固定验证链）

```
B0 deep-fix R3 终测通过（回归安全基线，含 2.11 Cache 回归）
→ B1 校准四产物落盘（分册 §1 成品直接粘贴：新总览/§G 校正/registry 登记块/冻结标注）
→ B2 token 先行 → S3 接线 → S1/S2/S4/S5/S6 验收回执 + 首批 7 个 L2 脚本
→ B3 D4 旗舰（专册）→ A7 → A8 → B2 → B8 → B11 → C3 → C13 → D1 → E2
→ B4-a 登记 6 项 → B4-b 收口 5 项（B9 裁决→D3→D5→D7→D2 压轴）→ B4-c 列表三连+About 全新
→ B5 销号/巡检/AiComposeTheme 评分/KPI 终值
每批：编译门禁 assembleAppDebug → 5.5 E2E → registry 回执 → daemon 清场 → 检查点
```

## File Changes

| 文件 | 变更 | 批次 |
|---|---|---|
| docs/specs/compose-migration-status-audit/（4 主文档+4 分册） | 本 spec（分册逐文件源码核验后产出） | 已完成 |
| docs/INDEX.md | 活跃 Specs 登记 | 已完成 |
| docs/specs/ui-redesign-m3/pages-inventory.md | §0 成品表替换（55% 行口径）+§G 校正 X-01~22（分册 §1.1/1.2） | B1 |
| docs/project-flow/ui-standards/migration-registry.md | §七 登记块 aq~bn 24 项（分册 §1.3） | B1/B2 |
| ui-redesign-m3/tasks.md | 头部冻结标注（分册 §1.4 成品段落） | B1 |
| app 源码（🔨 20 行对应页面，文件级清单见各分册册尾变更总表） | 逐页迁移 | B3/B4 |
| ai_tests/scripts/ | l2_verify_compose_{page}.py 系列（B2 首批 7+B3 9+B4 17 场景） | B2 起每批 |
