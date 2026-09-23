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
}