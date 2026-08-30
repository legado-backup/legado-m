# OpenSpec 设计偏差审查报告（B0）

> 审查对象：`docs/specs/yesterday-changes-deep-audit/` 与 `docs/specs/p0-bugfix-round1/` 两个 OpenSpec
> 审查依据：用户导出的 364KB 历史任务文档（`temp/tmp/审查昨日改动与功能.md`）中用户在提问里给出的反馈/回复
> 审查目的：找出"用户明确要求改但压根没改"、"openspec 设计与用户设想不一样"导致"最新包功能与设想千差万里"的根因
> 生成时间：2026-07-09 Phase 3 Part B B0

---

## 一、用户提问反馈提取（F1-F10）

从历史文档中提取用户在提问中明确给出的反馈/回复（非 AI 臆测）：

| 编号 | 用户反馈要点 | 来源上下文 |
|------|-------------|-----------|
| F1 | 书源/订阅源管理界面要深度重构，对齐书架两维度独立架构（分组样式 + 视图模式解耦） | 昨日改动审查主线 |
| F2 | 搜索框反模式必须修复：筛选类型/分组不得回填 type:/group: 到搜索框 | 昨日改动审查主线 |
| F3 | 默认主题改为暗夜紫夜间主题 | 昨日改动审查主线 |
| F4 | 工具栏精简：所有功能图标收进右上角三点菜单 | 昨日改动审查主线 |
| F5 | 文件夹视图优化：新增配置对话框（分组样式/视图/间距），卡片改书架风格 | 昨日改动审查主线 |
| F6 | "按类型"文件夹归类必须生效 | 昨日改动审查主线 |
| F7 | 欢迎页自定义：替换欢迎页开关 + 自动裁剪 | 昨日改动审查主线 |
| F8 | **首页布局架构（style1/style2）是用户核心诉求** — 书架要支持 Tab+ViewPager（style1）与单RV混排（style2）两种风格 | 昨日改动审查主线（核心） |
| F9 | Cron 输入简化为三选一选择器 | 昨日改动审查主线 |
| F10 | 视频倍速面板优化 + 默认静音 + 高倍速 + 边下边播开关 | 昨日改动审查主线 |

## 二、上下文压缩后丢失的反馈（L1-L4）

| 编号 | 丢失的反馈内容 | 丢失时机 | 影响 |
|------|---------------|---------|------|
| L1 | 用户在 AskUserQuestion 中选择"需调整"并给出的具体修订意见 | 上下文压缩 | AI 续接后无视修订意见，按旧方案继续 |
| L2 | 用户明确要求"深度分析主线任务完成质量" | 第一次压缩后 | AI 只做了反馈保全，未审查主线 |
| L3 | 用户明确要求"对照历史文档找出明确要改但没改的地方" | 第二次压缩后 | AI 未从历史文档提取用户反馈 |
| L4 | 用户明确要求"对照两个 openspec 找设计偏差" | 第二次压缩后 | AI 未做 openspec 偏差审查 |

## 三、OpenSpec 缺失项（G1-G7）

用户明确要求但 openspec 未记录的项目：

| 编号 | 缺失内容 | 应归属 spec | 实际状态 |
|------|---------|------------|---------|
| G1 | 订阅源管理移除文件夹视图（回归列表/紧凑/网格三视图） | p0-bugfix-round1 | ⚠️ **代码已实施**（updateLog 第 12 行有记录），但 spec 未记录 |
| G2 | 优化书源文件夹卡片样式（对齐书架 grid，移除 CardView，渐变遮罩） | p0-bugfix-round1 | ⚠️ **代码已实施**（updateLog 第 13 行有记录），但 spec 未记录 |
| G3 | 首页 style1/style2 布局架构（Tab+ViewPager / 单RV混排） | 应新建独立 spec | ❌ 被 p0-bugfix-round1 列为 Out of Scope，未归属任何 spec |
| G4 | 双维度下拉菜单（归类维度 + 样式维度，4 种组合） | 应新建独立 spec | ❌ 未归属任何 spec |
| G5 | 用户反馈持久化机制（上下文压缩后不丢反馈） | context-compression-feedback-preservation | ✅ 本 spec Part A 已实施 |
| G6 | OpenSpec 生成前必须对照用户提问反馈清单 | context-compression-feedback-preservation | ✅ 本 spec Part B B0 正在执行 |
| G7 | 主线任务完成质量三层审查（B0+B1+B2） | context-compression-feedback-preservation | ✅ 本 spec Part B 正在执行 |

## 四、OpenSpec 设计偏差（D1-D5）

| 编号 | 偏差描述 | 严重度 | 涉及 spec | 根因 |
|------|---------|--------|----------|------|
| **D1** | **F-08 首页 style1/style2 从用户核心诉求被降级为 p0-bugfix-round1 的 Out of Scope** | 🔴 致命 | p0-bugfix-round1/spec.md line 18-23 | openspec 生成时未对照用户提问反馈清单，把用户最核心的诉求误判为"P2 架构重构"排除 |
| D2 | yesterday-changes-deep-audit R5 正确捕获了 F-08 诉求（line 102），但 R5 的结论未传导到 p0-bugfix-round1 的 Scope | 🟠 高 | 两 spec 之间 | 两个 openspec 缺乏联动机制，R5 审查结论未反向修正 p0-bugfix-round1 |
| D3 | G1/G2 代码已实施但 p0-bugfix-round1 spec 未记录 | 🟡 中 | p0-bugfix-round1 | spec 编写时未同步代码实际改动，导致 spec 与代码脱节 |
| D4 | L1-L4 丢失的反馈未在任何 openspec 中体现 | 🟠 高 | 全局 | 上下文压缩后 AI 无视用户反馈，按旧方案继续，反馈未持久化 |
| D5 | D1 导致"最新包功能与设想千差万里" — 用户最想要的首页 style1/style2 完全没做 | 🔴 致命 | p0-bugfix-round1 | D1 的直接后果，用户感知最强 |

## 五、铁证：F-08 降级偏差（D1）

### R5 正确捕获（yesterday-changes-deep-audit/spec.md line 102）

```
### R5: 首页布局架构审查（核心，用户检查点1二次反馈要求）
```

R5 明确标注"核心"，且注明"用户检查点1二次反馈要求"，说明 AI 在审查阶段**正确识别**了 F-08 是用户核心诉求。

### Out of Scope 明确排除（p0-bugfix-round1/spec.md line 18-23）

```
### Out of Scope
- F-08 首页 style1/style2 设计（P2 架构重构）
```

p0-bugfix-round1 在 Scope 定义时，将 F-08 明确列为 Out of Scope，归类为"P2 架构重构"。

### 偏差成立

R5（审查 spec）正确捕获 → p0-bugfix-round1（实施 spec）明确排除 → **F-08 完全没做** → 用户看到最新包发现"千差万里"。

这正是用户控诉的"生成的两个 openspec，导致我现在看到你打的最新包里面整改的功能完全跟我设想的不一样的"的**根因**。

## 六、处理建议

| 偏差/缺失 | 处理建议 | 归属 |
|-----------|---------|------|
| D1/D5 F-08 首页 style1/style2 | 明确归属：不在本 spec 实施，应新建独立 spec `home-layout-style1-style2`，本 spec 只明确归属 | Part C C1 |
| D2 R5 结论未传导 | 新增规范：openspec 审查 spec 的结论必须反向修正实施 spec 的 Scope | Part C C1 |
| D3 G1/G2 代码已实施但 spec 未记录 | 补录到 p0-bugfix-round1 spec 的已完成项（代码已实施，只需补文档） | Part C C1 |
| D4 L1-L4 反馈丢失 | 已由本 spec Part A 反馈持久化机制解决 | Part A ✅ |
| G3/G4 首页布局/双维度菜单 | 归属新 spec `home-layout-style1-style2`（本 spec 只明确归属，不实施） | Part C C1 |

## 七、B0 审查结论

| 维度 | 结论 |
|------|------|
| 用户提问反馈提取 | ✅ 10 项（F1-F10）已全部提取 |
| 丢失反馈识别 | ✅ 4 项（L1-L4）已识别 |
| OpenSpec 缺失项 | ✅ 7 项（G1-G7）已识别，其中 G5/G6/G7 由本 spec 解决 |
| OpenSpec 设计偏差 | ✅ 5 项（D1-D5）已识别，D1/D5 为致命级 |
| 致命偏差根因 | ✅ D1：F-08 从核心诉求被降级为 Out of Scope |
| 处理建议 | ✅ 已给出每项的归属与处理方式 |

**B0 审查完成，进入 B1 代码实施审查 + B2 交付质量审查（见 audit-report.md）。**
