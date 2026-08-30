# Spec: 嗅探回归与图片订阅源崩溃取证修复

## Intent

修复两个用户反馈问题：
1. 视频嗅探能力下降——系统浏览器可正常播放，App 内置嗅探失败（回归性 Bug，根因已定位到 WebView 池分层重构 `bbc9d0a89`）。
2. 浏览图片订阅源崩溃——本次日志未捕获崩溃栈，需建立取证闭环后精准修复。

## Scope

### In Scope
- 修复 `WebViewPool` 中进程级 `pauseTimers()`/`resumeTimers()` 的 scope 隔离误判（跨 scope 全局互斥语义回归）
- 日志导出增强：导出内容附带 `crash/` 目录最近崩溃文件（取证链路补全）
- 嗅探链路回归验证（真机 L2）

### Out of Scope
- 图片订阅源崩溃的根因修复（依赖 crash 文件取证结果，二次任务）
- `destroyScope()` 销毁 inUsePool 的伴生风险重构（单独评估，本次不动，避免改 A 坏 B）
- 嗅探窗口时长（R5_DELAY_TIME/R5_TIMEOUT）调参（根因修复后视真机结果再定）

## Approach

### Selected Approach

**问题1（嗅探回归）**：将 `pauseTimers()`/`resumeTimers()` 的判断从"单一 scope 的 inUsePool 是否为空"改为"**所有 scope 的 inUsePool + resettingPool 全局是否为空**"。
- `release()`：仅当全局无任何使用中 WebView 时才 `pauseTimers()`
- `acquire()`：无条件 `resumeTimers()`（幂等且廉价，彻底消除冻结窗口）
理由：`pauseTimers()`/`resumeTimers()` 本身就是进程级 API，其判断条件必须与作用域一致——这是重构 `bbc9d0a89` 引入的语义错误，修复即回归到重构前的"全进程互斥"语义，scoped 池只应隔离缓存容量/闲置回收。

**问题2（图片订阅源崩溃）**：取证优先。在日志导出入口附带 crash 目录最近崩溃文件，用户复现后导出日志即可携带崩溃栈，二次任务精准修复。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 嗅探场景 acquire 后强制 `resumeTimers()`，其余不动 | 只堵 GLOBAL 池一个入口，发现页/订阅页后台 WebView 的 pauseTimers 仍可能在其他 BackstageWebView（书源调试等）场景冻结嗅探；且语义仍是错的（进程级 API 配 scope 级判断） |
| 恢复单一全局池（回退 `bbc9d0a89`） | 分层池的缓存隔离/闲置回收收益是真实的，回退损失大且高风险；只修进程级 API 的判断条件即可，改动最小 |
| BackstageWebView 嗅探改用独立 new WebView 不入池 | 绕开池但破坏池化管理，增加 WebView 实例数与内存压力，治标不治本 |
| 图片崩溃：直接对图片解码/WebView 渲染路径做防御性加固（OOM 兜底/onRenderProcessGone） | 无崩溃栈支撑，加固点靠猜，可能改不到真根因；且违反"不能只改代码不验证"，取证成本远低于盲改成本 |
| 图片崩溃：要求用户手动 adb pull crash 文件 | 用户操作成本高；且 App 内日志导出功能本就该附带崩溃文件（取证能力缺失是真实缺陷） |

### Drawbacks

- `acquire()` 无条件 `resumeTimers()`：在全局确有其他 WebView 使用时多调用一次进程级恢复（幂等，无功能副作用，仅一次 binder 调用开销），接受。
- 全局计数判断需跨 scope 池遍历：三池规模极小（每池 maxCached≤2），遍历开销可忽略，接受。
- 日志导出附带 crash 文件会略微增大导出包体：crash 文件 7 天自动清理（现有逻辑）且为纯文本，体积可控，接受。
- 图片崩溃本次只交付取证不交付修复：用户需多一轮复现，但换来精准根因，避免盲改引入新问题，接受。

### Prior Art

- 重构前基线：`bbc9d0a89` 之前的单一池实现（pauseTimers 判断遍历全局 inUsePool，嗅探中 WebView 计入 → 永不误暂停）
- 图片栈前科：crash-2026-07-26（ImageGalleryActivity/ImageCanvasAdapter 已有 Activity 销毁守卫、postValue→setValue 修复），说明该栈历来是崩溃高发区，取证后修复方向有据可循

## Requirements

1. `WebViewPool.release()` 中 `pauseTimers()` 仅在**全部 scope**（GLOBAL/DISCOVERY/RSS）的 inUsePool + resettingPool 均为空时执行
2. `WebViewPool.acquire()` 中无条件 `resumeTimers()`（保持原 L98 语义向上兼容）
3. 日志导出内容附带 crash 目录最近崩溃文件（存在才带，不存在静默跳过）
4. 修复后视频嗅探在"刚浏览过发现页/订阅页"场景下仍能正常命中（真机验证）
5. 不改变 scoped 池的缓存容量/闲置回收/destroyScope 现有行为

## Scenarios

| # | 场景 | 预期 |
|---|------|------|
| S1 | 从订阅页/发现页返回后立即进入视频文章触发嗅探 | 嗅探 WebView JS 不被冻结，6 秒窗口内正常命中视频地址 |
| S2 | 无任何后台 WebView 使用时释放最后一个 WebView | 正常 `pauseTimers()`（省电语义保留） |
| S3 | GLOBAL 池嗅探进行中，DISCOVERY 池最后一个 WebView 释放 | 不执行 `pauseTimers()`，嗅探不受影响 |
| S4 | 图片订阅源崩溃后导出日志 | 导出内容包含 `crash-*.log` 崩溃栈文件 |
| S5 | 从未崩溃的设备导出日志 | 无 crash 文件，导出正常不报错 |
