package io.legado.app.ui.main.bookshelf

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R16「书架未读颜色强调」的**设置项接线**不变量。
 *
 * 只做渲染不做开关、或只做开关不落盘，都会表现为「功能做了但用户不可达 / 重启丢失」——
 * 本项目已有同类先例（半死配置），故把三处接线固化为断言。
 */
class BookshelfUnreadEmphasisWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun configDialog_exposesUnreadEmphasisSwitch() {
        val dialog = code("ui/main/bookshelf/BookshelfConfigDialog.kt")
        assertTrue(
            "书架配置弹窗必须有未读强调开关项",
            dialog.contains("\"unreadEmphasis\"") && dialog.contains("R.string.bookshelf_unread_emphasis")
        )
        assertTrue("配置值需进 BookshelfConfigValues", dialog.contains("val unreadEmphasis: Boolean"))
    }

    @Test
    fun hostFragment_readsAndPersistsUnreadEmphasis() {
        val host = code("ui/main/bookshelf/BaseBookshelfFragment.kt")
        assertTrue("打开弹窗时必须带入当前值", host.contains("unreadEmphasis = AppConfig.bookshelfUnreadEmphasis"))
        assertTrue(
            "应用配置时必须落盘并触发刷新",
            host.contains("AppConfig.bookshelfUnreadEmphasis = values.unreadEmphasis") &&
                host.contains("bookshelfUnreadEmphasis != values.unreadEmphasis")
        )
    }
}