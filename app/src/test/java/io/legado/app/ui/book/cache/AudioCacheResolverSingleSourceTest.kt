package io.legado.app.ui.book.cache

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-08：缓存管理页与详情页共用音频 resolver 单源（不再自持私有实现）。
 */
class AudioCacheResolverSingleSourceTest {

    private val src = SourceFileProbe.sourceText("ui/book/cache/CacheManageActivityViewModel.kt")

    @Test
    fun usesSharedResolver() {
        assertEquals(true, src.contains("AudioMediaRequestResolver.resolve(context, b, c)"))
        assertEquals(false, src.contains("private suspend fun resolveAudioMediaRequest"))
    }
}
