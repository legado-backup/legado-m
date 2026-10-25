package io.legado.app.constant

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 切集加载反馈事件键契约（episode-switch-loading-and-legacy-inline C1）。
 *
 * EventBus 以字符串为键，键值撞车会让「加载反馈」与其它事件互相串扰
 * （例如与 VIDEO_SUB_TITLE 同键 ⇒ 标题变更被当成显隐指令）。本测试锁定取值与唯一性。
 */
class EventBusVideoSwitchLoadingTest {

    @Test
    fun switchLoadingKeyValueIsStable() {
        assertEquals("VideoSwitchLoading", EventBus.VIDEO_SWITCH_LOADING)
    }

    @Test
    fun switchLoadingKeyDoesNotCollideWithNeighbors() {
        assertEquals(false, EventBus.VIDEO_SWITCH_LOADING == EventBus.VIDEO_SUB_TITLE)
        assertEquals(false, EventBus.VIDEO_SWITCH_LOADING == EventBus.VIDEO_PLAY_ERROR)
        assertEquals(false, EventBus.VIDEO_SWITCH_LOADING == EventBus.UP_VIDEO_INFO)
    }
}
