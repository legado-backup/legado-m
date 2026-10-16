package io.legado.app.ui.main.readrecord

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-42 放量批：阅读记录页 8 处 Compose 宿主主题作用域守护。
 *
 * 原 8 处内容根为 `LegadoComposeTheme`（只透传字体层）⇒ 主题包/夜间下回落 M3 默认色板；
 * 本批统一上提为 `LegadoTheme`（色板 + 同一套排版，严格超集）。
 */
class ReadRecordFragmentThemeScopeTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `阅读记录页 8 处内容根均已上提 LegadoTheme`() {
        val src = code("src/main/java/io/legado/app/ui/main/readrecord/ReadRecordFragment.kt")
        assertEquals("须引入 LegadoTheme", true, src.contains("import io.legado.app.ui.theme.LegadoTheme"))
        // 8 个宿主入口逐处上提（计数断言 ⇒ 少改一处即失败）
        assertEquals("LegadoTheme 内容根应为 8 处", 8, src.split("LegadoTheme {").size - 1)
        assertEquals("不得再以 LegadoComposeTheme 作内容根", false, src.contains("LegadoComposeTheme {"))
    }
}
