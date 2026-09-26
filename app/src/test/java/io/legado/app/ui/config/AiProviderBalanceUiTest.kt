package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N3 余额查询的「接线 + 展示」不变量。
 *
 * 三件必须锁死的事：
 * ①编辑页真的渲染了两个输入框与「查询余额」按钮（否则配置项无法录入 ⇒ 功能不可达）；
 * ②保存路径逐字段透传（`.copy(...)` 固定字段列表，漏了就「保存即丢」）；
 * ③结果弹框的金额格式化口径（尾随 0 不显示、NaN 显示占位符）。
 */
class AiProviderBalanceUiTest {

    private fun editScreen(): String = SourceFileProbe.sourceText("ui/config/AiProviderEditScreen.kt")

    private fun editActivity(): String = SourceFileProbe.sourceText("ui/config/AiProviderEditActivity.kt")

    @Test
    fun editScreen_exposesBalanceFieldsAndQueryButton() {
        val source = editScreen()
        assertTrue(source.contains("R.string.ai_balance_url"))
        assertTrue(source.contains("R.string.ai_balance_json_path"))
        assertTrue(source.contains("R.string.ai_query_balance"))
        assertTrue(source.contains("onBalanceUrlChange"))
        assertTrue(source.contains("onBalanceJsonPathChange"))
    }

    @Test
    fun editActivity_savesBalanceFieldsAndQueriesProvider() {
        val source = editActivity()
        assertTrue("保存时须透传 balanceUrl", source.contains("balanceUrl = balanceUrl"))
        assertTrue("保存时须透传 balanceJsonPath", source.contains("balanceJsonPath = balanceJsonPath"))
        assertTrue("查询须走 AiBalanceProvider", source.contains("AiBalanceProvider.query(provider)"))
        assertTrue(
            "未填地址时应直接提示，不发起请求",
            source.contains("R.string.ai_balance_url_required")
        )
    }

    @Test
    fun balanceFormat_keepsSignificantDecimalsOnly() {
        assertEquals("12.5", AiBalanceResultDialog.formatAmount(12.5))
        assertEquals("3", AiBalanceResultDialog.formatAmount(3.0))
        assertEquals("1.2346", AiBalanceResultDialog.formatAmount(1.23456))
        assertEquals("-", AiBalanceResultDialog.formatAmount(Double.NaN))
    }
}