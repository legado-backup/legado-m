package io.legado.app.help.player

import androidx.media3.common.PlaybackException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-13（AD-04）：播放错误**三态裁决表 + 会话记账**不变量。
 *
 * 覆盖三类易失守的约定：
 * 1. 错误码 → 大类的分组（网络/HTTP/资源/解析/解码/直播窗口），新增错误码漏挂会退化为 UNKNOWN；
 * 2. 大类 → 动作的三态表（**不可自愈类绝不换线**：解码/DRM/未知一律 ABORT）；
 * 3. 会话记账：上限 3 次 + 冷却 60s（预置决策 design §9.2#16），冷却结束后预算复位。
 *
 * 纯 JVM：`PlaybackException.ERROR_CODE_*` 为编译期常量（内联），不引入 Android 运行时依赖。
 */
class PlaybackErrorPolicyTest {

    // ------------------------------------------------------------ 分类

    @Test
    fun classifiesNetworkHttpResourceAndParseGroups() {
        assertEquals(
            PlaybackErrorKind.NETWORK,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED)
        )
        assertEquals(
            PlaybackErrorKind.NETWORK,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT)
        )
        assertEquals(
            PlaybackErrorKind.HTTP_STATUS,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS)
        )
        assertEquals(
            PlaybackErrorKind.RESOURCE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_IO_FILE_NOT_FOUND)
        )
        assertEquals(
            PlaybackErrorKind.RESOURCE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_IO_INVALID_HTTP_CONTENT_TYPE)
        )
        assertEquals(
            PlaybackErrorKind.PARSE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_PARSING_CONTAINER_MALFORMED)
        )
        assertEquals(
            PlaybackErrorKind.PARSE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_PARSING_MANIFEST_MALFORMED)
        )
    }

    @Test
    fun classifiesDecodeAndLiveWindowGroups() {
        assertEquals(
            PlaybackErrorKind.DECODE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_DECODER_INIT_FAILED)
        )
        assertEquals(
            PlaybackErrorKind.DECODE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_DECODING_FAILED)
        )
        assertEquals(
            PlaybackErrorKind.DECODE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_AUDIO_TRACK_INIT_FAILED)
        )
        assertEquals(
            PlaybackErrorKind.DECODE,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_DRM_LICENSE_ACQUISITION_FAILED)
        )
        assertEquals(
            PlaybackErrorKind.LIVE_WINDOW,
            PlaybackErrorPolicy.classify(PlaybackException.ERROR_CODE_BEHIND_LIVE_WINDOW)
        )
    }

    @Test
    fun unknownErrorCodeFallsBackToUnknownKind() {
        assertEquals(PlaybackErrorKind.UNKNOWN, PlaybackErrorPolicy.classify(Int.MAX_VALUE))
    }

    // ------------------------------------------------------------ 三态表

    @Test
    fun nonSelfHealableKindsNeverSwitchSource() {
        assertEquals(
            PlaybackErrorAction.ABORT,
            PlaybackErrorPolicy.actionOf(PlaybackErrorKind.DECODE)
        )
        assertEquals(
            PlaybackErrorAction.ABORT,
            PlaybackErrorPolicy.actionOf(PlaybackErrorKind.UNKNOWN)
        )
    }

    @Test
    fun networkAndLiveWindowSelfHealOthersDegrade() {
        assertEquals(PlaybackErrorAction.SELF_HEAL, PlaybackErrorPolicy.actionOf(PlaybackErrorKind.NETWORK))
        assertEquals(PlaybackErrorAction.SELF_HEAL, PlaybackErrorPolicy.actionOf(PlaybackErrorKind.LIVE_WINDOW))
        assertEquals(PlaybackErrorAction.DEGRADE, PlaybackErrorPolicy.actionOf(PlaybackErrorKind.HTTP_STATUS))
        assertEquals(PlaybackErrorAction.DEGRADE, PlaybackErrorPolicy.actionOf(PlaybackErrorKind.RESOURCE))
        assertEquals(PlaybackErrorAction.DEGRADE, PlaybackErrorPolicy.actionOf(PlaybackErrorKind.PARSE))
    }

    @Test
    fun presetThresholdsMatchDesignDecision() {
        assertEquals(3, PlaybackErrorPolicy.MAX_ATTEMPTS)
        assertEquals(60_000L, PlaybackErrorPolicy.COOLDOWN_MS)
    }

    // ------------------------------------------------------------ 会话记账

    @Test
    fun attemptsCapAtThreeThenCooldownBlocksFurtherSelfHeal() {
        var now = 1_000L
        val session = PlaybackErrorSession(clock = { now })
        val code = PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED
        repeat(PlaybackErrorPolicy.MAX_ATTEMPTS) {
            assertEquals(PlaybackErrorAction.SELF_HEAL, session.decide(code))
        }
        assertEquals(3, session.attempts)
        // 第 4 次：预算耗尽 ⇒ ABORT + 进入冷却（不循环）
        assertEquals(PlaybackErrorAction.ABORT, session.decide(code))
        assertTrue("预算耗尽须进入冷却", session.isCoolingDown())
        // 冷却期内即便收到可自愈错误也 ABORT
        now += PlaybackErrorPolicy.COOLDOWN_MS / 2
        assertEquals(PlaybackErrorAction.ABORT, session.decide(code))
    }

    @Test
    fun budgetResetsAfterCooldownExpires() {
        var now = 1_000L
        val session = PlaybackErrorSession(clock = { now })
        val code = PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED
        repeat(PlaybackErrorPolicy.MAX_ATTEMPTS + 1) { session.decide(code) }
        assertTrue(session.isCoolingDown())
        now += PlaybackErrorPolicy.COOLDOWN_MS + 1
        assertFalse("冷却到期即解除", session.isCoolingDown())
        assertEquals("冷却结束后预算须复位（否则自愈永久失效）", PlaybackErrorAction.SELF_HEAL, session.decide(code))
        assertEquals(1, session.attempts)
    }

    @Test
    fun decodeKindAbortsWithoutConsumingBudget() {
        val session = PlaybackErrorSession()
        assertEquals(
            PlaybackErrorAction.ABORT,
            session.decide(PlaybackException.ERROR_CODE_DECODER_INIT_FAILED)
        )
        assertEquals("不可自愈类不消耗预算", 0, session.attempts)
        assertFalse("不可自愈类不进入冷却（不阻塞后续网络自愈）", session.isCoolingDown())
    }

    @Test
    fun resetClearsAttemptsAndCooldown() {
        var now = 1_000L
        val session = PlaybackErrorSession(clock = { now })
        val code = PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED
        repeat(PlaybackErrorPolicy.MAX_ATTEMPTS + 1) { session.decide(code) }
        assertTrue(session.isCoolingDown())
        session.reset()
        assertFalse(session.isCoolingDown())
        assertEquals(0, session.attempts)
        assertEquals(PlaybackErrorAction.SELF_HEAL, session.decide(code))
    }

    // ------------------------------------------------------------ 换线裁决

    @Test
    fun routeSelfHealRotatesAndWrapsAround() {
        val session = PlaybackErrorSession()
        val kind = PlaybackErrorKind.NETWORK
        assertEquals(
            1,
            PlaybackErrorPolicy.decideRouteSelfHeal(kind, 3, 0, session).targetIndex
        )
        assertEquals(
            0,
            PlaybackErrorPolicy.decideRouteSelfHeal(kind, 3, 2, session).targetIndex
        )
        assertTrue(PlaybackErrorPolicy.decideRouteSelfHeal(kind, 3, 0, session).allowed)
    }

    @Test
    fun routeSelfHealRefusesForSingleRouteOrUnknownKind() {
        val session = PlaybackErrorSession()
        val single = PlaybackErrorPolicy.decideRouteSelfHeal(PlaybackErrorKind.NETWORK, 1, 0, session)
        assertFalse("单线路源无换线语义", single.allowed)
        assertEquals(0, session.attempts)

        val noKind = PlaybackErrorPolicy.decideRouteSelfHeal(null, 3, 0, session)
        assertFalse("无错误分类时保守终止", noKind.allowed)
        assertEquals(0, session.attempts)
    }

    @Test
    fun routeSelfHealRefusesForNonSelfHealableKindAndExhaustedBudget() {
        val session = PlaybackErrorSession()
        val decode = PlaybackErrorPolicy.decideRouteSelfHeal(PlaybackErrorKind.DECODE, 3, 0, session)
        assertFalse("不可自愈类不换线", decode.allowed)
        assertEquals(PlaybackErrorAction.ABORT, decode.action)

        repeat(PlaybackErrorPolicy.MAX_ATTEMPTS) {
            PlaybackErrorPolicy.decideRouteSelfHeal(PlaybackErrorKind.HTTP_STATUS, 3, 0, session)
        }
        val exhausted = PlaybackErrorPolicy.decideRouteSelfHeal(PlaybackErrorKind.HTTP_STATUS, 3, 0, session)
        assertFalse("预算耗尽后必须停手（不循环遍历线路）", exhausted.allowed)
        assertTrue(exhausted.coolingDown)
    }

    @Test
    fun routeSelfHealDecisionExposesLogFields() {
        val decision = PlaybackErrorPolicy.decideRouteSelfHeal(
            PlaybackErrorKind.HTTP_STATUS, 2, 0, PlaybackErrorSession()
        )
        assertNotNull(decision.action)
        assertEquals(PlaybackErrorAction.DEGRADE, decision.action)
        assertEquals(1, decision.targetIndex)
        assertEquals(1, decision.attempts)
    }
}