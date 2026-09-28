package io.legado.app.ui.image.adapter

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W7 8.4（REQ-27 / AD-19）+ W6 7.4/7.5（例外登记）：`PhotoView` 收口 —— **保留为技术硬例外** 的引用收敛审计。
 *
 * ## 技术硬例外表（W6 7.4 / 7.5 判据要求四要素：页面 / 依赖 API / 保留理由 / 替代评估结论）
 *
 * | # | 页面（消费点） | 依赖 API（实测） | 保留理由 | 替代评估结论 |
 * |---|---------------|----------------|---------|-------------|
 * | ① | `ImageCropActivity` | `photoView.setScaleType/setMaxScale` + `cropOverlay.getCropRect()` + `android.graphics.Matrix` | 裁剪需要**旋转变换矩阵**参与裁剪矩形计算 | **SSIV 无等价 API**（无 `setMaxScale`/裁剪矩形读取）⇒ 不替换 |
 * | ② | `ImageDetailAdapter`（含子类 `ImageDetailViewPagerAdapter`；宿主 `ImageDetailActivity` 经 adapter 使用） | `photoView.rotation`（顺/逆 90° 旋转 + 重置）、`photoView.scaleType = FIT_CENTER` | 详情页有**独立旋转按钮**（每图独立 `rotationDegree`，R1b.5-R1b.8） | **SSIV 无 `rotation` 属性 / 无 `setOrientation`**：替换即**丢失旋转能力**（用户可感回归）⇒ 7.4 改为**例外登记**，不替换（与 7.5 同范式） |
 *
 * > 判定口径来源：`spec.md`/tasks §7.4-7.5「消费点替换」原文只给「手势回归录屏」判据，**未评估旋转 API**；
 * > 实施期实读源码后按「**能力等价优先于轨统一**」原则降级为例外（本表即 7.4/7.5 交付物）。
 *
 * ## 收口清单（按实际引用逐个评估，**待删项 = 空集**）
 *
 * | 候选 | 引用者 | 结论 |
 * |------|--------|------|
 * | `ui/widget/image/PhotoView.kt` 本体 | `ImageCropActivity`（例外①）、`ImageDetailAdapter`（例外②）、
 * `item_image_canvas.xml`（共享元素动画载体） | **保留** |
 * | `ui/widget/image/photo/Info.kt`、`RotateGestureDetector.kt` | `PhotoView.kt` 本体 | **随本体保留** |
 * | `res/layout/item_image_canvas.xml` | `ImageCanvasAdapter`（在用） | 保留 |
 * | `res/layout/item_image_page.xml` | `ImageDetailAdapter`（例外②） | 保留 |
 * | `res/layout/dialog_photo_view.xml` | `PhotoDialog`（**W6 7.3 已换 SSIV 轨，无 PhotoView 标签**） | 保留 |
 *
 * 本测试锁三件事（防未来失守）：
 * ① **防误删**：白名单内文件必须仍然存在（否则例外能力会被静默移除）；
 * ② **防扩散**：全仓 `PhotoView` 的**实际引用**（import / XML 标签）必须收敛在白名单内 ——
 *    白名单外出现新引用即「新的技术债」（应换轨，或补例外登记后更新白名单）；
 * ③ **防过期**：两条例外的**依赖 API 必须在源码中仍可追溯** —— 否则说明该页已换轨（应删例外条目），
 *    或说明理由已失真（应重写），两种都必须显式处理而不是留一条假理由。
 *
 * 注：**注释里提到** `PhotoView`（换轨说明）不计入实际引用，故判据用 `import ` 与 `<` 前缀。
 */
class ImagePhotoViewRetentionAuditTest {

    private val appDir = File(".").canonicalFile.let {
        if (File(it, "src/main").isDirectory) it else File(it, "../app").canonicalFile
    }

    /** 例外与在用清单（AD-19「例外清单内的引用不计」的**正向**表达） */
    private val allowed = linkedSetOf(
        "src/main/java/io/legado/app/ui/widget/image/PhotoView.kt",
        "src/main/java/io/legado/app/ui/widget/image/photo/Info.kt",
        "src/main/java/io/legado/app/ui/widget/image/photo/RotateGestureDetector.kt",
        "src/main/java/io/legado/app/ui/image/ImageCropActivity.kt",
        "src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt",
        "src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt",
        "src/main/res/layout/item_image_page.xml",
        "src/main/res/layout/item_image_canvas.xml",
    )

    /** 实际引用判据：Kotlin import 或 XML 标签（不含注释与全限定名提及） */
    private fun actualRefs(): Map<String, String> {
        val root = File(appDir, "src/main")
        val hit = linkedMapOf<String, String>()
        root.walkTopDown()
            .filter { it.isFile && (it.extension == "kt" || it.extension == "xml") }
            .forEach { f ->
                val rel = f.relativeTo(appDir).path.replace('\\', '/')
                val text = f.readText().replace("\r\n", "\n")
                val reasons = mutableListOf<String>()
                if (text.contains("import io.legado.app.ui.widget.image.PhotoView")) {
                    reasons += "import"
                }
                if (text.contains("<io.legado.app.ui.widget.image.PhotoView")) {
                    reasons += "xml-tag"
                }
                if (reasons.isNotEmpty()) hit[rel] = reasons.joinToString("+")
            }
        return hit
    }

    @Test
    fun photoViewReferencesStayInsideDocumentedAllowlist() {
        val refs = actualRefs()
        val outside = refs.keys - allowed
        assertTrue(
            "PhotoView 出现白名单外引用（新的技术债：应换 SSIV 轨，或补例外登记）：$outside",
            outside.isEmpty()
        )
        // 白名单里除「本体 + photo/ 工具类 + 间接消费者」外的消费点必须**仍在直接引用**
        // （否则该条例外已过期，应清理）
        // 注：`ImageCanvasAdapter` 经 ViewBinding 间接使用（`binding.photoView`，无 import）
        // ⇒ 其「仍在用」由 `item_image_canvas.xml` 的 XML 标签断言覆盖。
        val consumers = allowed.filterNot {
            it.contains("/widget/image/") || it.endsWith("ImageCanvasAdapter.kt")
        }
        val stale = consumers.filterNot { refs.containsKey(it) }
        assertTrue(
            "白名单中的消费点已不再引用 PhotoView（例外过期，应删条目与对应布局）：$stale",
            stale.isEmpty()
        )
    }

    @Test
    fun photoViewBodyAndRotateToolsAreRetained() {
        listOf(
            "src/main/java/io/legado/app/ui/widget/image/PhotoView.kt",
            "src/main/java/io/legado/app/ui/widget/image/photo/Info.kt",
            "src/main/java/io/legado/app/ui/widget/image/photo/RotateGestureDetector.kt",
        ).forEach { rel ->
            assertTrue("技术硬例外依赖的本体/工具类不得删除：$rel", File(appDir, rel).isFile)
        }
        // 裁剪页与详情页（例外①②）的保留理由必须仍在源码中可追溯
        val crop = File(appDir, "src/main/java/io/legado/app/ui/image/ImageCropActivity.kt").readText()
        assertTrue("裁剪页须仍使用 PhotoView（例外①）", crop.contains("PhotoView"))
    }

    /**
     * 例外表的**理由可追溯性**（W6 7.4 / 7.5）：两条例外各自的「依赖 API」必须仍在源码中命中。
     *
     * 为什么必须机器校验：例外条目最危险的失效形态是**理由过期** —— 页面早已换轨，例外表却还写着
     * 「因 A/B API 保留」，后人据此以为「这里不能动」（本仓已有先例：文档行号/注释与实际失同步）。
     */
    @Test
    fun exceptionRationalesStayTraceable() {
        val crop =
            File(appDir, "src/main/java/io/legado/app/ui/image/ImageCropActivity.kt").readText()
        assertTrue(
            "例外① 理由失真：裁剪页已不再依赖 setMaxScale/getCropRect（若已换轨应删该例外条目）",
            crop.contains("setMaxScale") && crop.contains("getCropRect()")
        )
        val detail =
            File(appDir, "src/main/java/io/legado/app/ui/image/adapter/ImageDetailAdapter.kt")
                .readText()
        assertTrue(
            "例外② 理由失真：详情页已不再使用 photoView.rotation（若已换轨应删该例外条目）",
            detail.contains("photoView.rotation")
        )
        assertTrue(
            "例外② 的「每图独立旋转状态」能力不得静默删除（删能力须显式评审并改例外表）",
            detail.contains("rotationDegree")
        )
    }

    @Test
    fun dialogPhotoViewHasNoPhotoViewTagLeft() {
        // W6 7.3 已把 PhotoDialog 换到 SSIV 轨 ⇒ 该布局不得残留 PhotoView 标签
        val dialog = File(appDir, "src/main/res/layout/dialog_photo_view.xml").readText()
        assertTrue("PhotoDialog 应已换 SSIV 轨", dialog.contains("SubsamplingScaleImageView"))
        assertTrue(
            "dialog_photo_view.xml 不得残留 PhotoView 标签（换轨未收尾）",
            !dialog.contains("<io.legado.app.ui.widget.image.PhotoView")
        )
        assertEquals(
            "三个候选布局都应仍被工程使用（不允许静默删除）",
            3,
            listOf(
                "src/main/res/layout/item_image_canvas.xml",
                "src/main/res/layout/item_image_page.xml",
                "src/main/res/layout/dialog_photo_view.xml",
            ).count { File(appDir, it).isFile }
        )
    }
}
