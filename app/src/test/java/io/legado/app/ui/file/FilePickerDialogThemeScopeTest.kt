package io.legado.app.ui.file

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-42 放量批：文件选择弹窗宿主主题作用域守护（原内容根为 `LegadoComposeTheme` ⇒ 主题包/夜间回落 M3 色板）。
 */
class FilePickerDialogThemeScopeTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `文件选择弹窗内容根已上提 LegadoTheme`() {
        val src = code("src/main/java/io/legado/app/ui/file/FilePickerDialog.kt")
        assertEquals("须引入 LegadoTheme", true, src.contains("import io.legado.app.ui.theme.LegadoTheme"))
        assertEquals("setContent 内容根须为 LegadoTheme", true, src.contains("LegadoTheme {"))
        assertEquals("不得再以 LegadoComposeTheme 作内容根", false, src.contains("LegadoComposeTheme {"))
    }
}
