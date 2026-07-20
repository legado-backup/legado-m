# F-P0-8 订阅源统一搜索 测试用例（第二波覆盖）

> 订阅源统一搜索核心功能：跨源搜索、多源聚合、换源、搜索历史、搜索范围筛选

## 功能概述

订阅源统一搜索对标书架统一搜索，让用户在订阅源栏目首屏输入关键词即可跨源搜索所有支持搜索的订阅源内容，结果聚合展示，支持多源换源。

**入口**：RssFragment（订阅源栏目首屏）顶部搜索框 → onQueryTextSubmit 跳转 RssSearchActivity
**实现文件**：RssSearchActivity.kt + RssSearchViewModel.kt + RssSearchModel.kt + RssSearchAdapter.kt + ChangeRssArticleSourceDialog.kt + RssSearchSourceHolder.kt + RssSearchScope.kt + SearchRssArticle.kt
**修改文件**：RssFragment.kt（入口改造）+ SearchKeyword.kt/Dao + AppDatabase.kt + SearchViewModel.kt + ReadRss.kt + ReadRssActivity.kt + VideoPlayerActivity.kt + res/menu/rss_read.xml + res/menu/video_play.xml

## 测试环境

- 设备：MEmu 模拟器（Android 7.1+，已 root）
- 构建版本：appDebug
- Python 环境：`ai_tests/venv/Scripts/python.exe`（禁止公共 Python）
- 前置：导入至少 5 个订阅源，其中至少 3 个配置了 `searchUrl`（覆盖 HTTP/HTTPS、网页/图片/视频类型）
- Cronet 库：首次安装后必须等待 60 秒自动下载（HTTPS 源依赖）

---

## TC-F-P0-8-01：基础搜索流程（Level 1，P0 阻塞）

**关联源码**：RssSearchActivity.kt, RssSearchViewModel.kt, RssSearchModel.kt
**关联 Activity**：RssFragment → RssSearchActivity

**前置资源**：
[共享] 已导入 5 个订阅源，其中 3 个配置了 searchUrl

**测试步骤**：
1. 在订阅源栏目首屏（RssFragment）顶部搜索框输入"AI"
2. 点击搜索按钮（或回车）
3. 观察跳转 RssSearchActivity 后的行为
4. 等待搜索完成（≤35 秒）

**预期结果**：
- ✅ 跳转 RssSearchActivity，自动发起搜索
- ✅ RefreshProgressBar 顶部进度条显示
- ✅ 搜索结果实时填充到列表
- ✅ 搜索完成后进度条消失
- ✅ FloatingActionButton 搜索中显示停止图标，搜索完成后隐藏（AD-13）
- ✅ 不崩溃

## TC-F-P0-8-02：搜索结果展示字段（Level 1，P0 阻塞）

**关联源码**：RssSearchAdapter.kt, item_rss_search.xml
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已完成一次搜索，结果列表非空

**测试步骤**：
1. 观察搜索结果列表每个 item 的字段展示

**预期结果**：
- ✅ iv_cover 显示封面图片（80dp×80dp 圆角）
- ✅ tv_title 显示标题（16sp 加粗，最多 2 行）
- ✅ tv_description 显示描述（12sp，最多 2 行，空时隐藏）
- ✅ tv_pub_date 显示发布日期（12sp 斜体，单行，空时隐藏）
- ✅ bv_origin_count 在 origins.size ≥ 2 时显示源数量
- ✅ 已读文章标题灰色，未读正常色（FR-03.5）
- ✅ 图片加载失败时 iv_cover 隐藏（FR-03.6）
- ✅ 不崩溃

## TC-F-P0-8-03：多源换源流程（Level 1，P0 阻塞）

**关联源码**：ChangeRssArticleSourceDialog.kt, RssSearchSourceHolder.kt, ReadRss.kt
**关联 Activity**：RssSearchActivity → ReadRssActivity / VideoPlayerActivity

**前置资源**：
[共享] 搜索结果中存在 origins.size ≥ 2 的文章（多源聚合）

**测试步骤**：
1. 在搜索结果列表中找到 BadgeView 显示源数量 ≥ 2 的文章
2. 点击该文章进入详情页
3. 点击菜单 → 观察"换源"菜单项
4. 点击"换源" → 弹出 ChangeRssArticleSourceDialog
5. 选择另一个源
6. 观察详情页内容切换

**预期结果**：
- ✅ 详情页菜单显示"换源"项（RssSearchSourceHolder.articles.size > 1）
- ✅ ChangeRssArticleSourceDialog 列出所有来源（订阅源名称）
- ✅ 选择新源后详情页内容刷新
- ✅ 不崩溃

## TC-F-P0-8-04：搜索范围筛选 - 按分组（Level 1，P0 阻塞）

**关联源码**：RssSearchScope.kt, RssSearchActivity.onMenuOpened
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 订阅源有至少 2 个分组（如"科技"、"娱乐"）

**测试步骤**：
1. 进入 RssSearchActivity
2. 点击菜单 → 观察动态生成的分组列表
3. 选择某分组（如"科技"）
4. 输入关键词并搜索
5. 观察搜索结果
6. 重新点击菜单 → 选择"全部源"
7. 重新搜索

**预期结果**：
- ✅ 菜单展开时动态生成分组列表（已选分组带勾选，可选分组无勾选）
- ✅ 选择某分组后仅搜索该分组下配置了 searchUrl 的订阅源
- ✅ 选择"全部源"后清空已选分组，搜索全部
- ✅ 搜索范围持久化：退出 RssSearchActivity 重新进入，搜索范围保持
- ✅ 不崩溃

## TC-F-P0-8-05：搜索历史 - 增删查（Level 1，P0 阻塞）

**关联源码**：RssSearchHistoryAdapter.kt, RssSearchViewModel.kt, SearchKeywordDao.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已搜索过几个关键词（如"AI"、"机器学习"）

**测试步骤**：
1. 进入 RssSearchActivity（未输入关键词）
2. 点击搜索框获得焦点 → 观察历史关键词列表
3. 点击某个历史关键词 → 观察行为
4. 长按某个历史关键词 → 观察弹出菜单
5. 选择删除 → 观察列表更新
6. 点击"清空"按钮 → 确认清空 → 观察列表

**预期结果**：
- ✅ 搜索框获得焦点时显示 ll_input_help（仅搜索历史区域，无 tv_book_show/rv_bookshelf_search，AD-11）
- ✅ 历史关键词列表按时间倒序展示
- ✅ 点击历史关键词直接触发搜索（FR-08.3 简化，不检查书架）
- ✅ 长按弹出删除菜单
- ✅ 删除单条历史成功
- ✅ 清空全部历史后列表为空
- ✅ 不崩溃

## TC-F-P0-8-06：书源/订阅源搜索历史隔离（Level 1，P0 阻塞）

**关联源码**：SearchViewModel.kt, RssSearchViewModel.kt, SearchKeyword.kt
**关联 Activity**：SearchActivity, RssSearchActivity

**前置资源**：
[共享] App 同时有书源搜索历史和订阅源搜索历史

**测试步骤**：
1. 在书架搜索界面（SearchActivity）搜索几个关键词
2. 退出后观察书源搜索历史列表
3. 进入订阅源搜索界面（RssSearchActivity）搜索几个关键词
4. 退出后观察订阅源搜索历史列表
5. 在书源搜索界面清空历史
6. 重新进入订阅源搜索界面 → 观察订阅源搜索历史

**预期结果**：
- ✅ 书源搜索历史只显示书源关键词（type=0）
- ✅ 订阅源搜索历史只显示订阅源关键词（type=1）
- ✅ 书源清空历史后，订阅源搜索历史保持不变
- ✅ 反之亦然
- ✅ 不崩溃

## TC-F-P0-8-07：入口职责分离（Level 1，P0 阻塞）

**关联源码**：RssFragment.kt, RssSourceActivity.kt
**关联 Activity**：RssFragment, RssSourceActivity

**前置资源**：
[共享] 订阅源栏目有多个订阅源（部分名称含"科"）

**测试步骤**：
1. 在订阅源栏目首屏（RssFragment）搜索框输入"科"（不点击搜索按钮）
2. 观察订阅源列表变化
3. 点击搜索按钮
4. 观察是否跳转 RssSearchActivity
5. 返回 RssFragment → 点击菜单"订阅源管理"进入 RssSourceActivity
6. 在 RssSourceActivity 顶部搜索框输入"科"
7. 观察订阅源列表变化

**预期结果**：
- ✅ RssFragment 首屏输入"科"时实时过滤订阅源列表（onQueryTextChange 保留）
- ✅ 点击搜索按钮跳转 RssSearchActivity（onQueryTextSubmit 改造）
- ✅ RssSourceActivity 设置页输入"科"时按名称过滤（原功能不变）
- ✅ queryHint 在 RssFragment 显示"搜索订阅源内容"
- ✅ queryHint 在 RssSourceActivity 显示"搜索订阅源"（不变）
- ✅ 不崩溃

## TC-F-P0-8-08：数据库 Migration 98→99（Level 1，P0 阻塞）

**关联源码**：AppDatabase.kt, SearchKeyword.kt, DatabaseMigrations.kt
**关联 Activity**：无（数据库层）

**前置资源**：
[共享] 旧版本 App（version=98）已安装，有书源搜索历史数据

**测试步骤**：
1. 在旧版本 App 中搜索几个书源关键词（生成 SearchKeyword 数据）
2. 覆盖安装新版本 App（version=99）
3. 启动 App → 观察启动日志
4. 进入书源搜索界面 → 观察历史关键词
5. 进入订阅源搜索界面 → 观察历史关键词

**预期结果**：
- ✅ App 启动不崩溃（Migration SQL 表名 search_keywords 正确）
- ✅ 旧版书源搜索历史保留，type=0（默认值）
- ✅ 书源搜索历史可正常显示
- ✅ 订阅源搜索历史初始为空
- ✅ 不崩溃

## TC-F-P0-8-09：搜索失败容错（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt, Rss.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 3 个支持搜索的订阅源中 1 个网络不通（关闭网络或使用无效 URL）

**测试步骤**：
1. 输入关键词"AI"并搜索
2. 等待搜索完成（30 秒超时）
3. 观察搜索结果和日志

**预期结果**：
- ✅ 1 个订阅源超时后其他 2 个源结果正常展示
- ✅ 无崩溃
- ✅ 日志记录超时源的异常信息（AppLog.put）
- ✅ 搜索总耗时 ≤ 35 秒（30 秒超时 + 5 秒聚合开销）

## TC-F-P0-8-10：不支持搜索的订阅源被排除（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 5 个订阅源中 2 个未配置 searchUrl

**测试步骤**：
1. 输入关键词搜索
2. 观察搜索过程
3. 查看日志确认搜索的源数量

**预期结果**：
- ✅ 系统仅调用 3 个配置了 searchUrl 的订阅源
- ✅ 2 个未配置 searchUrl 的订阅源被排除
- ✅ 搜索过程不报错
- ✅ 不崩溃

## TC-F-P0-8-11：视频文章换源限制（Level 2，P1 关键）

**关联源码**：ReadRss.kt, VideoPlayerActivity.kt, VideoPlay.kt
**关联 Activity**：RssSearchActivity → VideoPlayerActivity

**前置资源**：
[共享] 搜索视频订阅源，结果中含视频文章（type=2）

**测试步骤**：
1. 搜索视频订阅源 → 点击视频文章进入播放器
2. 尝试上下滑动切换文章
3. 在视频播放器中点击"换源" → 选择新源
4. 切换后再次尝试上下滑动

**预期结果**：
- ✅ 进入视频播放器后无法上下滑动切换文章（rssArticles=null，FR-04.5）
- ✅ 点击"换源"可切换源
- ✅ 切换后仍无法上下滑动切换文章
- ✅ 不崩溃

## TC-F-P0-8-12：RssSearchActivity 交互细节（Level 2，P1 关键）

**关联源码**：RssSearchActivity.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] App 已安装，可进入 RssSearchActivity

**测试步骤**：
1. 进入 RssSearchActivity → 点击搜索框
2. 观察 ll_input_help 显示
3. 输入关键词（不提交）→ 观察行为
4. 提交搜索 → 等待完成
5. 点击搜索框失焦 → 观察 ll_input_help
6. 点击菜单 → 观察菜单项
7. 按返回键第一次 → 观察焦点
8. 按返回键第二次 → 观察 Activity 是否 finish

**预期结果**：
- ✅ ll_input_help 只显示搜索历史区域，不显示 tv_book_show/rv_bookshelf_search（AD-11）
- ✅ 搜索框获焦显示 ll_input_help，失焦且有搜索结果时隐藏（FR-08.9）
- ✅ 输入时停止当前搜索 + 隐藏 FAB + 更新历史关键词（FR-08.2）
- ✅ 菜单不包含"精度搜索"项（AD-14）
- ✅ 菜单包含"搜索范围"、"订阅源管理"、"日志"项
- ✅ 第一次按返回键清搜索框焦点，第二次按返回键真正 finish（FR-08.7）
- ✅ 滚动到底部不会触发加载更多（AD-15）
- ✅ 不崩溃

## TC-F-P0-8-13：搜索结果为空的处理（Level 2，P1 关键）

**关联源码**：RssSearchActivity.kt, RssSearchViewModel.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 订阅源有至少 2 个分组

**测试步骤**：
1. 搜索范围设为"全部源" → 搜索一个不可能存在的关键词（如"zzzzz"）
2. 观察空状态展示
3. 搜索范围设为某分组 → 搜索同样关键词
4. 观察是否弹出对话框
5. 点击对话框"是" → 观察切换
6. 重复步骤 3-4 → 点击对话框"否" → 观察行为

**预期结果**：
- ✅ 范围"全部"且空 → 列表区域显示"无搜索结果"提示，不弹对话框（FR-08.5）
- ✅ 范围某分组且空 → 弹出"是否切换到全部分组？"对话框
- ✅ 点击"是" → 切换到全部分组并重新搜索
- ✅ 点击"否" → 保持当前分组，不重新搜索
- ✅ 不崩溃

## TC-F-P0-8-14：详情页换源菜单回归测试（Level 2，P1 关键）

**关联源码**：ReadRssActivity.kt, VideoPlayerActivity.kt, RssSearchSourceHolder.kt
**关联 Activity**：RssSortActivity → ReadRssActivity / VideoPlayerActivity

**前置资源**：
[共享] 订阅源栏目有支持文章阅读/视频播放的订阅源

**测试步骤**：
1. 从 RssSortActivity（订阅源文章列表）进入文章详情页
2. 点击菜单 → 观察"换源"菜单项是否显示
3. 退出 → 从 RssSearchActivity 进入详情页 → 观察换源菜单
4. 退出详情页 → 再次从 RssSortActivity 进入 → 观察换源菜单

**预期结果**：
- ✅ 从 RssSortActivity 进入详情页时，换源菜单**不显示**（RssSearchSourceHolder.articles == null）
- ✅ 从 RssSearchActivity 进入详情页时，换源菜单显示（articles.size > 1）
- ✅ 退出详情页后再次从 RssSortActivity 进入，换源菜单不显示（onDestroy 已清理 articles）
- ✅ 不崩溃

## TC-F-P0-8-15：内存泄漏测试 - RssSearchSourceHolder 清理（Level 2，P1 关键）

**关联源码**：RssSearchSourceHolder.kt, ReadRssActivity.kt, VideoPlayerActivity.kt
**关联 Activity**：ReadRssActivity, VideoPlayerActivity

**前置资源**：
[共享] 从 RssSearchActivity 进入详情页（已设置 RssSearchSourceHolder.articles）

**测试步骤**：
1. 从 RssSearchActivity 进入详情页
2. 退出详情页（onDestroy 触发）
3. 通过 Profiler 或日志检查 RssSearchSourceHolder.articles 状态

**预期结果**：
- ✅ 详情页 onDestroy 后 RssSearchSourceHolder.articles == null（避免内存泄漏）
- ✅ 不崩溃

## TC-F-P0-8-16：并发安全 - 快速切换搜索关键词（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt, RssSearchViewModel.kt, ConflateLiveData
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已进入 RssSearchActivity

**测试步骤**：
1. 快速输入关键词"AI" → 立即输入"机器学习" → 立即输入"深度学习"
2. 观察搜索行为
3. 搜索中快速点击 FAB 停止/恢复多次
4. 观察行为

**预期结果**：
- ✅ 快速切换关键词时停止前一个搜索，启动新搜索（viewModel.stop()）
- ✅ FAB 显示状态正确（搜索中显示，搜索完成隐藏）
- ✅ ConflateLiveData 防抖生效，UI 不卡顿
- ✅ 无崩溃、无 ANR

## TC-F-P0-8-17：边界条件 - 空关键词和特殊字符（Level 3，P2 一般）

**关联源码**：RssSearchActivity.kt, RssSearchViewModel.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已进入 RssSearchActivity

**测试步骤**：
1. 输入空字符串 → 点击搜索按钮
2. 输入仅空格 → 点击搜索按钮
3. 输入超长关键词（200+ 字符）
4. 输入特殊字符（如 `' OR 1=1 --`、`<script>`、emoji）
5. 观察行为

**预期结果**：
- ✅ 空关键词被拒绝（不发起搜索）
- ✅ 仅空格被 trim 后拒绝
- ✅ 超长关键词正常搜索（不崩溃，可能无结果）
- ✅ 特殊字符关键词正常搜索（不崩溃，SQL 注入字符被转义）
- ✅ emoji 关键词正常搜索

## TC-F-P0-8-18：边界条件 - 0/1/大量订阅源（Level 3，P2 一般）

**关联源码**：RssSearchModel.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 可控制订阅源数量

**测试步骤**：
1. 删除所有支持搜索的订阅源（保留 0 个）→ 搜索关键词
2. 仅保留 1 个支持搜索的订阅源 → 搜索关键词
3. 导入大量订阅源（50+ 个支持搜索）→ 搜索关键词

**预期结果**：
- ✅ 0 个支持搜索的源 → 提示"启用订阅源为空或无 searchUrl"（NoStackTraceException）
- ✅ 1 个支持搜索的源 → 正常搜索，结果列表显示
- ✅ 50+ 个支持搜索的源 → 并发受 threadCount 控制（AppConfig.threadCount），不崩溃
- ✅ 不崩溃

## TC-F-P0-8-19：性能 - 搜索响应时间和内存（Level 3，P2 一般）

**关联源码**：RssSearchModel.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 5 个支持搜索的订阅源（含 HTTPS 源）

**测试步骤**：
1. 使用 Profiler 监控内存
2. 输入关键词搜索 → 记录开始时间
3. 等待搜索完成 → 记录结束时间
4. 计算搜索总耗时
5. 检查内存占用增量

**预期结果**：
- ✅ 搜索总耗时 ≤ 35 秒（NFR-01）
- ✅ 内存占用增量 ≤ 50MB（NFR-01，结果 ≤ 500 条）
- ✅ 不崩溃

## TC-F-P0-8-20：Cronet 库预下载检查（Level 1，P0 阻塞）

**关联源码**：无（环境依赖）
**关联 Activity**：无

**前置资源**：
[共享] 模拟器首次安装 App（或重置后重装）

**测试步骤**：
1. 安装新版本 App
2. 启动 App 等待 60 秒（触发 Cronet 库自动下载）
3. 执行诊断脚本检查 Cronet 库可用性
4. 搜索含 HTTPS 源的关键词
5. 观察 HTTPS 源是否能正常返回结果

**预期结果**：
- ✅ Cronet 库文件存在（`/data/data/io.legado.app/files/cronet/libcronet.so`）
- ✅ logcat 无 `libcronet.so FileNotFoundException`
- ✅ HTTPS 源搜索结果正常返回
- ✅ 不崩溃

## TC-F-P0-8-21：日志分析 - 错误模式验证（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt, AppLog
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已完成多次搜索操作

**测试步骤**：
1. 完成多次搜索（含正常、失败、空结果场景）
2. 使用 logcat 抓取日志
3. 分析日志中的错误模式

**预期结果**：
- ✅ logcat 无 `ClassCastException`（详情页换源类型兼容）
- ✅ logcat 无 `IllegalBlockSizeException`（加密相关）
- ✅ logcat 无 `Malformed URL`（searchUrl 格式正确）
- ✅ logcat 无 `NullPointerException`（关键路径）
- ✅ 失败源的异常被 AppLog.put 记录但不崩溃

## TC-F-P0-8-22：回归测试 - 书源搜索功能不受影响（Level 1，P0 阻塞）

**关联源码**：SearchActivity.kt, SearchViewModel.kt, SearchModel.kt
**关联 Activity**：SearchActivity

**前置资源**：
[共享] App 已安装新版（含订阅源统一搜索改动）

**测试步骤**：
1. 进入书架搜索界面（SearchActivity）
2. 搜索几个书源关键词
3. 观察搜索结果
4. 查看书源搜索历史
5. 清空书源搜索历史

**预期结果**：
- ✅ 书源搜索功能正常（结果展示、换源、详情跳转）
- ✅ 书源搜索历史显示正确（type=0）
- ✅ 清空书源搜索历史不影响订阅源搜索历史
- ✅ 不崩溃

## TC-F-P0-8-23：回归测试 - 单源搜索功能不受影响（Level 1，P0 阻塞）

**关联源码**：RssSortActivity.kt
**关联 Activity**：RssSortActivity

**前置资源**：
[共享] 有支持搜索的订阅源

**测试步骤**：
1. 进入订阅源栏目 → 点击某订阅源进入 RssSortActivity
2. 点击菜单 `R.id.menu_search` → 输入关键词搜索
3. 观察单源搜索结果

**预期结果**：
- ✅ 单源搜索功能正常（菜单 `R.id.menu_search` 未被修改）
- ✅ 搜索结果正常展示
- ✅ 不崩溃

## TC-F-P0-8-24：回归测试 - 订阅源管理页搜索不受影响（Level 1，P0 阻塞）

**关联源码**：RssSourceActivity.kt
**关联 Activity**：RssSourceActivity

**前置资源**：
[共享] 订阅源栏目有多个订阅源

**测试步骤**：
1. 进入订阅源栏目 → 点击菜单"订阅源管理"进入 RssSourceActivity
2. 在顶部搜索框输入"科"
3. 观察订阅源列表变化

**预期结果**：
- ✅ RssSourceActivity 按名称过滤功能正常（原功能不变，AD-04）
- ✅ queryHint 显示"搜索订阅源"（不变）
- ✅ 不崩溃

## TC-F-P0-8-25：搜索结果排序策略（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt#mergeItems
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已导入至少 2 个配置 searchUrl 的订阅源，且搜索结果中存在：
- 标题完全匹配关键词的文章（至少 1 条）
- 标题包含关键词的文章（至少 1 条）
- 标题不含关键词的文章（至少 1 条，因订阅源自身规则匹配）

**测试步骤**：
1. 在 RssSearchActivity 搜索关键词"AI"
2. 等待搜索完成
3. 观察搜索结果列表的顺序

**预期结果**：
- ✅ 标题完全匹配"AI"的文章排在最前（equalData 组）
- ✅ 标题包含"AI"的文章排在中间（containsData 组）
- ✅ 其他文章排在最后（otherData 组）
- ✅ 组内按 origins.size 降序排列（多源文章靠前）

**自动化级别**：B 轨 Python（半自动 - 需人工观察排序结果）

## TC-F-P0-8-26：去重 key 边界测试（Level 2，P1 关键）

**关联源码**：SearchRssArticle.kt#deduplicationKey, RssSearchModel.kt#mergeItems
**关联 Activity**：RssSearchActivity

**前置资源**：
[专用] 2 个订阅源配置相同 searchUrl（同源数据），且返回的文章中存在：
- 标题相同 + pubDate 相同的文章（应聚合）
- 标题相同 + pubDate 为空的文章（应聚合，key=`"标题|"`)
- 标题相同 + pubDate 不同（不应聚合，视为不同文章）
- 标题大小写不同但内容相同（不应聚合，大小写敏感）

**测试步骤**：
1. 导入 2 个相同 searchUrl 的订阅源（不同 sourceUrl 但同 searchUrl）
2. 搜索关键词触发搜索
3. 观察搜索结果中的 BadgeView 源数量

**预期结果**：
- ✅ 标题相同 + pubDate 相同的文章 BadgeView 显示 2（聚合成功）
- ✅ 标题相同 + pubDate 为空的文章 BadgeView 显示 2（聚合成功，key=`"标题|"`)
- ✅ 标题相同 + pubDate 不同的文章显示为 2 个独立条目（不聚合）
- ✅ 标题大小写不同的文章显示为 2 个独立条目（不聚合）

**自动化级别**：A 轨 MD（人工执行 - 需准备专用数据）

## TC-F-P0-8-27：异常数据容错（Level 2，P1 关键）

**关联源码**：RssSearchModel.kt#mergeItems, RssSearchAdapter.kt#convert
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已导入订阅源，搜索结果包含以下异常数据：
- 标题为空字符串的文章
- pubDate 为 null 的文章
- description 为 null 的文章
- image 为空字符串或非法 URL 的文章
- type 字段异常（非 0/1/2）的文章

**测试步骤**：
1. 在 RssSearchActivity 搜索关键词
2. 等待搜索完成
3. 观察异常数据文章的显示情况

**预期结果**：
- ✅ 标题为空的文章不崩溃，tv_title 显示空或占位
- ✅ pubDate 为 null 的文章不崩溃，tv_pub_date gone()
- ✅ description 为 null 的文章不崩溃，tv_description gone()
- ✅ image 为空/非法的文章不崩溃，iv_cover 显示占位图或 gone()
- ✅ type 异常的文章不崩溃，按默认 type=0 处理（进入 ReadRssActivity）
- ✅ 搜索过程不崩溃，不卡死

**自动化级别**：B 轨 Python（半自动 - 需人工观察显示效果）

## TC-F-P0-8-28：UI 适配测试（Level 3，P2 一般）

**关联源码**：activity_rss_search.xml, item_rss_search.xml, RssSearchAdapter.kt
**关联 Activity**：RssSearchActivity

**前置资源**：
[共享] 已导入订阅源，搜索结果至少 10 条

**测试步骤**：
1. 在不同屏幕尺寸下打开 RssSearchActivity（手机/平板/横屏）
2. 调整系统字体大小（小/默认/大/最大）
3. 调整系统主题（日间/夜间）
4. 观察搜索结果列表的显示效果

**预期结果**：
- ✅ 手机竖屏：item 布局正确显示（图片 80dp + 标题/描述/日期）
- ✅ 平板/横屏：item 布局不变形（不强制拉伸）
- ✅ 字体放大：标题/描述/日期不溢出，maxLines 生效
- ✅ 夜间模式：文字颜色自适应，图片不变黑
- ✅ BadgeView 右上角位置正确，不遮挡标题
- ✅ 长标题（最多 2 行）正确省略显示
- ✅ 长描述（最多 2 行）正确省略显示

**自动化级别**：A 轨 MD（人工执行 - 需多设备/多配置验证）

---

## 自动化级别说明（优化点 13 修复）

| 级别 | 含义 | 执行方式 |
|------|------|---------|
| A 轨 MD | 人工执行用例 | 测试人员按 MD 步骤手动执行，记录结果 |
| B 轨 Python | 半自动用例 | Python 脚本辅助（如导入数据、触发操作），人工观察结果 |
| 全自动 | 完全脚本化 | Python 脚本全自动执行 + 断言（本次需求暂无） |

> 当前 28 个 TC 中：
> - A 轨 MD：TC-03/11/17/22/23/24/26/28（8 个，需人工操作或多设备验证）
> - B 轨 Python：TC-01/02/04/05/06/07/08/09/10/12/13/14/15/16/18/19/20/21/25/27（20 个，脚本辅助）
> - 全自动：0 个（订阅源搜索 UI 强相关，暂不适合全自动）
