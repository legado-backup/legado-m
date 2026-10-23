package io.legado.app.ui.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 本地视频外部播放的路径判定（2026-10-23 js-source-parity-and-crash-fix R7）。
 *
 * 真机崩溃：`FileUriExposedException`（`VideoPlayerActivity.openInOtherPlayer` 外发 `file://`）。
 * 判定写错的代价是双向的：漏判 ⇒ 崩溃；误判 ⇒ 网络地址被当文件、能播的播不了。
 */
class VideoExternalOpenPolicyTest {

    @Test
    fun fileSchemeResolvesToFile() {
        val file = VideoExternalOpenPolicy.localFileOf("file:///storage/emulated/0/Download/demo.mp4")
        assertEquals(
            "/storage/emulated/0/Download/demo.mp4",
            VideoExternalOpenPolicy.localFilePathOf("file:///storage/emulated/0/Download/demo.mp4")
        )
        assertEquals(
            "/storage/emulated/0/Download/demo.mp4",
            file?.invariantSeparatorsPath
        )
    }

    @Test
    fun fileSchemeIsCaseInsensitive() {
        assertEquals(
            "/sdcard/a.mp4",
            VideoExternalOpenPolicy.localFilePathOf("FILE:///sdcard/a.mp4")
        )
    }

    @Test
    fun bareAbsolutePathResolvesToFile() {
        assertEquals(
            "/storage/emulated/0/Movies/b.m3u8",
            VideoExternalOpenPolicy.localFilePathOf("/storage/emulated/0/Movies/b.m3u8")
        )
    }

    @Test
    fun networkAndContentUrlsAreNotLocal() {
        assertNull(VideoExternalOpenPolicy.localFileOf("http://example.com/a.mp4"))
        assertNull(VideoExternalOpenPolicy.localFileOf("https://example.com/a.m3u8"))
        assertNull(VideoExternalOpenPolicy.localFileOf("content://media/external/video/1"))
        // 协议相对地址（//host/path）不是本地文件
        assertNull(VideoExternalOpenPolicy.localFileOf("//example.com/a.mp4"))
        // file:// 带 host 的形式（file://host/path）同样不支持外发
        assertNull(VideoExternalOpenPolicy.localFileOf("file://example.com/a.mp4"))
    }

    @Test
    fun blankInputIsNotLocal() {
        assertNull(VideoExternalOpenPolicy.localFileOf(null))
        assertNull(VideoExternalOpenPolicy.localFileOf(""))
        assertNull(VideoExternalOpenPolicy.localFileOf("file://"))
    }
}
