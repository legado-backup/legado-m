package io.legado.app.help.exoplayer

import io.legado.app.BuildConfig
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.7：UA 的 Chrome 版本与内置 Cronet so 版本一致（单源）
 */
class BrowserUaCronetVersionTest {

    @Test
    fun browserUaEmbedsCronetMainVersion() {
        assertTrue("BuildConfig.Cronet_Main_Version 不得为空", BuildConfig.Cronet_Main_Version.isNotBlank())
        assertTrue(
            "浏览器 UA 必须内嵌 Cronet so 主版本",
            ExoPlayerHelper.BROWSER_UA.contains("Chrome/${BuildConfig.Cronet_Main_Version}")
        )
    }

    @Test
    fun noHardcodedChromeVersionLeftInExoPlayerHelper() {
        val code = SourceFileProbe.sourceText("help/exoplayer/ExoPlayerHelper.kt")
        assertFalse("不得残留硬编码 Chrome/120", code.contains("Chrome/120"))
        assertTrue(
            "必须改用 BuildConfig.Cronet_Main_Version 单源",
            code.contains("Chrome/\${BuildConfig.Cronet_Main_Version} Mobile Safari/537.36")
        )
    }
}