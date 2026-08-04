# 图片画廊线程修复（image-canvas-thread-fix-20260728）

> 状态：✅ 已实施（Glide 回调切主线程 + currentUrl 守卫源码实证，勾选已同步）
>
> 创建日期：2026-07-28
>
> 类型：Bug 修复（OpenSpec 任务）

## 功能概述

修复图片画廊（`ImageGalleryActivity`）进入后图片永远不显示的 Bug。

### 问题表现

- 图片 URL 嗅探成功（典型场景 24/26/28 张）
- 图片 HTTP 200 下载成功（Glide `downloadOnly().submit()` 正常返回 `File`）
- UI 上图片永远不显示，降级链也未启动

### 根因（logcat 铁证确认）

`ImageCanvasAdapter.loadImage` 方法使用 `Glide.downloadOnly().load(url).submit()` 下载图片到磁盘缓存，其 `RequestListener<File>.onResourceReady` 回调在 **glide-disk-cache-thread** 线程执行（非主线程）。

回调链 `onResourceReady → onImageFileReady → loadIntoPhotoView → binding.ssivView.recycle()` 中，`SubsamplingScaleImageView.recycle()` 内部会 `reset() → setGestureDetector() → new GestureDetector() → new Handler()`，由于当前线程没有调用 `Looper.prepare()`，抛出 `RuntimeException: Can't create handler inside thread that has not called Looper.prepare()`。

该异常被 Glide 包装为 `CallbackException`，**不触发 `onLoadFailed`**，被 `GlideExecutor` 以 "Request threw uncaught throwable" 吞掉，导致 `onImageFileReady` 中断、图片未渲染、降级链未启动。

## 核心能力

| 能力 | 说明 |
|------|------|
| 线程切换修复 | 在 `onResourceReady` / `onLoadFailed` 回调中用 `itemView.post { ... }` 切到主线程 |
| ViewHolder 复用守卫 | `post` 块内再次校验 `currentUrl != url`，防止复用后渲染错位 |
| 事件消费约定 | `onResourceReady` 返回 `true` 消费事件，防止 Glide 二次处理 |
| 日志增强 | 关键节点添加 AOAdapt 日志，便于真机验证线程切换生效 |

## 文档索引

| 文档 | 用途 |
|------|------|
| [README.md](./README.md) | 功能概述、核心能力、文档索引、状态标记（本文件） |
| [spec.md](./spec.md) | 意图、范围、方案选型（含替代方案与权衡）、需求、测试场景 |
| [design.md](./design.md) | 技术方案、架构决策（ADR Y-Statement）、数据流、文件变更清单 |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式）、AOAdapt 日志模板 |

## 关联信息

- **受影响文件**：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`
- **测试包**：`io.legado.miss.app.debug`（代码优化任务必须用测试包）
- **铁证来源**：2026-07-28 00:17:41.198 logcat（2800 包，异常栈见 spec.md / design.md）
- **规范引用**：
  - `AGENTS.md` § 强制规则：AI 自动端到端测试
  - `AGENTS.md` § 强制规则：真机测试包选择规范
  - `docs/project-rules/ai_e2e_testing_workflow.md`
