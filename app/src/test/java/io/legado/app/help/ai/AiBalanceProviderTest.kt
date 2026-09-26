package io.legado.app.help.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Q-N3 余额取值路径的**纯函数**不变量（与上游 `AiBalanceProvider` 逐字对齐的口径）。
 *
 * 之所以全部落在纯函数上：路径解析/减号表达式是「配置式通道」的全部语义，
 * 任何一处口径漂移都会让用户拿到**错误金额**（比查不到更糟），必须以用例锁死。
 */
class AiBalanceProviderTest {

    private val payload: Map<String, Any?> = mapOf(
        "data" to mapOf(
            "total_balance" to 12.5,
            "total_credits" to "30",
            "total_usage" to 7.5,
            "amount" to 3,
            "remaining" to "abc",
            "items" to listOf(
                mapOf("value" to 1.25),
                mapOf("value" to "2.75")
            ),
            "matrix" to listOf(listOf(5, 6))
        )
    )

    private fun assertNear(expected: Double, actual: Double?) {
        assertEquals(expected, actual ?: Double.NaN, 1e-9)
    }

    // ── valueByPath ──────────────────────────────────────────────────────────

    @Test
    fun valueByPath_walksNestedObject() {
        assertNear(12.5, AiBalanceProvider.doubleOrNull(
            AiBalanceProvider.valueByPath(payload, "data.total_balance")
        ))
    }

    @Test
    fun valueByPath_readsArrayIndex() {
        assertNear(1.25, AiBalanceProvider.doubleOrNull(
            AiBalanceProvider.valueByPath(payload, "data.items[0].value")
        ))
        assertNear(2.75, AiBalanceProvider.doubleOrNull(
            AiBalanceProvider.valueByPath(payload, "data.items[1].value")
        ))
    }

    @Test
    fun valueByPath_supportsMultipleIndexesInOneSegment() {
        assertNear(6.0, AiBalanceProvider.doubleOrNull(
            AiBalanceProvider.valueByPath(payload, "data.matrix[0][1]")
        ))
    }

    @Test
    fun valueByPath_blankPathReturnsRoot() {
        assertEquals(payload, AiBalanceProvider.valueByPath(payload, "   "))
    }

    @Test
    fun valueByPath_missingKeyOrOutOfRangeReturnsNull() {
        assertNull(AiBalanceProvider.valueByPath(payload, "data.missing"))
        assertNull(AiBalanceProvider.valueByPath(payload, "data.items[5]"))
        assertNull(AiBalanceProvider.valueByPath(payload, "data.total_balance.child"))
        assertNull(AiBalanceProvider.valueByPath(payload, "data.items.value"))
    }

    // ── balanceAmountByPath ─────────────────────────────────────────────────

    @Test
    fun balanceAmount_singlePath() {
        assertNear(12.5, AiBalanceProvider.balanceAmountByPath(payload, "data.total_balance"))
        assertNear(3.0, AiBalanceProvider.balanceAmountByPath(payload, "data.amount"))
    }

    @Test
    fun balanceAmount_subtractsRemainingOperandsWhenSpacedMinus() {
        assertNear(
            22.5,
            AiBalanceProvider.balanceAmountByPath(payload, "data.total_credits - data.total_usage")
        )
        assertNear(
            8.25,
            AiBalanceProvider.balanceAmountByPath(
                payload,
                "data.total_balance - data.amount - data.items[0].value"
            )
        )
    }

    @Test
    fun balanceAmount_dashWithoutSpacesIsTreatedAsKeyName() {
        assertNull(
            AiBalanceProvider.balanceAmountByPath(
                payload,
                "data.total_credits-data.total_usage"
            )
        )
    }

    @Test
    fun balanceAmount_anyOperandUnresolvableMakesWholeExpressionNull() {
        assertNull(AiBalanceProvider.balanceAmountByPath(payload, "data.total_credits - data.missing"))
        assertNull(AiBalanceProvider.balanceAmountByPath(payload, "data.missing - data.total_usage"))
        // 字符串非数字 ⇒ 不兜底成 0
        assertNull(AiBalanceProvider.balanceAmountByPath(payload, "data.remaining"))
        assertNull(AiBalanceProvider.balanceAmountByPath(payload, "data.remaining - data.amount"))
    }

    @Test
    fun balanceAmount_blankPathIsNotNumeric() {
        assertNull(AiBalanceProvider.balanceAmountByPath(payload, ""))
    }

    @Test
    fun balanceAmount_negativeResultIsKept() {
        assertNear(
            -2.0,
            AiBalanceProvider.balanceAmountByPath(payload, "data.amount - data.matrix[0][0]")
        )
    }

    // ── doubleOrNull ────────────────────────────────────────────────────────

    @Test
    fun doubleOrNull_acceptsNumbersAndNumericStringsOnly() {
        assertNear(3.0, AiBalanceProvider.doubleOrNull(3))
        assertNear(3.5, AiBalanceProvider.doubleOrNull(" 3.5 "))
        assertNull(AiBalanceProvider.doubleOrNull(true))
        assertNull(AiBalanceProvider.doubleOrNull(mapOf("a" to 1)))
        assertNull(AiBalanceProvider.doubleOrNull(listOf(1)))
        assertNull(AiBalanceProvider.doubleOrNull(null))
        assertNull(AiBalanceProvider.doubleOrNull("abc"))
    }

    // ── resolveBalanceUrl ───────────────────────────────────────────────────

    @Test
    fun resolveBalanceUrl_keepsAbsoluteAddress() {
        assertEquals(
            "https://example.com/custom/balance",
            AiBalanceProvider.resolveBalanceUrl(
                "https://example.com/v1",
                "https://example.com/custom/balance"
            )
        )
    }

    @Test
    fun resolveBalanceUrl_joinsRelativePathToBaseRoot() {
        assertEquals(
            "https://example.com/v1/user/balance",
            AiBalanceProvider.resolveBalanceUrl("https://example.com/v1", "user/balance")
        )
        assertEquals(
            "https://example.com/v1/user/balance",
            AiBalanceProvider.resolveBalanceUrl(
                "https://example.com/v1/chat/completions",
                "/user/balance"
            )
        )
        assertEquals(
            "https://example.com/v1/user/balance",
            AiBalanceProvider.resolveBalanceUrl("https://example.com/v1/responses", "user/balance")
        )
    }
}