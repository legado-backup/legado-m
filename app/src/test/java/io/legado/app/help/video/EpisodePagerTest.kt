package io.legado.app.help.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep AD-03：集数分组边界（书源与订阅源共用规则）。
 */
class EpisodePagerTest {

    @Test
    fun `empty or single episode`() {
        val empty = EpisodePager.build(total = 0, currentIndex = 0)
        assertFalse(empty.hasGroups)
        assertEquals(-1, empty.currentGroupIndex)

        val one = EpisodePager.build(total = 1, currentIndex = 0)
        assertEquals(1, one.groups.size)
        assertEquals("1-1", one.groups[0].label)
        assertEquals(0, one.currentGroupIndex)
    }

    @Test
    fun `ten per group when within group budget`() {
        val paging = EpisodePager.build(total = 25, currentIndex = 4)
        assertEquals(10, paging.groupSize)
        assertEquals(listOf("1-10", "11-20", "21-25"), paging.groups.map { it.label })
        assertEquals(0, paging.currentGroupIndex)
        assertEquals(2, EpisodePager.build(total = 25, currentIndex = 24).currentGroupIndex)
    }

    @Test
    fun `group count never exceeds ten`() {
        listOf(60, 100, 263, 1000).forEach { total ->
            val paging = EpisodePager.build(total = total, currentIndex = 0)
            assertTrue("total=$total groups=${paging.groups.size}", paging.groups.size <= EpisodePager.MAX_GROUPS)
            assertEquals("last group must end at last episode (total=$total)", total - 1, paging.groups.last().endIndex)
        }
    }

    @Test
    fun `thousand episodes use hundred sized groups`() {
        val paging = EpisodePager.build(total = 1000, currentIndex = 999)
        assertEquals(100, paging.groupSize)
        assertEquals(10, paging.groups.size)
        assertEquals(9, paging.currentGroupIndex)
        assertEquals("901-1000", paging.groups.last().label)
    }

    @Test
    fun `current index is clamped into range`() {
        assertEquals(0, EpisodePager.build(total = 12, currentIndex = -5).currentGroupIndex)
        assertEquals(1, EpisodePager.build(total = 12, currentIndex = 999).currentGroupIndex)
    }
}
