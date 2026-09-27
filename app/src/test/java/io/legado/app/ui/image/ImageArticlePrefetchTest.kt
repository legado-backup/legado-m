package io.legado.app.ui.image

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W7 8.2 / REQ-30：**文章级离线预取**的挂钩点与口径不变量。
 *
 * 三条易失守约定：
 * ① 独立配置键且**默认关闭**（不改变既有行为）；
 * ② **挂钩点唯一**（本处紧跟 `extractImageList`）—— 多处挂钩会重复下载；
 * ③ 口径固定：并发 2 / 单文章 ≤200 张 / 单张失败不阻塞 / **复用既有 Glide downloadOnly 通道**。
 */
class ImageArticlePrefetchTest {

    private fun vm(): String =
        SourceFileProbe.sourceText("ui/image/ImageCanvasViewModel.kt").replace("\r\n", "\n")

    private fun config(): String =
        SourceFileProbe.sourceText("help/config/AppConfig.kt").replace("\r\n", "\n")

    private fun keys(): String =
        SourceFileProbe.sourceText("constant/PreferKey.kt").replace("\r\n", "\n")

    @Test
    fun switchKeyExistsAndDefaultsOff() {
        assertTrue(
            "须有独立配置键 `imageArticlePrefetch`",
            keys().contains("""const val imageArticlePrefetch = "imageArticlePrefetch"""")
        )
        assertTrue(
            "默认必须**关闭**（不改变既有行为）",
            config().contains("getPrefBoolean(PreferKey.imageArticlePrefetch, false)")
        )
    }

    @Test
    fun hookIsSingleAndGatedAfterExtraction() {
        val s = vm()
        val hooks = Regex("""if \(AppConfig\.imageArticlePrefetch\)""").findAll(s).count()
        assertEquals("挂钩点必须唯一（多处挂钩会重复下载）", 1, hooks)
        assertTrue(
            "须在 `extractImageList` **之后**挂钩（否则拿不到图片列表）",
            s.indexOf("AppConfig.imageArticlePrefetch") > s.indexOf("ImageUrlExtractor.extractImageList(")
        )
    }

    @Test
    fun prefetchLimitsAreFixedByDesign() {
        val s = vm()
        assertTrue("并发须为 2（分批 chunked(2)）", s.contains("chunked(2)"))
        assertTrue("单文章上限 200 张（take(200)）", s.contains("take(200)"))
        assertTrue(
            "单张失败不阻塞（runCatching 吞掉，不影响主链路）",
            s.contains("kotlin.runCatching { ImageLoader.loadFile(context, url)")
        )
        assertTrue(
            "必须复用既有 Glide downloadOnly 通道（不另建缓存层）",
            s.contains("ImageLoader.loadFile(")
        )
    }

    @Test
    fun switchHasSettingsEntryAndSearchRegistration() {
        assertTrue(
            "设置页须有开关入口",
            SourceFileProbe.sourceText("ui/config/OtherConfigFragment.kt")
                .contains("key = PreferKey.imageArticlePrefetch")
        )
        assertTrue(
            "pref XML 须同步登记（设置搜索收录）",
            SourceFileProbe.sourceTextByPath("src/main/res/xml/pref_config_other.xml")
                .contains("""android:key="imageArticlePrefetch"""")
        )
    }
}