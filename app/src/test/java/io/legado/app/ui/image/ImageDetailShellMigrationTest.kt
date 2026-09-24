package io.legado.app.ui.image

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 5 页（`activity_image_detail`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（ConstraintLayout，黑底）+ 4 个节点」：
 *   `view_pager`（全屏 `ViewPager2` + PhotoView 手势）/ `compose_top_bar`（已 Compose）/
 *   `tv_page_index`（右上页码徽标）/ `layout_rotate_toolbar`（底部三键旋转工具条）。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，其中**三个 View 内核**
 * （`ViewPager2` / 徽标 / 工具条）一律以 `AndroidView` **原样托管**。
 *
 * 本测试锁死六类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再手写 ComposeView / viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_image_detail.xml` 不存在）
 *   ③三个 View 内核仍**以 AndroidView 原样托管**（不是被换成「看起来差不多」的 Compose 组件）
 *   ④四个显隐/文案机制改由**状态**驱动（topBarVisible / rotateToolbarVisible / pageIndexVisible / pageIndexText）
 *   ⑤宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑥行为不变量：沉浸式切换、旋转三键、SAF 保存回执、返回传 currentIndex、共享元素动画
 */
class ImageDetailShellMigrationTest {

    private val page = "ui/image/ImageDetailActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityImageDetailBinding"))
        assertFalse("禁止再经 ComposeView.setContent（顶栏已直接进组合）", s.contains("composeTopBar.setContent"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_image_detail.xml")
        assertFalse("activity_image_detail.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue(
            "ViewPager2（PhotoView 手势，无 Compose 等价物）必须以 AndroidView 原样托管",
            s.contains("AndroidView(") && s.contains("ViewPager2(this)") &&
                s.contains("factory = { viewPager }")
        )
        assertTrue(
            "页码徽标必须以 AndroidView 程序化 TextView 托管（保 drawable 底/白字/14sp 几何）",
            s.contains("createPageIndexView(") && s.contains("R.drawable.bg_image_page_index")
        )
        assertTrue(
            "旋转工具条必须以 AndroidView 程序化 LinearLayout 托管（保底 drawable/内边距/48dp 按钮）",
            s.contains("createRotateToolbar(") && s.contains("R.drawable.bg_overlay_button")
        )
        assertTrue(
            "三个旋转按钮必须逐一还原（图标/尺寸/白色 tint）",
            s.contains("R.drawable.ic_rotate_left") && s.contains("R.drawable.ic_reset") &&
                s.contains("R.drawable.ic_rotate_right") && s.contains("48.dpToPx()")
        )
        assertTrue(
            "原 XML root 的黑色画布底必须由合成壳承担（否则亮色主题下露白）",
            s.contains("setBackgroundColor(Color.BLACK)")
        )
    }

    @Test
    fun viewMechanismsAreStateDriven() {
        val s = src()
        listOf(
            "topBarVisible", "rotateToolbarVisible", "pageIndexVisible", "pageIndexText",
        ).forEach { state ->
            assertTrue(
                "原 View 机制必须改由状态驱动：缺少 `$state`",
                s.contains("private var $state by mutableStateOf")
            )
        }
        assertFalse(
            "不得再调用旧的 visible()/gone()/invisible() 扩展",
            s.contains(".invisible()") || s.contains(".gone()") || s.contains(".visible()")
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initSharedElementTransition(",
            "private fun initImmersion(",
            "private fun initComposeContent(",
            "private fun createPageIndexView(",
            "private fun createRotateToolbar(",
            "private fun createRotateButton(",
            "private fun borderlessItemBackgroundRes(",
            "private fun initViewPager(",
            "private fun initRotateToolbar(",
            "private fun toggleImmersive(",
            "override fun onImageClick(",
            "override fun onImageLongClick(",
            "private fun saveImage(",
            "private fun saveImageInternal(",
            "private fun shareImage(",
            "private fun copyImageUrl(",
            "override fun onPageChanged(",
            "override fun onSaveInstanceState(",
            "override fun finish(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun behaviorInvariantsKept() {
        val s = src()
        // 沉浸式：隐藏/显示系统栏 + 顶栏与工具条随之收起（原两条 setVisibility 全量等价）
        assertTrue("沉浸式必须仍控制系统栏", s.contains("controller.hide(android.view.WindowInsets.Type.systemBars())"))
        assertTrue("沉浸式必须仍控制系统栏恢复", s.contains("controller.show(android.view.WindowInsets.Type.systemBars())"))
        // 旋转三键 → adapter 三个方法（逐一不得少）
        assertTrue("顺时针旋转链路必须保留", s.contains("rotateCurrentClockwise()"))
        assertTrue("逆时针旋转链路必须保留", s.contains("rotateCurrentCounterClockwise()"))
        assertTrue("重置视图链路必须保留", s.contains("resetCurrentView()"))
        // ViewPager2 关键配置
        assertTrue("ViewPager2 必须仍为横向", s.contains("ViewPager2.ORIENTATION_HORIZONTAL"))
        assertTrue("必须仍注册翻页回调", s.contains("registerOnPageChangeCallback("))
        // 页码口径：单图隐藏、多图「X / Y」（R1.4）
        assertTrue("页码文案口径必须保留", s.contains("pageIndexText = \"\${position + 1} / \$total\""))
        assertTrue("单图隐藏页码口径必须保留", s.contains("if (total > 1)"))
        // 状态保存与返回传值（V2 B-4 / R2.6）
        assertTrue("currentIndex 必须仍随实例态保存", s.contains("outState.putInt(KEY_CURRENT_INDEX, currentIndex)"))
        assertTrue("返回必须仍 setResult 传 currentIndex", s.contains("putExtra(EXTRA_CURRENT_INDEX, currentIndex)"))
        // 画布域固定黑白色已按同域同口径登记（门禁 16 可机检）
        assertTrue("白字/白 tint 必须保留（画布域）", s.contains("Color.WHITE"))
    }
}