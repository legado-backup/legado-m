package io.legado.app.ui.rss.article.compose

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：RSS 文章五样式族的 **Compose 侧实现契约**（JVM 可跑）。
 *
 * 迁移的等价性风险集中在三处，本测试分别锁死：
 * ①**五样式分派**（0/1 线性、2 两列、3 瀑布流、4 三列）——必须由 `style` 唯一决定容器与行组件；
 * ②**封面取数单源**——列表主查询不含 `image`（base64 大图会挤爆 CursorWindow）⇒ 必须逐项单行走 DAO；
 * ③**取色/尺寸走资源单源**——不得出现硬编码色值（本仓取色红线），文案尺寸沿用原 XML 的 dimen 数值。
 */
class RssArticleComposeComponentsTest {

    private fun listSource(): String =
        SourceFileProbe.sourceText("ui/rss/article/compose/RssArticlesComposeList.kt")

    private fun imageSource(): String =
        SourceFileProbe.sourceText("ui/rss/article/compose/RssArticleImage.kt")

    private fun favoritesSource(): String =
        SourceFileProbe.sourceText("ui/rss/favorites/compose/RssFavoritesComposeList.kt")

    private fun pagingSource(): String =
        SourceFileProbe.sourceText("ui/rss/article/compose/RssPaging.kt")

    /**
     * 取「非注释」代码文本。
     *
     * 断言「旧写法已删」时必须先剔除注释行：本文件的 KDoc 会**刻意保留**被替换旧实现的说明
     * （如 `AndroidView(FilletImageView)`），若直接在全文上断言 `!contains(...)` 会被注释自身误报命中
     * （本仓既有教训：断言"旧写法已删"要先剔除注释行）。
     */
    private fun codeOnly(text: String): String =
        text.lineSequence()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("//") || t.startsWith("*") || t.startsWith("/*")
            }
            .joinToString("\n")

    @Test
    fun composeImplementationsExist() {
        val root = SourceFileProbe.mainJavaRoot()
        listOf(
            "io/legado/app/ui/rss/article/compose/RssArticlesComposeList.kt",
            "io/legado/app/ui/rss/article/compose/RssArticleImage.kt",
            "io/legado/app/ui/rss/article/compose/RssPaging.kt",
            "io/legado/app/ui/rss/favorites/compose/RssFavoritesComposeList.kt",
        ).forEach { rel ->
            assertTrue("Compose 列表实现缺失：$rel", File(root, rel).isFile)
        }
    }

    @Test
    fun fiveStylesDispatchToDedicatedContainers() {
        val s = listSource()
        // 三种容器各司其职：线性 / 定列网格 / 瀑布流
        listOf(
            "LazyVerticalStaggeredGrid(",
            "LazyVerticalGrid(",
            "LazyColumn(",
        ).forEach { marker ->
            assertTrue("样式容器缺失：`$marker`", s.contains(marker))
        }
        // 五种行组件（含收藏页共用的样式 0 行）
        listOf(
            "fun RssArticleListRow(",
            "private fun RssArticleBigCoverRow(",
            "private fun RssArticleGridRow(",
            "private fun RssArticleCardRow(",
        ).forEach { marker ->
            assertTrue("样式行组件缺失：`$marker`", s.contains(marker))
        }
        // 翻页提前量必须走单源纯函数（阈值不再散落在列表层与宿主层两处）
        assertTrue(
            "翻页提前量必须由 RssPagingThresholdResolver 单源给出",
            s.contains("RssPagingThresholdResolver.resolve(style, isPreload)")
        )
        assertTrue("预加载阈值单源缺失", pagingSource().contains("PRELOAD_THRESHOLD = 5"))
    }

    /**
     * 2026-10-07 用户报障回归（rss-list-padding-tighten）：五样式左右留白必须走**固定 dp 单源**。
     *
     * 历史写法「`N px` 数值再做 px→dp 换算」（`with(LocalDensity.current){ 40.toDp() }`）会使留白随
     * 屏幕像素密度**反向**放大（手机 40px≈14.5dp、低密度模拟器/平板 26.7~40dp）⇒ 卡片被压窄
     * （用户体感「其他样式宽留白太多」）。现收敛为 [RssArticleListSpacing]（`OUTER_DP` / `GAP_DP`），
     * 对齐「自由」布局（样式 5）的紧凑口径。
     */
    @Test
    fun spacingUsesFixedDpSingleSource() {
        // 取值本身（真断言，非源码子串）
        assertEquals("外沿留白必须为 4dp（对齐自由布局）", 4, RssArticleListSpacing.OUTER_DP)
        assertEquals("条目间距必须为 4dp（对齐自由布局）", 4, RssArticleListSpacing.GAP_DP)
        val s = codeOnly(listSource())
        // 使用点：五样式留白均取自单源（外沿 / 间距）
        assertTrue("外沿必须取单源 OUTER_DP", s.contains("RssArticleListSpacing.OUTER_DP.dp"))
        assertTrue("间距必须取单源 GAP_DP", s.contains("RssArticleListSpacing.GAP_DP.dp"))
        // 回退防线：px 伪 dp 写法必须清零（KDoc/注释中的历史说明由 codeOnly 剔除）
        listOf("px40", "px30", "px60", "px8", "px4").forEach { gone ->
            assertFalse("不得回退为 px 伪 dp 写法：`$gone`", s.contains(gone))
        }
    }

    @Test
    fun xmlPixelAndFontFactsArePreserved() {
        val s = listSource()
        listOf(
            // 样式 0：100dp 行高 / 纵向 16dp 内边距（左右已于 2026-10-07 收窄至 OUTER_DP）/ 110×68 封面
            ".height(100.dp)",
            ".padding(horizontal = RssArticleListSpacing.OUTER_DP.dp, vertical = 16.dp)",
            ".width(110.dp)",
            ".height(68.dp)",
            // 样式 1：220dp 封面 + 8dp 分隔块
            ".height(220.dp)",
            ".height(8.dp)",
            // 样式 2/4：272dp / 182dp 封面（由网格行参数下发）
            "coverHeight = 272.dp",
            "coverHeight = 182.dp",
            // 圆角 12dp（沿用原 app:radius）
            "radiusDp = 12",
            // 字号/字重逐项对齐原 XML（样式 3 的横屏变体与竖屏共用同一实现 ⇒ 字号为三元表达式，见 `layout-land`）
            "fontSize = 16.sp",
            "fontSize = 15.sp",
            "fontSize = 13.sp",
            "fontSize = 12.sp",
            "fontSize = 11.sp",
            "if (landscape) 16.sp else 13.sp",
            "if (landscape) 14.sp else 11.sp",
            "fontWeight = FontWeight.Bold",
            "fontStyle = FontStyle.Italic",
        ).forEach { marker ->
            assertTrue("原 XML 的尺寸/字号事实不得丢：`$marker`", s.contains(marker))
        }
    }

    @Test
    fun colorsComeFromResourcesOnly() {
        val list = listSource()
        assertTrue("已读/未读标题色必须走资源", list.contains("colorResource(if (read) R.color.tv_text_summary else R.color.primaryText)"))
        assertTrue("分隔线色必须走资源", list.contains("colorResource(R.color.bg_divider_line)"))
        assertTrue("瀑布流卡底色必须走资源", list.contains("colorResource(R.color.card_bg_water)"))
        assertTrue("瀑布流卡描边色必须走资源", list.contains("colorResource(R.color.card_border_water)"))
        // 硬编码色值红线（本仓取色门禁口径：Compose 侧同样不得写死 0xAARRGGBB）
        assertFalse(
            "Compose 列表内不得硬编码色值",
            Regex("0x[0-9A-Fa-f]{8}").containsMatchIn(list)
        )
    }

    @Test
    fun articleImageIsSingleSourced() {
        val img = codeOnly(imageSource())
        // 取数：逐项单行 DAO（列表主查询不含 image，见 KDoc 的 CursorWindow 2MB 说明）
        assertTrue("必须逐项单行查 image", img.contains("appDb.rssArticleDao.getImage(origin, link)"))
        // Glide 必须带源站选项（漏传 ⇒ 大量源取不到图）
        assertTrue("Glide 必须带 sourceOriginOption", img.contains("OkHttpModelLoader.sourceOriginOption"))
        // 瀑布流比例缓存（20 天持久化）单源
        assertTrue("比例缓存单源缺失", img.contains("object RssImageAspectRatioStore"))
        assertTrue("比例必须落持久缓存", img.contains("CacheManager.put(KEY_NAME + url, aspectRatio, SAVE_TIME)"))
        // 取数通道 typealias 由列表与收藏页共同引用，不得改名（收藏页注入 rssStarDao 通道）
        assertTrue("取数通道 typealias 缺失", img.contains("typealias RssArticleImageQuery"))
    }

    /**
     * AD-05 回归（2026-09-28 用户报障）：封面必须走 **Compose 原生渲染**。
     *
     * 原实现用 `AndroidView(FilletImageView)`：RecyclerView 有 ViewHolder 复用池，而 LazyList 中
     * `AndroidView` **不保证底层 View 复用** ⇒ 每行滑入都新建 View + 一次单行查库 + 一次 Glide 请求
     * （View 创建在 UI 线程），fling 时被放大成可感知卡顿。
     */
    @Test
    fun articleImageRendersNativelyWithoutAndroidView() {
        val img = codeOnly(imageSource())
        assertFalse(
            "不得再用 AndroidView 承载封面（LazyList 不复用 ⇒ fling 时逐行新建 View + 查库 + 请求）",
            img.contains("AndroidView")
        )
        assertFalse("不得再依赖 FilletImageView 承载圆角", img.contains("FilletImageView"))
        assertTrue("必须用 Compose Image 呈现", img.contains("asImageBitmap()") && img.contains("ContentScale.Crop"))
        assertTrue("圆角必须走 Compose clip", img.contains("clip(RoundedCornerShape(radiusDp.dp))"))
        assertTrue("必须用 loadBitmap 取 Bitmap", img.contains("ImageLoader.loadBitmap(context, image)"))
        assertTrue("请求生命周期必须托管在 CustomTarget", img.contains("CustomTarget<Bitmap>"))
        assertTrue(
            "组合离开必须取消请求（View 版依赖 View 回收，改 Compose 后必须显式清除，否则泄漏 target）",
            img.contains("Glide.with(context.applicationContext).clear(")
        )
        assertTrue("必须显式限制解码尺寸（替代 ImageView 自动尺寸探测）", img.contains("onSizeChanged"))
        // 2026-10-01 缺陷④：尺寸由「等首个非零测量后一次性取用」得到（key 收敛为 origin,link），
        // 故下发形态由 `(width, height)` 变为 `(size.width, size.height)`；语义不变（仍限制解码尺寸）
        assertTrue("解码尺寸必须下发给 Glide", img.contains("CustomTarget<Bitmap>(size.width, size.height)"))
        // 硬编码色红线同样适用于图片组件（本仓取色门禁口径）
        assertFalse("不得硬编码色值", Regex("0x[0-9A-Fa-f]{8}").containsMatchIn(img))
    }

    /**
     * AD-01 / AD-03 / AD-04 回归：列表翻页改由 `snapshotFlow` + 纯函数驱动，数据/在途/有下一页走
     * **State 入参**，key 预计算。同时锁死「回退为组合期 `derivedStateOf` 读 `layoutInfo`」。
     */
    @Test
    fun listPagingUsesSnapshotFlowWithStateInputs() {
        val s = codeOnly(listSource())
        assertTrue("翻页判定必须走 snapshotFlow", s.contains("snapshotFlow {"))
        assertTrue("判定必须调用纯函数", s.contains("RssPagingDecision.shouldLoadMore("))
        assertTrue("必须用 distinctUntilChanged 收敛重复事件", s.contains("distinctUntilChanged()"))
        // 数据入口必须是 State：普通参数下 `items.size` 变化不被 snapshotFlow 捕获 ⇒ 判定永久不重算
        assertTrue("items 必须为 State 入参", s.contains("itemsState: State<List<RssArticle>>"))
        assertTrue("isLoading 必须为 State 入参", s.contains("isLoadingState: State<Boolean>"))
        assertTrue("hasMore 必须为 State 入参", s.contains("hasMoreState: State<Boolean>"))
        // key 预计算（不得每次组合为每个条目重新拼接字符串）
        assertTrue("稳定 key 必须预计算", s.contains("remember(items) { items.map(RssArticleKey::of) }"))
        // 回退防线
        assertFalse("不得回退为组合期 derivedStateOf 读 layoutInfo", s.contains("derivedStateOf"))
        assertFalse("不得残留旧阈值写法（threshold 恒 0）", s.contains("PRELOAD_THRESHOLD else 0"))
    }

    @Test
    fun rowHasNoRippleAndFooterReusesView() {
        val s = listSource()
        // 原条目根 View 无 selectableItemBackground ⇒ 保持零按下反馈
        assertTrue("行点击必须关闭水波（indication = null）", s.contains("indication = null"))
        // 页脚沿用 View 侧 LoadMoreView（三态 + 错误详情弹窗 + 重试）
        assertTrue("页脚必须托管原 LoadMoreView", s.contains("factory = { loadMoreView }"))
    }

    @Test
    fun stateHolderNormalizesOutOfRangeStyle() {
        // 原 View 实现 `when (articleStyle) { … else -> RssArticlesAdapter }` 有回退路径；
        // 换成「按样式 new state」后，越界值必须同样回退到线性容器，否则列表侧 `linear!!` 直接 NPE
        // （导入的来源 JSON 可携带任意 articleStyle）。构造期 `check()` 会断言「三类容器恰有一个非空」。
        val unknown = RssArticleListStateHolder(7)
        assertEquals("越界样式必须归一为 0", 0, unknown.normalizedStyle)
        assertNotNull("越界样式必须回退到线性列表容器", unknown.linear)
        assertNull(unknown.grid)
        assertNull(unknown.staggered)
        // 5 种在用样式逐一的容器分派（构造期不变量亦在此被验证）
        val expectedKind = mapOf(0 to 0, 1 to 0, 2 to 1, 3 to 2, 4 to 1)
        expectedKind.forEach { (style, kind) ->
            val holder = RssArticleListStateHolder(style)
            val actual = when {
                holder.linear != null -> 0
                holder.grid != null -> 1
                holder.staggered != null -> 2
                else -> -1
            }
            assertEquals("样式 $style 的容器分派不符（0=线性/1=定列网格/2=瀑布流）", kind, actual)
        }
    }

    @Test
    fun waterfallUnknownRatioFallsBackToSquareNotUnbounded() {
        // 2026-09-26 真机实测（cold cache）：比例未知时若「不加高度约束」，AndroidView 在瀑布流的
        // 无界高度下会塌成极端高度，且 ImageView 拿不到尺寸 ⇒ Glide 请求永不完成、比例永远学不到。
        // 原 View 实现的比例未知态 = WRAP_CONTENT + adjustViewBounds + 1:1 占位图（正方）⇒ 等价正方容器。
        val s = listSource()
        assertTrue(
            "比例未知时必须回退正方形容器（不得无高度约束）",
            s.contains(".aspectRatio(if (ratio > 0f) 1f / ratio else 1f)")
        )
    }

    @Test
    fun favoritesListReusesArticleRowSingleSource() {
        val fav = favoritesSource()
        assertTrue("收藏行必须复用文章样式 0 行单源", fav.contains("RssArticleListRow("))
        assertTrue("收藏封面取数必须走收藏表", fav.contains("appDb.rssStarDao.getImage(origin, link)"))
        assertTrue("长按删除语义必须保留", fav.contains("onLongClick = { onItemLongClick(star) }"))
    }
}