package io.legado.app.web

import com.google.gson.JsonParser
import fi.iki.elonen.NanoHTTPD
import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.constant.PreferKey
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRegistry
import io.legado.app.web.api.ApiRouteBootstrap
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * WebAuth 单测（一期 · 1.2.7 / REQ-1-105 ~ REQ-1-111）。
 *
 * 覆盖四类：
 * 1. **Bearer 解析**（大小写 / 空令牌 / 错 scheme）；
 * 2. **级别判定**（`allow` 纯比较；`required` 由调用方从 `ApiRoute.level` 传入 —— 本类不查路由表）；
 * 3. **白名单前缀边界**（`/uploadBooks` 不得命中 `/uploadBook/` 前缀 —— tasks 1.2.2 的陷阱用例）；
 * 4. **拒绝响应**（401 不泄露令牌存在性 / 403 明示所需级别）。
 *
 * 存储侧通过注入内存 [TokenManager.TokenStore] 在**纯 JVM**下跑（无需 Robolectric）。
 */
class WebAuthTest {

    private class MemoryStore : TokenManager.TokenStore {
        val map = HashMap<String, Any?>()
        override fun getString(key: String): String? = map[key] as? String
        override fun putString(key: String, value: String) {
            map[key] = value
        }

        override fun getLong(key: String, defValue: Long): Long = map[key] as? Long ?: defValue
        override fun putLong(key: String, value: Long) {
            map[key] = value
        }

        override fun getBoolean(key: String, defValue: Boolean): Boolean =
            map[key] as? Boolean ?: defValue

        override fun remove(key: String) {
            map.remove(key)
        }

        fun putBoolean(key: String, value: Boolean) {
            map[key] = value
        }
    }

    private lateinit var mem: MemoryStore

    @Before
    fun setUp() {
        mem = MemoryStore()
        TokenManager.store = mem
    }

    @After
    fun tearDown() {
        TokenManager.store = MemoryStore()
    }

    private fun body(resp: NanoHTTPD.Response): String =
        resp.data.readBytes().toString(Charsets.UTF_8)

    // ------------------------------------------------------------ Bearer 解析

    @Test
    fun extractBearer_acceptsValidHeader_caseInsensitive() {
        assertEquals("abc", WebAuth.extractBearer("Bearer abc"))
        assertEquals("abc", WebAuth.extractBearer("bearer abc"))
        assertEquals("abc", WebAuth.extractBearer("BEARER abc"))
        assertEquals("abc", WebAuth.extractBearer("  Bearer   abc  "))
    }

    @Test
    fun extractBearer_rejectsMissingOrMalformed() {
        assertNull(WebAuth.extractBearer(null))
        assertNull(WebAuth.extractBearer(""))
        assertNull(WebAuth.extractBearer("   "))
        assertNull("非 Bearer scheme 必须拒绝", WebAuth.extractBearer("Basic abc"))
        assertNull("空令牌视为未携带", WebAuth.extractBearer("Bearer"))
        assertNull(WebAuth.extractBearer("Bearer   "))
    }

    // ------------------------------------------------------------ 级别判定

    @Test
    fun levelOrdering_isAscending() {
        // allow() 依赖 ordinal 升序 —— 顺序被改就整体失效，故显式锁住
        val expected = listOf(
            TokenManager.Level.NONE,
            TokenManager.Level.READONLY,
            TokenManager.Level.MANAGE,
            TokenManager.Level.ADMIN,
        )
        assertEquals("级别枚举顺序即权限升序", expected, TokenManager.Level.values().toList())
    }

    @Test
    fun allow_isPureLevelComparison() {
        // 注意：嵌套 enum 不能当作表达式别名（`val l = TokenManager.Level` 会报
        // "does not have a companion object"）⇒ 必须写全限定名。
        assertTrue("同级放行", WebAuth.allow(Level.READONLY, Level.READONLY))
        assertTrue("高阶令牌可访问低阶端点", WebAuth.allow(Level.ADMIN, Level.READONLY))
        assertTrue(WebAuth.allow(Level.MANAGE, Level.MANAGE))
        assertFalse("无令牌一律拒绝", WebAuth.allow(Level.NONE, Level.READONLY))
        assertFalse("低阶不得访问高阶", WebAuth.allow(Level.READONLY, Level.MANAGE))
        assertFalse(WebAuth.allow(Level.MANAGE, Level.ADMIN))
    }

    // ------------------------------------------------------------ 白名单

    @Test
    fun isWhitelisted_matchesExactPaths() {
        listOf("/", "/index.html", "/favicon.ico").forEach {
            assertTrue("$it 应放行", WebAuth.isWhitelisted(it))
        }
    }

    @Test
    fun isWhitelisted_matchesPrefixesWithBoundary() {
        listOf("/vue/index.html", "/uploadBook/a.epub", "/uploadBook", "/help/x", "/console/y").forEach {
            assertTrue("$it 应放行", WebAuth.isWhitelisted(it))
        }
    }

    @Test
    fun isWhitelisted_doesNotLeakAcrossPrefixBoundary() {
        // tasks 1.2.2 陷阱用例：`/uploadBooks` 不得命中 `/uploadBook/` 前缀
        assertFalse("/uploadBooks 不得命中 /uploadBook/ 前缀", WebAuth.isWhitelisted("/uploadBooks"))
        assertFalse(WebAuth.isWhitelisted("/vues"))
        assertFalse(WebAuth.isWhitelisted("/helpers"))
    }

    @Test
    fun isWhitelisted_doesNotCoverBusinessEndpoints() {
        listOf("/getBookshelf", "/saveBookSource", "/deleteBookSources", "/backup", "/addLocalBook")
            .forEach { assertFalse("$it 属业务端点，不得白名单放行", WebAuth.isWhitelisted(it)) }
    }

    // ------------------------------------------------------------ WS 握手

    @Test
    fun verifyWs_checksTokenAgainstTokenManager() {
        val manage = TokenManager.generate(TokenManager.Level.MANAGE)
        assertEquals(TokenManager.Level.MANAGE, WebAuth.verifyWs(manage))
        assertEquals(TokenManager.Level.NONE, WebAuth.verifyWs(null))
        assertEquals(TokenManager.Level.NONE, WebAuth.verifyWs(""))
        assertEquals(TokenManager.Level.NONE, WebAuth.verifyWs("bogus-token"))
    }

    // ------------------------------------------------------------ 拒绝响应

    @Test
    fun denyResponse_noToken_returns401_withoutLeakingExistence() {
        val resp = WebAuth.denyResponse(TokenManager.Level.MANAGE, TokenManager.Level.NONE)
        assertEquals(401, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertEquals(401, json.get("code").asInt)
        assertFalse(json.get("isSuccess").asBoolean)
        val msg = json.get("errorMsg").asString
        assertFalse("401 不得出现「令牌不存在 / 无效」类字样（防令牌枚举）", msg.contains("不存在"))
        assertFalse("不得把「无效」与「未携带」区分开（否则可枚举）", msg.contains("无效"))
        assertTrue("401 须给出可执行引导", msg.contains("Bearer"))
    }

    @Test
    fun denyResponse_insufficientLevel_returns403_withRequiredLevel() {
        val resp = WebAuth.denyResponse(TokenManager.Level.MANAGE, TokenManager.Level.READONLY)
        assertEquals(403, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertEquals(403, json.get("code").asInt)
        val msg = json.get("errorMsg").asString
        assertTrue("403 须明示所需级别：$msg", msg.contains("MANAGE"))
        assertTrue("403 须明示当前级别：$msg", msg.contains("READONLY"))
    }

    // ------------------------------------------------------------ strict 开关

    @Test
    fun strict_reflectsPreference() {
        assertFalse("默认 false（REQ-1-108）", WebAuth.strict)
        mem.putBoolean(PreferKey.webAuthStrict, true)
        assertTrue(WebAuth.strict)
    }

    // ------------------------------------------------------------ 关键陷阱（SC-1-03）

    @Test
    fun addLocalBook_requiresManage_evenThoughItsPageSitsUnderUploadBook() {
        // 任务 1.2.6：`/addLocalBook` 的调用页在 `/uploadBook/` 目录下，但它是**写端点**
        // ⇒ 级别只由 `ApiRoute.level` 声明（manage），**不得**因 URL 前缀被白名单放行。
        ApiRouteBootstrap.install()
        val route = ApiRegistry.find(Method.POST, "/addLocalBook")
        assertEquals(TokenManager.Level.MANAGE, route?.level)
        assertFalse(
            "即便调用页在白名单目录下，端点本身也不得白名单放行（1.2.6）",
            WebAuth.isWhitelisted("/addLocalBook")
        )
        assertTrue("无令牌访问该端点必须被拒", !WebAuth.allow(TokenManager.Level.NONE, route!!.level))
    }

}
