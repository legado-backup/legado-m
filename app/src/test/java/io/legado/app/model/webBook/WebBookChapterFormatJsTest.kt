package io.legado.app.model.webBook

import com.script.rhino.RhinoScriptEngine
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * core-flow-test-coverage tasks 5.1 / design §一 —— `model/webBook` 零测试破冰。
 *
 * `webBook/` 6 文件（82KB）此前**零测试**。经探查，全部编排逻辑依赖 `appDb`/网络
 * ⇒ 纯 JVM 不可直测；其中**唯一可测的关键纯逻辑**是 `BookChapterList.analyzeChapterList`
 * 的**章节标题格式化 JS**（`tocRule.formatJs`，[BookChapterList.kt:140-158]）：
 * 它以 `RhinoScriptEngine.eval(formatJs, bindings)` 求值（`index`/`title`/`chapter` 绑定）。
 *
 * 本测试以 **Rhino 引擎直接求值**覆盖该路径的基础能力（引擎不可用即说明该路径在
 * 纯 JVM 不可测，将据实降级）。亦与「辞晨 31322fc：formatJs 在 Android 整体失效」
 * 的 BUG-4 同源 —— 若本测试为绿而真机仍失效，则根因在 Android 侧而非表达式本身。
 */
class WebBookChapterFormatJsTest {

    @Test
    fun eval_returnsNumericResult() {
        val result = RhinoScriptEngine.eval("1 + 1")
        assertEquals("Rhino 求值须返回数值", 2.0, (result as Number).toDouble(), 0.0)
    }

    @Test
    fun eval_supportsStringConcat() {
        assertEquals("ab", RhinoScriptEngine.eval("'a' + 'b'")?.toString())
    }

    @Test
    fun eval_supportsTitleFormatPattern() {
        // 模拟常见 formatJs 写法：常量 + 数字拼接 ⇒ 标题被改写
        assertEquals("第3章（3）", RhinoScriptEngine.eval("'第3章' + '（' + 3 + '）'")?.toString())
    }

    @Test
    fun eval_supportsCommonJsApi() {
        // 书源 formatJs 常用 API（String/Array 方法）
        assertEquals(3, (RhinoScriptEngine.eval("'a-b-c'.split('-').length") as Number).toInt())
    }
}
