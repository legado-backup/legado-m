package io.legado.app.ui.autoTask

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 自动任务编辑页「死入口」退役护栏（2026-10-17）。
 *
 * 背景：顶栏含一个「调试」菜单项，点击只 toast `auto_task_debug_pending`（文案＝「调试功能待实现」）
 * ⇒ 用户可点的**死入口**（placeholder control）。经核实 `AutoTaskRule` 只有 script/url 语义、
 * 无搜索/发现规则 ⇒ 复用 `BookSourceDebugActivity` 无从调试，故按「移除死入口 + 退役占位字符串」处置。
 * 「登录」入口保留，其接线正确性由 `ui/login/SourceLoginAutoTaskBranchTest` 的行为断言覆盖。
 */
class AutoTaskEditMenuWiringTest {

    private val act = SourceFileProbe.sourceText("ui/autoTask/AutoTaskEditActivity.kt")

    @Test
    fun `调试死入口与其占用字符串均已退役`() {
        assertEquals("不得再有占位调试入口", false, act.contains("R.string.auto_task_debug_pending"))
        assertEquals("不得再引用 BugReport 图标（该入口唯一用处）", false, act.contains("Icons.Default.BugReport"))
        assertEquals(
            "不得再导入 BugReport（否则留下无引用 import）",
            false,
            act.contains("import androidx.compose.material.icons.filled.BugReport")
        )
        val values = SourceFileProbe.resValuesText("strings.xml")
        assertEquals(
            "占位字符串须退役（否则零引用回归）",
            false,
            values.contains("name=\"auto_task_debug_pending\"")
        )
    }

    @Test
    fun `登录入口保留且旧 TODO 已消除`() {
        assertEquals(
            "登录入口必须在位",
            true,
            act.contains("MenuAction(Icons.Default.Login, getString(R.string.login)) { openLogin() }")
        )
        assertEquals("须以 autoTask 类型进入登录页", true, act.contains("putExtra(\"type\", \"autoTask\")"))
        assertEquals(
            "旧 TODO（未支持 autoTask 类型）不得残留",
            false,
            act.contains("TODO: SourceLoginViewModel 当前的 initData 仅支持")
        )
    }
}
