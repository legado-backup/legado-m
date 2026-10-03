package io.legado.app.ui.rss.article.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅封面图**请求生命周期契约**回归测试（2026-10-01 缺陷④）。
 *
 * 背景：用户报障「瀑布样式翻页/上下滑时列表图片严重变形或花掉」。根因是把解码尺寸 `boxSize` 当作
 * `DisposableEffect` 的重启键，而瀑布流盒高由比例回填驱动 ⇒ 图片就绪即重启 effect ⇒ `onDispose`
 * 对**仍在显示的 Bitmap** 执行 `Glide.clear`（退回 `BitmapPool` 后被其它请求复用覆写像素）。
 *
 * 双向断言（缺一不可）：
 * ① 键**不得**含 `boxSize` —— 防「尺寸再次成为重启键」复发；
 * ② `onDispose` 内**必须**保留 `Glide.clear` —— 防「为了不花屏而放弃离屏取消 ⇒ target 泄漏」。
 */
class RssArticleImageLifecycleContractTest {

    private val source: String by lazy {
        SourceFileProbe.sourceText("ui/rss/article/compose/RssArticleImage.kt")
    }

    @Test
    fun effectKeyIsSourceIdentityOnly() {
        assertTrue(
            "缺陷④：DisposableEffect 的键必须收敛为图源标识 (origin, link)",
            source.contains("DisposableEffect(origin, link)")
        )
        assertFalse(
            "缺陷④：键中不得再出现 boxSize / persistRatio（尺寸变化会重启 effect ⇒ clear 掉在显示的 Bitmap）",
            Regex("""DisposableEffect\([^)]*(boxSize|persistRatio)""").containsMatchIn(source)
        )
    }

    @Test
    fun disposeStillCancelsRequest() {
        assertTrue(
            "离屏取消能力不可回退：onDispose 内必须保留 Glide.clear(target)（否则泄漏 target）",
            Regex("""onDispose\s*\{[\s\S]*?Glide\.with\([^)]*\)\.clear\(""").containsMatchIn(source)
        )
    }

    @Test
    fun decodeSizeIsWaitedOnceNotUsedAsKey() {
        assertTrue(
            "解码尺寸应「等首个非零测量后一次性取用」（snapshotFlow + first），而非作为 effect 键",
            source.contains("snapshotFlow { boxSize }.first { it.width > 0 && it.height > 0 }")
        )
    }
}