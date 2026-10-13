package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 结构性回归防线（阶段 5.1）：EPUB 引擎**默认值必须为 `core`（富管线）**。
 *
 * 依据：①分类误判 + 布局 NPE 两个阻断缺陷已修（`issues-found.md` 第 15 条）；
 * ②12 本多样化/异常 EPUB 的 L3 语料 12/12 PASS；③XB.2 性能劣化 ≤10%。
 * `text` 保留为一键回退，故只断言"默认取 core"，不断言 `text` 分支被删除。
 */
class AppConfigEpubReadEngineDefaultTest {

    private val source by lazy { SourceFileProbe.sourceText("help/config/AppConfig.kt") }

    @Test
    fun epubReadEngine_defaultsToCore() {
        val start = source.indexOf("var epubReadEngine")
        assertTrue("未找到 epubReadEngine（口径漂移）", start >= 0)
        val block = source.substring(start, source.indexOf("var epubCoreScheduleMode", start))
        assertTrue(
            "epubReadEngine 默认值必须为 EPUB_READ_ENGINE_CORE（富管线）",
            block.contains("getPrefString(PreferKey.epubReadEngine, EPUB_READ_ENGINE_CORE)")
        )
        assertTrue(
            "默认值不得回落到 text",
            !block.contains("\"text\"")
        )
    }

    @Test
    fun engineConstValuesAreStable() {
        assertTrue("引擎取值常量 text 必须保留（一键回退）", source.contains("const val EPUB_READ_ENGINE_TEXT = \"text\""))
        assertTrue("引擎取值常量 core 必须保留", source.contains("const val EPUB_READ_ENGINE_CORE = \"core\""))
        assertTrue("useExperimentalEpubCore 判据必须复用常量", source.contains("epubReadEngine == EPUB_READ_ENGINE_CORE"))
    }
}