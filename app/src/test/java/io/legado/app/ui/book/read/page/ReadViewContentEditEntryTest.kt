package io.legado.app.ui.book.read.page

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R14（B3）阅读页「编辑内容」点按区接线不变量。
 *
 * 需求（spec R14-2）：从原入口（无选区 offset）打开编辑器时必须**沿用既有进度定位**、不回归；
 * 且必须与其余三个入口一样经**统一入口**构造（`ContentEditDialog.create(...)`），
 * 否则新增的选区锚点语义会被此处绕过（裸构造 ⇒ 永远走回退分支，看似正常但破坏了统一契约）。
 */
class ReadViewContentEditEntryTest {

    private fun sourceCode(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/page/ReadView.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun clickAction8_usesUnifiedFactoryWithNullAnchor() {
        val code = sourceCode()
        assertTrue(
            "点按区 action 8（编辑内容）必须走统一入口并显式传 null（走缺省进度回退）",
            code.contains("ContentEditDialog.create(null)")
        )
        assertEquals(
            "不得残留裸构造的入口（会绕过统一锚点契约）",
            0,
            Regex("showDialogFragment\\(ContentEditDialog\\(\\)\\)").findAll(code).count()
        )
    }
}