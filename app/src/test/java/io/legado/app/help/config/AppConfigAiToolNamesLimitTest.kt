package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 结构性回归防线（IF-24）：`AppConfig.aiEnabledToolNames` 的**写入侧必须有边界归一**。
 *
 * 缺陷型（2026-10-13 真机实测）：该键是 `SharedPreferences` string-set，由 UI 与 MCP 工具
 * `ai_agent_config_save` 共同写入；旧 setter 只做 `filter { it.isNotBlank() }`，
 * 畸形入参被原样落盘 ⇒ 调试机上单键被写成 **155MB**、整个 prefs XML 涨到 **402MB**
 * ⇒ `SharedPreferences` 首次解析极慢（卡顿）且依赖 prefs 的脚本全部超时。
 *
 * 本用例把「写入必经 [io.legado.app.help.ai.AiToolNameLimits.sanitize]」写成结构不变量，
 * 防止后续重构把边界去掉。
 */
class AppConfigAiToolNamesLimitTest {

    private fun setterBlock(): String {
        val source = SourceFileProbe.sourceText("help/config/AppConfig.kt")
        val start = source.indexOf("var aiEnabledToolNames")
        assertTrue("未找到 aiEnabledToolNames（口径漂移）", start >= 0)
        val end = source.indexOf("var aiEnabledToolNamesVersion", start)
        assertTrue("未找到 aiEnabledToolNamesVersion 边界", end > start)
        return source.substring(start, end)
    }

    @Test
    fun aiEnabledToolNames_setter_goesThroughLimits() {
        val block = setterBlock()
        assertTrue(
            "写入必须经 AiToolNameLimits.sanitize（否则畸形入参可把 prefs 撑爆）",
            block.contains("AiToolNameLimits.sanitize(value)")
        )
        assertTrue(
            "不得再用无上限的 filter 直写",
            !block.contains("value.filter { it.isNotBlank() }.toMutableSet()")
        )
    }
}