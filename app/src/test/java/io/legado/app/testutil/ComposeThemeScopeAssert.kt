package io.legado.app.testutil

import java.io.File
import org.junit.Assert.assertTrue

/**
 * Compose 宿主主题作用域 / 弹层取色的**源契约**断言工具（JVM 单测用）。
 *
 * 背景（fix-compose-theme-scope-and-cache-icon AD-01 / AD-06）：
 * - `LegadoComposeTheme` 只透传 `MaterialTheme.colorScheme` 并覆盖字体族，**不提供色板**；
 *   宿主内容若不在 `LegadoTheme` 作用域内，`MaterialTheme.colorScheme` 会回落 M3 默认亮色基线
 *   ⇒ 夜间主题下弹层出现「黑字黑图标」。
 * - 弹层/对话框组件的文字与图标取色必须走 `AppDialogStyle` 直色 / 弹层内容色，
 *   **禁止** `MaterialTheme.colorScheme.onSurface(Variant)` 等 M3 派生色。
 *
 * 说明（诚实披露已知上限）：本工具是**源文本契约**（非运行期组合断言）——项目无 Robolectric、
 * `app/src/androidTest` 已知不可执行，运行期断言不可得；主防线是门禁
 * `ai_tests/scripts/audit_compose_theme_scope.py`（G-37），本工具同时充当测试铁律的配对凭据。
 */
object ComposeThemeScopeAssert {

    /** 主题作用域合法形态（顶层出现即视为已覆盖）；`LegadoComposeTheme` 不计。 */
    private val acceptedScopes = listOf(
        Regex("(?<![A-Za-z0-9_])LegadoTheme\\s*\\{"),
        Regex("(?<![A-Za-z0-9_])LegadoThemeWithBackground\\s*\\("),
        Regex("(?<![A-Za-z0-9_])setLegadoContent\\s*\\(")
    )

    private val m3DerivedTextColor = Regex(
        "MaterialTheme\\.colorScheme\\.(onSurface|onSurfaceVariant|surface|surfaceVariant|secondaryContainer|outline)\\b"
    )

    /** 定位仓库根（单测工作目录通常为模块目录 `app/`，故逐级上溯找 settings.gradle）。 */
    fun repoRoot(): File {
        var dir: File? = File("").absoluteFile
        var guard = 0
        while (dir != null && guard < 6) {
            if (File(dir, "settings.gradle").exists() || File(dir, "settings.gradle.kts").exists()) {
                return dir
            }
            dir = dir.parentFile
            guard++
        }
        throw IllegalStateException("未找到仓库根（含 settings.gradle 的目录），CWD=${File("").absolutePath}")
    }

    /** 读取 `app/src/main/java` 下的源文件内容。 */
    fun sourceText(relPath: String): String {
        val f = File(repoRoot(), "app/src/main/java/$relPath")
        assertTrue("源文件不存在：app/src/main/java/$relPath", f.isFile)
        return f.readText()
    }

    /**
     * 断言：宿主入口（`attachComposeContent{…}` / `setContent{…}`）的**顶层**存在主题作用域。
     * 与门禁 G-37 同口径（顶层作用域），故「LegadoTheme 只包顶栏、内容先 Column」的旧形态会失败。
     */
    fun assertHostProvidesThemeScope(relPath: String) {
        val text = sourceText(relPath)
        val blocks = locateHostBlocks(text)
        assertTrue("$relPath 未找到 Compose 宿主入口（attachComposeContent / setContent）", blocks.isNotEmpty())
        blocks.forEach { openIdx ->
            val top = topLevelSlice(text, openIdx)
            assertTrue(
                "$relPath 的宿主内容顶层缺少主题作用域（LegadoTheme{…}）——" +
                    "LegadoComposeTheme 只透传色板、不算作用域",
                acceptedScopes.any { it.containsMatchIn(top) }
            )
        }
    }

    /** 断言：该文件不再使用 M3 派生色作文字/图标/面（弹层取色单源 AD-06）。 */
    fun assertNoM3DerivedTextColor(relPath: String) {
        // 先剥离注释/字符串：否则「注释里提到该键」会被误判为违规
        val text = stripCommentsAndStrings(sourceText(relPath))
        val hit = m3DerivedTextColor.find(text)
        assertTrue(
            "$relPath 仍存在 M3 派生色取色：${hit?.value}（应改走 AppDialogStyle 直色 / 弹层内容色）",
            hit == null
        )
    }

    // ---------------------------------------------------------------- 内部实现

    private fun locateHostBlocks(text: String): List<Int> {
        val stripped = stripCommentsAndStrings(text)
        val opens = mutableListOf<Int>()
        // attachComposeContent 有两种调用形态：省略参数括号（尾随 lambda，全仓主流）与显式括号
        Regex("attachComposeContent\\s*([({])").findAll(stripped).forEach { m ->
            val open = if (stripped[m.range.last] == '{') {
                m.range.last
            } else {
                val close = matchParen(stripped, m.range.last)
                if (close > 0) nextBrace(stripped, close + 1) else -1
            }
            if (open > 0) opens.add(open)
        }
        Regex("(?<![A-Za-z0-9_])setContent\\s*\\{").findAll(stripped).forEach { m ->
            opens.add(m.range.last)
        }
        return opens
    }

    private fun matchParen(text: String, openIdx: Int): Int {
        var depth = 0
        for (i in openIdx until text.length) {
            when (text[i]) {
                '(' -> depth++
                ')' -> {
                    depth--
                    if (depth == 0) return i
                }
            }
        }
        return -1
    }

    private fun nextBrace(text: String, from: Int): Int {
        var i = from
        while (i < text.length && text[i].isWhitespace()) i++
        return if (i < text.length && text[i] == '{') i else -1
    }

    /**
     * 取花括号块内 depth==1 的文本。
     * ⚠ 从 depth 1→2 的子块起始 `{` 必须保留，否则 `LegadoTheme {` 会被截成 `LegadoTheme `
     * 而被误判为缺失（与门禁 G-37 同口径）。
     */
    private fun topLevelSlice(text: String, openIdx: Int): String {
        val sb = StringBuilder()
        var depth = 0
        var i = openIdx
        while (i < text.length) {
            when (text[i]) {
                '{' -> {
                    if (depth == 1) sb.append('{')
                    depth++
                    i++
                }
                '}' -> {
                    depth--
                    if (depth == 0) return sb.toString()
                    i++
                }
                else -> {
                    if (depth == 1) sb.append(text[i])
                    i++
                }
            }
        }
        return sb.toString()
    }

    /** 剥离注释与字符串字面量内容（保留换行），避免"注释里写一次"造成假通过。 */
    private fun stripCommentsAndStrings(text: String): String {
        val out = text.toCharArray()
        var i = 0
        fun blank(from: Int, to: Int) {
            for (k in from until minOf(to, out.size)) if (out[k] != '\n') out[k] = ' '
        }
        while (i < text.length) {
            when {
                text.startsWith("//", i) -> {
                    val j = text.indexOf('\n', i).let { if (it == -1) text.length else it }
                    blank(i, j)
                    i = j
                }
                text.startsWith("/*", i) -> {
                    val j = text.indexOf("*/", i + 2).let { if (it == -1) text.length else it + 2 }
                    blank(i, j)
                    i = j
                }
                text[i] == '"' -> {
                    val j = if (text.startsWith("\"\"\"", i)) {
                        text.indexOf("\"\"\"", i + 3).let { if (it == -1) text.length else it + 3 }
                    } else {
                        var k = i + 1
                        while (k < text.length) {
                            if (text[k] == '\\') {
                                k += 2
                                continue
                            }
                            if (text[k] == '"') {
                                k++
                                break
                            }
                            k++
                        }
                        k
                    }
                    blank(i, j)
                    i = j
                }
                else -> i++
            }
        }
        return String(out)
    }
}