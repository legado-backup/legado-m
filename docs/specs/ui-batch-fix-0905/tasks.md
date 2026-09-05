# tasks.md — ui-batch-fix-0905

## 1. 准备工作
- [x] 1.1 确认分支与工作区干净（基于 origin/master 最新）
- [x] 1.2 备份待改核心文件到 bak 目录（MainActivity/VideoPlay/RssFragment/CrashHandler）

## 2. 核心实现

### 修复1：崩溃弹框回归
- [x] 2.1 MainActivity.kt：将 `showComposeConfirmDialog` 移回 `if (LocalConfig.appCrash)` 块内（[x] (L2)：T1 debug 会话弹框文案 0 出现+FATAL=0+重建复测 0）
- [x] 2.2 CrashHandler.kt：`saveCrashInfo2File` 两条静默 catch 补 `AppLog.put`（[x] (L1)：Grep 两处 catch 均含 AppLog.put）

### 修复2：视频书源沉浸式线路
- [x] 2.3 VideoPlay.kt initSource：volumes 空且 toc 非空时包装单线路 RssRoute("线路1") + RssEpisode 映射（[x] (L3)：T6 SwipeTest 铁证 flatFallback episodes=72 + rv_episodes 渲染 + epLikeTexts=6；isNewRoutesMode/switchBookRoute/playBookEpisode/saveRead 兼容核验通过）
- [x] 2.4 编译通过（assembleAppDebug，090523/090600 两轮）

### 修复3：发现页分组弹框 Bug
- [x] 2.5 复现与根因定位：ModernActionPopup.show L129 空分组静默返回（actions.isEmpty() → return previousPopup），用户场景 groups 空（enabledExplore=1 且 bookSourceGroup 非空的源为空集）→ 点击零反馈
- [x] 2.6 修复：ExploreFragment.showExploreGroupPopup 空分组补 toast"当前没有发现源分组"；非空路径不变（[x] (L2)：T4 legacy 发现页点击分组图标灰差 50.48，反馈生效；发现页模式 UI 通道切换+还原验证）

### 修复4：死菜单清理
- [x] 2.7 删除 rss_source_sel.xml `menu_check_rss_source`；删除 content_select_action.xml `menu_search_content/menu_browser/menu_share_str`；连带清理 TextActionMenu/ReadBookActivity 死分支与失效 import（[x] (L2)：T5 多选菜单无"校验所选订阅源"；Grep 4 个 id 全项目零残留；编译通过）

### 修复5：订阅头部收口
- [x] 2.8 RssFragment.kt 经典路径：`setActionsVisible(star=false, refresh=false, login=false)`；移除 3 个 addActionButton（[x] (L2)：T2 顶栏一级按钮 content-desc 全部消失，仅剩搜索+三点）
- [x] 2.9 moreButton 启用 + ModernActionPopup 6 项（阅读记录/收藏/刷新/订阅源管理/布局设置/分组管理）；删除 showGroupMenu 与分组信息列举（[x] (L2)：T3 菜单 6 项齐全、布局设置弹窗打开验证、FATAL=0；modern 形态经 setMode 自动隐藏三点，互不影响）

## 3. 验证测试
- [x] 3.1 编译：build-legado.bat（daemon 复用），构建前 Get-Process 校验
- [x] 3.2 updateLog.md：基于 git diff 三步流程追加（编译前完成）
- [x] 3.3 L2 真机（测试包 io.legado.miss.app.debug，脚本 l2_verify_ui_batch_fix_0905.py T1-T8 场景化，证据 ai_tests/reports/ui_batch_fix_0905/）：
  - [x] 3.3.1 崩溃弹框：debug 弹框文案 0 + FATAL=0 + HOME 重建复测 0（T1）
  - [x] 3.3.2 无卷视频书源沉浸式：rv_episodes 渲染 + 集数文本 + flatFallback=72 集（T6）；有卷书源回归（T7）
  - [x] 3.3.3 发现页分组反馈（T4）+ 书架/阅读记录弹窗机制同源未动（ModernActionPopup 公共层零修改）
  - [x] 3.3.4 订阅源管理多选菜单无死项（T5）
  - [x] 3.3.5 经典订阅头部收口 + 6 项菜单 + modern 不回归（T2/T3）
  - [x] 3.3.6 视频播放器深度回归（goal 三次强化）：传统布局真实播放（帧差 15.99）/选集切换第01→02→01 标题 hash 三次变化+真实播放（5.09/2.98）/沉浸式↔传统双向切换后集数+播放正常（4.73）；四错误模式（Malformed URL/destroy failed/ClassCastException/IllegalBlockSizeException）+FATAL 全日会话计数=0
- [x] 3.4 关联回归：verify_rss_sniff_after_download.py 执行 0/3——甄别为环境失真（recordLog 关→AppLog 空、无预下载视频、Compose 标题 u2 不可读），非本次回归（本次变更未触碰嗅探/switchToArticle 链路）；脚本已过时待后续治理
- [x] 3.5 临时日志治理：SwipeTest 2 处移除，Grep `android.util.Log.d|Log.e` 全项目 0 残留

## 4. 文档收尾
- [x] 4.1 同步关联文档（SOP 脚本表 16s 登记；INDEX.md 状态流转；issues-found 见 AOAdapt；经验见下方）
- [x] 4.2 移除临时日志/调试代码（见 3.5）
- [x] 4.3 清理 bak 备份与临时文件，提交变更

## AOAdapt 日志
- [x] 2.5 发现页分组弹框
  - Action: 静态分析 ModernActionPopup.show + flowExploreGroups SQL
  - Observation: L129 `actions.isEmpty() → return previousPopup` 静默；用户设备无启用发现分组源
  - Adapt: 空分组 toast 反馈（对齐用户"是 bug 要给反馈"要求），非空路径零改动
- [x] 3.3 T6 无卷视频书验证
  - Action: Intent 直唤播放器 + SwipeTest 埋点取证
  - Observation: 首轮 FAIL（rv_episodes 不渲染）→ 铁证 `hasBook=false, tocSize=0`：bookUrl 含 `&` 被 adb shell 远端截断 intent extra；另有模拟器 video_config 残留 layoutMode=1（用户手测残留）干扰
  - Adapt: 测试脚本 URL 单引号包裹重传 → tocSize=72/episodes=72 全链路 PASS；结论为测试脚本缺陷而非 App 缺陷
- [x] 3.3 T8 上一部/下一部
  - Action: 传统布局直接点击上下部按钮
  - Observation: Intent 直唤无书源队列注入 → 上一部/下一部按设计隐藏（无可切换目标）；截图证实传统布局渲染完整（播放器+选集列表+信息区）
  - Adapt: 改验证选集切换链路（同一采集/嗅探/播放链），订阅源用户路径上下部由既有 W3b/W4 用户真机验收覆盖
- [x] 3.4 嗅探脚本失真
  - Action: verify_rss_sniff_after_download.py 全流程执行
  - Observation: 0/3，三项 FAIL 均为脚本环境依赖（AppLog 空文件/无预下载视频/Compose 标题不可读）
  - Adapt: 判定脚本对当前 Compose 形态失真，登记为待治理项，不作为本次回归结论
