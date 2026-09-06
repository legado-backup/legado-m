# Tasks: ui-settings-fix-pack

> 格式：`- [ ] X.Y` 分级；核心任务标注验证标准与完成级别（L1 代码/L2 功能/L3 场景）

## 1 准备工作

- [x] 1.1 加载子规范：ui-standards/architecture.md + frontend-ui-standards.md + version-delivery-sync.md
- [x] 1.2 精读源码锚点（子代理查证：OtherConfigFragment switch 体系 L531-546、PreferKey L391、activeDirName/DEFAULT_DIR_NAME public、toHex6 L262）
- [x] 1.3 备份目标文件到 bak 目录（ui-settings-fix-pack_20260906/，5 文件）
- [x] 1.4 模拟器环境就绪（MEmu 21503 在线 + 测试包基线安装）

## 2 F1 搜索框显隐入口

- [x] 2.1 我的设置页新增"主界面底栏搜索框"快捷开关 (L1)（OtherConfigFragment L134-140 + isDefaultNavBarPackage L164-166 防回滚；strings 双语）
  - 验证结果：开关条目渲染 PASS、切换写 pref PASS（io.legado.miss.app.debug_preferences.xml 确认键存在）
- [x] 2.2 strings.xml（默认 + zh）新增标题/summary 资源 (L1)
- [x] 2.3 验证主界面刷新链与点击回归 (L2)：关闭开关→返回主界面悬浮搜索按钮消失 PASS；打开→恢复 PASS；点击搜索按钮→SearchActivity 前台 PASS
- [x] 2.4 一致性与防回滚验证 (L2 默认套装部分)：默认套装下开关切换链路 PASS；⚠️ 自定义底栏套装激活时条目隐藏场景未自动化（isDefaultNavBarPackage 判定逻辑已实现，待用户走查补充）

## 3 F2 字号截断排查与修复

- [x] 3.1 截断点清单落盘 (L2)：静态扫描 3 轮定性 14 候选（91→14，剔 77 误报），见附录；1.6x 模拟器抽查主界面+设置页文本完整 PASS
- [x] 3.2 逐点修复 12 处 height→heightIn(min) 跨 8 文件 (L1)，编译通过；保留 2 处设计性截断（#13 预览画布/#14 Ellipsis 简介）
- [x] 3.3 1.0x 回归 (L2 部分)：主界面/设置页/主题页 1.0x 正常渲染 PASS；修复点逐点 1.0x 截图对比未做（均为 min 语义视觉无变化）
- [x] 3.4 已知限制登记：#13/#14 保留理由见附录清单

## 4 F3 取色器恢复

- [x] 4.1 ColorPickerSheet 扩展 allowFollowDefault/onFollowDefault 可选参数 (L1)（默认关闭向后兼容；"跟随默认"OutlinedButton 样式对齐操作区）
- [x] 4.2 ThemeEditorScreen 替换为 ColorPickerSheet (L1)（toHex6 回传链对齐；SimpleColorPickerDialog 保留注释标注）
- [ ] 4.3 弹窗五场景验证（固定槽位取色/跟随默认清除/取消不落 pref/Dialog 宿主 back/点外关闭）：⚠️ 自动化仅覆盖主题设置页可达（D6 有生产先例兜底），弹窗视觉与交互场景待用户真机走查

## 5 综合验证与收尾

- [x] 5.1 编译通过（两次增量：F1+F3 首编 19:19 → F2 修复后终编 19:37，libcronet OK）
- [x] 5.2 updateLog 基于 git diff 更新（编译前，第五批条目）
- [x] 5.3 L2 真机自动化 10/10 PASS（l2_verify_ui_settings_fix_pack.py，FATAL=0）；⚠️ F3 弹窗五场景与 F2 其余 9 页面 1.6x 视觉走查待用户真机补充
- [x] 5.4 文档同步：INDEX.md/README 状态更新；无其他接口文档需同步（纯 UI 层变更）
- [x] 5.5 清理：调试日志 0 残留（rg 确认）；bak 保留至验收
- [x] 5.6 git 提交（用户验收通过后分离提交本任务文件）

### AOAdapt 日志

- [x] 5.3 pref 校验 FAIL 排查
  - Action: 脚本 run-as cat DEFAULT.xml 校验 pref 写入
  - Observation: FAIL 但 UI 显隐链路两步 PASS（pref 生效实锤）
  - Adapt: 排查发现 debug 包 pref 文件为 io.legado.miss.app.debug_preferences.xml（包名_preferences），修正脚本文件名后 10/10 PASS
- [x] L2 脚本 v1 入口崩溃
  - Action: open_other_config 用"我的"tab 文本导航
  - Observation: 文本未命中 b=None → tap(*None) TypeError
  - Adapt: 改 ConfigActivity 直达（configTag=otherConfig），与记忆中直达范式对齐

## 附录

### 3.1 截断点清单（静态扫描 3 轮定性 14 候选 + 实施处置）

修复模式：文本容器固定 height → heightIn(min=)，语义保持视觉最小高度不变

| # | 级别 | 文件 | 行号(修前) | 组件 | 高度 | 处置 |
|---|------|------|-----------|------|------|------|
| 1 | P1 | ui/book/read/config/SpeakEngineDialog.kt | 606 | InlineEngineAction TextButton | 32dp | ✅ heightIn(min) |
| 2 | P1 | ui/book/read/ReadAloudPlayerPanel.kt | 4873 | PlayerControlDock pill 行 | 40dp | ✅ heightIn(min) |
| 3 | P1 | ui/book/read/ReadAloudPlayerPanel.kt | 5118 | ChapterSheet 按钮行 | 40dp | ✅ heightIn(min) |
| 4 | P1 | ui/book/read/ReadAloudPlayerPanel.kt | 5426 | CharactersSheet 按钮行 | 40dp | ✅ heightIn(min) |
| 5 | P1 | ui/widget/components/MenuLayer.kt | 668 | 阅读菜单底栏章节行 | 48dp | ✅ heightIn(min) |
| 6 | P1 | ui/widget/components/ImportSourceSheet.kt | 217/233/242 | 全选/取消/导入按钮 | 48dp | ✅ heightIn(min)×3 |
| 7 | P1 | ui/book/read/config/SpeakerGroupManageDialog.kt | 1007 | SpeakerActionButton | 42dp | ✅ heightIn(min) |
| 8 | P1 | ui/config/BookInfoManageScreen.kt | 212 | StyleTabButton | 42dp | ✅ heightIn(min) |
| 9 | P2 | ui/widget/components/ImportSourceSheet.kt | 115 | 头部标题行 | 56dp | ✅ heightIn(min) |
| 10 | P2 | ui/widget/components/ColorPickerSheet.kt | 207/216 | 跟随默认/确认按钮 | 48dp | ✅ heightIn(min)×2 |
| 11 | P2 | ui/main/ai/compose/AiToolPreviewDialog.kt | 334 | 空态预览 Box | 110dp | ✅ heightIn(min) |
| 12 | P2 | ui/book/read/ReadAloudPlayerPanel.kt | 4817 | Dock 外层 Column | 126dp | ✅ heightIn(min) |
| 13 | P2 | ui/config/AppearanceKitActivity.kt | 651 | 套装预览画布 | 104dp | ⏸ 保留（刻意缩略预览，画布外文本不受限） |
| 14 | P2 | ui/widget/compose/SearchBookPreviewOverlay.kt | 271 | 简介 heightIn(max=84) | max84dp | ⏸ 保留（maxLines=4+Ellipsis 设计性截断，非裁剪） |

静态扫描初筛 91 处 → 剔除 77 误报（Spacer 邻接假阳性/自适应容器/滚动容器吸收）。

### AOAdapt 日志（开发中追加）
（无）
