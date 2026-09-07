# 子页面顶栏样式统一（subpage-topbar-unify）

## 状态
**开发中**（2026-09-07 设计审核通过）

## 功能概述
全面收敛子页面顶栏：**两层收敛 = 取色单点化 + 组件缩减（4→3）**。当前 4 套顶栏组件（AppManagementTopBar / GlassTopAppBar / ConfigTopBar / MainTopBarView）存在 3 条互不一致的取色策略，导致 30+ 子页面顶栏"要么纯黑、要么纯色"，不随主题设置体系变化。

## 核心能力
1. 在 `TopBarConfig` 新增统一三级取色决策函数（自定义背景色 → 沉浸开关页面底色 → 主题主色），全部顶栏组件接入
2. **组件缩减（检查点 R1 用户裁决）**：ConfigTopBar 消灭（并入 GlassTopAppBar）；AppManagementTopBar 定位为脚手架内置；MainTopBarView 定位为 View 过渡态（Mode.SUB 随页面迁移消亡）——顶栏 bug 修复面从 4 套缩为边界清晰的三层
3. 顶栏包壁纸态保持原语义（withOpacity + resolve），不受统一函数影响
4. 清理 4 处 XML 残留死代码顶栏
5. 豁免清单明确：主页 Mode.MAIN、看图/裁剪/播放器沉浸页、自绘搜索头页保持现状

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 |

## 变更日志
| 日期 | 变更 |
|------|------|
| 2026-09-07 | v1.2：检查点 R2 用户锚定终极目标（对标 legado_NG 全面 Compose 化），方案升格"顶栏语义色单源=Compose 化铺路"（新增 AD-05 + NG 对标章节），Mode.SUB 消亡路线挂接 master-track B 波次 |
| 2026-09-07 | v1.1：检查点 R1 用户裁决=需调整，方案升级两层收敛（取色单点化 + 组件缩减 4→3：ConfigTopBar 消灭，新增 AD-04）；红队复审通过 |
| 2026-09-07 | v1.0 初版设计（四文档 + 五轮红队审查：修复 updateLog 门禁顺序、ConfigTopBar 内容色半改状态、Mode.SUB 内容色对比校验 3 项） |
