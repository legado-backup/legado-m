# Tasks: "我的"页功能归堆重构

## 1. 准备工作（可行性核查，已完成并记录 design.md C1-C10）
- [x] 1.1 C1 分组标题字符串引用面核实（仅 MySettingsData.kt 单点引用）
- [x] 1.2 C3 urlRecord 引用面核实（删 3 处零残留）+ C10 直达路径核实（通知/崩溃不经入口行）
- [x] 1.3 C6/C7/C8 组件能力核实（showDialogFragment 扩展/SettingsCard title/SettingsClickRow 可空参数）
- [x] 1.4 C9 字符串现状核实（复用项 + 需新增 3 条清单）

## 2. 核心实现（主代理串行执行）
- [ ] 2.1 strings.xml（values + values-zh）：改值 2 条（appearance→外观/tools→工具）+ 新增 3 条（config_category_about/log_diagnostics/data_manage）
- [ ] 2.2 MySettingsData.kt：buildSettingsSections 重排 6 组（高亮迁内容组/AI 迁工具组/删 cacheManage 行/删 urlRecord 行/精准管理独立组/关于组）
- [ ] 2.3 MySettingsData.kt：handleSettingsRowClick 删 "cacheManage"/"urlRecord" 分支 + 删对应 import
- [ ] 2.4 PreciseManageFragment.kt：新增 onCacheManageClick 回调
- [ ] 2.5 PreciseManageFragment.kt：平移 AboutFragment 五个诊断私有方法（saveLog/createHeapDump/copyLogs/copyHeapDump/dumpLogcat）+ waitDialog
- [ ] 2.6 PreciseManageScreen.kt：数据管理卡片加"数据管理"标题 + 存储与下载之间插"缓存管理"行（CloudSync）
- [ ] 2.7 PreciseManageScreen.kt：新增"日志与诊断"标题卡片 3 行（崩溃日志→CrashLogsDialog/保存日志/创建堆转储）
- [ ] 2.8 AboutFragment.kt："其他"分区删三件套三行 + 删五个诊断方法 + 删 KEY 常量 + 清理无用 import

## 3. 验证
- [ ] 3.1 updateLog 基于 git diff 更新（编译前）
- [ ] 3.2 编译 `assembleAppDebug` 通过（构建前 Get-Process 校验无残留构建进程）
- [ ] 3.3 Grep 复核："cacheManage"/"urlRecord" 路由残留 0 处；AboutFragment 无诊断方法残留；无用 import 0
- [ ] 3.4 模拟器 L2：我的页 6 组结构与行归属（S1/S2/S3/S5/S7/S8）
- [ ] 3.5 模拟器 L2：精准管理两卡片（数据管理 5 行含缓存行 + 日志与诊断 3 行）功能与行为一致（S4/S6/S11/S12）
- [ ] 3.6 模拟器 L2：设置搜索页与我的页一致（S9）；直达链路（S10）
- [ ] 3.7 文档同步：tasks/INDEX/项目记忆/updateLog

## AOAdapt 日志

（实施中遇到问题记录于此）
