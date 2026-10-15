package io.legado.app.model.analyzeRule

import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.9 —— `QueryTTF`（字体反爬解析）零覆盖补齐（**边界防御**）。
 *
 * 真实字体解析需完整 TTF 字节数组（构造成本高），此处**只钉边界契约**：
 * 畸形/截断输入必须快速失败（不挂死、不无限循环）。
 * `@Test(timeout=5000)` 即"防挂死"的硬断言（超时判失败）。
 */
class QueryTTFBoundaryTest {

    @Test(timeout = 5000)
    fun truncatedBuffer_failsFastInsteadOfHanging() {
        var thrown = false
        try {
            QueryTTF(ByteArray(4))
        } catch (t: Throwable) {
            thrown = true
        }
        assertTrue("截断字体字节须快速失败（不得挂死/静默成功）", thrown)
    }

    @Test(timeout = 5000)
    fun emptyBuffer_failsFastInsteadOfHanging() {
        var thrown = false
        try {
            QueryTTF(ByteArray(0))
        } catch (t: Throwable) {
            thrown = true
        }
        assertTrue("空字体字节须快速失败（不得挂死）", thrown)
    }
}
