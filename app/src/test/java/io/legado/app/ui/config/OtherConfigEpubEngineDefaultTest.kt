package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阶段 5.1：设置页「EPUB 阅读引擎」条目的**默认值必须与 AppConfig 的默认值同源**。
 *
 * 缺陷型：设置项 `defaultValue` 与 `AppConfig` 取默认值分别硬编码字面量时，两处极易口径漂移
 * （旧代码一处 `"text"`、一处 `"core"` 就会让"设置页显示的当前值"与"引擎实际取值"不一致）。
 * 本用例锁死：条目默认值必须引用 `AppConfig.EPUB_READ_ENGINE_CORE` 常量，且不得再出现字面量。
 */
class OtherConfigEpubEngineDefaultTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val fragment by lazy { read("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt") }

    @Test
    fun engineEntryDefaultsToCoreConstant() {
        val at = fragment.indexOf("key = PreferKey.epubReadEngine")
        assertTrue("未找到 EPUB 引擎设置条目（口径漂移）", at > 0)
        val block = fragment.substring(at, at + 400)
        assertTrue(
            "条目默认值必须引用 AppConfig.EPUB_READ_ENGINE_CORE",
            block.contains("defaultValue = AppConfig.EPUB_READ_ENGINE_CORE")
        )
        assertFalse(
            "不得再硬编码字面量默认值（与 AppConfig 两处漂移）",
            block.contains("defaultValue = \"text\"")
        )
    }

    @Test
    fun engineSummaryUsesConstantsForCurrentValue() {
        val at = fragment.indexOf("private fun epubReadEngineSummary")
        assertTrue("未找到 epubReadEngineSummary", at > 0)
        val block = fragment.substring(at, at + 400)
        assertTrue("当前值判定须复用常量", block.contains("AppConfig.EPUB_READ_ENGINE_TEXT"))
    }
}