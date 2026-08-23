# §9.6 迁移登记表（Archive 对齐迁移）

> 登记 Archive 对齐迁移任务（`docs/specs/archive-ui-migration-202608/tasks.md`）各子项的完成状态。
> E 类为「子页面内部实现再审查」补充（E1 弹框 / E2 列表 / E3 半迁移壳 / E4 特色统一外观 / E5 骨架补缺，子任务 `7.11aa~7.11an2`），此外保留 §7.11 其它类（A 管理页缺失 / B 旧实现未对齐 / C 作用域复核 / D 我的页）及 8.x 主任务关键落点。
> 当前状态以 tasks.md 勾选为准（未勾 = `[ ]` 待做，勾选 = `[x]` 已完成/已覆盖）。

## 一、§7.11 E 类（弹框 / 列表 / 壳 / 外观 / 骨架）

### E1 弹框类

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11aa | `book/group/GroupEditDialog`+`GroupSelectDialog`+`GroupManageDialog`、`replace/GroupManageDialog` | [ ] 待迁移 | Compose：`GroupManageComposeDialog` | 复用分组管理 Compose 对话框 |
| 7.11ab | `association` ImportBookSource/ImportDictRule/ImportHttpTts/ImportReplaceRule/ImportRssSource/ImportTheme/ImportTxtTocRule（7）+`OnLineImportActivity` | [ ] 待迁移 | E3：Compose 导入对话框族 | 配套 7.11k 在线导入体系 |
| 7.11ac | `manga/config/MangaColorFilterDialog`+`MangaEpaperDialog`+`MangaFooterSettingDialog`、`import/remote/ServerConfigDialog`、`bookmark/BookmarkDialog`、`audio/config/AudioSkipCredits` | [ ] 待迁移 | Compose 对话框族 | 阅读/图源相关弹框 |
| 7.11ad | `config/CheckSourceConfig`+`CoverRuleConfigDialog`+`DirectLinkUploadConfig`、`dict/rule/DictRuleEditDialog` | [ ] 待迁移 | Compose：`ComposeDirectLinkUploadDialog` | 配置/字典弹框 |
| 7.11ae | `about/UpdateDialog` | [ ] 待迁移 | Compose 对话框族 | 补充 `UpdateAcceleratorDialog`（含于 7.11l） |
| 7.11af | `toc/rule/TxtTocRuleEditComposeDialog` | [ ] 待迁移 | Compose 对话框族 | 替代旧 `TxtTocRuleEditDialog`（并入原 7.11o） |
| 7.11am | `highlight/` 旧弹框（GroupManage/Edit/PresetRule） | [ ] 待迁移 | Compose：`GroupManageComposeDialog`/`AppEditDialog` | 高亮弹框统一外观（E4） |
| 7.11an | `autoTask/`（AutoTaskLogDialog/ImportAutoTaskDialog）+`widget/dialog/TextListDialog`+`config/CheckRssSourceConfig` | [ ] 待迁移 | `ui/widget/components` | 统一外观 |
| 7.11an2 | `video/`（播放器内部旧弹框）+`image/`（图片浏览旧弹框）+`urlrecord/`（访问记录旧弹框） | [ ] 待迁移 | `ui/widget/components`（8.1/8.4 标注落点） | 统一到组件库（E4） |
| 7.11ao | `bookshelf/BookshelfConfigDialog`（`BaseBookshelfFragment` 旧弹框） | [ ] 待迁移 | Compose | 替换书架旧弹框 |

### E2 列表类

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11ag | `replace/ReplaceRuleActivity` 列表 | [ ] 待迁移 | `AppManagementScaffold` 全 Compose | 删 `ReplaceRuleAdapter` 死代码 |
| 7.11ah | `book/search/SearchActivity` 结果列表 | [ ] 待迁移 | Compose 列表组件 | 去除残留 `RecyclerView`/`SearchAdapter`/`AlertDialog`；清 `BookAdapter`/`HistoryKeyAdapter` 死代码 |
| 7.11ai | `book/cache/CacheActivity` | [ ] 待迁移 | Compose 列表组件 | 去除残留 `RecyclerView`/`AlertDialog` 段 |

### E3 半迁移壳（配置页升 ComposeSettingFragment）

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11ak | config `CoverConfigFragment`/`ThemeConfigFragment`/`WelcomeConfigFragment` | [ ] 待迁移 | `ComposeSettingFragment` | 升声明式设置壳 |
| 7.11al | config `BackupConfigFragment`/`OtherConfigFragment` | [ ] 待迁移（纠正：现为纯 `PreferenceFragment` 未 Compose 化） | `ComposeSettingFragment` | 差异最大；**纠正 7.7a「备份已对齐」表述** |

### E4 特色统一外观（接入组件库）

| 任务编号 | 文件（现状） | 现状 | 所属组件 | 备注 |
|---------|------------|------|---------|------|
| 7.11aj | `explore/ExploreFragment` 主列表接入现代/套件 | [ ] 待迁移 | 现代 discovery 套件 | 并入 7.11h（唯一搬入 owner） |
| 7.11an | （并入 E1 行） | — | — | 特色弹框统一外观归 E4 |
| 7.11an2 | video/image/urlrecord 旧弹框 | [ ] 待迁移 | `ui/widget/components` | 统一到组件库 |

### E5 骨架补缺 / 综合

| 任务编号 | 说明 | 现状 | 所属组件 | 备注 |
|---------|------|------|---------|------|
| 7.11（E 类门禁） | 每项编译 `assembleAppDebug` + 运行可达性核对 | [ ] | — | A/B/D/E 每项补完即过门禁；E1 弹框优先可批量并行 |
| 7.11ap | 作用域复核：`widget/SourceSelectDialog`（并入 7.11t）、`widget/WaterfallCardMetrics`（并入 7.11h 瀑布流批） | [ ] | — | 作用域判定项 |

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