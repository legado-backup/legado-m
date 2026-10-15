package io.legado.app.help.book

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 协程取消**不得被吞**守卫（项目铁律：`CancellationException` 必须原样重抛）。
 *
 * 缺陷背景（2026-10-15 静默失败普查）：`ContentProcessor` 替换净化循环里曾有
 * `catch (_: CancellationException) {}` —— 该写法把取消信号**吞掉** ⇒ 父协程感知不到取消、
 * 内容处理被误判为"已完成"，且循环结束前仍可能继续 `runBlocking(IO)` 写库。
 * 已改为 `throw e`（本用例即防回潮）。
 *
 * 为何用源码不变量而非运行时断言：`ContentProcessor` 依赖 `appCtx` / `appDb`（Room），
 * 纯 JVM 无法驱动其替换净化路径（G-42 exception 登记见 `empty_test_allowlist.json`）。
 */
class ContentProcessorCancellationTest {

    private val src by lazy {
        listOf(
            File("src/main/java/io/legado/app/help/book/ContentProcessor.kt"),
            File("../app/src/main/java/io/legado/app/help/book/ContentProcessor.kt"),
            File("app/src/main/java/io/legado/app/help/book/ContentProcessor.kt")
        ).first { it.isFile }.readText().replace("\r\n", "\n")
    }

    @Test
    fun cancellationIsRethrownNotSwallowed() {
        assertFalse(
            "不得存在吞掉取消信号的空 catch 体（catch (_: CancellationException) {}）",
            src.contains("catch (_: CancellationException) {")
        )
        assertTrue(
            "取消分支须捕获为具名变量并显式重抛",
            src.contains("catch (e: CancellationException) {") && src.contains("throw e")
        )
    }
}
