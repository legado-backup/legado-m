package io.legado.app.help.dlna

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * dlna-cast-cache-unify AD-06/REQ-8：Range 解析与完整性判定纯逻辑单测。
 *
 * 覆盖：整段 / 单区间 / 开区间 / 后缀区间 / 越界 416 / 末位钳制 / 畸形 / 多区间忽略 /
 * `Content-Range` 组装 / L1 完整性闸 / L2 整段命中判定。
 */
class CastRangeSpecTest {

    @Test
    fun `无 Range 头按整段返回`() {
        val range = CastRangeSpec.parse(null, 1000)
        assertEquals(0L, range!!.start)
        assertEquals(999L, range.end)
        assertFalse(range.partial)
        assertEquals(1000L, range.length)
    }

    @Test
    fun `总长不可知时按整段返回`() {
        val range = CastRangeSpec.parse("bytes=0-99", -1)
        assertFalse(range!!.partial)
    }

    @Test
    fun `单区间解析正确`() {
        val range = CastRangeSpec.parse("bytes=0-1023", 10000)!!
        assertEquals(0L, range.start)
        assertEquals(1023L, range.end)
        assertTrue(range.partial)
        assertEquals(1024L, range.length)
    }

    @Test
    fun `开区间解析到末尾`() {
        val range = CastRangeSpec.parse("bytes=9000-", 10000)!!
        assertEquals(9000L, range.start)
        assertEquals(9999L, range.end)
        assertTrue(range.partial)
    }

    @Test
    fun `后缀区间取最后 n 字节`() {
        val range = CastRangeSpec.parse("bytes=-500", 10000)!!
        assertEquals(9500L, range.start)
        assertEquals(9999L, range.end)
        assertTrue(range.partial)
        assertEquals(500L, range.length)
    }

    @Test
    fun `起点越界返回 null（应回 416）`() {
        assertNull(CastRangeSpec.parse("bytes=10000-", 10000))
        assertNull(CastRangeSpec.parse("bytes=10001-10002", 10000))
    }

    @Test
    fun `终点超界被钳制到末位`() {
        val range = CastRangeSpec.parse("bytes=9000-99999", 10000)!!
        assertEquals(9999L, range.end)
    }

    @Test
    fun `终点小于起点返回 null`() {
        assertNull(CastRangeSpec.parse("bytes=100-50", 10000))
    }

    @Test
    fun `后缀为 0 返回 null`() {
        assertNull(CastRangeSpec.parse("bytes=-0", 10000))
    }

    @Test
    fun `畸形区间按整段忽略`() {
        assertFalse(CastRangeSpec.parse("bytes=abc-def", 10000)!!.partial)
        assertFalse(CastRangeSpec.parse("bytes=", 10000)!!.partial)
        assertFalse(CastRangeSpec.parse("items=0-10", 10000)!!.partial)
    }

    @Test
    fun `多区间按整段忽略`() {
        val range = CastRangeSpec.parse("bytes=0-99,200-299", 10000)!!
        assertFalse(range.partial)
        assertEquals(10000L, range.length)
    }

    @Test
    fun `Content-Range 组装格式正确`() {
        assertEquals("bytes 0-1023/10000", CastRangeSpec.contentRange(0, 1023, 10000))
    }

    @Test
    fun `完整性闸只在读满且长度可知时通过`() {
        assertTrue(CastRangeSpec.isComplete(1024, 1024))
        // 截断（少读）→ 不得进 L1
        assertFalse(CastRangeSpec.isComplete(1000, 1024))
        // 长度不可知 → 一律不进 L1（宁可少缓存，不可存截断数据）
        assertFalse(CastRangeSpec.isComplete(1024, -1))
        assertFalse(CastRangeSpec.isComplete(0, 0))
    }

    @Test
    fun `L2 整段命中判定：未命中返回 0 不算命中`() {
        // javap 实证：getCachedBytes 未命中返回 0（不是 -1）
        assertFalse(CastRangeSpec.isFullyCached(0, 1024))
        assertFalse(CastRangeSpec.isFullyCached(1000, 1024))
        assertTrue(CastRangeSpec.isFullyCached(1024, 1024))
        assertTrue(CastRangeSpec.isFullyCached(2048, 1024))
        // 长度未知（-1 = 读到末尾）时，只要缓存里有内容即视为命中
        assertTrue(CastRangeSpec.isFullyCached(1, -1))
        assertFalse(CastRangeSpec.isFullyCached(0, -1))
    }
}