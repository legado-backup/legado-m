package io.legado.app.web.api

import android.app.Application
import android.graphics.Bitmap
import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.api.ReturnData
import io.legado.app.web.TokenManager.Level
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * 位图端点的响应装配回归护栏（一期 · 2.1.8 旧端点回归发现的 P0 回归）。
 *
 * **回归事实**：改造前 `HttpServer.serve()` 在响应装配点是
 * `if (returnData.data is Bitmap) → image/png 字节流 else → JSON`；路由注册表化
 * 时该分支随 `when(uri)` 被删除 ⇒ `/cover`、`/image` 退化成 JSON 信封
 * （GSON 序列化 Bitmap 得到 `{}`）⇒ 老页**全部封面与正文图片失效**
 * （真机实测 23/23 封面 broken）。
 *
 * 必须跑 Robolectric：`unitTests.returnDefaultValues = true` 下纯 JVM 无法构造 `Bitmap`。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class ApiEnvelopeImagePayloadTest {

    private fun route(handler: suspend (ApiContext) -> Any): ApiRoute =
        ApiRoute(Method.GET, "/cover", Level.READONLY) { handler(it) }

    private fun ctx() = ApiContext(Method.GET, "/cover", emptyMap())

    private fun body(resp: fi.iki.elonen.NanoHTTPD.Response): String =
        resp.data.readBytes().toString(Charsets.ISO_8859_1)

    @Test
    fun bitmapPayload_returnsPngBinary_notJsonEnvelope() = runBlocking {
        val bitmap = Bitmap.createBitmap(4, 4, Bitmap.Config.ARGB_8888)
        val resp = ApiEnvelope.dispatch(route { ReturnData().setData(bitmap) }, ctx())
        assertEquals("位图端点须仍是 200", 200, resp.status.requestStatus)
        assertEquals("位图端点 MIME 须为 image/png", "image/png", resp.mimeType)
        assertFalse(
            "位图端点不得再回 JSON 信封（回归签名：body 含 isSuccess）",
            body(resp).contains("isSuccess")
        )
    }

    @Test
    fun nonBitmapPayload_stillWrappedAsJsonEnvelope() = runBlocking {
        val resp = ApiEnvelope.dispatch(route { ReturnData().setData("ok") }, ctx())
        assertEquals("application/json", resp.mimeType)
        assertTrue(body(resp).contains("isSuccess"))
    }
}
