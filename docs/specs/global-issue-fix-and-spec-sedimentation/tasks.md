# Tasks: 全局问题修复与规范沉淀

> **执行顺序**：规范先行 → 数据库 → 崩溃 → 功能闭环 → UI Bug → 规范沉淀收尾
> **强制**：每个阶段完成后必须真机验证

## 1. 规范层先行（P2，但必须先建）

- [x]1.1 新建 `docs/project-rules/global-thinking-checklist.md`（全局思考检查清单）
  - 前端入口盘点（功能有几个入口？入口在哪？）
  - 后端接口影响（动了哪些接口？影响哪些功能？）
  - 数据库改动评估（是否改 schema？如何覆盖安装？）
  - 覆盖安装兼容性（migration 是否可回退？）
- [x]1.2 新建 `docs/project-rules/spec-sedimentation-mechanism.md`（错误沉淀机制）
  - 错误→沉淀→子规范→主规范引用闭环
  - 沉淀触发条件（犯过一次的错误必须沉淀）
  - 沉淀格式规范
- [x]1.3 新建 `docs/project-rules/database-migration-safety.md`（数据库升级安全规范）
  - DatabaseView 修改必须 DROP+CREATE 重建
  - migration 必须 runCatching 包裹
  - version 必须递增，不可降级
  - 覆盖安装兼容性测试要求
- [x]1.4 新建 `docs/project-rules/real-device-test-reuse.md`（真机测试流程复用规范）
  - 测试脚本复用机制
  - 测试用例库管理
  - 测试发现问题的记录→修复闭环
- [x]1.5 AGENTS.md 引用新增子规范

## 2. 数据库升级覆盖安装修复（P0 阻塞）

- [x]2.1 AppDatabase.kt: version 96→97
- [x]2.2 DatabaseMigrations.kt: 新增 migration_96_97（DROP+CREATE VIEW）
- [x]2.3 注册 migration_96_97 到 migrations 数组
- [x]2.4 编译验证
- [x]2.5 真机验证：覆盖安装成功，App 正常启动，书源数据保留

## 3. 高亮规则崩溃修复（P0 崩溃）

- [x]3.1 dialog_highlight_rule_edit.xml: MaterialButton→Button
- [x]3.2 dialog_highlight_rule_group_manage.xml: MaterialButton→Button
- [x]3.3 dialog_highlight_note.xml: MaterialButton→Button
- [x]3.4 item_highlight_rule_group.xml: MaterialButton→Button
- [x]3.5 编译验证
- [x]3.6 真机验证：点+号不再崩溃，能正常打开编辑对话框

## 4. lastHost 三层回填（P1 功能闭环）

- [x]4.1 WebBook.kt: searchBookAwait/getBookInfoAwait/getChapterListAwait/getContentAwait 回填 lastHost
- [x]4.2 Rss.kt: getArticlesAwait/getContentAwait 回填 lastHost
- [x]4.3 BookSourceDebugActivity.kt: 调试时回填 lastHost
- [x]4.4 实现"变化才写 DB"持久化策略（内存缓存+批量持久化）
- [x]4.5 编译验证
- [x]4.6 真机验证：搜索书籍后查 DB 确认 lastHost 已回填

## 5. 域名分组复合键（P1 功能闭环）

- [x]5.1 BookSourceActivity.kt: 分组键改为 (host, bookSourceType)
- [x]5.2 RssSourceActivity.kt: 补齐 groupSourcesByDomain 开关+getSourceHost 方法
- [x]5.3 编译验证
- [x]5.4 真机验证：同域名不同类型源分开显示

## 6. 校验逻辑重构（P1 功能）

- [x]6.1 CheckSourceService.kt: doCheckSource 改为维度并发（coroutineScope+async）
- [x]6.2 每个维度请求完成后回填 lastHost
- [x]6.3 SourceWeightCalculator.kt: 权重计算改为基于关键元素获取结果
- [x]6.4 CheckRssSourceService.kt: 同步重构
- [x]6.5 编译验证
- [x]6.6 真机验证：勾选"域名"CheckBox+AnalyzeUrl模式，校验获取真实域名

## 7. 订阅源播放器菜单修复（P1 UI）

- [x]7.1 定位 VideoPlayerActivity 菜单丢失根因（对比原版 menu XML）
- [x]7.2 恢复刷新按钮+"浏览器打开"菜单项
- [x]7.3 修复返回按钮（toolbar navigationOnClickListener）
- [x]7.4 编译验证
- [x]7.5 真机验证：菜单显示，返回按钮生效

## 8. 订阅源编辑页单源线程数配置（P1 UI）

- [x]8.1 activity_rss_source_edit.xml: 添加 parseConcurrency 配置控件
- [x]8.2 RssSourceEditActivity.kt: 绑定 parseConcurrency 字段
- [x]8.3 编译验证
- [x]8.4 真机验证：配置项可见可保存

## 9. 视频浏览器弹框样式修复（P2 UI）

- [x]9.1 定位弹框组件类型（AlertDialog/BottomSheetDialog）
- [x]9.2 适配 AppTheme.Light 主题
- [x]9.3 编译验证
- [x]9.4 真机验证：弹框样式与整体风格一致

## 10. 规范沉淀收尾（P2）

> 每个"如何避免"必须沉淀到对应子规范，主规范 AGENTS.md 引用

- [x]10.1 `database-migration-safety.md` 沉淀：
  - DatabaseView 修改必须 DROP+CREATE 重建（Issue-1）
  - migration 必须 runCatching 包裹+日志
  - version 必须递增，不可降级
  - Room schema 校验是运行时的
  - 覆盖安装兼容性测试要求
- [x]10.2 `spec-sedimentation-mechanism.md` 沉淀：
  - MaterialButton 需要 Material 主题（Issue-2）
  - 校验必须真正触发功能路径，权重基于关键元素获取程度（Issue-7）
  - 字段回填必须覆盖使用/调试/校验三层（Issue-8）
  - Activity 布局禁止两个 TitleBar 并存，BaseActivity final 方法需绕过（Issue-4）
  - 复杂需求设计方案必须经过3次验证（自检+对照原始反馈+子代理交叉审查）才能提交（Issue-14）
  - 错误→沉淀→子规范→主规范引用闭环
- [x]10.3 `global-thinking-checklist.md` 沉淀：
  - 迁移/重构功能时必须盘点所有使用场景的菜单项（Issue-3）
  - 新增数据字段必须完成全链路：模型+UI+Activity+加载/保存（Issue-5）
  - 新建 UI 组件禁止硬编码颜色，必须用 ?attr/* 或 @color/* 引用（Issue-6）
  - 前端入口盘点+后端接口影响+数据库改动评估+覆盖安装兼容性+使用场景盘点+回填点盘点
  - OpenSpec 步骤1强制门禁
- [x]10.4 `real-device-test-reuse.md` 沉淀：
  - 测试脚本必须放 ai_tests/scripts/，禁止 temp/ 创建临时脚本
  - 测试流程模板：编译安装→导入数据→执行功能→日志分析→问题记录
  - 测试发现问题闭环：记录→修复→真机验证→回填状态（Issue-9）
- [x]10.5 AGENTS.md 引用新增4个子规范
- [x]10.6 更新 `assets/updateLog.md`（基于 git diff 分析真实变更）
- [x]10.7 更新 `docs/INDEX.md`

## 11. 综合真机测试

- [ ] 11.1 全量功能验证（所有修复项）
- [ ] 11.2 覆盖安装验证（从旧版本覆盖升级）
- [ ] 11.3 日志分析确认无崩溃
- [ ] 11.4 更新 issues-found.md

## AOAdapt 日志

（实施中追加，每完成一个任务记录 Action/Observation/Adapt）
