package io.legado.app.ui.qrcode

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：扫码页（`activity_qrcode_capture`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `LinearLayout { compose_top_bar ; FrameLayout { fl_content(相机预览 Fragment 容器) ;
 * compose_qr_overlay } }`。CE-b 把骨架交给 Compose，其中 `fl_content` 以 `AndroidView` 原样托管
 * （**Fragment 事务按 id 定位容器** ⇒ 必须显式赋同 id，且事务要延到容器上树后提交）。
 *
 * 本测试锁死五类事实（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 已退役（`activity_qrcode_capture.xml` 不存在），但 `fl_content` id 必须已迁入 `values/ids.xml`
 *   ③预览容器以 `AndroidView` 原样托管并**显式赋 `R.id.fl_content`**
 *   ④Fragment 事务必须延到容器上树之后（`flContent.post`），不得在 `onActivityCreated` 里直接 commit
 *   ⑤宿主业务逻辑未消失（解码闭环 / 权限兜底 / 结果回传）
 */
class QrCodeShellMigrationTest {

    private val page = "ui/qrcode/QrCodeActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertTrue("顶栏与覆盖层必须收敛为单一 initComposeContent", s.contains("private fun initComposeContent("))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityQrcodeCaptureBinding"))
    }

    @Test
    fun xmlIsRetiredButIdMovedToIds() {
        val f = File(SourceFileProbe.layoutDir(), "activity_qrcode_capture.xml")
        assertFalse("activity_qrcode_capture.xml 应已退役（CE-b）", f.exists())
        val ids = SourceFileProbe.sourceTextByPath("src/main/res/values/ids.xml")
        assertTrue("退役 XML 的 fl_content id 必须迁入 values/ids.xml", ids.contains("name=\"fl_content\""))
    }

    @Test
    fun fragmentContainerHostedViaAndroidViewWithExplicitId() {
        val s = src()
        assertTrue("预览容器必须以 AndroidView 原样托管", s.contains("factory = { flContent }"))
        assertTrue("必须显式赋 R.id.fl_content（Fragment 事务按 id 定位）", s.contains("id = R.id.fl_content"))
        assertTrue("Fragment 事务必须延到容器上树后（flContent.post）", s.contains("flContent.post {"))
        assertFalse("不得再引用 XML 时代的 compose_qr_overlay 节点", s.contains("binding.composeQrOverlay"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun attachQrFragment(",
            "override fun onResume(",
            "private fun launchImagePicker(",
            "private fun openAppPermissionSettings(",
            "private fun decodeQrImage(",
            "private fun onDecodeFailed(",
            "private fun checkCameraPermission(",
            "private fun qrCodeFragment(",
            "fun onCameraPermissionDenied(",
            "override fun onScanResultCallback(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // F188/F189/A3-3 三条优化语义不得被换装带掉
        listOf(
            "DECODE_CONFIRM_DELAY",
            "enabled = !decoding",
            "cameraBlocked = true",
            "decodeFailed = true",
            "setResult(RESULT_OK, intent)",
        ).forEach { marker ->
            assertTrue("扫码闭环语义不得缺失：`$marker`", s.contains(marker))
        }
    }
}