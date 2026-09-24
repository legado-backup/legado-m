package io.legado.app.utils

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1 配对（View 侧工具）：`applyMainBottomBarPadding` 必须读 **dimen 单源**、不得用字面量 dp。
 *
 * 改造前实现为 `navigationBarHeight + 90.dpToPx()`（字面量），且注释宣称「目标项目无对应 dimen」——
 * 该 dimen 实际存在于 `res/values/dimens.xml`（`main_content_bottom_bar_padding` = 90dp）
 * ⇒ 注释与事实不符，已一并纠正。字面量与 Compose 侧单源并存会造成「同一语义两套口径」，
 * 任一侧调整即漂移（本次 Bug 的根因之一）。
 */
class ViewExtensionsBottomInsetTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun applyMainBottomBarPadding_readsDimen_notLiteral() {
        val src = code("utils/ViewExtensions.kt")
        assertTrue(
            "必须读 dimen 单源 main_content_bottom_bar_padding",
            src.contains("getDimensionPixelSize(R.dimen.main_content_bottom_bar_padding)")
        )
        assertFalse(
            "不得回退为 90dp 字面量（单源漂移风险）",
            src.contains("navigationBarHeight + 90.dpToPx()")
        )
    }
}