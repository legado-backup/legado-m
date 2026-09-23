package io.legado.app.help

import io.legado.app.utils.GSON
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B6 · R26「高亮字号/字距独立调整」单测。
 *
 * 验收口径（tasks §6.2）：
 * - **R26-3 旧 JSON（无新字段）反序列化**必须零回归（字段为 null ⇒ 不覆写画笔）；
 * - R26-2 默认值不改渲染（`resolved*` 回退 1.0 / 0）；
 * - 域越界必须被 `sanitized()` 夹回（手改 JSON 不得把正文挤出列宽）。
 */
class HighlightStyleFontOverrideTest {

    /** R26-3：旧 JSON（改造前写入的样式）反序列化后不得带任何新通道值。 */
    @Test
    fun legacyJsonWithoutNewFields_deserializesToNull() {
        val legacyJson = """{"fill":-123456,"bold":true,"underline":{"kind":"WAVY","color":0}}"""
        val style = GSON.fromJson(legacyJson, HighlightStyle::class.java)
        assertNull("旧 JSON 不得凭空产生字号倍率", style.fontScale)
        assertNull("旧 JSON 不得凭空产生字距增量", style.letterSpacingEm)
        assertFalse("未设置 ⇒ 不得进入绘制期覆写", style.hasFontOverrides)
        assertEquals("未设置 ⇒ 倍率回退 1.0（零回归）", 1f, style.resolvedFontScale, 0f)
        assertEquals("未设置 ⇒ 字距回退 0（零回归）", 0f, style.resolvedLetterSpacingEm, 0f)
    }

    /** 新 JSON 往返一致（导出/导入/规则编辑共用同一序列化口径）。 */
    @Test
    fun newFields_roundTrip() {
        val style = HighlightStyle(fontScale = 1.08f, letterSpacingEm = 0.06f)
        val restored = GSON.fromJson(GSON.toJson(style), HighlightStyle::class.java)
        assertEquals(style, restored)
        assertTrue(restored.hasFontOverrides)
    }

    /** R26-2 + 越界：sanitized 必须把倍率/字距夹进域内（含手改 JSON 的极端值）。 */
    @Test
    fun sanitized_clampsOutOfRangeValues() {
        assertEquals(
            HighlightStyle.MAX_FONT_SCALE,
            HighlightStyle(fontScale = 9f).sanitized().fontScale!!
        )
        assertEquals(
            HighlightStyle.MIN_FONT_SCALE,
            HighlightStyle(fontScale = 0.1f).sanitized().fontScale!!
        )
        assertEquals(
            HighlightStyle.MAX_LETTER_SPACING_EM,
            HighlightStyle(letterSpacingEm = 5f).sanitized().letterSpacingEm!!
        )
        assertEquals(
            HighlightStyle.MIN_LETTER_SPACING_EM,
            HighlightStyle(letterSpacingEm = -1f).sanitized().letterSpacingEm!!
        )
        // 域内值不得被改写（幂等）
        val inside = HighlightStyle(fontScale = 1.05f, letterSpacingEm = 0.05f).sanitized()
        assertEquals(1.05f, inside.fontScale!!, 0f)
        assertEquals(0.05f, inside.letterSpacingEm!!, 0f)
    }

    /** 仅设置字号/字距的样式**不是空样式**（否则会被判为「无高亮」而整段跳过）。 */
    @Test
    fun fontOverrideOnlyStyle_isNotEmptyAndNeedsPerColumnDraw() {
        val style = HighlightStyle(fontScale = 1.05f)
        assertFalse("仅字号覆写不得判为空样式", style.isEmpty)
        assertTrue("仅字号覆写必须走逐列绘制", style.needsPerColumnDraw)
    }

    /** 非法（≤0）倍率回退 1.0，不得产生 0 字号（会把正文画没）。 */
    @Test
    fun nonPositiveFontScale_fallsBackToOne() {
        @Suppress("SENSELESS_COMPARISON")
        val style = HighlightStyle(fontScale = 0f)
        assertEquals(1f, style.resolvedFontScale, 0f)
        // 经 sanitized 后仍不得出现 0（先夹到 MIN）
        assertEquals(HighlightStyle.MIN_FONT_SCALE, style.sanitized().fontScale!!)
    }

    /** 绘制期覆写/复位必须成对出现在唯一出口（漏复位 ⇒ 字号泄漏到后续列/行）。 */
    @Test
    fun applyAndRestoreCoverTextSizeAndLetterSpacing() {
        val rel = "src/main/java/io/legado/app/ui/book/read/page/HighlightDraw.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        val source = file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        val apply = source.substringAfter("fun applyTextStyle(").substringBefore("fun restoreTextStyle(")
        val restore = source.substringAfter("fun restoreTextStyle(").substringBefore("fun drawEmphasis(")
        assertTrue("apply 必须保存原字号", apply.contains("paint.textSize,"))
        assertTrue("apply 必须按倍率覆写字号", apply.contains("paint.textSize = saved.textSize * style.resolvedFontScale"))
        assertTrue("apply 必须按增量覆写字距", apply.contains("paint.letterSpacing = saved.letterSpacing + style.resolvedLetterSpacingEm"))
        assertTrue("restore 必须复位字号", restore.contains("paint.textSize = saved.textSize"))
        assertTrue("restore 必须复位字距", restore.contains("paint.letterSpacing = saved.letterSpacing"))
    }
}