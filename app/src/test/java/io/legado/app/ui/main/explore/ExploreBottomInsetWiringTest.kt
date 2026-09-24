package io.legado.app.ui.main.explore

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1 配对（发现-modern）：发现页默认列表必须走「底栏安全区」**单源**，且不得回退硬编码。
 *
 * 改造前该文件三处 `contentPadding` 硬编码 `bottom = 86.dp`（不含导航栏 inset）⇒ 三键导航设备被遮挡。
 * 单源定义见 `io.legado.app.base.ComposeMainInsets`。
 */
class ExploreBottomInsetWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun exploreModern_listsUseSingleSourceBottomInset() {
        val src = code("ui/main/explore/ExploreModernListScreen.kt")
        assertTrue(
            "发现页列表底部留白必须走单源 mainBottomBarContentPadding(...)",
            src.contains("mainBottomBarContentPadding(")
        )
        assertFalse(
            "不得回退为硬编码 bottom = 86.dp（历史偏差：不含导航栏 inset）",
            Regex("bottom\\s*=\\s*\\d+\\.dp").containsMatchIn(src)
        )
    }
}