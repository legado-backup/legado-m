# 订阅搜索范围上下文修复 spec

> 功能名：fix-rss-search-scope
> 模块：订阅页搜索（RssFragment 经典形态 → RssSearchActivity 文章聚合搜索）
> 阶段：spec

## Intent

订阅页头部搜索按钮的定位是"搜索当前浏览范围内的订阅源文章资源"。当前实现中，用户已进入某个分组/文件夹/类型上下文后点击搜索，触发的仍是全局搜索（搜索全部启用且有 searchUrl 的订阅源），与用户"进入某范围内搜索该范围内资源"的直觉相悖，搜索范围与浏览上下文脱节。

问题锚点：`RssFragment.kt` L929-931 经典形态搜索按钮调用 `RssSearchActivity.start(requireContext(), null)`，第二个参数 searchScope 恒传 null（全局），未读取当前浏览上下文 `currentGroup` / `currentType`。

## Scope

### 做什么

1. `RssFragment.kt` 经典形态搜索按钮：按当前浏览上下文（currentGroup / currentType）计算 scope 并传入 `RssSearchActivity.start()`：
   - currentGroup = 普通分组名 → scope = 该分组
   - currentGroup = no_group 字符串（未分组）→ scope = 未分组源
   - currentType = 0/1/2（类型体系）→ scope = 网页/图片/视频类型
   - 全部上下文（currentGroup=null 且 currentType=-1）→ 传 null，保持全局现状
2. `RssSearchScope.kt` 扩展 token 语法支持：类型 token（@type:0/@type:1/@type:2）、未分组 token（@no_group），getRssSources 解析后走对应查询。
3. `RssSearchScope` 的 display / displayNames 对 token 映射友好文案（网页源/图片源/视频源/未分组源）。
4. `RssSourceDao` 按需新增按类型（type 字段）查询启用的可搜索源。

### 不做什么（明确列出）

1. 不改搜索引擎与结果逻辑（RssSearchModel 既有搜索流程、聚合展示不动）。
2. 不改现代形态 openRssSearch（`RssFragment.kt` L897，单源内容页搜索语义，传 source.sourceGroup 已合理）。
3. 不改设置页入口（`MySettingsData.kt` L283，全局搜索语义合理）。
4. like 模糊匹配本身保留（列表页等其他调用点仍依赖），但其子串误匹配在本次搜索链路内消除（见 R1）：getRssSources 分组分支对查询结果追加 hasGroup 精确判定，分组"A"不再混入分组"AB"的源。
5. 二级源标签（selectedRssTag 单源快捷过滤）不参与 scope 计算。

### 影响模块

| 模块 | 变更性质 |
|------|---------|
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | 修改：经典形态搜索按钮 scope 计算与传参（L929-931 附近） |
| `RssSearchScope.kt` | 修改：token 解析、getRssSources 分派、display/displayNames 映射 |
| `app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt` | 可能新增：按类型查询（type + searchUrl 非空 + enabled） |
| `app/src/main/res/values/strings.xml` | 可能新增：范围显示文案（实施时核实现有资源是否可复用） |

## Approach

### Selected Approach

RssSearchScope 扩展 token 语法，scope 仍为单一字符串通道，token 用 `@` 前缀避开用户分组名字面冲突：

| token | 语义 |
|-------|------|
| `@type:0` | 网页类型源 |
| `@type:1` | 图片类型源 |
| `@type:2` | 视频类型源 |
| `@no_group` | 未分组源（sourceGroup 为空白） |

实现要点：

1. **getRssSources 解析分派**（RssSearchScope.kt L87-116 现有逻辑内扩展）：
   - scope 为空 → 既有全部逻辑（启用 + searchUrl 非空），不变；
   - 解析逗号分隔项，命中 `@type:` token → 走新增 DAO 按类型查询；命中 `@no_group` → 复用既有 noGroup 查询（RssSourceDao L171-174 已存在）；其余 → 既有 getByGroup 分组查询 + hasGroup 精确过滤（消除 like 子串误匹配）；
   - 保留既有"无有效源回退全部"的兜底逻辑。
2. **display / displayNames 映射**：token → 友好文案（网页源/图片源/视频源/未分组源）；普通分组名照旧原文显示。
3. **RssFragment 经典形态搜索按钮**：读取 currentGroup / currentType（L241-244 状态定义、L1303-1325 onFolderClick、L260-269 一级胶囊 tagSelectedListener 维护的状态）计算 scope：
   - currentGroup 为普通分组名 → scope = 分组名；
   - currentGroup = no_group → scope = `@no_group`；
   - currentGroup = null 且 currentType = 0/1/2 → scope = `@type:{currentType}`；
   - 全部上下文 → scope = null（保持全局现状）。
4. **传递通道**：复用 `RssSearchActivity.start()` L492-497 已有的 searchScope 参数；receiptIntent（L352-356）`update(save=false)` 不持久化传入值，该通道现成，无需改动。

选择理由：

- 范围解析逻辑内聚在 RssSearchScope 单处，Activity/ViewModel/Model 链路零新增传递；
- receiptIntent save=false 通道现成，改动面最小；
- 搜索页手动切换范围等既有能力不受影响。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| RssSearchActivity.start 新增 type:Int 等独立参数直通 ViewModel | 链路散：需改 Activity/ViewModel/Model 多处传递；未分组仍需字符串表达；与既有 scope 体系割裂 |
| RssFragment 侧预查源列表（List&lt;RssSource&gt;）传给搜索页 | 跨层传实体破坏 RssSearchScope 抽象；Activity 间传大列表需序列化；搜索页切换范围能力需另建 |
| 仅传 currentGroup 字符串、不支持类型/未分组场景 | 覆盖不全：用户明确要求"标签可能是分组也可能是类型"，类型体系（sourceGroupStyle==1）下进入类型文件夹搜索范围无法表达；未分组分组名 getByGroup 匹配不到任何源 |

### Drawbacks

1. token 字符串进入 scope 后，display/displayNames 需特判映射，遗漏会显示原始 token（风险低，映射集中一处）。
2. `@` 前缀理论上与以 @ 开头的真分组名冲突（概率极低，接受）。
3. 分组名含逗号仍会破坏 scope 解析（既有全局行为，本次不新增风险也不修复）。
4. 搜索页既有范围菜单仅列普通分组名，传入的类型/未分组 token 范围在搜索页内不可重新选择（只能回订阅页重新进入再搜）——能力边界，登记接受，不为本目标扩菜单。
5. 现代形态（modernRssPage）是否存在"分组列表浏览"场景实施时核实（tasks 1.1）：若无则本方案覆盖完备；若核实存在，再评估是否同步（预判不需要——现代形态上下文是"当前源"而非分组列表）。

### Prior Art

项目内 `io.legado.app.ui.book.search.SearchScope`（书源搜索范围）同款"逗号分隔分组名"设计，RssSearchScope 即参考其简化而来；本次 token 扩展仅作用于 RssSearchScope，与书源体系无耦合。

## Requirements

- **R1** 经典形态进入普通分组（currentGroup=分组名）后点搜索：scope=该分组，仅搜索该分组内启用且有 searchUrl 的源；分组判定精确（hasGroup：多分组 sourceGroup="A,B" 命中 A，"AB" 不误命中）。
- **R2** 进入"未分组"（currentGroup=no_group 字符串）后点搜索：scope=未分组源（sourceGroup 为空白的源）。
- **R3** 类型体系进入类型文件夹/胶囊（currentType=0/1/2）后点搜索：scope=该类型（网页/图片/视频）下启用且有 searchUrl 的源。
- **R4** 根目录"全部"上下文（currentGroup=null 且 currentType=-1）点搜索：保持全局搜索现状。
- **R5** 搜索页内手动切换搜索范围的既有能力不受影响；传入 scope 不持久化到 AppConfig。
- **R6** 范围显示对 token 映射友好文案；现代形态与设置页入口行为不变。

## Scenarios

### 正常

- 文件夹视图点进分组A → 搜索 → 结果仅来自分组A的源。
- 类型视图点进"图片" → 搜索 → 结果仅来自图片类源。
- 标签视图一级胶囊选中分组B → 搜索 → 结果仅来自分组B。

### 边界

- 分组内无任何有 searchUrl 的源 → 沿用 RssSearchScope 既有回退逻辑（回退全部），不崩溃。
- 分组名恰为"未分组"字样 → 因 token 机制不受字面歧义影响。
- 搜索返回中用户切到别的分组再返回 → 搜索页 scope 为初始传入值（Activity 生命周期内不变）。
- 分组"A"与分组"AB"并存 → 进入"A"搜索时，hasGroup 精确过滤保证不混入"AB"的源（like 粗筛 + hasGroup 精筛两级）。

### 异常

- 数据库查询为空 / 网络搜索全部失败 → 沿用 RssSearchModel 既有错误处理，本次不新增异常路径。