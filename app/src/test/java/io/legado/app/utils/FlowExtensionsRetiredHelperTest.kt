package io.legado.app.utils

import io.legado.app.testkit.SourceFileProbe
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：`FlowExtensions` 零调用残余退役守护 + 活替代者行为固化。
 *
 * 退役项：`Flow<T>.mapNotNullParallel`（全仓除声明外零引用）。
 * 同语义活替代者：`mapParallel(...).filterNotNull()`（即被删函数的唯一实现体；`mapParallel` 全仓 4 处在用）。
 * 本类**双侧**：既锁「退役项不得回潮」，也用 `runTest` 证明活替代者在真实协程中仍按序产出（防误删替代者）。
 */
class FlowExtensionsRetiredHelperTest {

    @Test
    fun `零调用包装已退役且活替代者仍在`() {
        val src = SourceFileProbe.sourceText("utils/FlowExtensions.kt")
        assertEquals("退役项不得回潮", false, src.contains("mapNotNullParallel"))
        assertEquals("活替代者 mapParallel 必须保留", true, src.contains("fun <T, R> Flow<T>.mapParallel("))
        assertEquals("并发安全版 mapParallelSafe 必须保留", true, src.contains("fun <T, R> Flow<T>.mapParallelSafe("))
        assertEquals("并发执行版 onEachParallel 必须保留", true, src.contains("fun <T> Flow<T>.onEachParallel("))
    }

    @Test
    fun `mapParallel 单并发下按上游顺序产出`() = runTest {
        // 行为断言（非文本探针）：并发上限=1 时 flatMapMerge 退化为顺序执行 ⇒ 结果必须与输入同序，
        // 且「非空过滤」这一退役项原语义可由 mapParallel + 下游操作符等价表达。
        val mapped = flowOf(1, 2, 3, 4).mapParallel(1) { it * 2 }.toList()
        assertEquals(listOf(2, 4, 6, 8), mapped)
    }
}
