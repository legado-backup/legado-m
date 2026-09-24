package io.legado.app.base

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-1「底栏安全区统一」的**结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：主壳 `activity_main.xml` 中 `content_container` 与 `bottom_controls` 是**同层兄弟**
 * ⇒ 底栏是 overlay，承载于 `LockableViewPager` 内的页面必须自加底部留白，否则滚到底时
 * 最后一项被底栏遮挡（用户 2026-09-24 报障）。历史实现有两个问题：
 * ①Compose 侧只取静态 dp（另有 86dp 硬编码三处）⇒ 三键导航设备必然遮挡；
 * ②View 侧工具把 90dp 写成字面量、且注释声称「目标项目无对应 dimen」（与企业实际不符）。
 *
 * 本测试把「单源 + 主 Tab 页必须引用 + 禁止硬编码回流」固化为断言 —— 只写文档的约束一律失效，
 * 故必须以可机检的不变量兜底（同 `BareAndroidLogCleanupTest` 口径）。
 */
class BottomBarInsetWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    private val mainTabPages = listOf(
        "ui/main/bookshelf/BookshelfScreen.kt",
        "ui/main/explore/ExploreModernListScreen.kt",
        "ui/adapter/SourceFolderComposeGrid.kt",
    )

    @Test
    fun singleSource_tool_usesDimenAndNavInset() {
        val tool = code("base/ComposeMainInsets.kt")
        assertTrue(
            "单源工具必须取 dimen（而非字面量 dp）",
            tool.contains("R.dimen.main_content_bottom_bar_padding")
        )
        assertTrue(
            "单源工具必须叠加导航栏 inset（三键导航 inset≈48dp，只取静态 dp 必被遮挡）",
            tool.contains("WindowInsets.navigationBars")
        )
        assertTrue("必须导出可复用的 contentPadding 入口", tool.contains("fun mainBottomBarContentPadding("))
    }

    @Test
    fun mainTabPages_referenceSingleSource() {
        mainTabPages.forEach { rel ->
            assertTrue(
                "承载于主壳底栏之上的页面必须引用单源留白（$rel）",
                code(rel).contains("mainBottomBarContentPadding(")
            )
        }
        assertTrue(
            "订阅 classic 列表（View 侧）必须调用 applyMainBottomBarPadding()",
            code("ui/main/rss/RssFragment.kt").contains("applyMainBottomBarPadding()")
        )
    }

    @Test
    fun mainTabPages_haveNoHardcodedBottomSpacer() {
        mainTabPages.forEach { rel ->
            assertFalse(
                "禁止硬编码底栏留白（$rel 出现 bottom = 86.dp 之类）",
                Regex("bottom\\s*=\\s*\\d+\\.dp").containsMatchIn(code(rel))
            )
        }
    }

    @Test
    fun viewSideTool_usesDimenNotLiteral() {
        val tool = code("utils/ViewExtensions.kt")
        assertTrue(
            "View 侧工具必须走 dimen 单源",
            tool.contains("getDimensionPixelSize(R.dimen.main_content_bottom_bar_padding)")
        )
        assertFalse(
            "不得回退为 90dp 字面量（会导致单源漂移）",
            tool.contains("navigationBarHeight + 90.dpToPx()")
        )
    }
}