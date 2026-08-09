# H-1 真机验证记录（高亮规则空数据自动修复）

> 测试日期：2026-08-08
> 测试范围：harden-blank-highlight-rules-20260808 阶段B 自愈验证（S1 全空 / S2 正常 / S3 混合）
> 测试方法：模拟器（MEmu 127.0.0.1:21503）+ 测试包 `io.legado.miss.app.debug` + prefs 注入 + UI 验证 + logcat
> 测试包：`app\build\outputs\apk\app\debug\legado_miss_app_3.26.080821.apk`（含 H-1 加固）

## 1. 编译 + 安装

| 项 | 结果 | 备注 |
|----|------|------|
| assembleAppDebug | ✅ | 需 `$env:GRADLE_USER_HOME='F:\gh'`（C 盘 .gradle 损坏），--console=plain |
| adb install -r | ✅ | Success |

## 2. 自愈验证场景

| # | 场景 | 注入数据 | 结果 | 备注 |
|---|------|---------|------|------|
| S1 | 全空规则自愈 | 12 条规则 name/pattern 全部置空 | ✅ | 启动 HighlightRuleActivity → UI 显示内置中文规则名（对话高亮/书名号高亮/括号标注高亮/标题强调/心理活动/旁白说明/重点强调/诗词引用）；prefs 9241→12195B（reset 写回）；logcat 出现「高亮规则：检测到全部规则为空数据，已自动恢复内置规则」 |
| S2 | 正常数据 | 完整 12 条内置数据 | ✅（回归） | 列表正常，无自愈日志，prefs 未额外重写 |
| S3 | 混合数据不误伤 | 仅 rules[0]=dialog_default 完整，其余 11 条空 | ✅ | 无自愈日志、仅保留用户数据、不触发 reset |

## 3. 发现并修复的问题

### BUG-H01（用户真机损坏数据，已自愈加固）

| 项 | 内容 |
|----|------|
| 严重程度 | 高（功能不可用：列表空名+编辑空+不生效） |
| 描述 | 用户升级后高亮规则 12 条 name/pattern 全部为空，App 忠实展示/匹配空数据，导致规则管理列表空名、编辑对话框空、阅读页高亮不生效 |
| 根因 | 设备 prefs `highlightRuleItems` JSON 中规则字段被写空；load() 的 reset 分支（空/"[]"/解析失败/空列表）未覆盖"非空列表但全空字段"形态 |
| 复现 | 模拟器注入 12 条 name/pattern 全空 JSON → 复现 |
| 修复 | `HighlightRuleStore.load()` 在 parseArray 成功且非空后、normalizeRules 前插入 H-1 检测：`rules.all { name.isNullOrBlank() && pattern.isNullOrBlank() }` → AppLog.put + return reset() |
| 修复验证 | S1 全空自动恢复内置规则 ✓；S3 混合数据保留用户规则 ✓ |

## 4. 测试结论

- **Bug 总数**：1（BUG-H01 用户真机损坏数据，自愈加固已生效）
- **通过率**：S1/S2/S3 全通过
- **测试结论**：✅ 通过（H-1 自动修复加固真机验证完成）