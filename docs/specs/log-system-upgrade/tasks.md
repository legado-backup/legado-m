# tasks.md - 日志系统升级改造

> 状态标记：`[ ]` 待办 ｜ 验证级别：L1 代码完成 / L2 功能验证 / L3 场景验证

## 1. 准备工作

- [x] 1.1 加载实施前置规范：`ui-standards/architecture.md`（四组件族基线+取色唯一基线）+ `frontend-ui-standards.md` + compose-ui-engineering + `logging_rules.md` 【验证标准：规范要点已确认】
- [x] 1.2 精读 AppLog.kt / AppConfig.kt(recordLog) / PreciseManageFragment.kt 当前实现，确认设计假设与源码一致（禁凭文档臆测）【验证标准：假设偏差已记录并回改设计文档（如有）】

## 2. 核心实现

- [x] 2.1 AppLog 调整：MAX_LOG_SIZE 100→500；putDebug/putDebugWithTag 在 recordLog=true 时与其它级别同等记录（内存+文件），release 包 logcat 行为不变 【验证标准：L1 + Grep 确认守卫分支逻辑存在】
- [x] 2.2 AppConfig.recordLog 默认值：无偏好值时 debug 包 true / release 包 false，用户显式设置优先 【验证标准：L1 + 三场景推演（debug 未设置/release 未设置/显式设置）】
- [x] 2.3 新建 LogActivity 宿主：TabRow 4 Tab 骨架 + 顶栏（一键清除/导出）+ 空态占位 + Manifest 注册 【验证标准：L1 + 编译通过】
- [x] 2.4 应用日志 Tab：内存日志列表（AppLog 新增 @Synchronized 快照方法返回不可变副本）+ 级别筛选 + 关键字搜索 + 多选删除（经 AppLog.removeLogs 按对象引用删除，避免实时插入索引漂移）+ 单条详情（Throwable 堆栈）+ 单条复制 【验证标准：L2 真机：搜索命中/多选删除生效/详情含堆栈/记录期间操作无并发异常】
- [x] 2.5 崩溃日志 Tab：crash 目录扫描（名称+大小+时间）+ 查看全文（尾部截断）+ 单删/多删 + FileProvider 分享 【验证标准：L2 真机：构造崩溃文件后可查看/删除/分享；前置：确认项目已有 FileProvider 配置，若无则补注册及 crash 文件 paths 声明】
- [x] 2.6 文件日志 Tab：logs 目录扫描（含 .lck 纳入删除范围）+ 尾部 500 行截断查看 + 删除 【验证标准：L2 真机：大文件查看不 OOM 且有截断提示】
- [x] 2.7 堆转储 Tab：heapDump 目录扫描 + 大小展示 + 删除（无预览入口） 【验证标准：L2 真机：手动创建堆转储后列表可见、可删除】
- [x] 2.8 一键清除：确认弹窗（统计各类日志条数/文件数）→ IO 线程逐文件 runCatching 删除（占用中文件跳过，.lck 一并清理）→ 全 Tab 刷新 + 结果 toast（AD-06） 【验证标准：L2 真机：清除后四 Tab 全空、目录文件 0 残留、写盘不中断】
- [x] 2.9 导出整合：复用 saveLog 逻辑（logcat.txt + logs/ + crash/ 打包 logs.zip） 【验证标准：L2 真机：导出文件可用】
- [x] 2.10 入口接线：精准管理页新增「日志管理」入口；「崩溃日志」入口改跳转日志管理页崩溃 Tab（LogActivity 支持 Intent extra 指定初始 Tab）；「保存日志」「创建堆转储」保留原逻辑 【验证标准：L2 真机：三入口行为正确，AppLogDialog/CrashLogsDialog 原入口不受影响】

## 3. 验证测试

- [x] 3.1 全量编译 `build-legado.bat`（测试包）通过 【验证标准：L1，无编译错误】
- [x] 3.2 updateLog.md 基于 git diff 真实变更更新（编译前完成） 【验证标准：逐文件对照变更列表无漏项】
- [x] 3.3 真机 L2 全场景验证（测试包 io.legado.miss.app.debug）：spec.md 全部 8 个 Scenario 逐项执行 【验证标准：L2/L3，全部通过并记录证据】
- [x] 3.4 Grep 检查：无 android.util.Log 残留调试日志、无硬编码色值、无残留临时日志 【验证标准：Grep 0 命中】

## 4. 文档收尾

- [x] 4.1 同步 `docs/project-rules/logging_rules.md`：新守卫语义（开=全量四级/关=ERROR/WARN/INFO）+ 默认值包类型差异 + 日志管理页说明 【验证标准：Read 确认内容存在】
- [x] 4.2 更新 `docs/INDEX.md` 状态流转 【验证标准：Read 确认】
- [x] 4.3 issues-found.md 记录真机问题（如有）；清理临时文件与调试代码 【验证标准：目录无临时脚本残留】
- [x] 4.4 检查点 2 最终验收（AskUserQuestion 三选项）→ 通过后归档至 `docs/specs/archive/{日期}-log-system-upgrade/`

## AOAdapt 日志

（开发中遇到问题时记录）
- [x] 2.4 AppLog @Synchronized 快照
  - Action: 并行会话实施后由 video-regression-fix-0906 会话接管核验
  - Observation: @Synchronized 直接标注无后备字段属性导致编译失败（kapt stubs 阶段）
  - Adapt: 改为 @get:Synchronized（getter 用法点），语义不变，编译通过
