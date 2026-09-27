package io.legado.app.service

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-13：音频侧（听书 + HTTP 朗读）**自愈接线**不变量。
 *
 * 背景：两处在改造前分别是「**零自愈**」（听书：直接 STOP + toast）与「硬编码阈值 5」
 * （朗读）。本批统一到 [io.legado.app.help.player.PlaybackErrorPolicy] 三态裁决后，
 * 最容易失守的是：① 某处忘了接线（回到零自愈）；② 旧阈值/旧字段残留（两套判据并存）；
 * ③ 日志缺失（真机排障无据）。此处逐条固化。
 */
class AudioPlaybackSelfHealWiringTest {

    private fun src(pkgPath: String): String {
        val rel = "src/main/java/io/legado/app/$pkgPath"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()
    }

    private val audioService by lazy { src("service/AudioPlayService.kt") }
    private val readAloudService by lazy { src("service/HttpReadAloudService.kt") }

    @Test
    fun audioPlayServiceUsesPolicyAndHandlesAllThreeStates() {
        assertTrue("听书侧须接入策略裁决", audioService.contains("playbackErrorSession.decide(kind)"))
        assertTrue("须有自愈档", audioService.contains("PlaybackErrorAction.SELF_HEAL ->"))
        assertTrue("须有降级档（重新取播放地址）", audioService.contains("AudioPlay.reloadPlayUrl()"))
        assertTrue("须有终止档（保留原有 STOP + 非空提示）", audioService.contains("handleAudioPlayFatal(error)"))
        assertTrue(
            "终止档须保留原错误提示语义（非空）",
            audioService.contains("val errorMsg = \"音频播放出错\\n")
        )
    }

    @Test
    fun audioPlayServiceResetsSessionOnNewPlayback() {
        val resetAt = audioService.indexOf("playbackErrorSession.reset()")
        val playBranchAt = audioService.indexOf("IntentAction.play, IntentAction.playNew ->")
        assertTrue("播放分支须复位自愈记账（切章/切书不继承历史预算）", resetAt > playBranchAt && playBranchAt > 0)
    }

    @Test
    fun readAloudServiceReplacesHardcodedThresholdWithPolicy() {
        assertTrue("朗读侧须接入策略裁决", readAloudService.contains("playbackErrorSession.decide(kind)"))
        assertFalse(
            "旧硬编码阈值字段 playErrorNo 必须随改造删除（否则两套判据并存）",
            Regex("var playErrorNo\\b").containsMatchIn(readAloudService)
        )
        assertFalse(
            "旧阈值读写点必须清零",
            readAloudService.contains("playErrorNo = 0") || readAloudService.contains("playErrorNo++")
        )
        assertTrue("须保留原自愈动作（推进下一段落）", readAloudService.contains("exoPlayer.seekToNextMediaItem()"))
        assertTrue("须保留原终止动作", readAloudService.contains("pauseReadAloud()"))
        assertTrue("ABORT 分支须显式存在", readAloudService.contains("if (action == PlaybackErrorAction.ABORT) {"))
    }

    @Test
    fun readAloudServiceResetsSessionOnAutoAdvance() {
        val autoAt = readAloudService.indexOf("Player.MEDIA_ITEM_TRANSITION_REASON_AUTO")
        val resetAt = readAloudService.indexOf("playbackErrorSession.reset()", autoAt)
        assertTrue("自动推进段落须复位记账（等价原 playErrorNo = 0）", resetAt > autoAt)
    }

    @Test
    fun bothServicesEmitDiagnosableLogs() {
        assertTrue("听书侧缺诊断日志 tag", audioService.contains("AudioPlaybackSelfHeal:"))
        assertTrue("朗读侧缺诊断日志 tag", readAloudService.contains("ReadAloudSelfHeal:"))
        assertTrue(
            "朗读侧日志不得回显段落正文（输出安全）",
            !readAloudService.contains("AppLog.put(\"朗读错误\\n")
        )
    }
}