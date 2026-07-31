# 阅读高亮规则系统修复 - 任务清单

> **创建时间**：2026-07-27
> **依据**：[design.md](./design.md) 修复方案 + [spec.md](./spec.md) 验收标准
> **状态**：代码实施完成（核心修复已实施），待真机验收
> **说明**：所有行号为 2026-07-27 源码核验确认的当前行号；实施时若遇偏移以方法名/锚点描述为准

---

## Phase A：匹配层止血（isRegex 修正 + 存量愈合）

> 同时解决 R-P1-1（字体覆盖主根因）与 R-P1-2a（预设启用无效）。改动最小、收益最大。

- [x] T-A1 `createDefaultRules()` 12 条内置规则全部补 `isRegex = true`（HighlightRuleStore.kt:129-256，每条构造函数加一个参数，共 12 处）
- [x] T-A2 `normalizeRules()` 刷新判定增加 isRegex 愈合条件：`builtin != null && !safeRule.isRegex && safeRule.pattern == builtin.pattern` → 走 `builtin.copy(...)` 刷新通道（HighlightRuleStore.kt:266-267；刷新通道本体 268-280 行沿用不动）
- [ ] T-A3 JVM 仿真器验证：12 条内置 pattern 以 `isRegex=true` 对各自 `sampleText` 至少 1 次命中；同批 pattern 以 `isRegex=false` 0 命中（回归对照）（HighlightRuleMatcher.kt:22-63 纯函数；规则样本 HighlightRuleStore.kt:131-255）
- [ ] T-A4 merge 叠加断言：fontPath 样式与 textColor 样式经 `HighlightStyle.merge()` 后两通道同时非默认（HighlightStyle.kt:38-51）
- [ ] T-A5 编译验证（assembleDebug 通过，无警告新增）

## Phase B：数据层修复（首启播种 + 写库 + 即时生效）

> 解决 R-P1-2b（无初始化）与 R-P1-2c（预设添加静默丢弃 + 即时性）。

- [x] T-B1 `load()` 空值播种：`stored.isNullOrBlank()` 分支改为 `return reset(context)`（HighlightRuleStore.kt:44-47；reset 本体 78-83 行不动）
- [ ] T-B2 播种语义自检验证：`"[]"` 不重复播种（用户清空全部规则后重启列表保持为空）
- [x] T-B3 `HighlightRuleViewModel.update()` 升级 upsert：`if (idx >= 0) list[idx] = rule else list.add(rule)`（HighlightRuleViewModel.kt:38-39；对齐 HighlightRuleEditDialog.kt:229-236 先例）
- [x] T-B4 预设添加保留内置 id：去掉 `id = System.currentTimeMillis().toString()` 覆盖（HighlightPresetRuleDialog.kt:83-86），重复添加走 upsert 刷新防副本堆积
- [x] T-B5 即时生效：`update()` 写库成功后调 `ReadBook.upHighlightRules()`（HighlightRuleViewModel.kt:41-44 onSuccess 链路；对标 HighlightRuleEditDialog.kt:238 既有模式；HighlightRuleActivity.kt:139-142 onDestroy 调用保留）
- [ ] T-B6 Grep 复核 `update(` 全部调用方，确认 upsert 语义扩散无负面影响（HighlightRuleActivity.kt:144、HighlightRuleAdapter.kt:80-87 勾选链路）
- [ ] T-B7 编译验证（assembleDebug 通过）

## Phase C：绘制层收尾（fill-only 快绘修复 + 可选 UX 提示）

> 解决 R-P1-1c（附带缺陷）；R-P1-1b 为可选增强。

- [x] T-C1 `fastDrawTextLine()` 逐列循环补画 fill 矩形（TextLine.kt:223-228 循环内，逻辑同 TextColumn.kt:74-77，`view.highlightPaint(fill)`）
- [ ] T-C2 （可选）字体规则去色 UX 提示：`bindFontRow()` 字体行增加"字体规则建议清除字色，避免覆盖其他颜色规则"提示（HighlightStyleDialog.kt:203-211）
- [ ] T-C3 编译验证（assembleDebug 通过）

## Phase D：验收交付（真机 + 文档同步）

> 测试包：`io.legado.miss.app.debug`；脚本固定 `ai_tests/scripts/`。

- [ ] T-D1 真机验收场景 1：清除应用数据启动 → 高亮规则管理可见 12 条内置规则，对话/书名号/括号/标题 4 条默认勾选（对应 spec §1.2-1）
- [ ] T-D2 真机验收场景 2：预设对话框添加任一规则 → 管理列表出现 → 杀进程重启 → 规则仍在（对应 spec §1.2-2）
- [ ] T-D3 真机验收场景 3：启用"对话高亮"→ 含对话章节引号区域着色；启用"书名号高亮"→ 波浪下划线（对应 spec §1.1-2/§1.1-3）
- [ ] T-D4 真机验收场景 4：对话规则设独立字体 + 启用命中引号内文本的颜色规则 → 双引号区域字体+颜色同时呈现（对应 spec §1.1-1，问题 1 终验）
- [ ] T-D5 真机验收场景 5：管理页勾选/取消勾选 → 直接返回阅读页 → 高亮立即出现/消失（对应 spec §1.2-4）
- [ ] T-D6 真机验收场景 6：`optimizeRender` 开/关两种状态下 fill 背景色高亮均可见（对应 spec §1.1-4）
- [ ] T-D7 回归验证：手动划线与规则高亮同区叠加时手动压规则（ContentTextView.kt:129-133 顺序不变）；删除全部规则重启后列表保持为空（spec §1.2-5）
- [ ] T-D8 调试日志清理检查：Grep `android.util.Log.d|android.util.Log.e` 确认无残留（遵守 logging-during-refactoring 规范）
- [ ] T-D9 更新 `assets/updateLog.md`（基于真实代码变更分析，逐文件审计，面向用户语言）
- [ ] T-D10 问题清单回填 `issues/user/temp/20260727/001/` 修复状态 + `docs/INDEX.md` 收录本 spec 目录

---

## 依赖与顺序说明

```
Phase A（T-A1~T-A5）──┐
                      ├─→ Phase D（T-D1~T-D10）
Phase B（T-B1~T-B7）──┤
                      │
Phase C（T-C1~T-C3）──┘
```

- A/B/C 三 Phase 改动文件互不重叠（A：HighlightRuleStore.kt；B：HighlightRuleStore.kt:44-47 + ViewModel + PresetDialog；C：TextLine.kt），B 中 T-B1 与 A 中 T-A1/T-A2 同文件不同方法，建议同一工作会话内按 A→B→C 顺序串行实施，避免并发改同一文件
- T-A2 愈合依赖 T-A1 的内置 pattern 为最新值，必须 A 内先行
- Phase D 任何场景不通过 → 回退对应 Phase 修复后重验，禁止带缺陷交付
