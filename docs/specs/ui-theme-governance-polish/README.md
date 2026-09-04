# UI 主题纳管与弹框交互优化（ui-theme-governance-polish）

> 状态：✅ 设计完成（🔄 开发中）
> 创建：2026-09-03
> 类型：UI 优化 + Bug 修复 + 主题体系扩展

## 功能概述

本轮排查用户反馈的 6 个 UI 问题，根因均可归为两类：**主题取色未纳管**（P1/P3/P5/P6）与**弹框交互体验缺陷**（P2/P3/P4）。修复方案以现有主题体系（ThemeStore + AppDialogStyle 取色基线）为唯一权威源，补齐纳管点位并扩展"管理页透明度"配置能力，参考 archive 弹框范式但不照搬。

## 核心能力

| # | 问题 | 根因 | 修复方向 |
|---|------|------|---------|
| P1 | 订阅布局弹框"升序排列"开关底色与主题色不匹配 | 裸用 M3 Switch 无 colors 映射，脱离取色基线（全项目唯一离群点） | 换用既有 `LegadoMiuixSwitch` + toMiuixPalette 桥接；组件加可选 stroke 参数并迁移书架弹框，**本期完成两弹框开关视觉统一** |
| P2 | 登录弹框底部 4 按钮拥挤需滑动 | 按钮横排超宽 | "确定"固定右下，其余 3 按钮收进标题栏三点菜单；换源弹框三点菜单一并迁移至同槽 |
| P3 | 主题编辑页无保存/取消感知 + 元素未纳管 | 自绘按钮视觉弱 + apply 即落盘 + colorScheme 直读约 38 行（0x 字面量为零） | 标准化取消/保存按钮 + 按模式快照 dirty 拦截 + 取色分层纳管（chrome 区+取色器，预览画布豁免） |
| P4 | 默认字号滑块居中 + 文字显示一半 | fallback 硬编码 `12f`（范围中点）+ 双重固定高度裁切 | 默认值偏左（10f）+ 高度策略改自适应 + 截断点扩展排查清单 |
| P5 | 管理页沉浸顶栏开关不生效 | REGULAR 顶栏风格用户（首装暗夜紫预设/顶栏包）`isRegular=true` 时开关分支被短路成死代码 | 顶栏背景决策链三级化（显式自定义→沉浸开关→默认主色）+ 壁纸调制维度保留，保证全用户群开关有效 |
| P6 | 管理页组件底色不透明，缺透明度设置 | 主题体系无透明度配置 | 新增"管理页背景透明度"设置项（coerceIn+E-Ink 豁免），**管理族全部宿主**消费（Scaffold 顶栏+根背景+非 Scaffold 管理页根背景）；弹框面板复用既有 dialogAlpha 机制；弹框域 Checkbox/RadioButton 三处取色离群本期清零 |
| P7 | 设置本地密码弹框是孤岛未托管（用户追加） | MainActivity 备份链路 `setLocalPassword()` 用旧 View 体系 `alert()`+DialogEditTextBinding，脱离 AppDialogFrame 托管体系 | 迁移至既有托管组件 `showComposeTextInputDialog`（AppDialogFrame 体系）+ ComposeTextInputDialog 新增可选 onNegative 回调保留"取消→置空"语义 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y`）+ 红队轮次账本 + AOAdapt 日志 |
| [red-team-report.md](./red-team-report.md) | 五轮红队对抗审查报告（发现分级+整改闭环） |

## 状态流转

- 🔄 设计中（当前）
- ✅ 设计完成 → 🔄 开发中 → ✅ 已完成
