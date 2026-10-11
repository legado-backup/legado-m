package io.legado.app.model.reader.render

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书级渲染治理单测（epub-md-rich-rendering 补充任务 S6 配对；AD-25③ / AD-28②）。
 *
 * 覆盖：①开局建立书级后端且**全书一致**；②一次失败即**整书原子降级**（无逐章抖动）；
 * ③同章冷却窗内二次降级被**熔断**；④冷却后同章可再降一级；⑤另一章属新故障可立即降级；
 * ⑥换书重置（降级状态不串书）；⑦未开局不发生降级；⑧`TEXT` 为后端链终态。
 */
class BookRenderGovernorTest {

    private class Fixture(cooldownMs: Long = 15_000L) {
        var now: Long = 1_000L
        val governor = BookRenderGovernor(clock = { now }, degradeCooldownMs = cooldownMs)
        fun advance(ms: Long) {
            now += ms
        }
    }

    @Test
    fun `开局建立书级后端且全书各章取到同一后端`() {
        val f = Fixture()
        val initial = f.governor.startBook(
            bookKey = "book-a",
            initial = BackendSelectionPolicy.Backend.DIRECT_WEB
        )
        assertEquals(BackendSelectionPolicy.Backend.DIRECT_WEB, initial)
        (0..9).forEach { chapter ->
            assertEquals(
                "第 $chapter 章必须与书级后端一致（书级一致性 AD-25③）",
                BackendSelectionPolicy.Backend.DIRECT_WEB,
                f.governor.backendFor("book-a")
            )
        }
    }

    @Test
    fun `一次失败即整书原子降级且无逐章抖动`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)

        val outcome = f.governor.onChapterFailure("book-a", chapterIndex = 3, failure = RenderFailure.ENGINE_UNAVAILABLE)
        assertEquals(true, outcome.degraded)
        assertEquals(BackendSelectionPolicy.Backend.CANVAS, outcome.backend)
        // 原子性：降级后**所有**章节（含已读的前章与未读的后章）都是同一个后端
        (0..9).forEach { chapter ->
            assertEquals(
                "第 $chapter 章不得出现与书级不一致的后端（防逐章样式抖动）",
                BackendSelectionPolicy.Backend.CANVAS,
                f.governor.backendFor("book-a")
            )
        }
    }

    @Test
    fun `同章冷却窗内重复降级被熔断拒绝`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)

        assertTrue(f.governor.onChapterFailure("book-a", 3, RenderFailure.TIMEOUT).degraded)
        // 冷却未到：同一章再次上报视为同一故障余波 ⇒ 拒绝
        val blocked = f.governor.onChapterFailure("book-a", 3, RenderFailure.TIMEOUT)
        assertEquals(false, blocked.degraded)
        assertEquals("熔断期间后端不得变化", BackendSelectionPolicy.Backend.CANVAS, blocked.backend)
    }

    @Test
    fun `冷却结束后同章可再降一级`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)

        assertTrue(f.governor.onChapterFailure("book-a", 3, RenderFailure.EMPTY_RESULT).degraded)
        f.advance(15_000L)
        val again = f.governor.onChapterFailure("book-a", 3, RenderFailure.EMPTY_RESULT)
        assertEquals(true, again.degraded)
        assertEquals(BackendSelectionPolicy.Backend.TEXT, again.backend)
    }

    @Test
    fun `另一章属新故障可在冷却窗内立即降级`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)

        assertTrue(f.governor.onChapterFailure("book-a", 3, RenderFailure.LAYOUT_ERROR).degraded)
        val otherChapter = f.governor.onChapterFailure("book-a", 4, RenderFailure.LAYOUT_ERROR)
        assertEquals("换章不是同一故障的余波，熔断不得误伤", true, otherChapter.degraded)
        assertEquals(BackendSelectionPolicy.Backend.TEXT, otherChapter.backend)
    }

    @Test
    fun `换书重置降级状态不串书`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)
        f.governor.onChapterFailure("book-a", 0, RenderFailure.ENGINE_UNAVAILABLE)
        assertEquals(BackendSelectionPolicy.Backend.CANVAS, f.governor.backendFor("book-a"))

        f.governor.startBook("book-b", BackendSelectionPolicy.Backend.DIRECT_WEB)
        assertEquals("换书后必须回到该书的初始后端", BackendSelectionPolicy.Backend.DIRECT_WEB, f.governor.backendFor("book-b"))
        assertNull("不得把上一本的降级状态串给新书", f.governor.backendFor("book-a"))
    }

    @Test
    fun `未开局时不上报降级且无当前后端`() {
        val f = Fixture()
        assertNull(f.governor.currentBackend)
        assertNull(f.governor.backendFor("book-a"))
        val outcome = f.governor.onChapterFailure("book-a", 0, RenderFailure.TIMEOUT)
        assertEquals(false, outcome.degraded)
    }

    @Test
    fun `TEXT 为后端链终态且冷却门与状态机同源`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.CANVAS)
        val first = f.governor.onChapterFailure("book-a", 1, RenderFailure.TIMEOUT)
        assertEquals(BackendSelectionPolicy.Backend.TEXT, first.backend)
        f.advance(15_000L)
        val again = f.governor.onChapterFailure("book-a", 1, RenderFailure.TIMEOUT)
        assertEquals("TEXT 已是后端链终态，再失败仍为 TEXT（由 RAW 兜底页承担）", BackendSelectionPolicy.Backend.TEXT, again.backend)
        assertEquals(
            RenderBackendStateMachine.DEFAULT_DEGRADE_COOLDOWN_MS,
            BookRenderGovernor.DEFAULT_DEGRADE_COOLDOWN_MS
        )
    }

    @Test
    fun `释放后清空全部状态`() {
        val f = Fixture()
        f.governor.startBook("book-a", BackendSelectionPolicy.Backend.DIRECT_WEB)
        f.governor.onChapterFailure("book-a", 0, RenderFailure.TIMEOUT)
        f.governor.dispose()
        assertNull(f.governor.currentBackend)
        assertNull(f.governor.backendFor("book-a"))
    }
}