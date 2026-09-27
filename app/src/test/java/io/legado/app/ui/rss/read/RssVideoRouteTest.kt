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
}