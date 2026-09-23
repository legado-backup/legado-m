package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 外观套件顶栏包「不得钉死标签栏字面色」不变量（2026-09-23 用户实证缺陷）。
 *
 * 缺陷：暗夜紫套件的顶栏包把 `tagBarColor`/`tagSelectedColor` 写成**字面色**（KDoc 写着「贴主题色」），
 * 而字面色运行时优先于主题面 token ⇒ **标签栏永不随主题变化**
 * （真机实证：页面主题为深棕、选中标签仍为固定紫色）。
 *
 * 修复口径：套件顶栏包两个标签色留空，交回主题面 token
 * （栏底 = `themeTabBackgroundColor`，选中底 = 主题强调色；套件主题自身已声明 `tabBackgroundColor`，
 * 故紫调观感延续）。
 */
class AppearanceKitTopBarTagColorTest {

    private fun sourceCode(): String {
        val rel = "src/main/java/io/legado/app/help/config/AppearanceKitManager.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    private fun darkPurpleTopBarBody(code: String): String {
        val start = code.indexOf("private fun darkPurpleTopBarConfig(")
        assertTrue("未定位到 darkPurpleTopBarConfig", start >= 0)
        return code.substring(start, code.indexOf("\n    )", start))
    }

    @Test
    fun kitTopBarPackage_mustNotPinTagColorsAsLiterals() {
        val body = darkPurpleTopBarBody(sourceCode())
        assertTrue(
            "套件顶栏包 tagBarColor 必须留空（交回主题面 token），不得写字面色",
            Regex("tagBarColor\\s*=\\s*null").containsMatchIn(body)
        )
        assertTrue(
            "套件顶栏包 tagSelectedColor 必须留空（交回主题强调色），不得写字面色",
            Regex("tagSelectedColor\\s*=\\s*null").containsMatchIn(body)
        )
        assertFalse(
            "不得再出现 0xFF… 形式的标签色字面量（会导致标签栏不随主题变化）",
            Regex("tag(Bar|Selected)Color\\s*=\\s*0x").containsMatchIn(body)
        )
    }

    /** 仍须保留 regular 形态 + 非零不透明度（否则栏底退化为完全无填充，失去可辨识的栏面）。 */
    @Test
    fun kitTopBarPackage_keepsRegularStyleAndVisibleAlpha() {
        val body = darkPurpleTopBarBody(sourceCode())
        assertTrue(body.contains("TopBarConfig.STYLE_REGULAR"))
        assertTrue(Regex("tagBarAlpha\\s*=\\s*if\\s*\\(isNightMode\\)").containsMatchIn(body))
    }
}