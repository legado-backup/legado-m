package io.legado.app.help.source

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18「书源查询短时缓存 + epoch 失效」核心单测（纯 JVM，可注入时钟）。
 *
 * 验收口径（tasks §4.2）：**20 次连读 = 1 次回库**；写入口失效后**立即读到最新**；
 * 开关关闭行为不变（该分支由 `SourceQueryCacheWiringTest` 做结构断言）。
 */
class TtlEpochCacheTest {

    private var now = 1_000L
    private val clock = { now }
    private fun cache(ttlMs: Long = 2_000L, maxSize: Int = 64) =
        TtlEpochCache<String>(ttlMs = ttlMs, maxSize = maxSize, clock = clock)

    /** R18-1：连续读取只回库一次。 */
    @Test
    fun twentyConsecutiveReads_hitBackendOnce() {
        val cache = cache()
        var backend = 0
        repeat(20) {
            val value = cache.getOrLoad("k") {
                backend++
                "v"
            }
            assertEquals("v", value)
        }
        assertEquals("20 次连读应只回库 1 次", 1, cache.loadCount)
        assertEquals("回库计数应与 loader 实际调用一致", 1, backend)
    }

    /** R18-2：TTL 到期后自动回库（兜底：写源绕过登记入口也能自愈）。 */
    @Test
    fun expiredEntry_reloadsFromBackend() {
        val cache = cache(ttlMs = 1_000L)
        var backend = 0
        cache.getOrLoad("k") { backend++; "v1" }
        now += 999
        cache.getOrLoad("k") { backend++; "v2" }
        assertEquals("未超 TTL 不得回库", 1, backend)
        now += 2
        val after = cache.getOrLoad("k") { backend++; "v3" }
        assertEquals("超 TTL 必须回库", 2, backend)
        assertEquals("v3", after)
    }

    /** R18-3：invalidate 后**立即**失效（不依赖 TTL）——「写完立即读到最新」的机制保证。 */
    @Test
    fun invalidate_makesImmediatelyStale() {
        val cache = cache()
        var backend = 0
        assertEquals("v1", cache.getOrLoad("k") { backend++; "v1" })
        val epochBefore = cache.currentEpoch()
        cache.invalidate()
        assertTrue("epoch 必须自增", cache.currentEpoch() > epochBefore)
        assertTrue("失效后条目必须清空", cache.isEmpty())
        assertEquals("v2", cache.getOrLoad("k") { backend++; "v2" })
        assertEquals("失效后必须回库读到新值", 2, backend)
    }

    /** R18-4：查不到（null）不得写入缓存，否则「先查后建」的源会被永久判空。 */
    @Test
    fun nullResult_isNotCached() {
        val cache = cache()
        var backend = 0
        assertNull(cache.getOrLoad("missing") { backend++; null })
        assertNull(cache.getOrLoad("missing") { backend++; null })
        assertEquals("null 结果不得被缓存（应按未命中处理）", 2, backend)
        assertEquals(0, cache.size())
    }

    /** 不同 key 互不干扰（书源与订阅源同串 key 场景由装配侧加类型前缀解决，见 wiring 测试）。 */
    @Test
    fun distinctKeys_areIndependent() {
        val cache = cache()
        var backend = 0
        assertEquals("a", cache.getOrLoad("k1") { backend++; "a" })
        assertEquals("b", cache.getOrLoad("k2") { backend++; "b" })
        assertEquals("a", cache.getOrLoad("k1") { backend++; "x" })
        assertEquals("b", cache.getOrLoad("k2") { backend++; "y" })
        assertEquals(2, backend)
    }

    /** 容量上限：超限淘汰**最旧写入**的条目（插入序 FIFO，非访问序），避免无界增长。 */
    @Test
    fun maxSize_evictsOldest() {
        val cache = cache(maxSize = 2)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")
        assertEquals("容量上限必须生效", 2, cache.size())
        var backend = 0
        cache.getOrLoad("k1") { backend++; "reload" }
        assertEquals("最旧条目应被淘汰（需回库）", 1, backend)
    }

    /** 覆盖写：同一 key 重复 put 不增加条目数。 */
    @Test
    fun put_sameKeyOverwritesWithoutGrowing() {
        val cache = cache(maxSize = 2)
        cache.put("k1", "v1")
        cache.put("k1", "v2")
        assertEquals(1, cache.size())
    }
}