package io.legado.app.ui.rss.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.3：订阅正文「保存图片」的 data URI 解码统一到宽容解码单源
 *
 * 原实现 `Base64.decode(data.split(",")[1], DEFAULT)`：无逗号越界 + 严格解码抛异常（正文畸形图即失败）。
 */
class ReadRssViewModelDataUriDecodeTest {

    private val code = SourceFileProbe.sourceText("ui/rss/read/ReadRssViewModel.kt")

    @Test
    fun webPicGoesThroughSharedTolerantDecoder() {
        assertTrue(
            "data URI 分支必须走单源宽容解码（含无逗号兜底）",
            code.contains("decodeTolerantBase64(data.substringAfter(',', data))")
        )
        assertFalse("不得残留 split 越界写法", code.contains("data.split(\",\").toTypedArray()[1], Base64.DEFAULT"))
    }

    @Test
    fun networkUrlBranchIsUnchanged() {
        assertTrue(
            "合法 http(s) 图片仍走网络下载分支",
            code.contains("if (URLUtil.isValidUrl(data)) {")
        )
    }
}