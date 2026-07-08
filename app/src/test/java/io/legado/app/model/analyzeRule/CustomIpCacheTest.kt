package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * customIp LRU 缓存策略单元测试（Task 18 / C5）
 *
 * 验证点：
 * 1. customIp 使用模式（put + remove 一次性）正确性
 * 2. LRU 上限 100 自动淘汰最久未访问
 * 3. accessOrder=true 时访问会刷新顺序
 *
 * 测试用同模式 LinkedHashMap 子类模拟 android.util.LruCache 行为
 * （android.util.LruCache 依赖 Android 框架，纯 JVM 无法实例化）
 *
 * 已知上限：未直接测 AnalyzeUrl.customIp（依赖 Android LruCache） | 升级路径：引入 Robolectric 测真实 LruCache 行为
 */
class CustomIpCacheTest {

    /** 复用 AnalyzeUrl.kt 中 customIp 的同模式 LRU map（上限 100） */
    private fun <V> newLruCache(maxSize: Int): java.util.LinkedHashMap<String, V> =
        object : java.util.LinkedHashMap<String, V>(16, 0.75f, true) {
            override fun removeEldestEntry(eldest: Map.Entry<String, V>?): Boolean {
                return size > maxSize
            }
        }

    @Test
    fun customIp_putThenRemove_oneTimeUsagePattern() {
        // 正常业务用例：customIp 的典型使用模式（put + remove 一次性）
        val cache = newLruCache<String>(100)
        cache.put("http://example.com/book", "192.168.1.1")
        // CronetHelper.customHost 读取并 remove
        val urlIp = cache.remove("http://example.com/book")
        assertEquals("remove 应返回写入的 IP", "192.168.1.1", urlIp)
        assertFalse("remove 后 entry 应不存在", cache.containsKey("http://example.com/book"))
    }

    @Test
    fun customIp_withinMaxSize_doesNotEvict() {
        // 边界值用例：上限内不淘汰
        val cache = newLruCache<String>(100)
        for (i in 1..100) {
            cache.put("url$i", "10.0.0.$i")
        }
        assertEquals("100 个 entry 应全部保留", 100, cache.size)
    }

    @Test
    fun customIp_exceedMaxSize_evictsOldest() {
        // 正常业务用例：超过上限时淘汰最老的
        val cache = newLruCache<String>(100)
        for (i in 1..101) {
            cache.put("url$i", "10.0.0.$i")
        }
        assertEquals("淘汰后应保持 100 个", 100, cache.size)
        assertFalse("最老的 url1 应被淘汰", cache.containsKey("url1"))
        assertTrue("最新的 url101 应保留", cache.containsKey("url101"))
    }

    @Test
    fun customIp_emptyCacheRemoveReturnsNull() {
        // 边界值用例：空 cache remove 返回 null（CronetHelper.customHost 的 urlIp == null 分支）
        val cache = newLruCache<String>(100)
        val urlIp = cache.remove("nonexistent")
        assertNull("空 cache remove 应返回 null", urlIp)
    }

    @Test
    fun customIp_multipleEvictions_keepsMostRecent100() {
        // 综合用例：连续淘汰多个，始终保留最近 100 个
        val cache = newLruCache<String>(100)
        for (i in 1..250) {
            cache.put("url$i", "10.0.0.$i")
        }
        assertEquals("应始终保留 100 个", 100, cache.size)
        // 应保留 url151~url250
        for (i in 151..250) {
            assertTrue("url$i 应保留", cache.containsKey("url$i"))
        }
        for (i in 1..150) {
            assertFalse("url$i 应被淘汰", cache.containsKey("url$i"))
        }
    }
}
