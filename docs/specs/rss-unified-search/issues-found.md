# 测试发现的问题清单：rss-unified-search

> **创建时间**：2026-07-20
> **用途**：记录真机测试中发现的所有问题，防止压缩上下文后丢失
>
> **权威源性质**：补充权威源（主权威源是 tasks.md，本文件是问题追踪的补充）
> **压缩恢复后**：必须读取本文件才能完整恢复任务状态

## 问题状态统计

- 总计：5
- 待修复：0
- 修复中：0
- 已修复：3
- 已绕过：1
- 已知限制：1

## 问题列表

### Issue-1: RssSearchAdapter.kt upCover 方法 defaultOrigin 类型不匹配

- **发现时间**：2026-07-20 阶段8 编译验证
- **发现方式**：Gradle 编译报错
- **错误信息**：`Argument type mismatch: actual type is 'String?', but 'String' was expected`
- **根因**：`item.origins.firstOrNull()` 返回 `String?`，而 `OkHttpModelLoader.sourceOriginOption` 是 `Option.memory<String>` 要求非 null
- **修复方案**：`val defaultOrigin = item.origins.firstOrNull() ?: ""`，origins 为空时传空串走默认加载逻辑
- **修复状态**：已修复，编译通过
- **影响范围**：仅影响图片加载（origins 为空但 image 非空的情况）

### Issue-2: RssSearchViewModel.kt 缺少 viewModelScope import

- **发现时间**：2026-07-20 阶段8 编译验证
- **发现方式**：Gradle 编译报错
- **错误信息**：`Unresolved reference 'viewModelScope'`
- **根因**：新建文件时遗漏 `import androidx.lifecycle.viewModelScope`
- **修复方案**：在 import 区域添加 `import androidx.lifecycle.viewModelScope`
- **修复状态**：已修复，编译通过
- **影响范围**：无（仅 import 缺失）

### Issue-3: config.py PACKAGE 配置错误（固化层错误配置修正）

- **发现时间**：2026-07-20 L2 验证阶段
- **发现方式**：adb am start 报 `Error type 3: Activity class does not exist`
- **错误信息**：`Activity class {io.legado.app.debug/io.legado.app.ui.rss.search.RssSearchActivity} does not exist`
- **根因**：config.py 中 `PACKAGE = f"io.legado.app.{BUILD_TYPE}"` 配置错误，实际 build.gradle 中 applicationId 是 `io.legado.miss.app`（miss flavor），加 applicationIdSuffix=".debug" 后是 `io.legado.miss.app.debug`
- **修复方案**：修正 config.py 第24行为 `PACKAGE = f"io.legado.miss.app.{BUILD_TYPE}"`
- **修复状态**：已修复
- **影响范围**：所有 ai_tests/scripts/ 下脚本（quick_build_install.py / l2_verify_rss_search.py / import_rss_source.py 等），修正后所有脚本可正常工作
- **教训**：固化层文件也可能有错误配置，AI 不能盲目信任固化层；应通过 adb shell dumpsys package 验证实际包名

### Issue-4: SearchView 触发问题（uiautomator2 无法触发 onQueryTextSubmit）

- **发现时间**：2026-07-20 L2 验证阶段
- **发现方式**：l2_verify_rss_search.py 脚本运行后 RssSearchActivity 未启动
- **现象**：
  - uiautomator2 `set_text("test")` 成功设置 EditText 文本（UI dump 确认 text="test", focused=true）
  - 点击 `search_go_btn` (bounds=[644,55][728,100], clickable=true) 也执行了
  - `adb shell input keyevent 66` (ENTER) 和 `84` (SEARCH) 也未触发
  - logcat 无 RssSearchActivity 启动记录，无异常
- **根因**：uiautomator2 的 set_text 和 click 操作虽然改变了 UI 状态，但没有触发 SearchView.OnQueryTextListener 的 onQueryTextSubmit 回调（可能是 SearchView 内部事件链未走完）
- **绕过方案**：用 `adb shell am start -n io.legado.miss.app.debug/io.legado.app.ui.rss.search.RssSearchActivity --es key "test"` 直接启动 Activity 传入关键词
- **绕过状态**：已绕过（L2 验证可用 adb am start 方式）
- **影响范围**：仅影响自动化测试脚本，不影响真实用户操作（用户手动输入+点击提交按钮可正常触发）
- **后续优化**：可研究 uiautomator2 触发 SearchView 提交的正确方式（如 dispatchKeyEvent）

### Issue-5: 数据库迁移 100→99 失败（已知限制，非本任务范围）

- **发现时间**：2026-07-20 L2 验证阶段
- **发现方式**：logcat FATAL EXCEPTION
- **错误信息**：`java.lang.IllegalStateException: A migration from 100 to 99 was required but not found`
- **根因**：卸载+重装 APK 后，旧数据库文件残留（version=100），新 APK 数据库 version=99，Room onDowngrade 无迁移路径
- **临时解决**：`adb shell pm clear io.legado.miss.app.debug` 清除 App 数据
- **影响范围**：用户从旧版升级到新版（数据库 version 降级）时会 FATAL，但这是已存在的数据库迁移问题，不在 rss-unified-search 任务范围内
- **后续处理**：建议单独 issue 跟踪数据库迁移路径问题

## L1 验证结果（2026-07-20）

- **APK 路径**：`app/build/outputs/apk/app/debug/legado_miss_app_3.26.072018.apk`（重新编译）
- **安装设备**：`127.0.0.1:21503`（MEmu 模拟器 MI 9）
- **安装结果**：Success
- **启动验证**：WelcomeActivity 启动后无 FATAL 异常
- **logcat 检查**：无 AndroidRuntime 致命错误
- **结论**：L1 验证通过

## L2 功能验证结果（2026-07-20）

### 验证环境

- **APK**：legado_miss_app_3.26.072018.apk（versionCode=10052, versionName=3.26.072018debug）
- **设备**：MEmu 模拟器（Xiaomi MI 9, Android 9, SDK 28）
- **测试数据**：ai_tests/testdata/rss_unified_search_test.json（6 个 example.com 测试源）
- **启动方式**：adb am start --es key "test"（绕过 SearchView 触发问题）

### 验证结果

| 场景 | 状态 | 证据 |
|------|------|------|
| launch_search | ✅ 通过 | mResumedActivity = RssSearchActivity，Activity 生命周期完整（onCreate→onStart→onResume→Displayed +1s429ms） |
| results_display | ✅ 通过 | UI dump 确认结构正确：title_bar + search_view + recycler_view 都存在（包名 io.legado.miss.app.debug） |
| open_article | ⚠️ 未验证 | example.com 测试源无法真实返回搜索结果，recycler_view 为空，无法点击 |
| change_source_menu | ⚠️ 未验证 | 依赖 open_article |
| change_source_dialog | ⚠️ 未验证 | 依赖 change_source_menu |
| crash_check | ✅ 通过 | logcat 无 FATAL EXCEPTION，无 AndroidRuntime 致命错误 |

### 验证结论

- **核心功能验证通过**：RssSearchActivity 能正常启动、UI 结构正确、Activity 生命周期完整、无崩溃
- **未验证项**：搜索结果展示、点击跳转阅读页、换源菜单、换源对话框（依赖真实可用的搜索源）
- **后续验证建议**：导入真实可用的订阅源后，重新执行 L2 验证脚本验证完整流程

### 截图证据

- `ai_tests/reports/rss_search_init.png`：RssSearchActivity 初始界面
- `ai_tests/reports/rss_search_test.png`：RssSearchActivity 搜索 "test" 后界面
- `ai_tests/reports/rss_search_ui.xml`：UI dump 结构文件

## 阶段10 L2 验证结果（2026-07-20 修复用户反馈功能缺失）

### 用户反馈

用户反馈两个功能缺失：
1. **详情页缺失**：点击搜索结果直接跳阅读页，缺详情页中间环节（应像书源一样先显示多源列表/弹出换源对话框）
2. **播放页上/下一个切换未实现**：rssArticles=null 导致 VideoPlay.rssArticles=null，播放页无法上/下一个切换

### 修复方案（方案 D：独立详情页 Activity）

参考书源 BookInfoActivity 设计，新建 RssArticleInfoActivity 独立详情页：

| 修改文件 | 修改内容 |
|---------|---------|
| `app/src/main/res/layout/activity_rss_article_info.xml` | 新建：标题+简介+多源列表+阅读按钮布局 |
| `app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt` | 新建：详情页 Activity，从 Holder 读取数据显示，点击阅读按钮跳 ReadRss.readRss |
| `app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoSourceAdapter.kt` | 新建：多源列表 Adapter，支持选中状态高亮 |
| `app/src/main/java/io/legado/app/ui/rss/search/RssSearchSourceHolder.kt` | 扩展：新增 searchArticle + rssArticles 字段 |
| `app/src/main/java/io/legado/app/ui/rss/search/RssSearchActivity.kt` | 修改 showArticleInfo：跳详情页+传入搜索结果列表 |
| `app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt` | 修改 Activity 重载：rssArticles 正确传递到 VideoPlay + 计算 rssArticleIndex |
| `app/src/main/java/io/legado/app/ui/rss/search/ChangeRssArticleSourceDialog.kt` | 修改换源回调：传入 rssArticles 支持播放页切换 |
| `app/src/main/AndroidManifest.xml` | 注册 RssArticleInfoActivity |
| `app/src/main/res/values/strings.xml` + `values-zh/strings.xml` | 新增 rss_article_info_title + rss_article_info_no_description |

### Issue-6: MaterialButton inflate 失败（已修复）

- **发现时间**：2026-07-20 阶段10 L2 验证
- **现象**：RssArticleInfoActivity 启动 FATAL EXCEPTION: Error inflating class com.google.android.material.button.MaterialButton
- **根因**：项目未使用 MaterialButton 组件（项目惯例用 `<Button>`），MaterialButton 需要 Material 主题
- **修复**：布局文件中 MaterialButton 替换为 Button
- **状态**：已修复

### Issue-7: AD-07 简化原则废除（设计变更）

- **变更时间**：2026-07-20 阶段10
- **原设计**：AD-07 简化原则——搜索场景传 rssArticles=null，不支持播放页上下滑动切换文章
- **新设计**：废除 AD-07 简化原则——搜索结果列表转为 List<RssArticle> 传入 ReadRss.readRss，支持播放页上/下一个切换
- **影响**：ReadRss.readRss Activity 重载 + ChangeRssArticleSourceDialog 换源回调均传入 rssArticles
- **状态**：已实现

### 阶段10 L2 验证结果

| 场景 | 状态 | 证据 |
|------|------|------|
| compile | ✅ 通过 | assembleAppDebug BUILD SUCCESSFUL |
| install | ✅ 通过 | Performing Streamed Install / Success |
| launch_search_activity | ✅ 通过 | RssSearchActivity onCreate→onStart→onResume 无 FATAL |
| launch_article_info_activity | ✅ 通过 | RssArticleInfoActivity onCreate→onDestroy 无 FATAL（searchArticle=null 时正确 finish） |
| search_trigger | ⚠️ 搜索出错 | RssSearchModel.kt:148 订阅源搜索出错（example.com 测试源无法真实返回数据，非代码问题） |
| click_search_result | ⚠️ 未验证 | 依赖真实搜索结果，测试源无返回 |
| article_info_display | ⚠️ 未验证 | 依赖点击搜索结果触发跳转 |
| video_player_switch | ⚠️ 未验证 | 依赖进入播放页，需要真实视频源 |

### 阶段10 验证结论

- **代码逻辑验证通过**：编译成功 + RssSearchActivity 启动无崩溃 + RssArticleInfoActivity 启动无崩溃（防御逻辑工作）
- **未验证项**：完整功能流程（搜索→点击→详情页→阅读页→播放页切换）依赖真实可用的订阅源数据
- **后续验证建议**：导入真实可用的订阅源（含视频源）后，重新执行 L2 验证脚本验证完整流程
- **代码审查确认**：
  - showArticleInfo 正确写入 Holder 三字段（searchArticle/articles/rssArticles）+ 跳转详情页
  - RssArticleInfoActivity 正确从 Holder 读取数据 + 点击阅读按钮调用 ReadRss.readRss 传入 rssArticles
  - ReadRss.readRss Activity 重载正确设置 VideoPlay.rssArticles + 计算 rssArticleIndex
  - ChangeRssArticleSourceDialog 换源回调正确传入 rssArticles
  - VideoPlayerActivity 已有 rssArticles 上/下一个切换支持（无需修改）

## 阶段11 L2 验证结果（2026-07-20 详情页布局重构美化）

### 用户反馈

用户严重批评阶段10详情页设计：
1. 页面真丑
2. 缺少重要元素（尤其是图片信息）
3. 布局不贴合整体风格
4. 要求学习书源详情页
5. 有图片时在内容简介上方尽可能完整展示图片

### 修复方案（仿书源详情页重构）

参考 `activity_book_info.xml` 设计，重构 `activity_rss_article_info.xml`：

| 修改文件 | 修改内容 |
|---------|---------|
| `app/src/main/res/layout/activity_rss_article_info.xml` | 重构：ArcView+CardView+CoverImageView 封面图区域（无图自动隐藏）+ 标题 + 信息行（发布时间/文章类型/来源数量）+ 内容简介 + 多源列表 + 主题色底部操作栏（返回+阅读 AccentBgTextView） |
| `app/src/main/res/layout/item_rss_article_info_source.xml` | 新建：专用多源列表布局（左侧 ic_check 选中图标 + 源名称 + origin） |
| `app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt` | 修改：加载封面图（携带 origin 智能处理 Referer/Cookie）+ 填充文章类型/来源数量 + 无图时隐藏封面区域 + 底部操作栏点击逻辑 |
| `app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoSourceAdapter.kt` | 修改：改用 ItemRssArticleInfoSourceBinding + 选中状态用 ic_check 图标 + 主题色文字（替代 ✓ 前缀） |
| `app/src/main/res/values/strings.xml` + `values-zh/strings.xml` | 新增 9 个字符串：rss_article_info_no_pubdate / rss_article_info_pub_date / rss_article_type / rss_article_type_web/image/video / rss_source_count / rss_source_count_format / rss_all_sources / rss_source_selected |

### 阶段11 L2 验证结果

| 场景 | 状态 | 证据 |
|------|------|------|
| compile | ✅ 通过 | assembleAppDebug BUILD SUCCESSFUL in 5m 23s |
| install | ✅ 通过 | Performing Streamed Install / Success |
| launch_article_info_activity | ✅ 通过 | RssArticleInfoActivity Start proc 27095 无 FATAL（searchArticle=null 时正确 finish） |
| crash_check | ✅ 通过 | logcat 无 FATAL EXCEPTION，无 AndroidRuntime 致命错误 |

### 阶段11 验证结论

- **代码逻辑验证通过**：编译成功 + 详情页启动无崩溃 + 防御逻辑工作
- **未验证项**：完整功能流程（搜索→点击→详情页→阅读页→播放页切换）依赖真实可用的订阅源数据
- **设计改进点**：
  1. 顶部封面图区域：ArcView 弧形背景 + CardView 圆角卡片 + CoverImageView 16:9 展示，无图时整体隐藏
  2. 信息行：发布时间 + 文章类型（网页/图片/视频）+ 来源数量，带图标，与书源详情页风格一致
  3. 底部操作栏：返回（TextView）+ 阅读（AccentBgTextView 主题色背景），与书源详情页 fl_action 一致
  4. 多源列表：专用布局 + ic_check 选中图标 + 主题色高亮，替代原 ✓ 前缀
