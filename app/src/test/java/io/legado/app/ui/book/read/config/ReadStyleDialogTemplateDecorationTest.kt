package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读页样式弹层的「页面模板」区契约（epub-md-rich-rendering 阶段 4.8d 配对）。
 *
 * 为什么用源码级断言：该区落在 Compose 弹层里，JVM 无法实例化（依赖 `ReadBook`/`ReadBookConfig`
 * 与 Android 上下文），而它要防的三类失守**都不会崩溃**、只会静默欺骗用户：
 * ① 装饰档位改了但没落偏好 ⇒ 下次打开又变回"中"；
 * ② 改了没重渲染 ⇒ 沙箱里的档位是 init 时下发的，界面看着变了、正文没变（"设置了没反应"）；
 * ③ 模板接管排版却仍让用户调字号/行距 ⇒ 调完毫无变化（AD-33/4.8d 明确要求置灰 + 给说明）。
 */
class ReadStyleDialogTemplateDecorationTest {

    private val src = "ui/book/read/config/ReadStyleDialog.kt"

    private fun text(): String = SourceFileProbe.sourceText(src)

    @Test
    fun `装饰强度四档齐备且落偏好`() {
        val s = text()
        assertTrue("必须存在装饰区", s.contains("private fun TemplateDecorationSection("))
        listOf("\"0\", \"无\"", "\"1\", \"轻\"", "\"2\", \"中\"", "\"3\", \"强\"").forEach { option ->
            assertTrue("缺档位选项：$option", s.contains(option))
        }
        assertTrue("档位变更必须写偏好（否则下次打开回落默认）", s.contains("ReaderTemplateManager.setDecorationLevel(next)"))
        assertTrue("专注模式必须写偏好", s.contains("ReaderTemplateManager.setFocusMode(checked)"))
    }

    @Test
    fun `装饰变更必须触发重渲染`() {
        val s = text()
        assertTrue("必须有重渲染出口", s.contains("private fun reloadAfterTemplatePreferenceChanged()"))
        assertTrue(
            "重渲染必须走既有配置事件（沙箱档位只在 init 下发 ⇒ 不重载则界面变了正文没变）",
            s.contains("postEvent(EventBus.UP_CONFIG, arrayListOf(5))")
        )
        // 档位与专注模式两处都要调重渲染（漏一处 = 该设置静默失效）
        assertTrue(
            "档位与专注模式都必须调重渲染（当前 ${Regex("reloadAfterTemplatePreferenceChanged\\(\\)").findAll(s).count()} 次）",
            Regex("reloadAfterTemplatePreferenceChanged\\(\\)").findAll(s).count() >= 3
        )
    }

    @Test
    fun `模板接管排版时原生排版项置灰并给说明`() {
        val s = text()
        assertTrue("必须有作用域判定", s.contains("private fun templateTakesOverTypography()"))
        assertTrue("必须有与总开关无关的作用域判据", s.contains("private fun templateInScope()"))
        assertTrue(
            "作用域须对齐 archive 的 isOrdinaryText（非 EPUB、非音视频/图片/PDF）：现由判据单源 `ReaderTemplateManager.isTextLikeContent` 承担",
            s.contains("ReaderTemplateManager.isTextLikeContent(ReadBook.book)")
        )
        assertTrue("必须先过总开关", s.contains("if (!ReaderTemplateManager.templatesEnabled()) return false"))
        // 字号/字距/行距/段距四块 + 字重 + 三个入口（字体/缩进/版面）都要按锁置灰
        val gated = Regex("enabled = !typographyLocked").findAll(s).count()
        assertTrue("置灰点不足（当前 $gated 处，至少 8 处：4 指标 + 字重 + 字体/缩进/版面）", gated >= 8)
        assertTrue("必须给出「已置灰 / 由模板决定」的说明", s.contains("模板已接管正文排版"))
    }

    @Test
    fun `入口按作用域显性化且未启用时不渲染装饰控件`() {
        val s = text()
        // 用户反馈「不知道入口在哪」的机制性根因：入口原先只在"模板已启用"时出现 ⇒ 未启用用户永远看不到（鸡生蛋）
        assertTrue("必须有与总开关无关的作用域判据", s.contains("private fun templateInScope()"))
        assertTrue("入口区必须按作用域显示", s.contains("if (templateInScope()) {"))
        assertTrue(
            "未启用时必须就地给出启用开关（无需去设置里翻找）",
            s.contains("\"启用页面模板\"") && s.contains("ReaderTemplateManager.setTemplatesEnabled(enable)")
        )
        assertTrue("必须有管理页直达入口", s.contains("startActivity<ReaderTemplateManageActivity>()"))
        assertTrue(
            "不支持的内容形态不得出现入口（判定走单源 `ReaderTemplateManager.isTextLikeContent`）",
            s.contains("ReaderTemplateManager.isTextLikeContent(ReadBook.book)")
        )
        assertTrue("未启用时不渲染装饰档位/专注开关", s.contains("if (!enabled) return@ReaderSectionCard"))
        assertTrue("就地启用后必须立刻重渲染", s.contains("reloadAfterTemplatePreferenceChanged()"))
    }

    @Test
    fun `装饰区取色仍走弹层单源且无硬编码色`() {
        val s = text()
        assertTrue("取色只能走 style 单源", s.contains("style.secondaryText") && s.contains("style.primaryText"))
        assertFalse("不得硬编码色值（违规色一律登记 allowlist 后才可出现）", s.contains("Color(0x"))
        assertFalse("禁用态只用 alpha 弱化，不引入新色", s.contains("Color.Gray"))
    }
}