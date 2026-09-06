# tasks.md — main-topbar-transparent-align

## 1. 准备工作
- [x] 1.1 确认工作区状态与分支（当前 feat/master-track-waves，需评估是否新开分支或沿用，避免与并行会话变更混淆）
  - AOAdapt: 实况=master 分支（记忆中 feat 分支已过期），工作区有并行会话未提交变更；目标两文件 git status 干净，决定沿用 master 串行小步修改、不新开分支（避免搁浅并行变更）
- [x] 1.2 备份待改文件到 bak 目录（MaterialValueHelper.kt、BaseActivity.kt）→ 同目录 *.bak
- [x] 1.3 全量 Grep 盘点 `backgroundColor` 消费点清单（Context/Fragment 扩展的调用方），回填 design.md 回归盘点表 (L1) → 17 文件已回填

## 2. 核心实现
- [ ] 2.1 MaterialValueHelper.kt：恢复 `Context.backgroundColor` 透明分支（`!AppConfig.isEInkMode && ThemeConfig.hasUsableBgImage → TRANSPARENT`）+ `Fragment.backgroundColor` 委托 context (L2)
  - 热点约束：master-track 热点⑧串行文件，light-theme 已交付属性（isDarkTheme/字色派生）禁止回退，实施前后逐行 diff 确认仅动目标属性
  - 验证标准：Grep 确认分支存在；与 archive-ref 同名文件 L74-79/L118 逐行比对一致
- [ ] 2.2 MaterialValueHelper.kt：`dialogSurfaceBackground` 摘除 backgroundColor 依赖，对齐 Archive（`themeColorOrNull(PreferKey.themeCardColor) ?: R.color.dialog_surface`）(L2)
  - 验证标准：Grep 确认不再消费 backgroundColor；弹窗底色来源与 Archive L196-200 一致
- [ ] 2.3 BaseActivity.kt：`initTheme` 非管理页宿主路径对齐 Archive（清 tint + fallback 实色），保留 `manageHostTintColor()` 管理页钩子 (L2)
  - 验证标准：Grep 确认管理页分支保留 + 非管理页分支清 tint
- [ ] 2.4 BaseActivity.kt：`upBackgroundImage` 基类恢复 Archive 三分支（无图→清 tint+实色 / 有图→清 tint 后挂图 / 异常→实色）(L2)
  - 验证标准：三分支逐一比对 Archive 版本；MainActivity override 路径不受影响确认
- [ ] 2.5 更新 updateLog.md（基于 git diff 三步流程，编译前完成）(L1)

## 3. 验证测试
- [ ] 3.1 编译验证：`build-legado.bat`（构建前 Get-Process 校验构建进程）(L1)
- [ ] 3.2 真机 L2 验证矩阵（测试包 io.legado.miss.app.debug）：四 Tab × 背景图 on/off × 昼夜主题，头部（状态栏+顶栏）视觉逐项截图比对 (L2)
  - 验证标准：背景图 on 时四 Tab 头部透出背景图无实色色带；off 时与修复前一致
- [ ] 3.3 消费点回归：管理页（AppManagementScaffold）、设置组件（AppSettingComponents）、书源封面（BookCoverImage）、弹窗底色（dialogSurfaceBackground 任选 3 类弹框）、发现页 TitleBar 托管链（topBarColorManaged）、1.3 清单中其余消费点逐一过一遍；另抽查 2-3 个普通 Activity（BaseActivity.upBackgroundImage 基类路径）背景图 on/off (L2/L3)
  - 验证标准：背景图 on/off 两形态无黑块/穿帮/对比度异常；弹窗不透明正常
- [ ] 3.4 E-Ink 抽查（如设备可用）：E-Ink 模式 + 背景图 → 头部仍实色 (L3)
- [ ] 3.5 兜底排查（仅在 3.2 未达标时执行）：按 decorView → 窗口背景层 → Fragment 根 → 顶栏渲染逐层定位并回改设计 (L3)

## 4. 文档收尾
- [ ] 4.1 移除临时调试日志/文件，Grep 确认零残留 (L1)
- [ ] 4.2 文档同步：按声明式映射核对（取色基线相关文档/INDEX 状态流转）(L1)
- [ ] 4.3 issues-found.md 记录真机问题（如有）(L1)
- [ ] 4.4 检查点 2 最终验收（AskUserQuestion），通过后归档到 docs/specs/archive/ (L1)

## AOAdapt 日志
（开发中遇到问题时记录）
