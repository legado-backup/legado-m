package io.legado.app.ui.theme

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71：`LegadoTheme` 作为**唯一主题入口**，必须同时给出色板 + 字号 + 主题字体族。
 *
 * 回归背景：批 A 把宿主内容根由 `LegadoComposeTheme`（字体层）换成 `LegadoTheme`，
 * 而 `LegadoTheme` 当时只设 `LegadoTypography`（仅字号，`fontFamily` 为空）⇒ 用户设置的
 * 「系统内置字体样式 / 自定义界面·标题字体文件」在这些宿主内失效。本测试锁死字体族已在
 * `LegadoTheme` 内下发（映射本身的行为断言见 `lib/theme/ThemeFontFamiliesTest`）。
 */
class LegadoThemeFontLayerTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val rel = "src/main/java/io/legado/app/ui/theme/LegadoTheme.kt"

    @Test
    fun `LegadoTheme 已下发主题字体族`() {
        val src = code(rel)
        assertEquals(
            "必须引入字体族单源（lib/theme）",
            1,
            Regex("import io\\.legado\\.app\\.lib\\.theme\\.withThemeFontFamilies").findAll(src).count()
        )
        assertEquals(
            "必须引入字体族读取单源（lib/theme）",
            1,
            Regex("import io\\.legado\\.app\\.lib\\.theme\\.rememberThemeFontFamilies").findAll(src).count()
        )
        assertEquals(
            "typography 必须经 withThemeFontFamilies 下发（否则 Compose 文本回落系统字体）",
            1,
            Regex("LegadoTypography\\.withThemeFontFamilies\\(bodyFamily, titleFamily\\)").findAll(src).count()
        )
        assertEquals(
            "字体族须由单源 rememberThemeFontFamilies() 读取（随主题签名重建）",
            1,
            Regex("val \\(bodyFamily, titleFamily\\) = rememberThemeFontFamilies\\(\\)").findAll(src).count()
        )
    }
}
