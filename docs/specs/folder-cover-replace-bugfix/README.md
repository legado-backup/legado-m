# 文件夹封面替换回归修复（书架 / 订阅）

> 状态：✅ 设计完成

## 功能概述

修复本 fork「书架 / 订阅源文件夹」自定义封面替换功能失效的回归问题。

用户在书架与订阅源的文件夹样式下长按分组 ->「选择图片」替换自定义封面，期望封面立即更新；当前实际表现为**替换后封面不生效**（仍显示默认文件夹图标）。

## 根因（已定位）

**订阅 / 书源文件夹**（`SourceFolderComposeGrid`）在迁移到 Compose 渲染后，封面数据源为 `folderComposeCovers`（`mutableState` map）；但修改/恢复封面的两个入口**只更新了 View 版 `SourceFolderAdapter` 的让缓存，未更新 Compose state**，导致 Compose 不重组、封面不刷新。

- [RssFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt) L209-214（替换）仅调 `folderAdapter.updateCover`
- [RssFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt) L1287-1298（恢复默认）同样仅调 `folderAdapter.updateCover`

**书架文件夹**：`GroupCover` 用 `BookGroup.cover` + DB flow 驱动重组，链路相对完整，需真机确认是否受同一迁移影响（本任务一并验证）。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 实施任务清单（`- [ ] X.Y`） |

## 状态标记

- [ ] 设计中
- [ ] 设计完成
- [ ] 开发中
- [ ] 已完成