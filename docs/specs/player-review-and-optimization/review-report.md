# 视频/图片播放器设计文档 - 多维度审查报告

> 状态：✅ 审查完成
> 审查时间：2026-07-26
> 审查维度：用户角度 / 架构设计角度 / 风格统一角度 / 测试角度 / 源码状态核查
> 审查方法：4 个子代理并行审查 + 主代理整合
> 审查结论：**需调整**（14 个 P0 + 12 个 P1 + 11 个 P2 问题）

---

## 1. 审查结论

设计文档整体结构完整（88 任务 / 12 ADR / 13 场景），用户 10 条核心诉求覆盖度约 70%（7 条完整闭环 / 3 条部分缺失），但存在 **14 个 P0 严重问题**必须修复后才能进入实施阶段。最严重问题集中在 **ADR 编号引用错乱**、**AD-01 决策与源码不符**、**视频硬编码颜色覆盖遗漏 7 类**、**测试脚本引用完全缺失** 四个方面。

源码状态核查：11 项声明中 9 项属实、2 项不符（L4 兜底未真正移除、resetView 已改 FIT_CENTER），可信度 82%。

---

## 2. P0 严重问题（必须修复，14 项）

### P0-1：spec.md 与 design.md ADR 编号引用错乱（用户+风格维度）

**问题**：spec.md §6 矩阵和 R2.1-R2.3 引用的 ADR 编号与 design.md 实际编号严重错位。

**证据**：
| spec.md 引用 | design.md 实际 | 错位情况 |
|------------|--------------|---------|
| R2.1 → AD-06（articleStyle==2 回退） | AD-05 才是 articleStyle==2 回退 | ❌ 错位 |
| R2.2 → AD-07（header/cookie 复用） | AD-03 才是 header/cookie 复用 | ❌ 错位 |
| R2.3 → AD-08（多线程预缓存） | AD-04 才是多线程预缓存 | ❌ 错位 |
| R2.4 → "新 ADR"（图片尺寸适配） | AD-06 是图片尺寸适配 | ⚠️ 不精确 |
| 矩阵诉求5 → AD-07 | AD-03 才是 | ❌ 错位 |
| 矩阵诉求6 → AD-06 | AD-05 才是 | ❌ 错位 |

**建议**：统一修正 spec.md §6 矩阵和 R2.1-R2.5 的 ADR 编号引用，对齐 design.md 实际编号。

### P0-2：AD-01 决策与源码实际状态不符（架构维度）

**问题**：design.md L17/L154/L157 声明"移除 L4 URL 后缀兜底，5 级识别链改为 4 级"，但源码 `ExoPlayerHelper.kt:127-136` 实际仍保留 L4 兜底，仅改为"不缓存"。

**证据**：
- design.md L17：「移除 L1.5 URL 后缀快速路径与 L4 URL 后缀兜底」
- 源码 `ExoPlayerHelper.kt:127-136`：L4 仍调用 `getMimeType(url)`，仅 L131 注释"不缓存"

**建议**：二选一——
- **方案 A（推荐）**：修订 AD-01 Decision 为「保留 L4 但不缓存」（与源码一致），同步修订 spec.md R1.1、tasks.md 2.1 验证步骤、数据流图 1 增补 L4 分支
- **方案 B**：真正实施 L4 移除（删除 L127-136），仅返回 null 让 ExoPlayer 内置 sniff 尝试

### P0-3：ImagePageAdapter.resetView 状态描述过时（架构维度）

**问题**：design.md L85/L198/AD-06 Context 声明「源码 ImagePageAdapter.kt:165 resetView 用 CENTER_INSIDE」，但源码实际已改为 FIT_CENTER。

**证据**：
- design.md L85：「源码 ImagePageAdapter.kt:165 resetView 用 CENTER_INSIDE」
- 源码 `ImagePageAdapter.kt:165`：「binding.photoView.scaleType = ImageView.ScaleType.FIT_CENTER」

**建议**：修订 design.md L85/L198/AD-06 Context 为「源码已改为 FIT_CENTER，但 resetView 仍通过改变 scaleType 重置（应改为 PhotoView.scale = 1f 不改变 scaleType）」。

### P0-4：数据流图 1 与源码实现层级不一致（架构维度）

**问题**：design.md §3 数据流 1（L273-300）声明为「4 级识别链」，但源码实际为 5 级（含 L4 URL 后缀兜底），数据流图遗漏 L4 分支。

**证据**：
- design.md L284：「I -- 否 --> K[L4: 返回 null 不缓存]」直接从 magic number 失败跳到返回 null
- 源码 `ExoPlayerHelper.kt:127-136`：magic number 失败后先走 L4 URL 后缀兜底，再返回 null

**建议**：与 P0-2 同步修订——选方案 A 则增补 L4 分支，选方案 B 则保持现状。

### P0-5：任务统计数字前后矛盾（用户维度）

**问题**：spec.md、tasks.md、README.md 三处对问题总数统计不一致。

**证据**：
| 文档 | ERROR | WARN | INFO | 合计 |
|------|-------|------|------|------|
| spec.md 开头 | 32 | 38 | 13 | 83 |
| tasks.md §问题分级汇总表 | 32 | 44 | 32 | 108 |
| README.md §1 | 18 | 27 | 13 | 58（仅原始 5 份） |
| design.md §1 | 32（含明细） | 未给总计 | 未给总计 | - |

**建议**：统一三处统计口径为"含风格审查"口径（32E+44W+32I=108），README.md §1 同步更新或在文中明确"原始 5 份：18E+27W+13I，新增风格审查后：32E+44W+32I"。

### P0-6：tasks.md 任务顺序违反"代码与文档同步"原则（用户维度）

**问题**：spec.md §3.1 明确"代码修复与文档同步进行，禁止先改代码后补文档"，但 tasks.md 将文档同步（阶段 8）放在所有代码修复（阶段 2-7）之后。

**证据**：
- spec.md §3.1：「代码修复与文档同步进行，禁止'先改代码后补文档'」
- tasks.md 阶段顺序：2→3→4→5→6→7→**8 文档同步**→9 验证

**建议**：将阶段 8 文档同步拆分到各代码修复阶段内（如阶段 2.1 修复后立即更新 exoplayer-resilience 文档；阶段 4.1-4.5 补全 ADR 后立即同步 image-gallery-activity design.md），阶段 8 仅保留"全局索引同步（INDEX.md / updateLog.md）"。

### P0-7：P0 内部优先级冲突——14 个架构风格 ERROR 排在阶段 11-14 最后（用户维度）

**问题**：spec.md §4.1 明确将 14 个架构风格 ERROR 列为 P0（与 18 个原功能 ERROR 同级），但 tasks.md 将它们排在阶段 11-14（最后），与"P0 必须修复"语义矛盾。

**证据**：
- spec.md §4.1 P0 必须（32 个 ERROR）包含 R1.4-R1.9（视频架构风格）和 R2.14-R2.21（图片架构风格）
- tasks.md 阶段 11/12 标注"P0"，但排在阶段 9 验证、阶段 10 AOAdapt 日志之后

**建议**：将阶段 11-12（架构风格 P0）前移至阶段 7 之后、阶段 8 文档同步之前；或明确分两批 P0（P0-A 功能修复 / P0-B 风格统一），并在 spec.md §4.1 显式声明分批策略。

### P0-8：R4.9 UI 样式美化任务在 tasks.md 找不到对应（用户维度）

**问题**：spec.md R4.9（UI 样式美化任务）在 tasks.md 中找不到对应任务项；tasks.md 任务用 2.1/4.3 等数字编号，但未提供 R 编号↔任务编号映射表。

**证据**：
- spec.md R4.9：要求"tasks 补充 UI 样式美化任务（配色/图标/间距）"
- tasks.md 4.9 是"补全 tasks 5 项关键任务"（语义不同）
- 阶段 12 子任务（12.1/12.3/12.8）虽涉及样式，未明确标注"对应 R4.9"

**建议**：在 tasks.md 末尾新增"R 编号↔任务编号映射表"，并补全 R4.9 对应的显式任务（如阶段 12 新增 12.13"UI 样式美化总任务"）。

### P0-9：视频模块硬编码颜色覆盖遗漏 7 类共 14 处（风格维度）

**问题**：spec.md R1.6 / design.md AD-10 / tasks.md 11.3 仅覆盖部分硬编码颜色，遗漏 7 类。

**证据**（Grep 实测）：
| 文件 | 行号 | 颜色 | 设计文档覆盖 |
|------|------|------|-------------|
| `activity_video_player.xml` | 298 | `#80000000` | ❌ 遗漏 |
| `switch_episode_video_dialog.xml` | 24,25,29 | `#00000000` | ❌ 遗漏 |
| `switch_speed_video_dialog.xml` | 15,16,18 | `#00000000` | ❌ 遗漏 |
| `switch_video_dialog_item.xml` | 12 | `#FFFFFF` | ❌ 遗漏 |
| `video_layout_controller.xml` | 28 | `#000000` | ❌ 遗漏 |
| `video_layout_controller_full.xml` | 29,37 | `#000000` / `#80000000` | ❌ 遗漏 |
| `WebViewVideoPlayer.kt` | 57 | `Color.BLACK` | ❌ 遗漏 |
| `fragment_video.xml` | 52,86,172,188,201 | `android:tint="#FFFFFF"` | ❌ 遗漏（R4.35 仅图片） |

**建议**：
- R1.6 补充上述 7 类硬编码颜色的清理任务
- 明确 `video_layout_controller*.xml`（GSY 视频控制器布局）是否在本期范围——若不在，spec.md §2.2 显式排除；若在，纳入 R1.6
- R4.35 tint 规范扩展覆盖视频模块（与图片对称）

### P0-10：AD-10 颜色映射错误（风格维度）

**问题**：design.md AD-10 声明「#80000000 / #B3000000 → 复用项目 transparent50 色阶」，但 `colors.xml:29` 实际 `transparent50=#50000000`（50% 黑），80% 黑 ≠ 50% 黑。

**证据**：
- design.md L246：「#80000000 / #B3000000 → 复用项目 transparent50 色阶」
- `colors.xml:29`：`<color name="transparent50">#50000000</color>`

**建议**：在 colors.xml 新增 `transparent80`（#80000000）和 `transparent70`（#B3000000）色阶，或修正 AD-10 描述为「新增 transparent80/transparent70 色阶，复用至 video_overlay_bg 等」。

### P0-11：测试脚本引用完全缺失（测试维度）

**问题**：tasks.md §9 共 13 个验证任务，仅 9.1 提到 `./gradlew assembleDebug`、9.7 用 Grep，其余 11 个真机验证任务均未引用 `ai_tests/scripts/` 下任何脚本，违反 AGENTS.md "测试必须用 ai_tests/scripts/" 规范。

**证据**：
- `ai_tests/scripts/` 存在 `quick_build_install.py` / `l2_verify_video_player.py` / `swipe_test_log.py` / `import_rss_source_v5.py` / `dump_ui_safe_v2.py` 共 33 个可用脚本
- tasks.md 9.1 仅写 `./gradlew assembleDebug` 未引用 `quick_build_install.py`
- 9.2 视频 L2 验证未引用 `l2_verify_video_player.py`

**建议**：
- 9.1 改为引用 `quick_build_install.py`（编译+安装+L1验证）
- 9.2 改为引用 `l2_verify_video_player.py --scenario sniff`
- 9.5 跨文章预加载引用 `swipe_test_log.py capture/analyze`
- 9.6 路由回退用 `dump_ui_safe_v2.py` 抓取 Activity 栈
- 9.10 风格对比用 `dump_ui_safe_v2.py` 抓取 TitleBar/按钮 DOM

### P0-12：测试数据源清单缺失（测试维度）

**问题**：spec.md 场景1要求 m3u8+mp4+flv 三类视频源、场景8要求多 CDN 域名图片源，但 tasks.md 完全未文档化具体测试源清单（即使是源[N]代号也没有）。

**证据**：
- tasks.md 3.4 仅写"补充测试源清单（m3u8+mp4+flv 三类）"作为待办任务
- 9.x 验证任务中无任何源导入步骤
- design.md §6 真机测试要求只列验证点不列数据准备

**建议**：tasks.md §9 前新增 §9.0 测试数据准备子任务：用 `import_rss_source_v5.py` 导入视频测试源[1]/源[2]/源[3]（m3u8/mp4/flv）+ 图片测试源[4]/源[5]（单域名/多CDN域名），用代号替代真实源名称（output-safety 规范）。

### P0-13：场景 3/4 测试构造方法未说明（测试维度）

**问题**：场景3（3003 bitstream malformed 降级）和场景4（协程取消）的触发条件构造方法在 tasks.md 完全缺失，无法执行。

**证据**：
- spec.md 场景3前置"视频源返回 bitstream malformed（3003）"
- 场景4前置"用户在嗅探过程中（3秒内）退出Activity"
- tasks.md 9.x 未说明如何构造此类错误源、如何精确在3秒内退出

**建议**：
- 场景3：tasks.md 3.4 补充本地 mock 服务器配置（返回截断的 mp4 流触发 3003），或准备已知 malformed 源[6]
- 场景4：tasks.md 9.x 补充"播放长 URL 视频源，嗅探启动后立即按返回键，logcat 观察 `CancellationException` 重新抛出"

### P0-14：spec.md §2.2 与 R2.19 自相矛盾（用户维度）

**问题**：spec.md §2.2 明确排除"图片错误处理对齐视频自动降级（长期建议，本期仅手动重试优化）"，但 R2.19（图片错误降级链补全）在 P0 中要求"图片加载失败时用 alert {} 提供三选项"，语义上已构成"对齐视频降级链"。

**证据**：
- spec.md §2.2："图片错误处理对齐视频自动降级（长期建议，本期仅手动重试优化）"
- spec.md R2.19："图片加载失败时用 alert {} 提供'重试'/'浏览器打开'/'复制URL'三选项，对齐视频四级降级链"

**建议**：明确区分"手动三选项降级链（本期 P0）"vs"自动降级（长期 P2）"，将 §2.2 表述改为"图片错误处理自动降级对齐视频（长期，本期仅手动三选项降级链）"。

---

## 3. P1 中等问题（建议修复，12 项）

### P1-1：BasePlayerActivity 抽取高风险（架构+风格维度）

**问题**：design.md AD-12 决定提取 `BasePlayerActivity` 基类，但视频（全屏/PiP/字幕/倍速）与图片（PhotoView 缩放/旋转/长按菜单）业务差异大，共同点仅 3 个方法（toggleSystemBar + scheduleAutoHide + hideControlsAnimated），且 `toggleSystemBar` 已在 `ActivityExtensions.kt:187` 作为扩展函数存在，无需继承。

**建议**：改用「扩展函数 + 工具类」方案，将 `scheduleAutoHide`/`hideControlsAnimated`/`showControlsAnimated` 抽取到 `PlayerControlsHelper` 工具类；若必须抽取基类，design.md AD-12 应补充 abstract 方法清单 + 子类覆写约定 + 至少 3 个真机回归场景。

### P1-2：R2.18 FragmentStateAdapter 改造风险高（架构维度）

**问题**：将 RecyclerView.Adapter 嵌套 ViewPager2 改为 FragmentStateAdapter + Fragment 拆分，需重构 ImagePageAdapter 为 ImagePageFragment；Fragment 生命周期复杂；当前 Bug1（适配器复用）可通过简单 `updateSource` 修复，无需架构重写。

**建议**：优先实施 Bug1 简单修复（else 分支改 updateSource），架构重写降级为 P2 长期建议；若必须实施，需配套真机回归测试覆盖快速滑动/横竖屏切换/内存泄漏。

### P1-3：AD-06 横屏 fitXY 决策自相矛盾（架构维度）

**问题**：design.md L200 声明「横屏时切 fitXY（充满 View）」，但 L202 Tradeoff 自己承认「fitXY 可能导致非等比拉伸变形，需评估是否改用 centerCrop」。

**建议**：直接决策为 `centerCrop`（裁剪填充，无变形），删除 fitXY 选项；或在 Decision 中明确「优先 centerCrop，fitXY 仅作为长图特殊场景 fallback」。

### P1-4：用户验收标准过于简略（用户维度）

**问题**：spec.md §7.3 用户验收仅 2 条（10条诉求100%落地 + updateLog.md 同步），缺少可量化的成功标准。

**建议**：补充量化指标，如"嗅探准确率≥95%（m3u8/mp4/flv 三类源真机测试）"、"图片加载成功率≥90%（多域名 CDN 场景）"、"快速切换文章 10 次无数据错乱"。

### P1-5：日志规范化任务优先级冲突（用户维度）

**问题**：design.md §1 第8层"日志规范化"是 P1，但 spec.md R1.7（视频清除 Log.d）是 P0，tasks.md 11.4 也是 P0，同一任务优先级标注冲突。

**建议**：合并 tasks.md 3.1 与 11.4 为单一任务，统一优先级为 P0（因违反 AGENTS.md 硬性规范），并在 design.md §1 第8层明确"P0 部分（R1.7）+ P1 部分（R4.5）"。

### P1-6：风格统一后缺少完整回归验证（用户维度）

**问题**：阶段 14 风格统一验证仅 5 项（主题切换/视觉一致性/BottomSheet/沉浸式），未覆盖阶段 2-7 已验证的功能在风格统一后是否回归。

**建议**：阶段 14 新增 14.6 "回归验证：风格统一后重跑 9.2-9.6 核心功能场景，确认无回归"。

### P1-7：selectableItemBackgroundBorderless 改造范围边界不清（风格维度）

**问题**：Grep 显示项目其他模块（dialog_read_aloud.xml 12 处 / dialog_book_change_source.xml 3 处等）大量使用 `?attr/selectableItemBackgroundBorderless`，是项目通用按钮样式。spec.md R2.16/R2.20 仅说"图片布局无残留"，未明确是否影响项目其他模块。

**建议**：spec.md §2.1 明确「仅图片播放器范围（activity_image_gallery.xml + item_image_page.xml）改 bg_overlay_button，不影响项目其他模块的 selectableItemBackgroundBorderless 使用」。

### P1-8：ImageInfoPanel 引用未溯源（风格维度）

**问题**：tasks.md 13.1/14.4 提到 `ImageInfoPanel`，但 Grep 项目代码无此类，图片模块当前无 BottomSheet 组件。design.md AD-12 也未提 ImageInfoPanel。

**建议**：tasks.md 13.1 与 design.md AD-12 统一——若 ImageInfoPanel 为待新建组件应在 tasks.md 明确"新建 ImageInfoPanel"任务项；若为笔误应移除。

### P1-9：spec.md R2.10 与 tasks.md 任务编号体系不一致（风格维度）

**问题**：spec.md R2.10 引用任务编号 2.17/2.18/2.19/2.20/3.6，但 tasks.md 实际编号为 4.1/4.2/4.3/4.4/4.5，完全错位。

**建议**：spec.md R2.10 修正为引用 tasks.md 实际编号 4.1-4.5，或统一两文档的任务编号体系。

### P1-10：tasks.md 9.x 未在每条任务中重复包名（测试维度）

**问题**：tasks.md 9.1 明确 `io.legado.miss.app.debug`，但 9.2-9.12 真机任务未重复声明，存在执行时误用正式包风险。

**建议**：在 §9 章节开头加一行声明"本节所有真机验证任务必须使用测试包 `io.legado.miss.app.debug`（uid=10064）"。

### P1-11：场景 6/9 缺少 logcat 关键词（测试维度）

**问题**：场景6（自动路由）和场景9（协程取消）的"验证"字段无明确 logcat 关键词或 Grep 命令，无法自动化验证。场景9"数据被覆盖"不是真实 logcat 关键词。

**建议**：补充具体关键词：场景6 `Grep "ImagePlay.*set.*position"`；场景9 `Grep "loadJob.*cancel|preloadedArticles.*skip"`。

### P1-12：边界场景遗漏（测试维度）

**问题**：13 场景未覆盖三类关键边界：网络异常（断网/超时）、cookie 过期、横竖屏切换。

**建议**：至少补充：场景14（cookie 过期 → 自动重新预热 → 图片加载成功）；场景15（横屏切换 → fitXY 适配性最大展示无变形）；E-Ink 主题模式（场景10 扩展为亮/暗/E-Ink 三模式）。

---

## 4. P2 轻微问题（可选优化，11 项）

| # | 问题 | 建议 |
|---|------|------|
| P2-1 | 技术术语对用户不友好（L1.5/L4/FragmentStateAdapter 等） | spec.md 新增"术语表"附录 |
| P2-2 | README.md §7 已知限制未覆盖 R2.18 改造风险 | 补充"图片 FragmentStateAdapter 改造风险较高需充分真机验证" |
| P2-3 | design.md AD-12 提及 BasePlayerActivity 但未列入 File Changes | §4 新增"新建文件"小节 |
| P2-4 | design.md §7 与原设计文档关系未声明优先级 | 补充"冲突时以本整合设计为准" |
| P2-5 | spec.md 场景8 多域名代号（站点A/B/C）未在文档前文定义 | §1 或术语表中预先定义 |
| P2-6 | tasks.md §10 AOAdapt 日志表为空模板 | 注明"实施阶段实时填写"或删除 |
| P2-7 | design.md §8 输出安全约束章节位置不合理 | 迁移至 tasks.md「验证」章节 |
| P2-8 | AOAdapt 日志阶段划分不全 | 补全阶段行或说明"仅记录关键决策点" |
| P2-9 | 量化通过标准不够具体 | §7.1 补充"Grep 命令清单表" |
| P2-10 | 无"部分通过"机制 | 补充"P0 通过即视为基本验收，P1/P2 可后续迭代" |
| P2-11 | design.md 第9-12层与 AD-09~AD-12 模板不一致 | 第9-12层精简为"指向 AD-09~AD-12"避免重复 |

---

## 5. 源码状态核查表

| # | 设计文档声明 | 源码实际状态 | 结论 | 证据 |
|---|------------|------------|------|------|
| 1 | sniffMimeType 移除 L1.5 URL 后缀快速路径 | 源码无 L1.5 快速路径 | ✅属实 | `ExoPlayerHelper.kt:99-117` |
| 2 | sniffMimeType 移除 L4 URL 后缀兜底 | 源码 L127-136 仍保留 L4 兜底，仅改为不缓存 | ❌不符 | `ExoPlayerHelper.kt:127-136` |
| 3 | Exo2MediaPlayer.scope 未在 release() 时 cancel | 源码无 release() 重写 | ✅属实 | `Exo2MediaPlayer.kt` 全文 |
| 4 | VideoFragment 直接继承 Fragment() | 源码 L49 `class VideoFragment : Fragment()` | ✅属实 | `VideoFragment.kt:49` |
| 5 | VideoSettingsPanel 直接继承 BottomSheetDialogFragment | 源码 L48 | ✅属实 | `VideoSettingsPanel.kt:48` |
| 6 | ImageArticlePagerAdapter.bind 两分支都新建 adapter | 源码 L96 新建、L101 也新建 | ✅属实 | `ImageArticlePagerAdapter.kt:95-103` |
| 7 | ImageGalleryViewModel.loadArticleContent 无协程取消 | 源码 L57 入口无 loadJob?.cancel() | ✅属实 | `ImageGalleryViewModel.kt:57` |
| 8 | ImageGalleryActivity.toggleImmersive 用废弃 API | 源码 L217 window.setFlags + L405 systemUiVisibility | ✅属实 | `ImageGalleryActivity.kt:217,400-417` |
| 9 | ReadRss.kt L41-43 路由回退已实现 | 源码 L40-44 已实现回退 | ✅属实 | `ReadRss.kt:40-44` |
| 10 | ImagePageAdapter.resetView 用 CENTER_INSIDE | 源码 L165 实际用 FIT_CENTER | ❌不符 | `ImagePageAdapter.kt:159-166` |
| 11 | ExoPlayerHelper 日志用 Log.d/Log.e | 源码 L334,337 仍用 Log.d/Log.e | ✅属实 | `ExoPlayerHelper.kt:334,337` |

**核查结论**：11 项中 9 项属实、2 项不符（L4 兜底未移除、resetView 已改 FIT_CENTER）。设计文档对源码"已实现"声明的整体可信度约 82%，但 2 项不符均为 P0 级关键问题。

---

## 6. 过度工程化风险表

| # | 设计项 | 风险评估 | 风险等级 | 建议 |
|---|--------|---------|---------|------|
| 1 | **AD-12 提取 BasePlayerActivity 基类** | 视频/图片业务差异大；通用逻辑仅 3 个方法；`toggleSystemBar` 已在 `ActivityExtensions.kt:187` 作为扩展函数存在，无需继承 | **高** | 改用「扩展函数 + 工具类」方案；或补充 abstract 方法清单 + 子类覆写约定 + 至少 3 个真机回归场景 |
| 2 | **R2.18 图片 FragmentStateAdapter 改造** | 需重构 ImagePageAdapter 为 ImagePageFragment；Fragment 生命周期复杂；当前 Bug1 可通过简单 updateSource 修复 | **高** | 优先实施 Bug1 简单修复，架构重写降级为 P2 长期建议；若必须实施，需配套真机回归测试 |
| 3 | **R4.37 提取 BaseBottomSheetDialog 基类** | 影响 4 个 BottomSheet；4 维度统一；项目当前无统一基类是真实薄弱点 | **中** | 可实施，分阶段——先 VideoSettingsPanel + ImageInfoPanel 两个播放器 BottomSheet 继承，验证无回归后再推广 |

---

## 7. 修复优先级建议

### 第一批（必须修复，进入实施前）
1. **P0-1 ADR 编号错乱** → 修正 spec.md §6 矩阵和 R2.1-R2.5 引用
2. **P0-2 AD-01 与源码不符** → 选方案 A（保留 L4 不缓存）修订 design.md
3. **P0-3 resetView 状态过时** → 修订 design.md L85/L198/AD-06 Context
4. **P0-4 数据流图不一致** → 与 P0-2 同步修订
5. **P0-5 统计数字矛盾** → 统一三处口径
6. **P0-14 §2.2 与 R2.19 矛盾** → 明确区分手动 vs 自动降级

### 第二批（影响实施流程）
7. **P0-6 任务顺序违反同步原则** → 拆分阶段 8 到各代码修复阶段
8. **P0-7 P0 内部优先级冲突** → 前移阶段 11-12 或显式分批
9. **P0-8 R4.9 无对应任务** → 新增映射表 + 显式任务
10. **P0-9 视频硬编码颜色遗漏** → R1.6 补充 7 类清理
11. **P0-10 AD-10 颜色映射错误** → 新增 transparent80/70 色阶
12. **P0-11 测试脚本引用缺失** → tasks.md §9 引用脚本
13. **P0-12 测试数据源清单缺失** → 新增 §9.0 数据准备
14. **P0-13 场景3/4 构造方法** → 补充 mock 服务器/复现步骤

### 第三批（P1 关键项）
15. **P1-1 BasePlayerActivity 高风险** → 改用扩展函数+工具类
16. **P1-2 R2.18 高风险** → 降级为 P2
17. **P1-3 AD-06 fitXY 矛盾** → 改 centerCrop
18. **P1-4 用户验收量化指标** → 补充嗅探准确率/加载成功率
19. **P1-5 日志规范化优先级冲突** → 合并 3.1 与 11.4
20. **P1-6 风格统一后回归验证** → 新增 14.6
21. **P1-7 selectableItemBackgroundBorderless 边界** → §2.1 明确范围
22. **P1-8 ImageInfoPanel 笔误** → 统一 AD-12 与 tasks.md 13.1
23. **P1-9 R2.10 任务编号错位** → 修正为 4.1-4.5
24. **P1-10 包名重复声明** → §9 章节开头声明
25. **P1-11 场景6/9 logcat 关键词** → 补充具体 Grep 命令
26. **P1-12 边界场景遗漏** → 新增场景14/15 + E-Ink

### 第四批（P2 优化项）
27-37. P2-1 ~ P2-11 按需优化

---

## 8. 审查维度总结

| 维度 | P0 | P1 | P2 | 关键发现 |
|------|----|----|----|---------|
| 用户角度 | 5 | 4 | 3 | ADR 编号错位、统计矛盾、R4.9 无任务、§2.2 矛盾、任务顺序违反同步原则 |
| 架构设计 | 3 | 4 | 4 | AD-01 与源码不符、resetView 状态过时、数据流图不一致、BasePlayerActivity 高风险 |
| 风格统一 | 4 | 4 | 4 | 视频硬编码颜色遗漏 7 类、AD-10 颜色映射错误、tint 规范未覆盖视频 |
| 测试角度 | 3 | 4 | 3 | 测试脚本引用完全缺失、测试数据源清单缺失、场景3/4 构造方法未说明 |
| **合计** | **14**（去重） | **12** | **11** | - |

---

## 9. 优化方案

基于上述审查发现，本次优化将修订 4 个设计文档：

| 文档 | 修订内容 |
|------|---------|
| **README.md** | 同步问题统计（32E+44W+32I=108）；§7 已知限制补充 R2.18 改造风险；状态标记为"🔄 设计中（R2 修订完成，待实施）" |
| **spec.md** | §1 统计数字统一；§2.1 明确 selectableItemBackgroundBorderless 范围；§2.2 区分手动 vs 自动降级；§3.1 同步原则重申；§4.1 P0 分批策略；§4 R2.1-R2.5 ADR 编号修正；R1.6 补充 7 类硬编码颜色；R2.10 任务编号修正；R4.9 显式任务；R4.35 扩展视频覆盖；§5 场景6/9 logcat 关键词；§6 矩阵 ADR 编号修正；§7.3 量化指标；新增场景14/15/E-Ink |
| **design.md** | AD-01 修订为"保留 L4 不缓存"；AD-06 Context 修正 + fitXY 改 centerCrop；AD-10 颜色映射修正 + 新增 transparent80/70；AD-12 补充风险评估 + 改用扩展函数方案；数据流图1增补 L4 分支；§4 新增"新建文件"小节；§7 优先级声明 |
| **tasks.md** | §9 章节开头声明测试包；新增 §9.0 测试数据准备；9.x 引用具体脚本；3.4 补充 mock 服务器构造；阶段 8 拆分到各代码修复阶段；阶段 11-12 前移；新增 R 编号↔任务编号映射表；新增 12.13 UI 样式美化总任务；新增 14.6 回归验证；§10 AOAdapt 日志表注明"实施阶段实时填写" |

---

**审查报告完成**：14 个 P0 + 12 个 P1 + 11 个 P2 问题已识别并分级，源码状态核查 11 项（9✅2❌），3 个高风险设计已评估，修复优先级已规划为 4 批次。下一步将基于此报告优化 4 个设计文档。
