package io.legado.app.web

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 端口策略单源回归（一期 §6 · 端口合法区间）。
 *
 * 该策略被两处消费：`WebService.getPort()`（服务实际绑定端口）与设置页端口选择器
 * （min/max）。**归一的动因**是实测到的漂移：原「其他设置」页选择器上限写 `60000`，
 * 而服务侧判 `..65530` ⇒ 60001~65530 在选择器里根本选不到。
 */
class WebPortPolicyTest {

    @Test
    fun normalize_keepsValuesInsideRange() {
        assertEquals(1024, WebPortPolicy.normalize(1024))
        assertEquals(1122, WebPortPolicy.normalize(1122))
        assertEquals(60000, WebPortPolicy.normalize(60000))
        assertEquals(65530, WebPortPolicy.normalize(65530))
    }

    @Test
    fun normalize_fallsBackToDefaultOutsideRange() {
        assertEquals(
            "下限之下（含特权端口）⇒ 回落默认端口",
            WebPortPolicy.DEFAULT,
            WebPortPolicy.normalize(1023)
        )
        assertEquals(
            "上限之上（保留段）⇒ 回落默认端口",
            WebPortPolicy.DEFAULT,
            WebPortPolicy.normalize(65531)
        )
        assertEquals("0 / 负数同样回落", WebPortPolicy.DEFAULT, WebPortPolicy.normalize(0))
        assertEquals("负数同样回落", WebPortPolicy.DEFAULT, WebPortPolicy.normalize(-1))
        assertEquals("Int 极值不得触发异常", WebPortPolicy.DEFAULT, WebPortPolicy.normalize(Int.MAX_VALUE))
    }

    @Test
    fun defaultPortIsInsideRange() {
        assertEquals(
            "默认端口必须在合法区间内（否则 normalize(DEFAULT) 不幂等）",
            WebPortPolicy.DEFAULT,
            WebPortPolicy.normalize(WebPortPolicy.DEFAULT)
        )
        assertEquals("默认端口保持既有出厂值", 1122, WebPortPolicy.DEFAULT)
    }

    @Test
    fun rangeIsSingleSourceForPickerBounds() {
        assertEquals("选择器下界须取区间首值", 1024, WebPortPolicy.RANGE.first)
        assertEquals("选择器上界须取区间末值", 65530, WebPortPolicy.RANGE.last)
    }
}
