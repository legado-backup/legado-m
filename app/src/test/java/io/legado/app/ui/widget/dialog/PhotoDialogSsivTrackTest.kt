package io.legado.app.ui.widget.dialog

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W6 7.3（AD-10/AD-21）：`PhotoDialog` 呈现轨收敛为 SSIV 的不变量。
 *
 * 为什么值得测（实证根因）：本对话框有 **15 处调用点**（书源调试 / RSS 脚本 / 验证码 / 书籍详情 /
 * 词典 / 视频 / 正文长按等），是共享面板 ⇒ ① 若仍留 `PhotoView` 引用，W7 无法收口删除；
 * ② 远程分支必须走 `downloadOnly` 取文件（SSIV 不能直接吃 URL），漏改会导致「远程图打不开」
 * 且**不会**编译失败；③ 异步回调必须带生命周期守卫（对话框已关闭时访问 binding 会崩）。
 */
class PhotoDialogSsivTrackTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val dialog by lazy { read("src/main/java/io/legado/app/ui/widget/dialog/PhotoDialog.kt") }
    private val layout by lazy { read("src/main/res/layout/dialog_photo_view.xml") }

    @Test
    fun viewIsSubsamplingScaleImageViewAndNoPhotoViewLeft() {
        assertTrue("布局须换成 SSIV", layout.contains("com.davemorrissey.labs.subscaleview.SubsamplingScaleImageView"))
        assertFalse(
            "布局不得再以 PhotoView 作为视图节点（注释中提及原实现不算）",
            layout.contains("<io.legado.app.ui.widget.image.PhotoView")
        )
        assertFalse("代码不得再引用 PhotoView", dialog.contains("ui.widget.image.PhotoView"))
    }

    @Test
    fun threeBranchesBindThroughPyramidLoader() {
        assertTrue("① 内存缓存命中绑 Bitmap", dialog.contains("ImagePyramidLoader.bindNormalBitmap("))
        assertTrue("② 本地书籍图绑文件", dialog.contains("ImagePyramidLoader.bindNormalImage("))
        assertTrue(
            "③ 远程图须先 downloadOnly 落地文件再绑",
            dialog.contains("ImageLoader.loadFile(") && dialog.contains(".submit().get()")
        )
        assertTrue(
            "远程取图须保留 sourceOrigin 注入（CDN 防盗链）",
            dialog.contains("OkHttpModelLoader.sourceOriginOption")
        )
    }

    @Test
    fun asyncCallbacksAreLifecycleGuardedAndErrorIsVisible() {
        assertTrue("异步回调须判 isAdded（防 detached 访问 binding）", dialog.contains("if (!isAdded"))
        assertTrue("失败须有可见兜底图（非静默黑屏）", dialog.contains("ImageSource.bitmap(it.toBitmap())"))
        assertTrue("失败须可定位日志", dialog.contains("AppLog.put("))
    }
}