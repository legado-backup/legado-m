package io.legado.app.lib.webdav

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * WebDAV 失败消息**非空兜底**不变量（REQ-08）。
 *
 * 缺陷形态：`checkResult()` 从错误响应体里取 `<s:message>`，该节点可能**缺失或为空白**
 * ⇒ 直接拼接会把字面量 `null` / 空串抛给上层，用户看到无意义提示。
 * `checkResult` 依赖真实网络响应，纯 JVM 无法构造 ⇒ 以源码不变量守住接线。
 */
class WebDavMessageFallbackTest {

    private val webDav by lazy {
        listOf(
            File("src/main/java/io/legado/app/lib/webdav/WebDav.kt"),
            File("../app/src/main/java/io/legado/app/lib/webdav/WebDav.kt"),
            File("app/src/main/java/io/legado/app/lib/webdav/WebDav.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun messageMustBeNonBlankBeforeUse() {
        assertTrue(
            "s:message 取出后须 takeIf { isNotBlank() }（否则空串会当成正常提示）",
            webDav.contains("?.takeIf { it.isNotBlank() }")
        )
    }

    @Test
    fun bothFailureExitsHaveFallbackText() {
        assertTrue(
            "ObjectNotFound 出口须有兜底文案",
            webDav.contains("""message ?: "${'$'}path doesn't exist. code:${'$'}{response.code}"""")
        )
        assertTrue(
            "通用 WebDavException 出口须有兜底文案",
            webDav.contains("""message ?: "未知错误 code:${'$'}{response.code}"""")
        )
    }
}