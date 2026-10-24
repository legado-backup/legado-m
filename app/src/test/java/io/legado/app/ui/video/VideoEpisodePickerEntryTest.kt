package io.legado.app.ui.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R7 / V4：选集弹框入口可见性。
 *
 * 书源与订阅源双轨都必须能进分组选集；单集不展示入口（避免无操作的空弹框）。
 */
class VideoEpisodePickerEntryTest {

    @Test
    fun bookSourceMultiEpisodeShowsEntry() {
        assertTrue(VideoPlayerActivity.shouldOfferEpisodePicker(bookEpisodeCount = 24, rssEpisodeCount = 0))
    }

    @Test
    fun rssMultiEpisodeShowsEntry() {
        assertTrue(VideoPlayerActivity.shouldOfferEpisodePicker(bookEpisodeCount = 0, rssEpisodeCount = 36))
    }

    @Test
    fun singleEpisodeHidesEntry() {
        assertFalse(VideoPlayerActivity.shouldOfferEpisodePicker(1, 0))
        assertFalse(VideoPlayerActivity.shouldOfferEpisodePicker(0, 1))
        assertFalse(VideoPlayerActivity.shouldOfferEpisodePicker(0, 0))
    }

    @Test
    fun indicatorIndexFollowsSessionKind() {
        // 书源会话：章节索引是唯一权威（与左下角标题同源），不得用 rss 索引
        assertEquals(
            3,
            episodeIndicatorIndex(
                bookSession = true,
                chapterInVolumeIndex = 3,
                rssEpisodeIndex = 7,
            ),
        )
        // 订阅源会话：用集索引
        assertEquals(
            7,
            episodeIndicatorIndex(
                bookSession = false,
                chapterInVolumeIndex = 3,
                rssEpisodeIndex = 7,
            ),
        )
    }

    @Test
    fun secondaryEntriesHiddenInFullscreen() {
        // R10 / V6：右侧 7 个按钮在横屏全屏放不下 ⇒ 全屏只保留全屏/听视频/设置
        assertFalse(secondaryEntriesVisible(isFullscreen = true))
        assertTrue(secondaryEntriesVisible(isFullscreen = false))
    }

    @Test
    fun refreshEntryVisibleForBookSourceSessions() {
        // R6：书源视频会话（有书）与订阅源会话都显示刷新；单 URL 直链不显示
        assertTrue(VideoPlayerActivity.shouldShowRefresh(false, sourceIsBookSource = true, hasBook = true))
        assertFalse("书源会话尚未加载出书时不显示", VideoPlayerActivity.shouldShowRefresh(false, true, false))
        assertTrue(VideoPlayerActivity.shouldShowRefresh(true, false, false))
        assertFalse("无采集链的直链会话不显示", VideoPlayerActivity.shouldShowRefresh(false, false, true))
    }
}
