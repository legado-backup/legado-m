package io.legado.app.ui.image

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.3（REQ-32）：**图片订阅路径打标入口**接线不变量。
 *
 * 图片路径落点选在**长按图片菜单**（而非工具栏下拉）：只有长按事件携带「当前这张图」的 URL，
 * 工具栏菜单在画布态没有确定的当前图 ⇒ 落到工具栏会产出锚点不明的书签。
 *
 * 另锁载荷：`anchor` 必须**同时**带 `imageUrl` 与 `articleLink` —— 后者是跳回时重建 `ImagePlay`
 * 取图上下文的必要输入（`ReadRss.readNoHtml` 同口径），漏存会让跳回拿不到图。
 */
class SceneBookmarkImageEntryTest {

    private val activity by lazy { SourceFileProbe.sourceText("ui/image/ImageGalleryActivity.kt") }

    @Test
    fun longPressMenuCarriesSceneEntry() {
        assertTrue(
            "长按菜单未追加「加入名场面」",
            activity.contains("getString(R.string.scene_bookmark_add)")
        )
        assertTrue(
            "长按菜单未分发到打标方法",
            activity.contains("3 -> addSceneBookmarkFromImage(imageUrl)")
        )
    }

    @Test
    fun payloadKeepsImageAndArticleLink() {
        assertTrue(
            "图片路径 contentKind 必须为 KIND_IMAGE",
            activity.contains("contentKind = SceneBookmarkHelper.KIND_IMAGE")
        )
        assertTrue(
            "锚点必须同时存 imageUrl 与 articleLink（漏存则跳回取不到图）",
            activity.contains("SceneBookmarkHelper.imageAnchor(imageUrl, article?.link.orEmpty())")
        )
    }
}
