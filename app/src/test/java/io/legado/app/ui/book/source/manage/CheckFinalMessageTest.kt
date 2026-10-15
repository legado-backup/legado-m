package io.legado.app.ui.book.source.manage

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 巡检终态文案判据（`isCheckFinalMessage`）行为护栏。
 *
 * 背景：书源管理页在巡检结束后会把"未收敛为终态"的单源调试消息**补写为「校验失败」**
 * （`buildDebugMessagesSnapshot`）。新增「跳过·存疑」终态后，白名单若漏登记，用户会看到
 * **假的"校验失败"**（缺口3 接线时实测踩到）。
 */
class CheckFinalMessageTest {

    @Test
    fun finalStates_areRecognized() {
        assertTrue(isCheckFinalMessage("校验成功"))
        assertTrue(isCheckFinalMessage("校验失败:目录获取失败"))
        assertTrue(isCheckFinalMessage("跳过:存疑（登录依赖）Failed to connect"))
    }

    @Test
    fun runningStageText_isNotFinal() {
        // 过程态（进行中）不得被判为终态，否则失败收敛会漏掉真正的失败源
        assertFalse(isCheckFinalMessage("正在搜索"))
        assertFalse(isCheckFinalMessage("校验中·搜索"))
        assertFalse(isCheckFinalMessage(""))
    }
}
