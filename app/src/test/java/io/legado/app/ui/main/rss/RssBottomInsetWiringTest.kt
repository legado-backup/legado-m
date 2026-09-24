package io.legado.app.ui.main.rss

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1 配对（订阅-classic）：View 侧经典列表必须调用 `applyMainBottomBarPadding()`。
 *
 * 该 import 曾长期为**死引用**（只 import 不调用），classic 列表底部 padding 被显式归零且无补偿
 * ⇒ 滚到底被底栏遮挡（用户 2026-09-24 报障）。工具内部 = 导航栏 inset + `main_content_bottom_bar_padding`。
 */
class RssBottomInsetWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun rssClassicList_appliesMainBottomBarPadding() {
        val src = code("ui/main/rss/RssFragment.kt")
        assertFalse(
            "不得只剩死 import：必须真实调用 applyMainBottomBarPadding()",
            src.contains("import io.legado.app.utils.applyMainBottomBarPadding") &&
                !src.contains("applyMainBottomBarPadding()")
        )
        assertTrue(
            "经典列表必须叠加底栏安全区留白（先归零再叠加）",
            src.contains("applyMainBottomBarPadding()")
        )
    }
}