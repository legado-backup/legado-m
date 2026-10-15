package io.legado.app.model

import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-21 回归护栏：目录取样（`sampleProbeChapters`）是巡检服务与质量体检的**唯一权威口径**。
 *
 * 缺陷原貌（先红证据：`repro_volumeOnlyToc_breaksContentProbe` 实测 `java.util.NoSuchElementException`）：
 * `CheckSourceService.checkBook` 取样后直接 `first()` 取试读章，当目录条目**全是卷标题占位**
 * （`isVolume && url.startsWith(title)`）时取样为空 ⇒ 抛 `NoSuchElementException` ⇒ 被上游 `when`
 * 归为「网站失效」（可用源被标成死站、还被写进源注释），而质检底座 `SourceQualityChecker` 对同一序列
 * 已有空守卫 ⇒ 同一判定两处实现漂移。
 */
class SourceProbeSamplingTest {

    private fun volumePlaceholder(index: Int) = BookChapter(
        url = "第${index + 1}卷",
        title = "第${index + 1}卷",
        isVolume = true,
        bookUrl = "book",
        index = index,
    )

    private fun chapter(index: Int) = BookChapter(
        url = "/chapter/$index.html",
        title = "第${index + 1}章",
        isVolume = false,
        bookUrl = "book",
        index = index,
    )

    @Test
    fun sampleProbeChapters_volumeOnlyPlaceholders_yieldsEmpty() {
        val sample = sampleProbeChapters(listOf(volumePlaceholder(0), volumePlaceholder(1)))
        assertEquals(0, sample.size)
        // 新口径的正向指标：调用方按空守卫取值（无异常），而非 first()
        assertNull(sample.getOrNull(0))
    }

    @Test
    fun sampleProbeChapters_filtersPlaceholdersAndTakesTwo() {
        val sample = sampleProbeChapters(
            listOf(volumePlaceholder(0), chapter(0), chapter(1), chapter(2))
        )
        assertEquals(2, sample.size)
        assertEquals(listOf("第1章", "第2章"), sample.map { it.title })
    }

    @Test
    fun sampleProbeChapters_keepsRealEntryMarkedAsVolume() {
        // 卷标记但 url 是真实链接（不以标题开头）⇒ 属可试读条目，必须保留
        val realVolume = BookChapter(
            url = "/volume/1.html", title = "第1卷", isVolume = true, bookUrl = "book", index = 0
        )
        val sample = sampleProbeChapters(listOf(realVolume))
        assertEquals(1, sample.size)
        assertEquals("/volume/1.html", sample.first().url)
    }

    @Test
    fun sampleProbeChapters_singleUsableChapter_returnsOne() {
        val sample = sampleProbeChapters(listOf(chapter(0)))
        assertEquals(1, sample.size)
        assertEquals("第1章", sample.first().title)
    }

    @Test
    fun sampleProbeChapters_emptyInput_yieldsEmpty() {
        assertEquals(0, sampleProbeChapters(emptyList()).size)
    }

    @Test
    fun legacyPattern_firstOnPossiblyEmptySample_isHazardous() {
        val sample = sampleProbeChapters(listOf(volumePlaceholder(0)))
        // 旧写法（`sample.first()`）在空取样上必抛 —— 即 NEW-21 的复现现象（先红用例所证）
        var thrown: Throwable? = null
        try {
            sample.first()
        } catch (t: Throwable) {
            thrown = t
        }
        assertTrue(thrown is NoSuchElementException)
    }
}
