# UI 主题管理缺口审计与全量样式测试（ui-theme-gap-audit）

> 状态：🔄 设计中（2026-08-26）

## 功能概述

当前 App 前端处于**三态并存**：Archive 主题体系（ThemeManage/TopBarManage/外观套件/发现与订阅配置已部分搬入）+ 自研 Compose 化页面 + 残余 View/XML 头部与弹框。导致大量子页面、组件、弹框的样式**不被"主题设置 / 界面设置"的设置项管理到**——换主色只换部分页面、右上角三点菜单多风格、弹框多家族、搜索框圆角发散、订阅页经典/新版切换留结构性尾巴。

本任务分两阶段（本轮只做阶段 1+2，不进入修复）：

| 阶段 | 内容 | 产出 |
|------|------|------|
| 阶段 1 | **静态代码审计**：全 App 前端 UI，识别"未被主题设置管理到的页面/组件"，按判据矩阵扫描 + 人工核验 | 问题清单 v0（含源码定位 + 修复建议 + 优先级） |
| 阶段 2 | **测试用例设计**：承接静态分析结论，按前端 UI 强制基线编写全量样式测试用例，对接 `ai_tests`（uiautomator2 自动化 + Qwen3VL-8B 多模态图片分析） | `ai_tests/cases/F-UI-THEME/` 用例集 + VL 判定协议 |
| 阶段 3（后续轮） | 真机/模拟器**一次测全量** → 问题清单 v1 → **一次修复** → 第二轮/第三轮复测（用户明确禁止"边测边修"） | 按本 spec 轮次协议执行 |

## 核心能力

- **全量页面覆盖**（用户强制）：以 AndroidManifest 为唯一事实源清点全部 Activity / Fragment / 弹框 / 底部弹层，生成页面覆盖矩阵（页面 × 样式维度），审计与测试逐格覆盖、交付附覆盖率核对表，禁止抽样
- **主题管理面基线**：7 类设置项（主色体系 / 顶栏 / 圆角 / 字号 / 搜索框 / 弹框族 / 底部弹层）→ 管理面映射文档
- **静态审计判据矩阵**：C1-C6（硬编码颜色 / 硬编码圆角 / 硬编码字号 / View 直写色值 / 误用 MaterialTheme 代 ThemeSpec/PreferKey / 不订阅主题事件），Grep 模式集 + 脚本聚合
- **处置前后预期效果覆盖**：A1-A8 处置（改主色/背景/顶栏/圆角/字号/日夜/经典·新版/E-Ink）每项含 before 基线 → 处置 → after 生效 → 对账"预期应变 vs 实际变"，直接暴露"改了不生效"类问题
- **全量测试用例集**：按页面覆盖矩阵逐页建用例（S1-S6 页面骨架 × 组件六族 × 主题联动 × 经典/新版切换 × 夜间/墨水屏 × 空态），对接 `ai_tests`（uiautomator2 + Qwen3VL-8B 多模态图片分析）
- **多模态判定协议**：`LlmClient.chat_json` 结构化输出 + 三图采样（全图/局部/处置前后对照）+ 采样校准
- **问题清单以定位+解决为核心**：每条含源码定位（文件+行锚点）+ 可执行修复方案（改动文件+要点）+ P0/P1/P2 分级
- **轮次协议**：R1 全量测试 → 清单 v1 → 一次修复 → R2 复测(fail=0) → R3 终测验收，禁止边测边修

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach 含 Alternatives + Drawbacks / Requirements / Scenarios）
- [design.md](./design.md) — 技术设计（审计判据 / VL 协议 / ADR Y-Statement / 轮次协议 / 文件变更）
- [tasks.md](./tasks.md) — 任务清单（`- [ ] X.Y` 格式）
- [features-inventory.md](./features-inventory.md) — **功能清单 v1**（F1-F31 功能域 + M1-M7 消费对账 + **P1-P14 流程级流转链 + S-P1~P5 场景组合**，设计阶段产出）
- [pages-inventory.md](./pages-inventory.md) — **页面清单 v2 分层清点模型**（L0 功能域 31 / L1 Activity 98 / L2 Fragment 25 / L3 Compose Screen·Route 61 / L4 弹框·弹层 130+ / L5 布局 XML 208 / L6 设置项~68；页面单位合计 184 + 交互呈现全量，用 Glob 脚本可复现）

## 状态标记

- [x] 需求分析（现状三态并存 + 用户痛点确认）
- [x] 四文档生成 + **三维清单（功能 F1-F31 / 页面 L1-L6 / 流程 P1-P14+场景 S-P1~P5，用户强制设计阶段先有清单）**
- [x] 设计审查（🛑 检查点 1）✅ 2026-08-26 09:15 用户确认"通过，开始审计"
- [x] README 状态 → ✅ 设计完成
- [x] 阶段 1 静态审计 → **问题清单 v0**（11 条：P0×3/P1×6/P2×2，含源码定位+修复方案）✅ 检查点 2 用户确认"通过，继续阶段2"
- [x] 阶段 2 测试用例设计 → **F-UI-THEME 用例集 v2**（55 条结构 TC 覆盖 001-134 编号空间）+ **VL 协议**（ui_visual_prompt.py + ui_visual_verify.py）✅ **实测 CaseParser 解析 55/55 四段齐全**
- [x] 检查点 2b 用户审核用例集 + VL 协议（2026-08-26 通过）
- [x] 阶段 3（执行轮）：R1 全量测试（report_20260826_154627，52 条 + VL）→ 问题清单 v1（R1-01 CursorWindow 溢出修复，R1-04/05/06 复核关闭，R1-02 锚点校准）→ **一次修复 G1-G11**（issue-list v2 逐项登记）→ R2 全量复测（report_20260826_204811：52 条 fail=0 / warning=0 / VL 无新候选 / logcat 计数=0）→ R3 修复面专项（TC-071/041/081 步骤全过）+ case.md 锚点校准
- [x] 验收（✅ 2026-08-26 用户确认"通过（完成闭环）"）→ README 状态 → ✅ 全闭环
- [x] R3 收官复核（2026-08-27）：修复面专项 5 条单条报告（TC-071/041/081/090/007）人工复核全部回填 pass；G5 弹窗/ContentEdit/MoreConfig/AdvancedTitle 源码复核与 v2 声明一致 → issue-list v2 追加收官记录 ✅

## 轮次协议（阶段 3 执行预案）

```
R1 前置：
  ① 打包测试包（build-legado.bat debug 测试包 io.legado.miss.app.debug）
  ② 启动 MEmu → 安装 → 数据种子（附录 E：2 书源/2 订阅源/1 书/书架 1 本，import_book_source.py + import_rss_source.py）
  ③ 校验无构建进程占用（AGENTS 门禁）
R1 执行：
  ④ run_e2e.py --apk auto --tc F-UI-THEME（MD 轨道；[VL] 步骤统一截图；before/after 命名）
  ⑤ 无法触达页登记（发现源/真实视频源等情况）→ 触发覆盖求差集（附录 B）
R1 分析：
  ⑥ ui_visual_verify.py --evidence <report_dir> --v0 issue-list-v0.md
     → total / already_in_v0 / vl_new_candidates + calibration 校准样本
  ⑦ 人工/主代理 10% 校准（一致率 <85% 重跑）→ 合并为 问题清单 v1（P0/P1/P2 + 源码定位 + 方案）
  ⑧ 用户确认 v1 → 一次修复（阶段 3 修复轮）→ R2 全量复测 fail=0 → R3 终测 → 验收
```

## 关联基线（强制参考）

- `docs/project-rules/frontend-ui-standards.md` — archive 迁移后前端 UI 强制基线（设计 Token / S1-S6 骨架 / 组件六族）
- `docs/project-flow/ui-standards/` — 源核验文档（components / color / spacing / page-skeleton / dialog-shell / migration-registry）
- `ai_tests/`（run_e2e.py / LlmClient / config_ai.py）— 自动化 + 多模态地基
- `docs/specs/bugfix-ui-20260824/` — 已修复 11 项，本任务回归基点