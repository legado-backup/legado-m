# Tasks：亮色主题文字对比度系统性修复

> **状态**：🔄 已实施·编译通过·测试包已交付（真机 L2 验证按用户裁决延后）｜ **创建日期**：2026-08-31
> **关联文档**：[README.md](./README.md) ｜ [spec.md](./spec.md) ｜ [design.md](./design.md)
>
> 交付物：`output\apk\test\legado_miss_app_3.26.083116.apk`（io.legado.miss.app.debug，libcronet.so 校验通过）
> 延后项：3.3-3.5 真机逐屏走查、4.2-4.8b 真机 L2 九场景（S1-S9）——待用户真机验证后闭环
>
> 日志区约定：AOAdapt 修复动作以 `AOAdapt: ` 前缀追加到文末日志区（含时间戳），临时日志文件清理后仅保留结论。

## 1. 准备

- [x] 1.1 备份：`MaterialValueHelper.kt`、`ThemeConfig.kt`、`ThemeSpec.kt` 备份为 `*.bak`（危险操作规范：修改前备份）
- [x] 1.2 根因3 点位文件备份：`BookshelfScreen.kt`、`BookshelfItems.kt`、`BookshelfComposeItems.kt`、`LegadoMiuixComponents.kt`、`styles.xml` 备份为 `*.bak`
- [ ] 1.3 基准截图：测试包（`io.legado.miss.app.debug`）内置默认亮色主题下主界面/书架/弹窗/菜单基准截图（记录不可见点位基线）
- [ ] 1.4 夜间主题 + e-ink 模式基准截图（回归对照基线）
- [x] 1.5 生成消费点复核清单：Grep 技术字段 `primaryTextColor|secondaryTextColor|primaryDisabledTextColor|secondaryDisabledTextColor`（204 处/50 文件实测基线），修复后用于复核属性引用无残留旧链，临时清单放 `docs/temp-analysis/`

## 2. 核心修复

- [x] 2.1 `MaterialValueHelper.kt` 对齐 Archive 修正版：`isDarkTheme = AppConfig.isNightTheme`（基线：`archive-ref/legado-08172114` 同名文件 L171-172）
- [x] 2.2 `MaterialValueHelper.kt` 对齐 Archive：`primaryTextColor = AppConfig.uiFontColor.toThemeTextColorOrNull() ?: defaultThemeTextColor(AppConfig.isNightTheme)`（Archive L85-87，含 Fragment 扩展 L122-124）
- [x] 2.3 `MaterialValueHelper.kt` 对齐 Archive：`secondaryTextColor = 主字色 alpha 0.72 派生`（Archive L96-99，含 Fragment 扩展 L126-129）
- [x] 2.4 `MaterialValueHelper.kt` 对齐 Archive：`primaryDisabledTextColor/secondaryDisabledTextColor` 按 `!AppConfig.isNightTheme` 取反 + `buttonDisabledColor` 按 `AppConfig.isNightTheme`（Archive L101-105/L164-169，含 Fragment 扩展）
- [x] 2.5 `MaterialValueHelper.kt` 新增本项目扩展 `onPrimarySurfaceTextColor`（= `getPrimaryTextColor(!isColorLight(primaryColor))` 保持旧逻辑，供 primary 表面消费点使用）
- [x] 2.6 本项目自有演进核对：backgroundColor e-ink 背景图分支/filletBackground/dialogSurfaceBackground 的 UiCorner 实现保持现状不回退；核对 Archive 有而本项目缺的 import（PreferKey/ThemeConfig）
- [x] 2.7 `ThemeConfig.applyTheme()` 三分支补写 `KEY_TEXT_COLOR_SECONDARY`（亮色 #8A000000 系 / 夜间 #B3FFFFFF 系或主文字色降 alpha 的 Material secondary 档）
- [x] 2.8 `ThemeConfig.applyTheme()` e-ink 分支补写后验证 primary=WHITE → 白底黑字现状不翻转
- [x] 2.9 `ThemeSpec.kt`：`MIN_FONT_SURFACE_CONTRAST` 1.3→3.0，guard 槽位扩展到 `onPrimary`/`onSecondary`/`onErrorContainer`
- [x] 2.10 根因3 点修：`BookshelfScreen.kt` L825-830 未读角标（mutedColor 亮度选黑/白字）
- [x] 2.11 根因3 点修：`BookshelfScreen.kt` L521-528 封面角标（加遮罩或按底色选色）
- [x] 2.12 根因3 点修：`BookshelfItems.kt` L111 与 `BookshelfComposeItems.kt` L185 占位 tint 按渐变底色选色
- [x] 2.13 根因3 点修：`LegadoMiuixComponents.kt` L106 `onAccent` 默认值复用 `isColorLight(accent)→黑` 纠正模式（参照 AppComposeDialogs L147）
- [x] 2.14 根因3 点修：`styles.xml` L192/L205 VideoCtrlButton/VideoPanelButton 字色恒亮色（固定黑面板，与主题模式解耦）
- [x] 2.15 代码改后核验：git diff 逐文件对照本清单 2.1-2.14 确认修改正确无遗漏；与 Archive 基线 diff 复核逐行一致性
- [x] 2.16 新增统一工具 `Context.onAccentFor(bg: Int)`（MaterialValueHelper.kt，= if(isColorLight(bg)) 黑 else 白）并替换 accent 白字家族 8 处：LegadoMiuixComponents L106/L715、SearchScopeDialog L295、ReaderComposeComponents L359/L390、AiChatScreen L1890、ReadAiFloatingPanel L1926、BookInfoComposeRoute L1227
- [x] 2.17 高危点修：`activity_manga.xml` L58 indicatorColor 改主题感知色；`ClickActionConfigDialog.kt` L221-244/L296-308 白字半透明卡改不透明深底或按合成底选字
- [x] 2.18 中低点修：`BookInfoComposeRoute.kt` hero 区遮罩加深（L1614 scrim≥0.45、L1699-1732/L1760 渐变与 chip）；`EpubReadView.kt` L143/L1674 loading 遮罩 0x66000000→0x99000000
- [x] 2.19 根因4 槽位治理（`ThemeSpec.kt`）：inversePrimary 按 inverseSurface 亮度派生；onErrorContainer 改 contrastOn(errorContainer)；surfaceContainer 族亮色 lerp 0.02-0.08→0.04-0.14；outline 族亮色 lerp 0.12→0.22；guard 半透明前景先合成底色再校验
- [x] 2.20 清理：`activity_rss_artivles.xml` L22 死属性删除
- [x] 2.21 代码改后总核验：git diff 逐文件对照本清单 2.1-2.20 确认修改正确无遗漏

## 3. 复核与回归兜底（消费层零改动）

> 深挖实锤：204 处消费点写法与 Archive 逐行一致（弹窗/样式/顶栏/主界面），源头对齐后全链自动修复，**不做逐点甄别与批量替换**。

- [x] 3.1 Grep 复核：对照 1.5 清单确认 204 处消费点属性引用全部走新派生链，无 `getPrimaryTextColor(isDarkTheme)` 残留调用（`isDarkTheme` 旧语义调用点应为 0）
- [x] 3.2 Grep 复核：`backgroundColorBasedTextDark` 等旧方案残留标识符应为 0
- [ ] 3.3 真机逐屏走查：内置默认亮色主题（深 primary）逐屏走查主界面（书架/发现/订阅/我的）+ 顶栏 + 标签栏 + 弹窗 + 菜单
- [ ] 3.4 真机逐屏走查：典雅蓝等浅 primary 亮色主题 + 自定义 uiFontColor 场景抽验
- [ ] 3.5 真机异常点位处置：发现 primary 表面等异常点位时用 `onPrimarySurfaceTextColor` 定点处理，归档 `issues-found.md`；重点回归 `SourceFolderAdapter` L46-47 ripple（isDarkTheme 唯一非文字消费点）与 ChangeThemeDialog/CodeEditActivity（ThemeConfig.isDarkTheme 体系，应零变化）
- [ ] 3.6 每阶段编译复验（阶段门禁：每阶段构建验证，非最后一次性构建）

## 4. 验证

- [x] 4.1 编译门禁：`build-legado.bat`（测试包），构建后执行 `stop-daemons.bat` 清场（强制门禁）
- [ ] 4.2 真机 L2 验证 S1：内置默认亮色主题（primary 深）主界面文字可见（对比 WCAG ≥4.5）
- [ ] 4.3 真机 L2 验证 S2：典雅蓝等浅 primary 亮色主题文字按背景亮度选色
- [ ] 4.4 真机 L2 验证 S3：切回夜间主题全功能不回归（对照 1.4 基准截图）
- [ ] 4.5 真机 L2 验证 S4：e-ink 模式白底黑字不回归
- [ ] 4.6 真机 L2 验证 S5：弹窗/菜单两种模式下主/次文字可见（textColorSecondary 显式生效）
- [ ] 4.7 真机 L2 验证 S6：书架未读角标/封面角标/占位/视频控制面板按钮可见
- [ ] 4.8 真机 L2 验证 S7：用户自定义字体色仍优先生效（阅读界面不被覆盖）
- [ ] 4.8a 真机 L2 验证 S8：Compose 弹框表面层级/输入框描边/错误容器文字/inversePrimary 可见（亮+夜）
- [ ] 4.8b 真机 L2 验证 S9：isDarkTheme 修复边界（ChangeThemeDialog/CodeEditActivity 零变化+SourceFolderAdapter ripple 正常）
- [ ] 4.9 Grep `android.util.Log.d|android.util.Log.e` 确认无残留调试日志
- [x] 4.10 编译前更新 `app/src/main/assets/updateLog.md`（基于 git diff，追加在 `## cronet版本:` 之后、已有条目之前，面向用户语言）

## 5. 收尾

- [ ] 5.1 文档同步：`docs/specs/INDEX.md` 登记本 spec；`ai_memory_main.md` 经验沉淀（关键决策/文件路径/任务状态）
- [ ] 5.2 issues-found.md 真机问题全部归档（含 3.5 异常点位补修记录）
- [ ] 5.3 清理临时文件：`docs/temp-analysis/` 复核清单结论回填本文档后删除；`*.bak` 备份确认无回滚需求后清理
- [x] 5.4 文末 AOAdapt 日志区补全（各组完成时间戳与结论）
- [ ] 5.5 状态标记更新：README/spec/design/tasks 状态 🔄 设计中 → ✅ 已完成（经 AskUserQuestion 用户验收后）
- [ ] 5.6 经验沉淀：Archive 迁移类任务必须全文件逐行对比学习源（对比维度加入 global-thinking-checklist / forks_comparison_methodology）

---

## AOAdapt 日志区

<!-- 修复动作按时间顺序追加，格式：[YYYY-MM-DD HH:MM] AOAdapt: 动作与结论 -->

[2026-08-31 11:52] AOAdapt: 检查点1 一轮用户质询"为什么学习 archive 学出这么多问题"→ 亲自对比 archive-ref MaterialValueHelper.kt 实锤部分拷贝（工具函数逐字一致、四个核心属性漏搬），方案由 Surface-based 修订为 Archive-aligned（v2）
[2026-08-31 12:1x] AOAdapt: 二轮用户批评"分析完全不透彻"→ 3 子代理并行全量对比（存储应用层/消费层/git 考古）：①消费层 204 处零差异，作废批次点修计划（§3 由 10 条改 6 条）②git 实锤部分拷贝发生于 3c8aa5c7b（2026-08-23）单提交内范围裁剪 ③根因2 重新定性（新增层消费共有 fallback）④子代理间"标准场景风险判定"矛盾由主代理亲自读源码定案（深 primary → 白字，高风险）⑤新增范围外观察项 3 条（backgroundColor 透明化/dialogSurfaceBackground/filletBackground）→ v3 深度修订
[2026-08-31 12:1x] AOAdapt: 教训沉淀——迁移类问题排查第一步必须对比学习源同名文件（forks_comparison_methodology），新增 tasks 5.6 防复发
[2026-08-31 12:4x] AOAdapt: 三轮用户批评"没把控全局"→ 系统性枚举盲区清单一次查完（3 子代理+主代理亲核 AppConfig.isNightTheme 地基）：①盲区1-6 全部零差异（"Archive 有强制校验"系对比文档误记）②Compose 自创层 34 槽位全量推演净增 4 缺陷（inversePrimary 夜间 1.05:1 必然不可见/onErrorContainer 恒不达标/surfaceContainer 亮色层级坍缩/outline 1.3:1+guard 压平 alpha 缺陷）→ 新增 AD-06+根因4 ③全库地毯扫描净增 15 处（高危 2：manga 白圈/ClickActionConfigDialog 白字；accent 白字家族 8 处收敛 onAccentFor 工具）④isDarkTheme 修复回归面全量清查（唯一非文字消费点 SourceFolderAdapter ripple）→ v4 扩充（tasks 2.16-2.21+场景 S8/S9）
[2026-08-31 17:0x] AOAdapt: 用户裁决"开始实施，真机延后，编译通过打测试包交付"→ 全部源码修改完成（16 文件：源头 MaterialValueHelper 对齐 Archive 5 属性+isDarkTheme/onAccentFor/onPrimarySurfaceTextColor 新增、ThemeConfig secondary 补写、ThemeSpec 槽位治理+guard 增强 6 槽、根因3 已知 6 处+净增 15 处）| 首轮打包失败 9 个编译错误（@ColorInt 不适用顶层属性/Compose 调用点缺 Color() 包装/0x99000000 需 toInt()/Color.alpha(Int) 不存在改 ushr 24）→ 逐个修复后 compileAppDebugKotlin BUILD SUCCESSFUL 1m49s → build-legado.bat 整包 SUCCESS → legado_miss_app_3.26.083116.apk 交付 | 实施决策微偏差：BookInfo hero 区文字用 Shadow 替代渐变加深（观感变化更小）；EpubReadView 仅 L139 全屏遮罩需加深（L1674 白字在 0x99 黑徽章上已达标，子代理报告误判）| 编译前检测到并行会话正在构建，等待其完成后启动避免 Gradle 锁冲突
