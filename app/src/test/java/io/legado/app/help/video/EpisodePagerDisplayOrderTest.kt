package io.legado.app.help.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 选集弹框的正序 / 倒序展示顺序（2026-10-24 用户需求）。
 *
 * 需求原文：「选集弹框为什么不来个倒序正序按钮呢？」——
 * 86 集长剧要从最新集往回找时必须一直翻到底，故头部提供一键切换。
 *
 * 硬约束：
 * 1. 切换只影响**展示顺序**，点击回传的必须是真实**全集下标**（否则会播错集）；
 * 2. 分组标签随顺序变化（正序 `1-10` / 倒序 `10-1`）；
 * 3. 分组行与网格顺序必须一致（否则「点分组 81-86 出现的却是 1-10 的集」）。
 */
class EpisodePagerDisplayOrderTest {

    private val group = EpisodePager.Group(startIndex = 0, endIndex = 9)

    @Test
    fun ascendingIndicesCoverTheGroupInNaturalOrder() {
        assertEquals(
            "正序：start..end",
            listOf(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
            EpisodePager.displayIndices(group, descending = false)
        )
    }

    @Test
    fun descendingIndicesCoverTheGroupInReverseOrder() {
        assertEquals(
            "倒序：end..start（最新集在前）",
            listOf(9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
            EpisodePager.displayIndices(group, descending = true)
        )
    }

    @Test
    fun indicesStayWithinTheGroupForBothOrders() {
        // 无论正倒序，下标集合必须完全一致（只换顺序、不换内容）
        val asc = EpisodePager.displayIndices(group, descending = false)
        val desc = EpisodePager.displayIndices(group, descending = true)
        assertEquals("集数个数不变", asc.size, desc.size)
        assertEquals("集合内容不变", asc.toSet(), desc.toSet())
    }

    @Test
    fun labelFollowsTheDisplayOrder() {
        assertEquals("正序标签 1-10", "1-10", EpisodePager.displayLabel(group, descending = false))
        assertEquals("倒序标签 10-1", "10-1", EpisodePager.displayLabel(group, descending = true))
    }

    @Test
    fun lastGroupKeepsRealBoundsWhenDescending() {
        // 86 集、每组 10 集 ⇒ 最后一组 81-86
        val paging = EpisodePager.build(total = 86, currentIndex = 0)
        val last = paging.groups.last()
        assertEquals("最后一组真实边界", "81-86", EpisodePager.displayLabel(last, descending = false))
        assertEquals("倒序时最后一批显示在最前", "86-81", EpisodePager.displayLabel(last, descending = true))
    }

    @Test
    fun groupRowOrderMatchesGridOrder() {
        val paging = EpisodePager.build(total = 86, currentIndex = 0)
        val count = paging.groups.size
        assertEquals("正序：分组行 0..n-1", (0 until count).toList(), EpisodePager.displayGroupOrder(count, false))
        assertEquals(
            "倒序：分组行 n-1..0（最后一批集数排最前）",
            (count - 1 downTo 0).toList(),
            EpisodePager.displayGroupOrder(count, true)
        )
    }

    @Test
    fun emptyPagingYieldsEmptyOrder() {
        assertTrue("无分组时不得产生占位项", EpisodePager.displayGroupOrder(0, true).isEmpty())
        assertTrue(EpisodePager.displayGroupOrder(0, false).isEmpty())
    }
}
