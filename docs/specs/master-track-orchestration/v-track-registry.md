# V 轨挂靠登记（v-track-registry）

> 建立依据：master-track-orchestration AD-07（2026-08-31）。登记外部活跃任务与三轨总线的协调面。
> 铁律 R9：总线只做协调（占号/串行闸门/真机窗口/衔接建议单），**不接管** V 轨 spec 的任务归属与实施节奏；衔接建议单经并行会话确认前不排程。
> 快照机制：总线每波次收束时向并行会话拉取一次 V 轨进度快照，更新本文件"实况快照"节。

## 一、实质协调面（18 个）

| # | spec | 落点 | 协调动作 | 状态 |
|---|------|------|---------|------|
| 1 | video-sniff-403-and-rss-classic-fix | ~~W0~~ ✅ 已全闭环 | **Phase 0-4 全实施+L2 三轮用户实测全过（083118/083119/083121）+已提交推送（6ebfdd6e8 + 53bed6fd7）**；遗留后续批次：4.6 下载独立嗅探接线/4.7 结构感知/5.4 Exo variant 接入/S11 评分真机观测/6.8 模块文档映射表/6.9 正式基线报告 | ✅ 全闭环（2026-08-31） |
| 2 | bugfix-20260822 | W1 | 收尾或显式冻结（用户裁决） | 待处置 |
| 3 | bugfix-ui-20260824 | W1 | 收尾或显式冻结（用户裁决） | 待处置 |
| 4 | cronet-global-enable-20260731 | W1 | 与 video-sniff 4.8c 开关双逻辑合并裁决（tasks 2.11） | 待裁决 |
| 5 | network-perf-stability | W1 | 同上合并裁决 | 待裁决 |
| 6 | thread-pool-audit | W1→W2 首项 | 同上合并裁决 + 线程钳制定稿（3.6，防回退 Phase0 钳制） | 待定稿 |
| 7 | light-theme-contrast-fix | W1 | S1-S9 九场景并入 B0 真机合并窗口同包走查；MaterialValueHelper/ThemeSpec 改动面是 ng P5 前置基线（W5 前必须闭环） | 已实施待真机 |
| 8 | ai-test-system-refinement | W1 收束前 | scripts 批先行（W2 进入条件，tasks 2.12） | 待执行 |
| 9 | cache-entry-relocate | W2（B2 样板冻结前） | 收口（避免「我的」页迁移后再挪；先行→B4-c 瘦身 About） | 待执行 |
| 10 | fix-rss-search-scope | W2（3.5，B3 前置） | Rss 搜索域收口 | 待执行 |
| 11 | rss-folder-subtag-fix | W2（3.5，B3 前置） | 收口 | 待执行 |
| 12 | enhance-switch-governance-fix | W4 衔接建议单 | video-sniff Phase3 收口事件后按建议单顺序衔接（确认前不排程） | 待衔接 |
| 13 | video-back-fullscreen-fix | W4 衔接建议单 | 同上 | 待衔接 |
| 14 | rss-video-player-enhancement | W4 衔接建议单 | 同上 | 待衔接 |
| 15 | video-extractor-enhancement | W4 衔接建议单 | 同上（基于 SniffEngine） | 待衔接 |
| 16 | multiline-on-demand-extraction | W4 衔接建议单 | 同上（与 video-sniff Phase4 合并或紧随） | 待衔接 |
| 17 | download-hls-complete-fix | W4 衔接建议 | 排 video-sniff 4.6 headersJson 落地之后 | 待衔接 |
| 18 | download-manager-maturity | W4 衔接建议 | 同上 | 待衔接 |

## 二、顶栏集群（4 个，B1 盘点吸收/注销）

my-topbar-unify / subpage-topbar-unify / tag-mode-unify / topbar-icon-semantics-fix——B1 基线校准时盘点（tasks 2.7.3）；tag-mode 实施时点排 fix-rss-search-scope（3.5）之后（热点④）；subpage-topbar 与 compose B4 待迁页名单互斥（tasks 2.14，X2）。

## 三、低冲突（4 个，随窗插入）

rss-image-load-optimization / image-player-vertical-canvas-optimization / folder-cover-ratio-archive-align / image-thread-coordination-fix-20260731。

## 四、不占波次（7 个，登记）

forks-ecosystem-analysis / ui-redesign-m3（伞形容器）；global-spec-restructure / legado-skill-v2-rebuild（非代码轨）；ui-theme-gap-audit；player-mature-solutions-alignment（与 V 轨基准线对齐后裁决）；source-arch-mutual-borrow（与 C0 串行裁决，热点⑦）；reader-overlay-compose（热点①，实施不早于 W4）。

## 五、关键占号/真机项

- **DB 占号**：video-sniff 4.8e 已实占 v109（详见 db-version-registry.md）；ng P1 顺延 v110、P3 顺延 v111
- **真机待验项**：video-sniff 三轮 L2 已全过 ✅（083121 用户复测✅）；light-theme S1-S9 仍待用户实测（发布 3.26.083123 时裁决放行）→ 并入 B0 真机合并窗口（R8 同包覆盖）

## 六、实况快照

| 快照时间 | video-sniff | light-theme | 备注 |
|---------|-------------|-------------|------|
| 2026-08-31 W0 建立 | Phase 3 已落地 4.8e 方案 A（4.1-4.9 完成，083119 装机待用户 L2 验收），剩 4.10 复验+Phase 4 | 已实施 083116 交付，S1-S9 真机延后 | 快照源=并行会话记忆 |
| 2026-09-01 W0 更新 | **✅ 全闭环**（Phase 0-4+L2 三轮验收+已提交 6ebfdd6e8；遗留 4.6/4.7/5.4/S11/6.8/6.9 登记后续批次） | 修复已随 3.26.083123 正式发布；S1-S9 真机走查仍待用户实测 | 发布任务（e4cbd39d7）同步闭环；5.5 衔接建议单触发条件已满足（video-sniff 全闭环），W4 前出建议单 |
