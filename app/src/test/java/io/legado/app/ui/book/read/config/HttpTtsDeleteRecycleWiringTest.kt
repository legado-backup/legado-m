package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-64：HTTP TTS 语音配置**删除前必须回收**（回收站生产端接线守护）。
 *
 * 缺陷背景：`SourceRecycleBinHelp` 的 7 个回收入口中，**唯 `recycleHttpTtsRules` 全仓零调用**
 * （book/rss/replace/txtToc/dict/highlight 均有活调用方），而回收站 UI 已备 `TYPE_HTTP_TTS`
 * 分支与文案（`RecycleBinScreen`）⇒ 生产/消费两端不对称：**删除 HTTP TTS 后不进回收站、不可恢复**。
 * 本类锁两处删除路径（应用内 `SpeakEngineDialog` + 三端复用 `TtsKernel`）的接线与顺序。
 */
class HttpTtsDeleteRecycleWiringTest {

    @Test
    fun `应用内删除必须先回收再落库删除`() {
        val src = SourceFileProbe.sourceText("ui/book/read/config/SpeakEngineDialog.kt")
        assertTrue("删除路径必须调用回收入口", src.contains("SourceRecycleBinHelp.recycleHttpTtsRules(listOf(httpTTS))"))
        val recycleAt = src.indexOf("recycleHttpTtsRules")
        val deleteAt = src.indexOf("appDb.httpTTSDao.delete(httpTTS)")
        assertTrue("回收必须早于 DAO 删除（先回收再删，否则取不到实体）", recycleAt in 1 until deleteAt)
        assertEquals("回收异常不得阻断删除（须 runCatching 包裹）", true, src.contains("kotlin.runCatching { SourceRecycleBinHelp.recycleHttpTtsRules("))
    }

    @Test
    fun `回收入口七类齐备（勿只补 HTTP TTS）`() {
        val helper = SourceFileProbe.sourceText("help/source/SourceRecycleBinHelp.kt")
        listOf(
            "recycleBookSources", "recycleRssSources", "recycleReplaceRules", "recycleTxtTocRules",
            "recycleHttpTtsRules", "recycleDictRules", "recycleHighlightRules"
        ).forEach { name ->
            assertEquals("回收入口 $name 必须保留", true, helper.contains("fun $name("))
        }
    }
}
