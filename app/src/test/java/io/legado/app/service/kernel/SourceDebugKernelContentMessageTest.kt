package io.legado.app.service.kernel

import io.legado.app.constant.BookSourceType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 正文链失败文案组装回归（tasks 4.8.4 / 4.8.6，E-1 / E-4）。
 *
 * 背景（2026-10-26 真机实测）：视频源在「内置浏览器播放」模式下 `getContent` **按设计返回空串**
 * （取流交由网页播放器），但 `source_content_test` 原先统一报「正文规则解析失败」⇒ 把预期行为
 * 误读成源规则坏了。现按源变量 `playmode` 分两种成因给可读结论。
 *
 * 本测试直接调用真实实现（`internal` 纯函数），断言**带期望值的输出**，而非源码文本。
 */
class SourceDebugKernelContentMessageTest {

    private fun msg(err: String, type: Int, variable: String?) =
        SourceDebugKernel.contentFailureMessage(err, type, variable)

    @Test
    fun videoBrowserMode_saysEmptyIsExpected() {
        val text = msg("ContentEmptyException: 内容为空", BookSourceType.video, "playmode=browser")
        assertTrue("须保留底层异常文本（可追溯）", text.contains("ContentEmptyException"))
        assertTrue("浏览器模式须说明空正文属预期", text.contains("属预期"))
        assertFalse("浏览器模式不得再报「规则解析失败」（这正是被误读的成因）",
            text.contains("正文规则解析失败"))
    }

    @Test
    fun videoSniffMode_saysNoAddressWithNextStep() {
        val text = msg("ContentEmptyException: 内容为空", BookSourceType.video, "")
        assertTrue("嗅探模式须说明未取到地址", text.contains("未提取到可播放地址"))
        assertTrue("须给出登录这条可操作路径", text.contains("登录"))
        assertFalse("嗅探模式不应把成因归给浏览器模式", text.contains("属预期"))
    }

    @Test
    fun videoSniffMode_withOtherVariablesStillDetected() {
        // 变量串里还有别的键时，判定只认 playmode（不因多键而失效）
        val text = msg("boom", BookSourceType.video, "diag=1;playmode=browser")
        assertTrue("多键变量串仍应识别浏览器模式", text.contains("属预期"))
    }

    @Test
    fun nonVideoSource_keepsLegacyWording() {
        val text = msg("NullPointerException: x", BookSourceType.default, "playmode=browser")
        assertTrue("非视频源保持既有口径（未定位到具体规则行）",
            text.contains("未定位到具体规则行"))
        assertFalse("非视频源不得追加视频专属提示", text.contains("属预期"))
    }

    @Test
    fun messageAlwaysKeepsRawErrorPrefix() {
        assertEquals(
            "文案结构固定为「原始错误；结论」",
            "E；正文规则解析失败，未定位到具体规则行（既有解析 API 不返回失败规则/行号）",
            msg("E", BookSourceType.default, null),
        )
    }
}
