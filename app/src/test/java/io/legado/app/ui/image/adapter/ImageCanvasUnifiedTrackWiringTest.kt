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
        assertTrue(
            "KDoc 须写明删除闸门归属 W7 8.4（防再次被当成零调用死码误删）",
            adapter.contains("由 **W7 8.4** 在 `PhotoView` 收口时一并删除")
        )
        // B24 越界删除事故（2026-10-16）：曾按「零调用 = 死码」删掉本回滚点 ⇒
        // 破坏 W6 批次约定 + 使本用例与 `ImageItemLoadStateWiringTest` 两个用例失败。
        // 故在此把回滚点的**实现契约**也锁住：内存安全钳位一旦丢失，回滚轨即不可用。
        assertTrue(
            "回滚轨须保留小内存设备解码高度钳位（否则回滚点形同虚设）",
            adapter.contains("io.legado.app.help.MemoryPressure.isSmallHeap")
        )
        assertTrue(
            "回滚轨须保留按宽高比折算的目标高度",
            adapter.contains("ImagePyramidLoader.normalDisplayHeight(imgW, imgH, screenW, screenH)")
        )
        assertFalse(
            "回滚轨不得再有调用点",
            adapter.contains("loadIntoPhotoView(file, url, imgW, imgH, screenW, screenH, position)")
        )
    }
}