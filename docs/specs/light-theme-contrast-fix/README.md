# 亮色主题文字对比度系统性修复

> **Spec 状态**：🔄 已实施·编译通过·测试包已交付（真机 L2 验证按用户裁决延后）
> **创建日期**：2026-08-31
> **交付物**：`output\apk\test\legado_miss_app_3.26.083116.apk`（io.legado.miss.app.debug）
> **来源**：用户反馈——设置内置亮色主题（默认/典雅蓝/绿意/莫兰迪/海洋/薰衣草/琥珀/护眼绿/护眼黄/牛皮纸）后，很多区域字体或组件肉眼不可见

## 功能概述

修复内置亮色主题下大量区域文字/组件不可见的系统性问题。经三轮递进审查（用户两轮质询驱动）确认四条根因：

1. **根因1（机制性，主因）**：`MaterialValueHelper.kt` 的 `isDarkTheme` 用 primary 色亮度冒充主题深浅判定（亮色主题 primary 深 → 主文字色解析为纯白 #FFFFFFFF），画在 #F5F5F5 浅底上必然不可见。影响 4 个派生属性合计 204 处消费点/50 文件。**git 考古实锤：学习源 Archive（archive-ref/legado-08172114）同名文件早已修复（isDarkTheme=AppConfig.isNightTheme + 自定义字色优先 + secondary 0.72 alpha 派生 + disabled 按 !isNightTheme），本项目 3c8aa5c7b（2026-08-23 archive UI 迁移续作）单提交内部分拷贝漏搬**。深挖另实锤：204 处消费点写法与 Archive 逐行一致（消费层零差异），源头单文件对齐全链自动修复。
2. **根因2（结构性，本项目新增层暴露）**：`ThemeConfig.applyTheme()` 从不写 `textColorSecondary`（fallback View attr 是两边共有逻辑，但本项目自创的 LegadoTheme/ThemeSpec M3 层消费它才暴露）。
3. **根因3（点状，全量 21 处）**：硬编码亮前景与浅底错配——已知 6 处（书架角标/封面白字/占位 tint/onAccent 默认值/视频面板黑字黑底）+ 第三轮全库地毯扫描净增 15 处（manga loading 白圈配主题背景、ClickActionConfigDialog 白字淡遮罩等高危 2 处；accent 白字家族 8 处收敛 `onAccentFor` 统一工具；遮罩加深；XML 死属性清理）。
4. **根因4（Compose 自创层）**：ThemeSpec 34 槽位全量推演净增 4 缺陷——inversePrimary 夜间 1.05:1 必然不可见、onErrorContainer 恒不达标、surfaceContainer 族亮色层级坍缩（弹框与背景同色观感）、outline 族 1.3:1 + guard 压平 alpha 校验虚高放行。

**选定方案**：对齐 Archive 生产验证版取色派生（Archive-aligned）——`MaterialValueHelper.kt` 以 archive-ref 同名文件为基线逐行对齐（自有演进不回退），新增本项目扩展 `onPrimarySurfaceTextColor`（primary 表面点位）与 `onAccentFor`（底色自适应前景）；新增层内闭环补写 `textColorSecondary`；Compose 槽位治理 + guard 增强（阈值 3.0、扩 6 槽、合成校验）；消费层零改动。

## 核心能力

- 内置亮色主题下主界面/弹窗/菜单/书架等全场景文字清晰可见（204 处消费点全链自动修复）
- 夜间主题、e-ink 模式零回归（`AppConfig.isNightTheme` 地基经亲自核实与 Archive 逐字一致，含跟随系统模式）
- `textColorSecondary` 与主文字同源派生（0.72 alpha），弹窗/菜单文字层级清晰稳定
- Compose 弹框表面层级可辨（surfaceContainer 族）、描边可见（outline）、inversePrimary/onErrorContainer 修复
- 根因3 全量 21 处修复，accent 白字家族收敛 `onAccentFor` 单点工具防复发
- Compose guard 阈值 1.3→3.0 + 槽位扩展 3→6 + 半透明前景合成校验
- 用户自定义字体色仍优先生效

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios S1-S9） |
| [design.md](./design.md) | 技术设计（Technical Approach/AD-01~06/Data Flow/File Changes/范围外观察项） |
| [tasks.md](./tasks.md) | 任务清单（29/36 已勾，真机 L2 九场景延后） |

## 状态标记

- 🔄 已实施·编译通过·测试包已交付（2026-08-31）：真机 L2 验证（S1-S9）按用户裁决延后，待真机走查通过后流转 ✅
