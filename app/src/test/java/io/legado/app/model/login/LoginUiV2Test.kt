package io.legado.app.model.login

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 动态登录 V2 协议（ng-js-source-port）：渲染行校验与动作回执解析。
 *
 * 这些是纯函数边界，直接决定「脚本返回脏数据时弹窗会不会崩/会不会把非法行渲染出来」，
 * 故以行为断言（返回 null / malformed）而非异常类型作为契约。
 */
class LoginUiV2Test {

    @Test
    fun isV2_onlyAcceptsVersion2Marker() {
        assertTrue(LoginUiV2.isV2("""{"version":2}"""))
        assertFalse(LoginUiV2.isV2("""{"version":3}"""))
        assertFalse(LoginUiV2.isV2("[]"))
        assertFalse(LoginUiV2.isV2(null))
    }

    @Test
    fun parseRender_validRows_returnsRows() {
        val json = """
            {"rows":[
              {"name":"账号","type":"text","key":"username","value":"a"},
              {"name":"密码","type":"password","key":"password"},
              {"name":"登录","type":"button","action":"submit","countdown":30}
            ]}
        """.trimIndent()
        val rows = LoginUiV2.parseRender(json)
        requireNotNull(rows)
        assertEquals(3, rows.size)
        assertEquals("username", rows[0].key)
        assertEquals(30, rows[2].countdown)
    }

    @Test
    fun parseRender_duplicateKeys_returnsNull() {
        val json = """
            {"rows":[
              {"name":"A","type":"text","key":"same"},
              {"name":"B","type":"text","key":"same"}
            ]}
        """.trimIndent()
        assertNull(LoginUiV2.parseRender(json))
    }

    @Test
    fun parseRender_selectWithoutOptions_returnsNull() {
        val json = """{"rows":[{"name":"线路","type":"select","key":"line"}]}"""
        assertNull(LoginUiV2.parseRender(json))
    }

    @Test
    fun parseRender_negativeCountdown_returnsNull() {
        val json = """{"rows":[{"name":"发送","type":"button","action":"send","countdown":-1}]}"""
        assertNull(LoginUiV2.parseRender(json))
    }

    @Test
    fun parseRender_emptyRows_returnsNull() {
        assertNull(LoginUiV2.parseRender("""{"rows":[]}"""))
        assertNull(LoginUiV2.parseRender(null))
    }

    @Test
    fun parseActionResult_stateAndErrors_areParsed() {
        val result = LoginUiV2.parseActionResult(
            """{"state":{"step":2},"error":{"username":"必填"},"close":false}"""
        )
        assertFalse(result.malformed)
        assertTrue(result.stateJson!!.contains("\"step\":2"))
        assertEquals("必填", result.error!!["username"])
        assertFalse(result.close)
    }

    @Test
    fun parseActionResult_closeTrue_closesDialog() {
        val result = LoginUiV2.parseActionResult("""{"close":true}""")
        assertFalse(result.malformed)
        assertTrue(result.close)
    }

    @Test
    fun parseActionResult_malformedClose_isRejected() {
        val result = LoginUiV2.parseActionResult("""{"close":"yes"}""")
        assertTrue(result.malformed)
    }

    @Test
    fun parseActionResult_unknownKeys_areReported() {
        val result = LoginUiV2.parseActionResult("""{"state":{},"toast":"hi"}""")
        assertEquals(listOf("toast"), result.unknownKeys)
    }

    @Test
    fun resolveFieldValue_prefersRenderThenSessionThenStored() {
        assertEquals("render", LoginUiV2.resolveFieldValue("render", "session", "stored"))
        assertEquals("session", LoginUiV2.resolveFieldValue(null, "session", "stored"))
        assertEquals("stored", LoginUiV2.resolveFieldValue(null, null, "stored"))
        assertNull(LoginUiV2.resolveFieldValue(null, null, null))
    }
}
