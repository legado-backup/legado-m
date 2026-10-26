package io.legado.app.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 调试卷支路三条件判定单元测试（design AD-03 / tasks 2.1~2.5 / 测试配对清单）。
 *
 * 测试对象为 `src/main` 的**纯函数**，不触发 Android 依赖（不初始化 appCtx / WebView）。
 *
 * 断言要点（带期望值）：
 * 1. 三条件全满足 ⇒ `MANAGE`；
 * 2. 任一条件不满足 ⇒ `null`（回落三级令牌校验）：非回环 / 开关关闭 / 错误凭据 / 空凭据 / release 期望空值；
 * 3. 回环判定本身覆盖 IPv4 / IPv6 / localhost / 127.x 段。
 *
 * 已知上限：不覆盖 release 变体 `WebAuthDebugBranch`（恒 null）的编译期屏蔽 | 升级路径：双包门禁 grep 固定值常量。
 */
class DebugBranchPolicyTest {

    private val token = "9f2c7a41d8b34e6f90c5a2e7b18d4f63"

    // ============ 全满足 ============

    @Test
    fun allThreeConditionsMet_grantsManage() {
        val level = decideDebugBranchLevel(
            enabled = true,
            suppliedToken = token,
            clientIp = "127.0.0.1",
            expectedToken = token,
        )
        assertEquals("三条件全满足应授予 MANAGE", TokenManager.Level.MANAGE, level)
    }

    @Test
    fun ipv6Loopback_grantsManage() {
        val level = decideDebugBranchLevel(
            enabled = true, suppliedToken = token, clientIp = "::1", expectedToken = token,
        )
        assertEquals("IPv6 回环应视为本机来源", TokenManager.Level.MANAGE, level)
    }

    // ============ 各否定分支 ============

    @Test
    fun branchDisabled_fallsBackToNull() {
        // tasks 2.5：关闭开关后即使另外两条件满足也必须回落
        val level = decideDebugBranchLevel(
            enabled = false,
            suppliedToken = token,
            clientIp = "127.0.0.1",
            expectedToken = token,
        )
        assertNull("支路关闭必须回落（返回 null 交由三级令牌校验）", level)
    }

    @Test
    fun nonLoopbackClient_fallsBackToNull() {
        val level = decideDebugBranchLevel(
            enabled = true, suppliedToken = token, clientIp = "192.168.1.20", expectedToken = token,
        )
        assertNull("非回环来源不得授予支路级别", level)
    }

    @Test
    fun wrongToken_fallsBackToNull() {
        val level = decideDebugBranchLevel(
            enabled = true, suppliedToken = "wrong-token", clientIp = "127.0.0.1", expectedToken = token,
        )
        assertNull("错误凭据不得授予支路级别", level)
    }

    @Test
    fun emptyToken_fallsBackToNull() {
        assertNull(
            "空凭据不得授予",
            decideDebugBranchLevel(true, "", "127.0.0.1", token)
        )
        assertNull(
            "null 凭据不得授予",
            decideDebugBranchLevel(true, null, "127.0.0.1", token)
        )
    }

    @Test
    fun releaseVariant_emptyExpectedToken_neverMatches() {
        // release 变体不提供期望值 ⇒ 即使开关开、来源回环、凭据非空也必须为 null
        val level = decideDebugBranchLevel(
            enabled = true, suppliedToken = "any", clientIp = "127.0.0.1", expectedToken = "",
        )
        assertNull("release 变体（期望值为空）恒不匹配", level)
    }

    @Test
    fun blankClientIp_fallsBackToNull() {
        assertNull(
            "来源未知不得授予",
            decideDebugBranchLevel(true, token, "", token)
        )
        assertNull(
            "来源为 null 不得授予",
            decideDebugBranchLevel(true, token, null, token)
        )
    }

    // ============ 回环判定本身 ============

    @Test
    fun isLoopbackAddress_recognizesLoopbackForms() {
        assertTrue("127.0.0.1", isLoopbackAddress("127.0.0.1"))
        assertTrue("127.0.0.1 带空白", isLoopbackAddress("  127.0.0.1 "))
        assertTrue("127.0.0.53 属 127/8", isLoopbackAddress("127.0.0.53"))
        assertTrue("::1", isLoopbackAddress("::1"))
        assertTrue("localhost", isLoopbackAddress("localhost"))
    }

    @Test
    fun isLoopbackAddress_rejectsNonLoopback() {
        assertFalse("局域网地址", isLoopbackAddress("192.168.1.20"))
        assertFalse("公网地址", isLoopbackAddress("8.8.8.8"))
        assertFalse("空串", isLoopbackAddress(""))
        assertFalse("null", isLoopbackAddress(null))
        assertFalse("1270.0.0.1 不是 127 段", isLoopbackAddress("1270.0.0.1"))
    }

    // ============ 支路开关键（可关闭，tasks 2.5） ============

    @Test
    fun branchSwitchKey_isDeclaredAndStable() {
        // 开关键必须存在且非空：关闭后即回落既有三级令牌校验（tasks 2.5 的唯一入口）
        assertEquals(
            "支路开关键名必须稳定（调试脚本/设置页按此键读写）",
            "webAuthDebugBranch",
            io.legado.app.constant.PreferKey.webAuthDebugBranch,
        )
        assertTrue(
            "开关键不得与既有鉴权键混用（避免误关主令牌校验）",
            io.legado.app.constant.PreferKey.webAuthDebugBranch != io.legado.app.constant.PreferKey.webAuthStrict,
        )
    }

    // ============ 接入点防回归（真机 401 根因） ============

    /**
     * 支路挂接在 `WebAuth.verify(session)` 内；HTTP 层若直接调 `TokenManager.verify(token)`
     * 就会**绕过支路**，表现为「脚本全流程 PASS 但探活 401」（本轮真机首次实测即如此）。
     * 这里以源码断言锁住接入点，避免回归。
     */
    @Test
    fun httpLayer_authGoesThroughWebAuthVerify() {
        val file = java.io.File("src/main/java/io/legado/app/web/HttpServer.kt")
        assertTrue("HttpServer.kt 不存在：${file.absolutePath}", file.exists())
        val text = file.readText()
        assertTrue(
            "HTTP 鉴权必须经 WebAuth.verify（支路接入点），否则调试卷支路永不生效",
            text.contains("WebAuth.verify(session)"),
        )
        assertTrue(
            "HTTP 层不得直接调用 TokenManager.verify（会绕过支路）",
            !Regex("""(?m)^\s*TokenManager\.verify\(""").containsMatchIn(text),
        )
    }
}