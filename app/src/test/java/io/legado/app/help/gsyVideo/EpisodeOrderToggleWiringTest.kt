package io.legado.app.help.gsyVideo

import io.legado.app.help.video.EpisodePager
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 分组选集弹框「正序 / 倒序」接线（2026-10-24 用户需求）。
 *
 * 需求原文：「选集弹框为什么不来个倒序正序按钮呢？」——
 * 86 集长剧要从最新集往回找时必须一直翻到底，故头部提供一键切换。
 *
 * 硬约束：切换只改**展示顺序**，点击回传的必须是真实**全集下标**（否则会播错集）。
 */
class EpisodeOrderToggleWiringTest {

    private val dialog = SourceFileProbe.sourceText("help/gsyVideo/ChoiceEpisodeDialog.kt")
    private val layout =
        SourceFileProbe.sourceTextByPath("src/main/res/layout/switch_episode_video_dialog.xml")

    @Test
    fun layoutHasOrderToggleView() {
        assertTrue(
            "头部必须有排序按钮视图",
            layout.contains("android:id=\"@+id/order_toggle\"")
        )
        assertEquals(
            "按钮必须可点击（TextView 默认不可点击）",
            true,
            layout.contains("android:clickable=\"true\"")
        )
    }

    @Test
    fun dialogBindsToggleAndFlipsOrder() {
        assertTrue(
            "弹框必须绑定排序按钮",
            dialog.contains("orderToggle = view.findViewById(R.id.order_toggle)")
        )
        assertTrue(
            "点击必须翻转展示顺序并重排分组与网格",
            dialog.contains("descending = !descending") &&
                dialog.contains("renderGroups()") &&
                dialog.contains("renderGrid()")
        )
    }

    @Test
    fun gridIndicesUseDisplayIndicesWhenReversed() {
        assertTrue(
            "网格下标必须经 displayIndices 映射",
            dialog.contains("EpisodePager.displayIndices(group, descending)")
        )
        assertFalse(
            "不得再硬编码 startIndex + positionInGroup（倒序会点错集）",
            dialog.contains("val fullIndex = group.startIndex + positionInGroup")
        )
        // 行为期望值：倒序时第一个格子必须是该组最后一集
        val group = EpisodePager.Group(startIndex = 70, endIndex = 79)
        assertEquals(79, EpisodePager.displayIndices(group, descending = true).first())
        assertEquals(70, EpisodePager.displayIndices(group, descending = true).last())
    }

    @Test
    fun groupRowFollowsSameOrderAsGrid() {
        assertTrue(
            "分组行必须按 displayGroupOrder 渲染（与网格同序）",
            dialog.contains("EpisodePager.displayGroupOrder(groups.size, descending)")
        )
        assertEquals(
            "倒序时最后一组排在最前",
            listOf(8, 7, 6, 5, 4, 3, 2, 1, 0),
            EpisodePager.displayGroupOrder(9, descending = true)
        )
    }

    @Test
    fun labelReflectsOrder() {
        val group = EpisodePager.Group(startIndex = 0, endIndex = 9)
        assertEquals("正序 1-10", "1-10", EpisodePager.displayLabel(group, descending = false))
        assertEquals("倒序 10-1", "10-1", EpisodePager.displayLabel(group, descending = true))
    }

    /**
     * 弹框打开期间自动连播会继续推进（真机实证：标题到第 81 集，弹框仍高亮第 74 集）。
     * 因此必须支持实时选择器 + 轮询刷新，且 dismiss 时移除回调防泄漏。
     */
    @Test
    fun selectionFollowsLivePlayback() {
        assertTrue(
            "弹框必须支持实时当前集读取",
            dialog.contains("selectionProvider: (() -> Int)? = null")
        )
        assertTrue(
            "必须轮询刷新高亮（变化时才重绘）",
            dialog.contains("refreshSelectionIfChanged()") &&
                dialog.contains("if (latest !in titles.indices || latest == currentSelection) return")
        )
        assertTrue(
            "dismiss/onStop 必须移除轮询回调，防泄漏",
            dialog.contains("handler.removeCallbacks(selectionPollRunnable)")
        )
        // 行为期望值：组归属换算（86 集、每组 10 集 ⇒ 第 74 集属于第 8 组，下标 7）
        val paging = EpisodePager.build(total = 86, currentIndex = 73)
        assertEquals(7, paging.currentGroupIndex)
        assertEquals("71-80", paging.groups[paging.currentGroupIndex].label)
    }
}
