# Spec: 昨日改动深度审查

## Intent（意图）

对 2026-07-08 的全量改动进行**自我反省式深度审查**，主动发现 bug 而非被动等待用户反馈。用户明确告知"肯定有 bug，而且不少"，并指出改动过程中"来回横跳，来回改"的混乱现象。本审查的目标是：

1. **定位所有 bug**：覆盖编译期、运行期、逻辑期、体验期四个层面
2. **验证任务完成度**：对照 4 个 spec 的 tasks.md，核实"代码完成 / 功能验证 / 场景验证"三级完成度的真实性
3. **暴露设计与实施的不一致**：特别是 spec 设计与实际代码偏离的情况
4. **为修复提供精准定位**：每个 bug 给出文件:行号、根因、影响、修复方向

## Scope（范围）

### 在范围内

| 范围 | 说明 |
|------|------|
| **首页布局架构对比**（核心维度，用户检查点1二次反馈） | RssFragment（订阅源首页）/ ExploreFragment（发现页首页）是否参考书架 style1（Tab+ViewPager）/ style2（单RV混排）深度设计。**用户明确要求改的是首页，不是管理页** |
| **书架布局核心机制对比**（核心维度） | 以书架布局（BaseBooksAdapter 共享基类 + Fragment 级重建 + RecycledViewPool 隔离 + 浏览/管理分离哲学 + style1/style2 切换）为基准，逐项对比书源订阅源布局"学到了什么 / 漏掉了什么" |
| 书源/订阅源**管理页**布局重做 | BookSourceActivity / RssSourceActivity / 4 个 Adapter / SourceFolderAdapter（昨天改的对象，存在 Bug 1-8，但**非用户核心需求**） |
| 书源/订阅源**首页**布局现状 | RssFragment / ExploreFragment 当前只有简单"文件夹视图 vs 列表视图"切换，**缺书架 style1（Tab+ViewPager）和 style2（单RV混排+点击进入）设计** |
| 视频播放器改动 | VideoPlayer / VideoPlay / ChoiceSpeedDialog / SettingsDialog / ExoPlayerManager / ExoVideoManager / Exo2MediaPlayer / VideoPlayerActivity / 布局 |
| 数据库 Migration | RssSource @ColumnInfo defaultValue 变更 + DatabaseMigrations.kt + schema 92→93 |
| 任务清单一致性 | 4 个 spec 的 tasks.md 状态 vs 实际代码 |
| 配置项闭环 | PreferKey → AppConfig → 读取点 → 生效链路 |
| 菜单项闭环 | menu XML → onCompatOptionsItemSelected → 实际处理 |

### 不在范围内

- 昨天其他改动（cronet 升级、自动任务系统、高亮规则、调试工具、网络层优化等）的深度审查——仅在发现与两大改动耦合时附带审查
- bug 修复（修复将在用户确认后通过独立 OpenSpec 流程执行）
- 性能基准测试（仅审查代码逻辑，不跑性能用例）

## Approach（方法）

### Selected Approach（选定方案）

**书架对比优先 + 多 Agent 并行审查 + 交叉验证 + 主线汇总**：

0. **书架对比优先**（核心维度）：先深入研究书架布局的核心机制（A1-A6），建立"书架布局架构基准"，再逐项对比书源订阅源布局的差距（B1-B6），定位"徒有其表"的具体 bug（Bug 1-8）。此维度是用户在检查点1反馈要求强化的核心。
1. 按"书源订阅源布局"和"视频播放器"两个维度启动独立审查 Agent，每个 Agent 深入审查对应模块的所有源码
2. 额外启动 1 个 Agent 审查"配置项闭环 + 菜单项闭环 + 数据库 Migration"横向链路
3. 主线（本 AI）汇总各 Agent 发现，交叉验证（同一 bug 被多 Agent 发现则置信度高）
4. 输出结构化 bug 报告，每个 bug 包含：编号 / 严重度 / 文件:行号 / 根因 / 影响 / 修复方向 / 置信度

**理由**：用户反馈明确指出"只学到了表象，没有抓住核心"，要求以书架布局为基准对比审查。书架布局的核心是 `BaseBooksAdapter<VB>` 共享基类（统一 DiffUtil/payload/notification/CallBack），而书源订阅源布局只复制了配置项命名和多 adapter 切换形式，未复制共享基类架构，导致 compact/grid 模式下选择/拖拽/批量操作/校验刷新全部断裂。昨日改动涉及 168+ 文件，单次上下文无法容纳全部源码审查，必须多 Agent 并行。

### Alternatives Considered（替代方案）

| 替代方案 | 否决理由 |
|---------|---------|
| 单 Agent 串行审查全部文件 | 上下文超限；串行耗时长；无法交叉验证 |
| 只审查 tasks.md 标记未完成的项 | tasks.md 本身与代码不一致（L-07），不可作为审查依据 |
| 直接跑 E2E 测试发现 bug | E2E 测试只能发现运行期崩溃，无法发现逻辑错误/体验问题/配置耦合；且 E2E 基础设施昨天才建，未验证可靠 |
| 只依赖编译通过判定无 bug | 编译通过 ≠ 无 bug（所有疑似 bug 都能编译通过）；用户已明确否定此做法 |
| 询问用户直接告知 bug | 用户明确要求"先自我反省发现"，拒绝直接提供 |

### Drawbacks（缺点）

| 缺点 | 接受理由 |
|------|---------|
| 多 Agent 审查可能漏掉跨模块耦合 bug | 主线汇总时会专门检查跨模块耦合点（如共享配置项 sourceSort） |
| 静态审查无法发现运行期才暴露的 bug（如 ANR、内存泄漏） | 会结合生命周期分析 + 资源释放路径分析辅助发现；运行期 bug 标注"需真机验证" |
| 初步发现可能含误报 | 每个 bug 标注置信度，深度审查阶段验证后调整 |
| 审查耗时较长 | 用户要求"深度全面"，时间换质量可接受 |

### Prior Art（参考）

- AGENTS.md "复杂任务处理流程"五阶段流水线（Phase 1-5）
- AGENTS.md "OpenSpec 工作流程"检查点机制
- 昨日 source-layout-redesign AOAdapt 日志中记录的"菜单 XML 定义了选项 ≠ Activity 有处理逻辑"教训

## Requirements（需求）

### R1: 审查覆盖性

- R1.1 必须审查两大改动的所有核心源码文件（书源订阅源 20+ 文件、视频 10+ 文件）
- R1.2 必须验证每个配置项的"PreferKey → AppConfig → 读取 → 生效"完整闭环
- R1.3 必须验证每个菜单项的"XML 定义 → onCompatOptionsItemSelected → 实际处理"闭环
- R1.4 必须核实 4 个 spec 的 tasks.md 每一项的真实完成级别（Level 1/2/3）

### R2: Bug 报告质量

- R2.1 每个 bug 必须包含：编号 / 严重度（🔴高/🟡中/🟢低）/ 文件:行号 / 根因 / 影响 / 修复方向 / 置信度
- R2.2 不得有"可能有问题"的模糊描述，必须给出具体代码证据
- R2.3 误报率应 < 20%（深度审查验证后）

### R3: 审查纪律

- R3.1 审查阶段只读不改，任何修复须用户确认后另开 OpenSpec
- R3.2 不得因为"编译通过"就判定无 bug
- R3.3 不得跳过 tasks.md 中标记为完成但实际未验证（Level 2/3 缺失）的项

### R4: 书架对比审查（核心，用户检查点1反馈要求）

- R4.1 必须以书架布局的核心机制（A1-A6）为基准，逐项对比书源订阅源布局的差距（B1-B6）
- R4.2 必须验证"书架的 `BaseBooksAdapter<VB>` 共享基类架构"在书源订阅源中是否被复制——若未复制，必须定位因此导致的所有断裂 bug（选择/拖拽/批量操作/校验刷新）
- R4.3 必须验证书架的"Fragment 级重建（EventBus.RECREATE）+ RecycledViewPool 隔离"在书源订阅源中是否被复制——若未复制，必须定位布局切换时的状态丢失/视图复用混乱 bug
- R4.4 必须验证书架的"浏览界面与管理界面分离哲学"在书源订阅源中是否被遵守——若未遵守，必须定位浏览/管理模式混淆 bug
- R4.5 每个书架对比 bug 必须给出：书架怎么做（正确基准） / 书源订阅源怎么做（错误现状） / 差距导致的 bug 现象 / 修复方向

### R5: 首页布局架构审查（核心，用户检查点1二次反馈要求）

- R5.1 必须验证 RssFragment（订阅源首页）和 ExploreFragment（发现页首页）是否参考书架 style1（Tab+ViewPager，每个分组一个 Tab，ViewPager 滑动切换）设计——若未参考，定为"首页缺 style1 设计"问题
- R5.2 必须验证 RssFragment 和 ExploreFragment 是否参考书架 style2（单RV混排，分组文件夹+源混排，点击文件夹进入子目录，返回键回到根目录）设计——若未参考，定为"首页缺 style2 设计"问题
- R5.3 必须验证书架根据 `bookGroupStyle`（0=标签→style1，1=文件夹→style2）切换 Fragment 的机制在订阅源/发现页是否被复制——若未复制，定为"首页缺样式切换"问题
- R5.4 必须区分"管理页布局 bug"（Bug 1-8，昨天改的对象）和"首页布局缺失"（用户真正要的）两类问题，不得混淆
- R5.5 审查报告必须明确指出：昨天的改动**改错了对象**（改了管理页 RssSourceActivity/BookSourceActivity，而非首页 RssFragment/ExploreFragment），这是需求理解偏差
- R5.6 **布局配置对话框应支持双维度下拉菜单**（用户三次反馈核心设计建议）：
  - **归类维度**下拉菜单：按分组 / 按类型（文本/音频/图片/文件/视频，对应 BookSourceType.default/audio/image/file/video）
  - **样式维度**下拉菜单：标签（style1 Tab+ViewPager）/ 文件夹（style2 单RV混排）
  - 4 种组合：按分组+标签 / 按分组+文件夹 / 按类型+标签 / 按类型+文件夹
  - 这比书架更复杂（书架只按 group 归类），是书源/订阅源特有的增强设计
- R5.7 **首页搜索框应默认带当前归类信息传递给后端，不回填搜索框**（用户四次反馈核心设计建议）：
  - 归类信息（类型字段或分组字段）作为独立的筛选条件传递给后端查询，**不回填到搜索框**
  - 当前按类型=文本归类展示时，搜索时默认带上 type=0（文本）传递给后端
  - 当前按分组归类展示时，搜索时默认带上 group=分组名 传递给后端
  - 搜索框只接收用户输入的名称关键词，不显示归类前缀（如 `group:xxx`）
  - 当前 RssFragment/ExploreFragment 的 onFolderClick 把 `group:$group` 回填到 searchView（Bug 9），是错误设计
- R5.8 **数据模型一致性审查**（元审查发现 BP-1/AM-1/AM-2）：
  - 必须验证 RssSource.type（0=网页/1=图片/2=视频，3种，无@BookSourceType.Type注解）与 BookSource.bookSourceType（0=文本/1=音频/2=图片/3=文件/4=视频，5种，有@BookSourceType.Type注解）的语义差异
  - 必须验证"按类型"归类在订阅源上只有3种类型、书源有5种类型的不一致
  - 必须定义"按类型+文件夹"组合中类型文件夹的数据模型（动态生成 or 预定义？BookSource/RssSource 无"类型分组"实体）
- R5.9 **配置项迁移审查**（元审查发现 BP-3）：
  - 必须审查双维度下拉菜单重新设计后，现有 sourceGroupStyle（0=列表/1=按分组/2=按类型）如何迁移到新的双维度配置（归类维度+样式维度）
  - 必须定义迁移逻辑（如 sourceGroupStyle=1 → 归类维度=按分组+样式维度=?）
- R5.10 **Agent 职责边界明确**（元审查发现 BP-4/BP-5）：
  - 必须明确 Agent-A（3.1.1.6 审查 RssFragment/ExploreFragment 菜单处理 D2）与 Agent-D（3.4.2.1 审查 RssFragment/ExploreFragment 布局架构 D12）的分工边界
  - 必须明确 Bug 9（搜索框回填）的主审 Agent（Agent-A D3 数据流 vs Agent-D D12 首页布局）
- R5.11 **阻塞点与依赖关系分析**（元审查发现 BP-2/AM-3/AM-4）：
  - 必须分析 Bug 9 修复与首页布局重构（C1-C3 style1/style2）的依赖关系
  - 必须明确 style1/style2 是否需要 MainActivity 切换 Fragment（参考书架）还是只在 RssFragment 内部切换
  - 必须统一搜索框"归类信息"在 style1（当前Tab）/style2（当前文件夹）/现有RssFragment（onFolderClick group参数）三种情况下的 currentFilter 语义
- R5.12 **DAO 组合查询方法使用情况审查**（元审查发现 AM-5）：
  - 必须验证 flowByTypeSearch(type, searchKey) 和 flowGroupSearchExact(group, searchKey) 已存在于 DAO 层但未被 RssFragment/ExploreFragment 搜索框使用
  - 必须确认 Bug 9 修复方向应引用这些已有 DAO 方法，而非回填搜索框

## Scenarios（场景）

### S1: 配置项耦合场景（验证 L-01）

```
前置：AppConfig.sourceSort 当前值 = 0
操作1：用户进入订阅源管理 → 菜单 → 排序 → 名称 → sourceSort = 1
操作2：用户切到书源管理 → 进入页面
预期（正确）：书源按旧 sort 逻辑（Default）排序
实际（疑似 bug）：书源 sortSources 读到 sourceSort=1，按名称排序（与用户在书源菜单的选择不符）
```

### S2: 未分组文件夹场景（验证 L-02）

```
前置：sourceGroupStyle=2（按分组），存在分组"小说"和未分组源
操作：点击"未分组"文件夹
预期（正确）：列表只显示未分组的源
实际（疑似 bug）：currentGroup=null，upBookSource 走 flowAll 分支，显示全部源
```

### S3: 换集静音场景（验证 V-04）

```
前置：muteOnStart=true，用户播放视频 A
操作1：用户点击静音按钮取消静音（isMuted=false，player.setNeedMute(false)）
操作2：用户换集（onAutoCompletion → upDurIndex → startPlay → onPrepared）
预期（正确）：换集后保持用户取消静音的状态
实际（疑似 bug）：onPrepared 中 if(muteOnStart) setNeedMute(true)，重新静音
```

### S4: cachePlay 空操作场景（验证 V-01/V-02）

```
前置：用户打开视频设置
操作：寻找"边下边播"开关
预期（按 m3u8-cache tasks.md）：dialog_video_settings.xml 含 cb_cache_play 开关
实际：SettingsDialog.kt 无 cb_cache_play 处理；VideoPlay.cachePlay 已 @Deprecated 恒返回 false
结论：video-m3u8-cache spec 的 4 处 setUp(url, cachePlay, ...) 实际传入 false，是空操作
（注：ExoPlayer SimpleCache 已默认接管缓存，功能上不影响，但 spec 与代码严重不一致）
```

### S5: sourceLayout 边界场景（验证 L-04）

```
前置：AppConfig.sourceLayout 被外部修改为 7（或负数）
操作：applyListView 执行
预期（正确）：容错处理（回退列表或限制范围）
实际（疑似 bug）：
  - applyListView: else 分支 → GridLayoutManager(this, 7) + adapterGrid
  - collect: else 分支 → adapter.setItems（列表 adapter）
  - 布局是网格，数据填到列表 adapter，显示错乱
```

### S6: 任务清单真实性场景（验证 L-07）

```
前置：查看 video-m3u8-cache/tasks.md
操作：核对每项任务与实际代码
预期（按 tasks.md）：所有任务 [ ] 未完成
实际：AOAdapt 日志说"实施完成"，但 tasks.md 全部 [ ] 未勾选
结论：tasks.md 与实际完成状态严重脱节，无法反映真实进度
```

### S7: 书架对比——选择模式断裂（验证 Bug 1，🔴高）

```
前置：书源管理页面，sourceLayout=2（紧凑模式）
操作1：长按某条源进入选择模式（list adapter 的 selection）
操作2：点击"全选"菜单
预期（书架基准）：BaseBooksAdapter 统一 selection，全选作用于当前显示的所有源
实际（书源订阅源 bug）：
  - compact/grid adapter 无 selection 字段
  - selectAll 硬编码 adapter.selection（L598），操作的是 list adapter，但当前显示的是 compact adapter
  - 全选无效，批量操作（启用/禁用/删除/校验）全部失效
书架怎么做：BaseBooksAdapter<VB> 共享基类统一 selection，任意布局模式选择/批量操作一致
书源订阅源怎么做：三 adapter 各自独立，无共享基类，selection 只在 list adapter
```

### S8: 书架对比——拖拽排序断裂（验证 Bug 2/4，🟡中）

```
前置：书源管理页面，sourceLayout=2（紧凑模式）
操作：长按拖拽源进行排序
预期（书架基准）：ItemTouchHelper 绑定当前显示的 adapter，拖拽生效
实际（书源订阅源 bug）：
  - itemTouchCallback by lazy { ItemTouchCallback(adapter) }（L100）永远绑定 list adapter
  - compact/grid 模式下，ItemTouchHelper 拖拽的是 list adapter，但显示的是 compact/grid adapter
  - 拖拽无响应或拖拽了不可见的列表
  - isCanDrag 条件不一致：applyListView 含 layout==0（L362），collect 块缺少（L495）
书架怎么做：BooksFragment 按 bookshelfLayout 创建对应 adapter，ItemTouchHelper 绑定当前 adapter
书源订阅源怎么做：ItemTouchHelper 永远绑定 list adapter，与显示的 adapter 错位
```

### S9: 书架对比——校验进度刷新断裂（验证 Bug 5，🟡中）

```
前置：书源管理页面，sourceLayout=2（紧凑模式），执行批量校验
操作：校验过程中观察进度刷新
预期（书架基准）：upBookSource notification 统一刷新当前显示的 adapter
实际（书源订阅源 bug）：
  - upBookSource collect 块按 sourceLayout 分发数据到不同 adapter（L489-494）
  - 但 notification 等操作可能只作用于 list adapter
  - compact/grid 模式下校验进度不刷新
书架怎么做：BaseBooksAdapter 统一 notification，任意布局模式进度刷新一致
书源订阅源怎么做：数据分发到不同 adapter，但通知操作可能错位
```

### S10: 书架对比——布局切换状态丢失（验证 B2/B5）

```
前置：书源管理页面，sourceLayout=0（列表），滚动到第 50 条
操作：菜单切换为 sourceLayout=2（紧凑）
预期（书架基准）：EventBus.RECREATE 触发 Fragment 重建，RecycledViewPool 隔离 list/grid，状态正确恢复
实际（书源订阅源 bug）：
  - 书源订阅源布局切换只在 Activity 内 applyListView，无 Fragment 重建
  - 无 RecycledViewPool 隔离，list/grid 共用同一 pool，ViewHolder 类型冲突
  - 滚动位置丢失，视图复用混乱
书架怎么做：postEvent(EventBus.RECREATE, "") 重建 Fragment + 独立 RecycledViewPool
书源订阅源怎么做：applyListView 直接替换 layoutManager + adapter，无重建无隔离
```

### S11: 书架对比——排序状态不同步（验证 Bug 7，🟡中）

```
前置：书源管理页面
操作1：菜单 → 排序 → 名称 → AppConfig.sourceSort = 0（BookSource 菜单强制设为 0）
操作2：菜单 → 布局设置 → 排序 → 名称 → AppConfig.sourceSort = 1
预期（书架基准）：配置对话框与菜单排序状态一致
实际（书源订阅源 bug）：
  - 菜单排序强制 sourceSort=0（L205-252），配置对话框排序设 sourceSort=1
  - 两个入口设置的 sourceSort 值冲突，用户在菜单选的排序被配置对话框覆盖，反之亦然
书架怎么做：BaseBookshelfFragment.configBookshelf 统一管理 bookshelfSort，菜单与对话框一致
书源订阅源怎么做：菜单和配置对话框各自设置 sourceSort，语义冲突
```

### S12: 书架对比——浏览/管理分离哲学（验证 B4/B6）

```
前置：书架有"浏览界面（BooksFragment）"和"管理界面（BookshelfManageActivity）"分离
操作：书源管理页面同时承担浏览和管理职责
预期（书架基准）：浏览界面只读展示，管理界面支持选择/批量操作/拖拽
实际（书源订阅源 bug）：
  - BookSourceActivity 一个界面同时承担浏览和管理
  - compact/grid 模式下选择模式失效（Bug 1），拖拽失效（Bug 2）
  - 文件夹视图与列表视图互斥，无源计数（Bug 6）
书架怎么做：BooksFragment（浏览）+ BookshelfManageActivity（管理）分离
书源订阅源怎么做：BookSourceActivity 单界面混担，compact/grid 管理功能断裂
```

### S13: 书架对比——RssSource 同构问题（验证 Bug 3/4，🔴高）

```
前置：订阅源管理页面，sourceLayout=2（紧凑模式）
操作：长按进入选择模式 + 全选 + 批量删除
预期（书架基准）：选择/批量操作一致生效
实际（书源订阅源 bug）：
  - RssSourceActivity 与 BookSourceActivity 同构问题
  - compact/grid adapter 无 selection，selectAll/revertSelection 硬编码 adapter.selection
  - DragSelectTouchHelper 失效（Bug 4）
书架怎么做：统一 BaseBooksAdapter 架构
书源订阅源怎么做：三 adapter 独立，无共享基类
```

### S14: 书架对比——文件夹视图 ItemTouchHelper 残留（验证 Bug 8，🟢低）

```
前置：书源管理页面，sourceGroupStyle=2（按分组），点击进入文件夹视图
操作：在文件夹视图内长按拖拽
预期（书架基准）：拖拽行为与当前显示的 adapter 匹配
实际（书源订阅源 bug）：
  - 文件夹视图切换时，ItemTouchHelper 仍 attached 到 RV
  - folderAdapter 未实现 ItemTouchHelper.Callback
  - 拖拽无响应或异常
书架怎么做：N/A（书架无文件夹视图，此为书源订阅源新增功能）
书源订阅源怎么做：folderAdapter 未实现 Callback，ItemTouchHelper 残留
```

### S15: 首页缺 style1 设计（验证 R5.1，需求偏差核心问题）

```
前置：书架 bookGroupStyle=0（标签）→ BookshelfFragment1（Tab+ViewPager，每个分组一个 Tab）
操作：用户在订阅源首页（RssFragment）期望像书架一样按分组 Tab 展示
预期（书架 style1 基准）：
  - 订阅源首页有 TabLayout，每个分组一个 Tab（如"全部""未分组""小说""新闻"等）
  - ViewPager 滑动切换分组，每个 Tab 对应一个独立的 Fragment 显示该分组的源
实际（RssFragment 现状）：
  - RssFragment 只有"文件夹视图（SourceFolderAdapter）vs 列表视图（RssAdapter）"二选一切换
  - 没有 Tab + ViewPager 设计
  - 没有"每个分组一个 Tab"的平铺展示
结论：订阅源首页缺书架 style1（标签样式）设计，用户要的"首页参考书架布局"未实现
```

### S16: 首页缺 style2 设计（验证 R5.2，需求偏差核心问题）

```
前置：书架 bookGroupStyle=1（文件夹）→ BookshelfFragment2（单RV混排，分组文件夹+书籍混排）
操作：用户在订阅源首页（RssFragment）期望像书架一样分组文件夹+源混排，点击文件夹进入
预期（书架 style2 基准）：
  - 根目录显示分组文件夹 + 未分组源 混排在同一列表
  - 点击分组文件夹 → 进入该分组，只显示该分组的源
  - 返回键 → 回到根目录（groupId = IdRoot）
  - getItems() = bookGroups + books（混排）
实际（RssFragment 现状）：
  - RssFragment 的"文件夹视图"只是显示文件夹列表（all_groups/no_group/各分组名）
  - 点击文件夹 → 切换到列表视图 + searchView 筛选（onFolderClick 设 isShowingFolder=false）
  - 没有书架 style2 的"分组文件夹+源混排在同一列表"设计
  - 没有"点击进入子目录 + 返回键回根目录"的导航逻辑
结论：订阅源首页缺书架 style2（文件夹样式）深度设计，只有浅层文件夹概念
```

### S17: 首页缺样式切换机制（验证 R5.3，需求偏差核心问题）

```
前置：书架根据 bookGroupStyle（0=标签→style1，1=文件夹→style2）在 MainActivity 切换 Fragment
操作：用户期望订阅源首页也能像书架一样选择"标签样式"或"文件夹样式"
预期（书架基准）：
  - MainActivity.getFragmentId 根据 sourceGroupStyle 返回不同的 Fragment ID
  - sourceGroupStyle=0 → RssFragment1（Tab+ViewPager 标签样式）
  - sourceGroupStyle=1 → RssFragment2（单RV混排 文件夹样式）
  - 切换时 Fragment 重建
实际（现状）：
  - MainActivity 没有 sourceGroupStyle 切换 Fragment 的机制
  - RssFragment 只有一个，内部用 isShowingFolder 切换文件夹/列表视图
  - 没有 style1/style2 两种 Fragment 架构
结论：订阅源首页缺书架的 style1/style2 Fragment 级切换机制
```

### S18: 双维度下拉菜单设计建议（验证 R5.6，用户三次反馈核心设计）

```
前置：书架只有 bookGroupStyle（0=标签/1=文件夹）一个维度，且只按 group 字段归类
操作：用户期望书源/订阅源首页布局配置对话框支持双维度下拉菜单
预期（用户设计建议）：
  布局配置对话框含两个下拉菜单：
  1. 归类维度下拉菜单：
     - 按分组（按 BookSource.group / RssSource.group 字段归类）
     - 按类型（按 BookSource.bookSourceType / RssSource.type 字段归类：文本/音频/图片/文件/视频）
  2. 样式维度下拉菜单：
     - 标签（style1 Tab+ViewPager，每个归类项一个 Tab）
     - 文件夹（style2 单RV混排，归类文件夹+源混排，点击进入）
  4 种组合：
  - 按分组+标签 → style1，每个分组一个 Tab
  - 按分组+文件夹 → style2，分组文件夹+源混排
  - 按类型+标签 → style1，每个类型一个 Tab（文本/音频/图片/文件/视频）
  - 按类型+文件夹 → style2，类型文件夹+源混排
实际（现状）：
  - 当前 SourceFolderAdapter.showConfigDialog 只有 sourceGroupStyle（0=列表/1=按分组/2=按类型）和 sourceMargin
  - 没有"样式维度"下拉菜单（标签/文件夹）
  - sourceGroupStyle 把"归类维度"和"视图模式"混在一起，不是双维度独立选择
结论：需重新设计布局配置对话框为双维度下拉菜单（归类维度+样式维度），参考书架 style1/style2 但增加按类型归类
```

### S19: 搜索框回填归类信息（验证 R5.7/Bug 9，用户四次反馈核心设计）

```
前置：订阅源首页（RssFragment），sourceGroupStyle=1（按分组），点击"小说"文件夹
操作：观察搜索框内容 + 输入名称关键词搜索
预期（用户设计）：
  - 搜索框为空（或只显示用户输入的关键词），不显示 "group:小说"
  - 搜索时后端查询条件 = group=小说 + name=用户输入的关键词
  - 归类信息作为独立筛选条件传递，不污染搜索框
实际（RssFragment 现状 Bug 9）：
  - onFolderClick 执行 searchView.setQuery("group:小说", true)
  - 搜索框被回填为 "group:小说"，用户看到归类前缀
  - 用户搜索名称时需先清空 "group:" 前缀，体验极差
  - 归类信息与搜索关键词混为一谈
结论：搜索框回填归类信息是错误设计，需改为独立筛选条件传递给后端
```

### S20: RssSource.type 语义与 BookSourceType 不一致（验证 R5.8/BP-1，元审查发现）

```
前置：双维度下拉菜单"按类型"归类选项
操作：对比 BookSource.bookSourceType 与 RssSource.type 的类型定义
预期（一致性）：
  - 两者使用相同的类型定义（BookSourceType: 0=文本/1=音频/2=图片/3=文件/4=视频）
  - 两者都有 @BookSourceType.Type 注解
实际（不一致）：
  - BookSource.bookSourceType: @BookSourceType.Type，0=文本/1=音频/2=图片/3=文件/4=视频（5种）
  - RssSource.type: 无注解，注释"0网页，1图片，2视频"（3种）
  - 订阅源"按类型"归类只有3种类型，书源有5种
  - DAO flowByType(type) 对两者都存在，但 type 参数语义不同
结论：RssSource.type 与 BookSourceType 语义不一致，双维度下拉菜单"按类型"选项需根据源类型动态调整
```

### S21: 配置项迁移阻塞点（验证 R5.9/BP-3，元审查发现）

```
前置：现有 sourceGroupStyle=1（按分组）的用户
操作：升级到双维度下拉菜单设计后
预期（迁移正确）：
  - sourceGroupStyle=1 → 归类维度=按分组 + 样式维度=???（需定义）
  - sourceGroupStyle=2 → 归类维度=按类型 + 样式维度=???（需定义）
  - sourceGroupStyle=0 → 归类维度=无 + 样式维度=列表（需定义）
实际（未定义）：
  - 当前 sourceGroupStyle 把"归类维度"和"视图模式"混在一个值里
  - 重新设计为双维度后，现有值的迁移逻辑未定义
  - 用户升级后可能丢失原有配置
结论：双维度下拉菜单设计需补充配置项迁移逻辑
```

### S22: DAO 组合查询方法已存在但未被使用（验证 R5.12/AM-5，元审查发现）

```
前置：RssFragment 搜索框，当前在"小说"文件夹内
操作：用户输入名称关键词搜索
预期（正确设计）：
  - 调用 flowGroupSearchExact("小说", "用户输入的关键词") 组合查询
  - 搜索框只显示用户输入的关键词
  - 归类信息"小说"作为独立参数传递
实际（现状 Bug 9）：
  - onFolderClick 把 "group:小说" 回填到 searchView
  - upRssFlowJob 解析 searchKey.startsWith("group:") 调用 flowEnabledByGroup
  - 用户输入名称时，searchKey 变成 "用户输入"（不再是 group: 开头），走 flowEnabled(searchKey) 分支
  - 归类信息丢失！用户在"小说"文件夹内搜索名称，实际搜索了全部源
结论：DAO 层已有 flowByTypeSearch/flowGroupSearchExact 组合查询方法，但搜索框未使用，导致归类信息与名称搜索无法组合
```
