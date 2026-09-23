package io.legado.app.ui.main.bookshelf

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书架标签管理页 chip 底口径不变量回归测试（B7 R28/D2，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 D2）：分组 chip 底取 `settings.row`（面 token 越界：行底色用于
 * chip），与 `TagChip` / `AppFilterChip` / XML 侧 chip 口径不一致 ⇒ 同语义多套视觉。
 * 收敛后统一取 chip 面 token `tabBackgroundColor`。
 */
class BookshelfTagChipTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/main/bookshelf/BookshelfTagManageScreen.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val f = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return f.readLines()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("*") || t.startsWith("//") || t.startsWith("/*")
            }
            .joinToString("\n")
    }

    @Test
    fun groupChip_idleBackgroundUsesChipFaceToken() {
        val text = code()
        assertTrue("分组 chip 底应取 tabBackgroundColor", text.contains("tabBackgroundColor"))
        assertTrue("应通过 rememberThemeUiPalette 取面色", text.contains("rememberThemeUiPalette()"))
    }
}