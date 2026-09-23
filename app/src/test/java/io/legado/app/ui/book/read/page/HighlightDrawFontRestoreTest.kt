package io.legado.app.ui.book.read.page

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B6 · R26 绘制期覆盖/复位的配对不变量（源码级）。
 *
 * 为什么单独守：`applyTextStyle`/`restoreTextStyle` 共用**全局 `ChapterProvider.contentPaint`**，
 * 逐列覆写后若漏复位，字号/字距会**泄漏到后续列与行**（表现为整段文字忽大忽小）。
 * 该对象无 JVM 可测的纯逻辑（依赖 android.graphics），故用源码不变量固化「保存 → 覆写 → 复位」三件。
 */
class HighlightDrawFontRestoreTest {

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/page/HighlightDraw.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun applySavesAndOverridesThenRestores() {
        val code = source()
        val apply = code.substringAfter("fun applyTextStyle(").substringBefore("fun restoreTextStyle(")
        val restore = code.substringAfter("fun restoreTextStyle(").substringBefore("fun drawEmphasis(")
        // 保存原值
        assertTrue("必须保存原字号", apply.contains("paint.textSize,"))
        assertTrue("必须保存原字距", apply.contains("paint.letterSpacing"))
        // 覆写
        assertTrue(
            "必须按倍率覆写字号",
            apply.contains("paint.textSize = saved.textSize * style.resolvedFontScale")
        )
        assertTrue(
            "必须按增量覆写字距",
            apply.contains("paint.letterSpacing = saved.letterSpacing + style.resolvedLetterSpacingEm")
        )
        // 复位
        assertTrue("必须复位字号", restore.contains("paint.textSize = saved.textSize"))
        assertTrue("必须复位字距", restore.contains("paint.letterSpacing = saved.letterSpacing"))
        // 既有通道不得被漏掉（粗体/斜体/字体/阴影复位仍在）
        assertTrue(restore.contains("paint.isFakeBoldText = saved.bold"))
        assertTrue(restore.contains("paint.clearShadowLayer()"))
    }

    /** 未设置新通道时不得触碰画笔（零回归：旧样式渲染与改造前逐像素一致）。 */
    @Test
    fun unsetFieldsDoNotTouchPaint() {
        val apply = source().substringAfter("fun applyTextStyle(").substringBefore("fun restoreTextStyle(")
        assertTrue(
            "字号覆写必须在「已设置」分支内",
            apply.contains("if (style.fontScale != null) {")
        )
        assertTrue(
            "字距覆写必须在「已设置」分支内",
            apply.contains("if (style.letterSpacingEm != null) {")
        )
    }
}