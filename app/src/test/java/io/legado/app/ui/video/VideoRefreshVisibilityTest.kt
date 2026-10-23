package io.legado.app.ui.video

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep AD-08：刷新入口按能力判定（订阅源 / 书源章节会话均可见）。
 */
class VideoRefreshVisibilityTest {

    @Test
    fun `rss article session always shows refresh`() {
        assertTrue(VideoPlayerActivity.shouldShowRefresh(true, false, false))
        assertTrue(VideoPlayerActivity.shouldShowRefresh(true, true, true))
    }

    @Test
    fun `book source chapter session shows refresh only with a bound book`() {
        assertTrue(VideoPlayerActivity.shouldShowRefresh(false, true, true))
        assertFalse(VideoPlayerActivity.shouldShowRefresh(false, true, false))
    }

    @Test
    fun `single url session hides refresh`() {
        assertFalse(VideoPlayerActivity.shouldShowRefresh(false, false, false))
    }
}
