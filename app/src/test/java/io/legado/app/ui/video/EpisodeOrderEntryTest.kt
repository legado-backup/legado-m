package io.legado.app.ui.video

import io.legado.app.help.video.EpisodePager
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 视频详情抽屉的「正序 / 倒序」与高亮跟随（2026-10-24 用户需求 + 真机实证）。
 *
 * 书源视频有两个选集入口，[VideoBookDetailSheet] 是其中一个（点播放器标题打开）。
 * 真机实证两处缺陷：
 * 1. 集数列表没有排序按钮（86 集只能从头翻）；
 * 2. 抽屉打开期间自动连播到第 81 集，高亮还停在第 73 集（文案与高亮不一致）。
 */
class EpisodeOrderEntryTest {

    private val detailSheet = SourceFileProbe.sourceText("ui/video/VideoBookDetailSheet.kt")
    private val playerActivity = SourceFileProbe.sourceText("ui/video/VideoPlayerActivity.kt")

    @Test
    fun detailSheetHasOrderToggle() {
        assertTrue(
            "详情抽屉的集数列表需要正序/倒序",
            detailSheet.contains("var descending by remember { mutableStateOf(false) }") &&
                detailSheet.contains("episodes.asReversed()")
        )
    }

    @Test
    fun reversedClickKeepsRealIndex() {
        assertTrue(
            "倒序展示下点击按原始下标（rawIndex）派发，避免点错集",
            detailSheet.contains("val rawIndex = if (descending) episodes.lastIndex - displayIndex") &&
                detailSheet.contains("onDetailEpisodeSelected(rawIndex, episode)")
        )
        assertFalse(
            "不得再用按标题/位置查找的下标（倒序时会错）",
            detailSheet.contains("episodes.indexOf(episode)")
        )
        // 行为期望值：86 集倒序时，第 1 格是第 86 集（原始下标 85），第 6 格是第 81 集（80）
        val episodes = List(86) { it }
        fun rawIndexOf(displayIndex: Int, descending: Boolean) =
            if (descending) episodes.lastIndex - displayIndex else displayIndex
        assertEquals(85, rawIndexOf(0, true))
        assertEquals(80, rawIndexOf(5, true))
        assertEquals(0, rawIndexOf(0, false))
    }

    @Test
    fun highlightFollowsPlaybackProgress() {
        assertTrue(
            "高亮必须按播放进度轮询刷新",
            detailSheet.contains("currentEpisode = currentEpisodeIndex()") &&
                detailSheet.contains("CURRENT_EPISODE_POLL_MS")
        )
        assertTrue(
            "书源会话当前集权威字段是 chapterInVolumeIndex（rssEpisodeIndex 会错位一集）",
            detailSheet.contains("VideoPlay.chapterInVolumeIndex.coerceIn(0, count - 1)")
        )
    }

    @Test
    fun highlightComparesRealIndexNotTitle() {
        assertFalse(
            "高亮不得再按集标题文本比较（自动连播后会停留在旧集）",
            detailSheet.contains("episode.title == VideoPlay.rssEpisodes")
        )
        assertTrue(
            "高亮必须与真实下标比较",
            detailSheet.contains("val selected = rawIndex == currentEpisode")
        )
    }

    @Test
    fun groupLabelSemanticsMatchPager() {
        // 与分组弹框共用同一套顺序语义（避免两处入口表现不一致）
        val group = EpisodePager.Group(startIndex = 80, endIndex = 85)
        assertEquals("86-81", EpisodePager.displayLabel(group, descending = true))
        assertEquals(85, EpisodePager.displayIndices(group, descending = true).first())
    }

    /** 播放器侧必须把「实时当前集」注入弹框，否则弹框只能靠打开时的快照高亮。 */
    @Test
    fun playerInjectsLiveSelectionIntoPicker() {
        assertTrue(
            "选集入口必须注入实时集下标提供器",
            playerActivity.contains("val liveIndex = {") &&
                playerActivity.contains("VideoPlay.chapterInVolumeIndex")
        )
        assertTrue(
            "提供器必须作为最后一个参数传给弹框",
            playerActivity.contains("currentIndex,") && playerActivity.contains("liveIndex")
        )
    }
}
