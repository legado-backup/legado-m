package io.legado.app.help.audio

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-08：音频媒体请求解析单源（替代 ViewModel 私有实现）。
 */
class AudioMediaRequestResolverTest {

    private val src = SourceFileProbe.sourceText("help/audio/AudioMediaRequestResolver.kt")

    @Test
    fun isSharedSingleSourceObject() {
        assertEquals(true, src.contains("object AudioMediaRequestResolver"))
        assertEquals(true, src.contains("suspend fun resolve("))
    }

    @Test
    fun prefersExistingResourceUrlBeforeNetwork() {
        // 已存 resourceUrl 必须直用（详情页点缓存时不该再拉一次正文）
        assertEquals(true, src.contains("chapter.resourceUrl"))
        assertEquals(true, src.contains("return ExoPlayerHelper.MediaRequest(it)"))
    }
}
