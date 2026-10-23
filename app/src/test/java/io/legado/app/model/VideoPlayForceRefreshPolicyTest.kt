package io.legado.app.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep AD-06：视频书源不得复用旧播放地址的判定真值表。
 */
class VideoPlayForceRefreshPolicyTest {

    @Test
    fun `video source without local cache must refresh`() {
        assertTrue(VideoPlay.shouldForceRefreshVideo(isVideoSource = true, hasLocal = false))
    }

    @Test
    fun `video source with local cache must not refresh`() {
        assertFalse(VideoPlay.shouldForceRefreshVideo(isVideoSource = true, hasLocal = true))
    }

    @Test
    fun `non video source keeps legacy short circuit`() {
        assertFalse(VideoPlay.shouldForceRefreshVideo(isVideoSource = false, hasLocal = false))
        assertFalse(VideoPlay.shouldForceRefreshVideo(isVideoSource = false, hasLocal = true))
    }
}
