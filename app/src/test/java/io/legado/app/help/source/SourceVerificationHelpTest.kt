package io.legado.app.help.source

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * `SourceVerificationHelp` 死取值器退役守护。
 *
 * `verificationAttemptCount(sourceKey)` 全仓零引用；真实传递通道是
 * [SourceVerificationHelp.getVerificationResult] 把本次序号作为 `attempt` **意图附加项**
 * 交给验证码弹窗（`VerificationCodeActivity` → `VerificationCodeDialog`），弹窗按 `attempt >= 2`
 * 渲染升级引导行，无需回调本层取值。本类守护「取值器不得回流」与「计数链/传递通道不得被误删」。
 */
class SourceVerificationHelpTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val src by lazy { code("src/main/java/io/legado/app/help/source/SourceVerificationHelp.kt") }

    @Test
    fun `verificationAttemptCount 已退役`() {
        assertEquals(
            "死取值器 verificationAttemptCount 应退役",
            false,
            src.contains("fun verificationAttemptCount(")
        )
    }

    @Test
    fun `计数链与意图附加项传递必须保留`() {
        assertEquals("计数链必须保留", true, src.contains("verificationAttempts = ConcurrentHashMap"))
        assertEquals("意图附加项传递必须保留", true, src.contains("putExtra(\"attempt\", attempt)"))
    }
}
