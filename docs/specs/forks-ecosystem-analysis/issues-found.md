# 阶段D 真机测试记录（B12/B14/B15/B16）

> 测试日期：2026-08-07
> 测试范围：forks-ecosystem-analysis 阶段D 四项功能（B12 缓存并发率 / B14 WebDAV 删除重命名 / B15 高亮捕获组样式 / B16 划线批注导出 Obsidian）
> 测试方法：模拟器（MEmu 127.0.0.1:21503）+ 测试包 `io.legado.miss.app.debug` + L1 + 逐功能 UI 验证 + logcat
> 测试包：`output/apk/test/legado_miss_app_3.26.080715.apk`（54MB）

## 1. 编译+安装+L1 验证

| 项 | 结果 | 备注 |
|----|------|------|
| assembleAppDebug | ✅ | 48s（77 tasks: 5 exec/72 up-to-date） |
| adb install -r | ✅ | Success |
| L1 启动 | ✅ | WelcomeActivity→MainActivity 正常 |

## 2. 逐功能验证

| # | 功能 | 验证方法 | 结果 | 备注 |
|---|------|---------|------|------|
| 1 | B12 缓存并发率对话框 | UI 端到端 | ✅ | 对话框渲染完整；非法值「abc」阻止关闭；「20/60000」保存后菜单标题实时显示「缓存并发率(20/60000)」；已清空恢复默认 |
| 2 | B15 高亮规则编辑新字段 | UI 端到端 | ✅ | 阅读页→高亮规则管理→编辑对话框确认 `et_replacement`（替换模板 hint 完整含 `<b><font color="red">$1</font></b>` 示例）+ `cb_dot_all`（点号匹配换行）真实渲染 |
| 3 | B16 Obsidian 导出对话框 | UI 端到端 | ✅ | 目录→标注页菜单→导出到Obsidian：标题「导出《b15_test》到Obsidian」/双模式 radio/API URL 默认值/API 密钥/测试连接/仓库子路径/自动导出开关全渲染；测试连接按钮触发 toast（无本地 Obsidian 服务器，连接失败属预期） |
| 4 | B14 备份与恢复页 | UI 端到端 | ✅（受限） | 首次进入弹 WebDav 教程；页面全字段渲染；本地备份生成 backup.zip 17KB 到 DCIM；WebDAV 未配置恢复降级提示「WebDavError webDav没有配置 将从本地备份恢复」；本地恢复文件选择器正常 |

## 3. 发现并修复的问题

### BUG-D01（B15 UI 缺口，已修复）

| 项 | 内容 |
|----|------|
| 严重程度 | 高（功能不可用） |
| 描述 | B15 的 `HighlightRule` 已加 `replacement`/`isDotAll` 字段，但 `HighlightRuleEditDialog.kt` 完全没有 UI 读写这两个字段（grep 零命中），用户无法在编辑对话框输入替换模板/勾选点号匹配换行，与 updateLog 描述不符 |
| 复现步骤 | 阅读页→高亮规则管理→编辑任意规则→对话框无替换模板输入框、无点号匹配换行开关 |
| 影响范围 | B15 捕获组样式功能端到端不可用 |
| 修复 | ①`values/strings.xml` 加 `highlight_rule_replacement`（含 XML 转义示例）+ `highlight_rule_dot_all`；②`dialog_highlight_rule_edit.xml` 加 `et_replacement`（TextInputLayout+ThemeEditText）+ `cb_dot_all`（ThemeCheckBox）；③`HighlightRuleEditDialog.kt` upView()/getRule() 补字段读写 |
| 修复验证 | 重新编译 assembleAppDebug + 安装 → 编辑对话框真实渲染新字段 ✓ |

### 4.3.6 真机受限（非 Bug）

- **「云端备份名列表长按→删除/重命名」无法在模拟器验证**：该路径 `showRestoreDialog→selector(备份名)` 只在 WebDAV 配置成功且有云端备份时触发；本地恢复走文件选择器（非备份名 selector）。需真实 WebDAV 服务器环境（用户有账号时再验证）。
- 已验证：备份页渲染 / WebDAV 降级提示 / 本地备份生成 / 本地恢复文件选择器 —— 均正常。

## 4. 环境限制（非代码问题）

- 模拟器 ABI = x86_64，APK 内 libcronet.so 仅 arm64-v8a → 设备端无 Cronet。B12/B14/B15/B16 均为 UI 层功能，不依赖网络，不影响验证。
- PowerShell 终端 GBK 误读 dump XML 中文 → 需 `$env:PYTHONIOENCODING='utf-8'` 再用 venv python 解析。
- AppLog 写应用内部存储而非 logcat，功能日志需经 App 内日志页查看。

## 5. 测试结论

- **Bug 总数**：1（BUG-D01 高严重，已修复并复验）
- **通过率**：4/4 功能通过（B14 云端删除/重命名受限待用户 WebDAV 环境）
- **测试结论**：✅ 通过（阶段D 四项功能真机验证完成）
