package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R14（B3）选中文字「编辑此处」动作的**配置白名单**不变量。
 *
 * 缺陷型（B2.5 划线动作已踩过同一坑）：`ContentSelectMenuConfigDialog.sanitizeActionIds` 的白名单由
 * `actionItems` 列表派生 —— 新增动作若**未登记**在此，用户在选区菜单配置页保存一次后该动作会被
 * **静默剔除**、菜单里永久消失（表现为「功能做完了但用户看不到」）。
 */
class ContentSelectEditHereActionTest {

    private fun sourceCode(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/config/ContentSelectMenuConfigDialog.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun editHereAction_isRegisteredInWhitelist() {
        val code = sourceCode()
        assertTrue(
            "「编辑此处」动作必须登记在 actionItems（否则保存配置后会被静默剔除）",
            code.contains("ActionItem(ContentSelectConfig.ACTION_EDIT_HERE")
        )
        assertTrue("动作文案须有字符串资源", code.contains("R.string.edit_here"))
    }
}