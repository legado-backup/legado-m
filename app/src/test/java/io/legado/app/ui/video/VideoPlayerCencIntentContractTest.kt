package io.legado.app.ui.video

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 直连播放 × CENC 残留清理契约（AD-05）
 *
 * 直连 URL（Intent 带 videoUrl）本身不携带 DRM 声明，进入新会话必须先清空上一集残留；
 * 无 videoUrl（嗅探链路）不在此处清理，由采集链入口负责。
 */
class VideoPlayerCencIntentContractTest {

    @Test
    fun clearWhenIntentCarriesDirectUrl() {
        assertTrue(shouldClearCencForDirectUrl("file:///tmp/a.mp4"))
        assertTrue(shouldClearCencForDirectUrl("https://v.example/a.mp4"))
    }

    @Test
    fun keepWhenNoDirectUrl() {
        assertFalse(shouldClearCencForDirectUrl(null))
        assertFalse(shouldClearCencForDirectUrl(""))
        assertFalse(shouldClearCencForDirectUrl("   "))
    }
}
