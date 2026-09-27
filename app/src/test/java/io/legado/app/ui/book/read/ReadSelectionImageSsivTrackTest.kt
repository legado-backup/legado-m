package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W6 7.3（AD-10/AD-21）：选段 AI 配图预览对话框呈现轨收敛为 SSIV 的不变量。
 *
 * 该预览原为 `AndroidView { PhotoView } + Glide.into`；收敛后直接绑本地文件
 * （`AiGeneratedImage.localPath` 为绝对路径），与 `AiImagePreviewDialog` 同构。
 */
class ReadSelectionImageSsivTrackTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val dialog by lazy {
        read("src/main/java/io/legado/app/ui/book/read/ReadSelectionImageDialog.kt")
    }

    @Test
    fun previewUsesSsivInsteadOfPhotoView() {
        assertTrue("须用 SSIV", dialog.contains("SubsamplingScaleImageView(ctx)"))
        assertFalse("不得再引用 PhotoView", dialog.contains("PhotoView(ctx)"))
        assertFalse("不得再留 PhotoView import", dialog.contains("ui.widget.image.PhotoView"))
    }

    @Test
    fun bindsLocalFileThroughPyramidLoader() {
        assertTrue("须走统一绑定入口", dialog.contains("ImagePyramidLoader.bindNormalImage(ssiv, file)"))
        assertTrue("须先校验文件存在（缺失时不绑空源）", dialog.contains("if (file.exists())"))
    }
}