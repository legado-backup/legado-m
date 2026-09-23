package io.legado.app.ui.book.read.page

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B1·R5 翻页动画速度不变量：`ReadView.defaultAnimationSpeed` 必须来自配置档位的**单源映射**，
 * 不得再写死毫秒字面量（原为 `val defaultAnimationSpeed = 300`）。
 *
 * 为什么用源码不变量：`ReadView` 是 FrameLayout 子类（需 Android 渲染环境），本仓单测无 Robolectric；
 * 档位→毫秒的纯逻辑由 `PageTurnAnimSpeedTest` 覆盖，此处只锁「接线」。
 */
class ReadViewAnimSpeedTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/page/ReadView.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun animationSpeedComesFromTierSingleSource() {
        val t = code()
        assertTrue("应经 PageTurnAnimSpeed 映射", t.contains("PageTurnAnimSpeed.msOf("))
        assertTrue("应读 AppConfig.pageTurnAnimSpeedTier", t.contains("AppConfig.pageTurnAnimSpeedTier"))
        assertFalse("不得再硬编码 300ms", t.contains("val defaultAnimationSpeed = 300"))
    }
}