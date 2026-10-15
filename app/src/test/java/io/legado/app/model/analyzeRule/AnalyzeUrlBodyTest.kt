package io.legado.app.model.analyzeRule

import io.legado.app.exception.NoStackTraceException
import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Test

/**
 * core-flow-test-coverage —— `parseBodyMapOrThrow` 行为契约（替代原 `getOrNull()!!`）。
 *
 * 原实现（`AnalyzeUrl.upload` 内联）在 body 为空/非合法 JSON 对象时抛 **NPE**；
 * 用户书源规则驱动该路径 ⇒ 源不可用即崩溃。现改为业务异常，可被 `catch(Exception)` 捕获。
 */
class AnalyzeUrlBodyTest {

    private inline fun expectBusinessException(block: () -> Unit) {
        try {
            block()
            fail("期望抛出 NoStackTraceException（畸形 body 不得静默通过或抛 Error/NPE）")
        } catch (e: NoStackTraceException) {
            // 期望路径
        } catch (e: Throwable) {
            fail("抛出 ${e.javaClass.name}（应为 NoStackTraceException）")
        }
    }

    @Test
    fun blankBody_throwsBusinessException() {
        expectBusinessException { parseBodyMapOrThrow("   ") }
    }

    @Test
    fun nullBody_throwsBusinessException() {
        expectBusinessException { parseBodyMapOrThrow(null) }
    }

    @Test
    fun nonObjectJsonBody_throwsBusinessException() {
        // JSON 数组无法反序列化为 Map ⇒ 必须显式失败而非 NPE
        expectBusinessException { parseBodyMapOrThrow("[1,2,3]") }
    }

    @Test
    fun malformedJsonBody_throwsBusinessException() {
        expectBusinessException { parseBodyMapOrThrow("not-a-json") }
    }

    @Test
    fun validObjectBody_returnsMutableMap() {
        val map = parseBodyMapOrThrow("""{"a":1,"b":"x"}""")
        assertEquals(setOf("a", "b"), map.keys)
        assertEquals("x", map["b"])
        // 契约：返回可变 Map（调用方需就地上传字段）
        map["c"] = "y"
        assertEquals("y", map["c"])
    }
}
