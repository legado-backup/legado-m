package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * JS 书源 MCP 工具声明的权限边界（ng-js-source-port）。
 *
 * 脚本属凭据级内容 ⇒ 全部 MANAGE；落库必须走端侧确认（dangerous）；只读校验不得声明 readOnlyHint。
 */
class JsSourceToolsTest {

    private val byName = JsSourceTools.tools.associateBy { it.name }

    @Test
    fun declaresFourJsSourceTools() {
        assertEquals(
            setOf("js_source_validate", "js_source_save", "js_source_export", "js_source_debug"),
            byName.keys,
        )
    }

    @Test
    fun allScriptTools_requireManageLevel() {
        JsSourceTools.tools.forEach {
            assertEquals("${it.name} 必须 MANAGE", TokenManager.Level.MANAGE, it.level)
        }
    }

    @Test
    fun onlySave_isDangerousAndRequiresConfirmGate() {
        assertTrue(byName.getValue("js_source_save").dangerous)
        listOf("js_source_validate", "js_source_export", "js_source_debug").forEach {
            assertFalse("$it 不应触发端侧确认", byName.getValue(it).dangerous)
        }
    }

    @Test
    fun manageLevelTools_doNotClaimReadOnlyHint() {
        JsSourceTools.tools.forEach {
            assertFalse("${it.name} 非 READONLY 级 ⇒ readOnlyHint 必须为 false", it.readOnlyHint)
        }
    }
}
