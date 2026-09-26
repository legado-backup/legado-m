package io.legado.app.ui.widget.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2 路径 B（管理族侧）契约测试（JVM 可跑，2026-09-25）。
 *
 * 缺陷链（实测）：`MenuAction.iconRes` →[转换]→ `AppManagementMenuAction`（原先**无 icon 字段**）
 * →[映射]→ `ModernActionPopup.Action` →[渲染]→ 溢出弹层条目 ⇒ 中间两跳都丢图标，
 * 最终溢出菜单只能渲染纯文字（一级路径 `AppManagementScaffold` 一直是对的）。
 *
 * 本测试锁死：①模型有 icon 槽 ②两个映射点都透传 ③**全仓所有** `MenuAction → AppManagementMenuAction`
 * 转换点都透传（含清单断言，防「新增漏点」）④一级路径未被误改（回归对照基线）。
 */
class ManagementOverflowIconResPassthroughTest {

    private val components = "ui/widget/compose/AppSettingComponents.kt"
    private val packageComponents = "ui/widget/compose/AppPackageManageComponents.kt"
    private val scaffold = "ui/widget/compose/AppManagementScaffold.kt"

    /**
     * `MenuAction → AppManagementMenuAction` 转换点全仓实测量（2026-09-26 复核：新增
     * `AutoTaskScreen` —— 行收敛第二批把该页自绘顶栏/溢出菜单换成 `AppManagementScaffold`，
     * 因而新出现一处转换点，已按本测试要求同步核对图标双源透传）。
     */
    private val transformSites = listOf(
        "ui/dict/rule/DictRuleScreen.kt",
        "ui/book/toc/rule/TxtTocRuleScreen.kt",
        "ui/book/storage/StorageManageScreen.kt",
        "ui/highlight/HighlightRuleScreen.kt",
        "ui/download/DownloadManageScreen.kt",
        "ui/autoTask/AutoTaskScreen.kt",
    )

    private fun mainJavaFiles(): List<Pair<String, String>> {
        val root = SourceFileProbe.mainJavaRoot()
        return root.walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .map { it.relativeTo(root).path.replace('\\', '/') to it.readText() }
            .toList()
    }

    @Test
    fun menuActionModelCarriesIconSlot() {
        val s = SourceFileProbe.sourceText(components)
        assertTrue(
            "AppManagementMenuAction 必须声明 drawable 图标槽（默认 null ⇒ 既有调用点零改动）",
            s.contains("val iconRes: Int? = null")
        )
        assertTrue(
            "AppManagementMenuAction 必须声明 ImageVector 图标槽（与契约 MenuAction 双源一一对应）",
            s.contains("val icon: ImageVector? = null")
        )
    }

    @Test
    fun bothMappingSitesPassIconRes() {
        val a = SourceFileProbe.sourceText(components)
        val b = SourceFileProbe.sourceText(packageComponents)
        assertTrue("AppManagementMoreActionButton 映射必须透传 drawable 源", a.contains("iconRes = action.iconRes,"))
        assertTrue("AppManagementMoreActionButton 映射必须透传 ImageVector 源", a.contains("icon = action.icon,"))
        assertTrue("AppPackageManageMoreButton 映射必须透传 drawable 源", b.contains("iconRes = action.iconRes,"))
        assertTrue("AppPackageManageMoreButton 映射必须透传 ImageVector 源", b.contains("icon = action.icon,"))
    }

    @Test
    fun allTransformSitesPassIconRes() {
        // walk 的相对路径以 `app/src/main/java` 为根 ⇒ 前缀为 `io/legado/app/`（SourceFileProbe 则以该包为根）
        val hits = mainJavaFiles()
            .filter { it.second.contains("text = menuAction.title,") }
            .map { it.first }
            .sorted()
        assertEquals(
            "转换点清单变化（新增/删除）⇒ 必须同步核对图标透传（实测清单）",
            transformSites.map { "io/legado/app/$it" }.sorted(),
            hits
        )
        transformSites.forEach { rel ->
            val s = SourceFileProbe.sourceText(rel)
            assertTrue("$rel 的转换点必须透传 drawable 源", s.contains("iconRes = menuAction.iconRes,"))
            assertTrue("$rel 的转换点必须透传 ImageVector 源", s.contains("icon = menuAction.icon,"))
        }
    }

    @Test
    fun scaffoldActionAssetsComeFromContract() {
        // 顶栏包 §3.2（2026-09-26）：管理族动作槽的兜底图标 / 搜索位 / 选择态关闭位原写死
        // `R.drawable.ic_*` ⇒ 一并收口到 `TopBarConfig.Icons`（同口径机检门禁 20 阻断回流）。
        val s = SourceFileProbe.sourceText(scaffold)
        assertTrue("兜底图标须取契约值", s.contains("TopBarConfig.Icons.more"))
        assertTrue("搜索位图标须取契约值", s.contains("TopBarConfig.Icons.search"))
        assertTrue("选择态关闭位须取契约值", s.contains("TopBarConfig.Icons.close"))
        assertFalse(
            "不得再写死图标资产 R.drawable.ic_*",
            Regex("R\\.drawable\\.ic_").containsMatchIn(s)
        )
    }

    @Test
    fun firstLevelIconPathUntouched() {
        // 回归对照：一级路径（icon 优先 / fallback iconRes）本来就正确，本批不得改它
        val s = SourceFileProbe.sourceText(scaffold)
        assertTrue(
            "一级路径必须仍保留「iconRes 为空时兜底 more 图标」口径；顶栏包 §3.2 起兜底值改取契约",
            s.contains("action.iconRes ?: TopBarConfig.Icons.more")
        )
    }
}