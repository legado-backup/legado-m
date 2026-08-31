# compose-migration-status-audit — 前端 Compose 化进度全景审计与推进设计

> 状态：✅ 设计完成（5 轮交叉审核闭环，轮 5 终审 ACCEPT-WITH-NOTES）｜ 创建：2026-08-30 ｜ 方法：三路并行子代理扫描交叉验证 + 路线图/registry/红线原文逐条抽取 + 4 份实施级设计分册

## 功能概述

应用户要求，对**除阅读器核心正文页外**的全部前端页面做 Compose 化进度深度盘点，并按"设计先行、拒绝半成品"标准产出完全支撑实施的设计（页级 69 类总表 + B0-B5 批次计划，无阻塞点/待细化点）。

## 核心结论

| 结论 | 内容 |
|------|------|
| 总体判断 | **可以继续增进**。基建全可用；结构口径已 Compose 33/60 总表行（55%）；剩余结构性迁移 14+轻量收尾 6（🔨20 行），另有 30 项"已迁移未登记/缺回执" |
| 文档滞后实锤 | pages-inventory 总览 10.7% 过期（真实 55% 行口径）；C6/C9/C10/C11/C12/C15/C16/F3/E1/E3/E4/E6/B7/B9/B16/C17/E5 等源码已 Compose/桥接但文档标 View；S1-S6 样板大多已接线只缺验收回执 |
| 权威口径 | migration-registry 为唯一权威（AD-01）；本 spec 页级总表为校准裁决 |
| 主要风险 | 强跳过陷阱（已沉淀红线 5，AD-08 门禁）/miuix 与 M3 双体系（AD-04 治理）/Compose 测试盲区（AD-08 ②L2 脚本）/glide-compose beta08（AD-08 ④观察项） |
| 批次路线 | B0 deep-fix 收口 → B1 基线校准 → B2 样板冻结验收 → B3 P2 残余（D4 Rss 列表旗舰）→ B4 P3 长尾 → B5 收官（AD-07） |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach（含 Alternatives+Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | AD-01~08 定稿 + 页级 69 类总表（已回写分册勘误）+ 批次执行流 |
| [tasks.md](./tasks.md) | B0-B5 全量任务清单（页面级+验收标准）+ AOAdapt 日志 |
| [design-b1-b2-baseline-freeze.md](./design-b1-b2-baseline-freeze.md) | 分册①：B1 校准四产物成品+B2 样板 35 检查点+AppPageSpacing+L2 脚本模板+GeneratedCover 裁决段 |
| [design-b3-d4-flagship.md](./design-b3-d4-flagship.md) | 分册②：D4 旗舰函数级设计（五代 Adapter 收敛/RssArticleListScreen/双模式分派/12 场景测试） |
| [design-b3-pages.md](./design-b3-pages.md) | 分册③：B3 其余 9 页实施级 mini-design+复用矩阵 |
| [design-b4-b5-pages.md](./design-b4-b5-pages.md) | 分册④：B4 十三节复用映射设计+B5 收官可执行清单（含源码实况勘误表） |

## 页面状态速查（详见 design.md 页级总表）

1. **🧱 永久原生/N（9 组）**：阅读器正文、漫画内核、WebView 播放内核、CodeEdit(sora)、QrCode、透明窗系、WebViewLogin、ReadRss、BaseBookshelfFragment 菜单红线
2. **🔁/✅回 已迁待登记/补回执（30 项）**：registry 登记块 24 项（B1 批次粘贴）+D1/C19 收尾确认+B4-a 登记 6 项（B7/B16/C17/E5/D8/B13）
3. **🔨 待迁移/收尾（20 行）**：结构性迁移 14（B3=D4 旗舰/A7/A8/B8/C3；B4=B5/B14/B15 列表三连/D2/D3/D5/D7/C20 About）+轻量收尾 6（B2/B11/E2/B9/B12 壳层/C13 瘦身）
4. **🗑 清理（1 项）**：A6 BooksFragment（B5 确认 0 引用后删）
