# 高亮规则丢失修复 + 恢复默认规则 - 任务清单

> **创建时间**：2026-07-29
> **依据**：[design.md](./design.md) 修复方案 + [spec.md](./spec.md) 验收标准
> **状态**：Phase A/B 实施完成，待编译验证+真机验收

---

## Phase A：愈合逻辑修复（止血）

> 修复 R-1：用户编辑过的内置规则 pattern 被愈合覆盖。改动最小、止血用户数据丢失。

- [x] A.1 `shouldRefreshBuiltin` 增加 pattern 前置判断：`if (!rule.isRegex && rule.pattern == builtin.pattern) return true`，并改为接收 builtin 参数（HighlightRuleStore.kt:383-394）
- [x] A.2 `normalizeRules` 的 `builtin.copy()` 保留用户改过的 pattern/sampleText/name：`pattern = safeRule.pattern.takeIf { it != builtin.pattern } ?: builtin.pattern` 等（HighlightRuleStore.kt:282-294）
- [x] A.3 `normalizeRules` 调用 `shouldRefreshBuiltin` 处传入 builtin 参数（HighlightRuleStore.kt:281）
- [ ] A.4 编译验证（assembleDebug 通过，无警告新增）

## Phase B：恢复默认功能

> 修复 R-2/R-3/R-4/R-5：新增"恢复默认规则"菜单，支持合并+覆盖模式。

- [x] B.1 HighlightRuleStore 新增 `RestoreMode` 枚举（MERGE/OVERWRITE）+ `restoreDefaults(context, mode)` 方法（合并模式按 id 去重补充缺失内置，覆盖模式重置）
- [x] B.2 HighlightRuleViewModel 新增 `restoreDefaults(mode)` 方法（调用 store + upHighlightRules 即时生效）
- [x] B.3 HighlightRuleActivity 新增 `showRestoreDefaultDialog()` + `confirmOverwrite()`（二次确认覆盖模式）
- [x] B.4 HighlightRuleActivity `onCompatOptionsItemSelected` 增加 `R.id.menu_restore_default` 分支
- [x] B.5 res/menu/highlight_rule.xml 新增 `menu_restore_default` 菜单项（标题"恢复默认规则"）+ strings.xml(values+values-zh) 新增 10 个恢复默认相关字符串
- [ ] B.6 编译验证（assembleDebug 通过）

## Phase C：文档同步

> 修复 R-3：前序 spec tasks.md 未更新 + INDEX.md 未收录。

- [ ] C.1 更新前序 spec `highlight-rule-fix-20260727/tasks.md`：T-A1/A2/B1/B3/B4/B5/C1 标记 ✅（已实施确认）
- [ ] C.2 更新 docs/INDEX.md 收录本 spec（highlight-rule-restore-default-20260729）
- [ ] C.3 更新 docs/INDEX.md 收录前序 spec（highlight-rule-fix-20260727，标记 ✅ 已实施）

## Phase D：验收交付（真机 + 文档）

> 测试包：`io.legado.miss.app.debug`（代码优化任务用测试包）。

- [ ] D.1 真机验证 S1：编辑内置规则 dialog_default 的 pattern 为自定义正则 → 重启 → pattern 保持用户的值
- [ ] D.2 真机验证 S2：旧版数据内置规则 isRegex=false + pattern 未改 → 重启 → isRegex 愈合为 true，pattern 保持内置值
- [ ] D.3 真机验证 S3：清空全部规则 → 菜单点"恢复默认"→ 选合并模式 → 12 条内置规则出现
- [ ] D.4 真机验证 S4：有自定义规则 → 菜单点"恢复默认"→ 选覆盖模式 → 二次确认 → 重置为 12 条内置规则
- [ ] D.5 真机验证 S5：恢复默认后 → 阅读页高亮立即生效
- [ ] D.6 调试日志清理检查：Grep `android.util.Log.d|android.util.Log.e` 确认无残留
- [ ] D.7 更新 `assets/updateLog.md`（基于真实代码变更分析，逐文件审计，面向用户语言）
- [ ] D.8 问题清单回填（如有真机测试问题）

---

## 依赖与顺序说明

```
Phase A（A.1~A.4）──┐
                     ├─→ Phase D（D.1~D.8）
Phase B（B.1~B.6）──┤
                     │
Phase C（C.1~C.3）──┘
```

- Phase A 改 HighlightRuleStore.kt 愈合逻辑；Phase B 改 HighlightRuleStore.kt 新增方法 + Activity/ViewModel/menu；A 与 B 同文件不同方法，建议串行实施
- Phase C 文档同步可并行
- Phase D 任何场景不通过 → 回退对应 Phase 修复后重验，禁止带缺陷交付
