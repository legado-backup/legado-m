package io.legado.app.web.socket

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * WS 三通道握手鉴权「结构断言」单测（一期 · 1.3.2 / REQ-1-109）。
 *
 * **为什么用源码扫描而不是行为测试**：三个 WS 的鉴权发生在 `onOpen()`，而要真实构造
 * `NanoWSD.WebSocket` 需握手 session + Android 侧 `Debug` / `SearchModel` 依赖（非纯 JVM 可测）。
 * 鉴权判定逻辑本身已由 `WebAuthTest.verifyWs_*` / `denyResponse_*` 覆盖；
 * 本测试只锁**接线不退化** —— 与 `ApiRegistryTest.httpServer_hasNoEndpointLevelWhenBranch`
 * 同属本项目既有的"源码扫描式结构断言"范式。
 *
 * 断言三件事（逐个 WS，且**只在 `onOpen()` 体内**断言，避免文件别处的 return 让断言假通过）：
 * 1. 校验握手 query 参数 `token`（`WebAuth.verifyWs(...) == TokenManager.Level.NONE`）；
 * 2. 未过校验必须 **close + return**（不得继续进入业务/搜索流程）；
 * 3. 构造参数保留为属性 `private val handshake` —— 否则 `onOpen()` 无参就读不到握手 query（决策 #9）。
 */
class WebSocketAuthTest {

    private val targets = listOf(
        "BookSourceDebugWebSocket.kt",
        "RssSourceDebugWebSocket.kt",
        "BookSearchWebSocket.kt",
    )

    /** 读取源文件并剥掉整行注释（防注释里的字样让断言假通过）。 */
    private fun sourceOf(fileName: String): String {
        val rel = "src/main/java/io/legado/app/web/socket/$fileName"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
            .firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 截取 `onOpen()` 函数体（到首个缩进 4 空格的右花括号为止）。 */
    private fun onOpenBody(code: String): String {
        val body = code.substringAfter("override fun onOpen()", "")
        assertTrue("未找到 onOpen() 定义", body.isNotEmpty())
        return body.substringBefore("\n    }")
    }

    @Test
    fun eachWebSocket_verifiesHandshakeTokenInOnOpen() {
        targets.forEach { name ->
            val body = onOpenBody(sourceOf(name))
            assertTrue(
                "$name 的 onOpen 必须校验握手 query 参数 token",
                body.contains("parameters[\"token\"]") && body.contains("WebAuth.verifyWs(")
            )
            assertTrue(
                "$name 必须以 NONE 判定未授权",
                body.contains("TokenManager.Level.NONE")
            )
        }
    }

    @Test
    fun eachWebSocket_closesAndReturnsWhenUnauthorized() {
        targets.forEach { name ->
            val body = onOpenBody(sourceOf(name))
            assertTrue(
                "$name 未授权时必须关闭连接（CloseCode.ProtocolError）",
                body.contains("CloseCode.ProtocolError")
            )
            assertTrue(
                "$name 关闭后必须 return，不得继续进入业务流程",
                body.contains("return")
            )
        }
    }

    @Test
    fun eachWebSocket_keepsHandshakeAsProperty() {
        targets.forEach { name ->
            assertTrue(
                "$name 构造参数须为属性 `private val handshake`（NanoWSD 的 onOpen() 无参，"
                    + "不留存握手 session 就无法读取 token —— 决策 #9）",
                sourceOf(name).contains("private val handshake")
            )
        }
    }
}
