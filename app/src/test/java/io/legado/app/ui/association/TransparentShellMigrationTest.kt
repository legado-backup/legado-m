package io.legado.app.ui.association

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：透明壳页（`activity_translucence`，**5 个 Activity 共用**）换装的 **CB-1 结构不变量**
 * （配对测试，JVM 可跑）。
 *
 * 背景：原 XML = 透明底 `ConstraintLayout` + 居中 `RotateLoading@rotate_loading`（36dp / `app:loading_width=2dp` /
 * 初值 gone）+ 两个居中 ComposeView 卡槽（`cv_result_card` wrap_content / `cv_import_progress` match_parent 宽）。
 * 5 个宿主共用同一布局 ⇒ 换装不能每页各写一遍骨架，必须收敛到**共享装配** `TransparentShellViews`。
 *
 * 本测试锁死六类事实（只写文档的约束一律失效）：
 *  ①5 个宿主一律 composeShell + `shell.install(binding.root)` 单源，不再手写 ComposeView / viewBinding / 引用 R.layout
 *  ②XML 已退役（`activity_translucence.xml` 不存在）
 *  ③`ComposeView` 构造点收敛到唯一工厂 `slot()`（合成策略也只设一次）
 *  ④骨架几何与原 XML 逐项等价（透明底色名 / 36dp / 初值 gone / 笔宽 2dp / 两卡槽 wrap 与整宽居中）
 *  ⑤宿主卡槽接线保持（文件关联→结果卡槽，在线导入→进度卡槽，其余三页恒不接线 = 原 XML 的 gone）
 *  ⑥宿主业务逻辑未因换装消失
 */
class TransparentShellMigrationTest {

    /** 共用 `activity_translucence` 的 5 个宿主（同一批换装）。 */
    private val hosts = listOf(
        "ui/association/FileAssociationActivity.kt",
        "ui/association/OnLineImportActivity.kt",
        "ui/association/OpenUrlConfirmActivity.kt",
        "ui/association/VerificationCodeActivity.kt",
        "ui/file/HandleFileActivity.kt",
    )

    /** 共享装配（本批新增，唯一承载骨架与两卡槽）。 */
    private val assembly = "ui/association/TransparentShellViews.kt"

    private fun src(relFromMainJava: String): String = SourceFileProbe.sourceText(relFromMainJava)

    @Test
    fun everyHostUsesSingleSourceShell() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 必须经 composeShell 建壳", s.contains("composeShell(this)"))
            assertTrue(
                "$rel 必须装配共享壳（否则骨架会退化成逐页复制）",
                s.contains("shell.install(binding.root)")
            )
            assertTrue(
                "$rel 必须持有共享装配字段",
                s.contains("private val shell by lazy { TransparentShellViews(this) }")
            )
            assertFalse("$rel 禁止手写 ComposeView 装配", s.contains("ComposeView("))
            assertFalse(
                "$rel 禁止自行设置合成策略（已收敛到唯一工厂）",
                s.contains("ViewCompositionStrategy")
            )
            assertFalse("$rel 不得再走 viewBinding 委托", s.contains("viewBinding("))
            assertFalse("$rel 不得再引用已退役布局", s.contains("ActivityTranslucenceBinding"))
        }
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_translucence.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_translucence.xml").exists()
        )
    }

    @Test
    fun composeViewConstructionIsSingleFactory() {
        val s = src(assembly)
        assertEquals(
            "两个卡槽必须共用唯一 `slot()` 工厂，否则合成策略会分散在多处",
            1,
            Regex("""ComposeView\(""").findAll(s).count()
        )
        assertEquals(
            "合成策略只允许在唯一工厂内设置一次",
            1,
            Regex("""setViewCompositionStrategy\(""").findAll(s).count()
        )
        assertTrue("结果卡槽必须委托到 slot()", s.contains("val resultCard: ComposeView by lazy { slot() }"))
        assertTrue("进度卡槽必须委托到 slot()", s.contains("val importProgress: ComposeView by lazy { slot() }"))
        assertTrue(
            "卡槽初值必须 gone（与原 XML 的 android:visibility=\"gone\" 一致）",
            s.contains("visibility = View.GONE")
        )
    }

    @Test
    fun skeletonParityWithRetiredXml() {
        val s = src(assembly)
        // 根：透明底复用资源名（与 XML 同口径，不写字面色）
        assertTrue("透明底必须复用资源名", s.contains("R.color.transparent50"))
        assertFalse("禁止写字面色值", Regex("""Color\(0x""").containsMatchIn(s))
        // rotate_loading：36dp 几何 + 笔宽 2dp（原 app:loading_width）+ 初值 gone
        assertTrue("loading 必须复刻 36dp 几何", s.contains(".size(36.dp)"))
        assertTrue("loading 必须复刻 app:loading_width=2dp", s.contains("setLoadingWidthDp(2)"))
        // 三要素一律 AndroidView 原样托管
        listOf("rotateLoading", "resultCard", "importProgress").forEach { field ->
            assertTrue("`$field` 必须以 AndroidView 原样托管", s.contains("factory = { $field }"))
        }
        // 两卡槽几何：结果卡槽 wrap_content 居中 / 进度卡槽整宽居中
        assertTrue("结果卡槽须 wrap_content 居中", s.contains("wrapContentSize(Alignment.Center)"))
        assertTrue("进度卡槽须整宽", s.contains(".fillMaxWidth()"))
        assertTrue("进度卡槽须纵向居中", s.contains("wrapContentHeight(Alignment.CenterVertically)"))
    }

    @Test
    fun hostSlotWiringPreserved() {
        val file = src("ui/association/FileAssociationActivity.kt")
        assertTrue("文件关联页必须接线 loading 显隐", file.contains("shell.rotateLoading.visible()"))
        assertTrue("文件关联页必须接线结果卡槽", file.contains("shell.resultCard.setContent {"))
        assertFalse(
            "不得再操作退役布局的 id",
            file.contains("binding.rotateLoading") || file.contains("binding.cvResultCard")
        )

        val online = src("ui/association/OnLineImportActivity.kt")
        assertTrue("在线导入页必须接线进度卡槽", online.contains("shell.importProgress.setContent {"))
        assertTrue(
            "进度卡显隐必须走共享装配",
            online.contains("shell.importProgress.visibility = View.VISIBLE") &&
                online.contains("shell.importProgress.visibility = View.GONE")
        )
        assertFalse("不得再操作退役布局的 id", online.contains("binding.cvImportProgress"))

        // 其余三页只挂壳、不接线卡槽（原 XML 里两卡槽恒 gone ⇒ 零占位）
        listOf(
            "ui/association/OpenUrlConfirmActivity.kt",
            "ui/association/VerificationCodeActivity.kt",
            "ui/file/HandleFileActivity.kt",
        ).forEach { rel ->
            val s = src(rel)
            assertFalse(
                "$rel 不应接线卡槽（与原 XML 一致：恒 gone 零占位）",
                s.contains("shell.resultCard") || s.contains("shell.importProgress")
            )
        }
    }

    @Test
    fun hostLogicPreserved() {
        val file = src("ui/association/FileAssociationActivity.kt")
        listOf(
            "override fun onActivityCreated(",
            "private fun initResultCard(",
            "private fun showResult(",
            "private fun importBubble(",
            "private fun importBook(",
            "private fun launchBookTreeSelect(",
            "private fun confirmBookImport(",
            "private fun describeBookUri(",
        ).forEach { marker ->
            assertTrue("文件关联页换装不得删改宿主逻辑：缺少 `$marker`", file.contains(marker))
        }
        assertTrue(
            "本地书籍目录选择器必须保留（换装曾误删）",
            file.contains("private val localBookTreeSelect = registerForActivityResult(HandleFileContract())")
        )

        val online = src("ui/association/OnLineImportActivity.kt")
        listOf(
            "override fun onActivityCreated(",
            "private fun initProgressCard(",
            "private fun reportProgress(",
            "private fun downloadOnlinePackage(",
            "private fun prepareParagraphRuleImport(",
            "private fun showParagraphRulePreview(",
            "override fun onOnlineImportConfirmed(",
            "override fun onOnlineImportCancelled(",
            "override fun onOnlineImportRetry(",
            "private fun importOnlinePackage(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("在线导入页换装不得删改宿主逻辑：缺少 `$marker`", online.contains(marker))
        }
    }
}