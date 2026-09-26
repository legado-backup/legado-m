package io.legado.app.ui.image.adapter

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * CF 6.2 死件退役配对测试（图片浏览旧版 Pager 架构）。
 *
 * 背景（实测取证 2026-09-26）：V4 重写后图片浏览已改为「单 RecyclerView 垂直长画布
 * + ImageCanvasAdapter」，旧的外层 `ImageArticlePagerAdapter`（ViewPager2 垂直跨文章）
 * 与内层 `ImagePageAdapter`（ViewPager2 水平跨图）**再无实例创建**（全仓仅自身文件命中）
 * ⇒ 二者连同 `item_image_article` 一并退役（`item_image_page` 仍由 `ImageDetailAdapter` 在用，保留）。
 */
class ImageLegacyPagerAdapterRetiredTest {

    private fun mainJava(rel: String): File =
        File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel")

    @Test
    fun legacyPagerAdaptersAreGone() {
        listOf(
            "ui/image/ImageArticlePagerAdapter.kt",
            "ui/image/ImagePageAdapter.kt"
        ).forEach { rel ->
            assertFalse("旧版 Pager 适配器应已退役：$rel", mainJava(rel).isFile)
        }
    }

    @Test
    fun deadItemLayoutIsGone() {
        assertFalse(
            "死 item 布局应已退役：item_image_article.xml",
            File(SourceFileProbe.layoutDir(), "item_image_article.xml").isFile
        )
    }

    @Test
    fun detailAdapterNoLongerReferencesRetiredPager() {
        val detail = SourceFileProbe.sourceText("ui/image/adapter/ImageDetailAdapter.kt")
        assertFalse(
            "ImageDetailAdapter 不得引用已退役的 ImageArticlePagerAdapter / ImagePageAdapter（含过时注释）",
            detail.contains("ImageArticlePagerAdapter") || detail.contains("ImagePageAdapter")
        )
    }
}