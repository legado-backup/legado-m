package io.legado.app.help.rss

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * REQ-11 / AD-18：订阅正文 `<video>` 检测 单测。
 *
 * 用户口径（2026-09-27）：「内容规则**解析后**可能有视频标签，而不是刚开始就有的情况」
 * ⇒ 检测入口 [RssVideoDetector.detectVideoInBody] 必须同时覆盖两种**解析后**形态：
 * ① 含 `<video>` 标签的 HTML 片段；② 规则直抽的**直链视频地址**（无标签）。
 *
 * 覆盖点：MIN/MAX 长度边界、标签识别、直链识别、误判防线（裸单词 video / 普通 HTML）、异常安全。
 */
class RssVideoDetectTest {

    private fun htmlOf(len: Int, prefix: String = "", suffix: String = ""): String {
        val filler = "x".repeat((len - prefix.length - suffix.length).coerceAtLeast(0))
        return prefix + filler + suffix
    }

    // ---------- MIN_VIDEO_SCAN_LEN 边界 ----------

    @Test
    fun belowMinLengthIsSkippedEvenWithVideoTag() {
        // 长度 < MIN ⇒ 直接跳过（含 <video> 也不算命中）
        val short = "<video src=\"a.mp4\"></video>"
        assertTrue("前置条件：样本短于 MIN", short.length < RssVideoDetector.MIN_VIDEO_SCAN_LEN)
        assertFalse(RssVideoDetector.detectVideoInHtml(short))
        assertFalse(RssVideoDetector.detectVideoInBody(short))
    }

    @Test
    fun atMinLengthVideoTagIsDetected() {
        val prefix = "<video src=\"a.mp4\"></video>"
        val sample = htmlOf(RssVideoDetector.MIN_VIDEO_SCAN_LEN, prefix)
        assertTrue(sample.length >= RssVideoDetector.MIN_VIDEO_SCAN_LEN)
        assertTrue(RssVideoDetector.detectVideoInHtml(sample))
    }

    // ---------- MAX_VIDEO_SCAN_LEN 边界 ----------

    @Test
    fun videoTagBeyondMaxScanWindowIsMissedByDesign() {
        // 文档口径：超长**截断后**再解析 ⇒ 标签落在截断区之外时不命中（如实锁定该已知边界）
        val prefix = htmlOf(RssVideoDetector.MAX_VIDEO_SCAN_LEN + 10)
        val sample = prefix + "<video src=\"a.mp4\"></video>"
        assertFalse(RssVideoDetector.detectVideoInHtml(sample))
    }

    @Test
    fun videoTagInsideScanWindowIsDetectedForVeryLongBody() {
        val sample = "<video src=\"a.mp4\"></video>" + htmlOf(RssVideoDetector.MAX_VIDEO_SCAN_LEN + 100)
        assertTrue(sample.length > RssVideoDetector.MAX_VIDEO_SCAN_LEN)
        assertTrue(RssVideoDetector.detectVideoInHtml(sample))
    }

    // ---------- 标签形态与误判防线 ----------

    @Test
    fun videoTagVariantsAreDetected() {
        val long = """<div class="p">""" + htmlOf(300)
        listOf(
            """<video src="a.mp4">""",
            """<VIDEO controls>""",
            """<video/>""",
            """<video 
            poster="x">"""
        ).forEach { tag ->
            assertTrue("应命中标签形态: $tag", RssVideoDetector.detectVideoInHtml(tag + long))
        }
    }

    @Test
    fun plainWordVideoInArticleIsNotDetected() {
        // 影评里出现单词 video 不应触发跳转
        val sample = "这部电影的 video 剪辑很棒，" + htmlOf(400)
        assertFalse(RssVideoDetector.detectVideoInHtml(sample))
    }

    @Test
    fun blankOrNullIsNotDetected() {
        assertFalse(RssVideoDetector.detectVideoInBody(null))
        assertFalse(RssVideoDetector.detectVideoInBody(""))
        assertFalse(RssVideoDetector.detectVideoInBody("   "))
        assertFalse(RssVideoDetector.detectVideoInHtml(null))
    }

    // ---------- 规则直抽的直链地址（解析后无标签形态） ----------

    @Test
    fun directVideoUrlIsDetectedWithoutAnyTag() {
        listOf(
            "https://cdn.example.com/a/b/index.m3u8",
            "https://cdn.example.com/v.mp4",
            "http://cdn.example.com/a.flv",
            "https://cdn.example.com/x.m3u8?sign=abc&t=1"
        ).forEach { url ->
            assertTrue("直链应命中: $url", RssVideoDetector.looksLikeDirectVideoUrl(url))
            assertTrue("入口应命中: $url", RssVideoDetector.detectVideoInBody(url))
        }
    }

    @Test
    fun nonVideoTextOrHtmlIsNotTreatedAsDirectUrl() {
        listOf(
            "https://example.com/article.html",
            "https://example.com/page?id=1",
            "这是一段普通正文 https://cdn.example.com/v.mp4 夹在中间",
            "<p>https://cdn.example.com/v.mp4</p>",
            "https://example.com/" + "a".repeat(2100) + ".mp4"
        ).forEach { body ->
            assertFalse("不应判为直链: ${body.take(40)}…", RssVideoDetector.looksLikeDirectVideoUrl(body))
        }
    }

    @Test
    fun detectionNeverThrowsOnHostileInput() {
        val hostile = listOf("\u0000\u0001", "\uD800", "a".repeat(10_000) + "<video")
        hostile.forEach { input ->
            kotlin.runCatching { RssVideoDetector.detectVideoInBody(input) }
                .onFailure { throw AssertionError("检测不得抛异常: $it") }
        }
    }
}