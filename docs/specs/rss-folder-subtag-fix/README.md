# 订阅文件夹样式：点进文件夹头部误显标签/箭头

## 功能概述

订阅页布局设置为「文件夹样式」时，主页面（文件夹目录）头部正常、无标签。但**点进一个文件夹后**，头部会错误地多出「向下箭头」和「标签体系下的子标签」。

根本原因是 `renderRssSecondaryTags()` 在每次数据加载后**无条件**调用 `binding.topBar.showTags(true)`，覆盖了 `applyView()` 在文件夹模式下已执行的 `showTags(false)`，导致二级源标签栏与右侧向下箭头（filterToggleButton）被重新打开。

本次修复：让二级源标签栏**仅在标签样式（`isTagMode`）下展示**，文件夹样式点进文件夹后的列表视图不显示标签/箭头。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明（Intent / Scope / Approach / Requirements / Scenarios） |
| [design.md](./design.md) | 技术方案（Technical Approach / ADR / Data Flow / File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式 + AOAdapt 日志） |

## 状态标记

🔄 开发中