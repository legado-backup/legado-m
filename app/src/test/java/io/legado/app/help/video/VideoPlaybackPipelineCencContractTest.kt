package io.legado.app.help.video

import android.app.Application
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * 书源 CENC 契约解析单测（AD-05）：`ruleContent` 返回 `{url,kid,encryption}` 时拆包；
 * 普通字符串/MPD 文本/非 http 地址一律返回 null（保持原播放路径，绝不误判）。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class VideoPlaybackPipelineCencContractTest {

    private val kid = "0123456789abcdef0123456789abcdef"

    @Test
    fun parsesCencDeclaration() {
        val triple = VideoPlaybackPipeline.parseCencContent(
            """{"url":"https://v.example/a.mp4","kid":"$kid","encryption":"cenc-aes-ctr"}"""
        )
        assertEquals("https://v.example/a.mp4", triple?.first)
        assertEquals(kid, triple?.second)
        assertEquals("cenc-aes-ctr", triple?.third)
    }

    @Test
    fun missingKidOrEncryption_isTolerated() {
        val triple = VideoPlaybackPipeline.parseCencContent("""{"url":"https://v.example/a.mp4"}""")
        assertEquals("https://v.example/a.mp4", triple?.first)
        assertNull(triple?.second)
        assertNull(triple?.third)
    }

    @Test
    fun rejectsNonHttpAndJunk() {
        assertNull(VideoPlaybackPipeline.parseCencContent("""{"url":"file:///tmp/a.mp4","kid":"$kid"}"""))
        assertNull(VideoPlaybackPipeline.parseCencContent("https://v.example/a.mp4"))
        assertNull(VideoPlaybackPipeline.parseCencContent(""))
        assertNull(VideoPlaybackPipeline.parseCencContent("<mpd>text</mpd>"))
    }
}
