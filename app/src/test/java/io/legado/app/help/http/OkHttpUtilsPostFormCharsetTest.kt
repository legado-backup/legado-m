package io.legado.app.help.http

import java.nio.charset.Charset
import okhttp3.Request
import okhttp3.RequestBody
import okio.Buffer
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * REQ-09 / AD-14：`postForm` 新增可选 `charset`（默认 UTF-8）单测。
 *
 * 验收口径（tasks 1.2.5）：① 默认路径**零变化**（仍是 UTF-8 + 原 Content-Type）；
 * ② 指定非 UTF-8 时，Content-Type 的 charset 与请求体字节编码**同时**切换（否则目标站
 * 仍按 UTF-8 解析 ⇒ 乱码）。
 */
class OkHttpUtilsPostFormCharsetTest {

    private val gbk = Charset.forName("GBK")

    private fun RequestBody.bytes(): ByteArray {
        val buffer = Buffer()
        writeTo(buffer)
        return buffer.readByteArray()
    }

    /** 注：`postForm` 为「就地设 body」的 Builder 扩展（返回 Unit），故需分两步取 Request。 */
    private fun requestBuild(block: Request.Builder.() -> Unit): Request =
        Request.Builder().url("https://example.com/").apply(block).build()

    // ---------- String 变体 ----------

    @Test
    fun postForm_string_defaultIsUtf8AndPlainContentType() {
        val request = requestBuild { postForm("a=%E4%B8%AD") }
        val body = requireNotNull(request.body)
        assertEquals("application/x-www-form-urlencoded", body.contentType().toString())
        assertArrayEquals("a=%E4%B8%AD".toByteArray(Charsets.UTF_8), body.bytes())
    }

    @Test
    fun postForm_string_explicitCharsetSwitchesContentTypeAndBytes() {
        val request = requestBuild { postForm("a=中", gbk) }
        val body = requireNotNull(request.body)
        assertEquals("application/x-www-form-urlencoded; charset=GBK", body.contentType().toString())
        assertArrayEquals("a=中".toByteArray(gbk), body.bytes())
    }

    // ---------- Map 变体 ----------

    @Test
    fun postForm_map_defaultIsUtf8AndPlainContentType() {
        val request = requestBuild { postForm(mapOf("k" to "中")) }
        val body = requireNotNull(request.body)
        assertEquals("application/x-www-form-urlencoded", body.contentType().toString())
        // FormBody 既有行为：value 以 UTF-8 做 form-urlencode
        assertArrayEquals("k=%E4%B8%AD".toByteArray(Charsets.UTF_8), body.bytes())
    }

    @Test
    fun postForm_map_explicitCharsetEncodesFormWithThatCharset() {
        val request = requestBuild { postForm(mapOf("k" to "中"), charset = gbk) }
        val body = requireNotNull(request.body)
        assertEquals("application/x-www-form-urlencoded; charset=GBK", body.contentType().toString())
        // GBK 的「中」= D6 D0 ⇒ form-urlencode 后为 %D6%D0（URL 编码结果为 ASCII）
        assertArrayEquals("k=%D6%D0".toByteArray(Charsets.UTF_8), body.bytes())
    }

    @Test
    fun postForm_map_encodedFlagIsRespectedForNonUtf8() {
        val request = requestBuild {
            postForm(mapOf("k" to "%E4%B8%AD"), encoded = true, charset = gbk)
        }
        val body = requireNotNull(request.body)
        assertArrayEquals("k=%E4%B8%AD".toByteArray(Charsets.UTF_8), body.bytes())
    }
}