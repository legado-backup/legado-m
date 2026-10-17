package io.legado.app.ui.config

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 首屏加载模板**面板接线**契约单测（reader-theme-family 3.12 配对 · `ui/config` 目录）。
 *
 * 为什么只能做结构断言（并如实说明）：管理页是 **Compose + Activity** 面，纯 JVM 无 Compose 环境、
 * 也构造不出 appCtx ⇒ 无法行为化；而本项目的失守恰多在"面板接线漏一项"（入口没接、按钮没接、
 * 弹窗少一个按钮、Manifest 没注册 —— 都是"看着实现了、点了没反应"）。
 * 故这里把**接线不变量**逐条钉住并给**期望值**（参数集合逐项相等，不是"存在即可"的弱断言）。
 * 行为正确性由另外四份行为测试（Decode / Manager / Chrome / OverlayFallback）+ 真机 L2 承担。
 */
class EpubLoadingTemplateUiWiringTest {

    private fun source(path: String) = File("src/main/java/$path").readText()

    @Test
    fun `管理页 Screen 必须把五项交互全部接线`() {
        val screen = source("io/legado/app/ui/config/EpubLoadingTemplateManageScreen.kt")
        // 复用族（禁私自拉组件）：AppPackageManageScreen + AppPackageManageItemCard
        assertTrue("必须复用 AppPackageManageScreen", screen.contains("AppPackageManageScreen("))
        assertTrue("必须复用 AppPackageManageItemCard", screen.contains("AppPackageManageItemCard("))
        assertTrue("取色必须走 rememberAppManagementPalette 族（禁硬编码色）", !screen.contains("Color(0x"))
        // ①签名必须声明五项回调（形参写法 `onXxx:`）
        val declared = setOf("onApply", "onEdit", "onMoreActions", "onAddClick", "onRestoreDefault")
            .filter { screen.contains("$it:") }
            .toSet()
        assertEquals(
            "五项交互回调必须全部在 Screen 签名中声明",
            setOf("onApply", "onEdit", "onMoreActions", "onAddClick", "onRestoreDefault"), declared
        )
        // ②必须真的透传到组件调用点（少一项即对应按钮点了没反应）
        // ⚠️ 透传**目标形参名**与回调名不同（组件侧叫 `moreActions`、`onAdd`）——直接按组件形参名核对
        listOf("onApply =", "onEdit =", "moreActions =", "onAdd =", "onRestoreDefault =").forEach { marker ->
            assertTrue("组件调用点缺少透传：$marker", screen.contains(marker))
        }
        assertTrue("应用/已应用文案必须用既有字符串资源", screen.contains("R.string.theme_apply"))
        assertTrue("内置项不得提供编辑（canEdit 取反）", screen.contains("canEdit = !template.builtIn"))
    }

    @Test
    fun `管理页宿主必须接齐应用导入导出删除四条动作`() {
        val activity = source("io/legado/app/ui/config/EpubLoadingTemplateManageActivity.kt")
        assertTrue("应用", activity.contains("EpubLoadingTemplateManager.apply("))
        assertTrue("保存（导入/编辑）", activity.contains("EpubLoadingTemplateManager.save("))
        assertTrue("导出", activity.contains("EpubLoadingTemplateManager.export("))
        assertTrue("删除", activity.contains("EpubLoadingTemplateManager.delete("))
        assertTrue("恢复默认", activity.contains("EpubLoadingTemplateManager.restoreDefault("))
        assertTrue("失败必须可见化（禁止静默）", activity.contains("exceptionOrNull()?.message"))
        assertTrue("G-37：LegadoTheme 必须上提为内容根作用域", activity.contains("LegadoTheme {"))
        assertTrue("导入必须先给免责确认", activity.contains("ImportDisclaimer"))
    }

    @Test
    fun `预览弹窗必须双按钮且走既有载荷解码单源`() {
        val dialog = source("io/legado/app/ui/config/EpubLoadingPreviewDialog.kt")
        assertTrue("必须复用弹窗框架", dialog.contains("AppDialogFrame("))
        assertTrue("必须复用既有动作按钮族", dialog.contains("LegadoMiuixActionButton("))
        assertTrue("必须走既有载荷解码（校验白名单）", dialog.contains("decodeLoadingPayload("))
        assertTrue("必须复用正式绘制器承载的预览 View", dialog.contains("EpubLoadingPreviewView("))
        listOf("切换到日间", "切换到夜间", "关闭").forEach { label ->
            assertTrue("预览弹窗缺少按钮：$label", dialog.contains(label))
        }
    }

    @Test
    fun `预览 View 必须委托同一绘制器`() {
        val view = source("io/legado/app/ui/config/EpubLoadingPreviewView.kt")
        assertTrue("预览必须复用窗口首屏同一绘制器（预览所见即开书所见）", view.contains("EpubLoadingOverlay("))
        assertTrue("预览必须调用 draw(...)", view.contains(".draw("))
    }

    @Test
    fun `设置入口与清单注册`() {
        val fragment = source("io/legado/app/ui/config/ThemeConfigFragment.kt")
        assertTrue("设置页必须出现新入口行", fragment.contains("KEY_EPUB_LOADING_TEMPLATE_MANAGE"))
        assertTrue("入口必须指向新管理页", fragment.contains("EpubLoadingTemplateManageActivity"))
        assertTrue(
            "入口摘要必须显示当前模板名（读 Manager 单源）",
            fragment.contains("EpubLoadingTemplateManager.selected(")
        )
        assertTrue("入口须可被搜索命中", fragment.contains("searchKeys = listOf(\"首屏加载\""))

        val manifest = File("src/main/AndroidManifest.xml").readText()
        assertTrue("清单必须注册管理页", manifest.contains(".ui.config.EpubLoadingTemplateManageActivity"))
        assertFalse(
            "管理页不得导出（外部应用不可直接拉起）",
            Regex("""EpubLoadingTemplateManageActivity[\s\S]{0,160}?exported="true"""").containsMatchIn(manifest)
        )
        assertTrue("管理页须显式 exported=false", manifest.contains("""exported="false""""))
    }
}
