package io.legado.app.help.gsyVideo

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-13：`Exo2MediaPlayer.onPlayerError` **终端点接入策略**的接线不变量。
 *
 * 为什么用源码不变量而非行为测试：`onPlayerError` 依赖 ExoPlayer 运行时与真实错误码，
 * 纯 JVM 无法驱动；而本批最容易失守的是**接线约定**——
 * ① 策略只在「既有链已放弃」的终端点调用（不得插到既有重试分支之前 ⇒ 否则双重重试）；
 * ② 既有重试/降级/重建链**逐行不变**（回归红线）；
 * ③ 会话记账必须在「新起播 / 起播成功」两处复位。
 */
class Exo2MediaPlayerSelfHealWiringTest {

    private val player by lazy {
        listOf(
            File("src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt"),
            File("../app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt"),
            File("app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun policyIsConsultedAtEveryTerminalErrorPoint() {
        val calls = Regex("if \\(handleTerminalErrorByPolicy\\(error\\)\\) return").findAll(player).count()
        assertTrue("终端点接入数应 ≥4（SSL / 末端解析 / 阈值耗尽 / 通用终端），实测 $calls", calls >= 4)
    }

    @Test
    fun policyCallIsPlacedAfterExistingRetryBranches() {
        val policyAt = player.indexOf("handleTerminalErrorByPolicy(error)")
        val backoffAt = player.indexOf("T2.4: 指数退避重试策略")
        val retryAt = player.indexOf("if (isNetworkError && retryCount < MAX_RETRY)")
        assertTrue("策略接线点必须在既有退避重试分支之后", policyAt > backoffAt && policyAt > retryAt)
    }

    @Test
    fun existingResilienceChainIsUntouched() {
        // 回归红线：既有重试 / 降级 / 重建 / 不可恢复判定必须原样保留
        assertTrue("既有 HTTP 状态重试链丢失", player.contains("ERROR_CODE_IO_BAD_HTTP_STATUS && retryCount < MAX_RETRY"))
        assertTrue("既有指数退避表丢失", player.contains("(1L shl (retryCount - 1)) * 1000L"))
        assertTrue("既有 7001 重建链丢失", player.contains("rebuild7001Count"))
        assertTrue("既有不可恢复错误判定丢失", player.contains("isUnrecoverableError"))
        assertTrue("既有 416 清缓存重试丢失", player.contains("ExoPlayerHelper.clearCache()"))
        assertEquals("既有重试上限应保持 5", true, player.contains("private const val MAX_RETRY = 5"))
    }

    @Test
    fun sessionIsResetOnNewPlaybackAndOnSuccessfulStart() {
        val resetCount = Regex("VideoPlay\\.routeSelfHealSession\\.reset\\(\\)").findAll(player).count()
        assertTrue("会话记账须在「新起播」与「起播成功」两处复位，实测 $resetCount", resetCount >= 2)
        val prepareAt = player.indexOf("override fun prepareAsyncInternal()")
        val firstReset = player.indexOf("VideoPlay.routeSelfHealSession.reset()")
        assertTrue("prepareAsyncInternal 之后需有复位（新会话）", firstReset > prepareAt)
    }

    @Test
    fun degradeVerdictReusesExistingFallbackInsteadOfNewRetryLoop() {
        assertTrue(
            "DEGRADE 必须复用既有 tryNextFallback（合并非叠加）",
            player.contains("policy DEGRADE → tryNextFallback")
        )
        assertTrue(
            "策略须写入错误大类供 UI 换线判据",
            player.contains("VideoPlay.lastPlaybackErrorKind = kind")
        )
    }
}