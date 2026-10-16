package io.legado.app.help.book

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * `ParagraphRuleProcessor` pclick 旧 producer 退役守护（`audit_zero_ref_fun` 无契约档分诊）。
 *
 * 判据（`docs/project-rules/dead-code-cleanup.md` 双硬判据 = 零调用 + 同语义活替代）：
 * `clickKey`（`{"pclick": wrapClick(...)}`）与其私有助手 `wrapClick` 是全仓零引用的**旧 producer**，
 * 活体为同文件的 `wrapRuleClick`（`wrapPclicks` 在活路径使用，格式 `rule:<id>:<js>`）。
 * `parseClick` 的换行分支**保留**（容错解析旧缓存正文里可能残留的旧格式编码）。
 */
class ParagraphRuleProcessorTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val src by lazy { code("src/main/java/io/legado/app/help/book/ParagraphRuleProcessor.kt") }

    @Test
    fun `clickKey 与 wrapClick 已退役`() {
        assertEquals(
            "被取代的 pclick 旧 producer 应退役",
            emptyList<String>(),
            listOf("clickKey", "wrapClick").filter { src.contains("fun $it(") }
        )
    }

    @Test
    fun `活体 wrapRuleClick 与容错解析分支必须保留`() {
        assertEquals("活体 wrapRuleClick 必须保留", true, src.contains("private fun wrapRuleClick("))
        assertEquals("容错解析旧格式的换行分支必须保留", true, src.contains("body.indexOf('\\n')"))
    }
}
