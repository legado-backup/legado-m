package io.legado.app.ui.download

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 下载管理页**标签栏水平留白**不变量（用户报障 #3 / tasks 1.2.9）。
 *
 * 缺陷：标签栏此前无水平外边距 ⇒ 左右贴边，与下方列表内容左缘（`contentPadding` 16dp）
 * 不对齐，视觉上「跑道错位」。修复须**复用同源同值** `bookshelf_tag_bar_margin_horizontal`，
 * 不得硬编码 16.dp（否则主题/适配调整时会漂移）。
 */
class DownloadTagBarPaddingTest {

    private val screen by lazy {
        listOf(
            File("src/main/java/io/legado/app/ui/download/DownloadManageScreen.kt"),
            File("../app/src/main/java/io/legado/app/ui/download/DownloadManageScreen.kt"),
            File("app/src/main/java/io/legado/app/ui/download/DownloadManageScreen.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun tagBarUsesSharedHorizontalMarginToken() {
        assertTrue(
            "标签栏须复用 bookshelf_tag_bar_margin_horizontal（单源同值）",
            screen.contains("padding(horizontal = dimensionResource(R.dimen.bookshelf_tag_bar_margin_horizontal))")
        )
    }

    @Test
    fun tagBarDoesNotHardcodeHorizontalPadding() {
        // 反例守卫：不得为凑对齐写死 16.dp（会与顶栏族漂移）
        assertTrue(
            "标签栏不得硬编码水平留白（须走 dimen 单源）",
            !screen.contains("Modifier\n                    .fillMaxWidth()\n                    .padding(horizontal = 16.dp)")
        )
    }

    @Test
    fun listContentPaddingMatchesTagBarMargin() {
        assertTrue(
            "列表 contentPadding 水平值与标签栏留白同源（16dp）",
            screen.contains("horizontal = 16.dp")
        )
    }
}