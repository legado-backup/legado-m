package io.legado.app.help.gsyVideo

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache / m3u8 加密清单修复：HLS key 请求的 Referer 兜底必须同时接在
 * GSY 的两条 HLS 入口（管理器 prepare 前 + MediaSource 构建前）。
 */
class HlsRefererHeaderWiringTest {

    private val manager = SourceFileProbe.sourceText("help/gsyVideo/ExoPlayerManager.kt")
    private val player = SourceFileProbe.sourceText("help/gsyVideo/Exo2MediaPlayer.kt")

    @Test
    fun managerInjectsHlsRefererBeforePrepare() {
        assertEquals(true, manager.contains("headersWithHlsReferer(baseHeaders"))
        assertEquals(true, manager.contains("ExoPlayerHelper.setDefaultHeaders(effectiveHeaders)"))
    }

    @Test
    fun mediaSourceBuildInjectsHlsRefererWithOriginalUrl() {
        assertEquals(true, player.contains("headersWithHlsReferer(currentHeaders, url)"))
        // 必须用原始清单 URL（站点校验代理域），不能用重定向后的 CDN 地址
        assertEquals(false, player.contains("headersWithHlsReferer(currentHeaders, effectiveUrl)"))
    }
}
