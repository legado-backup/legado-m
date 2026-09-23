package io.legado.app.ui.widget.compose

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R12「自定义模板编辑器」弹窗不变量。
 *
 * 需求（spec R12-1）：编辑器必须是**可视化插入占位符**（点选变量插入到光标处）+ **实时预览**，
 * 而不是让用户手写模板串；插入语义复用纯函数 `ReadTipTemplate.insertPlaceholder`（可单测、可回归）。
 */
class AppComposeDialogsTipTemplateTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun dialogSupportsVisualPlaceholderInsertAndPreview() {
        val src = code("ui/widget/compose/AppComposeDialogs.kt")
        assertTrue("必须存在模板编辑器弹窗", src.contains("class ComposeTipTemplateDialog"))
        assertTrue(
            "占位符必须由变量白名单生成可点选 chip（可视化插入）",
            src.contains("ReadTipTemplate.variables.forEach")
        )
        assertTrue(
            "点选必须插入到光标处（复用纯函数，非手工拼串）",
            src.contains("ReadTipTemplate.insertPlaceholder(")
        )
        assertTrue(
            "必须携带光标状态（TextFieldValue），否则无法定位插入点",
            src.contains("TextFieldValue.Saver")
        )
        assertTrue(
            "必须有实时预览（与阅读页同引擎渲染）",
            src.contains("ReadTipTemplate.render(text, ReadTipTemplate.previewValues())")
        )
    }

    /** 编辑器已接线为 Fragment 扩展（宿主机以最小改动调用）。 */
    @Test
    fun fragmentAdapterExposed() {
        val adapters = code("ui/widget/compose/ComposeDialogAdapters.kt")
        assertTrue(adapters.contains("fun Fragment.showComposeTipTemplateDialog("))
        assertTrue(adapters.contains("ComposeTipTemplateDialog.create("))
    }
}