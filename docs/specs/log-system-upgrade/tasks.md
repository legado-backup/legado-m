# tasks.md - 日志系统升级改造

> 状态标记：`[ ]` 待办 ｜ 验证级别：L1 代码完成 / L2 功能验证 / L3 场景验证

## 1. 准备工作

- [x] 1.1 加载实施前置规范：`ui-standards/architecture.md`（四组件族基线+取色唯一基线）+ `frontend-ui-standards.md` + compose-ui-engineering + `logging_rules.md` 【验证标准：规范要点已确认】(L1)
- [x] 1.2 精读 AppLog.kt / AppConfig.kt(recordLog) / PreciseManageFragment.kt 当前实现，确认设计假设与源码一致（禁凭文档臆测）【假设偏差：putDebug/putDebugWithTag 守卫逻辑已符合 AD-02 目标语义，2.1 改动收窄为容量+快照+removeLogs；已回改记录于 AOAdapt】(L1)

## 2. 核心实现

- [x] 2.1 AppLog 调整：MAX_LOG_SIZE 100→500；putDebug/putDebugWithTag 在 recordLog=true 时与其它级别同等记录（内存+文件），release 包 logcat 行为不变；新增 @get:Synchronized logs 快照 + removeLogs(对象引用删除) 【验证标准：L1 编译通过 + Grep 确认 3 处替换】(L1)
- [x] 2.2 AppConfig.recordLog 默认值：无偏好值时 debug 包 true / release 包 false，用户显式设置优先 【验证标准：L1 + 三场景推演通过】(L1)
- [x] 2.3 新建 LogActivity 宿主：TabRow 4 Tab 骨架 + 顶栏 + 空态占位 + Manifest 注册 【验证标准：L1 编译通过】(L1)
- [x] 2.4 应用日志 Tab：内存日志列表（@get:Synchronized 快照）+ 级别筛选 + 关键字搜索（BasicTextField）+ 多选删除（对象引用）+ 单条详情（Throwable 堆栈 TextDialog）+ 单条复制 【验证标准：L2 真机：搜索命中/多选删除生效/详情含堆栈/记录期间操作无并发异常——待用户打包验收】(L1)
- [x] 2.5 崩溃日志 Tab：crash 目录扫描（含 backupPath SAF 副本合并去重）+ 查看全文（尾部截断）+ 单删/多删 + FileProvider 分享 【前置确认：项目已有 FileProvider 且 external-cache-path 覆盖根路径，零新增配置】(L1)
- [x] 2.6 文件日志 Tab：logs 目录扫描（含 .lck）+ 尾部 500 行截断查看 + 删除 (L1)
- [x] 2.7 堆转储 Tab：heapDump 目录扫描 + 大小展示 + 删除（无预览入口）+ 外部工具提示 (L1)
- [x] 2.8 一键清除：确认弹窗（统计各类数量）→ IO 线程逐文件 runCatching 删除（占用中跳过，.lck 一并清理）→ 全 Tab 刷新 + 结果 toast（AD-06）(L1)
- [x] 2.9 导出整合：LogExporter 抽取（saveLog 逻辑自 PreciseManageFragment 逐字节平移，双宿主复用）(L1)
- [x] 2.10 入口接线：精准管理页「日志管理」入口；AppLogDialog/CrashLogsDialog 原入口不受影响。**v1.1 收口修订（用户反馈）**：「崩溃日志」「保存日志」「创建堆转储」菜单移除收口至日志管理右上角 MoreVert 溢出菜单（AppDropdownMenu）；createHeapDump 平移至 LogActivity（onFinally 自动刷新）【验证标准：L1 编译通过】(L1)

## 3. 验证测试

- [x] 3.1 编译验证通过（compileAppDebugKotlin exit=0；首轮 build 因 Kotlin daemon 快照损坏失败，按 AGENTS.md 规范清 kotlin daemon 缓存后恢复）【验证标准：L1，无编译错误】
- [x] 3.2 updateLog.md 基于真实变更更新（含 v1.1 收口条目）【验证标准：逐文件对照变更列表无漏项】
- [ ] 3.3 真机 L2 全场景验证（测试包 io.legado.miss.app.debug）：spec.md 全部 8 个 Scenario 逐项执行——**待用户打包验收**（用户指示"先别打包"，090612 包不含本任务改动）
- [x] 3.4 Grep 检查：无 android.util.Log 残留调试日志、无硬编码色值、无残留临时日志 【验证标准：Grep 0 命中】✅ 两轮执行均 0 命中

## 4. 文档收尾

- [x] 4.1 同步 `docs/project-rules/logging_rules.md`：recordLog 开关语义（开=全量四级/关=ERROR/WARN/INFO）+ 默认值包类型差异 + 日志管理页说明 【验证标准：Read 确认内容存在】
- [x] 4.2 更新 `docs/INDEX.md` 状态流转（🔄 设计中→开发中）【验证标准：Read 确认】
- [x] 4.3 issues-found.md：本轮无新增真机问题（L2 待验收）；临时文件检查：无 temp 残留（全为 ui/log 正式文件）
- [ ] 4.4 检查点 2 最终验收（AskUserQuestion 三选项）→ 通过后归档至 `docs/specs/archive/{日期}-log-system-upgrade/`

## AOAdapt 日志

- 2.1 实现 AppLog 调整
  - Action: 按设计将 putDebug/putDebugWithTag 守卫分支改为 recordLog=true 即记录
  - Observation: 精读源码发现现有守卫逻辑已符合 AD-02 目标语义（recordLog=true 时 DEBUG 级已同等记录），无需改守卫
  - Adapt: 2.1 改动收窄为 MAX_LOG_SIZE 常量化+快照锁+removeLogs，1.2 假设偏差已回记
- 2.3 LogActivity 编译
  - Action: 首次 build-legado.bat 全量打包
  - Observation: Kotlin daemon 快照损坏（kapt3 incrementalData class 缺失 + kotlin-backups NoSuchFileException）构建失败
  - Adapt: 按 AGENTS.md 规范 daemon-stop + 删除 %LOCALAPPDATA%\kotlin\daemon 后恢复
- 2.3 logs 快照 getter 编译错误（并行会话修复）
  - Observation: object 中 val getter 直接标注 @Synchronized 编译错误（注解目标不适用）
  - Adapt: 并行会话（video-regression-fix-0906）修复为 @get:Synchronized；后续同场景直接用 @get:Synchronized
- 2.10 用户反馈收口（v1.1）
  - Action: 初版右上角 3 个一级图标（多选/导出/一键清除）
  - Observation: 用户反馈应按规范收口为三点溢出菜单，且三件套菜单（崩溃/保存/堆转储）应移除统一入口
  - Adapt: actions 改 MoreVert+AppDropdownMenu（4 菜单项）；PreciseManage 卡片2 精简为「日志管理」单行；createHeapDump 平移 LogActivity
- [x] 2.4 AppLog @Synchronized 快照
  - Action: 并行会话实施后由 video-regression-fix-0906 会话接管核验
  - Observation: @Synchronized 直接标注无后备字段属性导致编译失败（kapt stubs 阶段）
  - Adapt: 改为 @get:Synchronized（getter 用法点），语义不变，编译通过
