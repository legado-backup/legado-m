package io.legado.app.help.download

import io.legado.app.BuildConfig
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.7：下载链路默认 UA 收口到 `AppConfig.userAgent` 单源
 * （原硬编码 `Chrome/125.0.0.0` 与内置 Cronet so 版本漂移）
 */
class ChunkDownloaderUaSingleSourceTest {

    private val code = SourceFileProbe.sourceText("help/download/ChunkDownloader.kt")

    @Test
    fun defaultUaComesFromAppConfig() {
        assertTrue(
            "默认 UA 必须取 AppConfig.userAgent",
            code.contains("mapOf(\"User-Agent\" to AppConfig.userAgent)")
        )
        assertFalse("不得残留硬编码 Chrome/125", code.contains("Chrome/125"))
    }

    @Test
    fun headerPriorityIsUnchanged() {
        assertTrue(
            "任务级 headers 优先级与遗留回退链必须保持不变",
            code.contains("HeaderResolver.fromJsonHeaders(headersJson).ifEmpty {") &&
                code.contains("VideoPlay.currentPlayHeaders ?: mapOf(\"User-Agent\" to AppConfig.userAgent)")
        )
    }

    @Test
    fun cronetVersionAvailableForUaDerivation() {
        assertTrue(BuildConfig.Cronet_Main_Version.isNotBlank())
    }
}