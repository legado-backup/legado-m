package io.legado.app.ui.book.group

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-42 放量批：书架「分组」三弹窗宿主主题作用域守护。
 *
 * 原内容根为 `LegadoComposeTheme`（**只透传字体层、不提供色板**）⇒ 主题包/夜间/自定义主题色下
 * 这三处弹窗回落 M3 默认色板；本批上提为 `LegadoTheme`（= `MaterialTheme(colorScheme, LegadoTypography)`，
 * 是原层的**严格超集**：色板 + 同一套排版；见 `ui/theme/LegadoTheme.kt:105-110`）。
 */
class GroupDialogsThemeScopeTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val files = listOf(
        "src/main/java/io/legado/app/ui/book/group/GroupEditDialog.kt",
        "src/main/java/io/legado/app/ui/book/group/GroupManageDialog.kt",
        "src/main/java/io/legado/app/ui/book/group/GroupSelectDialog.kt",
    )

    @Test
    fun `三弹窗内容根均已上提 LegadoTheme`() {
        files.forEach { rel ->
            val src = code(rel)
            assertEquals("$rel 须引入 LegadoTheme", true,
                src.contains("import io.legado.app.ui.theme.LegadoTheme"))
            assertEquals("$rel setContent 内容根须为 LegadoTheme", true, src.contains("LegadoTheme {"))
            assertEquals("$rel 不得再以 LegadoComposeTheme 作内容根", false,
                src.contains("LegadoComposeTheme {"))
        }
    }
}
