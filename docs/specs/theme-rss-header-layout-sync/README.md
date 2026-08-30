# theme-rss-header-layout-sync

> 主题设置与订阅/发现页头部布局联动修复

## 状态

✅ 已完成（2026-08-30：编译门禁 BUILD SUCCESSFUL ×2 + MEmu 真机 L2 五场景 PASS/0 FATAL + 本地 VL 兜底视觉判定通过；测试包 legado_miss_app_3.26.083012.apk；检查点 2/3 用户合并验收通过，任务闭环）

## 功能概述

### 背景

用户反馈：主题设置里面，发现与订阅（订阅页头部布局设置）存在联动问题——整体发现有很多问题，需要详细仔细地定位问题、完善修复，并通过真机测试。

经三轮静态穿透核实，问题集中在两条链路：

1. **主题设置 → 订阅页头部（View 侧 `MainTopBarView`）联动链路**：RSS 模式下源标签选中背景缺失、主题色/字体/顶栏包变更后仅靠 RECREATE 全量重建驱动刷新（无增量通道，且有真机非粘性事件丢失史，现存 800ms 双发兜底）。
2. **发现与订阅设置页（`DiscoverySubscriptionConfigFragment`）→ 发现页布局链路**：`discoveryPageMode`/`discoveryPageLayout` 变更后，发现页布局重算仅靠 onResume 兜底，非事件驱动；同时订阅布局设置（间距/视图/排序）入口分散在订阅页分组菜单弹框，与主题设置入口割裂。

### 目标

- 修复 RSS 模式源标签选中背景缺失，统一各样式行为
- 发现页布局变更改为事件驱动刷新，消除 onResume 兜底延迟
- 评估并加固订阅页头部刷新机制（增量通道优先，兜底可回退）
- 清理废弃配置 key，消除残留
- 收敛订阅布局设置入口，主题设置与订阅页头部布局联动一致
- 全部修复通过编译门禁 + 真机 L2 场景验证

## 核心能力 / 修复范围

| 编号 | 修复项 | 对应文件 |
|------|--------|----------|
| P1 | RSS 模式源标签(tagsBar)选中背景缺失：regular 样式下仅 DISCOVERY 模式显示选中背景，RSS 模式无选中高亮；default 样式全模式有，行为不一致。修复为 RSS 模式正确显示选中背景 | `MainTopBarView.kt:489`（对照 default 样式 L437） |
| P2 | 发现页零事件订阅：`discoveryPageMode`/`discoveryPageLayout` 变更后发现页布局重算仅靠 onResume 兜底，非事件驱动。修复为事件驱动刷新 | `ExploreFragment.kt:349-359 / 1718-1737 / 3542-3556` |
| P3 | 主题色/字体/顶栏包变更 → RECREATE 全量重建驱动订阅页头部刷新，无增量通道；真机存在非粘性事件丢失史（800ms 双发兜底）。评估并加固刷新机制 | `MainTopBarView.kt`（View 侧） |
| P4 | 废弃 key 残留：`rssViewMode`/`sourceViewMode`/`sourceFolderStyle`/`sourceFolderMargin` 已废弃未清理 | `PreferKey.kt:292-296` |
| P5 | 订阅布局设置（间距/视图/排序）入口分散：入口在订阅页分组菜单弹框（`SourceFolderConfigDialog`），主题设置→发现订阅设置页仅 4 个模式/布局 key，联动割裂。收敛入口并联动 | `DiscoverySubscriptionConfigFragment` + `SourceFolderConfigDialog` |

> P6（rss-classic-layout-align spec README 状态滞后）、P7（L2 验证债）、P8（真机复现用户实际感知问题）不属代码修复项，分别归入文档状态修正与验证计划（见下）。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：P1-P5 修复项的需求描述、验收标准、非目标边界 |
| [design.md](./design.md) | 技术设计：F1 RSS 标签选中高亮修复 / F2 发现页事件驱动刷新 / F3 头部刷新机制评估加固 / F4 废弃 key 清理 / F5 真机 L2 全场景验证的实现方案与风险 |
| [tasks.md](./tasks.md) | 实施任务清单：按 F1-F5 拆解的任务项与完成门禁 |

## 影响范围

主要模块：

| 模块 | 关联修复项 |
|------|-----------|
| `MainTopBarView.kt` | P1（选中背景）、P3（头部刷新机制） |
| `ExploreFragment.kt` | P2（发现页事件驱动刷新） |
| `RssFragment.kt` | P3（头部刷新链路上游）、P5（订阅布局入口联动） |
| `PreferKey.kt` | P4（废弃 key 清理） |
| `DiscoverySubscriptionConfigFragment` | P5（订阅布局设置入口收敛） |
| `SourceFolderConfigDialog` | P5（入口迁移联动） |

联动影响：主题设置页、订阅页头部 View、发现页布局重算逻辑；不改动书源解析、阅读核心（`ReadBook`）与数据库结构。

## 验证计划摘要

1. **编译门禁**：`build-legado.bat`（测试包）编译通过，Lint 无新增问题；updateLog 同步更新。
2. **真机 L2 场景清单**（测试包 `io.legado.miss.app.debug`）：
   - F1：RSS 模式下源标签选中背景高亮显示，切换源/分类选中态正确
   - F2：发现与订阅设置页修改页面模式/布局后返回发现页，布局即时重算（事件驱动，无需 onResume 兜底）
   - F3：主题色/字体/顶栏包变更后订阅页头部正确刷新；验证非粘性事件丢失场景（冷启动/快速切换）800ms 兜底可回退
   - F4：废弃 key 清理后旧配置无崩溃，功能不回退
   - F5：订阅布局设置（间距/视图/排序）新入口可用，与原弹框入口行为一致
   - 偿还验证债：`config-needs-restart-fix` / `topbar-search-entry-align` / `ui-style-unify-deep-fix` 相关 L2 场景
   - 复现并验证用户实际感知问题（P8 真机特定场景），全部通过后记录 `issues-found.md`
