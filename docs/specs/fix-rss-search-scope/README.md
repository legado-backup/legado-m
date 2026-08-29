# 订阅搜索范围上下文修复（fix-rss-search-scope）

## 状态

✅ 设计完成（2026-08-28，检查点1 二轮通过）→ 🔄 开发中

## 功能概述

订阅页（RssFragment 经典形态）头部提供搜索按钮。用户进入某个分组/标签，或切换到某类内容形态（网页/图片/视频）后点击搜索，期望只查找当前上下文内的订阅源文章资源；但当前实现将搜索范围参数硬编码为空（全局搜索），导致结果跳出当前浏览上下文，与"在当前分组/类型内找资源"的使用预期不符。

目标行为：经典形态搜索按钮根据订阅页当前状态（`currentGroup` / `currentType`）动态计算搜索范围并传入搜索页。处于根目录（全部）时维持原有全局搜索不变；进入"未分组"节点时仅搜索未分配分组的订阅源；进入某分组时仅搜索该分组内订阅源；切换到某类型时仅搜索该类型订阅源。搜索页内部的范围切换能力保持可用，且范围选择不持久化。

方案一句话：扩展 `RssSearchScope` 的 token 语法（`@type:0/1/2` 表内容类型、`@no_group` 表未分组），`getRssSources` 解析 token 后走对应 DAO 查询，`display`/`displayNames` 映射友好文案；`RssFragment` 经典形态按钮按 `currentGroup`/`currentType` 计算 scope 传入，全部状态传 null 保持现状。

## 核心能力

- **分组内搜索**：进入某分组/标签后搜索，结果限定该分组内的订阅源（hasGroup 精确判定：多分组 sourceGroup="A,B" 正确命中、"AB" 不误命中）
- **类型内搜索**：切换为网页/图片/视频类型后搜索，结果限定该类型内的订阅源
- **未分组搜索**：进入"未分组"节点后搜索，结果限定未分配分组的订阅源
- **根目录全局保持**：处于根目录（全部）时搜索仍为全局，行为与现状完全一致
- **搜索页范围可切换保持**：搜索页内范围切换能力保留，且范围选择不持久化（save=false）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：背景、用户场景、改动点、验收标准 |
| [design.md](./design.md) | 技术设计：token 语法扩展、范围解析流程、数据流与改动清单 |
| [tasks.md](./tasks.md) | 实施任务清单：按阶段拆分的可执行步骤与验证方式 |

## 涉及模块

| 模块 | 位置 | 职责与改动 |
|------|------|-----------|
| RssFragment | `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | 订阅页容器；经典形态搜索按钮（约 L929-931）改为按 `currentGroup`/`currentType`（L241-244 状态字段）计算 scope 传入；现代形态入口（约 L897）保持不动 |
| RssSearchScope | `app/src/main/java/io/legado/app/model/rss/RssSearchScope.kt` | 搜索范围模型；扩展 token 语法（`@type:0/1/2`、`@no_group`），`getRssSources`（L87-116）解析 token 走对应 DAO 查询；`display`/`displayNames` 映射友好文案 |
| RssSourceDao | `app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt` | 数据访问层；noGroup 查询已存在可复用（未分组场景）；新增按类型查启用源查询（`type=:type and enabled=1`，类型场景）；`getByGroup` like 模糊匹配为既有全局行为不修 |

## 其他调用点说明（不改动）

- `RssFragment` 现代形态搜索入口（约 L897）：维持全局搜索
- 设置页搜索入口（`MySettingsData` 约 L283）：维持全局搜索
- `RssSearchActivity.start`（L492-497）已支持 `searchScope` 参数，`receiptIntent`（L352-356）保存范围为 save=false 不持久化，本次不修改其核心逻辑