package io.legado.app.ui.rss.search

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CA′ 1.2「B→A 写法归一」的**结构不变量**（配对测试，JVM 可跑）。
 *
 * 本页原为 B 旧写法（手写 `ComposeView + setViewCompositionStrategy + setContent`），现归一到
 * `View.attachComposeContent` 单源；**`LegadoTheme { }` 主题包裹必须保留**。另断言数据桥接逻辑
 * （从 `RssSearchSourceHolder` 读数据 + 选中源默认取 `searchArticle.origins.firstOrNull()` 的 B1 修复）
 * 未被换装破坏。
 *
 * 依据：`docs/specs/compose-advance-continuation/tasks.md` §1.2 子任务 A。
 */
class RssArticleInfoShellParityTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    private val page = "ui/rss/search/RssArticleInfoActivity.kt"

    @Test
    fun usesComposeShellAndSingleSourceAttach() {
        val src = code(page)
        assertTrue("必须经 composeShell 工厂创建合成壳（禁手写匿名壳）", src.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载 Compose 内容", src.contains("attachComposeContent {"))
    }

    @Test
    fun keepsLegadoThemeWrapper() {
        assertTrue(
            "主题包裹 LegadoTheme { } 必须保留（否则脱离主题体系）",
            code(page).contains("LegadoTheme {")
        )
    }

    @Test
    fun noHandWrittenComposeViewAssembly() {
        val src = code(page)
        assertFalse("禁止手写 ComposeView 装配（应走单源）", src.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy（应走单源）", src.contains("ViewCompositionStrategy"))
    }

    @Test
    fun hostLogicPreserved() {
        val src = code(page)
        listOf(
            "override fun onActivityCreated(",
            "private fun loadData(",
            "private fun onSourceClick(",
            "private fun onReadClick(",
            "private fun startRead(",
            "RssSearchSourceHolder",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", src.contains(marker))
        }
        assertTrue(
            "B1 修复不得回流：默认选中源须取 searchArticle.origins.firstOrNull()",
            src.contains("searchArticle?.origins?.firstOrNull()")
        )
    }
}