package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B2 · R9「目录结构化 diff」单测（覆盖 R9-1~R9-5）。
 *
 * 口径：按**章节身份（url）**匹配，而非「前后数量差」——后者在中间插入/删除混合时会算错，
 * 并让缓存区间漏掉插入段、错缓存既有章节。
 */
class AutoTaskTocDiffTest {

    private fun d(before: List<String>, after: List<String>, maxRanges: Int = AutoTaskTocDiff.DEFAULT_MAX_RANGES) =
        AutoTaskTocDiff.diff(before, after, maxRanges)

    // ---- R9-1：中间插入（原「数量差 + 尾段区间」口径的根因场景）----
    @Test
    fun r9_1_middleInsert_isCountedAndRangeIsExact() {
        // before 4 章；after 在中间插入两章（下标 1 与 3）
        val before = listOf("u1", "u2", "u3", "u4")
        val after = listOf("u1", "n1", "u2", "n2", "u3", "u4")
        val r = d(before, after)
        assertEquals("新增数必须按身份算出 2", 2, r.addedCount)
        assertEquals(0, r.removedCount)
        assertFalse(r.reordered)
        assertEquals("新增下标应合并为两段", listOf(1..1, 3..3), r.ranges)
        assertFalse("未超阈值不应降级", r.degraded)
    }

    /** 原口径最致命的一类：等量替换 ⇒ 数量差为 0，新增被漏报。 */
    @Test
    fun r9_1b_replacementWithEqualSize_isNotMissed() {
        val r = d(listOf("a", "b", "c"), listOf("a", "x", "c"))
        assertEquals("等量替换也必须报出 1 个新增", 1, r.addedCount)
        assertEquals(1, r.removedCount)
        assertEquals(listOf(1..1), r.ranges)
    }

    // ---- R9-2：重排（内容不变、顺序变化）----
    @Test
    fun r9_2_reorder_isDetected() {
        val r = d(listOf("a", "b", "c"), listOf("c", "a", "b"))
        assertTrue("应识别为重排", r.reordered)
        assertEquals(0, r.addedCount)
        assertEquals(0, r.removedCount)
        assertTrue("重排也算可感知变化", r.changed)
        assertTrue(r.ranges.isEmpty())
    }

    // ---- R9-3：重复标题（身份不同即各自独立；身份相同不重复计）----
    @Test
    fun r9_3_duplicateTitles_areJudgedByIdentity() {
        // 标题重复但身份不同：两章均为新增
        val r = d(listOf("t-1"), listOf("t-1", "t-2", "t-3"))
        assertEquals(2, r.addedCount)
        // 身份相同（同一 url）不应被重复计入新增
        val r2 = d(listOf("dup"), listOf("dup", "dup"))
        assertEquals("同一身份重复出现不算新增", 0, r2.addedCount)
    }

    // ---- R9-4：超阈值摘要（区间过多 ⇒ 摘要须可表达「降级」而非罗列全部）----
    @Test
    fun r9_4_overThreshold_isDegradedIntoSingleRange() {
        // 隔一个插一个 ⇒ 合并后 5 段 > 上限 4
        val before = listOf("u0", "u2", "u4", "u6", "u8", "u10", "u12", "u14", "u16", "u18")
        val after = listOf(
            "u0", "n1", "u2", "n3", "u4", "n5", "u6", "n7", "u8", "n9",
            "u10", "u12", "u14", "u16", "u18"
        )
        val r = d(before, after)
        assertEquals("共 5 个新增", 5, r.addedCount)
        assertTrue("区间数超上限应降级", r.degraded)
        assertEquals("降级为首尾单区间", 1, r.ranges.size)
        assertEquals(1..9, r.ranges.first())
    }

    // ---- R9-5：降级与边界（空集合 / 全删 / 上限<=0 / 无变化）----
    @Test
    fun r9_5_degradeAndBoundaries() {
        // 空 before（首次获取目录）⇒ 全部为新增，单区间
        val first = d(emptyList(), listOf("a", "b", "c"))
        assertEquals(3, first.addedCount)
        assertEquals(listOf(0..2), first.ranges)

        // 全删 ⇒ 只有移除，无区间
        val cleared = d(listOf("a", "b"), emptyList())
        assertEquals(0, cleared.addedCount)
        assertEquals(2, cleared.removedCount)
        assertTrue(cleared.ranges.isEmpty())

        // maxRanges<=0 视为 1 ⇒ 两段即降级
        val zero = d(listOf("x", "y"), listOf("x", "n1", "y", "n2"), maxRanges = 0)
        assertTrue(zero.degraded)
        assertEquals(1, zero.ranges.size)

        // 完全无变化
        val same = d(listOf("a", "b"), listOf("a", "b"))
        assertFalse(same.changed)
        assertTrue(same.ranges.isEmpty())
        assertEquals(0, same.addedCount)
        assertNotEquals(R9_SENTINEL, same.addedCount)
    }

    private companion object {
        /** 仅为可读性占位（防止未来误改成「用 -1 表示无变化」而破坏 changed 语义）。 */
        const val R9_SENTINEL = -1
    }
}