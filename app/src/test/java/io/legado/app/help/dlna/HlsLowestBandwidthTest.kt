package io.legado.app.help.dlna

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * AD-16「流畅优先」：master 清单只保留最低带宽变体 —— 纯逻辑单测。
 */
class HlsLowestBandwidthTest {

    @Test
    fun `多码率只保留最低带宽变体`() {
        val master = listOf(
            "#EXTM3U",
            "#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1920x1080",
            "1080/index.m3u8",
            "#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=1280x720",
            "720/index.m3u8",
            "#EXT-X-STREAM-INF:BANDWIDTH=300000",
            "480/index.m3u8"
        ).joinToString("\n")

        val out = HlsPlaylistRewriter.keepLowestBandwidth(master)

        assertTrue("最低带宽变体应保留", out.contains("480/index.m3u8"))
        assertFalse("高码率变体应被剔除", out.contains("1080/index.m3u8"))
        assertFalse("中码率变体应被剔除", out.contains("720/index.m3u8"))
        assertTrue("头部标签保留", out.startsWith("#EXTM3U"))
    }

    @Test
    fun `行内URI形态同样参与筛选`() {
        val master = listOf(
            "#EXTM3U",
            "#EXT-X-STREAM-INF:BANDWIDTH=1500000,URI=\"high/index.m3u8\"",
            "#EXT-X-STREAM-INF:BANDWIDTH=400000,URI=\"low/index.m3u8\""
        ).joinToString("\n")

        val out = HlsPlaylistRewriter.keepLowestBandwidth(master)

        assertTrue(out.contains("low/index.m3u8"))
        assertFalse(out.contains("high/index.m3u8"))
    }

    @Test
    fun `非master清单原样返回`() {
        val media = listOf(
            "#EXTM3U",
            "#EXT-X-TARGETDURATION:4",
            "#EXTINF:4.0,",
            "seg1.ts",
            "#EXTINF:4.0,",
            "seg2.ts"
        ).joinToString("\n")

        assertEquals(media, HlsPlaylistRewriter.keepLowestBandwidth(media))
    }

    @Test
    fun `只有一个变体时原样返回`() {
        val single = listOf(
            "#EXTM3U",
            "#EXT-X-STREAM-INF:BANDWIDTH=900000",
            "only/index.m3u8"
        ).joinToString("\n")

        assertEquals(single, HlsPlaylistRewriter.keepLowestBandwidth(single))
    }

    @Test
    fun `CRLF 行尾不破坏筛选`() {
        val master = "#EXTM3U\r\n" +
            "#EXT-X-STREAM-INF:BANDWIDTH=2000000\r\n" +
            "high.m3u8\r\n" +
            "#EXT-X-STREAM-INF:BANDWIDTH=500000\r\n" +
            "low.m3u8\r\n"

        val out = HlsPlaylistRewriter.keepLowestBandwidth(master)

        assertTrue(out.contains("low.m3u8"))
        assertFalse(out.contains("high.m3u8"))
    }
}