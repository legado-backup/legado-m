package io.legado.app.web.api

import fi.iki.elonen.NanoHTTPD.Method
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ApiContext 单测（一期 · 5.1 验证项：「`requireParam` 单测覆盖缺失参数抛异常」/ REQ-1-301）。
 *
 * 关键口径：取参失败一律抛 [IllegalArgumentException]，由 [ApiEnvelope] 统一映射为 HTTP 400
 * —— 故 handler 内**不自行判空手写错误信封**，这里逐条锁住该约定（含空串与非法整数）。
 */
class ApiContextTest {

    private fun ctx(
        params: Map<String, List<String>> = emptyMap(),
        postData: String? = null,
        files: Map<String, String> = emptyMap(),
    ) = ApiContext(Method.POST, "/__probe__", params, postData, files)

    private fun thrownOf(block: () -> Unit): Throwable? = runCatching { block() }.exceptionOrNull()

    @Test
    fun level_carriesTokenLevelForAudit() {
        // 一期 3.7：审计要回答"这次调用是谁的权限" ⇒ 级别必须随请求上下文传下去；
        // 未显式传入（老调用点 / 未鉴权路径）须安全回落 NONE，而不是 null 崩溃。
        assertEquals(
            "未传入级别须回落 NONE",
            io.legado.app.web.TokenManager.Level.NONE,
            ctx().level
        )
        assertEquals(
            "传入级别须原样承载",
            io.legado.app.web.TokenManager.Level.MANAGE,
            ApiContext(Method.POST, "/__probe__", emptyMap(), null, emptyMap(),
                io.legado.app.web.TokenManager.Level.MANAGE).level
        )
    }

    @Test
    fun param_returnsFirstValue_orNull() {
        assertEquals("v", ctx(mapOf("a" to listOf("v", "w"))).param("a"))
        assertNull("缺失参数取值须返回 null（非抛异常）", ctx().param("a"))
    }

    @Test
    fun requireParam_present_returnsValue() {
        assertEquals("v", ctx(mapOf("name" to listOf("v"))).requireParam("name"))
    }

    @Test
    fun requireParam_missing_throws() {
        assertTrue(
            "缺失必填参数须抛 IllegalArgumentException（→ HTTP 400）",
            thrownOf { ctx().requireParam("name") } is IllegalArgumentException
        )
    }

    @Test
    fun requireParam_emptyString_throws() {
        assertTrue(
            "空串等同于缺失（须抛异常）",
            thrownOf { ctx(mapOf("name" to listOf(""))).requireParam("name") } is IllegalArgumentException
        )
    }

    @Test
    fun requirePostData_presentOrMissing() {
        assertEquals("body", ctx(postData = "body").requirePostData())
        assertTrue(thrownOf { ctx().requirePostData() } is IllegalArgumentException)
        assertTrue(thrownOf { ctx(postData = "").requirePostData() } is IllegalArgumentException)
    }

    @Test
    fun intParam_parses_orFallsBackToDefault() {
        assertEquals(7, ctx(mapOf("i" to listOf("7"))).intParam("i"))
        assertEquals(3, ctx().intParam("i", 3))
    }

    @Test
    fun intParam_missingWithoutDefault_orNonNumeric_throws() {
        assertTrue(
            "缺省且未给默认值须抛异常",
            thrownOf { ctx().intParam("i") } is IllegalArgumentException
        )
        assertTrue(
            "非整数须抛异常（不得静默回落默认值）",
            thrownOf { ctx(mapOf("i" to listOf("abc"))).intParam("i") } is IllegalArgumentException
        )
    }

    @Test
    fun requireFile_presentOrMissing() {
        assertEquals("/tmp/x", ctx(files = mapOf("f" to "/tmp/x")).requireFile("f"))
        assertTrue(thrownOf { ctx().requireFile("f") } is IllegalArgumentException)
    }
}
