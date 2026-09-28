package io.legado.app.help.ai

import io.legado.app.data.entities.SceneBookmark
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 / REQ-32（AD-12）：名场面 AI 描述的**输出契约 + 降级链**。
 *
 * 为什么要锁：
 * ① 输出契约（`{"desc":≤30字,"tags":[3个]}`）是库页展示与备份回读的共同前提，改口径即破展示；
 * ② 降级链是「核心链路零 AI 依赖」的兜底 —— 一旦解析失败时抛异常，打标整条路径会被 AI 拖死；
 * ③ `isAvailable()` 的开关消费点若与 `PreferKey` 失联，会出现「设置无效」的静默失联（编译期无提示）。
 */
class AiSceneDescServiceTest {

    private fun bookmark(
        bookName: String = "",
        bookAuthor: String = "",
        chapterName: String = "",
        text: String = "",
        desc: String = ""
    ) = SceneBookmark(
        bookName = bookName,
        bookAuthor = bookAuthor,
        chapterName = chapterName,
        text = text,
        desc = desc
    )

    @Test
    fun parsesJsonContractWithMarkdownFence() {
        val raw = """
            ```json
            {"desc": "他转身走进雨里", "tags": ["离别", "雨夜", "转折"]}
            ```
        """.trimIndent()
        val result = AiSceneDescService.parse(raw, "兜底")
        assertEquals("应取 JSON 中的 desc", "他转身走进雨里", result.desc)
        assertEquals("应取 3 个标签", listOf("离别", "雨夜", "转折"), result.tags)
    }

    @Test
    fun parsesJsonWithSurroundingProse() {
        val raw = "好的，这是结果：{\"desc\":\"灯灭前的最后一瞥\",\"tags\":[\"悬念\"]} 以上。"
        val result = AiSceneDescService.parse(raw, "兜底")
        assertEquals("灯灭前的最后一瞥", result.desc)
        assertEquals(listOf("悬念"), result.tags)
    }

    @Test
    fun fallsBackToPlainTextWhenNotJson() {
        val raw = "模型这次没有按 JSON 输出，只是一句普通说明"
        val result = AiSceneDescService.parse(raw, "兜底")
        assertEquals("非 JSON 时截断原文", raw, result.desc)
        assertTrue("非 JSON 时标签置空", result.tags.isEmpty())
    }

    @Test
    fun fallsBackToProvidedTextWhenBlank() {
        val result = AiSceneDescService.parse("", "原文片段兜底")
        assertEquals("空白返回必须落回兜底文本", "原文片段兜底", result.desc)
        assertTrue(result.tags.isEmpty())
    }

    @Test
    fun descIsCollapsedAndTruncatedToLimit() {
        val long = "第一行\n第二行" + "很长的描述".repeat(10)
        val result = AiSceneDescService.sanitizeDesc(long)
        assertTrue("必须折叠换行", !result.contains("\n"))
        assertEquals("必须截断至 30 字", AiSceneDescService.MAX_DESC_LEN, result.length)
    }

    @Test
    fun tagsAreCleanedDedupedAndCapped() {
        val raw = """
            {"desc": "描述", "tags": ["转折", "转折", "雨夜", "  ", "离别", "多余"]}
        """.trimIndent()
        val result = AiSceneDescService.parse(raw, "兜底")
        assertEquals("去重 + 去空 + 限 3 个", listOf("转折", "雨夜", "离别"), result.tags)
    }

    @Test
    fun fallbackDescFollowsFieldPriority() {
        assertEquals(
            "手写备注优先",
            "我写的备注",
            AiSceneDescService.fallbackDesc(
                bookmark(bookName = "书", chapterName = "章", text = "原文", desc = "我写的备注")
            )
        )
        assertEquals(
            "其次取原文片段",
            "原文片段",
            AiSceneDescService.fallbackDesc(
                bookmark(bookName = "书", chapterName = "章", text = "原文片段")
            )
        )
        assertEquals(
            "再次取章节名",
            "第一章",
            AiSceneDescService.fallbackDesc(bookmark(bookName = "书", chapterName = "第一章"))
        )
        assertEquals(
            "最后取书名",
            "某书",
            AiSceneDescService.fallbackDesc(bookmark(bookName = "某书"))
        )
    }

    @Test
    fun promptCarriesContractAndReadingContext() {
        val prompt = AiSceneDescService.buildPrompt(
            bookmark(bookName = "测试书名", chapterName = "第三章", text = "他推开门")
        )
        assertTrue("提示词须含输出契约", prompt.contains("{\"desc\": \"描述\", \"tags\""))
        assertTrue("提示词须含书名", prompt.contains("测试书名"))
        assertTrue("提示词须含章节名", prompt.contains("第三章"))
        assertTrue("提示词须含原文片段", prompt.contains("他推开门"))
    }

    @Test
    fun availabilityGateConsumesThePrefSwitch() {
        val src = SourceFileProbe.sourceText("help/ai/AiSceneDescService.kt")
        assertTrue(
            "可用性判定必须消费 aiSceneDescEnabled 开关（否则设置无效）",
            src.contains("AppConfig.aiSceneDescEnabled")
        )
        assertTrue(
            "场景模型未配置时必须判为不可用（降级而非调用）",
            src.contains("AppConfig.aiSummaryModelConfig ?: return false")
        )
    }
}
