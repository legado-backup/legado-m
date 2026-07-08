package io.legado.app.help.http

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * proxyClientCache LRU 淘汰策略单元测试（Task 15 / A6）
 *
 * 验证点：
 * 1. 超过上限 20 时自动淘汰最久未访问的 entry
 * 2. accessOrder=true 时访问会刷新顺序，被访问的 entry 不会被淘汰
 * 3. 上限内不淘汰
 *
 * 测试用同模式 LinkedHashMap 子类（value 用 String 代替 OkHttpClient），
 * 不依赖 Android 框架，纯 JVM 可运行。
 *
 * 已知上限：未直接测 HttpHelper.getProxyClient（依赖 okHttpClient/Android 框架） | 升级路径：引入 Robolectric + MockWebServer 测代理客户端构造与缓存联动
 */
class ProxyClientCacheTest {

    /** 复用 HttpHelper.kt 中 proxyClientCache 的同模式 LRU map（上限 20） */
    private fun <V> newLruCache(maxSize: Int): java.util.LinkedHashMap<String, V> =
        object : java.util.LinkedHashMap<String, V>(16, 0.75f, true) {
            override fun removeEldestEntry(eldest: Map.Entry<String, V>?): Boolean {
                return size > maxSize
            }
        }

    @Test
    fun lruCache_withinMaxSize_doesNotEvict() {
        // 边界值用例：上限内不淘汰
        val cache = newLruCache<String>(20)
        for (i in 1..20) {
            cache["proxy$i"] = "client$i"
        }
        assertEquals("20 个 entry 应全部保留", 20, cache.size)
        assertEquals("第一个 entry 应存在", "client1", cache["proxy1"])
        assertEquals("最后一个 entry 应存在", "client20", cache["proxy20"])
    }

    @Test
    fun lruCache_exceedMaxSize_evictsOldest() {
        // 正常业务用例：超过上限时淘汰最老的
        val cache = newLruCache<String>(20)
        for (i in 1..21) {
            cache["proxy$i"] = "client$i"
        }
        assertEquals("淘汰后应保持 20 个", 20, cache.size)
        assertFalse("最老的 proxy1 应被淘汰", cache.containsKey("proxy1"))
        assertTrue("最新的 proxy21 应保留", cache.containsKey("proxy21"))
    }

    @Test
    fun lruCache_accessOrderRefreshesEvictionOrder() {
        // 对照用例：accessOrder=true 时访问会刷新顺序
        val cache = newLruCache<String>(20)
        for (i in 1..20) {
            cache["proxy$i"] = "client$i"
        }
        // 访问 proxy1，使其成为最近访问
        cache["proxy1"]
        // 再 put 一个，触发淘汰；被淘汰的应是 proxy2（最久未访问），而非 proxy1
        cache["proxy21"] = "client21"
        assertEquals("淘汰后应保持 20 个", 20, cache.size)
        assertTrue("被访问过的 proxy1 应保留", cache.containsKey("proxy1"))
        assertFalse("最久未访问的 proxy2 应被淘汰", cache.containsKey("proxy2"))
    }

    @Test
    fun lruCache_emptyCache_returnsNullForMissingKey() {
        // 边界值用例：空 cache 查询返回 null
        val cache = newLruCache<String>(20)
        assertNull("空 cache 查询应返回 null", cache["nonexistent"])
    }

    @Test
    fun lruCache_multipleEvictions_keepsMostRecent20() {
        // 综合用例：连续淘汰多个，始终保留最近 20 个
        val cache = newLruCache<String>(20)
        for (i in 1..50) {
            cache["proxy$i"] = "client$i"
        }
        assertEquals("应始终保留 20 个", 20, cache.size)
        // 应保留 proxy31~proxy50
        for (i in 31..50) {
            assertTrue("proxy$i 应保留", cache.containsKey("proxy$i"))
        }
        for (i in 1..30) {
            assertFalse("proxy$i 应被淘汰", cache.containsKey("proxy$i"))
        }
    }
}
