# Compose 化进度盘点与前端规范修订反思（0908 汇报）

> 任务性质：**汇报类**（用户指令：禁止私自动手直接优化，作为下次迭代输入）。
> 数据来源：migration-registry.md、page-tree.md、ui/ 全源码扫描、res/ 布局与字符串三源交叉、规范文档现状核对。生成于 2026-09-08。

## 一、当前 Compose 化进度汇报

### 1.1 "我的"域子页面及子子页面
- **全量收官**：MC-13 登记 W0~W7.2 全部 `[x]`——45 页盘点（C-full 36 / C-mixed 8 / C-none 2），W5 管理列表/编辑型穷举 17 页（10 零残留+7 实施）、W4 纯 View 重写 2 页（CacheManage/CoverCollectionDetail）、W3 并存收编 4 页、D1 旧弹框 35 个迁 ComposeDialogFragment（grep 残留=0）、W7.2 顶栏 Mode.SUB 消亡（10 页收官）。
- **结论：我的域子页面与子子页面 Compose 化完成**，遗留仅为验证类：真机 L3 全域回归 + W2/W3 视觉验收（挂起，MEmu GPU 故障待补验）。

### 1.2 项目整体还差的页面/组件
- **真传统 View 页约 14 个 Activity**（豁免域 8 个另计）：
  - ui/book/read/config 6 页（ReadMenuCustomButtonEdit、ReadMenuButtonManage、ReadAloudBgmManage、ParagraphRuleManage、ParagraphRuleEdit、AiReadAloudUsageRecord）——均 installGlassTopBar 模式达标顶栏，主体仍 View
  - BookSourceEditActivity（View 内核 CodeView + Compose 弹框；7.11bm 待接线）
  - ui/rss/article 群：RssArticlesFragment + 5 代 Adapter 并存（D4 批3 五代 Adapter 收编遗留）+ RssSortActivity
  - ui/association 2 页（OnLineImport/FileAssociation）+ HandleFileActivity
- **豁免域（非欠账）**：ReadBook/ReadManga/VideoPlayer/SourceLogin/WebView/QrCode/VerificationCode/OpenUrlConfirm/DebugTools 等已登记。
- **组件级**：Explore 主列表 RecyclerView 待接入（list-residue-compose 规格设计中）；page-tree 孤儿 7 项待治理（AdvancedTitleManage、ThemeEditorDialogFragment、CrashLogsDialog 等）。

### 1.3 死代码核查
- **死布局 5 个**（三源交叉零引用复核）：`dialog_edit_text.xml`、`item_rss_article_1/2/3/4.xml`（弹框收官批残留特征）。
- **孤儿字符串 554 个**（18%，含 modules 口径）——总数偏大疑有 getIdentifier 动态取用，**清理前须逐条真机验证**；featureBooks 相关已清干净；替换净化/书架媒体孤儿候选 8 个（bookshelf_tag_edit、menu_replace_rule 等）。
- page-tree 孤儿/死路由 7 项（W3.5 已清 5 个，剩余见 1.2）。

## 二、前端规范修订反思（归一完成后的同步需求）

现状核对：`dialog-shell.md` / `migration-registry.md` / `how-to.md` 已达标；以下 4 处明显滞后，**建议下次迭代修订**（本次未动手）：

1. `docs/project-flow/ui-standards/architecture.md`：§三仍写"顶栏 8 形态→3 基线"、AppManagementTopBar 列为基线、MainTopBarView 标注"将消亡"——与 registry 已登记的 **AppManagementTopBar 删除 + Mode.SUB 消亡 + GlassTopAppBar 子页单源** 矛盾；H3/H4/H5/H12"待治理"清单均已 ✅ 未回收。
2. `docs/project-rules/frontend-ui-standards.md`（强制基线）：ComposeDialogFragment 弹框体系 **0 条款**、组件族基线 0 条款、顶栏 3→1 归一未沉淀——作为强制基线严重滞后。
3. `docs/specs/my-compose-full/README.md` 状态行"设计中"应改"实施完成"。
4. `docs/specs/subpage-topbar-unify/README.md` 状态行"开发中"应改"已收官（3→1）"。
- 另有路径歧义：AGENTS.md 加载表写 `ui-standards/architecture.md`，实际在 docs/project-flow/ 下，建议顺带修正。

## 三、可归一 Compose 化的候选（下次迭代输入）

1. **RssArticles 五代 Adapter 收编**（D4 批3 遗留）：5 代适配器并存是最大重复面，建议 LazyColumn 单源重写并删除 item_rss_article_1~4 死布局。
2. **ui/book/read/config 6 页**：主体 View + installGlassTopBar，可复用编辑类/调试类同构组件族（表单+流式日志）批量收编。
3. **BookSourceEditActivity CodeView 接线**（7.11bm）：编辑器内核保留，外围壳 Compose 化。
4. **弹框家族零星尾巴**：F3/F4 WebView 承载 BottomSheet 保留登记，其余 D 类尾巴逐个核对。
5. **死代码清扫**：5 死布局直接删；554 孤儿字符串建立逐条验证清单后分批删（禁止批量盲删）。

## 四、登记与验证欠账（非代码）

- W2/W3 视觉验收 + 全量 L3（MEmu GPU 故障，真机补验）。
- B2 冻结回执 8 项（7.11bg~bn）、7.11bf RuleSub 收尾核对。
