package io.legado.app.help.gsyVideo

import io.legado.app.help.video.EpisodePager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R7/R9 / V4/V5：选集分组弹框与倍速单排的纯策略锁定。
 *
 * 为什么值得测：
 *  - 分组「组内下标 + 组起点 = 全集下标」是最容易错一位的换算（错一位＝选错集）；
 *  - 倍速档位曾被写死 11 档（含 0.5x），需求要求去掉 0.5 且常用档一排 5 个；
 *  - 选集网格列数 5 是布局契约（4 列会挤压集名，6 列点击区过小）。
 */
class EpisodePickerGroupingTest {

    @Test
    fun speedValuesDropHalfAndKeepFivePerRow() {
        val values = ChoiceSpeedDialog.SPEED_VALUES
        assertFalse("0.5x 必须移除", values.contains(0.5f))
        assertEquals("单排可见档位必须为 5", 5, ChoiceSpeedDialog.VISIBLE_COUNT)
        assertEquals(
            "常用档位顺序（一排 5 个）",
            listOf(0.75f, 1.0f, 1.25f, 1.5f, 2.0f),
            values.take(ChoiceSpeedDialog.VISIBLE_COUNT),
        )
    }

    @Test
    fun speedValuesAscendingAndUnique() {
        val values = ChoiceSpeedDialog.SPEED_VALUES
        assertEquals("档位不得重复", values.size, values.toSet().size)
        assertEquals("档位必须升序", values.sorted(), values)
    }

    @Test
    fun gridColumnsIsFive() {
        assertEquals(5, ChoiceEpisodeDialog.COLUMNS)
    }

    @Test
    fun groupIndexMapsBackToGlobalEpisode() {
        // 88 集、当前第 36 集（0-based 35）：应落在 31-40 组（startIndex=30），组内下标 5
        val paging = EpisodePager.build(total = 88, currentIndex = 35)
        val group = paging.groups[paging.currentGroupIndex]
        assertEquals("组起点", 30, group.startIndex)
        assertEquals("组终点", 39, group.endIndex)
        val positionInGroup = 35 - group.startIndex
        assertEquals("组内下标", 5, positionInGroup)
        assertEquals("回算全集下标必须一致", 35, group.startIndex + positionInGroup)
    }

    @Test
    fun groupsCoverEveryEpisodeExactlyOnce() {
        listOf(1, 9, 10, 11, 88, 263, 1000).forEach { total ->
            val groups = EpisodePager.build(total, 0).groups
            assertEquals("$total 集：首组从 0 开始", 0, groups.first().startIndex)
            assertEquals("$total 集：末组到 total-1 结束", total - 1, groups.last().endIndex)
            var expectedStart = 0
            groups.forEach { group ->
                assertEquals("$total 集：分组必须连续无空洞", expectedStart, group.startIndex)
                assertEquals("$total 集：组内计数与区间一致", group.count, group.endIndex - group.startIndex + 1)
                expectedStart = group.endIndex + 1
            }
            assertTrue("$total 集：组数不超过上限", groups.size <= EpisodePager.MAX_GROUPS)
        }
    }
}
