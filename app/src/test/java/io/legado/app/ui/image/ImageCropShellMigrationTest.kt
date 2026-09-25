package io.legado.app.ui.image

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 10 页（`activity_image_crop`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「FrameLayout 壳 + 6 类节点」：
 *   根底深色 / `photo_view`（PhotoView 手势内核）/ `crop_overlay`（裁剪取景框手势内核）
 *   / `tv_aspect_badge`（比例徽标，位置由 `cropOverlay.getCropRect()` 动态算出）
 *   / `error_bar`（可恢复失败：tv_error + 重试键）/ `action_bar`（取消 + 提示 + 保存 spinner + 确认）。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，**整棵 View 子树在一个
 * `AndroidView` 内原样托管**（托管容器仍是 `FrameLayout`：两处动态几何依赖其 `LayoutParams` 语义）。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再走 viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_image_crop.xml` 不存在）
 *   ③子树托管形态：单点 `AndroidView` + `FrameLayout` 容器 + 两个手势内核程序化构造
 *   ④动态几何口径未丢（徽标与 photoView 仍以 `FrameLayout.LayoutParams` 落位/落尺寸）
 *   ⑤逐项复刻（drawable 底、`progressBarStyleSmall`、selectableItemBackground、几何常量）
 *   ⑥宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑦行为不变量 + 取色处置（画布底走具名资源；亮色前景为画布域字面色并已登记豁免）
 */
class ImageCropShellMigrationTest {

    private val page = "ui/image/ImageCropActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityImageCropBinding"))
        assertTrue(
            "宿主必须显式改绑 ViewBinding 泛型参数",
            s.contains("BaseActivity<ViewBinding>(")
        )
        // 词边界防止把 `import androidx.viewbinding.ViewBinding` 误判为「换装后仍用 binding」
        val bindingRefs = Regex("(?<![A-Za-z])binding\\.[A-Za-z]+").findAll(s).map { it.value }.toSet()
        assertEquals("换装后 binding 只允许 root（合成壳）：${bindingRefs}", setOf("binding.root"), bindingRefs)
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_image_crop.xml")
        assertFalse("activity_image_crop.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewSubtreeHostedInSingleAndroidView() {
        val s = src()
        assertTrue("子树必须以单点 AndroidView 托管", s.contains("factory = { cropRoot }"))
        assertTrue(
            "托管容器必须仍是 FrameLayout（动态几何依赖其 LayoutParams 语义）",
            s.contains("private val cropRoot by lazy") && s.contains("FrameLayout(this).apply")
        )
        assertTrue(
            "两个手势内核必须程序化构造（无 Compose 等价物）",
            s.contains("PhotoView(this)") && s.contains("ImageCropOverlayView(this)")
        )
        assertTrue(
            "子节点顺序必须复刻 XML（声明顺序即 z-order）",
            s.contains("addView(photoView)") && s.contains("addView(cropOverlay)") &&
                s.contains("addView(tvAspectBadge)") && s.contains("addView(errorBar)") &&
                s.contains("addView(actionBar)")
        )
    }

    @Test
    fun dynamicGeometrySemanticsPreserved() {
        val s = src()
        assertTrue(
            "徽标必须仍以 FrameLayout.LayoutParams 落位（原 updateAspectBadge 口径）",
            s.contains("tvAspectBadge.layoutParams as FrameLayout.LayoutParams") &&
                s.contains("layoutParams.leftMargin = (cropRect.left + 8.dpToPx()).roundToInt()")
        )
        assertTrue(
            "photoView 必须仍以 FrameLayout.LayoutParams 落尺寸/边距视察",
            s.contains("(photoView.layoutParams as? FrameLayout.LayoutParams)") &&
                s.contains("layoutParams.leftMargin = cropRect.left.roundToInt()")
        )
        assertTrue("取景框比例必须仍在创建时下发", s.contains("cropOverlay.setAspect(aspectWidth, aspectHeight)"))
        assertTrue("取景框布局变化必须仍触发徽标重算", s.contains("cropOverlay.addOnLayoutChangeListener"))
    }

    @Test
    fun nodeDetailsAreReplicated() {
        val s = src()
        assertTrue(
            "三个 drawable 底必须原样保留",
            s.contains("R.drawable.bg_image_crop_toolbar") &&
                s.contains("R.drawable.bg_image_crop_error_bar") &&
                s.contains("R.drawable.bg_image_crop_aspect_badge")
        )
        assertTrue(
            "保存中 spinner 必须保留 ?android:attr/progressBarStyleSmall",
            s.contains("android.R.attr.progressBarStyleSmall")
        )
        assertTrue(
            "重试键波纹底必须保留 ?attr/selectableItemBackground",
            s.contains("android.R.attr.selectableItemBackground")
        )
        assertTrue(
            "徽标必须保留 monospace 粗体 11sp",
            s.contains("Typeface.MONOSPACE") && s.contains("textSize = 11f") && s.contains("Typeface.BOLD")
        )
        assertTrue(
            "几何常量必须保留（操作栏 64dp / 错误条下边距 76dp / 按钮 44dp）",
            s.contains("64.dpToPx()") && s.contains("bottomMargin = 76.dpToPx()") &&
                s.contains("44.dpToPx()")
        )
        assertTrue(
            "初始可见性必须一致（徽标/错误条/保存 spinner 初始 gone）",
            s.contains("visibility = View.GONE")
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun setupSystemBar(",
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun updateAspectBadge(",
            "private fun showCropError(",
            "private fun hideCropError(",
            "private fun setSavingState(",
            "override fun onDestroy(",
            "private fun loadImage(",
            "private fun decodeBounds(",
            "private fun decodeBitmapWithImageDecoder(",
            "private fun decodeBitmapWithBitmapFactory(",
            "private fun updatePhotoViewport(",
            "private fun saveCrop(",
            "private fun cropVisibleBitmap(",
            "private fun calculateNormalizedCropRect(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun behaviorInvariantsAndColorHandling() {
        val s = src()
        // 手势内核初始化口径
        assertTrue("photoView 必须仍 CENTER_INSIDE", s.contains("ImageView.ScaleType.CENTER_INSIDE"))
        assertTrue("photoView 必须仍限最大缩放 6f", s.contains("photoView.setMaxScale(6f)"))
        // 优化 2：错误条三件套
        assertTrue("错误条文案必须仍走 danger 语义", s.contains("AppSemanticColors.Danger.toArgb()"))
        assertTrue("重试键必须仍走 accent 取色", s.contains("btnRetry.setTextColor(accentColor)"))
        assertTrue("错误条显隐必须成对保留", s.contains("errorBar.visibility = View.VISIBLE") && s.contains("errorBar.visibility = View.GONE"))
        // 优化 1b：保存中态四件套
        assertTrue("保存中态必须仍切确认键可见性", s.contains("btnConfirm.visibility = if (saving) View.GONE else View.VISIBLE"))
        assertTrue("保存中态必须仍切 spinner", s.contains("progressSave.visibility = if (saving) View.VISIBLE else View.GONE"))
        assertTrue("保存中态必须仍切提示文案", s.contains("tvHint.setText(if (saving) R.string.image_crop_saving else R.string.image_crop_hint)"))
        // 取色处置：画布底走具名资源；亮色前景为画布域字面色（已登记豁免）
        assertTrue(
            "画布底色必须走具名资源（不新增行内字面色）",
            s.contains("ContextCompat.getColor(this, R.color.image_canvas_dark)")
        )
        assertTrue("画布域亮色前景必须保留原字面语义", s.contains("Color.WHITE"))
        assertFalse("不得使用 android.R.color.white（命中取色门禁 R.color.(white|black) 禁用模式）",
            s.contains("android.R.color.white"))
        assertFalse("不得回流行内十六进制色字面量", s.contains("#FF"))
        // 裁剪计算链路口径
        assertTrue("可见区裁剪必须保留", s.contains("private fun cropVisibleBitmap("))
        assertTrue("归一化裁剪必须保留", s.contains("private fun calculateNormalizedCropRect("))
        assertTrue("viewportOnly 分支必须保留", s.contains("if (viewportOnly)"))
    }
}