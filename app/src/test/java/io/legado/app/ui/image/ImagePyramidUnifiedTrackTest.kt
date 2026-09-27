package io.legado.app.ui.image

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W6 7.1 / 7.2（REQ-26 / REQ-25 / AD-10）：SSIV 呈现轨收敛的**接线不变量**。
 *
 * 为什么值得测（实证根因）：
 * - 7.1 要求「既有 5 方法签名冻结 + 长图轨零行为变化」——`bindLongImage` 若被改写而非委托，
 *   长图定位（capped 时 minScale + 顶部对齐）会静默改变；
 * - 7.2 要求「取消双轨判定」——若 `isLongImage` 分支被恢复（或新增第三轨），
 *   同一页内手势行为又会随图尺寸分叉。
 */
class ImagePyramidUnifiedTrackTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val loader by lazy { read("src/main/java/io/legado/app/ui/image/ImagePyramidLoader.kt") }

    @Test
    fun unifiedEntryExistsAndCompatEntryDelegates() {
        assertTrue("须有统一绑定入口", loader.contains("fun bindImage("))
        assertTrue("须有普通图绑定入口", loader.contains("fun bindNormalImage("))
        assertTrue(
            "冻结入口须纯委托（避免与统一实现分叉）",
            loader.contains(") = bindImage(ssiv, file, imgW, imgH, viewW, viewH)")
        )
    }

    @Test
    fun frozenSignaturesRemainIntact() {
        listOf(
            "fun isLongImage(imgW: Int, imgH: Int, screenH: Int): Boolean",
            "fun decodeBounds(file: File): IntArray?",
            "fun normalDisplayHeight(imgW: Int, imgH: Int, screenW: Int, screenH: Int): Int",
            "fun ssivDisplayHeight(imgW: Int, imgH: Int, screenW: Int, screenH: Int): Int",
            "fun bindLongImage(",
        ).forEach { sig ->
            assertTrue("冻结签名不得改动：$sig", loader.contains(sig))
        }
        // 上限常量是 W5/W6 共同口径，禁改
        assertTrue(loader.contains("const val NORMAL_MAX_HEIGHT_SCREEN_MULTIPLIER = 4"))
        assertTrue(loader.contains("const val SSIV_MAX_HEIGHT_SCREEN_MULTIPLIER = 20"))
    }
}