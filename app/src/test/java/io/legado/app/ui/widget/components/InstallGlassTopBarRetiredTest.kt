package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #8（2026-09-26）：「共用布局页」全部迁完 ⇒ `installGlassTopBar` 运行时注入通道**调用点归零**。
 *
 * 背景：该函数是「运行时把 ComposeView 首插到 root、再摘掉 XML 的 `MainTopBarView@title_bar` 锚点」
 * 的过渡通道，服务对象是 `activity_theme_manage.xml` 的 14 个共用页。这些页现已全部改为
 * **页内直接渲染** `GlassTopAppBar`，共用 XML 也随之下线 ⇒ 任何新增调用都意味着「有页面又回到
 * 依赖 XML 锚点的老路」，与 XML 已退役的现状矛盾（页面会顶栏丢失）。
 *
 * 定义本身保留（见 `AppMenuSheet.kt` KDoc：待「顶栏包 §1/§2」决策是否删除），本测试只锁：
 *   ①全仓 `main/java` 无任何 `installGlassTopBar(` 调用点；
 *   ②定义仍在且仍为扩展函数形态（避免「顺手删掉定义」时无人复核）。
 */
class InstallGlassTopBarRetiredTest {

    private fun mainJavaRoot() = SourceFileProbe.mainJavaRoot()

    @Test
    fun noCallSitesRemainInMainSource() {
        val offenders = mainJavaRoot().walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .filter { file ->
                SourceFileProbe.stripComments(file.readText())
                    .lineSequence()
                    .any { it.trimStart().startsWith("installGlassTopBar(") }
            }
            .map { it.relativeTo(mainJavaRoot()).path.replace('\\', '/') }
            .sorted()
            .toList()
        assertEquals(
            "共用布局页全部改为页内渲染 ⇒ 不得再有 installGlassTopBar 调用点：$offenders",
            emptyList<String>(),
            offenders
        )
    }

    @Test
    fun declarationKeptUntilTopBarBatchDecides() {
        val def = SourceFileProbe.sourceText("ui/widget/components/AppMenuSheet.kt")
        assertTrue(
            "定义应暂留（待「顶栏包 §1/§2」决策），删除须走复核",
            def.contains("fun ComponentActivity.installGlassTopBar(")
        )
        assertTrue(
            "KDoc 必须留痕「已无调用点 / 禁止新增调用」",
            SourceFileProbe.rawText("ui/widget/components/AppMenuSheet.kt").contains("已无调用点")
        )
    }
}