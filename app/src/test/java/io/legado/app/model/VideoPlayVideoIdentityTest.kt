package io.legado.app.model

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-06：起播链路视频身份复合判定 + 本地命中诊断日志。
 */
class VideoPlayVideoIdentityTest {

    private val src = SourceFileProbe.sourceText("model/VideoPlay.kt")

    @Test
    fun startPlayUsesCompositeVideoIdentity() {
        assertEquals(true, src.contains("val sourceVideo = (source as? BookSource)?.isVideoSource(book.type) == true"))
        assertEquals(true, src.contains("LocalMediaResolver.localUri(book, chapter, sourceVideo)"))
        assertEquals(true, src.contains("LocalMediaResolver.hasLocal(book, chapter, sourceVideo)"))
    }

    @Test
    fun startPlayLogsCacheDiagnostics() {
        assertEquals(true, src.contains("startPlayBookChapter: idx="))
        assertEquals(true, src.contains("localUri="))
    }
}
