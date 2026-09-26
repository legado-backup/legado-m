package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #8（2026-09-26）：`activity_theme_manage.xml` 退役（**14 个管理页共用布局**）契约测试。
 *
 * 换装口径：
 *  · **全部 14 个宿主**一律 `composeShell(this)` + `attachComposeContent` 单源，顶栏由
 *    `installGlassTopBar` 运行时注入改为**页内直接渲染** `GlassTopAppBar`；
 *  · 其中 10 页把内容整体迁入 Compose（另有各包自身测试锁定）；本包 4 页是**真消费者**——
 *    在 `onActivityCreated` 内直接配置布局内的节点，并向根 `LinearLayout` 动态 `addView`
 *    （批量栏 / 分组快捷栏 / 预览条）⇒ 内容区由 [ThemeManageShellViews] **单源装配**、
 *    以 `AndroidView` 原样托管（View 内核与插入语义保留）。
 *
 * 本测试锁死六件事（防回归 / 防「静默退化」）：
 *   ①四宿主不得回退到 ViewBinding inflate / 旧顶栏运行时注入；
 *   ②装配单源存在，且**子节点顺序即插入语义**（`addView` 次第不得漂移）；
 *   ③`root` 必须仍是 `LinearLayout(VERTICAL)`（宿主依赖 `root as? LinearLayout` 动态插栏）；
 *   ④`recycler_view` 的 `0dp + weight=1` 与 `tab_bar`/`btn_add` 的尺寸口径逐项复刻；
 *   ⑤共用 XML 已退役（`title_bar` 不再装配，改由页内顶栏承担）；
 *   ⑥`ReadMenuButtonManageActivity` 的**既有缺陷修复**被锁定：原 `initTopBar()` 从未被调用
 *     （顶栏标题与「重置」动作不可达），换装时一并接上页内顶栏。
 */
class ThemeManageShellMigrationTest {

    private val shellRel = "ui/book/read/config/ThemeManageShellViews.kt"
    private val hosts = listOf(
        "ui/book/read/config/AiReadAloudUsageRecordActivity.kt",
        "ui/book/read/config/ParagraphRuleManageActivity.kt",
        "ui/book/read/config/ReadAloudBgmManageActivity.kt",
        "ui/book/read/config/ReadMenuButtonManageActivity.kt",
    )

    private fun src(rel: String): String = SourceFileProbe.sourceText(rel)

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_theme_manage.xml 应已退役（CE-a #8，14 个管理页共用）",
            File(SourceFileProbe.layoutDir(), "activity_theme_manage.xml").exists()
        )
    }

    @Test
    fun everyHostUsesSingleSourceShell() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
            assertTrue("$rel 必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
            assertFalse("$rel 换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
            assertFalse("$rel 换装后不得再引用已退役布局", s.contains("ActivityThemeManageBinding"))
            assertFalse("$rel 不得残留旧顶栏运行时注入", s.contains("installGlassTopBar("))
            assertFalse("$rel 禁止手写 ComposeView 装配", s.contains("ComposeView("))
            assertFalse("$rel 禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
            // 原 `initTopBar()` 死方法必须消失（声明判定，避免被 KDoc 里的「原 dead initTopBar()」字样误伤）
            assertFalse("$rel 原 initTopBar 应已迁入 initComposeContent", s.contains("private fun initTopBar"))
        }
    }

    @Test
    fun topBarRenderedInPageComposition() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 顶栏必须页内渲染（GlassTopAppBar）", s.contains("GlassTopAppBar("))
            assertTrue("$rel 顶栏动作必须走 TopBarActionRow", s.contains("TopBarActionRow(topBarActions())"))
            assertTrue(
                "$rel 原共用布局内容区必须由 AndroidView 原样托管装配单源",
                s.contains("factory = { shell.root }")
            )
            assertTrue(
                "$rel 原 `recycler_view` 的 `0dp + weight=1` 语义必须由 Compose 权重表达",
                s.contains("Modifier.fillMaxWidth().weight(1f)")
            )
        }
    }

    @Test
    fun viewKernelAndInsertAnchorsKept() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 必须持有装配单源实例", s.contains("ThemeManageShellViews(this)"))
            listOf("binding.tabBar", "binding.btnDay", "binding.btnNight", "binding.btnAdd", "binding.tvSummary", "binding.recyclerView")
                .forEach { stale ->
                    assertFalse("$rel 不得残留布局绑定视图访问 `$stale`", s.contains(stale))
                }
            assertTrue("$rel 必须保留运行时动态插栏/锚点语义（shell.*）", s.contains("shell."))
        }
    }

    @Test
    fun shellSingleSourceAssemblesNodesInOriginalOrder() {
        val s = src(shellRel)
        // 顺序即插入语义：以 tv_summary / btn_add 为锚点插入的动态栏落点由其次第决定
        val order = listOf(
            "addView(tabBar)",
            "tabBar.addView(btnDay)",
            "tabBar.addView(btnNight)",
            "addView(tvSummary)",
            "addView(recyclerView)",
            "addView(btnAdd)",
        )
        var last = -1
        order.forEach { marker ->
            val idx = s.indexOf(marker)
            assertTrue("装配单源缺少 `$marker`", idx >= 0)
            assertTrue("子节点顺序即插入语义，`$marker` 位置不得漂移", idx > last)
            last = idx
        }
        // 🔴 真机截图实证的缺陷：`btn_day` / `btn_night`（宽 0dp + weight=1 + 高 match_parent，**横向**等宽写法）
        // 曾被误挂到竖向 `root` ⇒ weight 作用于**纵向**、宽为 0 ⇒ 两段文字不可见 + 把 `tv_summary`/
        // `recycler_view`/`btn_add` 挤成 0（整页只剩一条空 tab 条）。父节点必须是 `tab_bar`。
        assertFalse(
            "btn_day/btn_night 不得挂到竖向 root（weight 会作用于纵向并把其余内容挤成 0）",
            s.contains("addView(btnDay, btnDay.layoutParams)") ||
                s.contains("addView(btnNight, btnNight.layoutParams)")
        )
        assertTrue("root 必须仍是竖向 LinearLayout（宿主依赖 root as? LinearLayout 插栏）", s.contains("orientation = LinearLayout.VERTICAL"))
        assertTrue("tab_bar 必须仍为 42dp 高", s.contains("ViewGroup.LayoutParams.MATCH_PARENT, 42.dpToPx()"))
        assertTrue("btn_add 必须仍为 48dp 高", s.contains("ViewGroup.LayoutParams.MATCH_PARENT, 48.dpToPx()"))
        assertTrue("recycler_view 必须复刻 `0dp + weight=1`", s.contains("ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f"))
        assertTrue("tv_summary 必须复刻默认文案", s.contains("setText(R.string.theme_package_summary_default)"))
        assertTrue("btn_add 必须复刻默认文案", s.contains("setText(R.string.theme_add)"))
        assertTrue("btn_day/btn_night 必须复刻等宽两段", s.contains("0, ViewGroup.LayoutParams.MATCH_PARENT, 1f"))
        assertTrue("recycler_view 必须保留 clipToPadding=false", s.contains("clipToPadding = false"))
    }

    @Test
    fun shellNoLongerOwnsTopBar() {
        val s = src(shellRel)
        assertFalse("顶栏（原 title_bar）不再由装配单源承担", s.contains("title_bar"))
        assertFalse("顶栏（原 MainTopBarView）不再由装配单源承担", s.contains("MainTopBarView"))
    }

    @Test
    fun readMenuButtonTopBarDefectIsFixed() {
        val s = src("ui/book/read/config/ReadMenuButtonManageActivity.kt")
        assertTrue("页面必须真正调用 initComposeContent（原 initTopBar 是死代码）", s.contains("initComposeContent()"))
        assertTrue("标题必须取原 provider 的字符串资源", s.contains("getString(R.string.read_menu_button_manage)"))
        assertTrue("「重置」动作必须可达", s.contains("R.drawable.ic_restore"))
        assertTrue("「重置」实现不得丢", s.contains("private fun resetLayout()"))
    }

    @Test
    fun consumerFeaturesArePreserved() {
        // 各页在共用布局上叠的特性不得因换装丢失（逐项结构化标记）
        val aiUsage = src("ui/book/read/config/AiReadAloudUsageRecordActivity.kt")
        listOf(
            "private fun updateSummary()",
            "private fun renderBatchBar()",
            "shell.tvSummary.parent as? LinearLayout",
            "container.indexOfChild(shell.btnAdd)",
        ).forEach { assertTrue("消耗记录页特性丢失：$it", aiUsage.contains(it)) }

        val paragraph = src("ui/book/read/config/ParagraphRuleManageActivity.kt")
        listOf(
            "private fun load()",
            "private fun importRulesFromUrl(",
            "shell.btnAdd.isEnabled = false",
            "ItemTouchHelper(ItemTouchCallback(",
        ).forEach { assertTrue("段落规则管理页特性丢失：$it", paragraph.contains(it)) }

        val bgm = src("ui/book/read/config/ReadAloudBgmManageActivity.kt")
        listOf(
            "private fun initBatchActionBar(",
            "private fun ensureGroupActionBar(",
            "private fun updateEmptyAction()",
            // 装配单源 `root` 已是 `LinearLayout` ⇒ 宿主直接取用（不再需要运行时向下转型）
            "val parent = shell.root",
            "parent.indexOfChild(shell.tvSummary)",
        ).forEach { assertTrue("智能音频页特性丢失：$it", bgm.contains(it)) }

        val menuButton = src("ui/book/read/config/ReadMenuButtonManageActivity.kt")
        listOf(
            "private fun ensurePreviewBar(): LinearLayout?",
            "parent.indexOfChild(shell.btnAdd)",
            "private fun refreshPreview()",
        ).forEach { assertTrue("阅读菜单按键页特性丢失：$it", menuButton.contains(it)) }
    }

    /** 顶栏动作清单不得退化成空（`TopBarActionRow(topBarActions())` 必须有实际内容）。 */
    @Test
    fun topBarActionsAreNotEmpty() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 顶栏动作必须至少一项（MenuAction）", s.contains("MenuAction("))
            assertEquals(
                "$rel 顶栏动作必须只有一处 provider（防止重复定义）",
                1,
                Regex("private fun topBarActions\\(\\)").findAll(s).count()
            )
        }
    }
}
