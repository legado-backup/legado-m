package io.legado.app.ui.rss.read

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * REQ-11 / REQ-12（tasks 2.2 / 2.3）：`<video>` 自动转播放器的**路由与接线**不变量。
 *
 * 三条易失守约定：
 * ① 播放上下文必须有**单一写入点** `ReadRss.prepareVideoPlayContext`（三处调用点各写一遍必漂移）；
 * ② 检测必须作用于 **ruleContent 解析后的正文**，且在 **落库前** 判定、**不阻断落库**（§14.2 T2 防火墙）；
 * ③ 开关 `rssAutoVideoToPlayer` 必须有**双入口**（阅读菜单 + 设置页）。
 */
class RssVideoRouteTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val readRss by lazy { read("src/main/java/io/legado/app/ui/rss/read/ReadRss.kt") }
    private val viewModel by lazy { read("src/main/java/io/legado/app/ui/rss/read/ReadRssViewModel.kt") }
    private val activity by lazy { read("src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt") }

    @Test
    fun videoPlayContextHasSingleWriter() {
        assertTrue(
            "单一写入点须存在",
            readRss.contains("fun prepareVideoPlayContext(")
        )
        val calls = Regex("prepareVideoPlayContext\\(").findAll(readRss).count()
        assertTrue("两条既有路由均须改走单一写入点（实得 $calls 处含定义，期望 ≥ 3）", calls >= 3)
        assertEquals(
            "VideoPlay.rssArticles 只允许在单一写入点内赋值一次（散落直写会绕过单源）",
            1,
            Regex("""VideoPlay\.rssArticles\s*=""").findAll(readRss).count()
        )
    }

    @Test
    fun detectionRunsOnParsedBodyAndDoesNotBlockPersistence() {
        assertTrue(
            "检测须使用解析后正文入口 detectVideoInBody",
            viewModel.contains("RssVideoDetector.detectVideoInBody(body)")
        )
        val detectAt = viewModel.indexOf("detectVideoInBody(body)")
        val insertAt = viewModel.indexOf("appDb.rssArticleDao.insert(rssArticle)", detectAt)
        assertTrue("落库仍须发生（防火墙：不阻断落库）", insertAt > detectAt)
        assertFalse(
            "命中分支不得 return（否则阻断落库）",
            viewModel.substring(detectAt, insertAt).contains("return@")
        )
    }

    @Test
    fun detectionIsGatedBySwitchAndLogsDecision() {
        assertTrue(
            "检测须受开关 gating",
            viewModel.contains("AppConfig.rssAutoVideoToPlayer")
        )
        assertTrue(
            "须留一行可定位诊断日志（用户要求）",
            viewModel.contains("RssVideoDetect: 开关=")
        )
        val logStart = viewModel.indexOf("RssVideoDetect: 开关=")
        val logBlock = viewModel.substring(logStart, viewModel.indexOf("if (detected)", logStart))
        assertTrue(
            "诊断日志须以文章 hash 指代（输出安全：不落 URL）",
            logBlock.contains("articleHash=") && logBlock.contains("hashCode()")
        )
        assertFalse(
            "诊断日志不得直接落文章 URL",
            logBlock.contains("rssArticle.link}")
        )
    }

    @Test
    fun switchHasDualEntries() {
        assertTrue(
            "阅读菜单入口须存在",
            activity.contains("AppConfig.rssAutoVideoToPlayer = !AppConfig.rssAutoVideoToPlayer")
        )
        assertTrue(
            "设置页入口须存在（发现与订阅）",
            read("src/main/java/io/legado/app/ui/config/DiscoverySubscriptionConfigFragment.kt")
                .contains("key = PreferKey.rssAutoVideoToPlayer")
        )
    }

    @Test
    fun startsPlayerWithUniformExtras() {
        val detects = Regex("""appCtx\.startActivity<VideoPlayerActivity>""").findAll(viewModel).count()
        assertEquals("ViewModel 侧启动播放器须恰为一处", 1, detects)
        listOf("sourceKey", "sourceType", "record", "videoTitle").forEach { extra ->
            assertTrue(
                "播放器 extras「$extra」须齐备",
                viewModel.contains("""putExtra("$extra",""")
            )
        }
    }

    /**
     * W1 2.2 真机缺陷回归（2026-09-27 L2 实证）：
     *
     * 现象：自动路由**进了播放器但不播** —— 真机日志 `VideoPlay: rssArticle is null in startPlay`。
     * 根因：VM 侧路由只有「单篇文章」上下文（没有列表），若原样写入 `rssArticles = null`，
     * `VideoPlay.startPlay` 的解析式 `rssStar ?: rssRecord ?: rssArticles?.getOrNull(index)`
     * 三项全空 ⇒ 静默 `return`（既不报错也不播）。
     *
     * 约定：单一写入点必须保证播放器侧**可解析到文章**（无列表时兜底为「仅含本篇」的列表）。
     */
    @Test
    fun playContextMustBeResolvableByPlayer() {
        val write = Regex("""VideoPlay\.rssArticles\s*=\s*([^\n]+)""").find(readRss)
        assertTrue("未找到 rssArticles 赋值", write != null)
        val rhs = write!!.groupValues[1]
        assertTrue(
            "rssArticles 不得裸写 null（否则播放器侧 rssArticle 解析失败 ⇒ 进了播放器不播）：实际写入「$rhs」",
            !rhs.trim().startsWith("rssArticles") || rhs.contains("?:")
        )
    }

    /**
     * 2026-09-27 用户报障回归（严重）：**自动路由必须携带文章列表上下文**。
     *
     * 现象：视频订阅源在自由布局/传统式下「沉浸式上滑下滑切上一个下一个视频」全部失效。
     * 根因：本路由只传单篇文章 ⇒ 单一写入点内 W2 的兜底 `?: listOf(rssArticle)` 把列表
     * 退化为 **1 篇** ⇒ 播放器侧 `VideoFragment.isArticleMode`（`size > 1`）与
     * `VideoPlayerActivity` 的 `hasPrev/hasNext` 同时为假 ⇒ 手势与按钮双失效。
     *
     * 约定：命中分支必须按列表页同口径（同源 + 同分类）补齐列表，并保证**含本篇**
     * （判定早于落库，首读文章可能尚未入库；缺了会兜底 index=0 指向别的文章）。
     */
    @Test
    fun autoRouteMustCarryArticleListContextForSwipe() {
        val detectAt = viewModel.indexOf("if (detected)")
        assertTrue("未找到 detected 分支", detectAt > 0)
        val startAt = viewModel.indexOf("startActivity<VideoPlayerActivity>", detectAt)
        assertTrue("未找到检测分支内的播放器启动点", startAt > detectAt)
        val block = viewModel.substring(detectAt, startAt)
        assertTrue(
            "命中分支必须补齐同源同分类文章列表（单篇会击穿 size>1 的文章模式判定）",
            block.contains("getListByOriginSort")
        )
        assertTrue(
            "必须保证列表含本篇（否则索引兜底 0 指向别的文章）",
            block.contains("none { it.link == rssArticle.link }")
        )
        assertTrue(
            "补齐后的列表须显式传入单一写入点",
            Regex("""prepareVideoPlayContext\([\s\S]*?rssArticles\s*=\s*contextArticles""")
                .containsMatchIn(block)
        )
    }
}