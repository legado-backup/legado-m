# 子页面头部统一：全 App TitleBar 子页迁移 MainTopBarView

## 功能概述

项目四大主页面（书架/订阅/发现/我的）头部已统一由 `MainTopBarView` 组件承载，并被顶栏设置 / 主题设置 / 样式管理全量管控。但大量**子页面**头部仍使用旧的 `TitleBar`（AppBarLayout + Toolbar），其 `topBarColorManaged` 默认 `false`（仅跟随主题 `primaryColor`），未接入圆角 / 壁纸 / 胶囊 / 字号 / 搜索入口等顶栏全套样式，观感与主页面不一致，且存在多套头部样式并存。

本次将**全 App 所有使用 `TitleBar` 的子页面头部统一迁移到 `MainTopBarView`**，消除多套样式，使子页面头部同样受主题 / 顶栏设置全量管理。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明（Intent / Scope / Approach / Requirements / Scenarios） |
| [design.md](./design.md) | 技术方案（Technical Approach / ADR / Data Flow / File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式 + AOAdapt 日志） |

## 状态标记

🔄 开发中