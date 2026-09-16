package io.legado.app.service

import io.legado.app.service.SpeechFollowState.NextChapterDecision
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * R4 朗读跟随状态机单测（含 5 格互斥矩阵的可测部分）。
 *
 * 矩阵（见 [SpeechFollowState] 注释）：
 * 1. 跟随中 + 滚动 + 章节完成 → 既有 pause 分支胜出（在 ReadBook 侧，单测不覆盖）
 * 2. 跟随中 + 非滚动 + 完成 → nextChapterDecision 决策
 * 3. 脱离 + 完成 → 仅朗读推进（同步写入点被拦截）
 * 4. 脱离 + 未完成 → 朗读自推（写入点被拦截）
 * 5. 服务已停 → 写入一律拦截
 */
class SpeechFollowStateTest {

    @Before
    fun setUp() {
        // 单例状态在用例间共享，先复位到「跟随」态
        SpeechFollowState.reset()
    }

    @Test
    fun newSession_restoresFollow() {
        SpeechFollowState.detachForManualNavigation()
        assertFalse(SpeechFollowState.followReadAloudPosition)
        SpeechFollowState.restoreForNewSpeechSession()
        assertTrue(SpeechFollowState.followReadAloudPosition)
    }

    @Test
    fun manualNavigation_detachesFollow() {
        SpeechFollowState.detachForManualNavigation()
        assertFalse(SpeechFollowState.followReadAloudPosition)
    }

    @Test
    fun reset_returnsToFollow() {
        SpeechFollowState.detachForManualNavigation()
        SpeechFollowState.reset()
        assertTrue(SpeechFollowState.followReadAloudPosition)
    }

    /** 矩阵第 5 格：服务已停 → 写入一律拦截 */
    @Test
    fun serviceStopped_neverWritesVisibleReader() {
        assertFalse(SpeechFollowState.shouldApplySpeechProgressToVisibleReader(isSpeechPlaying = false))
        SpeechFollowState.detachForManualNavigation()
        assertFalse(SpeechFollowState.shouldApplySpeechProgressToVisibleReader(isSpeechPlaying = false))
    }

    /** 跟随中 + 播放中 → 允许写可视页 */
    @Test
    fun followingAndPlaying_appliesProgress() {
        assertTrue(SpeechFollowState.shouldApplySpeechProgressToVisibleReader(isSpeechPlaying = true))
    }

    /** 矩阵第 3/4 格：脱离后不拉回可视页（即使朗读仍在播放） */
    @Test
    fun detachedWhilePlaying_doesNotApplyProgress() {
        SpeechFollowState.detachForManualNavigation()
        assertFalse(SpeechFollowState.shouldApplySpeechProgressToVisibleReader(isSpeechPlaying = true))
    }

    @Test
    fun noNextChapter_stops() {
        assertEquals(
            NextChapterDecision.STOP,
            SpeechFollowState.nextChapterDecision(hasNextSpeechChapter = false, visibleSyncMoved = true)
        )
        assertEquals(
            NextChapterDecision.STOP,
            SpeechFollowState.nextChapterDecision(hasNextSpeechChapter = false, visibleSyncMoved = false)
        )
    }

    /** 矩阵第 2 格：跟随中 + 可视页已同步 → 继续并保持同步 */
    @Test
    fun followingWithVisibleSync_continuesWithSync() {
        assertEquals(
            NextChapterDecision.CONTINUE_WITH_VISIBLE_SYNC,
            SpeechFollowState.nextChapterDecision(hasNextSpeechChapter = true, visibleSyncMoved = true)
        )
    }

    @Test
    fun followingWithoutVisibleSync_continuesSpeechOnly() {
        assertEquals(
            NextChapterDecision.CONTINUE_SPEECH_ONLY,
            SpeechFollowState.nextChapterDecision(hasNextSpeechChapter = true, visibleSyncMoved = false)
        )
    }

    /** 矩阵第 3 格：脱离态章节读完 → 仅朗读推进，不拉回可视页 */
    @Test
    fun detachedAtChapterEnd_continuesSpeechOnly() {
        SpeechFollowState.detachForManualNavigation()
        assertEquals(
            NextChapterDecision.CONTINUE_SPEECH_ONLY,
            SpeechFollowState.nextChapterDecision(hasNextSpeechChapter = true, visibleSyncMoved = true)
        )
    }
}