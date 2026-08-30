# Tasks：修复高亮规则开关切换不即时刷新

## 1. 准备工作
- [x] 1.1 确认需求范围（修复 + 排查 + 规范补齐） ✅ 2026-08-30
- [x] 1.2 阅读相关源码（HighlightRuleActivity/ViewModel/Screen/HighlightRule.kt） ✅ 2026-08-30
- [x] 1.3 子代理全量审计同类模式（结论：仅 HighlightRuleActivity:58-61 一处确认，28 处先例均为 copy 模式） ✅ 2026-08-30

## 2. 核心实现
- [x] 2.1 修复 `HighlightRuleActivity.kt` onEnableToggle：原地修改 → `rule.copy(enabled = enabled)` ✅ Level 1（Edit 已确认落盘；原文件已备份 `bak/fix-highlight-rule-toggle-refresh/`）
- [x] 2.2 更新 `frontend-ui-standards.md`：§4 红线 5 / §5 门禁清单项 / §6 已知坑 ✅ 2026-08-30（三处串行 Edit 确认落盘）
- [x] 2.3 基于 git diff 更新 `updateLog.md`（2026/08/30 修复条目，追加在 cronet 行后） ✅ 2026-08-30
- [x] 2.4 编译验证（并入 3.1 `build-legado.bat` 全量构建门禁） ✅ BUILD SUCCESSFUL 6m8s（2026-08-30）

## 3. 验证
- [x] 3.1 打测试包 `build-legado.bat` 并安装（测试包 io.legado.miss.app.debug） ✅ `legado_miss_app_3.26.083009.apk` 已生成（output/apk/test/）+ MEmu 装机 Success；daemon 已自动清场
- [x] 3.2 真机/模拟器 L2 验证 ✅ Level 3 场景验证：`l2_verify_highlight_toggle.py` 四项断言 ALL PASS——①点选立即翻转 ②其它行不受影响 ③重启持久化 ④反向还原+持久化（12 条内置规则实测）

## 4. 文档同步
- [x] 4.1 更新 `docs/INDEX.md` 状态流转 ✅ 已标记"✅ 实施完成（编译门禁 BUILD SUCCESSFUL 6m8s；MEmu L2 四项断言 ALL PASS）"
- [x] 4.2 tasks.md 全量回执 + README 状态更新 ✅ 2026-08-30

## 交付清单
| 项 | 值 |
|----|----|
| 测试包 | `legado_miss_app_3.26.083009.apk`（output/apk/test/） |
| 源码变更 | HighlightRuleActivity.kt（1 处，copy 替代原地修改） |
| 规范变更 | frontend-ui-standards.md §4 红线5 + §5 门禁项 + §6 已知坑 |
| 验证脚本 | ai_tests/scripts/l2_verify_highlight_toggle.py（沉淀复用） |
| updateLog | 2026/08/30 修复条目已追加 |
| 日志残留 | 0（Grep android.util.Log.d/e 无命中） |
| AOAdapt | 无异常，任务按预期完成 |

## AOAdapt 日志

（实施中遇到问题时记录）
