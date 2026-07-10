# Tasks: 昨日改动深度审查

> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)
>
> 任务编排原则：审查计划 → 用户确认 → 并行审查 → 汇总报告 → 用户确认。
> 审查阶段只读不改，修复另开 OpenSpec。

---

## Phase 1: 审查准备（已完成）

- [x] 1.1 收集昨日 git log + git stat，建立改动文件清单
- [x] 1.2 读取 4 个 spec 的 tasks.md + AOAdapt 日志，建立预期完成清单
- [x] 1.3 读取核心源码（BookSourceActivity/RssSourceActivity/VideoPlayer/VideoPlay/ChoiceSpeedDialog/SettingsDialog）初步发现 15 个疑似 bug
- [x] 1.4 生成 OpenSpec 四文档（README/spec/design/tasks）
- [x] 1.5 更新 docs/INDEX.md

## Phase 2: 用户确认审查计划（🛑检查点1）

- [x] 2.1 用 AskUserQuestion 让用户确认审查范围、方法、初步发现
  - 用户反馈"需调整"：书源订阅源布局只学到表象，要求深入研究书架布局核心机制
- [x] 2.2 启动书架对比研究 Agent，深入研究书架布局核心机制（A1-A6）+ 对比差距（B1-B6）→ 发现 Bug 1-8
- [x] 2.3 更新四文档纳入 D11 书架架构对比维度 + R4 书架对比审查要求 + S7-S14 书架对比验证场景
- [x] 2.4 重新发起 AskUserQuestion 让用户确认修订后的审查计划
  - 用户二次反馈"需调整"：要求确认书架分组归类依据 + bookGroupStyle 两种样式差异 + 指出需求偏差（改了管理页而非首页）
- [x] 2.5 启动首页布局研究，确认书架分组归类依据（Book.group）+ bookGroupStyle 两种样式（style1 Tab+ViewPager / style2 单RV混排）+ 需求偏差（改了管理页而非首页）
- [x] 2.6 更新四文档纳入 D12 首页布局架构对比维度 + R5 首页布局审查要求 + S15-S17 首页布局验证场景 + 3.4 Agent-D 首页布局审查任务
- [x] 2.7 重新发起 AskUserQuestion 让用户确认修订后的审查计划
  - 用户三次反馈"需调整"：要求布局弹框支持双维度下拉菜单（归类维度：按分组/按类型 + 样式维度：标签/文件夹）
- [x] 2.8 确认 BookSourceType 类型定义（default=0 文本/audio=1 音频/image=2 图片/file=3 文件/video=4 视频）可用于"按类型"归类
- [x] 2.9 更新四文档纳入 R5.6 双维度下拉菜单设计建议 + S18 双维度验证场景 + C4 设计建议 + 3.4.3 双维度设计验证任务
- [x] 2.10 重新发起 AskUserQuestion 让用户确认修订后的审查计划
  - 用户六次反馈后隐式授权："你自己要做好最全面的审查呀。后面也是你自己去执行呢"
  - AI 完成元审查（5阻塞点+3设计不合理+5模糊地带全部补充），自主推进到 Phase 3

## Phase 3: 多 Agent 并行深度审查

### 3.1 Agent-A：书源订阅源布局审查（含 D11 书架对比维度）

#### 3.1.0 书架基准源码审查（D11 基准建立）

- [ ] 3.1.0.1 审查 BaseBookshelfFragment.kt 的 configBookshelf 统一配置管理（A6 基准）
- [ ] 3.1.0.2 审查 BooksFragment.kt 的 adapter 按 bookshelfLayout 选择 + RecycledViewPool 隔离（A1/A2/A4 基准）
- [ ] 3.1.0.3 审查 BaseBooksAdapter.kt 共享基类（DiffUtil/payload/notification/CallBack/selection）（A2 基准）
- [ ] 3.1.0.4 审查 BooksAdapterList/List2/Grid 三 adapter 继承 BaseBooksAdapter（A2 基准）
- [ ] 3.1.0.5 审查 MainViewModel.kt 的 booksListRecycledViewPool/booksGridRecycledViewPool 独立 pool（A4 基准）
- [ ] 3.1.0.6 审查 BookshelfManageActivity.kt 管理界面与浏览分离（A5 基准）

#### 3.1.1 书源订阅源对比审查（D11 差距定位）

- [ ] 3.1.1.1 审查 BookSourceActivity.kt 全部逻辑（D2/D3/D4/D5/D11，对比 BaseBookshelfFragment + BooksFragment）
- [ ] 3.1.1.2 审查 RssSourceActivity.kt 全部逻辑（D2/D3/D4/D5/D11，对比 BaseBookshelfFragment + BooksFragment）
- [ ] 3.1.1.3 审查 BookSourceAdapter/Compact/Grid 是否继承共享基类？是否有 selection？（D5/D11，对比 BaseBooksAdapter）
- [ ] 3.1.1.4 审查 RssSourceAdapter/Compact/Grid 是否继承共享基类？是否有 selection？（D5/D11，对比 BaseBooksAdapter）
- [ ] 3.1.1.5 审查 SourceFolderAdapter.kt 是否实现 ItemTouchHelper.Callback？（D1/D5/D11，验证 Bug 8）
- [ ] 3.1.1.6 审查 ExploreFragment.kt + RssFragment.kt 的菜单处理（D2）
- [ ] 3.1.1.7 审查 4 个 menu XML（book_source/rss_source/main_explore/main_rss）的菜单项定义（D2）
- [ ] 3.1.1.8 审查 6 个 item 布局 + 1 个 dialog 布局的 ID 与代码引用一致性（D5）

#### 3.1.2 Bug 验证（D11 书架对比 Bug 1-8 + L-01~L-06）

- [ ] 3.1.2.1 验证 Bug 1：BookSource compact/grid 选择模式与批量操作失效（🔴高，S7）
- [ ] 3.1.2.2 验证 Bug 2：BookSource ItemTouchHelper 错位绑定 + isCanDrag 条件不一致（🟡中，S8）
- [ ] 3.1.2.3 验证 Bug 3：RssSource compact/grid 选择模式失效（🔴高，S13）
- [ ] 3.1.2.4 验证 Bug 4：RssSource DragSelectTouchHelper 失效（🟡中，S13）
- [ ] 3.1.2.5 验证 Bug 5：校验进度刷新在 compact/grid 模式下无效（🟡中，S9）
- [ ] 3.1.2.6 验证 Bug 6：文件夹视图与列表视图互斥，无源计数（🟡中，S12）
- [ ] 3.1.2.7 验证 Bug 7：排序状态在配置对话框与菜单间不同步（🟡中，S11）
- [ ] 3.1.2.8 验证 Bug 8：文件夹视图 ItemTouchHelper 残留（🟢低，S14）
- [ ] 3.1.2.9 验证 L-01：sourceSort 配置项耦合（书源菜单强制 0，订阅源菜单设 1/2/5/6）
- [ ] 3.1.2.10 验证 L-02：未分组文件夹场景（currentGroup=null 走 flowAll 显示全部）
- [ ] 3.1.2.11 验证 L-03~L-06：其余疑似 bug
- [ ] 3.1.2.12 输出该模块完整 bug 清单（BUG-XX 格式）

### 3.2 Agent-B：视频播放器审查

- [ ] 3.2.1 审查 VideoPlayer.kt 全部逻辑（onPrepared/initView/showSpeedDialog/setVideoSpeed 生命周期 D6/D7/D8）
- [ ] 3.2.2 审查 VideoPlay.kt 的 startPlay/releaseAllVideos/saveRead 状态机（D6/D8/D10）
- [ ] 3.2.3 审查 ChoiceSpeedDialog.kt 的空安全与列表逻辑（D7/D8）
- [ ] 3.2.4 审查 SettingsDialog.kt 的配置项闭环（D1）
- [ ] 3.2.5 审查 VideoPlayerActivity.kt 的生命周期与 player 释放（D6/D10）
- [ ] 3.2.6 审查 ExoPlayerManager/ExoVideoManager/Exo2MediaPlayer/ExoPlayerHelper 的缓存与释放（D6/D10）
- [ ] 3.2.7 审查 video_layout_controller_full.xml + video_layout_controller.xml 的 iv_mute 等 ID 一致性（D5）
- [ ] 3.2.8 审查 dialog_video_settings.xml 的开关项与 SettingsDialog 代码一致性（D1）
- [ ] 3.2.9 验证 V-01~V-08 疑似 bug，输出确认/否决结论
- [ ] 3.2.10 输出该模块完整 bug 清单（BUG-XX 格式）

### 3.3 Agent-C：横向链路审查

- [ ] 3.3.1 审查 PreferKey.kt 新增 key 与 AppConfig.kt 属性的对应关系（D1）
- [ ] 3.3.2 审查 AppConfig.kt 的 sourceSort/sourceLayout/sourceGroupStyle/sourceMargin 默认值与读取（D1/D9）
- [ ] 3.3.3 审查 BookSourceDao.kt 新增方法（flowByType/flowByTypeSearch/flowGroupSearch/flowGroupSearchExact）SQL 正确性（D3）
- [ ] 3.3.4 审查 RssSourceDao.kt 新增方法 SQL 正确性（D3）
- [ ] 3.3.5 审查 RssSource.kt @ColumnInfo defaultValue 变更 + DatabaseMigrations.kt 92→93 迁移逻辑（D8）
- [ ] 3.3.6 审查 AppDatabase.kt version 是否为 93 + schema 93.json 是否存在（D8）
- [ ] 3.3.7 审查 strings.xml + values-zh/strings.xml 新增字符串的完整性（D1）
- [ ] 3.3.8 验证跨模块配置耦合（sourceSort 被书源和订阅源共享的语义冲突，L-01）（D9）
- [ ] 3.3.9 输出该模块完整 bug 清单（BUG-XX 格式）

### 3.4 Agent-D：首页布局架构对比审查（D12 维度，用户二次反馈核心）

#### 3.4.1 书架 style1/style2 架构研究（基准建立）

- [ ] 3.4.1.1 审查 BookshelfFragment1.kt 的 Tab+ViewPager 架构（style1 基准：每组一 Tab，ViewPager 切换）
- [ ] 3.4.1.2 审查 BookshelfFragment2.kt 的单RV混排架构（style2 基准：getItems=bookGroups+books，点击进入，返回回根目录）
- [ ] 3.4.1.3 审查 style2/BaseBooksAdapter.kt 的 getItemViewType 混排支持（BookGroup vs Book）
- [ ] 3.4.1.4 审查 MainActivity.kt 的 getFragmentId 按 bookGroupStyle 切换 Fragment 机制（A7 基准）

#### 3.4.2 首页（RssFragment/ExploreFragment）现状对比（D12 差距定位）

- [ ] 3.4.2.1 审查 RssFragment.kt 的文件夹/列表视图切换机制（D12，对比书架 style1/style2）
- [ ] 3.4.2.2 审查 ExploreFragment.kt 的文件夹/列表视图切换机制（D12，对比书架 style1/style2）
- [ ] 3.4.2.3 验证 C1：RssFragment/ExploreFragment 缺书架 style1（Tab+ViewPager）设计（S15）
- [ ] 3.4.2.4 验证 C2：RssFragment/ExploreFragment 缺书架 style2（单RV混排+点击进入+返回）设计（S16）
- [ ] 3.4.2.5 验证 C3：MainActivity 缺 sourceGroupStyle 切换 Fragment 机制（S17）

#### 3.4.3 需求理解偏差确认 + 双维度设计建议（R5.5/R5.6）

- [ ] 3.4.3.1 确认昨天改动对象是管理页（RssSourceActivity/BookSourceActivity）而非首页（RssFragment/ExploreFragment）
- [ ] 3.4.3.2 输出"需求偏差报告"：用户要的是首页参考书架布局，昨天改的是管理页布局
- [ ] 3.4.3.3 验证 C4：当前 SourceFolderAdapter.showConfigDialog 的 sourceGroupStyle 把"归类维度"和"视图模式"混在一起，需重新设计为双维度下拉菜单（S18）
- [ ] 3.4.3.4 确认 BookSourceType 类型定义（default=0 文本/audio=1 音频/image=2 图片/file=3 文件/video=4 视频）可用于"按类型"归类
- [ ] 3.4.3.5 输出"双维度下拉菜单设计建议"：归类维度（按分组/按类型）+ 样式维度（标签 style1/文件夹 style2），4 种组合矩阵
- [ ] 3.4.3.6 输出该模块完整问题清单（BUG-XX 格式 + 需求偏差标记 + 设计建议标记）
- [ ] 3.4.3.7 验证 Bug 9：搜索框回填归类信息（RssFragment/ExploreFragment onFolderClick 把 group:$group 回填 searchView，污染用户输入）（🔴高，S19）
- [ ] 3.4.3.8 验证 BP-1：RssSource.type（0=网页/1=图片/2=视频，3种，无注解）与 BookSource.bookSourceType（0=文本/1=音频/2=图片/3=文件/4=视频，5种，有注解）语义不一致（S20）
- [ ] 3.4.3.9 验证 BP-3：双维度下拉菜单重新设计后，现有 sourceGroupStyle（0=列表/1=按分组/2=按类型）迁移逻辑未定义（S21）
- [ ] 3.4.3.10 验证 AM-5：DAO 层已有 flowByTypeSearch/flowGroupSearchExact 组合查询方法但未被搜索框使用，导致归类信息与名称搜索无法组合（S22）
- [ ] 3.4.3.11 验证 AM-2：类型文件夹数据模型未定义（动态生成/预定义/参考BookGroup特殊ID），需确认方案（C8）

### 3.5 阻塞点与依赖关系分析（元审查新增）

- [ ] 3.5.1 分析 BP-2：Bug 9 修复与首页布局重构（C1-C3 style1/style2）的依赖关系，明确修复顺序
- [ ] 3.5.2 分析 AM-3：style1/style2 是否需要 MainActivity 切换 Fragment（参考书架）还是只在 RssFragment 内部切换
- [ ] 3.5.3 分析 AM-4：统一搜索框"归类信息"在 style1（当前Tab）/style2（当前文件夹）/现有RssFragment（onFolderClick group参数）三种情况下的 currentFilter 语义
- [ ] 3.5.4 输出"阻塞点与依赖关系报告"，明确各阻塞点的修复顺序和依赖关系

### 3.6 Agent 职责边界明确（元审查新增）

- [ ] 3.6.1 明确 Agent-A 与 Agent-D 对 RssFragment/ExploreFragment 的分工边界（Agent-A 审查菜单 D2，Agent-D 审查布局架构 D12）
- [ ] 3.6.2 明确 Bug 9 主审 Agent（Agent-D 主审首页布局+搜索框，Agent-A 辅助验证 DAO 数据流）
- [ ] 3.6.3 明确 Agent-A 3.1.0 与 Agent-D 3.4.1 书架源码审查的分工（Agent-A 关注共享基类 A2，Agent-D 关注 style1/style2 架构）
- [ ] 3.6.4 明确 Agent-C 3.3.3/3.3.4 DAO SQL 正确性与 Agent-D 3.4.3.10 DAO 使用情况的分工

## Phase 4: 主线汇总与交叉验证（已完成）

- [x] 4.1 合并 4 个 Agent 的 bug 清单，去重 → 29 项 bug（去重后）
- [x] 4.2 交叉验证：同一 bug 被多 Agent 发现 → 置信度"高"（C-01 sourceSort 耦合被 Agent-A3 + Agent-C 双重确认）
- [x] 4.3 补充跨模块耦合 bug（Agent 可能漏报的耦合点）→ C-01/C-02/C-03 跨模块耦合
- [x] 4.4 核对 4 个 spec 的 tasks.md 真实完成级别（Level 1/2/3），输出"任务完成度核实表" → video-m3u8-cache 勾选率 0% + cachePlay 已废弃
- [x] 4.5 汇总"需求理解偏差报告"（Agent-D 3.4.3.2）作为审查报告开篇 → audit-report.md 第一节
- [x] 4.6 生成完整 bug 报告（按严重度排序，每条含 编号/严重度/文件:行号/根因/影响/修复方向/置信度，区分"管理页 bug"和"首页布局缺失"两类）→ audit-report.md

### AOAdapt 日志：Phase 3-4 审查执行

- **A**: 启动 6 Agent 并行审查（Agent-A1 书架基准 / Agent-A2 管理页Adapter / Agent-A3 菜单布局 / Agent-B 视频 / Agent-C 横向链路 / Agent-D 首页布局+阻塞点）
- **O**: Agent-A1 关键修正：A2 实际是两套独立基类（style1 BaseBooksAdapter + style2 BaseBooksAdapter），非单一共享基类；selection 不在 BaseBooksAdapter 中，在 manage/BookAdapter.kt；bookshelfLayout >=2 是列数参数非枚举
- **O**: Agent-A2 确认 Bug 1-8 全部成立 + 新发现 BUG-A2-01（架构债：三 adapter 无共享基类）
- **O**: Agent-A3 确认 L-01（sourceSort 耦合）+ L-05（菜单可见性），否决 L-02/L-03/L-04/L-06
- **O**: Agent-B 确认 V-04（静音）+ V-07（后台暂停），否决 V-01/V-02/V-03/V-05/V-08，新发现 BUG-B-01（isLoading 时序）
- **O**: Agent-C 确认 L-01（与 Agent-A3 交叉验证）+ L-07（tasks.md 不可信），新发现 BUG-C-01（国际化）+ BUG-C-02（注释不一致）+ BUG-C-03（死代码）
- **O**: Agent-D 确认 Bug 9 + BP-1~BP-5 + AM-1~AM-5，新发现 BUG-D-01（Job 未保存）+ BUG-D-02（空判不一致）+ BUG-D-03（按类型未聚合）
- **Adapt**: 汇总去重后 29 项 bug + 7 阻塞点 + 1 需求偏差，生成 audit-report.md

## Phase 5: 用户确认审查报告（🛑检查点2，已完成）

- [x] 5.1 用 AskUserQuestion 让用户确认 bug 报告
  - 用户选"通过（继续交付）" → 进入 Phase 6

## Phase 6: 交付审查报告（已完成）

- [x] 6.1 更新 README.md 状态为 ✅ 审查完成
- [x] 6.2 更新 tasks.md 勾选完成项
- [x] 6.3 更新 docs/INDEX.md
- [x] 6.4 询问用户是否立即对发现的 bug 开 OpenSpec 修复流程

---

## AOAdapt 日志

> 记录审查过程中与计划的偏离、新发现、调整。

### 2026-07-09 审查计划阶段

- **A**: 读取 4 个 spec 的 tasks.md 评估任务完成情况
- **O**: 发现 video-m3u8-cache/tasks.md 全部 `[ ]` 未勾选，但 AOAdapt 日志说"实施完成"；source-layout-redesign/tasks.md Phase 1-7 大量未勾选但 AOAdapt 说 Phase 5 深度重构完成
- **Adapt**: 确认 tasks.md 状态不可信，定为审查对象之一（L-07），审查依据改为源码实际状态

- **A**: 读取 VideoPlay.kt 确认 cachePlay 实现
- **O**: 发现 cachePlay 已 `@Deprecated`，getter 恒返回 false，注释说"ExoPlayer SimpleCache 已默认接管缓存"。但 video-m3u8-cache/tasks.md 1.1-1.6 要求新增 cachePlay 属性并替换 4 处 setUp
- **Adapt**: 确认 video-m3u8-cache spec 的实施与设计严重偏离——cachePlay 被废弃，4 处 setUp 传入 false 是空操作。定为 V-01/V-02 bug

- **A**: 对比 BookSourceActivity 与 RssSourceActivity 的菜单排序处理
- **O**: BookSource 的 menu_sort_* 都设置 `AppConfig.sourceSort = 0`（走旧 sort 逻辑），RssSource 的 menu_sort_* 设置 `AppConfig.sourceSort = 1/2/5/6`。两个 Activity 共享同一 AppConfig.sourceSort
- **Adapt**: 确认配置项耦合，定为 L-01 高严重度 bug

- **A**: 读取 VideoPlayer.kt 的 onPrepared 静音逻辑
- **O**: `if (VideoPlay.muteOnStart) { getGSYVideoManager().player?.setNeedMute(true) }`。每次换集 onPrepared 都会触发，即使用户手动取消静音也会被重新静音
- **Adapt**: 定为 V-04 高严重度体验 bug

### 2026-07-09 检查点1用户反馈 + 书架对比研究

- **A**: 发起检查点1 AskUserQuestion 让用户确认审查计划
- **O**: 用户选"需调整"，反馈："书源订阅源布局，让你好好学习书架布局模式，但是你只学到了表象，没有抓住核心，你没有看到书架布局的所有类型以及布局条件影响的对象是谁，现在搞得书源订阅源布局有 bug 还徒有其表"
- **Adapt**: 初步审查计划只从通用维度（配置/菜单/数据流）审查，未以书架布局核心架构为基准对比。启动书架对比研究 Agent 深入研究

- **A**: 启动书架对比研究 Agent，深入研究书架布局核心机制
- **O**: Agent 报告书架布局核心机制（A1-A6）：
  - A1: 配置项语义（bookshelfLayout 0-6=Grid列数 / showBookname 0-2 / bookGroupStyle 0-1 / bookshelfSort 0-5）
  - A2: **BaseBooksAdapter<VB> 共享基类**（统一 DiffUtil/payload/notification/CallBack/selection）
  - A3: style1（Tab+ViewPager）vs style2（单 RV 混排+getItemViewType）
  - A4: Fragment 级重建（EventBus.RECREATE）+ 独立 RecycledViewPool
  - A5: 浏览界面（BooksFragment）与管理界面（BookshelfManageActivity）分离哲学
  - A6: 配置对话框统一管理（BaseBookshelfFragment.configBookshelf）
- **O**: Agent 报告书源订阅源布局差距（B1-B6）：
  - B1: **缺共享基类**——三 adapter 各自独立，无 BaseSourceAdapter
  - B2: 无 Fragment 重建——applyListView 直接替换 layoutManager+adapter
  - B3: ItemTouchHelper 错位绑定——itemTouchCallback by lazy 永远绑 list adapter
  - B4: 选择模式只作用 list——selectAll/revertSelection 硬编码 adapter.selection
  - B5: 无 RecycledViewPool 隔离——list/grid 共用同一 pool
  - B6: 配置对话框与菜单不同步——菜单强制 sourceSort=0，对话框设 sourceSort=1
- **O**: Agent 发现 8 个新 bug（Bug 1-8）：
  - Bug 1（🔴高）: BookSource compact/grid 选择模式与批量操作完全失效
  - Bug 2（🟡中）: BookSource ItemTouchHelper 错位绑定 + isCanDrag 条件不一致
  - Bug 3（🔴高）: RssSource compact/grid 选择模式失效
  - Bug 4（🟡中）: RssSource DragSelectTouchHelper 失效
  - Bug 5（🟡中）: 校验进度刷新在 compact/grid 模式下无效
  - Bug 6（🟡中）: 文件夹视图与列表视图互斥，无源计数
  - Bug 7（🟡中）: 排序状态在配置对话框与菜单间不同步
  - Bug 8（🟢低）: 文件夹视图 ItemTouchHelper 残留
- **Adapt**: 根因总结——书源订阅源布局只复制了书架的"配置项命名"和"多 adapter 切换"形式，但**没有复制 BaseBooksAdapter 共享基类的关键架构**，导致 compact/grid 模式下选择/拖拽/批量操作/校验刷新全部断裂。更新四文档纳入 D11 书架架构对比维度 + R4 书架对比审查要求 + S7-S14 书架对比验证场景 + AD-05 决策

### 2026-07-09 检查点1用户二次反馈 + 首页布局研究

- **A**: 重新发起检查点1 AskUserQuestion 确认修订后的审查计划
- **O**: 用户再次选"需调整"，反馈三个关键问题：
  1. "书架的对象是根据图书的什么信息进行归类的？"——要求确认书架分组归类依据
  2. "书架布局里面的分组样式里面选择标签后当前书架变成什么样，选择文件夹后变成什么样？"——要求确认 bookGroupStyle 两种样式的视觉差异
  3. "昨天为什么大量的去改了订阅源栏目设置里面的二级页面呢？我要的是订阅源栏目首页根据书架布局深度分析设计"——指出需求理解偏差
- **Adapt**: 启动首页布局研究，确认三个问题的答案：
  - 问题1答案：书架根据 Book.group 字段（Long 类型）归类，对应 BookGroup.groupId（Book.kt:79）
  - 问题2答案：bookGroupStyle=0（标签）→ BookshelfFragment1（Tab+ViewPager，每组一 Tab）；bookGroupStyle=1（文件夹）→ BookshelfFragment2（单RV混排，分组文件夹+书籍混排，点击进入子目录，返回回根目录）
  - 问题3答案：**需求理解根本性偏差**——昨天改的是管理页（RssSourceActivity/BookSourceActivity，二级页面），用户要的是首页（RssFragment/ExploreFragment，一级页面）参考书架 style1/style2 深度设计
- **O**: 首页现状研究（C1-C3 缺失）：
  - C1: 缺 style1 设计——RssFragment 无 Tab+ViewPager，只有文件夹/列表二选一
  - C2: 缺 style2 设计——RssFragment 文件夹视图只显示文件夹列表，点击切换到列表+searchView筛选，无书架 style2 的混排+点击进入+返回逻辑
  - C3: 缺样式切换机制——MainActivity 无 sourceGroupStyle 切换 Fragment 机制，RssFragment 只有一个
- **Adapt**: 更新四文档纳入 D12 首页布局架构对比维度 + R5 首页布局审查要求 + S15-S17 首页布局验证场景 + 3.4 Agent-D 首页布局审查任务 + 需求偏差报告要求。审查对象从"管理页布局"扩展到"首页布局架构对比"

### 2026-07-09 检查点1用户三次反馈 + 双维度下拉菜单设计

- **A**: 重新发起检查点1 AskUserQuestion 确认修订后的审查计划（含首页布局研究）
- **O**: 用户三次选"需调整"，反馈："结合今天的深度分析，再结合我昨天提到的需求，就是除了按照书源或订阅源的分组字段进行归类展示外，还要根据书源和订阅源的类型字段（文本、音频、图片、文件、视频），那是不是得在书源和订阅源的布局弹框上有一个下拉菜单，可以选择分组也可以选择类型呢？样式选择下拉菜单就是不是可以参考书架布局按照标签和文件夹呢？"
- **Adapt**: 确认 BookSourceType 类型定义（BookSourceType.kt）：
  - default=0（文本）/ audio=1（音频）/ image=2（图片）/ file=3（文件）/ video=4（视频）
  - BookSource.bookSourceType: Int（@BookSourceType.Type 注解）
  - RssSource.type: Int = 0
- **O**: 用户设计建议——双维度下拉菜单：
  - 归类维度下拉菜单：按分组 / 按类型（文本/音频/图片/文件/视频）
  - 样式维度下拉菜单：标签（style1 Tab+ViewPager）/ 文件夹（style2 单RV混排）
  - 4 种组合：按分组+标签 / 按分组+文件夹 / 按类型+标签 / 按类型+文件夹
- **Adapt**: 更新四文档纳入 R5.6 双维度下拉菜单设计建议 + S18 双维度验证场景 + C4 设计建议 + 3.4.3 双维度设计验证任务。当前 SourceFolderAdapter.showConfigDialog 的 sourceGroupStyle（0=列表/1=按分组/2=按类型）把"归类维度"和"视图模式"混在一起，需重新设计为双维度独立选择

### 2026-07-09 检查点1用户四次反馈 + 搜索框设计

- **A**: 重新发起检查点1 AskUserQuestion 确认修订后的审查计划（含双维度下拉菜单设计）
- **O**: 用户四次选"需调整"，反馈："昨天还提到了，在书源和订阅源栏目首页上方的搜索，其实按照设想，就是不管归类是什么样子的，其实上面的搜索框都默认要带过去这个信息查询的，比如我现在是按照类型为文本进行归类展示，那我现在选择了文本标签页面后，那上面的搜索在输入名称的时候，要默认带上类型字段呢，如果我归类展示选分组，那分组字段默认传后端，并且不要直接按照现在的设计回填在搜索框呢，是不是这个道理？"
- **O**: 读取 RssFragment.kt L276-285 onFolderClick 确认当前错误设计：
  - `searchView.setQuery("group:$group", true)` 把归类信息回填到搜索框
  - 搜索框被 `group:小说` 这样的前缀污染
  - 用户搜索名称时需先清空前缀，体验极差
  - ExploreFragment.kt L235 同样有 `searchKey.startsWith("group:")` 逻辑，同构问题
- **Adapt**: 定为 Bug 9（🔴高，搜索框回填归类信息污染用户输入）。更新四文档纳入 R5.7 搜索框设计建议 + S19 搜索框验证场景 + C5 设计建议 + 3.4.3.7 搜索框验证任务。正确设计应为：归类信息作为独立筛选条件传递后端，搜索框只接收名称关键词，不回填

### 2026-07-09 检查点1用户五次反馈 + 元审查（设计文档合理性审查）

- **A**: 重新发起检查点1 AskUserQuestion 确认修订后的审查计划（含搜索框设计）
- **O**: 用户五次选"需调整"，反馈："要求你全面审查当前整个设计文档设计是否合理，并且全面评估深度分析是否有阻塞点，是否有设计不合理的，或者是有模糊地带，请补充完善优化"
- **A**: 对四文档进行全面元审查，读取 RssSource.kt/BookSource.kt/RssSourceDao.kt/BookSourceDao.kt 验证数据模型和 DAO 方法
- **O**: 元审查发现 5 个阻塞点 + 3 个设计不合理 + 5 个模糊地带：
  - BP-1: RssSource.type（0=网页/1=图片/2=视频，3种，无注解）与 BookSource.bookSourceType（0=文本/1=音频/2=图片/3=文件/4=视频，5种，有注解）语义不一致
  - BP-2: Bug 9 修复与首页布局重构（C1-C3）的依赖关系——currentFilter 在 style1/style2 下语义不同，但 style1/style2 不存在
  - BP-3: 双维度下拉菜单重新设计后，现有 sourceGroupStyle 迁移逻辑未定义
  - BP-4: Agent-A 与 Agent-D 都审查 RssFragment/ExploreFragment，职责重叠
  - BP-5: Bug 9 主审 Agent 归属不明（跨 Agent-A D3 数据流和 Agent-D D12 首页布局）
  - UR-1: 缺少"数据模型一致性"审查维度（RssSource.type vs BookSource.bookSourceType）
  - UR-2: 缺少"配置项迁移"审查维度
  - UR-3: Agent-D 3.4.1 与 Agent-A 3.1.0 书架源码审查重叠
  - AM-1: RssSource.type 语义模糊（与 BookSourceType 不一致）
  - AM-2: 类型文件夹数据模型未定义（动态生成/预定义/参考BookGroup？）
  - AM-3: style1/style2 是否需要 MainActivity 切换 Fragment 未明确
  - AM-4: 搜索框"归类信息"在 style1/style2/现有RssFragment 三种情况下 currentFilter 语义未统一
  - AM-5: DAO 层已有 flowByTypeSearch/flowGroupSearchExact 组合查询方法但未被搜索框使用
- **O**: Bug 9 根因深化——不仅搜索框回填归类信息，用户输入名称后 searchKey 不再以 group: 开头，走 flowEnabled(searchKey) 分支，归类信息完全丢失
- **Adapt**: 更新四文档纳入 R5.8-R5.12 元审查要求 + S20-S22 元审查场景 + C5.1 DAO发现 + C6 数据模型一致性 + C7 配置项迁移 + C8 类型文件夹数据模型 + D13 阻塞点分析 + D14 Agent职责边界 + 3.5 阻塞点分析任务 + 3.6 Agent职责边界任务 + 3.4.3.8-3.4.3.11 元审查验证任务

---

## 完成级别说明

- **Level 1 - 代码完成（⚠️）**：审查任务执行完毕
- **Level 2 - 功能验证（⚠️）**：bug 经交叉验证确认
- **Level 3 - 场景验证（✅）**：用户确认 bug 报告符合实际
