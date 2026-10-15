package io.legado.app.help.ai

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B16：朗读分角色「旧引号启发式 + 分块管线」退役守护。
 *
 * 缺陷背景（本条测试存在的理由）：`AiReadAloudRoleService` 长期并存两条实现——
 * 旧的手写引号/冒号启发式（[buildDefaultSegmentsForText] 及其助手）+ 分块请求管线
 * （[requestChunkedSegments]/[requestSegments]/[buildPrompt]/[parseSegments]…），
 * 与新管线（`ReadAloudRolePreprocessor` + `requestUnitAssignmentBatches`/`buildBatchUnitPrompt`/
 * `confirmUnitsDefinition`）职责完全重合。经 `audit_dead_private_fun.py` 判定均为
 * `private` 作用域内零调用（不可达），本批整体退役。
 *
 * 本类把「退役结果」固化：任一旧符号回潮即红；同时包含一条**可行为化**断言，
 * 证明退役未波及并存的解析入口。
 */
class AiReadAloudPipelineRetirementTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `旧启发式与分块管线符号已整体退役`() {
        val ras = code("src/main/java/io/legado/app/help/ai/AiReadAloudRoleService.kt")
        val retired = listOf(
            "buildDefaultSegmentsForText", "requestChunkedSegments", "requestSegments",
            "buildPrompt", "parseSegments", "parseSegmentsArray", "parseFallbackResult",
            "recordSegmentsDefinition", "narratorSegment", "parseSpeakerColonSegment",
            "parseQuotedSpeechRanges", "normalizeSegmentBoundaries", "buildUnitPrompt"
        )
        // 行为断言：退役后不应存在任何上述函数的声明残留
        assertEquals("退役函数声明残留应为空", emptyList<String>(),
            retired.filter { ras.contains("fun $it(") })
        assertEquals("TOOL_RECORD_SEGMENTS 应随其唯一消费者一并退役", false,
            ras.contains("TOOL_RECORD_SEGMENTS"))

        val chat = code("src/main/java/io/legado/app/help/ai/AiChatService.kt")
        assertEquals("parseAssistantTurn 应已退役", false, chat.contains("fun parseAssistantTurn("))
    }

    @Test
    fun `并存工具名清洗入口不受退役影响`() {
        assertEquals(listOf("book_search", "book_info"), AiToolNameLimits.sanitize(
            listOf("", "  ", "  book_search  ", "book_info", "\t")
        ).toList())
    }
}
