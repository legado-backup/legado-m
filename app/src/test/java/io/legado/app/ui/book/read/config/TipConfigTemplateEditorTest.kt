package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R12「自定义模板」配置入口不变量。
 *
 * 需求（spec R12-1）：用户必须是**可视化插入占位符**（点选变量），而不是手写模板串；
 * 且多个槽位可同时自定义（各自独立模板），去重清除逻辑不得把 `custom` 当唯一槽位语义处理。
 */
class TipConfigTemplateEditorTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 选为「自定义模板」的槽位必须出现编辑入口（否则用户选了自定义却无从编辑）。 */
    @Test
    fun customSlotsExposeEditEntry() {
        val tip = code("ui/book/read/config/TipConfigDialog.kt")
        assertTrue(
            "必须按槽位列出可编辑项（多个槽位可同时自定义）",
            tip.contains("value == ReadTipConfig.custom")
        )
        assertTrue("必须有编辑入口提示", tip.contains("R.string.tip_template_edit_hint"))
        assertTrue(
            "点按必须以「槽位名 + 当前模板」打开编辑器并回写该槽位",
            tip.contains("onShowTemplateEditor(slotLabel(slot), template)") &&
                tip.contains("ReadTipConfig.setSlotTemplate(slot, newTemplate)")
        )
        assertTrue(
            "保存后必须触发阅读页刷新",
            tip.contains("ReadTipConfig.setSlotTemplate(slot, newTemplate)") &&
                tip.contains("postEvent(EventBus.UP_CONFIG")
        )
    }

    /** `custom` 非唯一槽位语义 ⇒ 去重清除必须跳过它（否则第二个自定义槽位会把第一个清成 none）。 */
    @Test
    fun clearRepeat_skipsCustomSentinel() {
        val tip = code("ui/book/read/config/TipConfigDialog.kt")
        assertTrue(
            "clearRepeat 必须对 custom 提前返回",
            tip.contains("if (value == ReadTipConfig.custom) return")
        )
    }

    /** 宿主（版面设置弹窗）必须接线到带「可视化插入占位符」的专用编辑器弹窗。 */
    @Test
    fun hostWiresTemplateEditorDialog() {
        val host = code("ui/book/read/config/PaddingConfigDialog.kt")
        assertTrue(host.contains("onShowTemplateEditor = ::showTemplateEditor"))
        assertTrue(
            "必须用专用模板编辑器（支持点选插入 + 预览），不得退化成通用文本输入框",
            host.contains("showComposeTipTemplateDialog(")
        )
        assertTrue(
            "编辑器必须透传到页眉页脚段内容体",
            host.contains("onShowTemplateEditor = onShowTemplateEditor")
        )
    }
}