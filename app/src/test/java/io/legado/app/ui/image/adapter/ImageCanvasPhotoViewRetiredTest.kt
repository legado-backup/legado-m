package io.legado.app.ui.image.adapter

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B24：`ImageCanvasAdapter.loadIntoPhotoView` 被取代加载路径退役守护。
 *
 * 证据：同文件 `PhotoView` 族有 23 处活引用（活的 PhotoView 加载/渲染路径存在）⇒
 * 零调用的 `loadIntoPhotoView`（companion 内层 private）属旧变体（被取代），退役。
 */
class ImageCanvasPhotoViewRetiredTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `被取代的加载路径已退役且活路径仍在`() {
        val src = code("src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt")
        assertEquals("被取代的加载路径应退役", false, src.contains("fun loadIntoPhotoView("))
        assertEquals("PhotoView 活路径仍须存在", true, src.contains("PhotoView"))
    }
}
