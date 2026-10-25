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

    /**
     * episode-switch-loading-and-legacy-inline C1：两条切集入口都必须立刻亮加载反馈，
     * 且**先置 true 再做采集**（顺序反了等于遮罩迟到，用户仍先看到黑屏）。
     */
    @Test
    fun switchLoadingRaisedBeforeCollectionOnBothEntries() {
        val bookEntry = src.substringAfter("private fun startPlayBookChapter")
        val rssEntry = src.substringAfter("fun playRssEpisode")
        val marker = "postEvent(EventBus.VIDEO_SWITCH_LOADING, true)"
        assertEquals(true, bookEntry.contains(marker))
        assertEquals(true, rssEntry.contains(marker))
        // 书源链：加载反馈必须先于「原始 URL 捕获 / 本地缓存判定」等采集前动作
        assertEquals(
            true,
            bookEntry.indexOf(marker) < bookEntry.indexOf("val localUri = LocalMediaResolver.localUri")
        )
    }

    /**
     * 2026-10-25 真机修复：书源线路映射下自动连播只推进 chapterInVolumeIndex，
     * 选集面板/计数会停在旧集 ⇒ upDurIndex 必须同步镜像的 rssEpisodeIndex。
     */
    @Test
    fun autoAdvanceSyncsMappedRssEpisodeIndex() {
        val upDurIndex = src.substringAfter("fun upDurIndex")
        assertEquals(true, upDurIndex.contains("rssEpisodeIndex = index.coerceIn(0, (mapped.size - 1)"))
        // 同步必须在 startPlay 之前（先对齐状态再起播，否则 UI 刷新读到旧值）
        assertEquals(
            true,
            upDurIndex.indexOf("rssEpisodeIndex = index") < upDurIndex.indexOf("startPlay(player)")
        )
    }
}
