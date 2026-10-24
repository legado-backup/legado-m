package io.legado.app.ui.video

import io.legado.app.help.video.EpisodePager
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-legacy-parity-hls AD-01/AD-02：传统模式选集统一走分组弹框（含倒序）的接线锁定。
 *
 * 结构断言确保「平铺列表真的停用了」；行为断言用 [EpisodePager] 的期望值锁定倒序映射，
 * 避免只测源码文本。
 */
class VideoLegacyEpisodePickerWiringTest {

    private val legacy = SourceFileProbe.sourceText("ui/video/VideoPlayerActivity.kt")

    @Test
    fun legacyNoLongerBindsFlatEpisodeLists() {
        // 书源平铺（ChapterAdapter 绑定 toc）与订阅源平铺（RssEpisodeAdapter）都不应再出现
        assertFalse(legacy.contains("ChapterAdapter(toc"))
        assertFalse(legacy.contains("RssEpisodeAdapter("))
        // 选集入口仍指向分组弹框
        assertTrue(legacy.contains("showEpisodePicker()"))
        assertTrue(legacy.contains("tvEpisodeLabel.setOnClickListener"))
    }

    @Test
    fun descendingOrderIsSharedWithDialog() {
        // 倒序能力随 ChoiceEpisodeDialog 共享：分组展示顺序在倒序时为升序结果的完全反转
        val asc = EpisodePager.displayGroupOrder(3, false)
        val desc = EpisodePager.displayGroupOrder(3, true)
        assertEquals(3, asc.size)
        assertEquals(asc.reversed(), desc)
    }

    @Test
    fun groupIndicesMapBackToRealEpisodeOrder() {
        // 组内下标：倒序时同样为升序反转，点击仍回传真实集号（AD-02）
        val paging = EpisodePager.build(total = 7, currentIndex = 0)
        val group = paging.groups.first()
        val asc = EpisodePager.displayIndices(group, false)
        val desc = EpisodePager.displayIndices(group, true)
        assertEquals(asc.reversed(), desc)
        assertEquals(asc.first(), group.startIndex)
    }
}
