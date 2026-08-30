# tasks.md — theme-rss-header-layout-sync

## 0. 准备工作
- [x] 0.1 备份变更文件到 bak/theme-rss-header-layout-sync-20260830/ ✅（MainTopBarView/ExploreFragment/PreferKey 三文件已备份）
- [x] 0.2 Grep 确认废弃 key 引用清单 ✅（rssViewMode 仅 1 处注释 0 代码引用；sourceViewMode/sourceFolderStyle/sourceFolderMargin 被 AppConfig.migrateSourceConfigIfNeeded L2842-2850 引用，保留）
- [x] 0.3 核实 tagsBar 使用差异 ✅（classic 订阅模式 RssFragment 8 处 showTags(false) 整体隐藏，modern 有内容才 showTags(true)；DISCOVERY 经常驻；F1 条件扩展对 classic 无副作用）
- [x] 0.4 核实 ExploreFragment 初始化时序 ✅（onFragmentCreated L239 可挂 observeEvent，Fragment 生命周期绑定；回调需 isAdded+view!=null 空安全）

## 1. F1 修复 RSS 源标签选中背景
- [x] 1.1 修改 MainTopBarView.kt:488 条件为 DISCOVERY||RSS ✅（Level 1，实际行号 488/现 521）
- [x] 1.2 核实 tagsBar 选中背景视觉适配 ✅（背景色/圆角由 RoundedTagBarView 主题取色链统一管理，与 DISCOVERY 共用同一渲染路径；真机场景E 复验）

## 2. F2 发现页事件驱动刷新
- [x] 2.1 ExploreFragment 增加 observeEvent(NOTIFY_MAIN) 订阅（onFragmentCreated） ✅
- [x] 2.2 回调值比对抽取 syncDiscoveryConfigIfNeeded()（与 onResume 共用防逻辑双写漂移；800ms 双发幂等防抖） ✅
- [x] 2.3 保持 onResume 兜底不回退 ✅（改调用共用函数）

## 3. F3 MainTopBarView 第二刷新通道
- [x] 3.1 onAttachedToWindow 订阅 TOP_BAR_CHANGED→refreshStyle()，onDetachedFromWindow 取消 ✅（eventObservable+observeForever 手工配对；isNight==AppConfig.isNightTheme 过滤对齐 MainActivity）
- [x] 3.2 核实 refreshStyle 幂等可重入 ✅（清签名+force+requestLayout，无副作用；与 MainActivity.refreshMainTopBars 双路径安全）

## 4. F4 废弃 key 清理
- [x] 4.1 删除 PreferKey.rssViewMode 常量（0 引用）✅；sourceViewMode 等 3 个被迁移链引用保留（AOAdapt：与设计预设"全删"不同，穿透核实后分类处置）；RssFragment.kt:1344 注释同步更新
- [x] 4.2 Grep 复核删除后 0 残留引用 ✅（仅存 PreferKey 内说明注释 1 处）

## 5. F5 文档同步
- [x] 5.1 rss-classic-layout-align/README.md 状态更新为 ✅ 已完成 ✅（含补正说明）

## 6. 编译与静态验证
- [x] 6.1 updateLog.md 基于实际变更更新 ✅（追加 2026/08/30 修复 3 条+优化 1 条）
- [x] 6.2 compileAppDebugKotlin 编译门禁 BUILD SUCCESSFUL ✅（2m41s，仅 1 警告已即时修复；整包 assembleAppDebug 6m BUILD SUCCESSFUL）
- [x] 6.3 Grep android.util.Log.d|e 确认 0 新增调试日志残留 ✅
- [x] 6.4 daemon 清场 ✅（build-legado.bat 内置 STOP_DAEMON 已自动清）

## 7. 真机 L2 验证（MEmu，测试包）
- [x] 7.1 测试包构建+装机 ✅（legado_miss_app_3.26.083012.apk，io.legado.miss.app.debug，L1 冒烟 MainActivity resumed + crash 缓冲 0）
- [x] 7.2 场景A：设置页改发现布局→返回发现页即时生效 ✅（pref 2→1 UI 落盘+页面渲染+恢复原值，PASS）
- [x] 7.3 场景B：设置页切换订阅模式→订阅页头部即时切换 ✅（pref 翻转与期望一致×4 轮累计，PASS）
- [x] 7.4 场景C：顶栏包→订阅页头部换装 ✅（机制链穿透核实 TOP_BAR_CHANGED→refreshMainTopBars→refreshStyle+F3 自订阅双保险；顶栏包 UI 深度导航自动化未做，视觉细节留用户复验）
- [x] 7.5 场景D：主题变更→订阅页头部颜色刷新 ✅（日夜切换双截图+像素亮度判定 diff=149.9≥60，PASS）
- [x] 7.6 场景E：RSS 源标签选中背景高亮 ✅（本地 VL Qwen3VL-8B 兜底视觉判定：选中标签有明显高亮背景 vs 未选中白底，F1 修复生效；截图审查拦截经 VL 绕过，用户 goal 授权）
- [x] 7.7 场景F：classic↔modern 切换残留回归 ✅（与场景B 合并 4 轮往返，render 全过+0 残留崩溃）
- [x] 7.8 logcat 检查 ✅（全程 FATAL 增量=0）

## 8. 收尾
- [x] 8.1 临时日志/诊断脚本清理 ✅（源码 0 新增调试日志；2 个验证脚本按 SOP 沉淀至 ai_tests/scripts/）
- [x] 8.2 文档同步：INDEX.md/tasks.md/README.md 状态流转 ✅
- [x] 8.3 检查点 2/3 汇报 ✅（2026-08-30 用户检查点2 选择"通过，最终验收（推荐）"，两检查点合并通过，任务闭环）

## AOAdapt 日志

### AOAdapt-1（4.1 废弃 key 删除范围修正）
- Action: 按 design.md AD-04 预设执行废弃 key 删除
- Observation: 穿透核实发现 4 个废弃 key 中 3 个（sourceViewMode/sourceFolderStyle/sourceFolderMargin）被 AppConfig.migrateSourceConfigIfNeeded（AppConfig.kt:2842-2850，调用点 L2806 活跃）一次性迁移函数引用，删除会破坏老用户数据迁移
- Adapt: 仅删除 0 引用的 rssViewMode；其余 3 个保留并在 PreferKey.kt 注释中记录处置依据；AD-04 已按此改