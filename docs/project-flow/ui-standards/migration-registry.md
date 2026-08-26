# §9.6 迁移登记表（Archive 对齐迁移）

> 登记 Archive 对齐迁移任务（`docs/specs/archive-ui-migration-202608/tasks.md`）各子项的完成状态。
> E 类为「子页面内部实现再审查」补充（E1 弹框 / E2 列表 / E3 半迁移壳 / E4 特色统一外观 / E5 骨架补缺，子任务 `7.11aa~7.11an2`），此外保留 §7.11 其它类（A 管理页缺失 / B 旧实现未对齐 / C 作用域复核 / D 我的页）及 8.x 主任务关键落点。
> **2026-08-25 回填**：本表此前全量 `[ ] 待迁移` 落后于 tasks 勾选；本次按源码实测逐项回填现状（下表"现状"列为代码核验结果），并标注与 tasks.md 勾选的偏差。

## 一、§7.11 E 类（弹框 / 列表 / 壳 / 外观 / 骨架）

### E1 弹框类

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11aa | `book/group/GroupEditDialog`+`GroupSelectDialog`+`GroupManageDialog`、`replace/GroupManageDialog` | [x] 已完成（源码核验 2026-08-25） | `ui/widget/compose/GroupManageComposeDialog` + ComposeDialogFragment | 分组弹框全部 ComposeDialogFragment；GroupManageComposeDialog 为公共 Compose 组件 |
| 7.11ab | `association` ImportBookSource/ImportDictRule/ImportHttpTts/ImportReplaceRule/ImportRssSource/ImportTheme/ImportTxtTocRule（7）+`OnLineImportActivity` | [x] 已完成（源码核验 2026-08-25） | Compose：导入对话框族 | 7 导入弹框均 ComposeDialogFragment + setContent |
| 7.11ac | `manga/config/MangaColorFilterDialog`+`MangaEpaperDialog`+`MangaFooterSettingDialog`、`import/remote/ServerConfigDialog`、`bookmark/BookmarkDialog`、`audio/config/AudioSkipCredits` | [x] 已完成（源码核验 2026-08-25） | Compose 对话框族 | 全部 ComposeDialogFragment + setContent |
| 7.11ad | `config/CheckSourceConfig`+`CoverRuleConfigDialog`+`DirectLinkUploadConfig`、`dict/rule/DictRuleEditDialog` | [x] 已完成（源码核验 2026-08-25） | Compose 对话框族 | 全部 ComposeDialogFragment + setContent（DirectLinkUploadConfig 即原 ComposeDirectLinkUploadDialog） |
| 7.11ae | `about/UpdateDialog` | [x] 已完成（源码核验 2026-08-25） | Compose 对话框族 | UpdateDialog 已 ComposeDialogFragment；UpdateAcceleratorDialog 见 7.11l |
| 7.11af | `toc/rule/TxtTocRuleEditComposeDialog` | [x] 已完成（源码核验 2026-08-25） | Compose 对话框族 | 已建 ComposeDialogFragment，替代旧 TxtTocRuleEditDialog |
| 7.11am | `highlight/` 旧弹框（GroupManage/Edit/PresetRule） | [x] 已完成（源码核验 2026-08-25） | Compose：`GroupManageComposeDialog`/`AppEditDialog` | 三弹框均已迁移 ComposeDialogFragment（HighlightRuleEditDialog 全屏 + HighlightRuleGroupManageDialog 薄壳受控复用 ComposeGroupManageDialogContent + HighlightPresetRuleDialog 底部档），删除 dialog_highlight_* 5 布局 + 1 menu |
| 7.11an | `autoTask/`（AutoTaskLogDialog/ImportAutoTaskDialog）+`widget/dialog/TextListDialog`+`config/CheckRssSourceConfig` | [x] 已完成（源码核验 2026-08-25）：AutoTaskLogDialog/ImportAutoTaskDialog 已迁移 ComposeDialogFragment（AppDialogFrame/dialog_recycler_view 不再引用）；TextListDialog、CheckRssSourceConfig 源码中未检索到（已删/并入检查体系） | `ui/widget/components` | 统一外观；规格 [dialog-leftovers-compose](../../specs/dialog-leftovers-compose/README.md)（✅ 实施完成） |
| 7.11an2 | `video/`（播放器内部旧弹框）+`image/`（图片浏览旧弹框）+`urlrecord/`（访问记录旧弹框） | [x] 已完成（源码核验 2026-08-25）：video `SettingsDialog` 已 ComposeView 承载；image 顶栏 Compose 化；urlrecord `UrlRecordFilterSheet`（过滤底部弹框）+ `ComposeConfirmDialog`（详情弹框）已迁移 | `ui/widget/components`（8.1/8.4 标注落点） | 统一到组件库（E4） |
| 7.11ao | `bookshelf/BookshelfConfigDialog`（`BaseBookshelfFragment` 旧弹框） | [x] 已完成（源码核验 2026-08-25） | Compose | 已建 ComposeDialogFragment 替换书架旧弹框 |

### E2 列表类

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11ag | `replace/ReplaceRuleActivity` 列表 | [x] 已完成（源码核验 2026-08-25） | `AppManagementScaffold` 全 Compose | setContent 已接管，recyclerView 已 removeView；ReplaceRuleAdapter 死代码已删 |
| 7.11ah | `book/search/SearchActivity` 结果列表 | [x] 已完成（源码核验 2026-08-25） | Compose 列表组件 | composeResults/composeInputHelp 已 setContent（SearchResultScreen/SearchInputHelpScreen）；残留 initRecyclerView 仅剩空壳调用 compose 初始化 |
| 7.11ai | `book/cache/CacheActivity` | [x] 已完成（compileAppDebugKotlin 通过 2026-08-25） | `CacheScreen` 纯 Compose `LazyColumn` | 列表 RecyclerView 全量退役：CacheAdapter/item_download.xml 已删，事件局部刷新（UP_DOWNLOAD/EXPORT_BOOK）改按 bookUrl tick 重组；顶栏 GlassTopAppBar 保留；待真机回归（tasks 3.1） |

### E3 半迁移壳（配置页升 ComposeSettingFragment）

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11ak | config `CoverConfigFragment`/`ThemeConfigFragment`/`WelcomeConfigFragment` | [x] 已完成（源码核验 2026-08-25） | `ComposeSettingFragment` | 三个 fragment 均继承 ComposeSettingFragment（另 Ai/Discovery/SubscriptionConfigFragment 也已完成） |
| 7.11al | config `BackupConfigFragment`/`OtherConfigFragment` | [x] **实际已完成但 tasks 未勾（tasks 标 [ ] 滞后）**：BackupConfigFragment:64 + OtherConfigFragment:55 均继承 ComposeSettingFragment | `ComposeSettingFragment` | ⚠️ 纠正 tasks 7.11al「BackupConfigFragment 仍为 PreferenceFragment」表述已过期：源码已 Compose 化 |

### E4 特色统一外观（接入组件库）

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11aj | `explore/ExploreFragment` 主列表接入现代/套件 | [ ] 未完成：主列表仍 RecyclerView（rvDiscoverBooks），但已新增 composeDiscoverBooks/composeDiscoverySuite 区块 | 现代 discovery 套件 | 并入 7.11h（唯一搬入 owner）；部分区块已 Compose，主列表待接入；已出规格 [list-residue-compose](../../specs/list-residue-compose/README.md)（🔄 设计中） |
| 7.11an | （并入 E1 行） | — | — | 特色弹框统一外观归 E4 |
| 7.11an2 | video/image/urlrecord 旧弹框 | [x] 已完成（见 E1 行） | `ui/widget/components` | 统一到组件库 |
| 7.11am | highlight 旧弹框外观 | [x] 已完成（见 E1 行） | `GroupManageComposeDialog`/`AppEditDialog` | 列入 E4 |

### E5 骨架补缺 / 综合

| 任务编号 | 说明 | 现状 | 所属组件 | 备注 |
|---------|------|------|---------|------|
| 7.11（E 类门禁） | 每项编译 `assembleAppDebug` + 运行可达性核对 | [ ] 未完：aa-ab-ac-ad-ae-af-ag-ah-ak-al-ao-am-an-an2 已 Compose 化（am/an/an2 随规格 dialog-leftovers-compose + highlight-dialog-compose 实施完成，待全量编译）；**ai/aj 仍待实施** | — | 待办：7.11ai CacheActivity 列表、7.11aj Explore 主列表（规格 list-residue-compose 实施中） |
| 7.11ap | 作用域复核：`widget/SourceSelectDialog`（并入 7.11t）、`widget/WaterfallCardMetrics`（并入 7.11h 瀑布流批） | [x] 已完成（tasks 已勾；SourceSelectDialog 已 Dialog+ComposeView setContent） | — | 作用域判定项 |

## 二、§7.11 其它类（A / B / C / D）

> 仅列任务骨架，明细见 tasks.md §7.11 主条目。

| 类 | 范围 | 现状 |
|----|------|------|
| A 管理页缺失 | 7.11a~q：云存储/封面图库/书籍信息/导航/顶栏/中转/在线导入/现代发现/书架标签/我的设置/在线导入协议/关于页/规则订阅/ExploreShow/目录规则/换源/RSS 文章搜索等 | [ ] 待实施（见 tasks.md） |
| B 旧实现未对齐 | 7.11r~z：书籍导入识别、音频缓存、SourceSelect 组件、头部布局对齐、关于页回退、配置顶栏回退、主题配置改 Archive、书架死适配器清理 | [ ] 待实施（关于页 7.11w/顶栏 7.11x/主题 7.11y 为回退 Archive 决策项） |
| C 作用域复核判定 | 7.11r/s/t：ImportBook、AudioCache、SourceSelect | [ ] 需判定位 |
| D 我的页 | — | 现状见 tasks.md（D 类在我页相关项） |

## 三、关键衔接（tasks.md「重叠去重/依赖」）

- **重叠去重**：8.9「RuleSub 用 Archive 版」与 7.11m（规则订阅）重复，RuleSub 主体归 7.11m，8.9 仅保留分组封面适配。
- **依赖衔接**：8.5 全局搜索入口依赖 7.11v 订阅顶栏对齐；8.6 分组入口依赖 7.11a-p 管理页 + 7.11v；8.1/8.4 特色弹框外观统一归 E4。
- **门禁**：A/B/D/E 每项补完 = 编译 + 运行可达性；C 类不单独设编译门禁。

## 四、填写说明（维护者）

- 「现状」列：勾选 `[x]` 表示已完成/已覆盖决策；`[ ]` 待做。以 authority tasks.md 勾选为准。
- 「所属组件」列：最终 Compose/组件化落点（`ui/widget/compose/` 或 `ui/widget/components/`）。
- 每完成一项，同步更新本表 + tasks.md 勾选 + 实施回执。