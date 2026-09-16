package io.legado.app.help.dlna

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * AD-16：会话级分片内存缓存（LRU）纯逻辑单测。
 *
 * 覆盖：命中/未命中统计、字节上限 LRU 淘汰、单片超限拒收、禁用、清空、并发读写。
 */
class CastSegmentCacheTest {

    private fun bytes(size: Int) = ByteArray(size)

    @Test
    fun `命中与未命中统计正确`() {
        val cache = CastSegmentCache(1024)
        cache.put("a", bytes(100), "video/mp2t")
        assertNotNull(cache.get("a"))
        assertNull(cache.get("missing"))
        assertEquals(1L, cache.hits)
        assertEquals(1L, cache.misses)
    }

    @Test
    fun `超限按最久未使用淘汰`() {
        val cache = CastSegmentCache(300)
        cache.put("a", bytes(100), "video/mp2t")
        cache.put("b", bytes(100), "video/mp2t")
        cache.put("c", bytes(100), "video/mp2t")
        // 访问 a → b 变为最久未使用
        cache.get("a")
        cache.put("d", bytes(100), "video/mp2t")
        assertNull("最久未使用的 b 应被淘汰", cache.get("b"))
        assertNotNull("刚访问过的 a 应保留", cache.get("a"))
        assertNotNull("新写入的 d 应在缓存中", cache.get("d"))
        assertTrue(cache.evictions >= 1L)
        assertTrue("占用不得超过上限", cache.bytes <= 300L)
    }

    @Test
    fun `同一URL重复写入不重复计字节`() {
        val cache = CastSegmentCache(1024)
        cache.put("a", bytes(100), "video/mp2t")
        cache.put("a", bytes(100), "video/mp2t")
        assertEquals(100L, cache.bytes)
        assertEquals(1, cache.size)
    }

    @Test
    fun `单片超上限拒收`() {
        val cache = CastSegmentCache(64L * 1024 * 1024)
        val oversized = bytes(DlnaConstants.MAX_SEGMENT_BYTES.toInt() + 1)
        assertFalse(cache.put("big", oversized, "video/mp2t"))
        assertEquals(0, cache.size)
        assertEquals(0L, cache.bytes)
    }

    @Test
    fun `上限为0时整体禁用`() {
        val cache = CastSegmentCache(0)
        assertFalse(cache.enabled)
        assertFalse(cache.put("a", bytes(10), "video/mp2t"))
        assertNull(cache.get("a"))
    }

    @Test
    fun `清空后归零`() {
        val cache = CastSegmentCache(1024)
        cache.put("a", bytes(100), "video/mp2t")
        cache.clear()
        assertEquals(0L, cache.bytes)
        assertEquals(0, cache.size)
    }

    @Test
    fun `prefetch 记账不影响命中统计`() {
        val cache = CastSegmentCache(1024)
        cache.addPrefetchedBytes(2048)
        assertEquals(2048L, cache.prefetched)
        assertEquals(0L, cache.hits)
        assertEquals(0L, cache.misses)
    }

    @Test
    fun `并发读写不损坏结构且不超上限`() {
        val limit = 64 * 1024L
        val cache = CastSegmentCache(limit)
        val threads = 8
        val pool = Executors.newFixedThreadPool(threads)
        val latch = CountDownLatch(threads)
        repeat(threads) { t ->
            pool.execute {
                try {
                    repeat(300) { i ->
                        val key = "k${(t * 300 + i) % 64}"
                        cache.put(key, bytes(256), "video/mp2t")
                        cache.get(key)
                        cache.contains(key)
                    }
                } finally {
                    latch.countDown()
                }
            }
        }
        assertTrue("并发任务应在超时前完成", latch.await(30, TimeUnit.SECONDS))
        pool.shutdown()
        assertTrue("结构未损坏（占用不超上限）", cache.bytes <= limit)
        assertTrue("条目数受容量约束", cache.size <= (limit / 256).toInt() + 1)
    }
}