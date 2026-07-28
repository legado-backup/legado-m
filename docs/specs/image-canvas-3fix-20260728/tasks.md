# 设计文档（image-canvas-3fix-20260728）

> tasks.md — 实施任务清单

## 0. 文档说明

本文档列出 image-canvas-3fix-20260728 的分阶段实施任务、验证方法和编译测试包验证步骤。所有任务基于 design.md 的源码级设计方案。

---

## 1. 实施阶段划分

| 阶段 | 任务 | 优先级 | 依赖 |
|------|------|--------|------|
| Phase 1 | Q3 修复（无限降级循环） | P0 | 无 |
| Phase 2 | Q2 修复（L2 超时丢弃 URL） | P0 | 无 |
| Phase 3 | Q1 修复（滚动位置） | P1 | 无 |
| Phase 4 | 编译测试包验证 | P0 | Phase 1-3 完成 |
| Phase 5 | 真机测试 + 日志验证 | P0 | Phase 4 完成 |
| Phase 6 | 更新日志 + 文档同步 | P0 | Phase 5 通过 |

---

## 2. Phase 1：Q3 修复（无限降级循环）

### 任务 1.1：bind 方法 isPreheatReload 计算前移 + retryCount 条件重置

**修改文件**：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

**修改位置**：L450-495 bind 方法

**修改内容**：
1. 将 L489 的 `val isPreheatReload = preheatReloadPositions.remove(position)` 前移到 L454 之前
2. L454 `retryCount = 0` 改为：
   ```kotlin
   if (isPreheatReload) {
       // 预热重载：保留 retryCount，降级链续接
       AppLog.putDebugWithTag(
           AppLog.TAG_IMAGE_CANVAS,
           "bind: preheat reload, retryCount preserved=$retryCount position=$position",
           level = AppLog.Level.INFO
       )
   } else {
       retryCount = 0
   }
   ```
3. L489 处移除重复的 isPreheatReload 计算（已在前面计算）

**验证方法**：
- [ ] 编译通过（./gradlew assembleDebug）
- [ ] Grep "retryCount = 0" 确认仅在不分支内存在
- [ ] Grep "isPreheatReload" 确认计算前移
- [ ] 真机测试：触发降级3 预热场景，确认降级链不循环（Q3-AC1）

---

## 3. Phase 2：Q2 修复（L2 超时丢弃 URL）

### 任务 2.1：extractWithWebView 移除外层 withTimeoutOrNull

**修改文件**：`app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt`

**修改位置**：L583-612 extractWithWebView 方法

**修改内容**：
1. 移除外层 `withTimeoutOrNull(L2_WEBVIEW_TIMEOUT_MS) { ... } ?: run { ... emptyList() }` 包装
2. 直接调用 `ImageSnifferWebView(...).sniffImageUrls()`（sniffImageUrls 内部已有超时机制）
3. 保留 try-catch 处理非超时异常

**修改后代码骨架**：
```kotlin
return webviewMutex.withLock {
    try {
        ImageSnifferWebView(
            url = link,
            headerMap = headerMap,
            tag = rssSource.sourceUrl,
            timeout = L2_WEBVIEW_TIMEOUT_MS,
            delayTime = 1500L
        ).sniffImageUrls()
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        AppLog.putDebugWithTag(..., "L2 webview sniff error: ...", ...)
        emptyList()
    }
}
```

**验证方法**：
- [ ] 编译通过
- [ ] Grep "withTimeoutOrNull" 确认 extractWithWebView 内无外层包装
- [ ] 真机测试：触发 L2 嗅探超时场景，确认 `extractImageList done` 日志中 l2 > 0（Q2-AC1）

### 任务 2.2：策略2 命中数 < 3 时继续策略3

**修改文件**：`app/src/main/java/io/legado/app/help/image/ImageUrlExtractor.kt`

**修改位置**：L264-316 策略2 + 策略3 代码块

**修改内容**：
1. 策略2 命中后判断 `imgUrls.size >= 3`，是则 return；否则保存到 `strategy2Result` 继续策略3
2. 策略3 命中后合并 `strategy2Result + regexUrls` 去重返回
3. 策略3 未命中但 `strategy2Result` 非空，返回 `strategy2Result`

**验证方法**：
- [ ] 编译通过
- [ ] Grep "strategy2Result" 确认合并逻辑存在
- [ ] 真机测试：限流场景（HTTP 429）下确认策略2 + 策略3 合并日志（Q2-AC2）

---

## 4. Phase 3：Q1 修复（滚动位置）

### 任务 3.1：onCreateViewHolder 强制创建新 layoutParams

**修改文件**：`app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

**修改位置**：L249-253 onCreateViewHolder

**修改内容**：
- `binding.root.layoutParams = binding.root.layoutParams.apply { height = defaultHeight }`
- 改为 `binding.root.layoutParams = ViewGroup.LayoutParams(MATCH_PARENT, defaultHeight)`

**验证方法**：
- [ ] 编译通过
- [ ] Grep "ViewGroup.LayoutParams" 确认新写法
- [ ] 真机测试：确认图片项 defaultHeight 生效（Q1-AC4）

### 任务 3.2：observeNewItems 使用 OnGlobalLayoutListener

**修改文件**：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

**修改位置**：L702-712 observeNewItems

**修改内容**：
- `binding.recyclerView.post { scrollToPosition(0) }`
- 改为 `viewTreeObserver.addOnGlobalLayoutListener { ... scrollToPosition(0) }`

**验证方法**：
- [ ] 编译通过
- [ ] Grep "OnGlobalLayoutListener" 确认新写法
- [ ] Grep "removeOnGlobalLayoutListener" 确认 listener 被移除（避免内存泄漏）
- [ ] 真机测试：确认进入图片画布定位第一张（Q1-AC1, Q1-AC2）

### 任务 3.3：首次插入时禁用 loadNextArticle

**修改文件**：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

**修改位置**：onScrolled 方法中的 loadNextArticle 触发逻辑

**修改内容**：
- 在 onScrolled 开头增加 `if (!isInitialScrollDone) return` 守卫

**验证方法**：
- [ ] 编译通过
- [ ] Grep "isInitialScrollDone" 确认 onScrolled 守卫
- [ ] 真机测试：确认首次插入后无 loadNextArticle 日志（Q1-AC3）

---

## 5. Phase 4：编译测试包验证

### 任务 4.1：编译测试包

**包类型**：测试包（debug 构建）
**包名**：`io.legado.miss.app.debug`

**编译命令**：
```bash
./gradlew assembleDebug
```

**验证方法**：
- [ ] 编译成功，无 error
- [ ] APK 生成路径：`app/build/outputs/apk/debug/app-debug.apk`
- [ ] Grep 确认无调试日志残留（android.util.Log.d / android.util.Log.e）

### 任务 4.2：安装测试包到真机/模拟器

**安装命令**：
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**验证方法**：
- [ ] 安装成功
- [ ] 应用名"阅读M"显示正常
- [ ] 包名确认为 `io.legado.miss.app.debug`

---

## 6. Phase 5：真机测试 + 日志验证

### 任务 5.1：Q1 真机测试

**测试步骤**：
1. 打开含图片的 RSS 文章
2. 进入图片画布
3. 观察初始滚动位置（应在第一张图片）
4. 抓取 appLog

**验证清单**：
- [ ] Q1-AC1：RecyclerView 定位在第一张图片
- [ ] Q1-AC2：日志含 `observeNewItems: initial scroll to position 0 (after layout)`
- [ ] Q1-AC3：首次插入后无 `Scroll: trigger loadNextArticle` 日志
- [ ] Q1-AC4：notifyItemRangeInserted 后 lastVisible < itemCount

### 任务 5.2：Q2 真机测试

**测试步骤**：
1. 打开含多图的 RSS 文章（模拟限流场景或选择已知限流源）
2. 进入图片画布
3. 等待 L2 WebView 嗅探完成
4. 抓取 appLog

**验证清单**：
- [ ] Q2-AC1：`extractImageList done` 日志中 l2 > 0
- [ ] Q2-AC2：strategy 2 success（count < 3）后存在 strategy 3 success 日志
- [ ] Q2-AC3：最终图片数量 ≥ L1 + L2 收集总数（去重后）
- [ ] Q2-AC4：限流场景下仍能通过 L2 嗅探获取完整图片列表

### 任务 5.3：Q3 真机测试

**测试步骤**：
1. 打开含防盗链图片的 RSS 文章
2. 进入图片画布
3. 等待降级链触发（观察 fallback hint 提示）
4. 观察图片是否反复闪烁（无限循环）
5. 抓取 appLog

**验证清单**：
- [ ] Q3-AC1：同一 urlHash 的降级链单调递增（无 fallback-1→2→3→1 循环）
- [ ] Q3-AC2：preheat reload 后 `bind: preheat reload, retryCount preserved=N` 日志
- [ ] Q3-AC3：预热重载后图片成功加载或进入降级4（非无限循环）
- [ ] Q3-AC4：非预热场景降级链从 fallback-1 开始（retryCount=0 重置正常）

### 任务 5.4：回归测试

**测试范围**：
- [ ] 正常图片文章阅读（无限流/无防盗链）
- [ ] 书架功能正常
- [ ] 书源管理正常
- [ ] 正文阅读正常
- [ ] 应用无崩溃

---

## 7. Phase 6：更新日志 + 文档同步

### 任务 6.1：更新 updateLog.md

**修改文件**：`assets/updateLog.md`

**更新内容**（基于真实代码变更分析）：
```
## 2026-07-28 image-canvas-3fix
- 修复：进入图片画布后滚动到最后一张图片的问题（初始滚动位置 + defaultHeight 设置）
- 修复：L2 WebView 嗅探超时后已收集的图片 URL 被丢弃的问题（51张URL丢失）
- 修复：图片加载失败后降级链无限循环的问题（fallback-1→2→3→1 循环）
- 优化：策略2 命中数不足时继续策略3 合并结果，提升限流场景图片提取率
```

**验证方法**：
- [ ] git diff 确认 updateLog.md 已更新
- [ ] 对照变更文件列表确认每个变更都有对应日志条目

### 任务 6.2：文档同步检查

**检查清单**：
- [ ] issues-found.md 记录所有测试中发现的问题
- [ ] tasks.md（本文件）所有任务勾选完成
- [ ] design.md 源码行号与实际代码一致（修复后行号可能变化）
- [ ] project_memory（ai_memory_main.md）记录本次任务状态

---

## 8. 任务总览清单

| 任务ID | 任务 | 阶段 | 状态 |
|--------|------|------|------|
| 1.1 | bind 方法 isPreheatReload 计算前移 + retryCount 条件重置 | Phase 1 | ☐ |
| 2.1 | extractWithWebView 移除外层 withTimeoutOrNull | Phase 2 | ☐ |
| 2.2 | 策略2 命中数 < 3 时继续策略3 | Phase 2 | ☐ |
| 3.1 | onCreateViewHolder 强制创建新 layoutParams | Phase 3 | ☐ |
| 3.2 | observeNewItems 使用 OnGlobalLayoutListener | Phase 3 | ☐ |
| 3.3 | 首次插入时禁用 loadNextArticle | Phase 3 | ☐ |
| 4.1 | 编译测试包 | Phase 4 | ☐ |
| 4.2 | 安装测试包到真机/模拟器 | Phase 4 | ☐ |
| 5.1 | Q1 真机测试 | Phase 5 | ☐ |
| 5.2 | Q2 真机测试 | Phase 5 | ☐ |
| 5.3 | Q3 真机测试 | Phase 5 | ☐ |
| 5.4 | 回归测试 | Phase 5 | ☐ |
| 6.1 | 更新 updateLog.md | Phase 6 | ☐ |
| 6.2 | 文档同步检查 | Phase 6 | ☐ |

---

## 9. 关键约束

### 9.1 测试包选择

- **代码优化任务**：必须使用测试包 `io.legado.miss.app.debug`（debug 构建，含调试日志，便于定位问题）
- 禁止使用正式包测试代码优化（无法定位问题，且正式包签名固定无法频繁替换）

### 9.2 日志验证

- 所有验证日志通过 `ai_tests/venv/Scripts/python.exe` + `ai_tests/scripts/` 下脚本抓取
- 禁止在 temp/ 创建临时脚本
- 日志分析只输出技术结论（错误码/异常类型/调用栈/数量统计），不输出含域名/URL 的原始日志行

### 9.3 代码约束

- 协程用自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装
- 错误处理用 `kotlin.runCatching`（带 `kotlin.` 前缀）
- 日志用 `AppLog.put()`，禁止 `android.util.Log`
- 异常用 `NoStackTraceException`（业务异常继承此类）

### 9.4 编译前检查

- [ ] Grep "android.util.Log.d\|android.util.Log.e" 确认无调试日志残留
- [ ] updateLog.md 已更新
- [ ] 代码变更基于 git diff 真实分析
