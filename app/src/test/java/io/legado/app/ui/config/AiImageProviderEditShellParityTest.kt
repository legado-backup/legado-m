package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CA′ 1.2「B→A 写法归一」的**结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：`composeShell` 的 29 个消费页里，本页原为 **B 旧写法**——手工 `removeAllViews()` +
 * `ComposeView(this).apply { setViewCompositionStrategy(...); setContent { ... } }` + `addView`。
 * 该写法与 A 范式 `View.attachComposeContent`（`base/ComposeBindingShells.kt`）**行为重复但不单源**
 * ⇒ 策略/布局参数一改动就要改 N 处。本测试把「只走单源」固化为断言（只写文档的约束一律失效）。
 *
 * 依据：`docs/specs/compose-advance-continuation/tasks.md` §1.2 子任务 A。
 */
class AiImageProviderEditShellParityTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    private val page = "ui/config/AiImageProviderEditActivity.kt"

    @Test
    fun usesComposeShellAndSingleSourceAttach() {
        val src = code(page)
        assertTrue("必须经 composeShell 工厂创建合成壳（禁手写匿名壳）", src.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载 Compose 内容", src.contains("attachComposeContent {"))
    }

    @Test
    fun noHandWrittenComposeViewAssembly() {
        val src = code(page)
        assertFalse("禁止手写 ComposeView 装配（应走单源）", src.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy（应走单源）", src.contains("ViewCompositionStrategy"))
        assertFalse("禁止手写 removeAllViews() 清壳", src.contains("removeAllViews()"))
    }

    @Test
    fun hostLogicPreserved() {
        val src = code(page)
        listOf(
            "override fun onActivityCreated(",
            "private fun bind(",
            "private fun selectType(",
            "private fun openCodeEditor(",
            "private fun save(",
            "private fun currentProvider(",
            "private fun defaultParams(",
            "codeEditLauncher",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", src.contains(marker))
        }
    }
}