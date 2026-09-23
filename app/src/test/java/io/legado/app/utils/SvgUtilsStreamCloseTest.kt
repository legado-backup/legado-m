package io.legado.app.utils

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B1 · R3「SvgUtils 文件流关闭」回归测试（源码不变量）。
 *
 * 缺陷（修复前）：`createBitmap(filePath)` 与 `getSize(filePath)` 直接 `FileInputStream(filePath)`
 * 后交给下游，**从不关闭** ⇒ fd 泄漏（高频加载 svg 时耗尽 fd）。
 * 修复：两处均改为 `FileInputStream(filePath).use { ... }`。
 *
 * 为什么用源码不变量：`SvgUtils` 依赖 Android 的 SVG/Bitmap 渲染，本项目单测无 Robolectric
 * （`returnDefaults = true`）⇒ 无法做真实渲染断言；按结构不变量固化（与 B7 同口径）。
 */
class SvgUtilsStreamCloseTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/utils/SvgUtils.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun fileInputStreamIsAlwaysClosedViaUse() {
        val t = code()
        val opened = Regex("FileInputStream\\(filePath\\)").findAll(t).count()
        val closed = Regex("FileInputStream\\(filePath\\)\\.use").findAll(t).count()
        assertTrue("应有两处按路径打开的文件流（createBitmap / getSize），实际 $opened", opened >= 2)
        assertTrue("两处都必须走 use{} 关闭，实际 $closed", closed >= 2)
        assertFalse(
            "不得再出现「先赋值后不关闭」的旧写法",
            t.contains("val inputStream = FileInputStream(filePath)")
        )
    }
}