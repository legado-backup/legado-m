package io.legado.app.model.reader.render

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 重测分页防抖单测（epub-md-rich-rendering 补充任务 S11 配对；AD-28⑤ 的 P-05）。
 *
 * 覆盖：①首个请求排定一次触发；②窗口内后续请求**只顺延不再排定**（合并）；
 * ③窗口已静默 ⇒ 到点执行一次；④窗口内又来了新请求 ⇒ 到点**不执行**、需继续等（不是"丢请求"）；
 * ⑤执行后复位可再次排定；⑥`reset` 清挂起（换章/释放不留悬空）。
 */
class RepaginationDebouncePolicyTest {

    private val window = 200L

    @Test
    fun `首个请求排定且窗口内后续请求合并为一次`() {
        val p = RepaginationDebouncePolicy(window)
        assertTrue("首个请求必须排定", p.onRequest(1_000L))
        assertTrue("已有挂起", p.isPending)
        assertFalse("窗口内第二次请求只顺延、不得重复排定", p.onRequest(1_050L))
        assertFalse("第三次同理", p.onRequest(1_100L))
        assertTrue("仍只有一个挂起", p.isPending)
    }

    @Test
    fun `静默到点执行一次并复位`() {
        val p = RepaginationDebouncePolicy(window)
        p.onRequest(1_000L)
        assertTrue("窗口内（<截止）不得执行", !p.onTimer(1_100L))
        assertTrue("静默到点必须执行", p.onTimer(1_200L))
        assertFalse("执行后不再挂起", p.isPending)
        assertFalse("已执行则再点定时器不得重复执行", p.onTimer(1_400L))
    }

    @Test
    fun `窗口内新请求会顺延而不是丢弃`() {
        val p = RepaginationDebouncePolicy(window)
        p.onRequest(1_000L)
        p.onRequest(1_150L)                       // 顺延到 1_350
        assertFalse("原截止(1_200)已过但被顺延 ⇒ 不得执行", p.onTimer(1_200L))
        assertFalse("仍未静默", p.onTimer(1_300L))
        assertTrue("顺延后的截止已到 ⇒ 必须执行（请求未被丢弃）", p.onTimer(1_350L))
    }

    @Test
    fun `执行后可再次排定`() {
        val p = RepaginationDebouncePolicy(window)
        p.onRequest(0L)
        assertTrue(p.onTimer(200L))
        assertTrue("下一波请求必须能重新排定（否则第二次重测永远不再发生）", p.onRequest(500L))
        assertTrue(p.onTimer(700L))
    }

    @Test
    fun `reset 清挂起且不误触发`() {
        val p = RepaginationDebouncePolicy(window)
        p.onRequest(1_000L)
        p.reset()
        assertFalse("reset 后不得再挂起", p.isPending)
        assertFalse("reset 后定时器到点不得执行", p.onTimer(9_999L))
    }
}
