package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R15「外接手柄翻页预设」单测（覆盖 spec R15-1 / R15-2 / R15-3）。
 *
 * 口径：
 * - R15-1 选预设即把**上/下页键码**填入对应值（一键同时填两栏）；
 * - R15-2 应用预设后手动修改以手动值为准 ⇒ 实现上必须「只在显式选择时写入」，无自动重套用；
 * - R15-3 预设与既有自定义键码冲突时提示，不静默覆盖。
 */
class GamepadKeyPresetsTest {

    // ---- R15-1：预设填入正确 ----
    @Test
    fun r15_1_presetsFillBothFieldsWithExpectedKeyCodes() {
        val shoulder = GamepadKeyPresets.byId("shoulder")!!
        assertEquals("102", GamepadKeyPresets.toKeyString(shoulder.prevKeys))
        assertEquals("103", GamepadKeyPresets.toKeyString(shoulder.nextKeys))

        val trigger = GamepadKeyPresets.byId("trigger")!!
        assertEquals("104", GamepadKeyPresets.toKeyString(trigger.prevKeys))
        assertEquals("105", GamepadKeyPresets.toKeyString(trigger.nextKeys))

        val dpad = GamepadKeyPresets.byId("dpad")!!
        assertEquals("19", GamepadKeyPresets.toKeyString(dpad.prevKeys))
        assertEquals("20", GamepadKeyPresets.toKeyString(dpad.nextKeys))
    }

    /** 多手柄家族（产品超越点：不止 LB/RB 一套）且 id 唯一。 */
    @Test
    fun r15_1b_multipleGamepadFamiliesWithUniqueIds() {
        assertTrue("预设家族应 ≥3 套，实际 ${GamepadKeyPresets.all.size}", GamepadKeyPresets.all.size >= 3)
        val ids = GamepadKeyPresets.all.map { it.id }
        assertEquals("预设 id 必须唯一", ids.size, ids.toSet().size)
        GamepadKeyPresets.all.forEach {
            assertTrue("预设 ${it.id} 上/下页键码不得重叠", GamepadKeyPresets.isSelfConsistent(it))
        }
    }

    /** 逗号串解析：与录入路径同格式（`a,b`），非法项忽略。 */
    @Test
    fun r15_1c_keyStringRoundTrip() {
        assertEquals(emptyList<Int>(), GamepadKeyPresets.parseKeyString(""))
        assertEquals(listOf(102), GamepadKeyPresets.parseKeyString("102"))
        assertEquals(listOf(102, 103), GamepadKeyPresets.parseKeyString("102,103"))
        assertEquals(listOf(102, 103), GamepadKeyPresets.parseKeyString(" 102 , 103 "))
        assertEquals(listOf(102), GamepadKeyPresets.parseKeyString("102,x,"))
    }

    // ---- R15-3：冲突（覆盖既有自定义）判定 ----
    @Test
    fun r15_3_conflictDetectedOnlyWhenCustomValueWouldBeReplaced() {
        val shoulder = GamepadKeyPresets.byId("shoulder")!!
        assertFalse(
            "两栏皆空 ⇒ 无冲突（首次套用）",
            GamepadKeyPresets.overwritesCustomKey(shoulder, "", "")
        )
        assertFalse(
            "当前值恰为预设值 ⇒ 不算冲突（幂等套用）",
            GamepadKeyPresets.overwritesCustomKey(shoulder, "102", "103")
        )
        assertTrue(
            "上页已有其它自定义键码 ⇒ 冲突",
            GamepadKeyPresets.overwritesCustomKey(shoulder, "999", "103")
        )
        assertTrue(
            "下页已有其它自定义键码 ⇒ 冲突",
            GamepadKeyPresets.overwritesCustomKey(shoulder, "102", "999")
        )
    }

    /**
     * R15-2「手动编辑不被覆盖」的接线不变量：
     * 预设写入只能出现在 [PageKeyDialog.showGamepadPreset] 的显式选择回调中。
     */
    @Test
    fun r15_2_presetWriteOnlyHappensOnExplicitSelection() {
        val rel = "src/main/java/io/legado/app/ui/book/read/config/PageKeyDialog.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        val code = file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")

        assertTrue("必须已接线手柄预设入口", code.contains("onShowGamepadPreset"))
        assertTrue(
            "预设值必须在显式选择回调里写入两栏",
            Regex("prevKeys = GamepadKeyPresets\\.toKeyString").containsMatchIn(code) &&
                Regex("nextKeys = GamepadKeyPresets\\.toKeyString").containsMatchIn(code)
        )
        assertFalse(
            "不得存在自动重套用（如 LaunchedEffect / SideEffect 内调用预设）",
            code.contains("LaunchedEffect") || code.contains("SideEffect")
        )
        assertEquals(
            "预设写入点必须只有一处（apply 内两条赋值），实际 ${
                Regex("GamepadKeyPresets\\.toKeyString\\(").findAll(code).count()
            }",
            2,
            Regex("GamepadKeyPresets\\.toKeyString\\(").findAll(code).count()
        )
    }
}