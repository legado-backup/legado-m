package io.legado.app.help.config

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R12「页眉页脚模板渲染」核心单测。
 *
 * 覆盖 spec R12-3（**未知占位符原样保留**，不得渲染为空）与 R12-1 的渲染语义
 * （已知占位符按实际值渲染，两种写法 `${x}` / `{{x}}` 均支持 —— 复用全项目唯一占位符引擎）。
 */
class ReadTipTemplateTest {

    private val values = mapOf(
        "chapterTitle" to "第一章 起风了",
        "bookName" to "样本集",
        "time" to "09:30",
        "page" to "12",
        "totalProgress" to "3.5%"
    )

    // ---- R12-1：已知变量按实际值渲染 ----
    @Test
    fun knownVariables_areReplacedInBothSyntaxes() {
        assertEquals(
            "第一章 起风了",
            ReadTipTemplate.render("\${chapterTitle}", values)
        )
        assertEquals(
            "第一章 起风了",
            ReadTipTemplate.render("{{chapterTitle}}", values)
        )
        assertEquals(
            "样本集 · 12 / 3.5%",
            ReadTipTemplate.render("\${bookName} · \${page} / \${totalProgress}", values)
        )
    }

    // ---- R12-3：未知占位符原样保留（不得渲染为空）----
    @Test
    fun unknownPlaceholder_isKeptVerbatim() {
        assertEquals(
            "未知段原样保留",
            "未知段原样保留",
            ReadTipTemplate.render("未知段原样保留", values)
        )
        assertEquals(
            "12 页，未知：\${notAVariable}",
            ReadTipTemplate.render("\${page} 页，未知：\${notAVariable}", values)
        )
        assertEquals(
            "12 页，未知：{{notAVariable}}",
            ReadTipTemplate.render("\${page} 页，未知：{{notAVariable}}", values)
        )
    }

    /** 缺失变量（本轮无值）⇒ 该占位符同样原样保留，而不是被替换成空串。 */
    @Test
    fun missingValue_keepsPlaceholder() {
        assertEquals(
            "\${author}",
            ReadTipTemplate.render("\${author}", values)
        )
    }

    @Test
    fun emptyTemplate_returnsEmpty() {
        assertEquals("", ReadTipTemplate.render("", values))
    }

    /** 电量类变量判定（渲染侧据此走电量视图分支）。 */
    @Test
    fun batteryVariableDetection() {
        assertTrue(ReadTipTemplate.usesBatteryVariable("\${battery}"))
        assertTrue(ReadTipTemplate.usesBatteryVariable("{{batteryPercentage}}"))
        assertFalse(ReadTipTemplate.usesBatteryVariable("\${page}"))
        assertFalse(ReadTipTemplate.usesBatteryVariable("battery"))
    }

    /** 变量白名单：必须覆盖传统枚举可表达的语义（否则「自定义」等于能力倒退）。 */
    @Test
    fun variableWhitelist_coversLegacyEnumSemantics() {
        listOf(
            "chapterTitle", "bookName", "time", "battery",
            "batteryPercentage", "page", "totalProgress"
        ).forEach { name ->
            assertTrue("变量白名单缺少 $name", ReadTipTemplate.variables.contains(name))
        }
    }

    // ---- R12 变量值构造：battery 取裸数值（供电量图标定位），batteryPercentage 带 % ----
    @Test
    fun values_batteryIsBareNumber_percentageHasSign() {
        val map = ReadTipTemplate.values(
            chapterTitle = "标题", bookName = "书名", author = "作者", time = "09:30",
            battery = 85, page = "3/20", totalProgress = "12.5%", totalProgress1 = "3/120"
        )
        assertEquals("85", map["battery"])
        assertEquals("85%", map["batteryPercentage"])
        assertEquals(ReadTipTemplate.variables.toSet(), map.keys)
    }

    /** 预览值必须覆盖全部变量（否则配置页点选后预览无效，等于「可视化插入」缺一半）。 */
    @Test
    fun previewValues_coverAllVariables() {
        val preview = ReadTipTemplate.previewValues()
        ReadTipTemplate.variables.forEach { name ->
            val rendered = ReadTipTemplate.render(ReadTipTemplate.placeholderToken(name), preview)
            assertFalse("预览值缺少 $name（占位符未被替换）", rendered.contains("\${$name}"))
        }
    }

    // ---- 电量图标分支：仅末尾电量占位符可走图标（BatteryView 按文本尾部数字画框）----
    @Test
    fun batteryIconTrailing_onlyWhenBatteryIsLast() {
        assertTrue(ReadTipTemplate.batteryIconTrailing("\${battery}"))
        assertTrue(ReadTipTemplate.batteryIconTrailing("{{battery}}"))
        assertTrue("尾部空白不影响判定", ReadTipTemplate.batteryIconTrailing("\${time}  \${battery}  "))
        assertFalse("电量在中间 ⇒ 纯文本（避免电量框画错位置）", ReadTipTemplate.batteryIconTrailing("\${battery}%"))
        assertFalse(ReadTipTemplate.batteryIconTrailing("\${batteryPercentage}"))
        assertFalse(ReadTipTemplate.batteryIconTrailing("\${page}"))
        assertFalse(ReadTipTemplate.batteryIconTrailing(""))
    }

    // ---- 可视化插入：光标处插入 / 替换选区 / 越界与反向选区归一化 ----
    @Test
    fun insertPlaceholder_atCursor() {
        val (text, cursor) = ReadTipTemplate.insertPlaceholder("ab", 1, 1, "page")
        assertEquals("a\${page}b", text)
        assertEquals("a\${page}".length, cursor)
    }

    @Test
    fun insertPlaceholder_replacesSelection() {
        val (text, cursor) = ReadTipTemplate.insertPlaceholder("abXYZcd", 2, 5, "time")
        assertEquals("ab\${time}cd", text)
        assertEquals("ab\${time}".length, cursor)
    }

    @Test
    fun insertPlaceholder_clampsOutOfRangeAndReversedSelection() {
        // 超长光标 ⇒ 截断到文本末尾
        assertEquals(
            "ab\${page}",
            ReadTipTemplate.insertPlaceholder("ab", 99, 99, "page").first
        )
        // 负下标 ⇒ 截断到文本开头
        assertEquals(
            "\${page}ab",
            ReadTipTemplate.insertPlaceholder("ab", -5, -5, "page").first
        )
        // 反向选区 ⇒ 归一化为 [0, 2) 整段替换
        assertEquals(
            "\${page}",
            ReadTipTemplate.insertPlaceholder("ab", 99, 0, "page").first
        )
    }

    /** 插入后再渲染必须能替换成实际值（插入文本 ↔ 渲染引擎契约一致）。 */
    @Test
    fun insertedPlaceholder_isRenderable() {
        val (text, _) = ReadTipTemplate.insertPlaceholder("电量：", 3, 3, "batteryPercentage")
        assertEquals("电量：85%", ReadTipTemplate.render(text, ReadTipTemplate.previewValues()))
    }
}