package io.legado.app.ui.video

import io.legado.app.ui.video.VideoPlayerActivity.Companion.shouldRetryInit
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 2026-10-24 真机铁证回归：`onPause` 取消 `initSourceJob` 后不补跑 ⇒ 播放器永不挂载的白屏。
 *
 * 触发序列（logcat 实测）：`initSource begin` → 3ms 后 `onPause: initSourceJob cancelled`
 * → `onResume`（无任何后续 initSource）⇒ 界面只剩顶栏白屏，用户感知「播放不了」。
 * 修复：`onResume` 在会话未就绪且协程不在跑时补跑初始化（上限 3 次）。
 */
class VideoPlayerActivityInitRetryTest {

    @Test
    fun cancelledInitIsRetriedOnResume() {
        assertTrue(
            "onPause 取消协程且会话未就绪时，onResume 必须补跑初始化",
            shouldRetryInit(isNew = true, sessionReady = false, initJobActive = false, retryCount = 0)
        )
    }

    @Test
    fun readySessionIsNotReinitialized() {
        assertFalse(
            "会话已完成（播放器已挂载）不得重复初始化，避免重播/状态重置",
            shouldRetryInit(isNew = true, sessionReady = true, initJobActive = false, retryCount = 0)
        )
    }

    @Test
    fun runningInitJobIsNotDuplicated() {
        assertFalse(
            "协程仍在跑（瞬态 pause）时不重复启动，防双份 initSource",
            shouldRetryInit(isNew = true, sessionReady = false, initJobActive = true, retryCount = 0)
        )
    }

    @Test
    fun floatingWindowResumeSessionIsNotReinitialized() {
        assertFalse(
            "isNew=false 为悬浮窗恢复会话，必须继续原会话，不得重新初始化",
            shouldRetryInit(isNew = false, sessionReady = false, initJobActive = false, retryCount = 0)
        )
    }

    @Test
    fun retryStopsAtCapToAvoidPauseResumeLoop() {
        assertTrue(
            "补跑次数 2（<3）仍可继续",
            shouldRetryInit(isNew = true, sessionReady = false, initJobActive = false, retryCount = 2)
        )
        assertFalse(
            "达到上限 3 后必须停止，避免 pause/resume 抖动导致无限重试",
            shouldRetryInit(isNew = true, sessionReady = false, initJobActive = false, retryCount = 3)
        )
        assertFalse(
            "超过上限同样不得重试",
            shouldRetryInit(isNew = true, sessionReady = false, initJobActive = false, retryCount = 4)
        )
    }
}
