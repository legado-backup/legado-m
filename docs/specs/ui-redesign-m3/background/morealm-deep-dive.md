# 墨境 MoRealm 深度学习清单（学了什么 / 怎么学）

> 仓库：`temp/forks-comparison/morealm-reader`（纯 Compose + Material3 + Navigation + Hilt，兼容 Legado 书源）。全部为逐源码核验，`文件:行号` 佐证。可移植标签：直接搬 / 改造 / 仅参考。

## 0. 总评「现代工程设计」成立 vs 不成立

| 成立（值得学） | 不成立（警惕） |
|---|---|
| Hilt DI + UDF(StateFlow/SharedFlow) 分层干净 | **无类型安全路由**（纯字符串 `composable("string")`，非 sealed) |
| Room 主题表 + DataStore pref + 活动主题 id 同步读防白闪 | **无统一组件库**：设置项在 Profile/ReadingSettings 两处平行重复实现、空态每页一份、`ui/common` 仅 1 文件 |
| 自研主题推导(5 核心色→34 槽位) + 平滑换肤动画 | 无 Monet 动态取色、无 leadingIcon 抽象统一 |
| 边缘侧滑、骨架屏、玻璃拟态胶囊底栏 | 主题动画 34 个 animateColor 常驻成本高（不宜全套搬） |

## 一、导航与主骨架

- `ui/navigation/AppNavHost.kt:63` NavHost + `PillNavigationBar` overlay（非 Scaffold bottomBar）；阅读页 `Modifier.layout` 反向抵消 inset 实现真全屏（:471）。
- 4 Tab（`BottomTab.kt`）：**书架/发现/听书/我的**。Tab 不是 NavHost destination，而是 main_tabs 内部手写横滑 Pager（`cachedTabs`+`tabOffset: Animatable`+`detectHorizontalDragGestures` 拖 22% 切 tab、140ms 回归+`graphicsLayer alpha/translationX/zIndex` 层叠）。
- 导航安全：`navigateToReader` 500ms 连点节流防栈堆积；`safeNavigate/safePopBackStackOrHome` 吞 predictive-back 异常。
- `MainActivity.kt:38` `enableEdgeToEdge()`，顶层 `LaunchedEffect(isSystemInDarkTheme)` 驱动跟随系统（`ui/theme` **仅 1 个文件** MoRealmTheme.kt 283 行）。

### 借鉴 → PillNavigationBar（改造）
`PillNavigationBar.kt:75`：`surface@0.88` 半透明胶囊 + 1dp 顶白高光 + 18dp shadow 玻璃拟态；**单 4dp 滑动指示圆点**（spring 弹性 + radial glow + drawWithCache 缓存 brush）；按压 scale 0.92↔1.0 回弹；`combinedClickable` 长按；`tabExtras` 插槽；state 读下沉 placement 防整树重组。
→ 对应本设计「底部 NavigationBar 4 Tab」方案的**升级替代品**：Legado 现用 `BottomNavigationView`，可换 Compose `PillNavigationBar`（需剥离对 `LocalMoRealmColors` 依赖）。BADGE：MoRealm 全项目不用 `BadgedBox`（计数硬挂 label），更新红点用手绘 8dp error 圆点——与本设计 AD「小圆点角标」一致。

## 二、主题系统（MoRealmTheme.kt 精华）

- **ThemeEntity（Room 表 themes）**：id/name/author/isBuiltin/isNight/isActive/manifestJson/**5 色(mix palette)**/readerBackground/readerTextColor（★ 阅读区颜色存主题实体）/backgroundImageUri/transparentBars/customCss。当前主题 id 存 SharedPreferences **同步读**防启动白闪（ThemeViewModel:51）。
- **6 内置主题（BuiltinThemes.kt 常量）**：墨境紫 #7C5CFC 夜 / 纸上 #E08300 日+texture:paper 背景图 / 赛博朋克 #FF2D95 夜 / 森林 #4CAF50 夜 / 深夜 #6366F1 纯黑 AMOLED / 墨水屏 #333 高对比日。**Legado 主题兼容**（LegadoThemeConfig 按背景亮度判日夜 + LegadoReadConfig 拆日/夜两主题）。
- **ColorScheme 生成**（MoRealmTheme.kt:112-264）：ThemeEntity 5 核心色 → **34 个 M3 槽位**全量推导（Color.mix + hueShift(60°) 产 tertiary + contrastOn 黑白判定 + error 夜#FF897D）；`updateTransition` + 34 个 animateColor **420ms cubic-bezier(0.16,1,0.3,1) 平滑换肤**；单实例 ColorScheme 构造无 light/dark 分支（每槽已定值）。
- 扩展色板 `MoRealmColors(accent, readerBackground, readerText, isNight, transparentBars, bgUri)` + `LocalMoRealmColors staticCompositionLocalOf`——非 MaterialTheme 槽位也能取主题色。
- **阅读器配色跟随全局主题**（ReaderStyle.kt:23 注释「换阅读色=设置→挑主题」）+ 独立**阅读器背景图日夜双图**（AppPreferences READER_BG_IMAGE_DAY/NIGHT）。

### 借鉴取舍
| 学 | 不学 |
|---|---|
| 「主题实体 5 色→全槽位推导」替代现有 `lerp(bg,White,0.04)`（升级 AD-12 的 Hct 思路同源，MoRealm 给了现成 mix/hueShift 公式） | 34 animateColor 平滑换肤动画（常驻 recomposition 成本，本设计保留即时切换+局部动画） |
| readerBackground/readerText 随主题实体 → 但 **Legado 必须保留每书独立 ReadBookConfig**（用户核心生态），设计折衷：全局主题提供默认阅读底色，每书可覆盖 | Monet 动态取色（Legado minSdk 23 受限） |
| LegadoThemeConfig 兼容层（与 325506 OldThemeConfig 同思路，已有此解） | 阅读预设改为纯排版（Legado 现状配色预设为一块，保留现状更稳） |

## 三、设置组件（两套平行模板 → 本设计组件库直接采用）

### 派① Profile 派（分组卡片 + ListItem 行，无分隔线）
| 组件 | 位置 | 签名/实现 |
|---|---|---|
| `SettingsSection` | ProfileScreen:692 | `(title, content: ColumnScope.()->Unit)` → SectionTitle + 整张 `Card(surfaceContainerHigh, shapes.medium)` 包多行，行间**无 Divider** |
| `SettingsItem` | :840 | `(icon, title, subtitle=null, onClick)` → M3 `ListItem` 三槽位，containerColor=Transparent，tail 统一 `>` 箭头 |
| `SettingsCard` | :657 | `(icon, title, desc, onClick, extra: ColumnScope.()->Unit={})` 独立大卡 + `extra()` 插槽（置组件预览）shapes.large |
| `StatItem` | :593 | 22sp ExtraBold primary 数字 + 灰标签 |

### 派② 设置页派（行首 36dp 圆角图标块）
| 组件 | 位置 | 签名/实现 |
|---|---|---|
| `SectionHeader` | ReadingSettingsScreen:481 | 灰 labelMedium 左 24dp 缩进 |
| `SettingsCard` | :495（private） | 每 section 一张 `surfaceContainer` 16dp 圆角卡，行内自管 padding |
| `RowIcon` | :518 | 36dp 圆角 10dp 方块 + 20dp Outlined 图标，surfaceVariant 半透明凹感 |
| `SettingsClickRow` | :535 | `(icon, title, value, subtitle, onClick)` RowIcon + 标题/副标题 + 右 value |
| `SettingsToggleRow` | :566 | 同上尾部 `Switch(checkedTrack=primary, thumb=White)` 整行可点取反 |

### 借鉴决策
→ 本设计公共组件库（AD-15）**正式采用「每组一张卡 + 行内无分隔线 + 行首图标块」**双范式：
- `AppSettingCard`（分组卡容器，参考派① Card+派② surfaceContainer16dp）+
- `SettingClickableRow` / `SettingToggleRow`（参考派② RowIcon 36dp 图标块方案）+
- `SettingItemArrow`（统一 `>` 箭头三槽位，参考派①）。
统一一处实现，杜绝 MoRealm 两套重复的坏味道（我们 AD-15 的「组件化优先」直接规避之）。

## 四、阅读器（交互细节，Legado 有 7 种委托要保留）

- **点击分区 9 宫格**（ReaderTapZones.kt）：竖版 35/30/35、横版 25/50/25 —— 与 Legado ReadView 现有分区逻辑一致可保留。
- 渲染四路径全共享 9 宫格：Canvas 分页 / `PageLevelReaderHost`（4 槽位 prev/cur/next/nextPlus + ZoneTapOverlay）/ `ScrollCanvasReaderHost`（滚动与下拉刷新在**同一条 detectVerticalDragGestures 内互斥判别**）/ `SimulationReadView`（贝塞尔卷边，状态机与绘制解耦）/ `VerticalReaderView` 竖排 RAW。
- `ReaderTopBar`(:77) + `ReaderControlBar`(:215 章节滑块+上/下章)；`ReaderSettingsPanel`(:861) 底部 24dp 圆角面板含字号/字体/行距/间距/**主题/亮度**/翻页模式/繁简/重置。
- `ChapterBookmarkPanel`(:275) 目录/书签**双 Tab**，`fillMaxHeight(0.6f)` 底部弹出 —— 与我们的目录/书签 Sheet hub（ADR-06）同思路，佐证成立。
- **可配置选区菜单**（README 亮点）：长按选文后按钮列表可定制顺序/显示项——MoRealm 设于「选区与高亮」设置组。对应我们 P8 的「长按文字→工具条（拷贝/划线/高亮/分享）」升级方向：加「顺序可配」选项。
- **5 色高亮**选区→DB 持久化跨设备；选色交互（色板弹层）对应我们 AD-13「2 行 6 色 BottomSheet 化」可加「自定义色」。

## 五、书架/搜索/详情交互

- 书架响应式列数 `(maxWidth/100dp).coerceIn(2,4)`（ShelfScreen:701）；`BookGridItem`(:148) `AlternatingBadge` 角标留白 padding(top18)。
- **AlternatingBadge**（components.kt:155）：红色胶囊 `<=9 "N 新" / <=99 "N+" / >99 "99+"`——Legado 角标为 6dp 圆点（AD），可合并：小圆点 + 超出阈值变胶囊数字，两层角标策略。
- 搜索 `SearchResultCard(:2)` 封面+作者·书源+最新章节+字数/分类/状态+收藏心；加书架 `updateTransition fadeIn/scaleIn` 遮罩动画。
- 详情页收藏心跳动画（animateFloatAsState spring(0.45,800) 缩放 0.75→1.0+上弹 8dp）。→ 微交互可借鉴（Legado 目前无此）「收藏/加书架即时反馈」。

## 六、公共 Widget 全表（直接可用清单）

| 组件 | 来源 | 用途 | 标签 |
|---|---|---|---|
| `SwipeBackEdge` | SwipeBackEdge.kt:32 | 左缘 24dp 起手拖 60dp 返回（注明勿套阅读器） | 直接搬 |
| `shimmerBrush` + `ShelfGridSkeleton` | ShimmerSkeleton.kt:48/73 | 单 InfiniteTransition 共用时间线的骨架屏，感知提速 | 直接搬 |
| `ThemedSnackbarHost` | ThemedSnackbarHost.kt:24 | surfaceVariant 容器/primary action，避免 M3 反色块 | 直接搬 |
| `GlobalBackgroundScaffold` | common/GlobalBackgroundScaffold.kt:48 | Canvas+nativeCanvas.drawBitmap+Paint alpha（图自身透明、卡片不动）+ box-blur 缓存 | 改造（配 BgImageManager） |
| `EmptyShelf` | ShelfComponents.kt:418 | 空态 emoji📚+引导+导入按钮 | 改造（Legado 需换书源引导双动作） |
| `TtsErrorSnackbarHost` | 、TtsErrorSnackbar.kt:31 | 事件总线驱动 TTS 失败提示 | 直接搬 |
| `PhotoView` | image/PhotoView.kt | Matrix 缩放旋转平移，AndroidView 包 Compose | 仅参考（Legado 已有） |

## 七、风险红线（对照 our design）

1. **正文引擎绝不动**：MoRealm 自研 Canvas 排版对我们无用（Legado TextChapterLayout 更成熟/章节缓存体系依赖它）。
2. **不引入其主题平滑动画 34 个 animateColor**（常驻成本）。
3. **阅读预设不得按 MoRealm v20 改纯排版**——Legado 现状配色/排版双维预设为既有生态，保留。
4. **路由保持 Legado 现状 startActivity/VMBaseActivity**，不学其字符串路由（无类型安全）。

## 八、Top10 可搬运组件（进公共组件库）

1. `PillNavigationBar`（改造：悬浮胶囊底栏+滑动指示点+长按插槽）→ 替代 MainActivity BottomNavigationView
2. `SettingsSection + SettingsItem`（直接搬）→ 分组卡片模板
3. `SettingsCard(extra 插槽)`（直接搬）→ 高频入口大卡（P4 用）
4. `SettingsClickRow / SettingsToggleRow（RowIcon 图标块）`（直接搬）→ 设置行模板
5. 主题 5 色→34 槽位推导公式 + `LocalMoRealmColors`（仅参考，升级 AD-12 算法）
6. `shimmerBrush + ShelfGridSkeleton`（直接搬）
7. `SwipeBackEdge`（直接搬）
8. `ThemedSnackbarHost`（直接搬）
9. `AlternatingBadge`（改造：圆点+溢出胶囊数字双层角标）
10. `GlobalBackgroundScaffold`（改造：Legado 现有 ComposeActivitySupport 背景图升级 canvas box-blur）

> 全部证据来自 morealm-reader 真实文件。下一步据此焊入 four-fork-deep-dive 与 design（新增 ADR）。