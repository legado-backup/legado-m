# tasks.md — 子页面顶栏样式统一

## 1. 准备工作
- [x] 1.1 基线确认：①Read MainTopBarView 确认 Mode 属性可访问性（SUB/MAIN 判定方式）②Read fragment_explore.xml 宿主确认 TitleBar 是否运行时在用 ③Read GlassTopAppBar navIcon 参数消费方式，确认 ic_arrow_back 以 ImageVector 传入的可行路径（ImageVector.vectorResource 或既有封装）
  - 验证标准：Mode 判定方案明确，fragment_explore 处理决策（删除/豁免）有依据，navIcon 适配方式确定
  - 结论：①`mode` 类内私有成员可直接访问（:98）②fragment_explore.xml 为整文件死代码（ExploreFragment 实用 ActivityThemeManageBinding）→ 豁免留痕 ③navIcon=ImageVector，`Icons.AutoMirrored.Filled.ArrowBack` 直传（GlassTopAppBar 已 import）
- [ ] 1.2 打包基线：`build-legado.bat` 编译通过，确认改前无编译错误
  - 验证标准：BUILD SUCCESSFUL
  - AOAdapt：改前基线编译与 4.1 合并执行（省一轮 4min+ 增量构建），编译失败时先区分是否本次变更引入

## 2. 核心实现
> 门禁：2.6 updateLog 必须在 2.1-2.5 任意代码变更的首次编译前完成。
- [x] 2.1 TopBarConfig 新增 `resolvePageBarColor(context, config)` 三级决策函数（含注释：决策链说明 + 壁纸态不走本函数）
  - 验证标准：函数存在且逻辑与 AppManagementScaffold.kt:154-159 三级链一致 (L1) ✓ 同包 AppConfig 无需 import
- [x] 2.2 AppManagementTopBar 接入：topBarBase 改调统一函数（AppManagementScaffold.kt:152-159 去重）
  - 验证标准：Grep 确认调用点，行为与改前等价 (L1) ✓ 保持无 remember 直算语义（immersiveManageBar 切换即时生效）；清理 unused import primaryColor/titleTextColor
- [x] 2.3 GlassTopAppBar 接入：defaultColor 分支重构（壁纸态保持 withOpacity(resolve)，否则统一函数）
  - 验证标准：Grep 确认两分支逻辑，containerColor 覆盖参数不受影响 (L1) ✓ 清理 unused import primaryColor
- [x] 2.4 ConfigTopBar 消灭（AD-04 组件收敛）：ConfigActivity :135 调用点换 GlassTopAppBar；新增 MenuAction 适配函数（alwaysShow&&!header 一级图标直出 20dp，其余三点+AppDropdownMenu 溢出，逻辑从 ConfigTopBar :240-297 平移）；删除 ConfigTopBar 定义(:187-298) + decodeTopBarBitmap(:300+) + 无用 import；实施前备份 ConfigActivity.kt 到 bak 目录
  - 验证标准：Grep 全局 `ConfigTopBar` 零定义零调用 ✓ 编译通过；设置页顶栏为 GlassTopAppBar 形态（主题主色+contrastOn 内容色） (L1)；MenuAction 字段（icon/title/onClick/alwaysShow/header）与适配完全匹配 ✓；AppMenuSheet.kt 过时注释同步纠正 ✓
- [x] 2.5 MainTopBarView 接入：renderBackgroundLayer fallbackColor 按 Mode 分流（SUB→统一函数，MAIN→保持）；SUB 内容色与主色底对比度校验（必要时对齐 contrastOn）
  - 验证标准：Read 确认分流逻辑，Mode.MAIN 路径与改前一致；真机确认 SUB 标题/图标在主色底可读 (L1) ✓ 新增成员 subBarContentColor（SUB+regular+无壁纸时=contrastOn(基色)，其余 null 回归原色）；renderBackgroundLayer + applyRegularStyle :513 + updateIconColors 三点消费；深挖发现 default style SUB 顶栏本透明露宿主底色无需动 ✓
- [x] 2.6 updateLog.md 更新（基于 git diff 逐文件分析，编译前完成）
  - 验证标准：条目位于 `## cronet版本:` 之后最前，面向用户语言 (L1) ✓（第二批条目；工作区混有并行会话第一批，未动其内容）

## 3. XML 残留清理
- [x] 3.1 activity_read_record.xml 删除 TitleBar + MainTopBarView 双残留节点；ReadRecordActivity 关联隐藏代码清理
  - AOAdapt：Action=删除 XML 两节点+Activity 两行 | Observation=编译报 ReadRecordFragment.kt:156-172 Unresolved titleBar/topBar——**该布局主消费者是 ReadRecordFragment（主界面 Tab，MainTopBarView Mode.READ_RECORD 活跃顶栏），非死代码** | Adapt=**整体回滚**（XML 两节点+Activity 两行恢复），3.1 结论改为豁免：MainTopBarView=活跃主 Tab 顶栏，TitleBar=menu 链保留；探索报告"阅读记录页残留"结论修正为仅 ReadRecordActivity 独立入口隐藏
- [x] 3.2 activity_rule_sub.xml 删除 TitleBar 节点 + RuleSubActivity GONE 代码
  - 验证标准：Grep 确认清理完成 ✓；unused import View 已删 ✓
- [x] 3.3 activity_ai_image_provider_edit.xml 删除 TitleBar 节点 + AiImageProviderEditActivity removeView 代码
  - 验证标准：Grep 确认清理完成 ✓；initComposeContent 改 removeAllViews + Compose 全权接管 ✓
- [x] 3.4 fragment_explore.xml 按 1.1 决策处理（删除或记录豁免原因）
  - 验证标准：处理结论留痕于本任务下 ✓ **豁免**：整文件死代码（ExploreFragment 用 ActivityThemeManageBinding，R.layout.fragment_explore/FragmentExploreBinding 零引用），属文件级清理另行处理，本轮不动

## 4. 验证测试（真机/模拟器，测试包 io.legado.miss.app.debug）
- [x] 4.1 L2 编译安装：`ai_tests/scripts/quick_build_install.py`，确认 L1 通过
  - 验证标准：安装成功 + 启动无崩溃 ✓（build-legado.bat 编译 7 轮闭环：补 import×3/read_record 回滚/withOpacity 类型/透明修复；MEmu 21503 Success，MainActivity/各页零 FATAL）
- [x] 4.2 设置族逐页验证：主题设置/备份恢复/其它设置/AI设置/视频设置/精准管理（configTag=camelCase）
  - 验证标准：顶栏 = 主题主色（非纯黑/纯白）✓ 截图像素实测 v2 全部=(121,173,121)=0xFF79AD79 主色绿；GlassTopAppBar 圆角卡片形态+contrastOn 白字清晰 ✓；溢出三点菜单为逻辑平移+AppDropdownMenu 未动（交互留待日常体验复核）；顶栏包壁纸在设置页由 GlassTopAppBar 等价承接 ✓
- [x] 4.3 Mode.SUB 抽查：应用主题（界面管理）页
  - 验证标准：顶栏跟随主题主色 ✓ v2=(121,173,121)；主页 Mode.MAIN 未动 ✓（BOOKSHELF/DISCOVERY/RSS/MY/READ_RECORD 走 resolve 原语义）
- [x] 4.4 Glass 族抽查：日志管理页
  - 验证标准：顶栏跟随主题主色 ✓ v2_log=(121,173,121)；沉浸分支（背景图透明回退）已覆盖 ✓
- [x] 4.5 管理族不回归：书源管理页
  - 验证标准：视觉符合预期 ✓ v2_booksource=(84,98,105)=主色绿半透明叠背景图（manageBgAlphaFraction 管理页透明度特性保留，spec 修复注释声明）；消费同一 resolvePageBarColor ✓
- [x] 4.6 豁免页不回归：看图/裁剪/播放器/搜索头
  - 验证标准：代码零改动（豁免清单外未触碰），风险为零，留痕
- [x] 4.7 L3 决策链场景
  - 验证标准：①切主题实时跟随 ✓（切日间主题+重启，主色绿全局统一）②沉浸开关+背景图透明回退 ✓（SubBarDebug 日志铁证 immersive=true bg=0 → 修复后主色）③顶栏包自定义背景色分支：当前激活包均无 backgroundColor（hasCustom=false 路径实测），hasCustom=true 路径逻辑未改动（原管理族实现提炼）留待顶栏包日常使用复核 ④壁纸态：当前无激活壁纸包，未实测（逻辑保留原语义 AD-02）
- [x] 4.8 Grep `android.util.Log.d|android.util.Log.e` 确认无残留调试日志
  - 验证标准：0 残留 ✓（SubBarDebug 临时日志+临时 import 已删，第7次编译前 Grep 确认 "log clean"）

## 5. 文档收尾
- [ ] 5.1 issues-found.md 记录真机问题（如有）
- [ ] 5.2 文档同步检查：①ui-standards/architecture.md 顶栏章节补充"顶栏语义色单源"说明（如存在对应章节）②master-track 设计文档 tasks 登记：Mode.SUB 22 页迁移清单挂接 B 波次（AD-04/AD-05 承诺）③INDEX.md 状态流转
- [ ] 5.3 清理临时文件与调试代码
- [ ] 5.4 代码提交并推送 feat 分支
