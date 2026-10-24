package io.legado.app.help.video

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 2026-10-24 回归修复配套测试：
 * - 无扩展名媒体直链（CDN path 不带 `.mp4`）靠 Content-Type 判直连，必须只认以 video/ 开头的类型；
 * - 同时锁定「扩展名快速路径判不出这类 URL」的既有事实，防止有人误以为它已被覆盖。
 */
class VideoUrlExtractorContentTypeTest {

    @Test
    fun videoContentTypeIsDirectMedia() {
        assertTrue(VideoUrlExtractor.isVideoContentType("video/mp4"))
        assertTrue(VideoUrlExtractor.isVideoContentType("Video/MP4; charset=binary"))
        assertTrue(VideoUrlExtractor.isVideoContentType("video/webm"))
    }

    @Test
    fun nonVideoContentTypeIsNotDirectMedia() {
        assertFalse(VideoUrlExtractor.isVideoContentType(null))
        assertFalse(VideoUrlExtractor.isVideoContentType(""))
        assertFalse(VideoUrlExtractor.isVideoContentType("text/html; charset=utf-8"))
        assertFalse(VideoUrlExtractor.isVideoContentType("application/json"))
        // HLS 清单由扩展名快速路径处理，这里不能误判为直链
        assertFalse(VideoUrlExtractor.isVideoContentType("application/vnd.apple.mpegurl"))
    }

    @Test
    fun extensionlessCdnUrlIsNotRecognizedBySuffixRule() {
        assertFalse(
            VideoUrlExtractor.isDirectVideoStreamUrl(
                "https://cdn.example.com/video/tos/cn/abc123/xyz"
            )
        )
    }
}
