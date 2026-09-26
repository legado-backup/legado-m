package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N3 回归防线：`AppConfig.normalizeAiProviders` 的**固定字段重建**不得丢新增字段。
 *
 * 缺陷型（本轮实测）：该函数用「逐字段 new 对象」的方式归一化 Provider 列表，
 * 任何未在此处列举的字段都会在**每次读取**时被静默丢弃（表现为「编辑页保存了余额地址，
 * 退出再进就没了」）。本用例把两个字段的透传写成结构不变量，防止后续再被漏掉。
 */
class AppConfigAiProviderBalanceTest {

    private fun normalizeBlock(): String {
        val source = SourceFileProbe.sourceText("help/config/AppConfig.kt")
        val start = source.indexOf("private fun normalizeAiProviders")
        assertTrue("未找到 normalizeAiProviders（口径漂移）", start >= 0)
        val end = source.indexOf("private fun normalizeAiModels", start)
        assertTrue("未找到 normalizeAiModels 边界", end > start)
        return source.substring(start, end)
    }

    @Test
    fun normalizeAiProviders_keepsBalanceFields() {
        val block = normalizeBlock()
        assertTrue(
            "normalizeAiProviders 必须透传 balanceUrl（否则读取即丢）",
            block.contains("balanceUrl = safeString { provider.balanceUrl }")
        )
        assertTrue(
            "normalizeAiProviders 必须透传 balanceJsonPath（否则读取即丢）",
            block.contains("balanceJsonPath = safeString { provider.balanceJsonPath }")
        )
    }
}