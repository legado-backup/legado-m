package io.legado.app.model

import android.app.Application
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * CENC 会话状态机单测（AD-05/AD-07）：`clearCenc()` 必须一次清空 kid/encryption/声明地址，
 * 否则跨集/换源会把上一集 DRM 状态串到新播放（复用实例场景曾因此误判加密轨）。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class VideoPlayCencStateTest {

    @Test
    fun clearCenc_resetsAllDeclarationFields() {
        VideoPlay.cencKid = "0123456789abcdef0123456789abcdef"
        VideoPlay.cencEncryption = "cenc-aes-ctr"
        VideoPlay.cencUrl = "https://example.com/v/1.mp4"

        VideoPlay.clearCenc()

        assertNull(VideoPlay.cencKid)
        assertNull(VideoPlay.cencEncryption)
        assertNull(VideoPlay.cencUrl)
    }

    @Test
    fun declarationFields_areIndependentOfPlayUrl() {
        VideoPlay.videoUrl = "file:///tmp/decrypted.mp4"
        VideoPlay.cencKid = "0123456789abcdef0123456789abcdef"
        VideoPlay.cencEncryption = "cenc-aes-ctr"

        assertEquals("file:///tmp/decrypted.mp4", VideoPlay.videoUrl)
        assertEquals("cenc-aes-ctr", VideoPlay.cencEncryption)

        VideoPlay.clearCenc()
        assertEquals("file:///tmp/decrypted.mp4", VideoPlay.videoUrl)
        assertNull(VideoPlay.cencKid)
    }
}
