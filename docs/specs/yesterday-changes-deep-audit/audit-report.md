# 昨日改动深度审查报告

> 审查日期：2026-07-09
> 审查方法：6 Agent 并行深度审查（Agent-A1/A2/A3 + Agent-B + Agent-C + Agent-D）
> 审查范围：2026-07-08 全量改动（书源订阅源布局设计调整 + 内置视频播放器优化，168+ 文件，25768 行新增）
> 基准来源：书架布局核心架构 A1-A6（Agent-A1 建立）

---

## 一、需求偏差报告（开篇）

### 核心偏差

| 维度 | 昨天实际改动 | 用户需求 |
|------|------------|---------|
| 页面层级 | **二级页面**（管理页：BookSourceActivity/RssSourceActivity） | **一级页面**（首页：RssFragment/ExploreFragment） |
| 架构参考 | 自有 SourceFolderAdapter 轻量方案 | 书架 style1（Tab+ViewPager）/ style2（单RV混排+点击进入+返回） |
| 改动深度 | 布局样式调整、配置项迁移 | 架构级重构（Fragment 切换机制 + 双维度下拉菜单） |

### 偏差证据

1. **RssFragment.kt:73-79** 仍用 `isShowingFolder` 双状态 + Fragment 内部切换 adapter 的轻量方案，无 Tab+ViewPager（对比 BookshelfFragment1.kt:49-52）、无混排+进入+返回（对比 BookshelfFragment2.kt:224-231,250-259）
2. **MainActivity.kt:423-429** getFragmentId 仅为 bookshelf 做 style1/style2 切换，RssFragment/ExploreFragment 无对应切换机制
3. **AppConfig.kt:251-258** sourceGroupStyle 是单维度（0=列表/1=按类型/2=按分组），把"归类维度"和"视图模式"耦合，与书架双维度架构不对齐

### 用户感知

用户六次反馈的核心诉求——"首页参考书架 style1/style2 深度设计"——**完全未落地**。昨天改动停在管理页布局微调，首页架构未动。

---

## 二、完整 Bug 清单（按严重度排序）

### 第一类：管理页布局 Bug（BookSourceActivity/RssSourceActivity + Adapter）

| 编号 | 严重度 | 文件:行号 | 根因 | 置信度 |
|------|--------|----------|------|--------|
| M-01 | 🔴高 | BookSourceActivity.kt:96-100,598-608; BookSourceAdapterCompact/Grid.kt | compact/grid adapter 无 selection 机制，Activity 硬编码 list adapter，紧凑/网格模式下选择/批量操作全失效 | 高 |
| M-02 | 🔴高 | RssSourceActivity.kt:73-77,428-565; RssSourceAdapterCompact/Grid.kt | 同 M-01，RssSource compact/grid 选择模式失效 | 高 |
| M-03 | 🟡中 | BookSourceActivity.kt:100,362-364,495-497 | ItemTouchCallback 硬绑 list adapter + isCanDrag 两处条件不一致（applyListView 有 layout==0，upBookSource 缺） | 高 |
| M-04 | 🟡中 | RssSourceActivity.kt:281-284; RssSourceAdapter.kt:213-236 | DragSelectTouchHelper 硬绑 list adapter 的 dragSelectCallback，compact/grid 滑动选择无反馈 | 高 |
| M-05 | 🟡中 | BookSourceActivity.kt:799-803,819-829,680-685 | 校验进度 notifyItemRangeChanged/checkSource 硬编码 list adapter，compact/grid 模式校验静默失败 | 高 |
| M-06 | 🟡中 | BookSourceActivity.kt:408-425; RssSourceActivity.kt:360-375; SourceFolderAdapter.kt:25 | 文件夹视图数据为纯 String，无源计数，用户无法知道每组有多少源 | 高 |
| M-07 | 🟡中 | BookSourceActivity.kt:205-252,504-552; SourceFolderAdapter.kt:100-104 | 排序双轨冲突：菜单强制 sourceSort=0 走旧 sort，配置对话框设 sourceSort=1-6 走新逻辑，互相覆盖 | 高 |
| M-08 | 🟡中 | BookSourceActivity.kt:176-183,277-282,435; RssSourceActivity.kt:143-149 | onPrepareOptionsMenu 未按 isShowingFolder 控制菜单可见性，menu_group_sources_by_domain 无兜底，勾选与效果脱节 | 中 |
| M-09 | 🟢低 | BookSourceActivity.kt:331,368-378; RssSourceActivity.kt:286,321-331 | 文件夹视图 ItemTouchHelper 残留未 detach，folderAdapter 未实现 Callback，与 M-03 叠加可能数据错乱 | 中 |
| M-10 | 🟡中 | BookSourceAdapter.kt/Compact/Grid.kt; RssSourceAdapter.kt/Compact/Grid.kt | 架构债：三 adapter 无共享基类（对比书架 BaseBooksAdapter），是 M-01~M-05 共同根因 | 高 |

### 第二类：首页布局缺失 + 阻塞点（RssFragment/ExploreFragment）

| 编号 | 严重度 | 文件:行号 | 根因 | 置信度 |
|------|--------|----------|------|--------|
| F-01 | 🔴高 | RssFragment.kt:276-285,246-271; ExploreFragment.kt:292-301,222-255 | **Bug 9**：搜索框回填 "group:$group"，用户输入名称后归类信息完全丢失（走 flowEnabled(searchKey) 分支） | 高 |
| F-02 | 🔴高 | RssSource.kt:105-107; BookSourceType.kt:8-17 | **BP-1**：RssSource.type（0网页/1图片/2视频，3种无注解）与 BookSourceType（0文本/1音频/2图片/3文件/4视频，5种有注解）语义不一致，type=2 含义冲突 | 高 |
| F-03 | 🔴高 | AppConfig.kt:251-258,289-303 | **BP-3**：单维度 sourceGroupStyle 迁移到双维度配置（归类维度+样式维度）的逻辑未定义，旧用户升级配置会丢失 | 高 |
| F-04 | 🔴高 | RssFragment.kt:218-224; ExploreFragment.kt:192-198 | **BUG-D-03**：sourceGroupStyle=1（按类型）时 upFolderView 仍按 sourceGroup 聚合，未按 type 聚合，功能名不副实 | 高 |
| F-05 | 🔴高 | 首页整体 | **AM-2**：类型文件夹数据模型未定义（动态生成/预定义/参考 BookGroup），导致"按类型"归类无法落地 | 高 |
| F-06 | 🔴高 | 首页整体 | **AM-3**：style1/style2 架构路线未定（方案A MainActivity 切换 / 方案B Fragment 内部切换 / 方案C childFragmentManager），C1-C3 无法启动 | 高 |
| F-07 | 🔴高 | Bug 9 修复路径 | **BP-2**：Bug 9 修复依赖 style1/style2 重构（currentFilter 在 style1/style2/现有RssFragment 三种语义不统一：Long groupId vs String groupName vs String "group:xxx"） | 中 |
| F-08 | 🟡中 | 首页 C1-C3 | **C1 缺失**：无 style1（Tab+ViewPager）；**C2 缺失**：无 style2（单RV混排+点击进入+返回）；**C3 缺失**：MainActivity 无 sourceGroupStyle 切换 Fragment 机制 | 高 |
| F-09 | 🟡中 | RssSourceDao.kt:80,94; BookSourceDao.kt:115,130 | **AM-5**：DAO 层已有 flowByTypeSearch/flowGroupSearchExact 组合查询方法但未被搜索框使用（这是 Bug 9 的修复路径） | 高 |
| F-10 | 🟡中 | ExploreFragment.kt:200-219 | **BUG-D-01**：initGroupData 未保存 Job 引用，与 RssFragment.kt:226-227 范式不一致，Fragment 重建时协程管理不完整 | 高 |
| F-11 | 🟡中 | RssFragment.kt:251; ExploreFragment.kt:227 | **BUG-D-02**：空判逻辑不一致（RssFragment 用 isNullOrEmpty，ExploreFragment 用 isNullOrBlank），纯空格输入行为不同 | 高 |

### 第三类：配置耦合 + 横向链路（交叉验证置信度高）

| 编号 | 严重度 | 文件:行号 | 根因 | 置信度 | 交叉验证 |
|------|--------|----------|------|--------|---------|
| C-01 | 🔴高 | PreferKey.kt:235; AppConfig.kt:268-272; BookSourceActivity.kt:204-252; RssSourceActivity.kt:203-228 | **sourceSort 耦合**：BookSource 菜单恒置 0 走旧 sort，RssSource 菜单设 0/1/2/5/6 走新逻辑，两类源排序状态互相串扰 | 高 | Agent-A3 + Agent-C 双重确认 |
| C-02 | 🟡中 | values/strings.xml:1297,1300,1332; values-zh/strings.xml | **国际化破损**：默认 strings.xml 直接写中文（"间距"/"紧凑列表"/"边下边播"），values-zh 未同步 | 高 | - |
| C-03 | 🟡中 | 4个 spec 的 tasks.md | **tasks.md 不可信**：video-m3u8-cache 勾选率 0%（AOAdapt 声称完成但 cachePlay 已废弃）；source-layout-redesign 勾选率 21.6% | 高 | - |
| C-04 | 🟢低 | PreferKey.kt:235; AppConfig.kt:267; RssSourceActivity.kt:226,536 | sourceSort 注释不一致（PreferKey/AppConfig 只到 5=URL，RssSourceActivity 有 6=更新时间，BookSource 有 6 死分支） | 高 | - |
| C-05 | 🟢低 | PreferKey.kt:239-240; AppConfig.kt:335-345 | rssSort/rssSortAscending 死代码（已定义但 RssSourceActivity 实际用 sourceSort） | 高 | - |

### 第四类：视频播放器

| 编号 | 严重度 | 文件:行号 | 根因 | 置信度 |
|------|--------|----------|------|--------|
| V-01 | 🔴高 | VideoPlayer.kt:161-163,270-276 | onPrepared 每次换集强制重新静音（`if (muteOnStart) setNeedMute(true)`），用户手动取消静音后被覆盖；图标状态与实际静音不一致 | 高 |
| V-02 | 🟡中 | VideoPlayerActivity.kt（缺失） | 缺少 onPause/onResume override，VideoPlay.onPause()/onResume() 是死代码（无调用方），后台不暂停视频 | 中高 |
| V-03 | 🟡中 | VideoPlay.kt:311 | startPlay 的 book 分支 isLoading=false 在异步 getContent 前同步执行，退出 Activity 时可能对已释放 player 操作 | 中 |
| V-04 | 🟢低 | VideoPlayer.kt:262-264; SettingsDialog.kt:69-82 | fullBottomProgressBar 不实时生效 + videoCacheSize 修改后无"需重启"提示 | 高 |

---

## 三、阻塞点与依赖关系（修复顺序）

```
阶段1（并行，无依赖）:
  ├─ F-02/BP-1（RssSource.type 语义统一）
  ├─ F-03/BP-3（双维度配置项定义+迁移逻辑）
  └─ F-05/AM-2（类型文件夹数据模型定义）—— 依赖 BP-1 类型枚举统一后定稿

阶段2（依赖阶段1）:
  ├─ F-06/AM-3（架构路线决策：方案A/B/C）—— 依赖双维度配置
  └─ F-08/C1-C3（style1/style2 设计落地）—— 依赖架构决策 + 数据模型

阶段3（依赖阶段2）:
  └─ F-01/Bug 9 + F-07/BP-2（currentFilter 统一 + 解耦 searchView）—— 依赖 style1/style2 重构

阶段4（依赖阶段3）:
  └─ F-09/AM-5（启用 DAO 组合查询方法 flowGroupSearchExact/flowByTypeSearch）—— Bug 9 修复最后一步

并行可做（无依赖）:
  ├─ M-01~M-10（管理页 Adapter 架构重构，提取 BaseSourceAdapter 基类）
  ├─ C-01（sourceSort 拆分为 bookSourceSort/rssSourceSort）
  ├─ V-01~V-04（视频播放器修复）
  └─ C-02（国际化修复）
```

**必须先解决**：F-02（类型语义）+ F-03（配置迁移）+ F-05（数据模型）+ F-06（架构路线）—— 这四个是后续所有首页布局工作的前提。
**不可并行**：Bug 9 修复必须在 style1/style2 重构之后，否则 currentFilter 要返工。

---

## 四、4个 spec tasks.md 完成度核实表

| spec | tasks.md 勾选率 | AOAdapt 声称 | 实际源码状态 | 可信度 |
|------|---------------|-------------|------------|--------|
| source-layout-redesign | 21.6% (8/37) | "Phase 5 深度重构完成" | Phase 1-5 代码已写，但有 M-01~M-10 共 10 个 bug | 不可信 |
| video-m3u8-cache | **0%** (0/22) | "1.1-4.4 全部完成" | cachePlay 已 @Deprecated，4 处 setUp 传 false 是空操作，**实施与设计严重偏离** | 完全不可信 |
| rss-cache-first | 3.8% (1/26) | "1.1-5.2 完成" | cacheFirst defaultValue="1" ✓，migration_92_93 ✓，AppDatabase v93 ✓，基本属实 | 不可信（但源码正确） |
| yesterday-changes-deep-audit | ~25% | Phase 1-2 完成 | 本报告即 Phase 3-4 产出 | 基本可信 |

---

## 五、修复优先级建议

### P0（必须立即修复，影响核心功能）

1. **M-01/M-02**：compact/grid 选择模式失效（用户在紧凑/网格模式下无法批量操作）
2. **F-01/Bug 9**：搜索框回填归类信息（用户输入名称后归类丢失）
3. **V-01**：视频换集强制静音（每次换集都要重新取消静音）
4. **C-01**：sourceSort 耦合（两类源排序互相串扰）

### P1（阻塞首页布局重构，必须先决策）

5. **F-02/BP-1**：RssSource.type 语义统一
6. **F-03/BP-3**：双维度配置项迁移逻辑
7. **F-05/AM-2**：类型文件夹数据模型
8. **F-06/AM-3**：style1/style2 架构路线决策

### P2（架构重构，根治管理页 bug）

9. **M-10**：提取 BaseSourceAdapter 共享基类（M-01~M-05 共同根因）
10. **F-08/C1-C3**：首页 style1/style2 设计落地

### P3（体验优化 + 横向修复）

11. **V-02**：视频后台暂停
12. **C-02**：国际化修复
13. **M-06~M-09**：管理页其余 bug
14. **V-03/V-04**：视频其余 bug

---

## 六、审查统计

- 审查文件数：50+ 源文件（6 Agent × 8-12 文件）
- 确认 bug 数：**29 项**（M-01~M-10 + F-01~F-11 + C-01~C-05 + V-01~V-04，去重后）
- 阻塞点数：7 项（BP-1~BP-5 + AM-2/AM-3）
- 需求偏差：1 项（改了管理页而非首页）
- 交叉验证：C-01 被 Agent-A3 + Agent-C 双重确认
- Agent-A1 关键修正：A2 实际是两套独立基类（style1/style2），非单一共享基类

---

*本报告由 6 Agent 并行审查 + 主线汇总交叉验证生成。审查阶段只读不改，修复需另开 OpenSpec 流程。*
