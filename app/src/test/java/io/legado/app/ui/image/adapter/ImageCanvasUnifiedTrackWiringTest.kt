package io.legado.app.ui.image.adapter

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W6 7.2（REQ-25 / AD-10）：画布**双轨判定删除**的接线不变量。
 *
 * 为什么值得测（实证根因）：`onImageFileReady` 的 `isLongImage` 分支一旦被恢复
 * （或在别处新增第三条轨），同一页内手势/双击/回弹行为又会随图尺寸分叉 ——
 * 而这**不会**造成编译失败，只能靠断言锁住。
 */
class ImageCanvasUnifiedTrackWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val adapter by lazy {
        read("src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt")
    }

    @Test
    fun onImageFileReadyNoLongerBranchesBySize() {
        assertFalse(
            "不得再按 isLongImage 双轨分流",
            adapter.contains("if (ImagePyramidLoader.isLongImage(imgW, imgH, screenH))")
        )
        assertTrue(
            "长图/普通图须共用同一展示函数",
            adapter.contains("showSsivImage(file, imgW, imgH, screenW, screenH, position)")
        )
    }

    @Test
    fun unifiedShowBindsThroughSingleEntry() {
        assertTrue(
            "统一展示须走 bindImage 单一入口",
            adapter.contains(
                "ImagePyramidLoader.bindImage(binding.ssivView, file, imgW, imgH, screenW, viewH)"
            )
        )
        assertFalse(
            "不得再直调冻结入口（避免绕过统一分流）",
            adapter.contains("ImagePyramidLoader.bindLongImage(")
        )
    }

    @Test
    fun legacyPhotoViewTrackKeptOnlyForRollback() {
        assertTrue(
            "回滚点函数须保留（W7 8.4 删除）",
            adapter.contains("private fun loadIntoPhotoView(")
        )
        assertTrue(
            "须显式标注已无调用点 + 禁新增消费（防被当活路径复用）",
            adapter.contains("W6 7.2 起本函数已无调用点")
        )
        assertFalse(
            "回滚轨不得再有调用点",
            adapter.contains("loadIntoPhotoView(file, url, imgW, imgH, screenW, screenH, position)")
        )
    }
}