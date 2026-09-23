package io.legado.app.service

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R22 互斥接线（服务侧）。
 *
 * 协调器语义已由 `ListeningPlaybackCoordinatorTest` 覆盖；这里守**两条真机链路是否都接了**：
 * 漏接任一侧 ⇒ 该方向仍可「朗读与听书同时出声」。
 */
class ListeningMutualExclusionWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun readAloudService_acquiresAndReleases() {
        val service = code("service/BaseReadAloudService.kt")
        assertTrue(
            "朗读起播必须申请播放权",
            service.contains("ListeningPlaybackCoordinator.acquire(ListeningPlaybackCoordinator.Mode.READ_ALOUD)")
        )
        assertTrue("必须终止另一路（听书）", service.contains("AudioPlay.stop()"))
        assertTrue(
            "销毁必须释放（否则下次起播被误判为已在播）",
            service.contains("ListeningPlaybackCoordinator.release(ListeningPlaybackCoordinator.Mode.READ_ALOUD)")
        )
    }

    @Test
    fun audioPlayService_acquiresAndReleases() {
        val service = code("service/AudioPlayService.kt")
        assertTrue(
            "听书起播必须申请播放权",
            service.contains("ListeningPlaybackCoordinator.acquire(ListeningPlaybackCoordinator.Mode.AUDIO_PLAY)")
        )
        assertTrue(
            "必须经既有朗读停止通道终止朗读（下发式，非阻塞）",
            service.contains("ReadAloud.stop(this)")
        )
        assertTrue(
            "销毁必须释放",
            service.contains("ListeningPlaybackCoordinator.release(ListeningPlaybackCoordinator.Mode.AUDIO_PLAY)")
        )
    }
}