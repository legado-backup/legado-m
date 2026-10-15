package io.legado.app.model

import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-59 配对测试：媒体目录「占位地址」判定的行为契约。
 *
 * 背景：`MediaTocRefresh` 整族此前**零调用** ⇒ 设置项「自动刷新媒体目录」形同虚设。
 * 接线后该判定成为「打开媒体书籍时是否要重取目录」的唯一开关，判错两个方向都有害：
 *  - 误判为占位 ⇒ 每次打开都多打一轮目录请求（慢，且更易被风控）；
 *  - 漏判占位 ⇒ 正文加载恒失败（用户侧表现为"打开就白屏/无图"）。
 */
class MediaTocRefreshTest {

    private fun chapter(url: String, title: String = "第1话", isVolume: Boolean = false) =
        BookChapter(url = url, title = title, isVolume = isVolume)

    @Test
    fun `空地址按占位处理`() {
        assertTrue(MediaTocRefresh.isPlaceholderUrl(chapter("")))
    }

    @Test
    fun `纯空白地址按占位处理`() {
        assertTrue(MediaTocRefresh.isPlaceholderUrl(chapter("   ")))
    }

    @Test
    fun `地址等于章名按占位处理`() {
        assertTrue(MediaTocRefresh.isPlaceholderUrl(chapter("第1话", "第1话")))
    }

    @Test
    fun `地址以章名开头按占位处理`() {
        // 与 BookChapter.getAbsoluteURL 的占位分支（url.startsWith(title)）同口径
        assertTrue(MediaTocRefresh.isPlaceholderUrl(chapter("第1话-上", "第1话")))
    }

    @Test
    fun `真实地址不判为占位`() {
        assertFalse(MediaTocRefresh.isPlaceholderUrl(chapter("https://example.invalid/1.html", "第1话")))
    }

    @Test
    fun `卷行永不判为占位`() {
        assertFalse(MediaTocRefresh.isPlaceholderUrl(chapter("", "第一卷", isVolume = true)))
        assertFalse(MediaTocRefresh.isPlaceholderUrl(chapter("第一卷", "第一卷", isVolume = true)))
    }
}
