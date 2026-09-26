package io.legado.app.ui.video

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.1.1（P0-7）· 宿主侧：`VideoPlayerActivity.initFromIntent` 的书架状态缺省口径
 *
 * 旧行为：`intent.getBooleanExtra("inBookshelf", true)` 恒缺省「已入架」⇒ 从搜索/发现直接起播
 * （`:784` 等路径不带该 extra）的**临时书**被误判为已入架，退出时不再询问加入书架。
 * 新口径：真实身份由 `VideoPlay.initSource` 按库中 `notShelf` 位解析；宿主只负责
 * 「无 bookUrl ⇒ 无身份 ⇒ 恒已入架」这一结构性缺省。
 */
class VideoPlayerActivityBookshelfIntentTest {

    private val code = SourceFileProbe.sourceText("ui/video/VideoPlayerActivity.kt")

    @Test
    fun noBookUrlKeepsInShelfDefault() {
        assertTrue(
            "无 bookUrl（纯 URL 直连/下载播放）必须保持已入架，避免对空 book 走加入书架链路",
            code.contains("VideoPlay.inBookshelf = if (bookUrl.isNullOrBlank()) {")
        )
    }

    @Test
    fun bookUrlPathStillAcceptsExplicitExtra() {
        assertTrue(
            "有 bookUrl 时仍先取传入值（随后由 initSource 用库中身份纠正）",
            code.contains("intent.getBooleanExtra(\"inBookshelf\", true)")
        )
    }

    @Test
    fun shelfStateIsNoLongerUnconditionallyTrue() {
        assertFalse(
            "不得再出现「无条件取 extra 缺省 true」的旧写法",
            code.contains("VideoPlay.inBookshelf = intent.getBooleanExtra(\"inBookshelf\", true)")
        )
    }
}