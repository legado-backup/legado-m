package io.legado.app.ui.widget

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 标签栏「随主题联动」不变量（2026-09-23 用户实证缺陷）。
 *
 * 缺陷：书架 / 订阅源「标签」布局模式下，标签栏底色与选中标签底色**不随主题变化**。
 * 根因两类：
 * 1) 面 token 未自定义时兜底为静态灰资源（已在 `ThemeUiPalette.SurfaceLadder` 侧修，见 `SurfaceLadderTest`）；
 * 2) 本组件的**栏底解析顺序**把「顶栏包字面色」放在主题面 token 之前，且 regular 形态直接落「无填充」，
 *    使外观套件（regular + `tagBarAlpha>0`）钉死字面色时主题面**无法介入**；
 *    选中标签底的兜底取 `cardColor`（与未选中共族、且不随主题强调色变化）。
 *
 * 本测试固化修复后的解析顺序与兜底口径，防止静默回退。
 */
class RoundedTagBarViewThemeFollowTest {

    private fun sourceCode(): String {
        val rel = "src/main/java/io/legado/app/ui/widget/RoundedTagBarView.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun tagBarColor_resolvesThemeTokenBeforeRegularNoFillBranch() {
        val code = sourceCode()
        val tokenAt = code.indexOf("context.themeColorOrNull(PreferKey.themeTabBackgroundColor)")
        val regularAt = code.indexOf("config.style == TopBarConfig.STYLE_REGULAR")
        assertTrue("栏底解析必须读取主题面 token themeTabBackgroundColor", tokenAt >= 0)
        assertTrue("栏底解析必须保留 regular 判定分支", regularAt >= 0)
        assertTrue(
            "主题面 token 必须位于 regular「无填充」分支之前，否则套件钉色时主题面无法介入",
            tokenAt < regularAt
        )
    }

    @Test
    fun selectedTagBackground_fallsBackToThemeAccent() {
        val code = sourceCode()
        val start = code.indexOf("val selectedColor = config.tagSelectedColor")
        assertTrue("未定位到选中标签底解析", start >= 0)
        val segment = code.substring(start, start + 120)
        assertTrue(
            "选中标签底兜底必须是主题强调色（与 Compose AppFilterChip 同口径）",
            segment.contains("context.accentColor")
        )
        assertFalse(
            "选中标签底不得再以 cardColor 兜底（与未选中共族且不随主题强调色变化）",
            segment.contains("themeCardColorOrDefault")
        )
    }

    @Test
    fun contrastFallback_stillSingleSource() {
        assertTrue("对比度兜底必须仍走单源 contrastOnColor", sourceCode().contains("contrastOnColor("))
    }
}