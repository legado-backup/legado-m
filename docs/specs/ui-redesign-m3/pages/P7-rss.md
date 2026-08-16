# P7 RSS / 订阅源（Rss）

> **待改造页升级 v2（2026-08-13）**：对齐 RssFragment View 现状（P1 待接线）+ 登记 v2.8 预审 V1-V16 违例（含 rssSort/sourceLayout 双功能性 no-op）。另一 AI 开发本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssFragment（`ui/main/rss/`，View + RssViewModel + RssAdapter + SourceFolderAdapter）+ RssArticlesFragment/RssSortActivity（`ui/rss/article/`）
- **骨架归类**：S2 列表管理页（分组网格 + 文件夹 + 3 Tab）
- **对应 task**：tasks.md `12.16o`（v2.8 预审 A8）、`12.16l`（D1 RssSourceActivity 预审）；pages-inventory A8、D1-D8
- **fork 借鉴来源**：forks-deep-dive §7.2（HapeLee RssSourceScreen）、§12（huajideshutiao）；MoRealm

## 1. 设计意图（一段话）

订阅页是 RSS 内容中枢，核心目标 = **订阅源一目了然 + 分组筛选 + 文章智能分发**。与旧版差异：统一 `BadgeDot` 未读小圆点、分组 `GroupHeader` 折叠渲染、顶栏 `GlassTopAppBar` + `SettingsSearchBar`。**本文档是验收的「为什么」：订阅页改造必须先修两个功能性缺陷（rssSort 排序 no-op / sourceLayout no-op），再谈视觉收敛。**

## 2. 布局结构（文字框图 + 区块表）

```
┌──────────────────────────────────────┐
│ 顶栏（V1/V2：私有 TitleBar+SearchView  │ ← GlassTopAppBar + SettingsSearchBar 待换
│ 待换 SettingsSearchBar+GlassTopAppBar）│
├──────────────────────────────────────┤
│ 分组 chips / 3 Tab（网页/图片/视频）     │ ← V6：无 GroupHeader → 待接线
├──────────────────────────────────────┤
│ 列表项 [封面RSS图标] 源名+文章数        │
│        最后更新(灰)  ●新 n 推送        │ ← BadgeDot 小圆点
│ 左滑：收藏/置顶/删除                    │
├──────────────────────────────────────┤
│ 空态/加载态（V8：tv_empty_msg 死控件）  │ ← EmptyStatePlaceholder 待换
└──────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 顶栏 | `GlassTopAppBar`（§3.4：surface 实底） | — | V1 待修 |
| 搜索 | `SettingsSearchBar`（§3.4：孤儿）+ 搜索词升 VM | RssViewModel | V2 待修 |
| 分组 | `GroupHeader`（§3.4：titleSmall Bold + 徽标） | 分组 6 分支查询 | V6 待修 |
| 列表项 | `BadgeDot`（§3.4：error 底/10sp/99+）+ 卡片 | Room Flow | |
| 布局切换 | `ListLayoutMenu`（§3.4：受控组件） | AppConfig.rssSort | V3 待修 |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `GlassTopAppBar` | surface 实底、titleMedium | 顶栏（V1 待接线） |
| `SettingsSearchBar` | 搜索栏（孤儿） | 搜索（V2 待接线） |
| `ListLayoutMenu` | DropdownMenu 两区、选中 primary | 布局切换+排序（V3 待接线） |
| `GroupHeader` | titleSmall Bold、行≥48dp | 分组渲染（V6 待接线） |
| `BadgeDot` | error 底、10sp、99+ | 未读小圆点 |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空态（V8 待接线） |

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点源 | 进 RssArticlesFragment 文章列表 | ✅ | |
| 点文章 | openRss 智能分发（singleUrl→ReadRss 或浏览器；否则取 HTML） | ✅ | |
| 左滑 | 收藏/置顶/删除 | ✅ | |
| 长按 | 编辑/置顶/登录/删除/禁用 | ✅ | V10 PopupMenu 待下沉 |
| 顶栏搜索 | 提交跳 RssSearchActivity | ✅ | |
| 头部规则订阅 | 进 RuleSubActivity | ✅ | |

## 5. 状态管理（§4 范式）

- **⚠️ V7 违例待修**：Fragment 12 私有态（:77-105）+ 2 个 Flow Job + Room Flow collect 在 Fragment（:357-419）——RssViewModel 零状态零 StateFlow 仅 6 动作方法，需收敛 VM StateFlow。
- 旋转丢筛选态无 onSaveInstanceState——补 `rememberSaveable`。
- **功能性缺陷（P1 优先，2026-08-13 收敛代码级修复路径）**：
  - **V4 rssSort no-op**：`RssSourceDao.kt:27/33/39/40/48/58/62` 全部 `order by customOrder` 硬编码，`RssSourceSort` enum（Default/Name/Url/Update/Enable）为死代码。**修复路径**：Room `@Query` 不支持动态 ORDER BY，需 `@RawQuery(orderBy=true)` 拼 `ORDER BY {column} {ASC|DESC}`——排序列映射表 `RssSourceSort→(customOrder|sourceName|sourceUrl|lastUpdateTime|enabled)`，升降序read `AppConfig.rssSortAscending`；现有 `flowAll`/`flowSearch`/`flowGroupSearch`/`flowByType` 等全部改为带排序参数版本；ViewModel 暴露 `sortBy(sort, ascending)` 切换后重新 collect；前端 `ListLayoutMenu` 排序项（点同维度翻转）→ VM.sortBy。
  - **V5 sourceLayout no-op**：`RssFragment.kt:241-245` `applyListView()` 恒 `GridLayoutManager(context, 4)`（line 243 死代码，忽略 `AppConfig.sourceLayout`）。**修复路径**：`applyListView()` 读 `AppConfig.sourceLayout` 三态——列表→`LinearLayoutManager` / 紧凑→`GridLayoutManager(context, 2)` / 网格→复用 `applyFolderView` 的 `calculateSpanCount(requireContext(), marginDp)` 逻辑（`RssFragment.kt:249-254` 模式）；保存侧确认 `rgLayout` 已写 `AppConfig.sourceLayout`（设计文档已确认保存生效，只欠读取应用）。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 现状无骨架屏 | **V8 待修**：加载态用 `ShelfGridSkeleton`（§5 规范列表加载组件） |
| 空态 | tv_empty_msg 死控件零引用（fragment_rss.xml:37-49） | **V8 待修**：`EmptyStatePlaceholder` |
| 错误 | 仅 AppLog.put（:360-361/:413-414）无占位无重试 | **V8 待修**：错误分支 + 重试 |

## 7. i18n 与无障碍

- 已符合（v2.8 C）：用户可见文案全 R.string（:204,230,271-274,279-280,345-352+两菜单全 @string）；Kotlin 硬编码色 0。
- **⚠️ V11 待修**：i18n 硬编码 6 处（订阅界面获取分组数据失败 :361/订阅界面更新数据出错 :414/view_search.xml:19 搜索/strings.xml type_image 等英文文件中文值/1761-1763 source_group_mode 同款）
- 触控 ≥48dp（item_rss.xml:15 已符合）；Icon contentDescription。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（顶栏 + 分组 chips/3Tab + 列表 + 空态）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] **V4**：rssSort 排序真实生效（**`@RawQuery` 动态 ORDER BY + 排序列映射 + 升降序 read `AppConfig.rssSortAscending`**，见 §5 修复路径）+ ListLayoutMenu 持久化
- [ ] **V5**：sourceLayout 布局切换真实生效（**`applyListView()` 读 `AppConfig.sourceLayout` 三态转 layoutManager**，见 §5 修复路径）
- [ ] **P1 前置序全过**：**V4/V5（功能性缺陷：rssSort 排序生效 + sourceLayout 布局生效，先修否则视觉收敛后依然不生效）** → V8（view_search 中文 hint）→ V1/V2（GlassTopAppBar+SettingsSearchBar）→ V3（ListLayoutMenu）→ V10（菜单族）→ V6（GroupHeader）→ V7（状态收敛）→ V11（i18n）
- [ ] 三态齐全；空态/错误态文案 i18n
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory A8）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App RSS订阅源列表页高保真：RSS图标圆形 + 源名 + 灰色更新时间
一排,右侧小绿点未读标识,分组chips 顶部可横滑,卡片圆角18dp留白,底部导航栏,
浅色极温暖色调,无明艳高饱和,中文界面
```

## 10. 变更记录

- 2026-08-13：v2 升级——对齐 RssFragment View 现状，登记 V1-V16 违例 + 双功能性缺陷（rssSort/sourceLayout no-op，P1 优先），P1 接线前置序（对应 task 12.16o）。
