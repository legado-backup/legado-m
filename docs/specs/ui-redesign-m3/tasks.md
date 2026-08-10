# tasks.md — UI 重构设计 任务清单

> 本 spec 交付 **设计文档**。任务 = 完成 4 页设计 document + forks 深度学习清单 + 8 页面设计 outline 全部落地 pages/。不写代码。

## 1. 需求分析（已完成）
- [x] 1.1 确认需求范围（仅设计，保留暗夜紫，学习开源 fork）
- [x] 1.2 阅读相关源码（ThemeStore/LegadoTheme/ComposeActivitySupport/themeConfig.json）
- [x] 1.3 审核 33 个 fork 的 UI 资产（深度版：HapeLee/325506/legadoT/legados/Suml-1/youfengnoGht/Jingshiro）

## 2. 设计 Token 体系
- [x] 2.1 设计 color 令牌（三内置+暗紫，中心色板表）
- [x] 2.2 设计 spacing/radius/typography 令牌（复用路径）
- [x] 2.3 绘制栅格系统文档（360dp 基准/16dp 边距/档位表）

## 3. 主题系统设计
- [x] 3.1 确认 ThemeSpec（4 内置）与 ThemeConfig.applyConfig 联动
- [x] 3.2 确认阅读器独立配色（ReadBookConfig）不联动全局方案
- [x] 3.3 明确「暗夜紫为默认 dark」保留方案

## 4. Fork 深度学习清单
- [x] 4.1 深挖 HapeLee/legados/Rimchars/legado_NG 四仓前端（架构/组件/弹窗/主题/我的页）
- [x] 4.2 深挖 legado-Harmony 鸿蒙版 MyCenter 三级布局（统计卡→高频卡→低频列表）+ 设置分组
- [x] 4.3 原版痛点清单 8 条（长列表/弹窗深/无搜索/组件零散/角标/阅读设置路径/N过度画色漂移）逐条对齐解法
- [x] 4.4 产出 four-fork-deep-dive.md（组件化清单 + MyCenter 方案 + 风险红线）
- [x] 4.5 design.md 新增 AD-15（组件化优先）与 AD-16（My 页三级布局）
- [x] 4.6 深挖 MoRealm（墨境）：克隆 temp/forks-comparison/morealm-reader，逐源码拆解导航/主题/组件/阅读器/书架（两子代理+父代兜底）
- [x] 4.7 产出 morealm-deep-dive.md（Top10 可搬运组件 + 权衡表）
- [x] 4.8 design.md 新增 AD-17（PillNavigationBar 替代底部导航）与 AD-18（主题 5色→34槽位公式）；File Changes/README 索引同步
- [x] 4.9 新增 frontend-synthesis.md（整体前端思想综合：五支柱/贡献矩阵/不裁剪红线清单/Phase 0~4），design/README/INDEX 引用同步
- [x] 4.10 新增 implementation-spec.md（实现细化：17 组件签名/主题 toM3Scheme 映射/真实锚点/PR+KPI/themeConfig 封口），design/README/INDEX 引用同步

## 5. 页面设计（8 页四要素）
- [x] 5.1 书架（主 Grid）→ P1.md
- [x] 5.2 阅读器页 → P2.md
- [x] 5.3 书籍详情 → P3.md
- [x] **5.4 我的/设置（鸿蒙三级布局 → P4.md 重写，含真实统计+搜索+组件复用）**
- [x] 5.5 书源管理 → P5.md
- [x] 5.6 发现 / 网络书城 → P6.md
- [x] 5.7 RSS / 订阅源 → P7.md
- [x] 5.8 正文内浮层 → P8.md
- [x] 5.9 每页绘图 Prompt 统一前缀策略（写进 pages/_template.md）

## 6. 验证
- [x] 6.1 每页检查五要素齐（布局/交互/Compose 思路/绘图 Prompt）
- [x] 6.2 主题 4 套（含暗紫）在文档中一致
- [x] 6.3 docs/INDEX.md 更新 spec 条目
- [x] 6.4 与现有基础设施引用一致（之已存在代码不加改动）

## 7. 审查
- [x] 7.1 提交检查点1：用户审查设计（AskUserQuestion）
- [x] 7.2 按反馈修订（共三轮：深度不足→四仓鸿蒙→MoRealm→整体综合→实现细化）
- [x] 7.3 标记 README 状态与 INDEX 归位 → ✅ 设计完成

## AOAdapt 日志

- [x] 首轮审查反馈"深度不足" → 产出深度版 forks-deep-dive.md（逐源码核验）+ design.md 新增 AD-05~AD-14 + 用户旅程状态机
- [x] 用户点名四仓（HapeLee/legados/Rimchars/legado_NG）+鸿蒙版 → 产出 four-fork-deep-dive.md、P4 重写为鸿蒙三级布局、AD-15/16
- [x] 用户点名 morealm-reader（纯 Compose 现代工程标杆）→ 克隆+逐源码拆解 → morealm-deep-dive.md + AD-17/18
- [x] 用户质疑是否「整体前端视角」→ 新增 frontend-synthesis.md（五仓收敛+不裁剪红线清单 A~D）
- [x] 用户确认「全部补齐再开工」→ 新增 implementation-spec.md（17 组件签名+主题映射+文件锚点+PR/KPI+themeConfig 格式封口）
- [x] 用户确认「设计具备开发支撑」→ 设计阶段定稿 ✅，README/INDEX 状态清零，UI 重构设计闭环
- [ ] 后续任务过程记录 Action / Observation / Adapt（实施阶段立项后另行跟踪）

## 备注

- 本任务**不包含代码修改**；`src/` 全程不动。
- 实施阶段（另行立项）才动 `ui/theme/` 或页面 Compose 迁移。