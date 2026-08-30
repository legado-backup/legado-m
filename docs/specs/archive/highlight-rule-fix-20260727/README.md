# 阅读高亮规则系统修复 - 项目导航

> **创建时间**：2026-07-27
> **来源**：用户真机测试问题清单 `issues/user/temp/20260727/001/`（高亮×2）+ 深度源码分析报告 `docs/temp-analysis/highlight-rule-analysis-20260727.md` + 主代理源码核验（2026-07-27，全部锚点与当前源码逐一比对确认）
> **状态**：设计阶段，待用户审查
> **优先级**：P1（阅读核心体验缺陷，无崩溃但功能实质失效）
> **拆分自**：`docs/specs/realdevice-test-fix-20260727/` §1.9 R-P1（独立成档，专项实施）

---

## §1 项目简介

### 1.1 背景

用户真机测试反馈阅读高亮系统 2 个问题：

1. **双引号字体覆盖**：双引号被独立字体渲染后，颜色类高亮规则无法叠加到双引号区域
2. **预设规则不生效**：高亮规则管理中预设规则启用无效；新装/升级后无内置常用规则

深度源码分析确认：**绘制层无冲突（Canvas 自绘 + 逐通道 merge 天然支持字体+颜色叠加），真正根因在匹配层与数据层**——内置 12 条正则规则全部 `isRegex=false` 导致字面量匹配永不命中；首启播种逻辑缺失；预设添加写库链路断裂被静默丢弃。另发现 1 个绘制层附带缺陷（fill-only 高亮被快绘路径吞掉）。

### 1.2 核心目标

| 指标 | 当前值 | 目标值 | 修复来源 |
|------|--------|--------|---------|
| 内置规则命中率 | 0/12（isRegex=false 走字面量匹配，正则源码当普通字符串检索永不命中） | 12/12 按设计语义命中 | R-P1-2a：isRegex 修正 + 存量愈合 |
| 新装/升级后规则列表 | 空列表（无播种，`reset()` 全工程无调用方） | 12 条内置规则，对话/书名号/括号/标题 4 条默认启用 | R-P1-2b：首启播种 |
| 预设对话框添加 | 静默丢弃（重启后消失）但 toast "已添加" | 添加即写库，杀进程重启仍在 | R-P1-2c：upsert 修复 |
| 勾选/添加即时生效 | 依赖 `onDestroy` 时序才刷新阅读页 | 操作后立即生效 | R-P1-2c 连带修复 |
| 双引号字体+颜色叠加 | 颜色规则零命中 → 引号区域无任何颜色叠加 | 独立字体与颜色通道同时呈现 | R-P1-1（随 isRegex 修复自然解决） |
| optimizeRender + 背景色高亮 | 背景色矩形丢失（快绘路径吞掉） | 开/关两种状态均可见 | R-P1-1c：fill-only 快绘修复 |

### 1.3 问题清单总览

| 编号 | 问题 | 优先级 | 根因一句话 | 关键证据 |
|------|------|--------|-----------|---------|
| R-P1-1 | 双引号独立字体后颜色类高亮无法叠加 | P1 | 颜色类内置规则 `isRegex=false` → 字面量匹配永不命中，颜色从未参与绘制（非绘制层冲突） | HighlightRule.kt:33 + HighlightRuleStore.kt:129-256 + HighlightRuleMatcher.kt:27 |
| R-P1-1b | 字体规则自带字色的通道竞争（次要） | P2 | 内置对话规则自带 `textColor`，merge last-wins 语义下压过列表序在前的颜色规则 | HighlightRuleStore.kt:138 + HighlightStyle.kt:38-51 |
| R-P1-1c | fill-only 高亮被快绘路径吞掉（附带缺陷） | P2 | fill-only 样式不计入 `styledColumnCount`，`checkFastDraw` 放行后 `fastDrawTextLine` 不画 fill 矩形 | HighlightStyle.kt:31-34 + TextColumn.kt:46-56 + TextLine.kt:284-292/:196-229 |
| R-P1-2a | 内置 12 条预设规则全部不生效 | P1 | 正则 pattern + `isRegex=false` → `matchLiteral` 零命中；sanitize/愈合通道均不修正 isRegex | HighlightRuleMatcher.kt:27/:32-41 + HighlightRuleStore.kt:322/:369-378 |
| R-P1-2b | 新装/升级无内置常用规则 | P1 | `load()` 空值直接返回空列表不播种；`reset()` 有播种能力但全工程无调用方；规则存 SharedPreferences 非 Room，数据库升级不触发 | HighlightRuleStore.kt:42-60/:78-83 + PreferKey.kt:227 |
| R-P1-2c | 预设对话框添加被静默丢弃 | P1 | `ViewModel.update()` 仅按已有 id 替换，新 id `idx<0` 不入库，但 UI 仍 toast 成功 | HighlightRuleViewModel.kt:34-46 + HighlightPresetRuleDialog.kt:84 + HighlightRuleActivity.kt:85 |

> **编号说明**：R-P1-1/R-P1-2 对应用户反馈的 2 个原始问题；R-P1-1b/R-P1-1c 为分析中发现的关联缺陷；R-P1-2a/b/c 为问题 2 拆解出的 3 个独立根因。

---

## §2 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 功能规格：2 个问题的现象/根因/验收标准 + 非目标 |
| [design.md](./design.md) | 技术设计：根因源码锚点（带行号）+ 修复方案代码片段 + 成熟方案参考 + 日志设计 + 风险与回退 |
| [tasks.md](./tasks.md) | 任务清单：按 Phase 组织 + 验收勾选框 |

## §3 实施策略

- **Phase A（匹配层止血）**：R-P1-2a isRegex 修正 + 存量愈合 → R-P1-1 随动解决 → JVM 仿真器验证 + 编译
- **Phase B（数据层修复）**：R-P1-2b 首启播种 + R-P1-2c upsert/即时生效 → 编译验证
- **Phase C（绘制层收尾）**：R-P1-1c fill-only 快绘修复 + R-P1-1b UX 提示（可选）→ 编译验证
- **Phase D（验收交付）**：真机 6 项验收场景 + updateLog + 问题清单回填

> **实施顺序理由**：Phase A 改动最小、收益最大（一处字段修正同时解决两个 P1 问题的"不生效"表象）；Phase B 修数据链路；Phase C 收尾绘制层附带缺陷，均为低风险独立改动。
