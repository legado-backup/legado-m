# 主界面底栏精简 规格（spec.md）

## Intent

用户不喜欢默认底栏把「统计」作为一级 Tab，也不希望底栏右下角默认挂着搜索框。目标：默认底栏回归"书架/发现/订阅/我的"四项，统计信息收敛到「我的 → 工具 → 阅读记录」子页，并同步清理主题/底栏设置体系中对统计与搜索框的默认设置；同时移除「我的 → 工具 → 订阅源全局搜索」冗余菜单。**全部为默认行为收敛，不删除既有能力**（搜索能力、记录列表页、订阅源搜索能力均保留）。

## Scope

### 包含

1. 底栏默认项收敛为 4 项（书架/发现/订阅/我的），含侧边栏模式同步。
2. 阅读统计仪表盘（`ReadRecordFragment`）迁为独立子页，入口 =「我的 → 工具 → 阅读记录」。
3. 主题/底栏设置体系联动：「底栏项管理」弹窗、底栏包「图标编辑」弹窗移除统计条目；`NavigationBarIconConfig.items` / `MainBottomNavConfig.specs` 源头清理。
4. floating 底栏右下搜索框默认隐藏；默认值链（AppConfig / MainLayoutPresetConfig / Config 默认 / 外观管理内置预设 / 其他设置开关）全部对齐为"隐藏"。
5. 「我的 → 工具 → 订阅源全局搜索」行移除。

### 不包含

- 不删除 `RssSearchActivity`（订阅 Tab 顶栏搜索、订阅源内搜索保留）。
- 不删除 `ReadRecordActivity`（桌面小组件入口保留）。
- 不删除底栏包/外观管理/自定义套装的**编辑能力**（`hideSearchInFloatingStyle` 开关仍可用于自定义套装）。
- 不修改 AI 悬浮球逻辑、不修改搜索页（`SearchActivity`）本身。
- 不进行数据库迁移。

## Approach

### Selected Approach

**配置源头链式移除 + 默认值链翻转 + Fragment 宿主 Activity 复用**：

1. **统计 Tab 移除**：只改 3 个配置源 —— `MainBottomNavConfig.specs`（去 `KEY_READ_RECORD`）、`NavigationBarIconConfig.items`（去 `readRecord` NavItem）、`MainActivity` 相关硬编码分支。所有 UI（底栏渲染、底栏项管理弹窗、图标编辑弹窗、侧边栏）均为数据驱动，自动跟随。
2. **统计页迁移**：新增轻壳宿主 `ReadRecordStatsActivity`（BaseActivity + Fragment 容器），复用 `ReadRecordFragment` 完整仪表盘；`ReadRecordFragment` 增加 standalone 模式（参数驱动顶部加返回按钮）。
3. **搜索框默认隐藏**：翻转 4 处默认值（`AppConfig.floatingBottomBarHideSearch` / `MainLayoutPresetConfig.floatingBottomBarHideSearch()` / `NavigationBarIconConfig.Config.hideSearchInFloatingStyle` / `OtherConfigFragment` 开关默认值）+ 外观管理内置预设「悬浮底栏」对齐隐藏；自定义套装的编辑开关保留。
4. **订阅源全局搜索入口移除**：`MySettingsData.buildSettingsSections` 删行 + `handleSettingsRowClick` 删路由。

落地理由：改动集中在配置源头与少量宿主，栈深最浅；数据驱动 UI 自动收敛无漏网点；复用既有仪表盘避免重复实现（符合"编辑/调试类页面同构"项目惯例）。

### Alternatives Considered

| 方案 | 思路 | 否决理由 |
|------|------|---------|
| A. 统计页逻辑平移到 `ReadRecordActivity`（合并记录列表+统计） | 单页两用 | 职责混杂；`ReadRecordActivity` 是 S2 列表页且被小组件引用，改造面广、回归风险高；与"最小触碰"原则冲突 |
| B. 直接移除统计页无迁入入口 | 底栏删掉即完 | 统计信息是用户刚需（今日/月度/总时长/热力图/排名/目标卡），必须保留入口，"先删后补"违背用户意图 |
| C. 我的页新增「阅读统计」独立行，保留「阅读记录」列表行 | 两个入口 | 用户明确指定"放在 工具 阅读记录 作为子页面"，要求单入口收敛；新增行违背精简意图且与用户指名冲突 |
| D. 对自定义底栏套装的 icons 残留 key 强行清理/迁移 | 全量重扫各套装 | `applyTo` 以 `items` 白名单为循环依据，残留键自然忽略；强行迁移涉及套装包文件格式，无必要 |

### Drawbacks

| 缺陷/风险 | 接受理由 | 兜底预案 |
|-----------|---------|---------|
| 老用户自定义底栏套装若在编辑弹窗中曾配置过 `readRecord` 图标，移除后该图标配置静默失效 | 底栏已无统计项，图标无宿主可展示；行为符合预期 | 保留 icons map 残留键，不破坏套装文件；如用户回退版本，图标自动恢复 |
| standalone 统计页底部仍有 `applyMainBottomBarPadding` 的 88dp 避让 | 视觉底部留白，属低风险观感问题 | 页面底层视觉确认后，若过大则条件化该 padding |
| `shouldShowAiFloatingBall` 在搜索框隐藏时显示 AI 悬浮球（现逻辑）；默认隐藏搜索框后，开启 AI 助手的用户会默认看到悬浮球 | 与既有"搜索隐藏→AI 球补位"设计一致 | 不改动；AI 助手默认关闭，影响面仅限显式开启者 |
| 移除 `menu_read_record` 与 `ids.xml` id 需联动清理，存在编译期漏引用风险 | 引用清单已在 Explore 阶段全量盘点 | tasks.md 核心任务附 Grep 证据门禁（0 残留） |

## Requirements

### Requirement: 底栏默认收敛为四项

- 默认（无用户配置/全新安装）底栏仅含：书架、发现、订阅、我的。
- 侧边栏（sidebar 布局模式）同源跟随，不含「统计」项。
- 底栏项管理弹窗（底栏管理页头部卡片进入）可开关项同步为四项。

#### Scenario: 全新安装后底栏形态
- **WHEN** 全新安装应用启动主界面
- **THEN** 底栏显示书架/发现/订阅/我的 4 项，「统计」不出现

#### Scenario: 老用户预存配置兼容
- **WHEN** 老用户已保存含 `readRecord` 的 `mainBottomNavItems`
- **THEN** `normalize()` 按 specs 白名单过滤，底栏正常显示 4 项，不崩溃

### Requirement: 阅读统计页由「我的-工具-阅读记录」打开

- 「我的 → 工具 → 阅读记录」行点击后打开阅读统计仪表盘子页（原底栏统计 Tab 内容）。
- 子页保留全部既有能力：概览/热力图/最近阅读/每日记录/排行榜/目标卡/组件配置等，含顶栏年份/月份/日期筛选。
- 子页提供返回入口。

#### Scenario: 从我的页进入统计页
- **WHEN** 用户在「我的-工具」点击「阅读记录」
- **THEN** 打开阅读统计仪表盘，页面可返回「我的」，功能完整可用

#### Scenario: 桌面小组件点击
- **WHEN** 用户点击桌面「阅读排行/阅读目标」小组件
- **THEN** 仍进入 `ReadRecordActivity` 记录列表页（不受本变更影响）

### Requirement: 主题/底栏设置体系移除统计配置

- `MainBottomNavConfig` 与 `NavigationBarIconConfig` 不再包含「统计」条目。
- 「底栏项管理」弹窗、「底栏包图标编辑」弹窗不再渲染「统计」行。

#### Scenario: 底栏管理页
- **WHEN** 用户打开底栏管理页（导航栏管理）查看底栏项管理与图标编辑
- **THEN** 均不含「统计」条目

### Requirement: floating 底栏右下搜索框默认隐藏

- 默认（default 底栏包 + floating 布局）底部右下角不显示搜索按钮。
- 「其他设置 → 浮动底栏隐藏搜索」开关默认开启（隐藏）。
- 外观管理内置预设「悬浮底栏」默认隐藏搜索；「无搜索悬浮底栏」预设保留。
- 自定义底栏套装编辑弹窗中的「搜索」开关保留，默认隐藏。

#### Scenario: 全新安装默认底栏无搜索框
- **WHEN** 全新安装应用，使用默认底栏套装与 floating 布局
- **THEN** 底栏右下角无搜索按钮，「我的/发现/订阅/书架」顶栏搜索按钮不受影响

#### Scenario: 自定义套装恢复搜索框
- **WHEN** 用户编辑自定义底栏套装，将「搜索」开关设为显示并应用
- **THEN** floating 底栏右下角恢复搜索按钮（能力保留）

### Requirement: 「我的-工具」移除订阅源全局搜索入口

- 「我的 → 工具」分组不再显示「订阅源全局搜索」行。
- 路由 `rssSearch` 分支移除。
- 订阅 Tab 顶栏全局搜索按钮与订阅源内搜索不受影响。

#### Scenario: 我的页无冗余搜索入口
- **WHEN** 用户打开「我的-工具」
- **THEN** 不出现「订阅源全局搜索」行；在订阅 Tab 顶栏仍可进入全局搜索页