# red-team-report.md — 五轮红队对抗审查报告

> 任务：ui-theme-governance-polish
> 用户要求：实施前 ≥5 轮红队对抗审查（合理性/可行性/可靠性/稳定性/通用性，清零遗漏/阻塞/待优化点）
> 编排：R1 执行模拟 / R2 稳定健壮 / R3 通用遗漏（并行）→ 整改 → R4 一致性矛盾 → 整改 → R5 终审 GO/NO-GO

## 预审（检查点 1 首次提交后）

用户要求自主全面审查 → 审查子代理 14 项穿透核验（读源码 13 文件 + Grep 8 轮），结论 GO-WITH-NOTES（1P0+4P1+6P2），全量整改后进入红队流程。

| 级别 | 发现 | 整改 |
|------|------|------|
| P0 | P6 让 AppDialogFrame（全 App 82 调用点，面板已消费全局 dialogAlpha）消费管理页透明度 → 全 App 弹框误伤+双 alpha 叠乘 | manageBgAlpha 收敛为仅 AppManagementScaffold 消费，弹框透明度登记二期 |
| P1 | design 调用的 `hasCustomBackground()` API 不存在且 `backgroundColor != null` 恒真陷阱 | TopBarConfig 新增值比较判定封装（后经红队 R1 再修正为 resolve 兜底） |
| P1 | "isRegular 恒 true"论断以偏概全（仅 REGULAR 用户群死代码） | 根因表述与验证预期修正 |
| P1 | 硬编码色排查口径漏检（真违规是 colorScheme 直读非 0x 字面量） | 三文档排查口径统一 |
| P1 | 系统返回 dirty 拦截无实现挂点 | ComposeDialogFragment 新增 onBackIntercepted() 钩子 |
| P2×6 | alpha 叠乘语义/460dp 表述/抽验清单/checklist 幽灵链接/滑条重建风暴/thumb 结构色 | 全部修正 |

## R1 执行模拟对抗（评级 C：4P0+8P1+6P2，全部整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P0-1 | `LegadoMiuixSwitch` 已存在（LegadoMiuixComponents.kt:281，palette 契约+AppDialogSwitchRow 等消费点），新建同名组件=同包 Conflicting overloads 编译失败；改函数体外溢全 App 开关视觉 | LegadoMiuixComponents.kt:281/AppComposeDialogs.kt:1846 | 方案改为复用既有组件+toMiuixPalette 桥接；BookshelfMiniSwitch 保持不动；AD-01/File Changes/tasks §2 重写 |
| P0-2 | dirty 拦截漏第三关闭通道：点弹框外部走 Dialog.cancel() 不经 handleDialogBack，未保存静默丢失 | ComposeDialogFragment.kt:89-94；ThemeEditorDialogFragment 未设 isCancelable=false | ThemeEditorDialogFragment isCancelable=false，关闭收敛三路径（返回/取消/保存） |
| P0-3 | isDirty 单快照不可实现：state 含非编辑字段（isNight/applySuccess/suggestions/extracting/wallpaperBitmap）+日夜双草稿 drafts 整体替换 → 零编辑误报/保存后仍脏 | ThemeEditorViewModel.kt:56-78/90-91/166-172 | toDirtyComparable() 投影 + 按模式 initialSnapshots + applySuccess 复位 |
| P0-4 | manageBgAlpha 消费无落点：Scaffold 根 Column 本就 transparent，真实底色=宿主 windowBackground（不透明），顶栏与内容不重叠；copy(alpha) 会覆盖 wallpaperAlpha 调制 | AppManagementScaffold.kt:85-99/141-150 | 消费模型选定：根 Column 显式背景绘制层+顶栏终色；统一调制层（壁纸 alpha→fraction 同点应用）；S6 以可观测差异验收 |
| P1-5 | hasCustomBackground 裸值比较 null 盲区：自定义包 JSON 的 backgroundColor 可为 null → null != default 误判"自定义"，沉浸开关对该包失效（恰是 P5 要修的病） | TopBarConfig.kt:69/485-498 | 判定改为 resolveBackgroundColor（内含 ?: 兜底）值比较 |
| P1-6 | isRegular 三处联动未定义（wallpaperFile/cornerRadius/topBarContentColor） | AppManagementScaffold.kt:133-152 | design 明确 wallpaperFile/cornerRadius 门控不变，仅重写 topBarColor |
| P1-7 | wallpaperAlpha-only 自定义被误判（只调透明度未改背景色的顶栏包丢失调制） | AD-05 tradeoff 缺口 | 登记接受语义（罕见配置） |
| P1-8 | "全项目无裸 Switch 0 残留"不可达：组件内部 fallback 与预览画布为合法点 | LegadoMiuixComponents.kt:312/ThemeEditorScreen.kt:737 | 检查口径改为排除两处合法点 |
| P1-9 | S4 与现实矛盾：null 时 valueText 显示"跟随默认"文案非"10" | ThemeEditorScreen.kt:404-406 | S4 验收改为"滑块 25% 偏左+文案错位接受" |
| P1-10 | 滑条拖动中间值无宿主：渲染层 spec.value 驱动回显，照字面实施松手弹回 | SettingSpecScreen.kt:370-405/ThemeConfigFragment.kt:48 | draft+refreshSettings（refreshTick 重组桥）方案写入 design |
| P1-11 | 取色替换未分层：39 行命中含预览画布（文件头门禁注释禁改）与 SimpleColorPickerDialog，一刀切破坏预览语义 | ThemeEditorScreen.kt 全文 | 分层处置：chrome 区替换/预览画布豁免/Picker 登记二期 |
| P1-12 | 按钮迁移落点含糊（Fragment actions vs Screen 参数） | ThemeEditorDialogFragment.kt:58 | 明确 Fragment actions lambda 实现 |
| P2×6 | 标题 Row 结构/开关 semantics+双响应/ehandleDialogBack 语义表/图标选型/applyConfig RECREATE 竞态/REGULAR 透明度双口径债务 | 各处 | design 补细节+验证关注项 |

## R2 稳定健壮对抗（⚠️：2P0+4P1+8P2，全部整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P0-1 | manageBgAlpha 无 clamp：脏 pref（150/-5）→ copy(alpha>1) 抛 IllegalArgumentException → 5 管理页全崩；项目 alpha 族既有范式全 coerce | AppConfig.kt:2174-2177/2151/2453 | get/set 双向 coerceIn(0,100) 写入 spec R6/design P6/tasks 7.4 脏值验证项 |
| P0-2 | E-Ink 契约未排除：透明度+hasCustomBackground 误判双重破坏白底黑字契约 | AppComposeDialogs.kt:123-127/TopBarConfig.kt:310-311/ComposeDialogFragment.kt:34 | fraction = if(isEInkMode) 1f 强制豁免，E-Ink 回归验证项 |
| P1-1 | dirty 判定定义缺陷（同 R1-P0-3，独立取证） | ThemeEditorViewModel.kt:276 等 | 同上，另补 applySuccess 永不复位导致重复自动关闭问题 |
| P1-2 | 第三关闭通道绕过（同 R1-P0-2，独立取证） | ComposeDialogFragment.kt:39-51 | isCancelable=false |
| P1-3 | 本地顶栏包烘焙背景色 vs 主题背景后续变更 → 值比较误判"自定义" | TopBarConfig.kt:196-203 | AD-05 Tradeoff 登记接受语义；6.3 验收补改主题背景回归 |
| P1-4 | LegadoMiuixSwitch 同包重名冲突（同 R1-P0-1，独立取证） | LegadoMiuixComponents.kt:281-328 | 同 R1 整改 |
| P2×8 | 分 key 决策声明/双 alpha 叠乘矛盾/内容色先于 alpha/RECREATE 双发容忍/进程死亡 IntentData 降级/标题 Row weight/semantics MUST+双渲染路径回归/74 文件笔误+remember 读取 | 各处 | 全部写入 design P3/P5/P6 |

## R3 通用遗漏对抗（⚠️：1P0+4P1+3P2，全部整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P0-1 | P5 新决策链丢失 REGULAR+壁纸 wallpaperAlpha 调制维度 → "仅设壁纸不改背景色"用户壁纸被不透明顶栏遮死（修复自身引入回归） | AppManagementScaffold.kt:141-150/159-167 | 统一调制层保留壁纸 alpha（6.1 验收补"壁纸仍可见"） |
| P1-1 | 内容色未随新链联动：topBarContentColor 锚定 isRegular，alpha 后对比度失真 | AppManagementScaffold.kt:151 | contrastOn(topBarBase) 先于 alpha 决策 |
| P1-2 | 截断排查清单不完整：NavigationBarManageActivity:1239（同款 460dp）/AiProviderEditScreen:487/ThemeManageActivity 预览卡/AppearanceKitActivity 等同族候选 | 各文件 | tasks 5.3 清单扩展 |
| P1-3 | manageBgAlpha 作用域边界未登记：非 Scaffold 管理族宿主（ThemeManageActivity/TopBarManageActivity 等）不吃 alpha | AD-06 | 边界显式登记防验收误判 |
| P1-4 | R1.1 全称量词与 Scope 矛盾（"开关类组件"会被解读为含 Checkbox/RadioButton，实际存在 3 处同源离群但视觉未脱主题） | SingleChoiceDialog.kt:78/ServersDialog:216/SettingsSelectableRow:94 | R1.1 限定 Switch 类+现状清单，Checkbox/RadioButton 登记二期 |
| P2×3 | dialog 域 Checkbox/RadioButton 三处离群登记/换源弹框三点迁移二期/SourceLoginActivity 登记不动 | 各处 | design"登记不动"清单 |

## 红队取证补强（三轮交叉验证的关键事实）

- 裸 M3 Switch 全项目唯一离群点 = SourceFolderConfigDialog.kt:790（R1/R3 双确认，含工作区未跟踪文件扫描）
- AppDialogFrame 调用点 82 处/74 文件（R2 修正 R1 的 76 文件笔误）
- AppManagementScaffold 宿主恰 5 处（R3 逐一核验）
- ThemeEditorScreen colorScheme 直读 38-39 行、0x 字面量 0（R1/R3 双确认）
- AppManagementScaffold 根 Column transparent、真实底色=windowBackground（R1 取证，P6 消费模型的关键事实）
- ThemeEditorViewModel 日夜双草稿 drafts + switchMode 整体替换（R1/R2 双确认）

## R4 一致性矛盾对抗（⚠️：1P0+3P1+5P2，已整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P0-1 | 统一调制层 `copy(alpha=fraction)` 为绝对赋值，顺序第二次 copy 覆盖壁纸调制 → 默认 fraction=1f 时 REGULAR+壁纸用户壁纸透出被遮死（R3-P0-1 整改声明落盘但实现公式走样，S5 验收必挂） | AppManagementScaffold.kt:142-147 现状调制 | design P5 公式改乘法合成（`alpha = wallpaperFactor * fraction`）+ 显式禁止注释 |
| P1-2 | 任务顺序断裂：6.1 消费 7.1 才创建的 manageBgAlphaFraction，按"顺序强制"执行到 6.1 编译不过 | tasks 6.1 vs 7.1 | 6.1 本期仅含壁纸调制（等价重写），fraction 合成移至 7.3 追加 |
| P1-3 | 裸 Switch 检查口径与排除清单互斥（幽灵清单）：`material3.Switch(` 全限定名实际唯一命中=修复目标本身，两处"合法点"均为短名调用不被命中 | R4 实测 Grep | 口径改 `\bSwitch\(`（覆盖全限定名+短名 import），design P1/tasks 2.2/8.2 三处统一 |
| P1-4 | S1 无对应验证任务：8.1 抽验清单缺订阅布局弹框（P1 唯一用户可见改动点全程无人工视验） | tasks 8.1 vs spec S1 | 8.1 扩为 7 类（订阅布局为 S1 直接视验点） |
| P2×5 | 39→38 行口径统一/82 含定义行口径/伪代码 API 笔误 App.Theme.→AppConfig/AD-05 补内容色行为变化登记/BookshelfMiniSwitch 行号 1002-1042 核正 | 各处 | 全部核正 |

R4 附带结论：R1-R6/S1-S7 与任务覆盖矩阵核验通过（R4.1 阴影滑条补 5.4 验收点）；与 ui-standards/frontend-ui-standards 规范无实质冲突；账本抽查 5/5 整改声明真实落盘（1 项实现层走样即 P0-1，已由 R4 抓获）；AGENTS.md 引用的 `project-rules/ui-standards/architecture.md` 路径实测在 `project-flow/ui-standards/`（上游导航漂移，另行修正，非本设计问题）。

## R5 终审：GO-WITH-NOTES

| 复核项 | 结果 |
|--------|------|
| R4 必改 4 项（P0-1 乘法合成公式/6.1→7.3 依赖重排/`\bSwitch\(` 口径/8.1 七类清单） | 全部真实、正确落盘 |
| 全轮次 P0/P1 遗留清点 | 悬空项 0（全部已整改或在 spec Drawbacks/AD Tradeoff/登记清单显式登记接受） |
| 源码事实抽查（3 指定+5 延伸） | 8/8 吻合，整改编辑未引入新事实错误 |
| 实施就绪 | 实施工程师仅凭五份文档可无歧义开工（依赖序 7.1→6.1→7.2→7.3 无断裂） |

量化评分（终审参考）：代码匹配度 96 ｜ 技术成熟度 95 ｜ 落地清晰度 94。

终审 3 个不阻塞注意点已顺手清零：①design 验证策略两处旧口径（`\bSwitch\(` 与 7 类清单）已同步 ②tasks 4.4 行数口径统一 38 行 ③五文档状态标记同步至 R1-R5。

## 红队流程结论

五轮对抗收敛：预审（1P0+4P1+6P2）→ R1（4P0+8P1+6P2）→ R2（2P0+4P1+8P2）→ R3（1P0+4P1+3P2）→ R4（1P0+3P1+5P2）→ R5 终审 GO-WITH-NOTES。累计拦截 **9 项 P0**（含撞名编译失败/脏 pref 崩溃/E-Ink 契约破坏/壁纸调制回归/公式覆盖回归等实施必炸点），全部闭环。设计文档已具备作为实施指导依据的完备度。

## 用户裁决：无二期（2026-09-03，R5 后）

用户明确"没有二期，就这一期"，R1-R5 过程中所有"登记二期/二期评估"项**全部折入本期**：

| 原二期登记项 | 本期落点 |
|-------------|---------|
| 订阅/书架两弹框开关视觉统一 | P1：既有组件加可选 stroke 参数（默认 null 零影响）+ BookshelfMiniSwitch 迁移（tasks 2.1/2.3） |
| 换源弹框三点菜单迁 titleTrailing | P2：ChangeBookSourceDialog L414-477 迁移（tasks 3.3） |
| SimpleColorPickerDialog 取色纳管 | P3：本期替换（tasks 4.4） |
| dialog 域 Checkbox/RadioButton 三处离群 | 新增 §8：SingleChoiceDialog/ServersDialog/SettingsSelectableRow 本期修复 |
| 非 Scaffold 管理族宿主透明度消费 | P6：tasks 7.4（1.5 盘点清单） |
| 弹框面板透明度"二期能力" | 改口径：由**既有 AppConfig.dialogAlpha 机制承担**（已存在，复用非新增，防双 alpha 叠乘），非延期 |
| 内容卡片级透明度兜底 | S6 验收同任务内闭环：无可观测差异则追加内容卡片级消费后复验，不遗留 |

裁决后残留登记项仅剩真实边界（非延期）：`ThemeEditorScreen` 预览画布（文件头门禁注释豁免）、`SourceLoginActivity`（View 体系全屏登录，非弹框形态）、`AppDialogFrame` 面板取色链结构（透明度由既有机制承担）。

## 新增内容红队 N1 执行模拟+事实核验（⚠️：2P0+4P1+5P2，已整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P0-1 | 裸 Switch 存量清单失真：除已登记 3 处外实测**另有 8 处未登记命中**（AutoTaskEditScreen:127/144、AiWorldBookManageScreen:585/662/1015、SettingsSelectableRow:123、SettingsToggleRow:64、RegexTestScreen:338），"排除两处合法点=0 残留"验收不可达成 | 全源码 `\bSwitch\(` 枚举 | 按用户"无二期"哲学**全部折入本期清零**（tasks 8.4），验收口径回归"0 残留" |
| P0-2 | BookshelfMiniSwitch 迁移缺失尺寸/阴影语义：原 38x22dp/16dp thumb/无阴影 vs 公共组件默认 ~52x32+shadow(3dp)，实施者被迫超纲自创 | LegadoMiuixComponents.kt:281-287/BookshelfConfigDialog.kt:1014-1017 | 既有组件新增可选 `compact: Boolean = false` 参数（mini 尺寸+关阴影），design P1 实现规格落盘 |
| P1-1 | stroke 双路径绘制机制未定义（miuix colors 无 stroke 槽，M3 有） | LegadoMiuixComponents.kt:299-308 | 统一经 switchModifier border 实现（仅未选中态），双路径共用 |
| P1-2 | 外挂 toggleable 与内层 Switch 原生语义双触发风险 | L294-309 | 删除该表述，语义由内层 Switch 原生承担 |
| P1-3 | 管理族宿主清单未闭合（约 30 候选 vs 点名 2）+ activity_theme_manage.xml 根无 background（setBackgroundColor 改造点不存在） | activity_theme_manage.xml:2-6 | 1.5 产出封闭清单（列入/豁免+理由+recreateOnThemeChange 列） |
| P1-4 | SingleChoiceDialog 为 M3 AlertDialog，容器色由 scheme 派生，"dialog 域无离群"视觉口径不成立 | SingleChoiceDialog.kt:53 | 容器色登记豁免，8.4 验收注明 |
| P2×5 | SimpleColorPickerDialog 实为 ThemeEditorScreen.kt:819 私有函数+字段映射表/ServersRow 无 style 作用域/SettingsSelectableRow 用 rememberAppSettingPalette/thumb 白→resolvedOnAccent 裁决/stroke 插参末尾安全 | 各处 | 全部落盘 |

## 新增内容红队 N2 稳定回归对抗（⚠️：4P1+5P2，已整改）

| 级别 | 发现 | 证据 | 整改落点 |
|------|------|------|---------|
| P1-1 | task 2.4 grep 验收清单被源码证伪（8 处未登记命中，同 N1-P0-1 独立取证） | 各文件行号 | 同 N1：全域清零方案 |
| P1-2 | stroke 在 miuix 主路径无实现规格；canUseRealMiuix()=SDK>=M 恒真（minSdk23），M3 fallback 是死代码；mini 38x22 vs 标准尺寸+shadow | LegadoMiuixComponents.kt:158-160/288-292/299-308 | stroke border 规格+compact 参数+M3 fallback 同步（编译一致性） |
| P1-3 | "选中 thumb 白色保留"与组件 resolvedOnAccent 浅 accent 对比度防御互斥 | BookshelfConfigDialog.kt:1039/LegadoMiuixComponents.kt:111-116 | 裁决采用 resolvedOnAccent（浅 accent 下为改善），删除白色豁免表述 |
| P1-4 | View 宿主 alpha 接入未绑定 BaseActivity 三条刷新链路——豁免页（ConfigActivity recreateOnThemeChange=false）会被 L116 无 alpha 基色覆写丢失 | BaseActivity.kt:110-120/127-144/191-207、ConfigActivity.kt:124-127 | 集成契约改为 BaseActivity 统一钩子 `manageBackgroundAlphaEnabled()`+applyBackgroundTint 消费 fraction（单点覆盖三链路） |
| P2×5 | dialogAlpha×manageBgAlpha 双低组合边界声明/mini shadow E-Ink 灰圈（compact 关阴影已解）/8.4"三处宿主"口径含糊（SingleChoiceDialog 16+ 调用点）/9.1 缺新增内容宿主/semantics 附注 | 各处 | 全部落盘（组合边界书面登记接受） |

## 新增内容红队 N3 一致性终审：GO-WITH-NOTES

| 复核项 | 结果 |
|--------|------|
| N1/N2 全部声称整改项落盘复核 | 5/5 真实落盘且五文档口径一致（全域清零 11=9+2/stroke border+compact 规格/resolvedOnAccent 裁决/BaseActivity 钩子/封闭清单契约） |
| 新增内容 vs R1-R5 整改一致性 | 无矛盾（§8 与 P5 零交集/8.3 与 8.4 同文件不同行不冲突/compact 与 AD-01 一致） |
| 源码抽查（3 指定+4 延伸） | 7/7 吻合（switchModifier 实存/8.4 行号命中/BaseActivity 三链路断言精确/Grep 全量 11 处零偏差） |
| 实施就绪 | 仅凭五文档可无歧义开工新增内容 |

N3 三个注意点已顺手清零：①design P1"其余 11 处"→"其余 9 处（总数 11=9 待修+2 豁免）"与 spec R1.1 口径同步 ②File Changes 三处文件路径核正（AiWorldBookManageScreen→ui/main/ai/compose/、AutoTaskEditScreen→ui/autoTask/、RegexTestScreen→ui/debug/）③spec 补 R1.3（Checkbox/RadioButton 清零）与 R2.4（换源迁移等价）闭合 MUST↔场景映射。

N3 非阻断观察登记：onResume 链（BaseActivity L137-144）只刷系统栏/背景图不写 tint，"单点覆盖三链路"实际语义为"不被第三链路覆写"，安全结论不变；R4/R5 账本引用重构前任务编号属历史记录正常。
换源弹框迁移无阻断（L414-477 精确、菜单锚定上移只增下方空间、分组下拉 weight 只会变宽）；dialogAlpha UI 入口实存（ThemeManageActivity L659/L817-834）；Scaffold 前提与 5 宿主清单复核吻合；SimpleColorPickerDialog 字段映射表落地（surfaceContainerHigh→fieldSurface 等五映射）。
