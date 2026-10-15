package io.legado.app.ui.widget.image

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 协程取消**不得被吞**守卫（项目铁律：`CancellationException` 必须原样重抛）。
 *
 * 缺陷背景（2026-10-15 静默失败普查）：`CoverImageView` 的封面位图生成协程里曾有
 * `catch (_: CancellationException) {}` —— 吞掉取消 ⇒ 视图已 detach 后仍可能继续写缓存，
 * 且父协程感知不到取消。已改为 `throw e`（本用例即防回潮）。
 *
 * 为何用源码不变量：该路径依赖 Android `View` / `Bitmap`（含 `delay`+`ensureActive` 轮询），
 * 纯 JVM 无法驱动（G-42 exception 登记见 `empty_test_allowlist.json`）。
 */
class CoverImageViewCancellationTest {

    private val src by lazy {
        listOf(
            File("src/main/java/io/legado/app/ui/widget/image/CoverImageView.kt"),
            File("../app/src/main/java/io/legado/app/ui/widget/image/CoverImageView.kt"),
            File("app/src/main/java/io/legado/app/ui/widget/image/CoverImageView.kt")
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
