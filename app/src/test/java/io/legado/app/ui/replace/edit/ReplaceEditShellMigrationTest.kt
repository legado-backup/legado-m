package io.legado.app.ui.replace.edit

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 7 页（`activity_replace_edit`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（竖向 LinearLayout `root_view`）+ 4 个区」：
 *   `compose_top_bar`（已 Compose）/ `NoChildScrollNestedScrollView` + `ll_content`
 *   （6 组 `TextInputLayout`+`ThemeEditText` 字段 + 2 个勾选行 + 1 个帮助图标 +
 *    **2 个夹在字段中间的 ComposeView 槽**：F64 高级组头 / F69 样本试运行）/ `compose_bottom_bar`（已 Compose）。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，**字段区整体以 `AndroidView` 原样托管**
 * （滚动/焦点语义依赖 `NoChildScrollNestedScrollView` 对 `requestChildFocus` 的特化，不可用 Compose 滚动替代）。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再走 viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_replace_edit.xml` 不存在）
 *   ③字段区 View 内核**以 AndroidView 原样托管**，且 `NoChildScrollNestedScrollView` 未被换成普通滚动容器
 *   ④`ComposeView` 只允许出现在**唯一的槽位工厂** `composeSlot`（本页是换装页里的合法例外，须显式锁定）
 *   ⑤**CB-1 ⑤ insets 链路仍在**（锚点为合成壳 `root`，监听体只更新键盘工具初始内边距）
 *   ⑥宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑦行为不变量：6 组字段 + 2 勾选行 + 帮助图标 + 渐进披露可见性 + 表单读写 + 校验链路
 */
class ReplaceEditShellMigrationTest {

    private val page = "ui/replace/edit/ReplaceEditActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityReplaceEditBinding"))
        assertTrue(
            "宿主必须显式改绑 ViewBinding 泛型参数（否则编译期类型不匹配）",
            s.contains("VMBaseActivity<ViewBinding, ReplaceEditViewModel>()")
        )
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_replace_edit.xml")
        assertFalse("activity_replace_edit.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun fieldKernelHostedViaAndroidViewWithFocusSemanticsPreserved() {
        val s = src()
        assertTrue(
            "字段区必须以 AndroidView 托管",
            s.contains("AndroidView(") && s.contains("factory = { contentScrollView }")
        )
        assertTrue(
            "滚动容器必须仍是 NoChildScrollNestedScrollView（其 requestChildFocus 特化是键盘联动前提）",
            s.contains("NoChildScrollNestedScrollView(this)") &&
                s.contains("import io.legado.app.ui.widget.NoChildScrollNestedScrollView")
        )
        assertTrue(
            "字段必须成对重建为 TextInputLayout + ThemeEditText（XML 同构）",
            s.contains("TextInputLayout(this, null)") && s.contains("ThemeEditText(this)")
        )
        assertTrue(
            "勾选控件必须仍是 ThemeCheckBox（accent tint 语义不丢）",
            s.contains("ThemeCheckBox(this)")
        )
        assertTrue(
            "帮助图标必须保持 24dp + ic_help + primaryText tint（对齐原 app:tint）",
            s.contains("R.drawable.ic_help") && s.contains("AppCompatResources.getColorStateList")
        )
    }

    @Test
    fun composeViewOnlyInSanctionedSlotFactory() {
        val s = src()
        // 本页是唯一保留 ComposeView 程序化创建的换装页：两个槽位夹在 View 字段之间（位置即分组语义）
        assertTrue(
            "必须有且仅有 composeSlot 作为 ComposeView 创建点",
            s.contains("private fun composeSlot(content: @Composable () -> Unit): ComposeView")
        )
        val occurrences = Regex("ComposeView\\(").findAll(s).count()
        assertTrue(
            "ComposeView 构造点应被收敛到 composeSlot 单点（实际 $occurrences 处，仅允许返回类型声明 1 处 + 构造 1 处）",
            occurrences <= 2
        )
        assertTrue(
            "两个槽位必须固定在字段栈中（高级组头在「替换范围」之前、样本区在「超时」之后）",
            s.contains("content.addView(advancedHeaderCompose)") &&
                s.contains("content.addView(sampleSectionCompose)")
        )
        assertTrue(
            "字段栈顺序不得调整（含 4 个字段 + 两个勾选行 + 两个槽位）",
            s.contains("content.addView(tilName)") && s.contains("content.addView(tilGroup)") &&
                s.contains("content.addView(tilReplaceRule)") && s.contains("content.addView(tilReplaceTo)")
        )
    }

    @Test
    fun insetsAnchorChainPreserved() {
        val s = src()
        assertTrue("insets 监听必须仍在", s.contains("setOnApplyWindowInsetsListenerCompat"))
        assertTrue(
            "insets 锚点须为合成壳 root（组合内 AndroidView 不保证收到派发）",
            s.contains("binding.root.setOnApplyWindowInsetsListenerCompat")
        )
        assertTrue(
            "键盘工具初始内边距口径不得改动（原监听体唯一副作用）",
            s.contains("softKeyboardTool.initialPadding = windowInsets.imeHeight")
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun field(",
            "private fun createHelpIcon(",
            "private fun composeSlot(",
            "private fun createContentScroll(",
            "private fun applyAdvancedVisibility(",
            "private fun runSample(",
            "private fun buildMenuActions(",
            "private fun validateTimeout(",
            "private fun onFullEditClicked(",
            "private fun initView(",
            "private fun upReplaceView(",
            "private fun getReplaceRule(",
            "override fun onDestroy(",
            "override fun helpActions(",
            "override fun onHelpActionSelect(",
            "override fun sendText(",
            "override fun onUndoClicked(",
            "override fun onRedoClicked(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun behaviorInvariantsKept() {
        val s = src()
        // 顶栏/底部栏内容仍在（原两处 setContent 的内容搬入页内）
        assertTrue("顶栏标题必须保留", s.contains("R.string.replace_rule_edit"))
        assertTrue("顶栏必须仍有一级「代码」图标", s.contains("Icons.Filled.Code"))
        assertTrue("顶栏必须仍有一级「保存」图标", s.contains("Icons.Filled.Save"))
        assertTrue("底部栏必须仍有取消/保存两键", s.contains("R.string.cancel") && s.contains("R.string.action_save"))
        // F64 渐进披露：三个高级字段的可见性仍由 applyAdvancedVisibility 统一落
        assertTrue("高级组可见性必须仍在同一处落地", s.contains("tilScope.visibility = visibility"))
        assertTrue("高级组初值仍为收起（advancedExpanded 默认 false）", s.contains("advancedExpanded by mutableStateOf(false)"))
        // F69 样本区状态四件套
        listOf("sampleExpanded", "sampleInput", "sampleResult", "sampleRunning").forEach { name ->
            assertTrue("F69 样本区状态不得丢：缺少 `$name`", s.contains("private var $name by mutableStateOf"))
        }
        // 表单读写链路（保存/回填）
        assertTrue("保存必须仍读摘要", s.contains("replaceRule.name = etName.text.toString()"))
        assertTrue("保存必须仍读超时", s.contains("replaceRule.timeoutMillisecond = etTimeout.text.toString()"))
        assertTrue("回填必须仍写替换规则", s.contains("etReplaceRule.setText(replaceRule.pattern)"))
        // 超时校验（既有缺陷修复口径不得回退成 toLong()）
        assertTrue("超时非法值必须仍被拦截并展开高级组", s.contains("tilTimeout.error = getString(R.string.replace_timeout_invalid)"))
        assertFalse("不得回退成会抛异常的 toLong()", s.contains(".text.toString().toLong()"))
    }
}