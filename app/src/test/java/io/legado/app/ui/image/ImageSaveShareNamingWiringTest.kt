package io.legado.app.ui.image

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.4 / 6.5（REQ-23 / REQ-24）：图片**保存命名**与**分享**的接线不变量。
 *
 * 为什么值得测（实证根因）：
 * - 保存：两处（画布 `ImageCanvasViewModel`、详情 `ImageDetailActivity`）各写一份
 *   秒级时间戳名 ⇒ ① 无语义；② 同秒保存静默覆盖（`createFileIfNotExist` 复用同名文档）。
 * - 分享：两处各写 `sendToClip(url)` ⇒ 名为分享实为复制链接。
 * 两处都必须收敛到同一实现（单源），否则下次只在其中一处修 bug。
 */
class ImageSaveShareNamingWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val canvasVm by lazy { read("src/main/java/io/legado/app/ui/image/ImageCanvasViewModel.kt") }
    private val detailAct by lazy { read("src/main/java/io/legado/app/ui/image/ImageDetailActivity.kt") }
    private val galleryAct by lazy { read("src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt") }
    private val imagePlay by lazy { read("src/main/java/io/legado/app/ui/image/ImagePlay.kt") }

    private fun shareBody(src: String): String =
        Regex("private fun shareImage\\(imageUrl: String\\) \\{([\\s\\S]*?)\\n    \\}")
            .find(src)?.groupValues?.get(1) ?: ""

    @Test
    fun bothSaveSitesUseSemanticNamingWithDedup() {
        for ((tag, src) in listOf("画布" to canvasVm, "详情" to detailAct)) {
            assertTrue("$tag：须用语义命名器", src.contains("ImageFileNameBuilder.build("))
            assertTrue("$tag：须做目标目录重名消解", src.contains("ImageFileNameBuilder.uniqueNameFor("))
            assertFalse("$tag：不得残留秒级时间戳命名", src.contains("AppConst.fileNameFormat.format("))
        }
    }

    @Test
    fun namingContextComesFromSingleSourceInImagePlay() {
        assertTrue("须有统一的上下文推导入口", imagePlay.contains("fun nameContextOf(url: String)"))
        assertTrue("须含来源名", imagePlay.contains("rssSource?.sourceName"))
        assertTrue("须含文章标题（章节语义）", imagePlay.contains("rssArticles?.getOrNull(articleIndex)?.title"))
        assertTrue("须含序号", imagePlay.contains("index = position"))
    }

    @Test
    fun bothShareSitesUseFileProviderHelperInsteadOfClipboard() {
        for ((tag, src) in listOf("画布" to galleryAct, "详情" to detailAct)) {
            val body = shareBody(src)
            assertTrue("$tag：须走 ImageShareHelper", body.contains("ImageShareHelper.shareImage("))
            assertFalse("$tag：分享入口不得再复制链接", body.contains("sendToClip"))
        }
    }

    @Test
    fun canvasVmStillClearsCachedSavePathOnFailure() {
        assertTrue(
            "保存失败须继续清理 ACache 目录记忆（既有行为不得丢）",
            canvasVm.contains("ACache.get().remove(AppConst.imagePathKey)")
        )
    }
}