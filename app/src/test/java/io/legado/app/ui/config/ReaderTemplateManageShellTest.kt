package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读页面模板管理页结构不变量（epub-md-rich-rendering 阶段 4.8a 配对）。
 *
 * 为什么机检：管理页族有两条**已被本项目实证会静默回流的路径** ——
 *  ① 顶栏回退到运行时注入（共用布局退役后 ⇒ 顶栏丢失但编译通过）；
 *  ② 页面自行硬编码取色（脱离 `ThemeStore` 单源 ⇒ 四态截图与主题包下必然失守）。
 * 故把「合成壳单源 + 页内顶栏 + 管理组件族 + 无硬编码色 + 入口/清单登记」锁死。
 */
class ReaderTemplateManageShellTest {

    private val activity = "ui/config/ReaderTemplateManageActivity.kt"
    private val screen = "ui/config/ReaderTemplateManageScreen.kt"

    private fun src(rel: String): String = SourceFileProbe.sourceText(rel)

    @Test
    fun `宿主走合成壳单源且顶栏页内承担`() {
        val text = src(activity)
        assertTrue("必须经 composeShell 创建合成壳", text.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", text.contains("binding.root.attachComposeContent {"))
        assertTrue("顶栏必须页内承担", text.contains("GlassTopAppBar("))
        assertFalse("换装后不得回退 viewBinding 委托", text.contains("by viewBinding("))
        assertFalse("不得残留旧顶栏运行时注入", text.contains("installGlassTopBar("))
        assertTrue("管理族背景透明度单键必须接入", text.contains("manageBackgroundAlphaEnabled(): Boolean = true"))
    }

    @Test
    fun `内容区复用管理组件族且不硬编码色`() {
        val text = src(screen)
        assertTrue("必须复用管理页骨架（取色单源在其中）", text.contains("AppPackageManageScreen("))
        assertTrue("列表项必须复用管理卡片", text.contains("AppPackageManageItemCard("))
        assertTrue("行操作必须复用统一按钮族", text.contains("AppPackageManageActionButton("))
        assertTrue("卡内内容必须复用 AppManagementCard", text.contains("AppManagementCard("))
        assertFalse("管理页不得硬编码色（取色只能来自 palette）", text.contains("Color(0x"))
        assertFalse("管理页不得直接写 Color.常量", text.contains("Color."))
    }

    @Test
    fun `行操作覆盖设计要求的用户动作`() {
        val text = src(activity)
        listOf("applyTemplate", "openTemplateEditor", "duplicateTemplate", "exportJson", "confirmDelete", "confirmRestoreDefaults", "importJson")
            .forEach { action ->
                assertTrue("4.8a 行操作缺失：$action", text.contains(action))
            }
    }

    @Test
    fun `整体开关与导入导出免责已接线`() {
        val text = src(activity)
        listOf("toggleTemplates", "setTemplatesEnabled", "importDisclaimer", "exportNotice").forEach { mark ->
            assertTrue("4.9 接线缺失：$mark", text.contains(mark))
        }
        assertTrue("整体开关必须出现在页面上（否则用户无法关闭模板系统）", src(screen).contains("onToggleTemplates"))
        // 作用范围必须**如实**：当前只接了本地 Markdown ⇒ 文案不得声称在线正文/txt 已生效
        assertTrue(
            "摘要必须如实说明当前作用范围",
            src(screen).contains("当前作用于本地 Markdown 阅读")
        )
        assertTrue("必须说明出版 EPUB 不适用", src(screen).contains("出版 EPUB 不适用"))
    }

    @Test
    fun `应用内作者指南资产与入口齐备`() {
        val activityText = src(activity)
        // 路径取自**单源常量**：测试用同一常量读资产，避免"改了路径测试仍绿"
        assertTrue("必须声明指南资产路径常量", activityText.contains("const val GuideAssetPath"))
        assertTrue("指南必须以 Markdown 模式渲染", activityText.contains("TextDialog.Mode.MD"))
        assertTrue("指南入口处理器必须接线", activityText.contains("showAuthorGuide"))
        assertTrue("入口必须真的挂到页面上", activityText.contains("onOpenGuide = ::showAuthorGuide"))
        assertTrue("页面上必须有可点的「作者指南」按钮", src(screen).contains("\"作者指南\""))

        val guide = listOf(
            java.io.File("src/main/assets/md/template-author-guide.md"),
            java.io.File("../app/src/main/assets/md/template-author-guide.md"),
            java.io.File("app/src/main/assets/md/template-author-guide.md")
        ).firstOrNull { it.isFile }
        assertTrue("作者指南资产必须随包存在（缺失 = 入口点了没反应）", guide != null)
        val text = guide!!.readText()
        assertTrue("指南不得为空", text.length > 800)
        // 关键契约/红线必须在场：否则"指南与实现漂移"，用户照抄就写错
        listOf(
            "data-reader-flow=\"body\"",       // 正文槽位（写错静默失效）
            "data-reader-scroll-viewport",      // 滚动模板必填画框
            "data-reader-field",                // 字段槽位
            "[data-reader-theme=\"night\"]",    // 日/夜双版（只写一侧会读不清）
            "--md-font-size",                   // 宿主下发字号
            "OFL",                              // 字体许可白名单
            "CC0",                              // 图片许可白名单
            "本地使用"                           // 第三方素材合规（仅本地、不得分发）
        ).forEach { mark ->
            assertTrue("作者指南缺少关键内容：$mark", text.contains(mark))
        }
    }

    @Test
    fun `设置域入口与清单登记齐备`() {
        val theme = src("ui/config/ThemeConfigFragment.kt")
        assertTrue("设置域必须有入口", theme.contains("KEY_READER_TEMPLATE_MANAGE"))
        assertTrue("入口必须跳转模板管理页", theme.contains("startActivity<ReaderTemplateManageActivity>()"))

        // 清单读取沿用本包既有三候选路径回退（Gradle 单测工作目录随运行方式变化）
        val manifest = listOf(
            java.io.File("src/main/AndroidManifest.xml"),
            java.io.File("../app/src/main/AndroidManifest.xml"),
            java.io.File("app/src/main/AndroidManifest.xml")
        ).first { it.isFile }.readText()
        assertTrue(
            "新增 Activity 必须登记（未登记 = 启动即 ActivityNotFoundException）",
            manifest.contains(".ui.config.ReaderTemplateManageActivity")
        )
    }
}