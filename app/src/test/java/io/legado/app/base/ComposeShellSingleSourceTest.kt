package io.legado.app.base

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `composeShell` 消费页的**单源装配不变量**（CA′ 1.2 收口，JVM 可跑）。
 *
 * 判据（tasks §1.2 验证标准）：「3 页 B→A 归一后**断言不再出现 `composeShell` 之外的手写
 * ComposeView 装配**」——即凡经 `composeShell(this)` 建壳的页面，挂载 Compose 内容**只能**走
 * `View.attachComposeContent` 单源，禁止再手写
 * `ComposeView(…).apply { setViewCompositionStrategy(…); setContent { … } }`。
 *
 * 反模式根源：历史每页复制三行样板，策略（`DisposeOnViewTreeLifecycleDestroyed`）与
 * `layoutParams` 分散在 N 处 ⇒ 单源变更必漏（本次即归一 3 页）。
 */
class ComposeShellSingleSourceTest {

    private fun mainJavaRoot(): File =
        listOf(File("src/main/java"), File("../app/src/main/java"), File("app/src/main/java"))
            .firstOrNull { it.isDirectory }
            ?: throw AssertionError("未找到 main 源根（工作目录=${File(".").absolutePath}）")

    /** 剥掉行注释与 KDoc 星号行，避免注释里的写法制造假阳/假阴。 */
    private fun stripped(f: File): String =
        f.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")

    private fun consumers(): List<File> =
        mainJavaRoot().walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .filter { stripped(it).contains("composeShell(this)") }
            .toList()

    @Test
    fun consumersExist() {
        val n = consumers().size
        assertTrue("composeShell 消费页数量异常（$n）——扫描根或匹配口径可能失效", n >= 25)
    }

    @Test
    fun noConsumerHandWritesComposeView() {
        val bad = consumers().filter { f ->
            val s = stripped(f)
            s.contains("ComposeView(") || s.contains("ViewCompositionStrategy")
        }.map { it.relativeTo(mainJavaRoot()).path }
        assertEquals(
            "以下 composeShell 消费页仍在手写 ComposeView 装配（应统一走 attachComposeContent 单源）：$bad",
            emptyList<String>(),
            bad
        )
    }

    @Test
    fun normalizedThreePagesUseSingleSource() {
        val root = mainJavaRoot()
        listOf(
            "io/legado/app/ui/config/AiImageProviderEditActivity.kt",
            "io/legado/app/ui/main/ai/AiImageGalleryActivity.kt",
            "io/legado/app/ui/rss/search/RssArticleInfoActivity.kt",
        ).forEach { rel ->
            val f = File(root, rel)
            assertTrue("缺少 CA′ 1.2 归一目标页：$rel", f.isFile)
            assertTrue("$rel 必须走 attachComposeContent 单源", stripped(f).contains("attachComposeContent {"))
        }
    }
}