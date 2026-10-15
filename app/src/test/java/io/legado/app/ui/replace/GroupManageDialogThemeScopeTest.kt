package io.legado.app.ui.replace

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-42 试点批：替换规则「分组管理」弹窗宿主主题作用域守护。
 *
 * 原 `setContent` 内容根无 `LegadoTheme` ⇒ 主题包/夜间下回落 M3 默认色板与字号；本批已上提。
 */
class GroupManageDialogThemeScopeTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `宿主内容根已上提 LegadoTheme`() {
        val src = code("src/main/java/io/legado/app/ui/replace/GroupManageDialog.kt")
        assertEquals("须引入 LegadoTheme", true, src.contains("import io.legado.app.ui.theme.LegadoTheme"))
        val host = src.substringAfter("setContent {")
        assertEquals("setContent 内容根须为 LegadoTheme", true, host.replace("\n", "").contains("LegadoTheme {"))
    }
}
