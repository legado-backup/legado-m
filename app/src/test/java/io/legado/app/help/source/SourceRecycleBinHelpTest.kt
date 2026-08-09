package io.legado.app.help.source

import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.DictRule
import io.legado.app.data.entities.HttpTTS
import io.legado.app.data.entities.ReplaceRule
import io.legado.app.data.entities.RssSource
import io.legado.app.data.entities.TxtTocRule
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SourceRecycleBinHelpTest {

    @Test
    fun typeConstants_coverAllSevenTypes() {
        assertEquals(7, listOf(
            SourceRecycleBinHelp.TYPE_BOOK_SOURCE,
            SourceRecycleBinHelp.TYPE_RSS_SOURCE,
            SourceRecycleBinHelp.TYPE_REPLACE_RULE,
            SourceRecycleBinHelp.TYPE_TXT_TOC_RULE,
            SourceRecycleBinHelp.TYPE_HTTP_TTS,
            SourceRecycleBinHelp.TYPE_DICT_RULE,
            SourceRecycleBinHelp.TYPE_HIGHLIGHT_RULE
        ).distinct().size)
    }

    @Test
    fun bookSource_payloadRoundTrip() {
        val source = BookSource(
            bookSourceUrl = "https://example.com",
            bookSourceName = "测试书源",
            bookSourceGroup = "测试分组",
            bookSourceType = 0
        )
        val payload = GSON.toJson(source)
        val restored = GSON.fromJsonObject<BookSource>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(source.bookSourceUrl, restored!!.bookSourceUrl)
        assertEquals(source.bookSourceName, restored.bookSourceName)
        assertEquals(source.bookSourceGroup, restored.bookSourceGroup)
        assertEquals(source.bookSourceType, restored.bookSourceType)
    }

    @Test
    fun rssSource_payloadRoundTrip() {
        val source = RssSource(
            sourceUrl = "https://example.com/feed.xml",
            sourceName = "测试订阅源",
            sourceGroup = "分组"
        )
        val payload = GSON.toJson(source)
        val restored = GSON.fromJsonObject<RssSource>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(source.sourceUrl, restored!!.sourceUrl)
        assertEquals(source.sourceName, restored.sourceName)
        assertEquals(source.sourceGroup, restored.sourceGroup)
    }

    @Test
    fun replaceRule_payloadRoundTrip() {
        val rule = ReplaceRule(name = "测试替换", pattern = "\\d+", replacement = "x")
        val payload = GSON.toJson(rule)
        val restored = GSON.fromJsonObject<ReplaceRule>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(rule.id, restored!!.id)
        assertEquals(rule.name, restored.name)
        assertEquals(rule.pattern, restored.pattern)
        assertEquals(rule.replacement, restored.replacement)
    }

    @Test
    fun txtTocRule_payloadRoundTrip() {
        val rule = TxtTocRule(id = 100L, name = "测试目录规则", rule = "https://example.com/toc", enable = false)
        val payload = GSON.toJson(rule)
        val restored = GSON.fromJsonObject<TxtTocRule>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(rule.id, restored!!.id)
        assertEquals(rule.name, restored.name)
        assertEquals(rule.rule, restored.rule)
        assertEquals(rule.enable, restored.enable)
    }

    @Test
    fun httpTts_payloadRoundTrip() {
        val rule = HttpTTS(
            name = "测试TTS",
            loginUrl = "",
            url = "https://example.com/tts?text=\$content",
            header = ""
        )
        val payload = GSON.toJson(rule)
        val restored = GSON.fromJsonObject<HttpTTS>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(rule.id, restored!!.id)
        assertEquals(rule.name, restored.name)
        assertEquals(rule.url, restored.url)
    }

    @Test
    fun dictRule_payloadRoundTrip() {
        val rule = DictRule(name = "测试字典", urlRule = "@js:result", showRule = "")
        val payload = GSON.toJson(rule)
        val restored = GSON.fromJsonObject<DictRule>(payload).getOrNull()
        assertTrue(restored != null)
        assertEquals(rule.name, restored!!.name)
        assertEquals(rule.urlRule, restored.urlRule)
        assertEquals(rule.showRule, restored.showRule)
    }

    @Test
    fun malformedPayload_failsGracefully() {
        val result = GSON.fromJsonObject<BookSource>("not a json")
        assertTrue(result.isFailure)
    }
}
