package io.legado.app.model

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-13：播放侧**自愈状态与入口**不变量（`VideoPlay` 共享态 / `AudioPlay` 降级入口）。
 *
 * 为什么值得测：`VideoPlay` 是全局单例（多 Activity 共享），会话记账字段一旦被挪到
 * Activity 局部，就会出现「播放器侧记的账、UI 侧读不到」的静默失联；`AudioPlay.reloadPlayUrl()`
 * 若不清空 `durPlayUrl`，则「降级」会退化成「同地址原地重播」（等于没有换链）。
 */
class VideoPlaySelfHealStateTest {

    private fun src(relPath: String): String {
        val rel = "src/main/java/io/legado/app/$relPath"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()
    }

    private val videoPlay by lazy { src("model/VideoPlay.kt") }
    private val audioPlay by lazy { src("model/AudioPlay.kt") }

    @Test
    fun videoPlayExposesSessionScopedSelfHealState() {
        assertTrue(
            "换线记账须为 VideoPlay 单例字段（播放器侧与 UI 侧共用同一实例）",
            videoPlay.contains("val routeSelfHealSession = PlaybackErrorSession()")
        )
        assertTrue(
            "最近错误大类须可跨线程读取（播放器回调线程写、UI 线程读）",
            videoPlay.contains("@Volatile") && videoPlay.contains("var lastPlaybackErrorKind: PlaybackErrorKind?")
        )
    }

    @Test
    fun audioPlayReloadClearsUrlBeforeRefetching() {
        val fnAt = audioPlay.indexOf("fun reloadPlayUrl()")
        assertTrue("降级入口必须存在", fnAt > 0)
        val clearAt = audioPlay.indexOf("durPlayUrl = \"\"", fnAt)
        val loadAt = audioPlay.indexOf("loadOrUpPlayUrl()", fnAt)
        assertTrue("必须先清空播放地址（否则等价原地重播）", clearAt > fnAt)
        assertTrue("清空后须复用既有加载链", loadAt > clearAt)
    }

    @Test
    fun audioPlayKeepsLegacyEntryIntact() {
        assertTrue("既有 loadOrUpPlayUrl 语义不得被改写", audioPlay.contains("fun loadOrUpPlayUrl() {"))
    }
}