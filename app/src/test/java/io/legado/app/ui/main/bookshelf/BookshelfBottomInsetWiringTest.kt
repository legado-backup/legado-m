package io.legado.app.ui.main.bookshelf

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1 配对（书架）：书架页（网格/列表）必须走「底栏安全区」**单源**，且不得回退硬编码。
 *
 * 单源定义见 `io.legado.app.base.ComposeMainInsets`；集中视图见
 * `app/src/test/java/io/legado/app/base/BottomBarInsetWiringTest.kt`。
 * 背景：底栏与内容在主壳同层（overlay）⇒ 页面必须自加底部留白，且必须含导航栏 inset，
 * 否则三键导航设备上滚到底被遮挡（用户 2026-09-24 报障）。
 */
class BookshelfBottomInsetWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun bookshelfLists_useSingleSourceBottomInset() {
        val src = code("ui/main/bookshelf/BookshelfScreen.kt")
        assertTrue(
            "书架列表底部留白必须走单源 mainBottomBarContentPadding(...)（不得自行算 dp）",
            src.contains("mainBottomBarContentPadding(")
        )
        assertFalse(
            "禁止硬编码底栏留白（如 bottom = 86.dp）",
            Regex("bottom\\s*=\\s*\\d+\\.dp").containsMatchIn(src)
        )
    }
}