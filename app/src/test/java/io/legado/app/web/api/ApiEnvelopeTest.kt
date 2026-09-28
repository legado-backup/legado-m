package io.legado.app.web.api

import com.google.gson.JsonParser
import fi.iki.elonen.NanoHTTPD
import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.api.ReturnData
import io.legado.app.web.TokenManager.Level
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ApiEnvelope 单测（一期 · 5.3 验证项 / REQ-1-301 · REQ-1-302）。
 *
 * 锁三件事：
 * 1. **异常 → 状态码**：`IllegalArgumentException`→400、其他→500（不再恒 200）；
 * 2. **`Response` 逃生舱**：`/backup` 这类需回文件流的端点原样透传；
 * 3. **三字段语义不变**：`isSuccess` / `errorMsg` / `data` 保持原义，`code` 为新增字段（老 vue 页零改动）。
 *
 * 断言 JSON 一律走 [JsonParser]（本仓 GSON 开了 `setPrettyPrinting`，字符串直接比对会因空白失败）。
 */
class ApiEnvelopeTest {

    private fun route(handler: suspend (ApiContext) -> Any): ApiRoute =
        ApiRoute(Method.GET, "/__probe__", Level.READONLY) { handler(it) }

    private fun ctx() = ApiContext(Method.GET, "/__probe__", emptyMap())

    private fun body(resp: NanoHTTPD.Response): String =
        resp.data.readBytes().toString(Charsets.UTF_8)

    @Test
    fun returnData_isWrappedAs200Envelope() = runBlocking {
        val resp = ApiEnvelope.dispatch(route { ReturnData().setData("ok") }, ctx())
        assertEquals(200, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertTrue("成功响应 isSuccess 须为 true", json.get("isSuccess").asBoolean)
        assertEquals("ok", json.get("data").asString)
    }

    @Test
    fun statusOkIsTheAuditSuccessCriterion() = runBlocking {
        // 一期 3.7：审计的 success 判据是 `response.status == Response.Status.OK`（非 OK 即记失败）。
        // 本用例把判据两端钉住：正常信封 = OK；异常信封 ≠ OK。改判据会让审计成败列静默反转。
        val ok = ApiEnvelope.dispatch(route { ReturnData().setData("ok") }, ctx())
        assertSame("正常信封须为 OK", NanoHTTPD.Response.Status.OK, ok.status)
        val failed = ApiEnvelope.dispatch(route { throw IllegalStateException("boom") }, ctx())
        assertFalse(
            "异常信封不得被判为成功",
            failed.status == NanoHTTPD.Response.Status.OK
        )
    }

    @Test
    fun explicitCode_mapsToSameHttpStatus() = runBlocking {
        // code 与 HTTP 状态码严格一致（REQ-1-301）
        val resp = ApiEnvelope.dispatch(route { ReturnData().setErrorMsg("no").setCode(404) }, ctx())
        assertEquals(404, resp.status.requestStatus)
        assertEquals(404, JsonParser.parseString(body(resp)).asJsonObject.get("code").asInt)
    }

    @Test
    fun illegalArgument_mapsTo400() = runBlocking {
        val resp = ApiEnvelope.dispatch(route { throw IllegalArgumentException("bad param") }, ctx())
        assertEquals(400, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertFalse(json.get("isSuccess").asBoolean)
        assertEquals(400, json.get("code").asInt)
        assertEquals("异常信息须进 errorMsg（老页可见）", "bad param", json.get("errorMsg").asString)
    }

    @Test
    fun otherException_mapsTo500() = runBlocking {
        val resp = ApiEnvelope.dispatch(route { throw IllegalStateException("boom") }, ctx())
        assertEquals(500, resp.status.requestStatus)
        assertEquals(500, JsonParser.parseString(body(resp)).asJsonObject.get("code").asInt)
    }

    @Test
    fun response_escapeHatch_isReturnedAsIs() = runBlocking {
        val raw = NanoHTTPD.newFixedLengthResponse("zip-bytes")
        val resp = ApiEnvelope.dispatch(route { raw }, ctx())
        assertSame("Response 逃生舱须原样返回（如 /backup 的 ZIP 流）", raw, resp)
    }

    // ------------------------------------------------------------ 3.2 顶层 catch 的真实状态码

    @Test
    fun errorResponseOf_illegalArgument_mapsTo400() {
        // HttpServer 顶层 catch 复用本方法：改造前该分支恒 200 + 纯文本（质量债 3.2）
        val resp = ApiEnvelope.errorResponseOf(IllegalArgumentException("bad param"))
        assertEquals(400, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertEquals(400, json.get("code").asInt)
        assertFalse(json.get("isSuccess").asBoolean)
        assertEquals("bad param", json.get("errorMsg").asString)
    }

    @Test
    fun errorResponseOf_otherException_mapsTo500() {
        val resp = ApiEnvelope.errorResponseOf(IllegalStateException("boom"))
        assertEquals(500, resp.status.requestStatus)
        assertEquals(500, JsonParser.parseString(body(resp)).asJsonObject.get("code").asInt)
    }

    @Test
    fun errorResponseOf_exceptionWithoutMessage_stillHasMessage() {
        // errorMsg 不得为空串（否则老页展示空白）
        val resp = ApiEnvelope.errorResponseOf(RuntimeException())
        val msg = JsonParser.parseString(body(resp)).asJsonObject.get("errorMsg").asString
        assertTrue("errorMsg 必须有兜底文案：'$msg'", msg.isNotBlank())
    }

    @Test
    fun errorResponseOf_fileNotFound_mapsTo404() {
        // SC-1-19：未注册路径落到静态资源处理，资源不存在时必须是 404（改造前恒 200 + 纯文本）
        val resp = ApiEnvelope.errorResponseOf(java.io.FileNotFoundException("/web/not-exist.html"))
        assertEquals(404, resp.status.requestStatus)
        assertEquals(404, JsonParser.parseString(body(resp)).asJsonObject.get("code").asInt)
    }

    @Test
    fun deny_buildsUniform401Envelope() {
        val resp = ApiEnvelope.deny(401, "unauthorized")
        assertEquals(401, resp.status.requestStatus)
        val json = JsonParser.parseString(body(resp)).asJsonObject
        assertEquals(401, json.get("code").asInt)
        assertEquals("unauthorized", json.get("errorMsg").asString)
    }
}
