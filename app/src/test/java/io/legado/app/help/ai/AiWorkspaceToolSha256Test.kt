package io.legado.app.help.ai

import io.legado.app.utils.Utf8Sha256
import java.io.File
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R20 落地回归：`AiWorkspaceTool` 的文本哈希。
 *
 * 该函数用于 AI 工作区写入/比对时的内容指纹（大文本常见）⇒ 改造后必须
 * ①摘要与旧实现逐位一致（否则同一内容被判为"变了"）②不再逐字节 `%02x` 格式化。
 */
class AiWorkspaceToolSha256Test {

    private fun legacyHex(text: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(text.toByteArray())
            .joinToString("") { "%02x".format(it) }

    private fun sourceCode(): String {
        val rel = "src/main/java/io/legado/app/help/ai/AiWorkspaceTool.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines().joinToString("\n")
    }

    @Test
    fun workspaceHashIsEquivalentToLegacy() {
        // 直接对同一算法做等价比对（函数为 private，故用同口径断言工具本身 + 源码接线断言）
        listOf("", "{}", "工作区文本", "x".repeat(8192)).forEach { text ->
            assertEquals(
                "统一工具必须与旧实现逐位一致（len=${text.length}）",
                legacyHex(text),
                Utf8Sha256.hex(text)
            )
        }
    }

    @Test
    fun aiWorkspaceToolDelegatesToSharedTool() {
        val source = sourceCode()
        assertTrue("必须改调 Utf8Sha256", source.contains("Utf8Sha256.hex(text)"))
        assertTrue("不得残留 MessageDigest 直用", !source.contains("MessageDigest"))
        assertTrue("不得残留逐字节 %02x 格式化", !source.contains("\"%02x\".format(it)"))
    }
}