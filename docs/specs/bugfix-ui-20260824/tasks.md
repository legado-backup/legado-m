# bugfix-ui-20260824 任务清单

## 1. 需求确认
- [ ] 1.1 用户确认 8 项问题范围与顶栏方案（ADR-01）✅ 2026-08-24 检查点1
- [ ] 1.2 真机确认任务①用户具体指代界面（订阅列表/书源管理/文件夹）
- [ ] 1.3 真机确认任务②搜索框差异点（订阅头部 vs 发现/书源管理）

## 2. 文案类（⑦⑧④ 文案部分）
- [ ] 2.1 values-zh/strings.xml app_name_sigma "阅读Archive"→"阅读M"（⑦）
- [ ] 2.2 values-zh/strings.xml welcome_title "阅读"→"阅读M"（⑧）
- [ ] 2.3 values/strings.xml source_group_mode_folder "分组"→"文件夹"（④文案）

## 3. 订阅布局列数生效（④）
- [ ] 3.1 RssFragment 新增 effectiveSpanCount()（sourceLayout 2-6 直用，否则自适应）
- [ ] 3.2 applyListView/applyFolderView/initFolderComposeView 改用 effectiveSpanCount()
- [ ] 3.3 验证分组（文件夹）模式网格 3 列生效

## 4. 经典订阅切回头部标签销毁（⑤）
- [ ] 4.1 initComposeTopBar 清空 primaryBar/tagsBar（setPrimaryItems(emptyList)/submitItems(emptyList)/showTags(false)）
- [ ] 4.2 新版→经典切换验证头部标签即时销毁

## 5. 顶栏管理颜色生效（③，按 ADR-01 方案）
- [ ] 5.1 按用户选择方案实施 MyFragment 头部
- [ ] 5.2 按用户选择方案实施 ExploreFragment 经典头部
- [ ] 5.3 顶栏管理设色后真机验证我的/发现经典头部生效

## 6. 搜索框样式统一（②）
- [ ] 6.1 按确认范围统一订阅头部搜索框与发现/书源管理搜索框样式
- [ ] 6.2 真机验证各页搜索框样式一致

## 7. 订阅/书源列表图片圆角（①）
- [ ] 7.1 按确认范围统一订阅/书源/文件夹列表图片四角圆弧
- [ ] 7.2 真机验证各布局图片圆角

## 8. 我的页重复入口移除（⑥）
- [ ] 8.1 MyFragment.buildSections 删除 fileManage 行
- [ ] 8.2 验证精准管理文件管理入口正常

## 9. 订阅页分组管理入口（⑪）
- [ ] 9.1 RssFragment.showRssMenu 加"分组管理"Action → showDialogFragment<GroupManageDialog>
- [ ] 9.2 验证分组增删改后菜单/标签联动刷新

## 10. 前端 UI 规范沉淀（⑨）
- [x] 10.1 盘点 archive 迁移后实际 UI 架构（骨架/组件族/TopBar 选用/主题接入/状态范式）— ✅ 完成（盘点结论见 design.md 114-116 行；落地为 frontend-ui-standards.md §2-§3，回勾 2026-08-25）
- [x] 10.2 新建 docs/project-rules/frontend-ui-standards.md — ✅ 完成（2026-08-24 已建；本节 10.2 回勾 2026-08-25，并补正 §5 关联规范断链 → ui-redesign-m3/ui-standards.md + 职责边界）
- [x] 10.3 登记 docs/INDEX.md + AGENTS.md 子规范加载表 — ✅ 完成（INDEX.md:33 + AGENTS.md:124 已登记；compose-ui-engineering SKILL 项目文档表已同步钩挂新规范，回勾 2026-08-25）

## 11. APK 体积分析与精简（⑩）
- [ ] 11.1 输出 debug/release 包体积构成分析报告（含与 archive/历史包基线对比）
- [ ] 11.2 lint 死资源/死代码检查，输出清理清单
- [ ] 11.3 确认 release shrinkResources + resConfigs 语言裁剪
- [ ] 11.4 ABI 拆分（仅 arm64）——需用户确认后落地

## 12. 编译门禁 + 文档同步
- [ ] 12.1 assembleAppDebug BUILD SUCCESSFUL
- [ ] 12.2 updateLog.md 追加 2026/08/24 修复条目
- [ ] 12.3 tasks.md 全部勾选 + docs/INDEX.md 状态更新
- [ ] 12.4 项目记忆 ai_memory_main.md 同步

## AOAdapt 日志
（实施中如调整方案，在此记录 Action/Observation/Adapt）
