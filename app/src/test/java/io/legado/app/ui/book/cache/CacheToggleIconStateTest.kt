package io.legado.app.ui.book.cache

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 离线缓存页「开始 / 停止」开关的状态语义守护（fix-compose-theme-scope-and-cache-icon tasks 1.1）。
 *
 * 缺陷背景：图标状态派生原先写在 `IconButton` 的 content lambda 内，Kotlin 2.x 强跳过会记忆化该
 * lambda ⇒ 缓存任务开始后图标不重算（真机实证「点三角后不变方块」）。修复把派生上提到行级 body，
 * 并用本纯函数锁定语义。
 *
 * 说明：该缺陷本质是**组合期重组行为**，JVM 单测无法复现「IconButton 被跳过」；此处锁定的是
 * 状态派生语义与「图标语义 = 点击语义」不变量，防后续重构改错判定方向。
 */
class CacheToggleIconStateTest {

    @Test
    fun noTaskEntry_isNotRunning() {
        assertFalse(isCacheRunning(null))
    }

    @Test
    fun stoppedTask_isNotRunning() {
        assertFalse(isCacheRunning(isStop = true))
    }

    @Test
    fun activeTask_isRunning() {
        assertTrue(isCacheRunning(isStop = false))
    }

    @Test
    fun toggleAction_matchesIconSemantics() {
        // 图标显示「停止（方块）」⟺ 点击动作为 Stop
        for (isStop in listOf(null, true, false)) {
            assertEquals(
                "isStop=$isStop 时图标语义与点击动作必须一致",
                isCacheRunning(isStop),
                cacheToggleAction(isStop) == CacheToggleAction.Stop,
            )
        }
    }

    @Test
    fun toggleAction_noTaskEntry_startsDownload() {
        assertEquals(CacheToggleAction.Start, cacheToggleAction(null))
    }

    @Test
    fun toggleAction_running_stopsDownload() {
        assertEquals(CacheToggleAction.Stop, cacheToggleAction(isStop = false))
    }
}