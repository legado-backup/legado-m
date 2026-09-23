package io.legado.app.ui.book.read.page

import io.legado.app.utils.Utf8Sha256
import java.io.File
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R20 落地回归：`LottieImageMemoryPolicy.sourceSha256`。
 *
 * 该函数是阅读页「高级标题 Lottie」的缓存键来源，改造后必须**摘要逐位不变**（否则所有模板缓存失效、
 * 阅读页首屏变慢），且不得再走 `MessageDigest` + `%02x` 老路径。
 */
class LottieImageMemoryPolicySha256Test {

    private fun legacyHex(text: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(text.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    @Test
    fun sourceSha256_matchesLegacyDigest() {
        listOf("", "{}", "{\"v\":\"5.7.4\"}", "回归样本" + "x".repeat(5000)).forEach { source ->
            assertEquals(
                "Lottie 缓存键摘要必须与改造前一致（len=${source.length}）",
                legacyHex(source),
                LottieImageMemoryPolicy.sourceSha256(source)
            )
        }
        assertEquals(
            "必须与统一工具同口径",
            Utf8Sha256.hex("高级标题"),
            LottieImageMemoryPolicy.sourceSha256("高级标题")
        )
    }

    /** 结构：已改调统一工具，且本文件不再直接使用 MessageDigest（防回退成各写一份）。 */
    @Test
    fun sourceSha256_delegatesToSharedTool() {
        val rel = "src/main/java/io/legado/app/ui/book/read/page/LottieImageMemoryPolicy.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        val source = file.readLines().joinToString("\n")
        assertTrue("必须改调 Utf8Sha256", source.contains("Utf8Sha256.hex(source)"))
        assertTrue("不得残留 MessageDigest 直用", !source.contains("MessageDigest"))
    }
}