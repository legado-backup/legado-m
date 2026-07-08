# 书源/订阅源布局设置重做

> 状态：🔄 设计中
>
> 关联文档：[spec.md](./spec.md) | [design.md](./design.md) | [tasks.md](./tasks.md)

## 功能概述

统一重做书源管理和订阅源管理的布局设置，学习书架的视图模式（列表/紧凑列表/网格多列）和排序功能，修复书源分组不生效和订阅源类型不生效的 Bug。

## 核心能力

1. **Bug 修复**：书源分组菜单两种视图下都不生效（根因：`groupMenuLifecycleOwner` 懒加载导致分组数据来不及填充菜单）
2. **Bug 修复**：订阅源类型筛选不生效（根因：DAO 无 type 查询方法、菜单无类型筛选 UI）
3. **视图模式扩展**：书源/订阅源从「列表/文件夹」两种扩展为「列表/紧凑列表/网格2列/网格3列/文件夹」五种
4. **订阅源排序**：新增排序功能（手动/名称/URL/更新时间/启用状态），对齐书源已有排序
5. **类型筛选**：书源/订阅源新增按类型筛选（网页/图片/视频/音频/文件）
6. **统一配置对话框**：参考书架 `DialogBookshelfConfigBinding`，统一布局+排序+间距配置入口

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 涉及模块

| 模块 | 文件 | 变更类型 |
|------|------|---------|
| 书源管理 | `BookSourceActivity.kt` | 修复分组 bug + 视图模式扩展 + 类型筛选 |
| 订阅源管理 | `RssSourceActivity.kt` | 视图模式扩展 + 排序 + 类型筛选 |
| 书源 DAO | `BookSourceDao.kt` | 新增 type 查询方法 |
| 订阅源 DAO | `RssSourceDao.kt` | 新增 type 查询方法 |
| 配置 | `AppConfig.kt` | 新增 rssSort/sourceSort 配置项 |
| 布局 | `dialog_source_config.xml`（新建） | 统一配置对话框 |
| 菜单 | `book_source.xml` / `rss_source.xml` | 新增类型筛选菜单项 |
| 适配器 | `SourceFolderAdapter.kt` | 配置对话框重构 |
