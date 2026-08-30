# 发现/订阅源文件夹封面替换

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> OpenSpec 功能概述。状态：🔄 设计中。

## 功能概述

让「发现」页与「订阅源」主页的文件夹布局学到书架文件夹的精髓——**支持长按文件夹卡片自定义替换封面**（与书架 `GroupEditDialog` 交互一致），并提供「恢复默认封面」选项。同时将书源管理页与订阅源管理页改为**固定平铺列表**（去掉文件夹视图），简化管理体验。

## 核心能力

1. **文件夹封面自定义**：发现页（书源分组）与订阅源页（RSS 分组）的文件夹卡片支持长按弹菜单「选图」「恢复默认封面」
2. **双命名空间隔离**：书源分组与 RSS 分组互不干扰，同名分组可各自独立封面
3. **特殊分组同样支持**：全部分组/未分组/各类型 folder 均可换封面（固定英文 key 存表，与本地化文本解耦）
4. **封面持久化**：Room 新表 `source_group_covers`（复合主键 kind+groupName），选图复制到 `externalFiles/covers/`（MD5 命名），DB v103→v104 手动迁移
5. **管理页固定平铺**：书源管理页、订阅源管理页去掉文件夹视图，改为简单平铺全部源；配置对话框隐藏「分组样式」选项

## 文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [README.md](./README.md) | 功能概述与文档索引（本文件） | 🔄 设计中 |
| [spec.md](./spec.md) | Intent/Scope/Approach（含 Alternatives + Drawbacks）/Requirements/Scenarios | 🔄 设计中 |
| [design.md](./design.md) | Technical Approach/ADR Y-Statement/Data Flow/File Changes | 🔄 设计中 |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y`）+ AOAdapt 日志 | 🔄 设计中 |

## 状态

🔄 设计中 → 待强制检查点 1（用户审查设计方案）