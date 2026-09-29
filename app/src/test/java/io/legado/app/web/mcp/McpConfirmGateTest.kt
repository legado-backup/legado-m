package io.legado.app.web.mcp

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * MCP 端侧确认闸门单测（web-mcp-productization 二期 · tasks 7.1 / REQ-2-501）。
 *
 * 锁三件事：① 静默期常量（60s，spec §7.1）；② 初始无待确认请求；
 * ③ **无 UI 环境时必须保守拒绝**（拉起 Activity 失败 ⇒ false，**绝不能**退化成放行 ——
 * 这是安全底线：失败方向必须偏向"不放行"）。
 */
class McpConfirmGateTest {

    @Test
    fun timeout_is60Seconds() {
        assertEquals("静默期须为 60s（超时视为拒绝）", 60_000L, McpConfirmGate.TIMEOUT_MS)
    }

    @Test
    fun pending_isFalseInitially() {
        assertFalse("初始不得存在待确认请求", McpConfirmGate.pending)
    }

    @Test
    fun resolve_withoutPendingRequest_isNoOp() {
        // 没有待确认请求时回传结果不得抛异常（乱序回调的容错）
        McpConfirmGate.resolve(true)
        McpConfirmGate.resolve(false)
        assertFalse(McpConfirmGate.pending)
    }

    @Test
    fun requestConfirm_withoutUi_deniesConservatively() = runBlocking {
        // JVM 单测环境没有 Activity 可拉起 ⇒ 必须返回 false（保守拒绝）。
        // 若这里返回 true，说明"拉起失败"会退化成放行 —— 那是安全缺陷。
        val approved = McpConfirmGate.requestConfirm("标题", "内容", timeoutMs = 100L)
        assertFalse("无 UI 环境必须保守拒绝，绝不能放行", approved)
    }
}