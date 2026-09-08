# real-device-bugfix-0908-followup 子任务

> 规格：./spec.md。红队 3 轮记录见末尾。

## 子任务
- [x] T1 经典发现头部纯黑：TitleBar managed 分支改 resolvePageBarColorWithAlpha + 半透明清 elevation（init+refreshTopBarAppearance 两处）
- [x] T2 顶栏图标单源：①GlassTopAppBar 自绘分支补 CompositionLocalProvider(LocalContentColor=contentColor) ②MenuActionIcon 默认 tint 改 LocalContentColor.current（恢复 R5 继承决策）③TopBarActionRow 一级图标 20dp 统一
- [x] T3 摘录模板崩溃：ShareNoteTemplateManageActivity addView 索引 coerceAtMost（对齐同批 4 页写法）
- [x] T4 统一自测：编译 2 轮（首轮 import 未落盘失败，修复后过）+ L2 t6/t7/t8 全过 + 零 FATAL（留痕见下）
- [x] T5 提交推送 + updateLog 第十批 + INDEX 登记

## L2 自测留痕（l2_verify_bugfix_0908.py --scenario t6/t7/t8）
- 环境：MEmu 实例0，APK 3.26.090807（含第十批前代码；updateLog 第十批随交付包重打）
- **t6 摘录模板**：ShareNoteTemplateManageActivity 正常启动（修复前 IndexOutOfBoundsException index=3 count=1 必崩），页面锚点 4 个命中，FATAL=0 ✅
- **t7 经典发现**：发现页模式→经典发现切换成功，title_bar V 在位，FATAL=0 ✅；头部颜色/壁纸透出为绘制层效果，a11y/dump 不可判定，视觉留真机复核
- **t8 管理族自绘顶栏**：BookSourceActivity 存活零崩溃（自绘分支 LocalContentColor 作用域修复路径），FATAL=0 ✅；图标颜色/尺寸视觉留真机复核
- ⚠️ 环境限制：MEmu screencap 全黑（GPU 故障，重启实例无效），T1/T2 颜色类视觉判定留真机

## 红队对抗审查记录
- [x] R1 正确性/回归面：自绘分支补 LocalContentColor 仅影响该分支（M3 分支已有 contentColor 三键）；MenuActionIcon 默认 tint 改继承后，AppMenuSheet 菜单行图标色从 onSurfaceVariant→onSurface（与同行文字一致，视觉合理）；AppDropdownMenu 不经 MenuActionIcon（走 LegadoMiuixChoiceRow tint=null 默认），零影响；AppManagementScaffold 内部图标均显式 tint，零影响；TitleBar 半透明清阴影仅 managed+alpha<0xFF 分支
- [x] R2 边界/性能：CompositionLocalProvider 无重组开销；TitleBar setBackgroundColor/alpha 判算轻量；coerceAtMost 纯算术
- [x] R3 盲区/兼容性：MenuActionIcon 全部消费点（AppMenuSheet/ConfigActivity/ImportBookScreen）均在 M3 内容色提供者作用域内，无裸 fallback=黑风险；LocalContentColor 显式 action.tint 优先级保留；TitleBar managed=true 仅主界面"我的/发现经典"两处使用（bugfix ③ 注释锚定），不污染子页面；E-Ink 分支保持 bg_eink_border_bottom 不受影响

## 视觉统一追加（用户验收反馈：新批次标题偏大偏粗/图标偏粗）
- [x] T6 标题字重对齐：GlassTopAppBar titleStyle fontWeight Medium→Normal（主 Tab 主题字体默认 Regular，用户实锤"文字粗一点"）
- [x] T7 标题字体跟随主题：无 titleFontFamily 槽时回落 AppConfig.systemTypefaces 三态映射（对齐 MainTopBarView.applyUiTitleTypeface 的 baseSystemTypeface 口径）；titleFontFamily 槽（主题包字体）仍最优先，不破坏主题设置体系
- [x] T8 返回/溢出图标细线化：GlassTopAppBar 两分支 nav 渲染固定 ic_back（细线），TopBarActionRow/ConfigActivity 溢出图标改 ic_more_vert（主 Tab 同款资产）
- [x] T9 回归：编译过 + L1 过 + t6/t8 零 FATAL；已知限制=自定义标题字体文件（titleFontPath）在 Compose 侧以 systemTypefaces 三态近似（android.graphics.Typeface→Compose FontFamily 无法直桥），登记升级路径（AndroidView 桥接或 Font 文件加载）
