package io.legado.app.ui.widget.compose

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71：`LegadoComposeTheme` 必须**委派**到 `lib/theme` 字体族单源，不得自带第二份映射实现
 * （重复实现的相同逻辑会随主题能力演进而单边漂移）。
 *
 * 语义仍为「字体层 + 透传色板」（不改其既有语义，spec N3 不违）；因字体族已由唯一主题入口
 * `LegadoTheme` 下发，本组件当前**冗余**，仅保留以兼容既有嵌套写法。
 */
class LegadoComposeThemeDelegationTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val rel = "src/main/java/io/legado/app/ui/widget/compose/LegadoComposeTheme.kt"

    @Test
    fun `字体族映射已委派单源且无双份实现`() {
        val src = code(rel)
        assertEquals(
            "必须引入 lib/theme 的字体族单源",
            1,
            Regex("import io\\.legado\\.app\\.lib\\.theme\\.withThemeFontFamilies").findAll(src).count()
        )
        assertEquals(
            "typography 必须经单源 withThemeFontFamilies 下发",
            1,
            Regex("MaterialTheme\\.typography\\.withThemeFontFamilies\\(bodyFamily, titleFamily\\)").findAll(src).count()
        )
        assertEquals(
            "私有第二份映射实现必须已删除（15 槽位 copy 不得残留）",
            0,
            Regex("private fun Typography\\.withUiFontFamilies|withUiFontFamilies\\(").findAll(src).count()
        )
        assertEquals(
            "字体族须由单源读取（随主题签名重建）",
            1,
            Regex("val \\(bodyFamily, titleFamily\\) = rememberThemeFontFamilies\\(\\)").findAll(src).count()
        )
    }
}
