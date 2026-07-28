# spec.md — 图片画廊线程修复

> 状态：🔄 设计中
>
> 关联文档：[README.md](./README.md) | [design.md](./design.md) | [tasks.md](./tasks.md)

## Intent

修复图片画廊（`ImageGalleryActivity`）进入后图片永远不显示的 Bug。

具体目标：
1. 消除 `RuntimeException: Can't create handler inside thread that has not called Looper.prepare()` 异常
2. 使 `onResourceReady` 回调链能完整执行到 UI 渲染
3. 保证加载失败时降级链（`triggerFallbackChain`）能正常启动
4. 保证 ViewHolder 复用场景下不渲染错位图片

## Scope

### In Scope

- `ImageCanvasAdapter.kt` 的 `loadImage` 方法（L559-598）的 `RequestListener<File>` 回调线程修复
- `onResourceReady`（L569-580）回调切主线程
- `onLoadFailed`（L582-596）回调切主线程
- ViewHolder 复用守卫（`currentUrl != url` 二次校验）
- 关键节点 AOAdapt 日志增强

### Out of Scope

- 图片 URL 嗅探逻辑（已确认正常）
- 图片下载逻辑（已确认 HTTP 200）
- `ImagePyramidLoader` 长图分块加载逻辑
- 其他 Adapter / Activity 的线程问题
- Glide 版本升级（jsoup/rhino/hutool 均锁定，Glide 同样保持现状）

## Approach

### Selected Approach

在 `loadImage` 的 `onResourceReady` 和 `onLoadFailed` 回调里用 `itemView.post { ... }` 切到主线程再执行 UI 操作。

#### 修复代码示意

```kotlin
override fun onResourceReady(
    resource: File, model: Any, target: Target<File>?,
    dataSource: DataSource, isFirstResource: Boolean
): Boolean {
    if (currentUrl != url) return false
    // 修复：downloadOnly 回调在 glide-disk-cache-thread，onImageFileReady 会调用
    // SSIV.recycle() 创建 GestureDetector 抛 Handler 异常，必须切到主线程
    itemView.post {
        if (currentUrl != url) return@post  // ViewHolder 复用守卫
        onImageFileReady(resource, url, position)
    }
    return true
}

override fun onLoadFailed(
    e: GlideException?, model: Any?, target: Target<File>?,
    isFirstResource: Boolean
): Boolean {
    if (currentUrl != url) return true
    itemView.post {
        if (currentUrl != url) return@post  // ViewHolder 复用守卫
        val errLp = itemView.layoutParams
        errLp.height = (itemView.resources.displayMetrics.heightPixels * 0.4).toInt()
        itemView.layoutParams = errLp
        triggerFallbackChain(e, position)
    }
    return true
}
```

### Alternatives Considered

| 方案 | 实现方式 | 否决理由 |
|------|---------|---------|
| **方案A**：用 `Handler(Looper.getMainLooper()).post` | 显式构造主线程 Handler 投递任务 | 与 `itemView.post` 等价但更冗长；`itemView.post` 内部就是向 ViewRoot 的 Handler 投递，且自带 View 附着检查语义更清晰；项目内已有 `itemView.post` 用法，保持一致性 |
| **方案B**：用 `Coroutine Dispatchers.Main` | `launch(Dispatchers.Main) { onImageFileReady(...) }` | 引入协程作用域管理成本（ViewHolder 内无现成 `scope`，需新建 `MainScope` 或依赖 `Activity.lifecycleScope`）；项目 Code Style 要求协程用自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装，与 `launch` 不符；`itemView.post` 更轻量、无依赖 |
| **方案C**：在 `onImageFileReady` 内部每个 UI 操作单独 `post` | 把 `itemView.layoutParams = errLp`、`triggerFallbackChain`、`Glide.load.into` 等逐个 `post` | 破坏回调链原子性，多个 `post` 之间可能被其他线程插入导致状态不一致；代码可读性极差；同样需要在 `onLoadFailed` 中处理；维护成本高 |

### Drawbacks

1. **post 异步延迟**：`itemView.post` 异步投递，回调执行延迟一帧（约 16ms）。对于图片画廊场景可接受（用户对单帧延迟无感知），且 `downloadOnly` 本身已是异步，多一帧不影响整体体验。
2. **ViewHolder 复用需加守卫**：`post` 投递后到执行期间，ViewHolder 可能被复用绑定新 URL，若不校验会渲染错位图片。已通过 `if (currentUrl != url) return@post` 守卫解决。
3. **回调返回时机变化**：`onResourceReady` 在 `post` 投递后立即返回 `true`，Glide 认为事件已消费，但实际渲染延迟到主线程。若主线程 `post` 执行前 Activity 销毁，可能产生空指针。需在 `post` 块内做 `binding` 非空校验（已由 Kotlin 合成引用 + Activity 生命周期兜底，必要时补充判空）。

## Requirements

修复完成后必须满足以下全部条件：

### R1 — 异常消除
- `logcat` 中不再出现 `RuntimeException: Can't create handler inside thread that has not called Looper.prepare()`
- `logcat` 中不再出现 `CallbackException: Unexpected exception thrown by non-Glide code`
- `logcat` 中不再出现 `GlideExecutor: Request threw uncaught throwable`（针对本回调路径）

### R2 — 图片正常显示
- 进入图片画廊后，图片在主线程渲染到 `SubsamplingScaleImageView` 或降级到 `PhotoView`
- 典型场景（24/26/28 张图片）全部可见
- 长图（`ImagePyramidLoader.bindLongImage`）正常分块加载

### R3 — 降级链正常
- 加载失败时 `triggerFallbackChain` 在主线程执行
- `binding.photoView.postDelayed` 正常工作
- `showFallbackHint` 正常显示降级提示

### R4 — ViewHolder 复用安全
- 快速滑动时 `post` 块内的 `currentUrl != url` 守卫生效
- 不出现错位图片（旧 URL 的图片渲染到新 URL 的 ViewHolder）
- 不出现重复渲染（同一 ViewHolder 被多次 `post` 渲染）

### R5 — 不引入回归
- 图片嗅探逻辑不受影响
- 图片下载逻辑不受影响
- `ImagePyramidLoader` 长图逻辑不受影响
- 其他 Adapter / Activity 行为不受影响

### R6 — 真机测试通过
- 使用测试包 `io.legado.miss.app.debug` 真机验证
- 至少覆盖下方 Scenarios 中的 3 个场景
- 日志中可见 AOAdapt 线程切换记录

## Scenarios

### Scenario 1 — 正常加载（Happy Path）

**前置条件**：
- 真机已安装测试包 `io.legado.miss.app.debug`
- 打开包含 24 张图片的图片画廊（来源为已验证可嗅探的页面）

**操作步骤**：
1. 进入图片画廊 `ImageGalleryActivity`
2. 等待 2-5 秒

**预期结果**：
- 第 1 张图片正常显示在 `SubsamplingScaleImageView`（长图）或 `PhotoView`（普通图）
- 左右滑动可查看后续图片
- `logcat` 中可见 AOAdapt 日志：`onResourceReady thread=glide-disk-cache-thread-0 → post to main`
- `logcat` 中**无** `RuntimeException` / `CallbackException` / `Request threw uncaught throwable`

### Scenario 2 — ViewHolder 复用（快速滑动）

**前置条件**：
- 同 Scenario 1

**操作步骤**：
1. 进入图片画廊
2. 快速左右滑动 5 次以上（触发 ViewHolder 复用）
3. 停止滑动，等待 3 秒

**预期结果**：
- 当前可见的图片正确显示（URL 与 ViewHolder 当前 `currentUrl` 一致）
- 不出现错位图片（旧 URL 图片渲染到新位置）
- `logcat` 中可见守卫生效日志：`post guarded: currentUrl changed, skip render`
- 无崩溃、无 ANR

### Scenario 3 — 加载失败降级链（Fallback）

**前置条件**：
- 准备一个会触发下载失败的图片 URL（如返回 404 或图片格式损坏）

**操作步骤**：
1. 进入包含该失败 URL 的图片画廊
2. 等待 Glide 重试结束触发 `onLoadFailed`

**预期结果**：
- `onLoadFailed` 在主线程执行（AOAdapt 日志可见）
- `triggerFallbackChain` 正常启动
- `showFallbackHint` 显示降级提示
- `binding.photoView.postDelayed` 正常工作（无 `RuntimeException`）
- 用户可见降级提示文案

### Scenario 4 — 长图分块加载（ImagePyramidLoader）

**前置条件**：
- 准备一张长图（高度 > 屏幕高度 3 倍）

**操作步骤**：
1. 进入包含该长图的图片画廊
2. 等待加载完成

**预期结果**：
- `ImagePyramidLoader.bindLongImage` 在主线程被调用
- 长图正常分块显示，可上下滑动
- 无 `Handler` 异常

### Scenario 5 — Activity 销毁时序（边界）

**前置条件**：
- 同 Scenario 1

**操作步骤**：
1. 进入图片画廊
2. 在图片下载完成但 `post` 未执行前，快速按返回键销毁 Activity

**预期结果**：
- 不崩溃（`post` 块内对 `binding` / `itemView` 判空或由 Activity 生命周期兜底）
- `logcat` 无 `NullPointerException`
- 无内存泄漏（`post` 任务被 View 移除或对已 detach 的 View 无副作用）
