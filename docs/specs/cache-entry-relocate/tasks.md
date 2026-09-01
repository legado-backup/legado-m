# Tasks: "我的"页功能归堆重构

## 1. 准备工作（可行性核查，已完成并记录 design.md C1-C10）
- [x] 1.1 C1 分组标题字符串引用面核实（仅 MySettingsData.kt 单点引用）
- [x] 1.2 C3 urlRecord 引用面核实（删 3 处零残留）+ C10 直达路径核实（通知/崩溃不经入口行）
- [x] 1.3 C6/C7/C8 组件能力核实（showDialogFragment 扩展/SettingsCard title/SettingsClickRow 可空参数）
- [x] 1.4 C9 字符串现状核实（复用项 + 需新增 3 条清单）

## 2. 核心实现（主代理串行执行）
- [x] 2.1 strings.xml（values + values-zh）：改值 2 条（appearance→外观/tools→工具）+ 新增 3 条（config_category_about/log_diagnostics/data_manage）✅ 2026-09-01（收口核实：5 key 双语言全到位——values:1454-1455/2698-2701、values-zh:1383-1384/2377-2380；随 e706bae53 入库）
- [x] 2.2 MySettingsData.kt：buildSettingsSections 重排 6 组（高亮迁内容组/AI 迁工具组/删 cacheManage 行/删 urlRecord 行/精准管理独立组/关于组）✅ 2026-09-01（收口核实：6 组结构+行归属与 design 映射表逐项一致，highlightRule/ai_setting 归位）
- [x] 2.3 MySettingsData.kt：handleSettingsRowClick 删 "cacheManage"/"urlRecord" 分支 + 删对应 import ✅ 2026-09-01（Grep 复核 4 关键词残留=0）
- [x] 2.4 PreciseManageFragment.kt：新增 onCacheManageClick 回调 ✅ 2026-09-01（L56 onCacheManageClick→CacheManageActivity）
- [x] 2.5 PreciseManageFragment.kt：平移 AboutFragment 五个诊断私有方法（saveLog/createHeapDump/copyLogs/copyHeapDump/dumpLogcat）+ waitDialog 语义 ✅ 2026-09-01（L75-163 五方法平移到位；saveLog/createHeapDump 内联 waitDialog 语义由 Coroutine.async 链承接，无残留阻塞等待 UI）
- [x] 2.6 PreciseManageScreen.kt：数据管理卡片加"数据管理"标题 + 存储与下载之间插"缓存管理"行（CloudSync）✅ 2026-09-01（L57 title=data_manage、L79-84 缓存行 CloudSync 图标、行序 History→Storage→CloudSync→Download→Folder）
- [x] 2.7 PreciseManageScreen.kt：新增"日志与诊断"标题卡片 3 行（崩溃日志→CrashLogsDialog/保存日志/创建堆转储）✅ 2026-09-01（L106-133 卡片2：BugReport/SaveAlt/Memory）
- [x] 2.8 AboutFragment.kt："其他"分区删三件套三行 + 删五个诊断方法 + 删 KEY 常量 + 清理无用 import ✅ 2026-09-01（Grep 复核诊断方法/KEY/CrashHandler/ZipUtils/FileDoc 残留=0，"其他"分区仅剩隐私政策/License/免责声明）

## 3. 验证
- [x] 3.1 updateLog 基于 git diff 更新（编译前）✅ 2026-09-01（updateLog.md L193-195 已登记：6 组归堆/缓存入口迁移+诊断迁移/卡片标题+消双入口，随 e706bae53 入库）
- [x] 3.2 编译 `assembleAppDebug` 通过（构建前 Get-Process 校验无残留构建进程）✅ 2026-09-01（代码已随 e706bae53 入库，后续 b5a0df088 打包 3.26.090115 真机 L1/P0 L2 双 PASS=编译验证已覆盖；收口无代码改动且工作区混有并行会话未提交改动，重编译结果不可归因，不重复触发编译门禁）
- [x] 3.3 Grep 复核："cacheManage"/"urlRecord" 路由残留 0 处；AboutFragment 无诊断方法残留；无用 import 0 ✅ 2026-09-01（MySettingsData 4 关键词=0；AboutFragment 10 关键词=0）
- [ ] 3.4 模拟器 L2：我的页 6 组结构与行归属（S1/S2/S3/S5/S7/S8）（挂总线 2.6.2 真机窗口统一走查）
- [ ] 3.5 模拟器 L2：精准管理两卡片（数据管理 5 行含缓存行 + 日志与诊断 3 行）功能与行为一致（S4/S6/S11/S12）（挂总线 2.6.2 真机窗口统一走查）
- [ ] 3.6 模拟器 L2：设置搜索页与我的页一致（S9）；直达链路（S10）（挂总线 2.6.2 真机窗口统一走查）
- [x] 3.7 文档同步：tasks/INDEX/项目记忆/updateLog ✅ 2026-09-01（tasks 勾选+INDEX 状态 ✅+README 状态收口；updateLog 已有登记无需追加；项目记忆由总线会话统一维护）

## AOAdapt 日志

- [2026-09-01] 收口（总线 master-track-orchestration tasks 3.4）：代码实施核实已随 e706bae53 全量入库（6 文件与 design Technical Approach 表逐项一致），Grep 复核零残留，updateLog 已登记 L193-195；2.1-2.8+3.1-3.3+3.7 勾选，3.4-3.6 模拟器 L2 挂总线 2.6.2 真机窗口；收口零代码改动，未触发编译门禁（工作区混有并行会话未提交改动，重编译结果不可归因）。B4-c 瘦身 About 的反序重复劳动前置解除。
