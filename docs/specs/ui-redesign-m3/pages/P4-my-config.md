# P4 我的 / 设置（MyCenter / Config）

> **已接线页升级 v2（2026-08-13）**：对齐 MyFragment + ProfileScreen3Level 混血现状（P0 已改造）+ 登记遗留违例。另一 AI 开发本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：我的页 MyFragment + ProfileScreen3Level（`ui/main/my/`，XML 壳 + ComposeView）；设置子页 ConfigActivity（`ui/config/`，E1-E6 Preference 族，保留 View）
- **骨架归类**：S2 列表管理页（我的 Tab）+ 设置子页 E 族（S2 配置列表）
- **对应 task**：tasks.md `12.16k`（我的页 v2.8 复审）；pages-inventory A2（我的页）、E1-E6（配置子页）
- **fork 借鉴来源**：four-fork-deep-dive §四（鸿蒙三级布局）、forks §9.3（legado-archive 我的页）
- **⚠️ 真机测试发现（2026-08-15）**：`ConfigActivity.kt:32` `by mutableStateOf(getString(R.string.setting))` 在 Activity 构造阶段（Context 未 attach）调 getString 抛 NPE，**启动即崩溃，阻断 E1-E6 全部设置子页入口**。登记 D-15（P0）。修复：改 `mutableStateOf("")`（同 Cache/AudioPlay/RssSort/VideoPlayer/ReadRss/BookshelfManage 6 处一致）+ setTitle() 兜底。**门禁：am start ConfigActivity 正常进入设置页。**

## 1. 设计意图（一段话）

核心痛点解决：原版「一长串 Preference 列表混排」（备份/主题/书源/系统设置全在同一线性列表，高频难找）。目标 = **三级信息架构**（用户区 → 统计 → 高频功能卡 → 低频列表），让高频操作 ≤2 步可达。与现状差异：ProfileScreen3Level 已 Compose 化（组件复用率最高，全页 import 设置族），整页无私有组件。**本文档是验收的「为什么」：任何改造不得破坏「高频操作 ≤2 步」「统计卡真实数据」「开关即时持久化」三项。**

## 2. 布局结构（文字框图 + 区块表）

```
┌──────────────────────────────────────┐
│ XML 壳 TitleBar（V-：换 GlassTopAppBar）│ ← 标题「我的」+ 帮助菜单(壳内)
├──────────────────────────────────────┤
│ ① 统计卡 MetricGrid（4 列 chunked(2)）  │ ← 真实 Room：阅读数/总时长/书签/书源
├──────────────────────────────────────┤
│ ② 高频功能卡 8 行（SettingsSection 分组）│ ← 备份恢复/主题/其他/书源管理/替换净化/词典/TXT目录/自动任务
├──────────────────────────────────────┤
│ ③ 服务开关 2（SettingsToggleRow）       │ ← Web服务/自动任务服务
├──────────────────────────────────────┤
│ ④ 低频 6 行（SettingsClickRow×6）      │ ← 书签/阅读记录/文件管理/精准管理/关于/退出
└──────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 统计卡 | `MetricGrid`（§3.4：MetricTile 12dp 圆角，🟡 暗色待对齐） | Room stats | 真实数据 ✅ |
| 分组标题 | `SettingsSection`（§3.4：labelLarge Bold primary） | — | |
| 功能卡 | `SettingsCard`（§3.4：18dp 圆角）+ `SettingsClickRow`×14 / `SettingsToggleRow`×2 | AppConfig | 复用率最高 ✅ |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `SettingsCard` | 18dp 圆角、标题 h16 v12、surfaceVariant、1dp elevation | 高频功能卡容器 |
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 低频 6 行 + 功能 8 行 |
| `SettingsToggleRow` | h16 v12、bodyLarge、v12 垂直内边距 | Web/自动任务 2 开关 |
| `MetricGrid` | MetricTile 12dp 圆角、value titleMedium Bold | 统计卡 4 列 |
| `RowIcon` | 36dp/10dp/20dp、primary α0.12 底 | 行图标块 |

> ⚠️ `MetricGrid` §3.4 标 🟡（MetricTile 暗色硬用 surfaceVariant 无暗色处理），引用时注意暗色适配（CommonPageColors 对齐）。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点统计卡 | 进 ReadRecord / 成就页 | ✅ | 真实 Room 数据 |
| 点功能卡 | 直达对应 Activity（书源管理/主题设置/备份恢复） | ✅ | 高频 ≤2 步 |
| 点服务开关 | `SettingsToggleRow` 启停 Web/自动任务服务 | ✅ | **⚠️ V4 遗留**：`remember{mutableStateOf(WebService.isRun)}` 仅初始值，不观察 EventBus，子页返回不回读 |
| 点低频行 | startActivity | ✅ | |
| 壳内「帮助」 | XML 菜单（main_my.xml） | ✅ | V7：仍挂壳内，后续下沉 |

## 5. 状态管理（§4 范式）

- 数据源：`ProfileScreen3Level` 用 `produceState` 单次查询 Room stats + AppConfig 开关（可保留，§4.1 允许）
- 受控组件：统计卡/行组件全部无状态，state 提升到 Screen
- **⚠️ V2 遗留**：服务开关状态不同步——需观察 `EventBus.WEB_SERVICE`/`AUTO_TASK` 事件（MyPreferenceFragment:111-120 有 observeEventSticky，Compose 版未接）
- **⚠️ V3 遗留**：三态不全——stats 查询 `withContext(IO)` 无 `runCatching`，Room 异常会闪崩/永久 loading，需补错误占位/重试。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 现状居中 `CircularProgressIndicator` | **V3 遗留**：换顶部 LinearProgress/轻骨架 |
| 空态 | — | 我的页一般无空态 |
| 错误 | 无 | **V3 遗留**：需 `EmptyStatePlaceholder` + 重试（runCatching 包 IO） |

## 7. i18n 与无障碍

- **⚠️ V1 遗留**：实施回执缺失（§3.3/AD-23），待补填「页面回执：我的页 MyFragment」
- **⚠️ V2 遗留**：`formatDuring` 硬编码中文（`"${d}天"/"小时"/"分钟"/"秒"/"0秒"`）需迁 strings.xml 双语（唯一私有工具函数）
- 触控 ≥48dp；Icon contentDescription；颜色只 colorScheme。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（统计卡/高频/服务开关/低频 四区块齐全）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] **V1**：§3.3 实施回执已填；**V2**：formatDuring 双语；**V3**：三态补全 + runCatching；**V4**：服务开关观察 EventBus 回读
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App"我的"页高保真：顶部磨砂栏，首卡用户头像+今日阅读时长，
第二行四个小圆角统计数字卡（读过/在读/书签/时长），第三区2列大功能卡片
（备份/主题/书源/WebDAV）圆角18dp 带图标，Web服务独立卡带开关，
下方统一卡片分组列表（帮助/关于/缓存/文件），浅色米白留白底，低饱和护眼，中文界面
```

## 10. 变更记录

- 2026-08-13：v2 升级——对齐 ProfileScreen3Level 混血现状（设置族组件复用率最高/无私有组件），登记 V1 回执/V2 formatDuring i18n/V3 三态/V4 服务开关同步 4 项遗留（对应 task 12.16k）。
