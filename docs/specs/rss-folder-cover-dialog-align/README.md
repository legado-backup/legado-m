# README：rss-folder-cover-dialog-align（订阅文件夹封面弹框对齐书架）

## 功能概述

经典订阅模式文件夹视图中，长按文件夹触发的封面替换交互目前是"直调 HandleFileActivity 通用操作列表"的最简实现，无标准弹框容器、无封面预览、无恢复默认入口（Compose 版）、URL 语义与书架不一致。本任务新建 `RssFolderCoverDialog`（Compose 标准表单弹框），功能与样式对齐书架侧 `GroupEditDialog` 的封面编辑能力。

## 核心能力

1. 长按文件夹直接弹出封面编辑弹框（对齐书架"长按即弹框"交互）
2. 当前封面预览区（BookCoverImage 回显，对齐书架 90×120dp 预览）
3. 选择图片（复用 HandleFileContract；http/https 直存 URL，对齐书架语义；本地文件 MD5 复制到 covers/）
4. 恢复默认封面（置空预览，确定时删除 KIND_RSS 记录）
5. 确定/取消语义（取消不落库，对齐书架编辑态暂存模型）
6. 标准弹框样式（AppDialogFrame + AppDialogStyle + LegadoMiuixActionButton，随主题联动）

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 意图/范围/方案（含替代方案与缺点）/需求/场景 |
| [design.md](./design.md) | 技术方案/架构决策（ADR）/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 状态标记

- ✅ 设计完成（2026-08-29 检查点 1 通过）
- ✅ 实施完成（2026-08-29：编译门禁 + 测试包 082917 装机 L1 + L2 真机验证 ALL PASS，检查点 2 通过；S2 URL 直存/S3 恢复默认完整点击链路留用户自测）
