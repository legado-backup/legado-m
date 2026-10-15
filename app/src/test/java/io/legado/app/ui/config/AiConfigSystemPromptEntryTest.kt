package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-43：AI「系统提示词」编辑入口接线守护（未接线特性修复）。
 *
 * 缺陷背景：`AiConfigFragment.showSystemPromptDialog()`（能力完整：编辑 + 恢复默认）**早已实现却全仓零调用**
 * —— 同屏所有同类 `show*Dialog` 均有 `onClick = ::showXxxDialog` 入口，唯它没有 ⇒ 用户此前**无任何 UI 路径**
 * 编辑 AI 系统提示词（`AppConfig.aiSystemPrompt` 的 UI 写入方仅存在于该不可达弹窗内）。本批已接线（新增
 * `SettingActionSpec(key = KEY_SYSTEM_PROMPT, …, onClick = ::showSystemPromptDialog)`）。
 *
 * 本类把接线固化：入口消失即红（回归到「有实现无入口」的未接线状态）。
 */
class AiConfigSystemPromptEntryTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `系统提示词编辑入口已接线且弹窗实现仍在`() {
        val src = code("src/main/java/io/legado/app/ui/config/AiConfigFragment.kt")
        assertEquals("必须存在设置行入口（点击打开弹窗）", true, src.contains("onClick = ::showSystemPromptDialog"))
        assertEquals("必须登记入口 key", true, src.contains("key = KEY_SYSTEM_PROMPT"))
        assertEquals("key 常量须指向 aiSystemPrompt", true, src.contains("const val KEY_SYSTEM_PROMPT = \"aiSystemPrompt\""))
        assertEquals("弹窗实现必须保留", true, src.contains("private fun showSystemPromptDialog()"))
        assertEquals("弹窗必须写回 AppConfig 并支持恢复默认", true,
            src.contains("AppConfig.aiSystemPrompt = text") &&
                src.contains("AppConfig.aiSystemPrompt = AppConfig.DEFAULT_AI_SYSTEM_PROMPT"))
        assertEquals("入口标题须用既有字符串", true, src.contains("title = getString(R.string.ai_system_prompt)"))
    }
}
