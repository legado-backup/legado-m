# 图片消费契约（image-consumption-contract）

> 定位：**W7 8.3 的附加产出**（`docs/specs/archive/2026-09-28-next-stage-mainline/tasks.md` §8.3 / AD-21 沉淀）。
> 目的：把「画布域图片如何呈现」收敛为**单一契约**，后续任何图片相关需求**先读本文**再动手，
> **禁止再新增第三种图片视图**（历史上长图/普通图双轨已导致手势与回弹行为随图尺寸分叉）。
>
> 权威实现：`app/src/main/java/io/legado/app/ui/image/ImagePyramidLoader.kt`、
> `app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt`

---

## 一、唯一呈现入口（轨道归一）

| 入口 | 适用 | 说明 |
|------|------|------|
| `ImagePyramidLoader.bindImage(ssiv, file, imgW, imgH, viewW, viewH)` | **默认**（长图与普通图统一轨） | 内部分流判据 = 「视图高是否被上限截断」（`viewW * imgH / imgW > viewH`）：未截断走 `CENTER_INSIDE`（整图可见），已截断走 `SCALE_TYPE_CUSTOM + minScale` 宽度优先填充 + 平移查看 |
| `ImagePyramidLoader.bindLongImage(...)` | **冻结兼容入口**（纯委托到 `bindImage`） | 仅为回滚点保留；**新代码禁止调用** |
| `ImagePyramidLoader.bindNormalImage(...)` | 「必须以整图可见为前提」的消费点 | 不做截断分流，恒 `CENTER_INSIDE` |

**禁止事项**

1. 新增第三种图片视图 / 再引入第三方 zoomable view；
2. 在消费点自行写 `isLongImage` 式尺寸分流（会重新分裂手势语义）；
3. 绕过 `bindImage` 直调 `bindLongImage`。

## 二、加载通道（唯一）

```
Glide.downloadOnly()  →  磁盘缓存文件  →  decodeBounds(仅读文件头)  →  bindImage(SSIV 区域解码)
```

- **回调必须切主线程**：`downloadOnly` 回调在 `glide-disk-cache-thread`，SSIV 的 `recycle()` 会建 `GestureDetector` ⇒ 必须在 `itemView.post {}` 内执行（否则抛 Handler 异常且被 Glide 包装吞掉，表现为「不触发 onLoadFailed」）。
- **Activity 销毁后禁止一切 Glide 调用**：统一走 `isGlideUsable()` 守卫（防 `destroyed activity` 崩溃）。
- **内存**：SSIV 区域解码 ⇒ 内存占用与图片尺寸无关（长图不 OOM）；高度上限 `SSIV_MAX_HEIGHT_SCREEN_MULTIPLIER = 20` 倍屏高。

## 三、状态呈现（逐项 + footer 两级，**不新增状态机**）

| 层级 | 载体 | 内容 |
|------|------|------|
| **逐项**（W7 8.3） | `item_image_canvas.xml` 的 `pb_item_loading` / `layout_item_error` | ① 加载与降级期间显示占位（消除静默黑屏）② 终态失败显示**原因 + 原地重试**（`btn_item_retry` → `retryFromScratch()`） |
| **footer**（分页） | `item_image_canvas_footer.xml` | 加载中 / 失败（原因 + 重试 + 返回顶部）/ 没有更多 |

- 状态机**只有一套**：`ImageCanvasAdapter.LoadState`（`IDLE / LOADING / SUCCESS / ERROR / NO_MORE`）。逐项呈现只复用它的语义与分类，不引入新的 sealed class。
- 失败原因**分类单一源**：`ImageCanvasAdapter.ErrorCategory { NETWORK, PARSE, SOURCE }`（`classifyError()` 沿 cause 链判定）⇒ 文案资源 `image_load_error_{network,parse,source}`；**禁止**把 `Throwable.message` 直接呈现给用户（可能带内部路径）。
- 逐项失败文案色走语义色单源 `AppSemanticColors.Danger`（`AD-14`），禁止页内写死色值。

## 四、失败自愈（自动降级链 4 级）

| 级别 | 动作 | 约束 |
|------|------|------|
| 1 | Glide 重试（`skipMemoryCache` + 延迟 500ms） | 必须 `bypassFailCache` 否则不发请求 |
| 2 | OkHttp + Cookie 兜底（`DiskCacheStrategy.NONE`） | 经 `OkHttpModelLoader.sourceOriginOption` 注入源 header |
| 3 | WebView 即时预热（`onWebViewFallback`） | **每 URL 只允许一次**（`preheatedUrlHashes`，防「预热→重载→再预热」死循环） |
| 4 | 网页模式回退（`onWebModeFallback`） | 同时呈现**逐项失败 + 原地重试**（W7 8.3） |

**用户主动重试**（`retryFromScratch()`）与自动链的差别：主动重试会**清除该 URL 的预热标记**并归零 `retryCount`，让第 3 级重新可用（否则重试直接落到第 4 级，失去意义）。

## 五、防盗链头（防 403 / 图床拦截）

- 取值优先级：**显式传参**（`setAntiLeechHeaders(sourceOrigin, articleLinks)`）→ `ImagePlay` 全局态兜底。
- `source.header`（含 UA / Cookie）由 `OkHttpStreamFetcher` 经 `AnalyzeUrl` 自动注入；`Referer` 优先取 `source.header`，其次文章页 URL。
- 两者皆缺时输出 `headers missing` WARN（提前暴露误配）。

## 六、离线预取（文章级）

- 开关：`PreferKey.imageArticlePrefetch`（默认**关**）。
- **挂钩唯一**：`ui/image/ImageCanvasViewModel` 的 `ImageUrlExtractor.extractImageList(...)` 之后。
- 上限：并发 2 / 单文章 ≤200 张 / 单张失败不阻塞正文呈现。
- 已知上限：缓存**可查可清**（第 5 维）尚未接入 `CacheManageViewModel`（登记于交接文档遗留项）。

## 七、取色（画布域豁免）

画布域 = 图片全屏浏览 / 裁剪，**固定深色底 + 压在图片上的白色控件**，设计上与应用主题解耦：

- 路径族：`res/layout/item_image_*.xml`、`res/drawable/bg_image_crop_*`、`res/layout/activity_image_{gallery,detail,crop}.xml`
- 登记处：`ai_tests/config/theme_token_allowlist.json` 的 `entries`（新增画布域文件**必须**同步登记，否则 PreToolUse 拦截）
- **例外**：画布域内**非控件**语义（卡片/chip/分隔线等）仍须走面 token（`cardColor` / `tabBackgroundColor` / `searchFieldBackgroundColor` / `dividerColor`）

## 八、消费点清单（当前全量）

| 消费点 | 视图 | 契约状态 |
|--------|------|----------|
| `ui/image/adapter/ImageCanvasAdapter` | SSIV（`bindImage`） | ✅ 唯一呈现入口 + 逐项状态（W7 8.3） |
| `ui/widget/dialog/PhotoDialog` | SSIV | ✅ W6 已换轨 |
| `ui/main/ai/AiImagePreviewDialog` | SSIV | ✅ W6 已换轨 |
| `ui/book/read/ReadSelectionImageDialog` | SSIV | ✅ W6 已换轨 |
| `ui/image/adapter/ImageDetailAdapter`（+`item_image_page.xml`） | `PhotoView` | ⚖️ **技术硬例外**（横向 ViewPager2 翻页与平移手势竞争 + 旋转后手势坐标系错位；SSIV 无等价能力） |
| `ui/image/ImageCropActivity` | `PhotoView` | ⚖️ **技术硬例外**（依赖 `setScaleType/setMaxScale` + `cropOverlay.getCropRect()` + `imageMatrix`） |
| `ui/widget/image/PhotoView.kt` 本体 | — | ⚖️ 保留（上述两处例外依赖） |
| `ui/book/manga/`（`WebtoonRecyclerView`） | 漫画专用 | 阅读域，不属本契约呈现轨（见 `item_book_manga_page.xml` 豁免） |

> 例外口径来源：`docs/specs/archive/2026-09-28-next-stage-mainline/design.md` §5.7.1 / §5.7.2（四要素条目）。

## 九、新增图片需求的标准流程

1. **查本契约**，确认能否复用既有呈现轨与状态呈现；
2. 能复用 ⇒ **复用** `bindImage`，不得自建视图或分裂尺寸分流；
3. 确实不能复用 ⇒ 先做**技术例外评估**（依赖 API / 替代路径 / 回归手段），登记到 design.md 例外表；
4. 取色：画布域走豁免**并登记 allowlist**；非画布域走面 token；
5. **配对测试**：断言接线不变量（参考 `ImageItemLoadStateWiringTest` / `ImageCanvasUnifiedTrackWiringTest`）；
6. 性能：涉及列表滚动的改动须按 `ai_tests/scripts/perf_gfxinfo.py` 取 3 次中位数对比（劣化 >10% 回退）。
