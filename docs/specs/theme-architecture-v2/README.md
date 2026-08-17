# theme-architecture-v2 · 主题架构 v2（全局即时换肤 + 设置页重设计）

> 状态：✅ 已实施并真机（模拟器 127.0.0.1:21503，测试包 io.legado.miss.app.debug）验证
> 创建：2026-08-17 ｜ 类型：Bug 修复 + 架构升级 + UI 重设计
> 背景：用户反馈「Compose 迁移后主题设置大量失效：设置项管理不了、设置后不起作用；整体 UI 不够协调优雅」；要求学习 MoRealm/阅读Archive/MD3-DIY 的主题全局控制架构。

## 1. 根因诊断（为什么「设置后不起作用」）

| # | 根因 | 表现 |
|---|------|------|
| 1 | **RECREATE 事件只有 MainActivity/ConfigActivity 订阅**；其余 ~70 个 Compose 宿主 Activity 收不到主题变更事件 | 改色后栈内已打开页面保持旧色 |
| 2 | **LegadoTheme 组合时一次性读 ThemeStore**（remember 色值 key），无运行时观察 | 不重建就永不刷新（Compose 页面全部如此） |
| 3 | **upTheme 的"激活模式门"**：夜间模式下改日间组颜色静默无效 | 用户认为设置坏了 |
| 4 | **bottomBackground/transparentNavBar/barElevation 仅 2 个组件消费**（PillNavigationBar/GlassTopAppBar） | 设置项改了没效果（已由 08-16 前置修复覆盖） |
| 5 | **底部导航选中色=colorScheme.primary=accent**，与 View 体系「选中色=primaryColor」语义不符 | 蓝色主题下「蓝顶栏+红选中」撞色不协调 |

## 2. 新架构（三层传播，fork 模式混合）

```
ThemeConfig.applyTheme() ──► ThemeSync.bump()（Compose 全局快照信号）
   │                              │
   │                              └─► 所有在组合中读了 ThemeSync.version 的 Composable
   │                                  （LegadoTheme/GlassTopAppBar/PillNavigationBar/ThemeConfigScreen）
   │                                  立即重组重读 ThemeStore —— 零 Activity 重建即时换肤
   └─► postEvent(EventBus.RECREATE)
        ├─ 普通页面（BaseActivity 统一订阅）→ recreate()
        ├─ 豁免页（recreateOnThemeChange=false：阅读器/视频/音频/漫画/设置宿主页）
        │    → setupSystemBar() + upBackgroundImage()（Compose 内容仍经 ThemeSync 刷新）
        └─ 栈内后台页面 → 恢复前台时：
             ├─ LiveEventBus pending 事件补投递 → recreate()
             └─ BaseActivity.onResume 对比 ThemeStore.VALUES_CHANGED 令牌（Archive 模式）
                  → refreshThemeAppearanceIfChanged()：确定性刷系统栏/背景图
```

- **Compose 层**：`ui/theme/ThemeSync.kt`（mutableLongStateOf 版本号；MoRealm「根部单点包裹+全局状态」与 MD3-DIY prefDelegate 思路的轻量版，适配混编项目）
- **View 层**：BaseActivity 统一 RECREATE 订阅 + `recreateOnThemeChange` 开放钩子；onResume 令牌懒同步（from legado-archive `refreshThemeBackgroundIfChanged`）
- **派生层**：`ThemeSpec.toM3Scheme()` 生成后过 `withContrastGuard()`（Archive 撞色守卫：MIN_FONT_SURFACE_CONTRAST=1.3，文字槽位对容器槽位校验，撞色跨昼夜取对比度更高的 M3 中性色兜底；**对比色计算前压平 alpha**——`calculateContrast` 遇半透明背景抛 IllegalArgumentException，实测崩溃一次后修复）
- **消费语义**：底栏选中色改跟随 `context.primaryColor`（对齐原版 BottomNavigationView 与 View TitleBar 顶栏，消除 accent 撞色）

## 3. 主题设置页重设计（L-E2 Compose 化）

- 旧 PreferenceFragment（pref_config_theme.xml）→ 全 Compose `ThemeConfigScreen`（Fragment 壳保留文件选图/下载/分享）
- **主题瓦片网格**（MoRealm 瓦片 + MD3-DIY 手机模型预览思路）：themeConfig.json 全部主题三列瓦片（bg 底+primary 顶条+三色圆+bottom 底条+日夜图标+名称），点击 applyConfig 即时应用，长按删除/分享
- **色盘弹层** `ColorPickerSheet`（新组件）：MATERIAL_COLORS 预置网格 + HSL 三滑块（色相彩虹渐变轨道）+ hex 活预览，确认即 `applyTheme→ThemeSync.bump` 全局即时换肤（设置页不重建不闪屏——ConfigActivity 豁免 RECREATE）
- **非激活组反馈**：夜间模式改日间色 → toast「已保存，将在切换到白天模式后生效」（theme_saved_pending_mode）
- **背景色明暗守卫**（原 ColorPreference.onSaveColor 逻辑迁移）：日间背景过暗/夜间过亮直接拦截
- 背景图操作（选图/虚化/删除）收进 AppMenuSheet；模糊度 AppModalBottomSheet+Slider；栏阴影/字号缩放 AppNumberPickerDialog（**组件新增 neutralText/onNeutral 中性按钮**，恢复默认）
- 删除孤儿：ThemeListDialog + item_theme_config.xml + dialog_image_blurring.xml + menu_theme_list.xml

## 4. 新增/修改组件清单

| 组件 | 类型 | 说明 |
|------|------|------|
| `ui/theme/ThemeSync.kt` | 🆕 | 全局主题版本信号（bump→全 Compose 即时换肤） |
| `ColorPickerSheet` | 🆕 | 色盘弹层（预置+HSL 自定义活预览） |
| `SettingsColorRow` | 🆕 | 色设置行（36×28dp 色块预览） |
| `ThemeConfigScreen` | 🆕 | 主题设置页（瓦片网格+日夜组+通用组） |
| `ThemeSpec` | 改 | +withContrastGuard 撞色守卫 |
| `AppNumberPickerDialog` | 改 | +neutralText/onNeutral |
| `PillNavigationBar` | 改 | 选中色 accent→primaryColor |
| `BaseActivity` | 改 | RECREATE 统一订阅+豁免钩子+onResume 令牌 |
| `ThemeStore` | 改 | +valuesChanged() 令牌读取 |
| `LegadoTheme` | 改 | ThemeSync.version 参与 remember |

## 5. 真机验证记录（2026-08-17，模拟器 800x1280）

| 用例 | 结果 |
|------|------|
| 启动无崩溃（对比度守卫 alpha 崩溃已修复） | ✅ |
| 应用「典雅蓝」瓦片 → 设置页即时换肤、页面不重建 | ✅ VLM 确认蓝色系 |
| 返回主页 → 全局主题跟随（顶栏/内容） | ✅ |
| 日间「主色调」拖 HSL → #F4AA03 确认 → 顶栏即时变金、无闪屏 | ✅ VLM+像素验证 |
| 顶栏菜单切夜间 → 页面即时变暗、停留原页、「夜间（当前）」标记正确 | ✅ |
| 夜间改白天色 → toast 反馈、不即时生效（保存待切换） | ✅ Toast 日志确认 |
| 底栏选中色 = 顶栏主色 | ✅ 像素采样 (121,85,72)=#795548 两处一致 |
| 主题页 VLM 评审 | 8.5/10 |
| 四主页 VLM 综合 | 75/100（遗留：各页间距/圆角细节不统一，见 §6） |

## 6. 遗留与后续

1. 主页间距/圆角细节统一（VLM 75 分项：书架搜索框圆角 vs 卡片圆角、发现卡片间距、订阅列表间距）——属页面级打磨，建议按 ui-standards §3.4 规格逐页对账，独立立项
2. ThemeSync 目前是单一版本号（粗粒度）；若未来主题键值分散多处直改（不经 applyTheme），可升级 Archive 式「签名字符串 remember」（拼全部相关 key 的签名参与 remember）
3. 阅读器/视频/音频/漫画页 Compose 顶栏在主题变更时经 ThemeSync 刷新，但 View 侧窗口装饰依赖 onResume 令牌——若发现沉浸态系统栏异常再评估
4. 背景图在二级 Compose 页面的透出（Scaffold surface 实底盖图）未处理——保留 MainActivity/设置宿主页路径，与原版二级页行为一致
