package io.legado.app.lib.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.FontFamily
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Test

/**
 * NEW-71：主题字体族下发单源（[withThemeFontFamilies]）行为契约。
 *
 * 背景：字体族映射原先只存在于 `ui/widget/compose/LegadoComposeTheme.kt`（私有实现）⇒
 * 「只包 `LegadoTheme`」的宿主（含 `setLegadoContent` 全页路径）拿不到主题字体，
 * Compose 文本回落系统默认字体，与 View 页字体口径不一致。
 *
 * 本测试锁死映射口径（**真行为断言**，非源文本探针）：标题字体下发到
 * display/headline/titleLarge 共 7 槽位，界面字体下发到其余 8 槽位，合计 15 槽位全覆盖。
 */
class ThemeFontFamiliesTest {

    /** 刻意用两个可区分且不相同的族，避免"都下发同一族"的假通过。 */
    private val titleFamily = FontFamily.Monospace
    private val bodyFamily = FontFamily.Serif

    @Test
    fun `标题槽位下发标题字体`() {
        val t = Typography().withThemeFontFamilies(body = bodyFamily, title = titleFamily)
        val titleSlots = mapOf(
            "displayLarge" to t.displayLarge,
            "displayMedium" to t.displayMedium,
            "displaySmall" to t.displaySmall,
            "headlineLarge" to t.headlineLarge,
            "headlineMedium" to t.headlineMedium,
            "headlineSmall" to t.headlineSmall,
            "titleLarge" to t.titleLarge
        )
        titleSlots.forEach { (name, style) ->
            assertSame("$name 必须下发标题字体", titleFamily, style.fontFamily)
        }
        assertEquals("标题族槽位数必须为 7", 7, titleSlots.size)
    }

    @Test
    fun `正文与标签槽位下发界面字体`() {
        val t = Typography().withThemeFontFamilies(body = bodyFamily, title = titleFamily)
        val bodySlots = mapOf(
            "titleMedium" to t.titleMedium,
            "titleSmall" to t.titleSmall,
            "bodyLarge" to t.bodyLarge,
            "bodyMedium" to t.bodyMedium,
            "bodySmall" to t.bodySmall,
            "labelLarge" to t.labelLarge,
            "labelMedium" to t.labelMedium,
            "labelSmall" to t.labelSmall
        )
        bodySlots.forEach { (name, style) ->
            assertSame("$name 必须下发界面字体", bodyFamily, style.fontFamily)
        }
        assertEquals("正文/标签族槽位数必须为 8", 8, bodySlots.size)
    }

    @Test
    fun `全 15 槽位均被覆盖（无遗漏槽位）`() {
        val t = Typography().withThemeFontFamilies(body = bodyFamily, title = titleFamily)
        val all = listOf(
            t.displayLarge, t.displayMedium, t.displaySmall,
            t.headlineLarge, t.headlineMedium, t.headlineSmall,
            t.titleLarge, t.titleMedium, t.titleSmall,
            t.bodyLarge, t.bodyMedium, t.bodySmall,
            t.labelLarge, t.labelMedium, t.labelSmall
        )
        assertEquals("Typography 槽位总数必须为 15", 15, all.size)
        assertEquals(
            "任一槽位 fontFamily 为空即说明映射有遗漏",
            0,
            all.count { it.fontFamily == null }
        )
    }
}
