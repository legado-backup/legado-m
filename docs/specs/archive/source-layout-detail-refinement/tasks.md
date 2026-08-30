# Tasks: 书源/订阅源布局细节优化 + 视频播放细节优化

> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)

---

## Phase 1: OpenSpec 设计（🛑检查点1）

- [x] 1.1 分析用户 7 类细节不符反馈，理解需求
- [x] 1.2 源码分析：书架 BookshelfFragment1/2 两模式实现
- [x] 1.3 源码分析：书源/订阅源当前分组样式实现
- [x] 1.4 源码分析：视频缓存当前实现（SettingsDialog.kt 已有设置入口）
- [x] 1.5 源码分析：视频倍速当前实现（最高 15x，音频失真）
- [x] 1.6 生成四文档（README/spec/design/tasks）
- [x] 1.7 AskUserQuestion 检查点1：用户审核设计 —— ✅ 第1次"需调整"（D2新增bug修复+D6方案C），第2次"通过（继续实施）"

## Phase 2: 布局细节实施（D1-D4）

### D1: 标签+分组两模式（首页 RssFragment/ExploreFragment）

> 实施对象调整：用户明确 D1 对象是首页（RssFragment/ExploreFragment），非管理页（BookSourceActivity/RssSourceActivity）。方案选 B（TabLayout + 单 RecyclerView），非方案A（ViewPager + 多Fragment）。

- [x] 2.1.1 确认首页 RssFragment/ExploreFragment 当前 UI 结构，设计标签模式切换方案 ✅ 方案B（TabLayout + 单 RecyclerView）
- [x] 2.1.2 新增 sourceGroupMode 配置项（AppConfig.kt:260-264 + PreferKey.kt:234）✅
- [x] 2.1.3 dialog_source_folder_config.xml 新增"展示模式"Spinner（sp_group_mode）✅
- [x] 2.1.4 arrays.xml + strings.xml 新增展示模式数组和字符串 ✅
- [x] 2.1.5 RssFragment 实现标签模式（TabLayout + 单 RecyclerView，isTagMode/applyView/upTabLayout）✅
- [x] 2.1.6 ExploreFragment 实现标签模式（同 RssFragment 模式）✅
- [x] 2.1.7 SourceFolderAdapter.showConfigDialog 新增 sourceGroupMode 初始化和保存 ✅
- [x] 2.1.8 编译验证 ✅ BUILD SUCCESSFUL（2026-07-09 18:34 第一次全量 4m28s + 18:36 增量 14s + 18:51 增量 15s）
- [x] 2.1.9 真机 L2 验证 ✅ RssFragment TabLayout 可见（3 Tab：全部分组/未分组/LEGADO）+ ExploreFragment TabLayout 可见（2 Tab：全部分组/未分组）+ 配置对话框中文显示正确

### D2: 修复按类型分组一级页面不生效（首页 RssFragment/ExploreFragment）

> 实施对象：用户反馈"书源和订阅源的分组里面的类型分类一级页面，从来都没有成功过"。一级页面=首页（RssFragment/ExploreFragment），非管理页。管理页订阅源二级页面改回列表（D3 已处理）。

- [x] 2.2.1 **Bug 排查**：确认 bookSourceType 值含义 ✅ BookSource 0=文本/1=音频/2=图片/3=文件/4=视频；RssSource 0=网页/1=图片/2=视频
- [x] 2.2.2 **Bug 排查**：Read flowByType DAO 方法 ✅ SQL 正确（书源查 bookSourceType，订阅源查 type）
- [x] 2.2.3 **Bug 排查**：确认 upFolderView 文件夹视图逻辑 ✅ 书源代码正确；订阅源完全无实现
- [x] 2.2.4 **Bug 排查**：确认 onFolderClick 逻辑 ✅ 书源代码正确；订阅源无 onFolderClick
- [x] 2.2.6 确认 RssSource 是否有 type 字段 ✅ RssSource.kt line 107 `var type: Int = 0`
- [x] 2.2.5 **首页修复**：RssFragment 新增 currentType 字段 + 修改 tabSelectedListener/upTabLayout/upFolderView/upRssFlowJob/onFolderClick/showFolderConfig 7 处 ✅
- [x] 2.2.7 **首页修复**：ExploreFragment 同步修改 7 处（类型为 BookSource 5 种：文本/音频/图片/文件/视频）✅
- [x] 2.2.8 **DAO 新增**：BookSourceDao 新增 flowExploreByType/flowExploreByTypeSearch（只返回启用发现的书源）✅
- [x] 2.2.9 **字符串中文化**：strings.xml type_text/audio/image/file/video/web 从英文改为中文 ✅
- [x] 2.2.10 编译验证 ✅ BUILD SUCCESSFUL in 1m 20s
- [x] 2.2.11 真机 L2 验证 ✅ RssFragment 4 Tab（全部分组/网页/图片/视频）+ ExploreFragment 6 Tab（全部分组/文本/音频/图片/文件/视频）+ 点击 Tab 数据筛选正常 + 中文显示正确
- [~] 2.2.12 ~~BookSourceActivity/RssSourceActivity 两维度组合~~ —— 用户要求订阅源二级页面改回列表（D3 已处理），管理页无需文件夹视图，此任务取消
- [x] 2.2.13 **D2-补丁**：文件夹模式返回键功能（检查点2第2次反馈"文件夹模式点进去没有返回"）—— RssFragment/ExploreFragment 新增 OnBackPressedCallback，子目录内按返回键回文件夹列表 ✅ 编译通过(BUILD SUCCESSFUL in 53s) + L2 真机验证通过（RssFragment 4文件夹✅ + ExploreFragment 6文件夹✅，点击文件夹进子目录→按返回键→正确回到文件夹列表）
- [x] 2.2.14 **D2-补丁2**：全部分组文件夹返回键修复（检查点2第3次反馈"全部分组点进去右滑还有bug"）—— inSubDirectory 逻辑从 `currentType>=0 || currentGroup!=null` 改为 `isFolderViewMode && !isShowingFolder`，修复点击全部分组后 currentType=-1/currentGroup=null 导致 inSubDirectory=false 的 bug ✅ 编译通过(BUILD SUCCESSFUL in 47s) + L2 真机验证通过（点击全部分组进子目录→按返回键→正确回到文件夹列表✅）

### D3: 订阅源二级设置还原列表

- [x] 2.3.1 确认订阅源二级设置页面当前布局 ✅ onFolderClick 已实现（line 591-617）
- [x] 2.3.2 RssSourceActivity onFolderClick 进入二级页面时强制列表视图 ✅ line 612-616: isShowingFolder=false + applyListView() + upSourceFlow()
- [ ] 2.3.3 编译验证 + 真机 L2 验证（留待 Phase 4 统一）

### D4: 搜索框参考书架

- [x] 2.4.1 审查 BookSourceActivity/RssSourceActivity 搜索框当前实现 ✅ 两者都有 searchView + onQueryTextListener
- [x] 2.4.2 确保搜索框不回填 type:/group:（F2 修复已用 currentGroup 解耦）✅ RssSourceActivity:511-516 + BookSourceActivity:474-479 均清空前缀回填
- [ ] 2.4.3 搜索框与标签/分组模式配合（待 D1 首页实施后验证）
- [ ] 2.4.4 编译验证 + 真机 L2 验证（留待 Phase 4 统一）

## Phase 3: 视频细节实施（D5-D6）

### D5: 视频缓存下拉选择

- [x] 3.1.1 SettingsDialog.kt 缓存大小改为 Spinner 下拉选择 ✅ setSingleChoiceItems→Spinner+onItemSelectedListener
- [x] 3.1.2 dialog_video_settings.xml 缓存大小项改为 Spinner 布局 ✅ tv_video_cache_size→LinearLayout+Spinner(sp_video_cache_size)
- [ ] 3.1.3 可选：pref_config_other.xml 新增全局视频缓存设置入口（YAGNI 暂不做）
- [ ] 3.1.4 编译验证 + 真机 L2 验证（留待 Phase 4 统一）

### D6: 视频倍速保留 15x 不动（用户选方案C，无需代码修改）

- [x] 3.2.1 记录用户决策：保留 15x 不动，不处理音频失真 —— ✅ 无需代码修改

## Phase 4: updateLog + 交付

- [ ] 4.1 updateLog.md 编译前更新（面向用户描述 7 类细节修复）
- [ ] 4.2 编译 APK
- [ ] 4.3 真机 L2 验证全部功能
- [ ] 4.4 AskUserQuestion 检查点2：用户审核实施结果

## Phase 5: 文档同步

- [ ] 5.1 更新 docs/INDEX.md
- [ ] 5.2 更新 README.md 状态
- [ ] 5.3 写入 basic-memory（project=legado）完成证据

---

## AOAdapt 日志

### 2026-07-10 设计（初版）

- **A**: context-compression-feedback-preservation spec 审查发现 F1-F10 全部已实施，但用户反馈"功能可用但细节不符"，给出 7 类细节不符
- **O**: 之前的设计实现了功能但展示模式、分组维度、设置入口等细节与用户设想存在偏差。关键发现：D5 视频缓存已有设置入口但用户找不到；D1 书源分组样式是数据归类不是展示模式；D6 倍速 15x 音频失真未处理
- **Adapt**: 新建 spec 处理 7 类细节不符，D1 参考书架两模式实现标签+分组，D2 基于 bookSourceType 实现两维度组合，D5 优化缓存设置 UI 和入口可见性，D6 限制最高倍速到 5x
