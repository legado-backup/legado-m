package io.legado.app.help.gsyVideo

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-05：选集网格「已缓存勾选」接线（对话框传全集下标、adapter 按展示序换算）。
 *
 * 2026-10-25：渲染逻辑下沉到 [EpisodePanelBinder]（弹框与内嵌面板同一实现），
 * 故「传参 + 展示序换算」断言改读 binder；弹框仍需保留 receipt 参数并转交 binder。
 */
class EpisodeGridCachedBadgeTest {

    private val dialog = SourceFileProbe.sourceText("help/gsyVideo/ChoiceEpisodeDialog.kt")
    private val binder = SourceFileProbe.sourceText("help/gsyVideo/EpisodePanelBinder.kt")
    private val adapter = SourceFileProbe.sourceText("help/gsyVideo/EpisodeGridAdapter.kt")

    @Test
    fun dialogAcceptsCachedIndexesAndMapsToDisplayOrder() {
        // 弹框保留入参并原样转交 binder
        assertEquals(true, dialog.contains("cachedIndexes: Set<Int> = emptySet()"))
        assertEquals(true, dialog.contains("cachedIndexes = cachedIndexes"))
        // 展示序换算在 binder（倒序时角标必须跟随真实集号）
        assertEquals(true, binder.contains("val cachedFlags = indices.map { it in cachedIndexes }"))
    }

    @Test
    fun adapterRendersBadgeFromCachedFlags() {
        assertEquals(true, adapter.contains("cachedFlags: List<Boolean> = emptyList()"))
        assertEquals(true, adapter.contains("episode_cached_badge"))
        assertEquals(true, adapter.contains("R.id.text1"))
    }
}
