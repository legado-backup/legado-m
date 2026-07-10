# Tasks: P0 核心 Bug 修复

> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)

---

## Phase 1: OpenSpec 设计（🛑检查点1）

- [x] 1.1 基于 audit-report.md 设计 P0 修复方案
- [x] 1.2 生成四文档（README/spec/design/tasks）
- [x] 1.3 AskUserQuestion 检查点1：用户审核设计（用户选"通过"，含 DAO 缺口修正）

## Phase 2: 实施 P0 修复

### 2.1 C-01：sourceSort 拆分（配置层，先改底层）

- [x] 2.1.1 PreferKey.kt：新增 bookSourceSort，sourceSort 标记 @Deprecated，rssSort 注释统一语义
- [x] 2.1.2 AppConfig.kt：新增 bookSourceSort（含迁移兼容），sourceSort @Deprecated 委托，rssSort 注释统一
- [x] 2.1.3 BookSourceActivity.kt：菜单 sourceSort → bookSourceSort，sortSources 用 bookSourceSort（含注释）
- [x] 2.1.4 RssSourceActivity.kt：菜单 sourceSort → rssSort，sortSources 用 rssSort（含注释）
- [x] 2.1.5 SourceFolderAdapter.kt：showConfigDialog 添加 isBookSource 参数，按类型区分 bookSourceSort/rssSort
- [x] 2.1.6 修复 C-04：统一 sourceSort 排序值注释为 0=手动/1=名称/2=启用/3=类型/4=分组/5=URL/6=更新时间
- [x] 2.1.7 C-05 死代码激活：rssSort 已启用（rssSortAscending 暂保留，不影响功能）
- [x] 2.1.8 BookSourceAdapter.kt：sourceSort → bookSourceSort（menu_top/menu_bottom 可见性判断）

### 2.2 V-01：视频换集静音（独立模块，简单修复）

- [x] 2.2.1 VideoPlayer.kt:161-163：onPrepared 改为 `setNeedMute(isMuted)` 而非 `if (muteOnStart) setNeedMute(true)`
- [x] 2.2.2 验证 initView 中 isMuted 初始化保持 `isMuted = VideoPlay.muteOnStart`（line 270，仅首次播放应用）

### 2.3 F-01：搜索框回填 Bug 9（首页，引入 currentFilter）

- [x] 2.3.0 新增 DAO 方法（2个，组合查询缺口）：
  - RssSourceDao.kt 新增 `flowNoGroupSearch(searchKey)`（未分组+名称组合查询）
  - BookSourceDao.kt 新增 `flowExploreNoGroupSearch(searchKey)`（未分组发现页+名称组合查询）
  - SQL 见 design.md F-01 方案"需新增 DAO 方法"
- [x] 2.3.1 RssFragment.kt：添加 currentFilter 字段（var currentGroup: String? = null）
- [x] 2.3.2 RssFragment.kt：onFolderClick 设置 currentGroup，不回填 searchView（改为直接调 upRssFlowJob）
- [x] 2.3.3 RssFragment.kt：upRssFlowJob 用 currentGroup + searchKey 组合查询（6 分支，见 design.md）：
  - currentGroup == no_group && searchKey.blank() → flowEnabledNoGroup()
  - currentGroup == no_group && searchKey.notBlank() → flowNoGroupSearch(searchKey)（新增）
  - currentGroup != null && searchKey.notBlank() → flowGroupSearchExact(currentGroup, searchKey)
  - currentGroup != null && searchKey.blank() → flowEnabledByGroup(currentGroup)
  - currentGroup == null && searchKey.notBlank() → flowEnabled(searchKey)
  - currentGroup == null && searchKey.blank() → flowEnabled()
- [x] 2.3.4 RssFragment.kt：onFolderClick 点击"全部"时 currentGroup=null，点击"未分组"时 currentGroup=no_group 特殊处理
- [x] 2.3.5 RssFragment.kt：菜单 menu_group_text 快捷筛选也改为设置 currentGroup，不回填 searchView
- [x] 2.3.6 ExploreFragment.kt：同 2.3.1-2.3.5（用 BookSourceDao 的 flowGroupExplore/flowExplore/flowExploreNoGroup/flowExploreNoGroupSearch 组合）
- [x] 2.3.7 修复 F-11（BUG-D-02）：统一空判逻辑为 isNullOrBlank

### 2.4 M-01/M-02：compact/grid 选择模式（管理页，工作量大）

- [x] 2.4.1 BookSourceAdapterCompact.kt：添加 selection 机制（selected 集合 + selectAll + revertSelection + selection 属性 + dragSelectCallback + checkSelectedInterval + setSelection）
- [x] 2.4.2 BookSourceAdapterGrid.kt：同 2.4.1
- [x] 2.4.3 BookSourceAdapterCompact.kt：convert 添加 cb 复选框渲染 + 点击选择逻辑
- [x] 2.4.4 BookSourceAdapterGrid.kt：convert 添加选择逻辑（grid 布局无 cb，用 foreground 高亮）
- [x] 2.4.5 BookSourceActivity.kt：adapter 引用改为 currentAdapter() 动态获取（when sourceLayout { 1->adapterCompact; in 2..6->adapterGrid; else->adapter }）
- [x] 2.4.6 BookSourceActivity.kt：selectAll/revertSelection/onClickSelectBarMainAction/onMenuItemClick/checkSource/selectionAddToGroups/selectionRemoveFromGroups/upCountView 全部改用 currentAdapter()
- [x] 2.4.7 BookSourceActivity.kt：itemTouchCallback 和 DragSelectTouchHelper 改为按 currentAdapter() 动态获取
- [x] 2.4.8 BookSourceActivity.kt：校验进度 notifyItemRangeChanged 改用 currentAdapter()
- [x] 2.4.0 BookSourceAdapter.kt：定义 BookSourceSelection 接口 + 3 个 adapter 实现接口 + BookSourceViewModel.saveToFile 签名解耦
- [x] 2.4.9 RssSourceAdapterCompact.kt：同 2.4.1（RssSource 版本）
- [x] 2.4.10 RssSourceAdapterGrid.kt：同 2.4.2（RssSource 版本）
- [x] 2.4.11 RssSourceActivity.kt：同 2.4.5-2.4.8（RssSource 版本）
- [x] 2.4.12 RssSourceAdapter.kt：定义 RssSourceSelection 接口 + 3 个 adapter 实现接口

### 2.5 编译验证

- [x] 2.5.1 `./gradlew assembleRelease` 编译通过（BUILD SUCCESSFUL in 3m 34s，4 个 Mode 引用修复生效，Kotlin 编译 + lint + 打包全通过）
- [x] 2.5.2 `git diff` 确认变更范围符合预期（18 文件，663 insertions, 179 deletions，符合 P0 设计：C-01/V-01/F-01/M-01/M-02）

## Phase 3: E2E 自动化测试（步骤 5.5）

- [x] 3.1 源码影响分析（run_e2e.py --diff HEAD~1）→ 170 文件改动，14 Activity 受影响，46 TC-ID 关联
- [x] 3.2 APK 自动发现 + MEmu 启动 → MEmu 实例0启动，ADB 127.0.0.1:21503 连接，debug APK 3.26.070913 安装成功
- [ ] 3.3 双轨用例调度（F-P0-6 书源管理测试运行中，10 用例，job-89502a6e3d044da7a20adac9e1023946）
  - 修复用例加载问题：F-P0-6 用例从 ai_tests/cases/ 子目录复制到 docs/tests/F-P0-6-source-manage.md
  - TC-F-P0-6-01 完成（manual，置信度 50，需 AI 介入）
  - TC-F-P0-6-02 执行中
- [ ] 3.4 8 类证据收集（进行中，TC-01 已收集 6/8 成功 + 2 降级）
- [ ] 3.5 规则判定（进行中）
- [ ] 3.6 manual 用例 AI agent 介入（待 3.5 完成后批量处理）
- [ ] 3.7 五件套报告生成（待所有用例完成）
- [ ] 3.8 反馈闭环触发（待报告生成后）

## Phase 4: 用户确认（🛑检查点2）

- [ ] 4.1 AskUserQuestion 检查点2：用户审核实施 + E2E 测试结果

## Phase 5: 交付

- [ ] 5.1 更新 updateLog.md
- [ ] 5.2 更新 tasks.md 勾选完成项
- [ ] 5.3 更新 docs/INDEX.md
- [ ] 5.4 询问是否进入 P1 修复

---

## AOAdapt 日志

### 2026-07-09 P0 设计

- **A**: 基于 audit-report.md 设计 P0 修复方案
- **O**: F-01/Bug 9 的修复路径是引入 currentFilter + 启用 DAO 组合查询，不必等 style1/style2 重构（BP-2 的依赖是针对 currentFilter 在 style1/style2 下语义统一，但现有 RssFragment 也可以先用 String currentGroup 修复）
- **Adapt**: P0 采用简化方案——给 compact/grid 加 selection（不提取基类，P2 的 M-10 再做架构重构），F-01 引入 currentGroup 字段解耦 searchView
