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

    /**
     * 解析**优先级**不变量（2026-09-24 用户复现澄清后固化）。
     *
     * 顶栏包是「顶栏样式」的更具体用户设置 ⇒ 其字面色优先；主题面 token 仅在顶栏包**未声明**该面时参与。
     * ⚠ 主题列表切换主题**不会**切换顶栏包（`topBarPackageNight` 不变），故「顶栏包钉了标签色时
     * 切主题不变色」是**预期交互**（已在 `ui-standards/color.md` §三 第 5 条登记）；
     * 需要「标签随主题配套变化」应改用套件应用。此断言用于防止后续把顺序再翻回去（来回横跳）。
     */
    @Test
    fun precedence_packageLiteralBeforeThemeToken() {
        val code = sourceCode()
        val packageAt = code.indexOf("val tagBarColor = config.tagBarColor")
        val themeTokenAt = code.indexOf("context.themeColorOrNull(PreferKey.themeTabBackgroundColor)")
        assertTrue("未定位到顶栏包字面色解析", packageAt >= 0)
        assertTrue("未定位到主题面 token 解析", themeTokenAt >= 0)
        assertTrue(
            "顶栏包字面色必须先于主题面 token（更具体的用户设置优先）",
            packageAt < themeTokenAt
        )
    }
}