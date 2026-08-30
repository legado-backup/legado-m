# read-menu-highlight-entry-restore — 阅读页三个点菜单补回漏挂动作项（7 项）

## 功能概述

阅读页右上角三个点弹层（Compose 自绘 `buildOverflowActions`）在 08-29 Compose 迁移（e706bae53）时从 XML 菜单逐项翻译动作列表，发生同批漏译。经 XML `book_read.xml` 全量逐项比对核实，漏挂共 6 项：**高亮规则管理、设置字符集（本地书）、TXT目录规则（本地TXT）、删除注音标签/删除H标签（EPUB）、核心调度模式（EPUB核心模式）**；穿透自审再实锤 1 项存量迁移 bug：**「段落规则」在普通 EPUB 书误显示**（isEpub 语义混淆）。本任务按 XML 原顺序与生效条件一并补回并修正，共 7 项。

## 核心能力

- 三个点弹层补回 6 个漏挂动作项，各自生效条件与勾选态与旧 XML 菜单完全一致
- 动作链路：`buildOverflowActions` +6 项 → `ReadMenuTitleBarActions` +6 回调 → `ReadMenu.Callback` +6 方法 → `ReadBookActivity` 复用既有处理逻辑

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR Y-Statement/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 状态

✅ 已完成（2026-08-30 检查点 2 审核通过；L2 四场景 ALL PASS，测试包 legado_miss_app_3.26.083019.apk 已装机）
