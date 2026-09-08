# 主题字体大小：默认值统一与日夜配置生效修复

## 状态
**设计中**

## 功能概述
排查并修复主题「字体大小」（fontScale）体系的两个问题：

1. **夜间字号 Bug（确认，必修）**：主题包应用时，夜间主题的字体大小写入 `fontScaleN` 键，但全局生效链 `AppContextWrapper.getFontScale()` 及顶栏尺寸联动（MainTopBarView ×3、TopBarConfig ×1）只读白天键 `fontScale`，`fontScaleN` 全项目零读取点 → 切换白天/夜间后，字号永远按白天配置（或系统回退）生效，夜间主题配置的字体大小从未生效。
2. **默认字号策略（AD-02 已定稿）**：首次初始化安装时，内置日/夜主题字号为「跟随系统」。定稿 2A：内置主题 `fontScale=9`（0.9 倍），应用主题后生效（首装默认暗夜紫套件，实际首装即 0.9）。

## 变更点（设计目标）
- `AppContextWrapper` 字号读取增加日夜感知：夜间读 `fontScaleN`，白天读 `fontScale`
- 顶栏尺寸联动调用点（MainTopBarView / TopBarConfig）同步日夜感知
- 内置日/夜主题默认字体大小按 AD-02 决策调整（候选：统一 9 = 0.9 倍）
- 历史遗留 17 个默认主题资产（assets/defaultData/themeConfig.json）处置方案（AD-03 决策项）

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach 三要素/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR 决策/数据流/文件变更清单） |
| [tasks.md](./tasks.md) | 任务清单（分级格式 + 验证标准） |

## 变更日志
| 日期 | 变更 |
|------|------|
| 2026-09-08 | 初稿：探索结论 + 四文档生成，AD-02/AD-03 待用户反馈细化 |
| 2026-09-08 | 检查点1反馈定稿：AD-02=2A、AD-03=移除+暗夜紫迁移；新增 AD-04（暗夜紫日间变体 + 磨砂玻璃晨昏套件压缩入库与幂等 seeding）；红队复审通过 |
