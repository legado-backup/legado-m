# tasks.md — 图片画廊线程修复

> 状态：🔄 设计中
>
> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)

## 任务清单

### 阶段 1 — 准备工作

- [ ] 1.1 读取 `ImageCanvasAdapter.kt` 全文，确认 L559-598 的 `loadImage` 方法当前实现与 design.md 描述一致
- [ ] 1.2 确认 `ImageViewHolder` 的 `currentUrl` 字段定义位置（`bind` 方法 L441-492 内赋值），确认字段可见性（var / val）
- [ ] 1.3 确认 `AppLog` 工具类的 `put(tag, msg)` 方法签名（参考 `docs/project-rules/logging_rules.md`）
- [ ] 1.4 确认 `itemView.post` 在项目其他 Adapter 中的现有用法（保持风格一致）
- [ ] 1.5 确认测试包 `io.legado.miss.app.debug` 已安装在真机/模拟器

### 阶段 2 — 核心修复

- [ ] 2.1 修改 `onResourceReady` 回调（L569-580）：用 `itemView.post { ... }` 包裹 `onImageFileReady` 调用
- [ ] 2.2 在 `onResourceReady` 的 `post` 块入口添加 `if (currentUrl != url) return@post` 守卫
- [ ] 2.3 修改 `onLoadFailed` 回调（L582-596）：用 `itemView.post { ... }` 包裹 `layoutParams` 修改和 `triggerFallbackChain` 调用
- [ ] 2.4 在 `onLoadFailed` 的 `post` 块入口添加 `if (currentUrl != url) return@post` 守卫
- [ ] 2.5 确认 `onResourceReady` 返回值为 `true`（消费事件，见 design.md AD-03）
- [ ] 2.6 确认 `onLoadFailed` 返回值为 `true`（消费事件）
- [ ] 2.7 用 GetDiagnostics 工具检查 `ImageCanvasAdapter.kt` 无编译错误

### 阶段 3 — 日志增强（AOAdapt）

- [ ] 3.1 在 `onResourceReady` 入口添加 AOAdapt 日志：记录线程名、切换意图、url
- [ ] 3.2 在 `onResourceReady` 的 `post` 块守卫生效分支添加 AOAdapt 日志：记录守卫生效、跳过渲染
- [ ] 3.3 在 `onLoadFailed` 入口添加 AOAdapt 日志：记录线程名、切换意图、url
- [ ] 3.4 在 `onLoadFailed` 的 `post` 块守卫生效分支添加 AOAdapt 日志：记录守卫生效、跳过降级
- [ ] 3.5 确认所有 AOAdapt 日志使用 `AppLog.put("AOAdapt", msg)` 格式（不使用 `android.util.Log.d`）
- [ ] 3.6 用 Grep 确认无 `android.util.Log.d` / `android.util.Log.e` 残留（参考 `logging-during-refactoring.md`）

### 阶段 4 — 编译与真机验证

- [ ] 4.1 编译测试包 `io.legado.miss.app.debug`（命令参考 `docs/project-flow/quick-reference.md`）
- [ ] 4.2 安装到真机/模拟器
- [ ] 4.3 真机验证 Scenario 1（正常加载）：进入图片画廊，图片正常显示
- [ ] 4.4 真机验证 Scenario 2（ViewHolder 复用）：快速滑动，无错位图片
- [ ] 4.5 真机验证 Scenario 3（加载失败降级链）：失败 URL 触发降级提示
- [ ] 4.6 真机验证 Scenario 4（长图分块加载）：长图正常显示
- [ ] 4.7 真机验证 Scenario 5（Activity 销毁时序）：快速返回不崩溃
- [ ] 4.8 logcat 过滤 `AOAdapt` 关键词，确认线程切换日志出现
- [ ] 4.9 logcat 过滤 `RuntimeException` / `CallbackException` / `Request threw uncaught throwable`，确认无残留
- [ ] 4.10 记录真机测试结果到 `issues-found.md`（参考 `real-device-test-reuse.md`）

### 阶段 5 — 文档同步与交付

- [ ] 5.1 更新 `assets/updateLog.md`：基于 git diff 分析提炼用户可感知的变化（参考 `version-delivery-sync.md`）
- [ ] 5.2 更新 `docs/INDEX.md`：添加本次修复的设计文档索引
- [ ] 5.3 更新 `.trae/memory/ai_memory_main.md`：记录任务完成状态、关键决策、经验教训
- [ ] 5.4 将本目录的 README.md / spec.md / design.md / tasks.md 状态从 🔄 设计中 改为 ✅ 已完成
- [ ] 5.5 用 AskUserQuestion 向用户确认验收（三选项：通过 / 需调整 / 拒绝）

## AOAdapt 日志模板

### onResourceReady 入口日志

```kotlin
AppLog.put(
    "AOAdapt",
    "onResourceReady thread=${Thread.currentThread().name} → post to main, url=$url"
)
```

**预期 logcat 输出**：
```
AOAdapt: onResourceReady thread=glide-disk-cache-thread-0 → post to main, url=https://...
```

### onResourceReady 守卫生效日志

```kotlin
AppLog.put(
    "AOAdapt",
    "post guarded: currentUrl changed, skip render"
)
```

**预期 logcat 输出**：
```
AOAdapt: post guarded: currentUrl changed, skip render
```

### onLoadFailed 入口日志

```kotlin
AppLog.put(
    "AOAdapt",
    "onLoadFailed thread=${Thread.currentThread().name} → post to main, url=$url"
)
```

**预期 logcat 输出**：
```
AOAdapt: onLoadFailed thread=glide-disk-cache-thread-0 → post to main, url=https://...
```

### onLoadFailed 守卫生效日志

```kotlin
AppLog.put(
    "AOAdapt",
    "post guarded: currentUrl changed, skip fallback"
)
```

**预期 logcat 输出**：
```
AOAdapt: post guarded: currentUrl changed, skip fallback
```

## 验证清单

完成所有任务后，逐项核对：

- [ ] V1 `ImageCanvasAdapter.kt` 的 `onResourceReady` 和 `onLoadFailed` 已用 `itemView.post` 切主线程
- [ ] V2 两个 `post` 块入口均有 `currentUrl != url` 守卫
- [ ] V3 `onResourceReady` 和 `onLoadFailed` 返回值均为 `true`
- [ ] V4 4 处 AOAdapt 日志已添加（onResourceReady 入口 + 守卫、onLoadFailed 入口 + 守卫）
- [ ] V5 无 `android.util.Log.d` / `android.util.Log.e` 残留
- [ ] V6 测试包 `io.legado.miss.app.debug` 编译安装成功
- [ ] V7 真机验证 5 个 Scenario 全部通过
- [ ] V8 logcat 中可见 AOAdapt 线程切换日志
- [ ] V9 logcat 中无 `RuntimeException` / `CallbackException` / `Request threw uncaught throwable`
- [ ] V10 `assets/updateLog.md` 已更新
- [ ] V11 `.trae/memory/ai_memory_main.md` 已更新
- [ ] V12 四文档状态已改为 ✅ 已完成
- [ ] V13 已用 AskUserQuestion 向用户确认验收

## 反模式（禁止行为）

- ❌ 跳过真机测试，仅改代码即声称完成
- ❌ 使用正式包 `io.legado.miss.app.release` 测试（违反真机测试包选择规范）
- ❌ 使用 `android.util.Log.d` 替代 `AppLog.put`
- ❌ 在 `onImageFileReady` / `loadIntoPhotoView` / `triggerFallbackChain` 内部逐个 UI 操作 `post`（破坏原子性，见 spec.md 方案C）
- ❌ 删除 `currentUrl != url` 入口守卫（仅保留 `post` 内守卫）
- ❌ 修改 `ImagePyramidLoader` / `SubsamplingScaleImageView` / Glide 版本
- ❌ 不更新 `updateLog.md` 直接交付
- ❌ 不用 AskUserQuestion 确认验收直接结束任务
