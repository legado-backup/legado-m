package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R3「首屏加载模板」入口接线契约（reader-theme-family-rework 配对）。
 *
 * 背景（用户 2026-10-19 原话）：「Archive 的 EPUB 加载模板阅读器首屏功能……**我都没有找到对应的设置入口**！」
 * 旧任务的入口只存在于「主题设置 → 界面元素」分区，而旧 L2 判据用 `am start -n <Activity>` **直接拉起**
 * ⇒ **入口可达性从未被验证**（也能解释为何"入口不对"没被发现）。
 *
 * 本契约锁死三件事（均可在文本层机检，无需设备）：
 *  ①**第二入口存在**于「阅读设置」页（`OtherConfigFragment`，与 `epubReadEngine` 相邻）；
 *  ②**双入口同源**：两处摘要都取 `EpubLoadingTemplateManager.selected(...)`、都指向同一 Activity
 *    ⇒ 切换模板后两处必然一致刷新（不可能出现"一处显示 A、另一处显示 B"）；
 *  ③**检索键覆盖用户心智词**（首屏加载 / 开书首屏 / 加载模板），保证设置页搜索可发现。
 *
 * ⚠️ 为什么用源码文本探针而不是行为断言：`buildPageSpec()` 是 `ComposeSettingFragment` 的实例方法，
 * 依赖 Android Context/Compose 宿主，纯 JVM 无法调用（与本包既有 `OtherConfigEpubEngineDefaultTest`
 * 同族局限）。**行为侧**由真机 L2（`l2_verify_epub_loading_template.py` 的真实点击链）覆盖。
 */
class OtherConfigLoadingTemplateEntryTest {

    private val other = SourceFileProbe.sourceText("ui/config/OtherConfigFragment.kt")
    private val theme = SourceFileProbe.sourceText("ui/config/ThemeConfigFragment.kt")

    @Test
    fun `阅读设置页须存在首屏加载模板入口`() {
        assertEquals(
            "阅读设置页须定义该入口 key",
            true,
            other.contains("KEY_EPUB_LOADING_TEMPLATE_MANAGE")
        )
        assertEquals(
            "入口须指向首屏加载模板管理页",
            true,
            other.contains("startActivity<EpubLoadingTemplateManageActivity>()")
        )
        assertEquals(
            "标题须复用既有文案键（两处文案一致）",
            true,
            other.contains("R.string.epub_loading_template_manage")
        )
    }

    @Test
    fun `两个入口的摘要必须同源以保证状态一致`() {
        assertEquals(
            "阅读设置入口摘要取同一 Manager",
            true,
            other.contains("EpubLoadingTemplateManager.selected(")
        )
        assertEquals(
            "主题设置入口摘要取同一 Manager",
            true,
            theme.contains("EpubLoadingTemplateManager.selected(")
        )
        // 双入口同源计数：两处都必须出现（缺一即是"状态会分叉"）
        assertEquals(
            "两处入口都必须从同一数据源取摘要",
            2,
            listOf(other, theme).count { it.contains("EpubLoadingTemplateManager.selected(") }
        )
    }

    @Test
    fun `检索键须覆盖开书首屏与加载模板两类心智词`() {
        val hasKey = listOf("首屏加载", "开书首屏", "加载模板").count { other.contains("\"$it\"") }
        assertEquals("三类心智词须全部覆盖（可搜索到）", 3, hasKey)
        assertTrue("入口 Key 与主题设置侧保持同名（便于回归定位）", other.contains("\"epub_loading_template_manage\""))
    }

    @Test
    fun `设置项与说明页须明示适用范围与回落口径`() {
        // 背景（2026-10-20 用户实测 + 用户裁定）：用户先报「首屏加载模板设置已应用却没生效」——
        // 真机取证（`loading overlay mode=` 正式自证串）证实：EPUB 冷加载走模板；**在线文本小说 0 条样本**
        // （模板注入点只在 EPUB 内核加载面）。用户随后的裁定是「这玩意应该适配更多阅读格式，在线/离线小说
        // 文本都要支持，就跟主题模式一样」⇒ 已把模板扩到**文本阅读面**（见
        // `ui/book/read/loading/LoadingTemplateOverlayView.kt` + `activity_book_read.xml`）。
        // 故文案必须同步成"EPUB 与文本书均适用"，并写明回落口径（防再次出现"设置了却没反应"的误解）。
        val screen = SourceFileProbe.sourceText("ui/config/EpubLoadingTemplateManageScreen.kt")
        assertTrue("管理页说明须写明 EPUB 与文本书均适用", screen.contains("EPUB 与在线/离线文本书均适用"))
        assertTrue("管理页说明须写明回落口径（已有内容页/模板不可用）", screen.contains("自动回落原有加载态"))

        val strings = stringsXml()
        assertTrue(
            "设置项摘要须写成两种格式都生效（否则列表里看不出覆盖面）",
            strings.contains("<string name=\"epub_loading_template_manage_summary\">当前：%1\$s（EPUB 与文本书")
        )
    }

    /** 读 `strings.xml`（`SourceFileProbe` 只覆盖 java 源码根 ⇒ 这里自行三候选回退）。 */
    private fun stringsXml(): String {
        val candidates = listOf(
            "src/main/res/values/strings.xml",
            "../app/src/main/res/values/strings.xml",
            "app/src/main/res/values/strings.xml",
        )
        return candidates.map { java.io.File(it) }.firstOrNull { it.isFile }?.readText()
            ?: throw AssertionError("未找到 strings.xml（工作目录=${java.io.File(".").absolutePath}）")
    }
}
