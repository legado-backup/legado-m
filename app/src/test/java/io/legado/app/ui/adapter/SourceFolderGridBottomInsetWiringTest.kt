package io.legado.app.ui.adapter

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1 配对（订阅文件夹网格）：文件夹网格必须走「底栏安全区」**单源**。
 *
 * 改造前 `contentPadding` 只加四周 margin（底部无底栏留白）⇒ 文件夹列表滚到底被遮挡。
 * 单源定义见 `io.legado.app.base.ComposeMainInsets`。
 */
class SourceFolderGridBottomInsetWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun folderGrid_usesSingleSourceBottomInset() {
        val src = code("ui/adapter/SourceFolderComposeGrid.kt")
        assertTrue(
            "文件夹网格底部留白必须走单源 mainBottomBarContentPadding(...)",
            src.contains("mainBottomBarContentPadding(")
        )
        assertFalse(
            "禁止硬编码底栏留白（如 bottom = 86.dp）",
            Regex("bottom\\s*=\\s*\\d+\\.dp").containsMatchIn(src)
        )
    }
}