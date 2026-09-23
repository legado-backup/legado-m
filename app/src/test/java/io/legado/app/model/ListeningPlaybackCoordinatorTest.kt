package io.legado.app.model

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * B4 · R22「朗读 / 听书互斥」单测。
 *
 * 验收口径（tasks §4.6）：**两向互斥顺序**（朗读→听书、听书→朗读都要先终止对方）；
 * 且「终止回调」期间状态不得被抢回（占位在先）；A 停止不得误清 B 的占用。
 */
class ListeningPlaybackCoordinatorTest {

    private val readAloud = ListeningPlaybackCoordinator.Mode.READ_ALOUD
    private val audioPlay = ListeningPlaybackCoordinator.Mode.AUDIO_PLAY

    @Before
    fun setUp() {
        ListeningPlaybackCoordinator.resetForTest()
    }

    /** 方向一：听书中起朗读 ⇒ 必须先终止听书。 */
    @Test
    fun readAloudAcquire_stopsAudioPlayFirst() {
        val stopped = mutableListOf<ListeningPlaybackCoordinator.Mode>()
        ListeningPlaybackCoordinator.acquire(audioPlay) { stopped += it }
        val previous = ListeningPlaybackCoordinator.acquire(readAloud) { stopped += it }
        assertEquals("必须终止听书", listOf(audioPlay), stopped)
        assertEquals(audioPlay, previous)
        assertEquals(readAloud, ListeningPlaybackCoordinator.active())
        assertEquals(
            "动作顺序：先占位目标模式，再终止旧模式",
            listOf("active:AUDIO_PLAY", "active:READ_ALOUD", "stop:AUDIO_PLAY"),
            ListeningPlaybackCoordinator.recentActions()
        )
    }

    /** 方向二：朗读中起听书 ⇒ 必须先终止朗读。 */
    @Test
    fun audioPlayAcquire_stopsReadAloudFirst() {
        val stopped = mutableListOf<ListeningPlaybackCoordinator.Mode>()
        ListeningPlaybackCoordinator.acquire(readAloud) { stopped += it }
        ListeningPlaybackCoordinator.acquire(audioPlay) { stopped += it }
        assertEquals("必须终止朗读", listOf(readAloud), stopped)
        assertEquals(audioPlay, ListeningPlaybackCoordinator.active())
    }

    /** 占位在先：终止回调执行期间，状态已是**新目标模式**（防回调内 release/再 acquire 抢回）。 */
    @Test
    fun duringStopCallback_activeIsAlreadyTheNewMode() {
        ListeningPlaybackCoordinator.acquire(readAloud) {}
        var activeDuringStop: ListeningPlaybackCoordinator.Mode? = null
        ListeningPlaybackCoordinator.acquire(audioPlay) {
            activeDuringStop = ListeningPlaybackCoordinator.active()
            // 模拟真实停止链路里的 release（模式不匹配，必须被忽略）
            ListeningPlaybackCoordinator.release(readAloud)
        }
        assertEquals("回调期间必须已占位为新目标模式", audioPlay, activeDuringStop)
        assertEquals("旧模式的 release 不得清掉新占用", audioPlay, ListeningPlaybackCoordinator.active())
    }

    /** 同模式重复获取是幂等 no-op（不得重复终止/重复记录）。 */
    @Test
    fun sameModeAcquire_isIdempotent() {
        val stopped = mutableListOf<ListeningPlaybackCoordinator.Mode>()
        ListeningPlaybackCoordinator.acquire(readAloud) { stopped += it }
        assertNull(
            "同模式再获取不得返回被终止的模式",
            ListeningPlaybackCoordinator.acquire(readAloud) { stopped += it }
        )
        assertEquals(0, stopped.size)
        assertEquals(readAloud, ListeningPlaybackCoordinator.active())
        assertEquals(listOf("active:READ_ALOUD"), ListeningPlaybackCoordinator.recentActions())
    }

    /** 释放语义：模式匹配才清；不匹配忽略（A 停止不得误清 B）。 */
    @Test
    fun release_onlyClearsMatchingMode() {
        ListeningPlaybackCoordinator.acquire(audioPlay) {}
        ListeningPlaybackCoordinator.release(readAloud)
        assertEquals("不匹配的 release 必须被忽略", audioPlay, ListeningPlaybackCoordinator.active())
        ListeningPlaybackCoordinator.release(audioPlay)
        assertNull(ListeningPlaybackCoordinator.active())
    }

    /** 释放后可重新获取（服务销毁 → 再次起播不因残留状态被判定为"已在播"）。 */
    @Test
    fun releaseThenAcquire_worksAgain() {
        ListeningPlaybackCoordinator.acquire(readAloud) {}
        ListeningPlaybackCoordinator.release(readAloud)
        var stopped = 0
        assertNull(ListeningPlaybackCoordinator.acquire(audioPlay) { stopped++ })
        assertEquals("无占用时不应触发终止", 0, stopped)
        assertEquals(audioPlay, ListeningPlaybackCoordinator.active())
    }

    /** 双入口接线：两条起播链路都必须经协调器（漏一条 ⇒ 该方向仍可叠加播放）。 */
    @Test
    fun bothStartPointsGoThroughCoordinator() {
        val readAloudService = code("service/BaseReadAloudService.kt")
        val audioPlayService = code("service/AudioPlayService.kt")
        assertTrue(
            "朗读起播必须申请播放权",
            readAloudService.contains("Mode.READ_ALOUD)") && readAloudService.contains("AudioPlay.stop()")
        )
        assertTrue(
            "听书起播必须申请播放权",
            audioPlayService.contains("Mode.AUDIO_PLAY)") && audioPlayService.contains("ReadAloud.stop(this)")
        )
        assertTrue(
            "两侧服务销毁都必须释放播放权",
            readAloudService.contains("release(ListeningPlaybackCoordinator.Mode.READ_ALOUD)") &&
                audioPlayService.contains("release(ListeningPlaybackCoordinator.Mode.AUDIO_PLAY)")
        )
    }

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }
}