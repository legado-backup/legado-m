package io.legado.app.ui.mcp

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * MCP 确认页 Intent 契约单测（web-mcp-productization 二期 · tasks 7.2）。
 *
 * 锁的是 **gate ↔ activity 的契约键**：`McpConfirmGate` 用这两个常量传参、本 Activity 用它们取值，
 * 任一侧改名都会静默失联（界面空白 ⇒ 用户看到"无名确认框"）⇒ 用断言把键名钉住。
 */
class McpConfirmActivityTest {

    @Test
    fun extras_areStableForGateContract() {
        assertEquals("mcp_confirm_title", McpConfirmActivity.EXTRA_TITLE)
        assertEquals("mcp_confirm_message", McpConfirmActivity.EXTRA_MESSAGE)
    }
}