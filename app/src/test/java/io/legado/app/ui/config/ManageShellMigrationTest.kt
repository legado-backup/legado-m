package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #8（2026-09-26）：`activity_theme_manage.xml` 退役——**本包 9 个宿主**的换装不变量。
 *
 * 背景：该布局被 **14 个管理页共用**（本包 9 + `ui/main/explore/DiscoverySuiteManageActivity` +
 * `ui/book/read/config` 4 页）。共用布局的退役必须「先换装、后删 XML」⇒ 任一宿主漏改即无法编译；
 * 且换装把顶栏从「`installGlassTopBar` 运行时在 root 首插 ComposeView」改为「页内直接渲染」，
 * 这条路径一旦回流，XML 退役后的页面就会顶栏丢失 ⇒ 必须机检锁定。
 *
 * 本包 9 页的内容区已整体迁入 Compose（不再是原布局的消费者），故只锁三条：
 *   ①一律 `composeShell(this)` + `attachComposeContent` 单源（不得回退 inflate / 手拼 ComposeView）；
 *   ②顶栏必须页内承担（`GlassTopAppBar`，或经 `*Screen` 的 `AppManagementScaffold` 自带）；
 *   ③不得再有任何指向已退役共用布局的引用。
 *
 * 全仓「`installGlassTopBar` 调用点归零」由 `ui/widget/components/InstallGlassTopBarRetiredTest` 锁定
 *（该不变量属组件自身包，不在此重复）。
 */
class ManageShellMigrationTest {

    private val hosts = listOf(
        "ui/config/AdvancedTitleManageActivity.kt",
        "ui/config/AppearanceKitActivity.kt",
        "ui/config/AppearanceKitEditActivity.kt",
        "ui/config/BookInfoManageActivity.kt",
        "ui/config/BubbleManageActivity.kt",
        "ui/config/NavigationBarManageActivity.kt",
        "ui/config/ShareNoteTemplateManageActivity.kt",
        "ui/config/ThemeManageActivity.kt",
        "ui/config/TopBarManageActivity.kt",
    )

    /**
     * 例外汇总（显式登记，非放宽判据）：宿主文件内还定义了**与该页骨架无关**的 Compose 弹框
     * （独立窗口，其 `onCreateView` 必须自建 `ComposeView`）。与
     * `ComposeShellSingleSourceTest.sameFileComposeDialogExceptions` 同一条目。
     */
    private val sameFileComposeDialogHosts = setOf("ui/config/NavigationBarManageActivity.kt")

    private fun src(rel: String): String = SourceFileProbe.sourceText(rel)

    @Test
    fun everyHostUsesSingleSourceShell() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
            assertTrue("$rel 必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
            assertFalse("$rel 换装后不得再走 viewBinding 委托", s.contains("by viewBinding("))
            assertFalse("$rel 换装后不得再引用已退役布局", s.contains("ActivityThemeManageBinding"))
            assertFalse("$rel 不得残留旧顶栏运行时注入", s.contains("installGlassTopBar("))
            if (rel !in sameFileComposeDialogHosts) {
                assertFalse("$rel 禁止手写 ComposeView 装配", s.contains("ComposeView("))
                assertFalse("$rel 禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
            }
        }
    }

    @Test
    fun topBarIsOwnedInPage() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue(
                "$rel 顶栏必须页内承担（GlassTopAppBar 或 *Screen 的 AppManagementScaffold）",
                s.contains("GlassTopAppBar(") || s.contains("onBack = { finish() }")
            )
        }
    }

    /** 共用 XML 已退役：本包宿主不得再有任何指向它的布局引用（含 `R.layout.*` 形式）。 */
    @Test
    fun sharedLayoutIsRetired() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertFalse("$rel 不得引用已退役共用布局", s.contains("activity_theme_manage"))
        }
    }
}
