# tasks.md — compose-migration-status-audit

> 对应 design.md 页级总表（已回写分册勘误+交叉审核轮 1-4 修订）与 AD-07 批次依赖。实施细节以 4 份分册为准（design-b1-b2 / design-b3-d4-flagship / design-b3-pages / design-b4-b5-pages）。每批完成后跑编译门禁+5.5 E2E+registry 回执，批间设检查点。状态：🔄 设计中（交叉审核 4/5 轮完成+修订闭环，待轮 5 终审）。

## 1. 进度审计与设计编制（本 spec 本体）

- [x] 1.1 三路并行扫描（文档/源码/基建）✅ 2026-08-30
- [x] 1.2 路线图/registry/红线原文抽取（S1-S6 样板定义、P2 15 组 22 页、P3 全集、N 清单）✅ 2026-08-30
- [x] 1.3 页级 69 类校准总表编制（design.md）✅ 2026-08-30
- [x] 1.4 批次计划 B0-B5 与 AD-01~08 定稿 ✅ 2026-08-30
- [x] 1.5 四份实施级设计分册产出（463/767/971/704 行，分册源码勘误 10 处回写总表）✅ 2026-08-30
- [x] 1.6 交叉审核轮 1（册间一致性 7E/6W）+轮 2（源码符合性 10 确认/2 部分）+修订闭环 ✅ 2026-08-30
- [x] 1.7 交叉审核轮 3（规范符合性 5E/12W/6I）+轮 4（完整性 1E/4W，四方映射 58/59→59/59 闭合）+修订闭环（28 条落盘+2 条合规跳过+主文档 4 处）✅ 2026-08-30

## 2. B0 deep-fix 收口（依赖前置，继承 ui-style-unify-deep-fix tasks §4/§5）

- [ ] 2.1 R3-4.1 订阅切换专项：经典↔新版反复切换无残留+即时生效（真机）
- [ ] 2.2 R3-4.2 视频手势回归：上下滑切视频/左右滑 seek/长按倍速/双击暂停四件套不破坏
- [ ] 2.3 R3-4.3 G1-G11 成果回归（字号/圆角/主题联动/调试 7 页/书源编辑调试头）
- [ ] 2.4 R3-4.4 logcat 针对性计数=0+android.util.Log.d/e 残留=0
- [ ] 2.5 R3-4.5 门禁：4.1-4.4 全过+随批散项（X1 安装 L1 冒烟/X2 设置搜索走查/X3 间接宿主确认）
- [ ] 2.6 收尾 5.1 updateLog 基于 git diff 逐文件审计更新
- [ ] 2.7 收尾 5.2 registry 登记 H/D 迁移+INDEX 更新
- [ ] 2.8 收尾 5.3 stop-daemons.bat 清场
- [ ] 2.9 收尾 5.4 项目记忆+经验沉淀
- [ ] 2.10 收尾 5.5 🛑 检查点 3 用户验收
- [ ] 2.11 B10 CacheActivity 真机回归（registry 7.11ai 销项）

## 3. B1 基线校准（纯文档，成品直接粘贴自 design-b1-b2 分册 §1）

> ⚠️ **冻结标注（2026-09-01，总线 2.7.2）**：B1 基线校准已执行——pages-inventory §0/§G 校准（变更记录 v2.13）、registry §七 7.11aq~bn 24 项登记块、ui-redesign-m3/tasks.md 头部冻结标注均已落盘。基线校准后上述编号（X-01~X-22、7.11aq~bn）与校准范围**不再变更**；后续迁移状态变化一律走 migration-registry **增量登记**（7.11 系列顺延）+ pages-inventory §0 快照随回执刷新，禁止改写本批校准条目。

- [x] 3.1 pages-inventory.md §0 替换为分册 §1.1 成品总览表（55% 行口径+双口径注释）✅ 2026-09-01（总线 2.7.1；§0 整段替换+统计定稿/双口径/权威源 3 注落盘）
- [x] 3.2 pages-inventory.md §G 按分册 §1.2 校正表 X-01~X-22 逐条执行（含 6 项"维持免改"核验）✅ 2026-09-01（总线 2.7.1；X-01~X-18 条目技术标注 18 处+X-19/X-20 §G 清单归属 2 处+X-21 权威源增注+X-22 v2.13 变更记录；6 项维持免改核验通过：C1/C2/B7/D1/D4/B6 现行标注与分册一致零改动）
- [x] 3.3 ui-redesign-m3/tasks.md 头部冻结标注（分册 §1.4 成品段落）✅ 2026-09-01（总线 2.7.2；成品 4 条已插入头部标题与 §1 之间）
- [x] 3.4 migration-registry.md §七 登记块 aq~bn 24 项按分册 §1.3 粘贴（每项含证据三元组）✅ 2026-09-01（总线 2.7.2；B1 登记 16 项 aq~bf+B2 冻结回执 8 项 bg~bn 整块追加于 §六.4 之后；编号顺延核验：registry 原止于 7.11ap，aq~bn 无冲突）
- [ ] 3.5 六.3 遗留销项：BookshelfItems GeneratedCover 归位裁决（分册 §1.5 裁决成品段：方案 A 迁 ThemeSpec 取色/B 登记豁免，建议 A，随 B2 S2 验收批次实施）（注：分册 §1.3 成品登记块无该行，裁决登记随 B2 S2 批次按 §1.5 建议 A 落 registry）
- [x] 3.6 顶栏集群 4 spec 盘点吸收/注销（总线 2.7.3 增补账本项）✅ 2026-09-01——逐 spec 结论：①**my-topbar-unify**＝实施进行中（核心实现 2.1-2.5 已勾：MainTopBarView Mode.MY+MyFragment 接线；验证 §3/文档同步 §4 未勾），**保留**；②**subpage-topbar-unify**＝实施基本完成（批次 A/B/C 迁移+三批编译全过+5.1 全量回扫过；剩真机回归 2.6/3.6/4.8/5.4.2~4+TitleBar 废弃评估 5.3.1），**保留**；③**tag-mode-unify**＝实施基本完成（§1/§2/2.9 全勾+3.1 编译过；剩真机验证 3.2~3.4+清理 3.6），**保留**，实施时点排总线 3.5 后（热点④，按总线 tasks 2.7.3 原文）；④**topbar-icon-semantics-fix**＝实施基本完成（1~4 章+5.1/5.3 全勾；仅剩 5.2 真机 L2/L3 走查，1.2 排查与之合并执行），**保留**。总判定：四 spec 代码域均基本完成、均余真机验证尾巴，**无一达"吸收完毕待归档"销档线，全部保留不注销**；吸收路径＝四 spec 剩余真机验证项并入 compose B2 样板冻结检查点的真机窗口合并执行（S1 主框架检查点覆盖 my-topbar/tag-mode 顶栏形态，图标走查覆盖 topbar-icon 审计面），避免重复打包；互斥门禁维持＝B14 ExploreShow 列 compose B4-c 整页迁移名单，届时顶栏一次性收敛为 Compose、禁再独立改动 View 顶栏（subpage-topbar-unify 4.2 ↔ compose spec.md §X2）。

## 4. B2 样板冻结验收（AD-06；检查点全表=design-b1-b2 分册 §2，35 项含 S5-7）

- [ ] 4.1 AppPageSpacing token 落地（分册 §3 骨架，含与 AppListSpacing 边界注）+frontend-ui-standards 写入
- [ ] 4.2 L2 脚本模板落地（分册 §4，logcat 采集带 -T 时间戳起点）+首批 7 脚本
- [ ] 4.3 C2 BookSourceEditActivity S3 接线收尾（未保存拦截/CodeView/KeyboardToolPop 真机）
- [ ] 4.4 S1 MainActivity 冻结验收+回执
- [ ] 4.5 S2 BookSourceActivity 冻结验收（含 copy() 强跳过验收项）+回执
- [ ] 4.6 S3 BookSourceEditActivity 冻结验收+回执
- [ ] 4.7 S4 BookInfo 双栈分支各过+回执
- [ ] 4.8 S5 阅读器浮层冻结验收（3s 隐藏/单一 activeSheet/BackHandler 链/手势 R0-R4/磨砂降级/S5-7 书签高亮入口）+回执
- [ ] 4.9 S6 弹窗族冻结验收（L1/L2/L3 三层）+回执
- [ ] 4.10 D9/VideoFragment 残余浮层核对+S5 模式回执（手势四件套复用 2.2 证据）

## 5. B3 批次（D4 旗舰专册+其余 9 页分册；设计已函数级落盘+轮 3 骨架修订）

- [ ] 5.1 D4 旗舰：按 design-b3-d4-flagship.md 实施（五代 Adapter 收敛/RssArticleListScreen 含可选 onItemLongClick/topOverlaySpacePx 状态化/ScrollRestoreEffect snapshotFlow 化/双模式分派/embeddedInModernRss 兼容层）→ 12 场景 L2+订阅切换回归+删 4 代旧 Adapter
- [ ] 5.2 A7 classic rvFind 源行列表收敛（design-b3-pages §1，7.11aj 销项）
- [ ] 5.3 A8 RssFragment modern 全 Compose+classic 收敛（§2，复用 5.1 组件+PrimaryTagRow 泛型版，订阅切换回归）
- [ ] 5.4 B2 Toc 收尾：rememberSaveable 补齐+万章性能抽查（§3）
- [ ] 5.5 B8 BookshelfManage 整页 AppManagementScaffold 化（§4；主题包裹层级按 b4-b5 §B4-4 边界 5 统一裁决）
- [ ] 5.6 B11 残余三块收敛：searchView/btnMenu/源分组标签条（§5）
- [ ] 5.7 C3 BookSourceDebug 整页迁移（§6，ERROR 短路/前缀补全逐条保留）
- [ ] 5.8 C13 壳瘦身+S6 三层核对（§7）
- [ ] 5.9 D1 收尾清理：已全量接线，死代码删除+menu 逐项核对（§8）🔁
- [ ] 5.10 E2 违例修复：15 项逐项重判（V2/V3 销号候选）+V13 ThemeSpecPresets 落点（色值豁免声明已落册）+用户裁决程序（§9）

## 6. B4 批次（三波次；分册 design-b4-b5-pages）

- [ ] 6.1 B4-a 登记核对 6 项：B7（§B4-1）/B16（§B4-3）/C17（§B4-10）/E5（§B4-12）/D8（§B4-9）/B13 主题对齐（§B4-13）🔁
- [ ] 6.2 B4-b 收口 5 项：B9 底栏裁决（§B4-2）→D3（§B4-6）→D5（§B4-7）→D7（§B4-8，经 ReadRss.readRss 上行链）→D2 压轴（§B4-5，宿主统一包裹 LegadoTheme）
- [ ] 6.3 B4-c 迁移 4 项：B5/B14/B15 列表三连（§B4-4 共用模板；⚠️ B14 ExploreShow 列入顶栏 spec X2 互斥门禁，顶栏随整页迁移一次性收敛为 Compose，禁独立改动 View 顶栏，见 spec.md §X2）+C20 About 全新迁移（§B4-11，AnnotatedString）
- [ ] 6.4 B4 特殊：B12 漫画壳层对齐 S5（§B4-13，内核零改动断言）

## 7. B5 收官（可执行清单=design-b4-b5-pages §B5）

- [ ] 7.1 A6 BooksFragment 销号确认（已删 0 引用，走 §B5-1 清单）
- [ ] 7.2 C19 巡检：豁免色 1 处确认（§B5-2）+0 私有复制组件三步巡检法（§B5-3，含白名单落盘）+D4 recycler_view id 兜底代码随批删除
- [ ] 7.3 AiComposeTheme 五维评分（§B5-4，≥7 分启动收敛 spec）+结论登记（AD-04）
- [ ] 7.4 KPI 终值复盘：严格口径公式（§B5-4，半桥接不计入分子）落 registry+pages-inventory，对 NG 代差复盘

## 8. 每批固定验证链（模板）

- [ ] 8.1 每批：`./gradlew assembleAppDebug` 编译门禁（先 Get-Process 校验无构建进程）+5.5 E2E affected_modules 调度
- [ ] 8.2 Compose L2 脚本：按分册模板 l2_verify_compose_{page}.py（uiautomator 控件断言+截图基线+su -c 整串铁律+venv 专用 Python+logcat -T 起点）；B2 首批 7+B3 9+B4 17 场景（前缀已全册统一）
- [ ] 8.3 每批收尾：registry 回执+检查点审查+daemon 清场

## 9. 设计交叉审核（≥5 轮，用户强制要求）

- [x] 轮 1 册间一致性审核（7 ERROR/6 WARN/INFO 全过）✅ → 修订闭环
- [x] 轮 2 源码符合性抽查（12 断言：10 确认/2 部分/0 驳斥）✅ → 修订闭环
- [x] 轮 3 规范符合性审核（5E/12W/6I）✅ → 修订闭环（28 条 Edit+Grep 双向校验）
- [x] 轮 4 完整性与无悬空审核（1E/4W；四方映射 59/59 闭合；悬空词扫描 5 命中全合法）✅ → 修订闭环
- [x] 轮 5 可实施性终审（修订落实复验 14 PASS/1 PARTIAL+四维度 PASS；终审裁决 **ACCEPT-WITH-NOTES**：W-1 检查点基数 35 统一/W-2 RssSourceEditScreen modifier 已落死/W-3-W-4 为实施期指引项）✅ 2026-08-30

> **设计自审结论**：5 轮交叉审核完成，ACCEPT-WITH-NOTES 放行。遗留观察项 W-3（bottomPadding 示意注释/duplicateKeyGuard 创建点）与 W-4（ThemeSpecPresets 色值占位）均为实施期落死项，册内已有指引，非阻塞。

## AOAdapt 日志

- 轮 1：初版 tasks 路线写成"另立 spec/待校准"悬空 → 用户否决 → 页级总表+批次全量落盘
- 轮 2：页级总表仍为表格级 → 用户要求函数级深度 → 4 分册产出，分册源码勘误 10 处回写总表
- 轮 3（审核轮 1-2 修订）：统计三口径统一/B4-a 归属裁决/章节引用 10 处修正/悬空任务消除/D4 组件签名增补/占比重算 55%
- 轮 4（审核轮 3-4 修订）：①d4 骨架两处运行期缺陷修复（topOverlaySpacePx 状态化/ScrollRestoreEffect snapshotFlow 化）②AppShapes.pill 不存在→Capsule（3 处）③骨架 dp 字面量 token 化+PrimaryTagRow 泛型化+根 modifier 补齐④B4-b 链路契约统一（D7 经 ReadRss）⑤b1-b2 表头 6 列+S5-7 增补+GeneratedCover 裁决成品段⑥检查点基数 33→34⑦L2 前缀统一 l2_verify_compose_⑧统计分母 59/60 拆行口径显式化
