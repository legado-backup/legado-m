package io.legado.app.data.entities.rule

import io.legado.app.utils.GSON
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 动态登录 V2 的 `RowUi` 扩展字段（ng-js-source-port）。
 *
 * 老书源不填这些字段 ⇒ 全部 null，渲染路径零变化；
 * 新字段名对 JSON 的映射（key/hint/value/options/countdown）是脚本作者的公开契约，必须锁死。
 */
class RowUiV2FieldsTest {

    @Test
    fun legacyRows_keepNullV2Fields() {
        val row = GSON.fromJson(
            """{"name":"账号","type":"text","chars":["a","b"]}""",
            RowUi::class.java,
        )
        assertNull(row.key)
        assertNull(row.hint)
        assertNull(row.value)
        assertNull(row.options)
        assertNull(row.countdown)
    }

    @Test
    fun v2Fields_deserializeFromProtocolNames() {
        val row = GSON.fromJson(
            """{"name":"线路","type":"select","key":"line","hint":"选择线路",
               "value":"a","options":["a","b"],"countdown":30}""",
            RowUi::class.java,
        )
        assertEquals("line", row.key)
        assertEquals("选择线路", row.hint)
        assertEquals("a", row.value)
        assertEquals(listOf("a", "b"), row.options)
        assertEquals(30, row.countdown)
    }

    @Test
    fun labelType_isAvailableForV2Rendering() {
        assertTrue(RowUi.Type.label == "label")
    }
}
