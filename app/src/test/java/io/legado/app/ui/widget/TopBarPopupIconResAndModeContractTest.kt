package io.legado.app.ui.widget

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.7 + §1.2 路径 B（弹层侧）契约测试（JVM 可跑，2026-09-25）。
 *
 * 覆盖两件互不相关但同批交付的事：
 *   ①**§1.2 路径 B**：`ModernActionPopup.Action` 增 drawable 图标槽 `iconRes`，且条目渲染
 *     必须把它交给 `LegadoMiuixChoiceRow(leadingIconRes = …)`——否则「`AppManagementMenuAction.iconRes`
 *     → 溢出弹层」整条链在最后一步丢图标（与路径 A 的 `AppDropdownMenu` 缺口同源）。
 *   ②**§1.7**：`Mode.READ_RECORD` 是**无宿主的死分支**（全仓 `setMode(` 仅 4 类宿主），
 *     按 AD-TB-08 **保留不删 + 加注**，并锁死「不得有新宿主依赖该 Mode」。
 */
class TopBarPopupIconResAndModeContractTest {

    private val popup = "ui/widget/ModernActionPopup.kt"
    private val mainTopBar = "ui/widget/MainTopBarView.kt"

    private fun mainJavaFiles(): List<Pair<String, String>> {
        val root = SourceFileProbe.mainJavaRoot()
        return root.walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .map { it.relativeTo(root).path.replace('\\', '/') to it.readText() }
            .toList()
    }

    @Test
    fun popupActionCarriesDrawableIconSlot() {
        val s = SourceFileProbe.sourceText(popup)
        assertTrue(
            "ModernActionPopup.Action 必须声明 drawable 图标槽（默认 null ⇒ 既有调用点零改动）",
            s.contains("val iconRes: Int? = null")
        )
        assertTrue(
            "必须同时声明 ImageVector 图标槽（管理族溢出条目实测用 ImageVector 源，只补 drawable 显示不出）",
            s.contains("val icon: ImageVector? = null")
        )
        assertTrue("必须保留既有 String 图标槽（三者互不替代）", s.contains("val iconName: String? = null"))
    }

    @Test
    fun popupRowRendersDrawableIconSource() {
        val s = SourceFileProbe.sourceText(popup)
        assertTrue("条目渲染必须透传 drawable 源", s.contains("leadingIconRes = action.iconRes,"))
        assertTrue("条目渲染必须透传 ImageVector 源", s.contains("leadingIcon = action.icon,"))
        assertTrue("条目渲染必须仍透传 String 源", s.contains("leadingIconName = action.iconName,"))
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」误删）",
            SourceFileProbe.rawText(popup).contains("图标双源同链透传")
        )
    }

    @Test
    fun readRecordModeBranchKeptAndAnnotated() {
        val s = SourceFileProbe.sourceText(mainTopBar)
        assertTrue(
            "READ_RECORD 死分支必须保留原取值（不得静默删除改变既有可见性快照）",
            s.contains("mode == Mode.BOOKSHELF || mode == Mode.READ_RECORD || mode == Mode.MY")
        )
        val raw = SourceFileProbe.rawText(mainTopBar)
        assertTrue(
            "死分支必须带「历史遗留 / 禁止新宿主依赖」注释（AD-TB-08）",
            raw.contains("历史遗留死分支") && raw.contains("禁止新宿主依赖该 Mode")
        )
    }

    @Test
    fun noHostDependsOnReadRecordMode() {
        val hits = mainJavaFiles().flatMap { (path, text) ->
            text.lines().filter { it.contains("setMode(") }.map { path to it.trim() }
        }
        assertTrue("基线应有主 Tab 宿主调用 setMode（实测 4 类宿主）", hits.size >= 4)
        val bad = hits.filter { it.second.contains("READ_RECORD") }
        assertTrue("不得有宿主传入 Mode.READ_RECORD（该 Mode 无宿主，见 AD-TB-08）：$bad", bad.isEmpty())
    }
}