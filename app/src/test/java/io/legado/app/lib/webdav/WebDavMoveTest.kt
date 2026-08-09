package io.legado.app.lib.webdav

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * WebDav.move() 请求构造核心单元测试（B14 WebDAV 删除/重命名）
 *
 * 验证点：
 * 1. davs:// 前缀转 https://（坚果云默认 davs://）
 * 2. dav:// 前缀转 http://
 * 3. 已是 https/http 的 URL 保持不变
 * 4. 无 scheme 的纯路径不误转
 *
 * 测试用 companion 纯函数 WebDav.toHttpUrl，不依赖 Android 框架，纯 JVM 可运行。
 *
 * 已知上限：未直接测 move() 的 MOVE 方法 + Destination/Overwrite 头（依赖 okHttpClient/Android 框架） |
 * 升级路径：引入 MockWebServer 验证请求方法/头字段
 */
class WebDavMoveTest {

    @Test
    fun toHttpUrl_davsUrl_becomesHttps() {
        assertEquals(
            "davs:// 应转 https://",
            "https://dav.jianguoyun.com/dav/backup-20260807.zip",
            WebDav.toHttpUrl("davs://dav.jianguoyun.com/dav/backup-20260807.zip")
        )
    }

    @Test
    fun toHttpUrl_davUrl_becomesHttp() {
        assertEquals(
            "dav:// 应转 http://",
            "http://example.com/dav/backup.zip",
            WebDav.toHttpUrl("dav://example.com/dav/backup.zip")
        )
    }

    @Test
    fun toHttpUrl_httpsUrl_unchanged() {
        assertEquals(
            "已 https:// 不应变",
            "https://dav.jianguoyun.com/dav/backup.zip",
            WebDav.toHttpUrl("https://dav.jianguoyun.com/dav/backup.zip")
        )
    }

    @Test
    fun toHttpUrl_httpUrl_unchanged() {
        assertEquals(
            "已 http:// 不应变",
            "http://example.com/dav/backup.zip",
            WebDav.toHttpUrl("http://example.com/dav/backup.zip")
        )
    }

    @Test
    fun toHttpUrl_plainPath_unchanged() {
        assertEquals(
            "无 scheme 纯路径不应误转",
            "/dav/backup.zip",
            WebDav.toHttpUrl("/dav/backup.zip")
        )
    }

    @Test
    fun toHttpUrl_queryString_preserved() {
        assertEquals(
            "查询串应保留",
            "https://dav.jianguoyun.com/dav/backup.zip?x=1",
            WebDav.toHttpUrl("davs://dav.jianguoyun.com/dav/backup.zip?x=1")
        )
    }
}
