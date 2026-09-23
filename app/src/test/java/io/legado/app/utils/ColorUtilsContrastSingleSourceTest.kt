package io.legado.app.utils

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 对比度兜底单源不变量回归测试（B7 R31，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 D3）：同语义对比度兜底曾**三套并存**——
 * `BadgeDot.badgeTextBright`（亮度加权公式）、`RoundedTagBarView.readableTagTextColor`
 * （黑白内联推导）、`ThemeSpec.contrastOn`（另一份判据）⇒ 同主题下不同控件的兜底文字色分叉。
 *
 * 收敛后唯一真值 = `ColorUtils.contrastOnColor`（View 与 Compose 双栈共用；Compose 侧
 * `contrastOn` 仅做 Color ↔ ARGB 域转换后转发）。
 *
 * 本项目单测无 Robolectric 且 `returnDefaultValues = true` ⇒ `android.graphics.Color` /
 * `ColorUtils.calculateLuminance` 全桩化，无法对真实颜色做判据断言，故按**结构不变量**固化。
 */
class ColorUtilsContrastSingleSourceTest {

    private fun read(rel: String): String {
        val relUnderApp = "src/main/java/io/legado/app/$rel"
        val candidates = listOf(File(relUnderApp), File("../app/$relUnderApp"), File("app/$relUnderApp"))
        return candidates.firstOrNull { it.isFile }?.readText()
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$relUnderApp")
    }

    /** 真值单源必须存在且落在 ColorUtils（双栈共用点）。 */
    @Test
    fun contrastSingleSource_isDeclaredInColorUtils() {
        val text = read("utils/ColorUtils.kt")
        assertTrue("应在 ColorUtils 声明 contrastOnColor 单源", text.contains("fun contrastOnColor("))
    }

    /** Compose 侧不得就地重写亮度判据（必须转发单源）。 */
    @Test
    fun composeContrastOn_delegatesInsteadOfReimplementing() {
        val text = read("ui/widget/components/ThemeSpec.kt")
        assertTrue("Compose contrastOn 应转发 contrastOnColor", text.contains("contrastOnColor("))
    }

    /** View 侧标签栏不得再自建黑白兜底（必须转发单源）。 */
    @Test
    fun viewContrastFallback_delegatesInsteadOfReimplementing() {
        val text = read("ui/widget/RoundedTagBarView.kt")
        assertTrue("View 侧应转发 contrastOnColor", text.contains("contrastOnColor("))
    }
}