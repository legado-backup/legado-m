package io.legado.app.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R7 / V4：自动连播语义（「当前视频下一集」）。
 *
 * 回归护栏：历史实现对末集播完会 `switchToBookFromList` 跨影片续播；
 * 新语义要求停在末集并给提示，跨影片只能由用户主动上/下滑触发。
 */
class VideoPlayLastEpisodePolicyTest {

    @Test
    fun advancesWithinEpisodeRange() {
        assertTrue(VideoPlay.shouldAdvanceEpisode(1, 12))
        assertTrue(VideoPlay.shouldAdvanceEpisode(11, 12))
    }

    @Test
    fun stopsAtLastEpisode() {
        assertFalse("末集之后不得再前进", VideoPlay.shouldAdvanceEpisode(12, 12))
        assertFalse(VideoPlay.shouldAdvanceEpisode(13, 12))
    }

    @Test
    fun rejectsInvalidTotals() {
        assertFalse("空目录不得前进", VideoPlay.shouldAdvanceEpisode(0, 0))
        assertFalse("负总数不得前进", VideoPlay.shouldAdvanceEpisode(0, -3))
    }
}
