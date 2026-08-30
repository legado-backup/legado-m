# design.md — 图片画廊线程修复

> 状态：🔄 设计中
>
> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [tasks.md](./tasks.md)

## Technical Approach

### 问题根因（源码核实）

`ImageCanvasAdapter.kt` 的 `ImageViewHolder.loadImage` 方法（L559-598）使用 Glide 的 `downloadOnly().load(url).submit()` 模式下载图片到磁盘缓存，并通过 `RequestListener<File>` 监听下载结果。

**关键事实**：`downloadOnly` 模式下，`RequestListener.onResourceReady` 和 `onLoadFailed` 回调均在 **glide-disk-cache-thread** 线程执行（Glide 源码 `EngineJob.handleResultOnMainThread` 对 `downloadOnly` 走的是 `DiskCacheStrategy.DATA` 路径，回调线程为 GlideExecutor 的 disk-cache 线程池）。

回调链中调用了大量 UI 操作（见 spec.md Scope 分析），其中 `loadIntoPhotoView`（L703）调用 `binding.ssivView.recycle()`，`SubsamplingScaleImageView.recycle()`（SSIV.java:2037）→ `reset()`（L545）→ `setGestureDetector()`（L549）→ `new GestureDetector()` → `new Handler()`，由于当前线程未调用 `Looper.prepare()`，抛出 `RuntimeException: Can't create handler inside thread that has not called Looper.prepare()`。

该异常被 Glide 包装为 `CallbackException`，**不触发 `onLoadFailed`**（Glide 源码 `RequestFutureTarget` / `EngineJob` 对非 Glide 代码抛出的异常走 `onException` 而非 `onLoadFailed`），最终被 `GlideExecutor` 以 `Request threw uncaught throwable` 吞掉。

### 修复方案

在 `onResourceReady` 和 `onLoadFailed` 回调入口处，用 `itemView.post { ... }` 将后续 UI 操作切到主线程执行。

#### 修复点 1：`onResourceReady`（L569-580）

**修改前**（伪代码）：
```kotlin
override fun onResourceReady(...): Boolean {
    if (currentUrl != url) return false
    onImageFileReady(resource, url, position)  // 直接调用，在 glide-disk-cache-thread
    return true
}
```

**修改后**：
```kotlin
override fun onResourceReady(...): Boolean {
    if (currentUrl != url) return false
    // 修复：downloadOnly 回调在 glide-disk-cache-thread，onImageFileReady 会调用
    // SSIV.recycle() 创建 GestureDetector 抛 Handler 异常，必须切到主线程
    AppLog.put("AOAdapt", "onResourceReady thread=${Thread.currentThread().name} → post to main, url=$url")
    itemView.post {
        if (currentUrl != url) {
            AppLog.put("AOAdapt", "post guarded: currentUrl changed, skip render")
            return@post
        }
        onImageFileReady(resource, url, position)
    }
    return true
}
```

#### 修复点 2：`onLoadFailed`（L582-596）

**修改前**（伪代码）：
```kotlin
override fun onLoadFailed(...): Boolean {
    if (currentUrl != url) return true
    val errLp = itemView.layoutParams
    errLp.height = (itemView.resources.displayMetrics.heightPixels * 0.4).toInt()
    itemView.layoutParams = errLp  // UI 操作，在 glide-disk-cache-thread
    triggerFallbackChain(e, position)  // UI 操作
    return true
}
```

**修改后**：
```kotlin
override fun onLoadFailed(...): Boolean {
    if (currentUrl != url) return true
    AppLog.put("AOAdapt", "onLoadFailed thread=${Thread.currentThread().name} → post to main, url=$url")
    itemView.post {
        if (currentUrl != url) {
            AppLog.put("AOAdapt", "post guarded: currentUrl changed, skip fallback")
            return@post
        }
        val errLp = itemView.layoutParams
        errLp.height = (itemView.resources.displayMetrics.heightPixels * 0.4).toInt()
        itemView.layoutParams = errLp
        triggerFallbackChain(e, position)
    }
    return true
}
```

### 修复后的关键行为

1. **回调线程**：`onResourceReady` / `onLoadFailed` 仍在 glide-disk-cache-thread 触发，但内部 UI 操作通过 `itemView.post` 切到主线程
2. **事件消费**：`onResourceReady` 返回 `true`，告知 Glide 事件已消费，Glide 不会再走默认的 `into(target)` 路径
3. **ViewHolder 复用守卫**：`post` 块内再次校验 `currentUrl != url`，防止 ViewHolder 复用后渲染错位
4. **降级链原子性**：`onLoadFailed` 中的 `layoutParams` 修改 + `triggerFallbackChain` 在同一个 `post` 块内，保证原子性
5. **日志可观测**：关键节点添加 AOAdapt 日志，真机验证时可确认线程切换生效

## Architecture Decisions

### AD-01：选用 `itemView.post` 切主线程

**Context（上下文）**：
`ImageCanvasAdapter.loadImage` 使用 `Glide.downloadOnly().submit()` 下载图片，`RequestListener` 回调在 glide-disk-cache-thread 执行，回调链中的 UI 操作（特别是 `SSIV.recycle()` 内部 `new Handler()`）抛 `RuntimeException`。

**Concern（关注点）**：
- 消除 `Can't create handler inside thread` 异常
- 保证 UI 操作在主线程执行
- 与项目现有代码风格一致
- 不引入新依赖
- 延迟最小化

**Decision（决策）**：
在 `onResourceReady` 和 `onLoadFailed` 回调入口用 `itemView.post { ... }` 切主线程。

**Goal（目标）**：
保证回调链中的所有 UI 操作（`layoutParams` / `View.visibility` / `Glide.load.into` / `SSIV.recycle` / `triggerFallbackChain`）在主线程执行，消除 `Handler` 异常。

**Tradeoff（权衡）**：
- 优点：实现简单、与项目现有用法一致、无新依赖、`post` 内部自带 View 附着语义
- 缺点：异步延迟一帧（~16ms）、需补 ViewHolder 复用守卫
- 否决方案见 spec.md Alternatives Considered（Handler / Coroutine / 单点 post）

**Status（状态）**：🔄 设计中

---

### AD-02：ViewHolder 复用守卫（`currentUrl != url` 检查）

**Context（上下文）**：
`itemView.post` 是异步投递，从投递到执行期间，ViewHolder 可能被 `onBindViewHolder` 复用绑定新 URL，`post` 块内的 `currentUrl` 已更新为新 URL，但闭包捕获的 `url` 仍是旧 URL。

**Concern（关注点）**：
- 防止旧 URL 的图片渲染到新 URL 的 ViewHolder（错位）
- 防止旧 URL 的降级链覆盖新 URL 的正常显示
- 守卫逻辑简单可靠

**Decision（决策）**：
在 `post` 块入口添加 `if (currentUrl != url) return@post` 守卫。`currentUrl` 是 ViewHolder 的可变字段，`bind` 方法（L441-492）每次绑定时更新；`url` 是闭包捕获的不可变参数。

**Goal（目标）**：
快速滑动复用场景下，不渲染错位图片、不启动错误的降级链。

**Tradeoff（权衡）**：
- 优点：实现简单（一行代码）、语义清晰、与 `onResourceReady` 入口的 `currentUrl != url` 检查风格一致
- 缺点：`post` 任务仍会被执行（只是早退），有微小开销；若 `currentUrl` 字段并发读写需保证可见性（由 `bind` 在主线程调用 + `post` 在主线程执行保证，无需 `@Volatile`）

**Status（状态）**：🔄 设计中

---

### AD-03：`onResourceReady` 返回 `true` 消费事件

**Context（上下文）**：
`RequestListener.onResourceReady` 返回 `true` 表示事件已消费，Glide 不会再调用 `Target.onResourceReady`；返回 `false` 表示未消费，Glide 会继续走默认的 `into(target)` 路径。

**Concern（关注点）**：
- 防止 Glide 在 `downloadOnly` 完成后二次处理（如尝试将 `File` 加载到 `Target`）
- 与原代码语义保持一致（原代码已返回 `true`）
- 明确告知 Glide 资源已由回调处理

**Decision（决策）**：
`onResourceReady` 返回 `true`（保持原行为）。`onLoadFailed` 返回 `true`（保持原行为，已消费失败事件）。

**Goal（目标）**：
Glide 不再二次处理资源，所有渲染逻辑由 `onImageFileReady` / `triggerFallbackChain` 在主线程完成。

**Tradeoff（权衡）**：
- 优点：与原代码一致、语义明确
- 缺点：无（保持原行为，无新风险）

**Status（状态）**：🔄 设计中

## Data Flow

### 修复后的回调数据流（文字描述）

**阶段 1 — 下载触发**：
用户进入 `ImageGalleryActivity`，`ImageViewHolder.bind(url, position)` 被调用（L441-492），`bind` 内部调用 `loadImage(url, position)`（L559）。`loadImage` 构造 `Glide.downloadOnly().load(url).listener(RequestListener).submit()`，Glide 在内部线程池调度下载任务，`RequestListener` 被注册到该请求。

**阶段 2 — 下载完成（glide-disk-cache-thread）**：
Glide 下载完成，在 **glide-disk-cache-thread-0** 线程触发 `onResourceReady(resource: File, ...)`。此时：
- 入口守卫：检查 `currentUrl != url`，若 ViewHolder 已被复用则返回 `false`（未消费，Glide 自行处理）
- AOAdapt 日志：记录线程名和切换意图
- 投递主线程任务：调用 `itemView.post { ... }`，将 `onImageFileReady(resource, url, position)` 投递到主线程消息队列
- 立即返回 `true`：告知 Glide 事件已消费

**阶段 3 — 主线程执行渲染**：
主线程 Looper 取出 `post` 任务执行：
- 复用守卫：再次检查 `currentUrl != url`，若已复用则早退并记录守卫生效日志
- 调用 `onImageFileReady(resource, url, position)`（L604-632）：
  - `ImagePyramidLoader.decodeBounds(file)` 解析图片边界（CPU 密集，主线程可接受，原代码即在主线程）
  - 根据图片类型分流：
    - 长图 → `showSsivImage(...)`（L641-672）：设置 `layoutParams`、`Glide.with().clear(photoView)`、`View.visibility`、`ImagePyramidLoader.bindLongImage`、`hideFallbackHint`
    - 普通图 → `loadIntoPhotoView(...)`（L684-737）：设置 `layoutParams`、`ssivView.visibility`、`ssivView.recycle()`（**不再抛异常，因为在主线程**）、`photoView.visibility`、`Glide.load(file).into(photoView)`

**阶段 4 — UI 渲染完成**：
`PhotoView` 或 `SubsamplingScaleImageView` 显示图片，用户可见。

**阶段 5 — 失败路径（onLoadFailed）**：
若下载失败，Glide 在 glide-disk-cache-thread 触发 `onLoadFailed(e, ...)`：
- 入口守卫：检查 `currentUrl != url`
- AOAdapt 日志：记录失败线程和切换意图
- 投递主线程任务：`itemView.post { ... }` 投递降级逻辑
- 主线程执行：设置 `errLp`（高度 40%）、调用 `triggerFallbackChain(e, position)`（L755-838）：`photoView.postDelayed`、`showFallbackHint`

### 关键时序保证

1. **`onResourceReady` 返回 `true` 与 `post` 投递的原子性**：两者在同一个 glide-disk-cache-thread 调用栈内顺序执行，无并发风险
2. **`post` 任务在主线程串行执行**：多个 `post` 任务按投递顺序执行，不会并发
3. **ViewHolder 复用守卫的可见性**：`currentUrl` 由 `bind`（主线程）写入，由 `post` 块（主线程）读取，同线程无可见性问题
4. **Activity 销毁时序**：若 Activity 在 `post` 执行前销毁，`itemView` 已 detach，`post` 任务会被加入 ViewRoot 的队列但可能不执行（或执行时 `binding` 已失效）。需在 `post` 块内对关键 `binding` 字段判空（Kotlin 合成引用在 Activity 销毁后仍可访问，但 View 已 detach，操作无副作用）

## File Changes

### 文件：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

| 行号 | 修改类型 | 修改内容 |
|------|---------|---------|
| L559-598 | 修改 | `loadImage` 方法的 `RequestListener<File>` 回调实现 |
| L569-580 | 修改 | `onResourceReady` 回调：用 `itemView.post { ... }` 包裹 `onImageFileReady` 调用，添加入口守卫、`post` 内复用守卫、AOAdapt 日志 |
| L582-596 | 修改 | `onLoadFailed` 回调：用 `itemView.post { ... }` 包裹 `layoutParams` 修改和 `triggerFallbackChain` 调用，添加入口守卫、`post` 内复用守卫、AOAdapt 日志 |
| L579 | 修改 | `onResourceReady` 返回值保持 `true`（消费事件，见 AD-03） |
| L594 | 修改 | `onLoadFailed` 返回值保持 `true`（消费事件） |
| L441-492 | 不修改 | `bind` 方法（`currentUrl` 字段赋值在此，守卫依赖此字段） |
| L604-632 | 不修改 | `onImageFileReady` 方法（由 `post` 切到主线程后调用，内部逻辑无需改动） |
| L641-672 | 不修改 | `showSsivImage` 方法（主线程执行，无需改动） |
| L684-737 | 不修改 | `loadIntoPhotoView` 方法（主线程执行，L703 `ssivView.recycle()` 不再抛异常） |
| L755-838 | 不修改 | `triggerFallbackChain` 方法（主线程执行，无需改动） |

### 修改详情

#### 修改点 1：`onResourceReady` 回调（L569-580）

**修改前**（关键行）：
```kotlin
override fun onResourceReady(...): Boolean {
    if (currentUrl != url) return false
    onImageFileReady(resource, url, position)  // L579 直接调用
    return true
}
```

**修改后**：
```kotlin
override fun onResourceReady(...): Boolean {
    if (currentUrl != url) return false
    AppLog.put("AOAdapt", "onResourceReady thread=${Thread.currentThread().name} → post to main, url=$url")
    itemView.post {
        if (currentUrl != url) {
            AppLog.put("AOAdapt", "post guarded: currentUrl changed, skip render")
            return@post
        }
        onImageFileReady(resource, url, position)
    }
    return true
}
```

#### 修改点 2：`onLoadFailed` 回调（L582-596）

**修改前**（关键行）：
```kotlin
override fun onLoadFailed(...): Boolean {
    if (currentUrl != url) return true
    val errLp = itemView.layoutParams
    errLp.height = (itemView.resources.displayMetrics.heightPixels * 0.4).toInt()
    itemView.layoutParams = errLp
    triggerFallbackChain(e, position)  // L594
    return true
}
```

**修改后**：
```kotlin
override fun onLoadFailed(...): Boolean {
    if (currentUrl != url) return true
    AppLog.put("AOAdapt", "onLoadFailed thread=${Thread.currentThread().name} → post to main, url=$url")
    itemView.post {
        if (currentUrl != url) {
            AppLog.put("AOAdapt", "post guarded: currentUrl changed, skip fallback")
            return@post
        }
        val errLp = itemView.layoutParams
        errLp.height = (itemView.resources.displayMetrics.heightPixels * 0.4).toInt()
        itemView.layoutParams = errLp
        triggerFallbackChain(e, position)
    }
    return true
}
```

### 不修改的关联代码（说明）

- `ImagePyramidLoader`：长图分块加载逻辑，主线程调用，无需改动
- `SubsamplingScaleImageView`（SSIV）：第三方库，`recycle()` 行为正确，只是必须在主线程调用
- `Glide` 版本：保持现状（项目依赖锁定策略）
- `bind` 方法（L441-492）：`currentUrl` 字段赋值在此，守卫依赖此字段，不修改

### 影响范围

- **直接影响**：`ImageCanvasAdapter.kt` 一个文件，约 20 行代码修改
- **间接影响**：图片画廊的所有加载路径（正常加载、长图、失败降级）均受益
- **无影响**：其他 Adapter、其他 Activity、数据库、网络层、规则引擎
