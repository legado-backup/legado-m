package io.legado.app.help.gsyVideo

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-05：选集网格「已缓存勾选」接线（对话框传全集下标、adapter 按展示序换算）。
 */
class EpisodeGridCachedBadgeTest {

    private val dialog = SourceFileProbe.sourceText("help/gsyVideo/ChoiceEpisodeDialog.kt")
    private val adapter = SourceFileProbe.sourceText("help/gsyVideo/EpisodeGridAdapter.kt")

    @Test
    fun dialogAcceptsCachedIndexesAndMapsToDisplayOrder() {
        assertEquals(true, dialog.contains("cachedIndexes: Set<Int> = emptySet()"))
        assertEquals(true, dialog.contains("val cachedFlags = indices.map { it in cachedIndexes }"))
    }

    @Test
    fun adapterRendersBadgeFromCachedFlags() {
        assertEquals(true, adapter.contains("cachedFlags: List<Boolean> = emptyList()"))
        assertEquals(true, adapter.contains("episode_cached_badge"))
        assertEquals(true, adapter.contains("R.id.text1"))
    }
}
