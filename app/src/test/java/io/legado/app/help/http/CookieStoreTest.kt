package io.legado.app.help.http

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CookieStore LRU 淘汰策略单元测试（Task 14 / A3）
 *
 * 验证点：
 * 1. tracking Cookie（_ga / _gid / _gat / _hjid / Hm_lvt_xxx / Hm_lpvt_xxx）优先删除
 * 2. 无 tracking Cookie 时按 key 长度降序删除
 * 3. 空 map 返回 null（边界）
 *
 * 测试对象为 top-level 纯函数，不触发 CookieStore object 的 Android 依赖初始化。
 * 已知上限：未覆盖 getCookie 完整流程（依赖 appDb/CacheManager/WebView） | 升级路径：引入 Robolectric 测整体 4096 截断链路
 */
class CookieStoreTest {

    // ============ isTrackingCookieKey ============

    @Test
    fun isTrackingCookieKey_recognizesCommonTrackingCookies() {
        assertTrue("_ga 应识别为 tracking", isTrackingCookieKey("_ga"))
        assertTrue("_gid 应识别为 tracking", isTrackingCookieKey("_gid"))
        assertTrue("_gat 应识别为 tracking", isTrackingCookieKey("_gat"))
        assertTrue("_hjid 应识别为 tracking", isTrackingCookieKey("_hjid"))
    }

    @Test
    fun isTrackingCookieKey_recognizesPrefixedVariants() {
        assertTrue("_ga_XYZ 应识别为 tracking", isTrackingCookieKey("_ga_XYZ"))
        assertTrue("_gat_UA-12345 应识别为 tracking", isTrackingCookieKey("_gat_UA-12345"))
        assertTrue("_gid_abc 应识别为 tracking", isTrackingCookieKey("_gid_abc"))
    }

    @Test
    fun isTrackingCookieKey_recognizesBaiduHmCookies() {
        assertTrue("Hm_lvt_xxx 应识别为 tracking", isTrackingCookieKey("Hm_lvt_123456"))
        assertTrue("Hm_lpvt_xxx 应识别为 tracking", isTrackingCookieKey("Hm_lpvt_abc"))
    }

    @Test
    fun isTrackingCookieKey_rejectsBusinessCookies() {
        assertFalse("JSESSIONID 不应识别为 tracking", isTrackingCookieKey("JSESSIONID"))
        assertFalse("token 不应识别为 tracking", isTrackingCookieKey("token"))
        assertFalse("sid 不应识别为 tracking", isTrackingCookieKey("sid"))
        assertFalse("PHPSESSID 不应识别为 tracking", isTrackingCookieKey("PHPSESSID"))
    }

    @Test
    fun isTrackingCookieKey_trimsWhitespace() {
        assertTrue("带空白的 _ga 应识别为 tracking", isTrackingCookieKey("  _ga  "))
    }

    // ============ selectCookieKeyToRemove ============

    @Test
    fun selectCookieKeyToRemove_emptyMap_returnsNull() {
        // 边界值用例：空 map 应返回 null
        val result = selectCookieKeyToRemove(emptyMap())
        assertNull("空 map 应返回 null", result)
    }

    @Test
    fun selectCookieKeyToRemove_singleEntry_returnsThatKey() {
        // 边界值用例：单元素 map 应返回该 key
        val map = mapOf("JSESSIONID" to "abc123")
        assertEquals("单元素 map 应返回该 key", "JSESSIONID", selectCookieKeyToRemove(map))
    }

    @Test
    fun selectCookieKeyToRemove_prefersTrackingCookieOverBusinessCookie() {
        // 正常业务用例：tracking Cookie 应优先于业务 Cookie 删除
        val map = linkedMapOf(
            "JSESSIONID" to "abc123",
            "_ga" to "GA1.2.xxx",
            "token" to "bearer-yyy"
        )
        assertEquals("应优先删除 tracking Cookie _ga", "_ga", selectCookieKeyToRemove(map))
    }

    @Test
    fun selectCookieKeyToRemove_prefersLongestTrackingCookie() {
        // 正常业务用例：多个 tracking Cookie 时，取 key 最长者最大化释放空间
        val map = linkedMapOf(
            "_ga" to "GA1.2.xxx",
            "_gid" to "GA1.2.yyy",
            "Hm_lvt_1234567890" to "1710000000"
        )
        assertEquals(
            "多个 tracking Cookie 应取最长 key",
            "Hm_lvt_1234567890",
            selectCookieKeyToRemove(map)
        )
    }

    @Test
    fun selectCookieKeyToRemove_noTrackingCookie_fallsBackToLongestKey() {
        // 对照用例：无 tracking Cookie 时按 key 长度降序
        val map = linkedMapOf(
            "sid" to "s1",
            "JSESSIONID" to "j1",
            "token" to "t1"
        )
        assertEquals(
            "无 tracking Cookie 时应返回最长 key JSESSIONID",
            "JSESSIONID",
            selectCookieKeyToRemove(map)
        )
    }

    @Test
    fun selectCookieKeyToRemove_mixedTrackingAndBusiness_prefersTracking() {
        // 综合用例：tracking + 业务混合，即使业务 key 更长也优先删 tracking
        val map = linkedMapOf(
            "PHPSESSID" to "p1",                // 9 chars，业务 Cookie
            "_gat_UA-12345-1" to "g1",          // tracking Cookie
            "a" to "x"                          // 1 char，业务 Cookie
        )
        assertEquals(
            "混合场景应优先删 tracking Cookie，而非最长业务 key",
            "_gat_UA-12345-1",
            selectCookieKeyToRemove(map)
        )
    }
}
