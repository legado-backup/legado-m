package io.legado.app.ui.book.read.textweb

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 沙箱状态日志门禁行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 覆盖：状态名抽取（含逗号 / 不含逗号）+ 首次输出 / 同状态名抑制 / 状态名变化放行。
 */
class RenderStateLogGateTest {

    @Test
    fun stateTag_takesTokenBeforeComma() {
        assertEquals(
            "settle",
            RenderStateLogGate.stateTag("settle,shell=opening,body=0,page=0/28,h=490,slotTop=210")
        )
    }

    @Test
    fun stateTag_withoutComma_returnsWhole() {
        assertEquals("ready", RenderStateLogGate.stateTag("ready"))
    }

    @Test
    fun firstReport_isLogged() {
        assertTrue(RenderStateLogGate.shouldLog(null, "settle"))
    }

    @Test
    fun sameStateTag_isSuppressed() {
        assertFalse(RenderStateLogGate.shouldLog("settle", "settle"))
    }

    @Test
    fun changedStateTag_isLogged() {
        assertTrue(RenderStateLogGate.shouldLog("opening", "settle"))
    }
}
