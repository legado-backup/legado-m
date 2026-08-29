# 配置修改需重启生效 + 视效对齐 archive（config-needs-restart-fix）

> 状态：✅ 已完成（2026-08-29 实施完成，编译门禁通过；真机 L2 延后归 R2）

## 功能概述

用户反馈两类同根因 bug，合并为一套统一设计处理：

**Bug A（订阅顶栏残留）**：在订阅设置中从「新版(modern)」切「经典(classic)」，返回订阅 Tab 后顶栏 primaryBar/tagsBar 仍残留新版分类标签，重启才生效。

**Bug B（书架布局配置失效）**：书架布局设置大量不生效（布局/分组/书名/列表样式/边距），需重启才生效，且页面样式不如 archive（参考 fork）。

**统一根因（穿透审查后三处源码级实锤）**：
1. **订阅**：classic 路径不取消 modern 的 `rssFlowJob` collector（文件夹视图路径完全不取消），返回 RESUMED 时 `flowWithLifecycleAndDatabaseChange` 重发 → modern 源标签重新覆盖经典顶栏
2. **style2**：[BookshelfFragment2](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BookshelfFragment2.kt) **零事件监听**（BOOKSHELF_REFRESH 仅 style1 接），配置变更完全无响应
3. **书架渲染**：[BookshelfScreen.kt:88-92](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfScreen.kt#L88-L92) 5 项 `remember{AppConfig.x}` 快照 + margin/listItemStyle/introLines 三配置未消费 + OURS 事件分类过宽（数据类开关错标 structure）

**Archive 对照**：archive 采用「事件总线双轨」——`BOOKSHELF_REFRESH`（刷数据）+ `BOOKSHELF_STRUCTURE_CHANGED`（`rebuildBookshelfContent()` 重建），双侧 Fragment 均监听；事件分类精确（layout/showBookname→结构，其余→刷新）。OURS 缺结构重建事件与机制，且分类过宽。

## 核心能力

- **诊断实证锁根**：统一 tag（`RssModeSwitch`/`BookshelfConfig`）插桩，真机复现定位断链点，验证后清除
- **订阅顶栏三态复位**：modern↔classic 切换强制清空顶栏标签 + 复位可见性请求位 + 覆盖监听，杜绝残留
- **书架渲染快照响应式化**：`BookshelfScreen.kt:88-92` 5 项 `remember{AppConfig.x}` 改为受控入参（Fragment 事件回调重读传入），`:214` 直读改受控；补齐 margin/listItemStyle/introLines 三配置消费
- **结构重建事件跨模块**：新增 `BOOKSHELF_STRUCTURE_CHANGED`（dialect archive），`applyBookshelfConfig` 分类发事件，style1/2 双侧 Fragment `rebuildBookshelfContent()`
- **视效对齐 archive**：先产出 OURS vs archive 差异清单交用户确认边界，再收敛间距/卡片样式/封面比例/边距
- **预防机制**：经验沉淀 ui-standards/how-to.md（「Compose 非响应式配置读取 + 缺结构重建 = 需重启」禁令）
- **真机 L2 验证**：逐项配置即时生效，双向切换无残留

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach 含 Alternatives + Drawbacks / Requirements / Scenarios）
- [design.md](./design.md) — 技术设计（统一根因模型/订阅复位/书架响应式/结构重建事件/ADR）
- [tasks.md](./tasks.md) — 任务清单（`- [ ] X.Y` + AOAdapt 日志）

## 状态标记

- [x] 需求分析（订阅顶栏 + 书架同根因定位 + 全库同类排查 + archive 对照）
- [x] **设计阶段穿透审查**（三实锤源码级核实 + 事件分类权威表 + 卡点表 K1-K9）
- [x] 视效差异清单产出（design.md 附录 A，8 维度）+ 新发现 K7 书名语义错位 / K8 封面正方形 bug + K3 核实回退
- [x] 四文档生成（穿透审查修订版，含附录 A 差异清单 + 附录 B 代码级设计）
- [ ] 检查点 1（二次审核）：用户审查（含 K7 存量值裁决 + A3 视效边界裁决）
- [ ] 修复（订阅 collector 泄漏 + 事件重排 + style2 双监听 + 参数化 + 三配置接入 + K7/K8 + 视效对齐）
- [ ] 编译门禁
- [ ] 真机 L2 验证
- [ ] 用户验收 + 文档同步

> 注：本 spec 由原 `rss-mode-switch-topbar-stale` + `bookshelf-layout-config-fix` 两独立 spec 按用户决策（2026-08-28）合并而来；原两目录已删除，内容整合至此。