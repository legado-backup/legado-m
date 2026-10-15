package io.legado.app.ui.book.read

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * HL-3 配对用例 —— 模板面正文**复用闸**真值表。
 *
 * 钉住的核心断言：**手动划线版本变化必须打破复用**（否则划一条线后模板正文不重装饰，
 * 用户看到"划了没反应"）；规则版本同理。两者的其余前置条件（同章/后端在场/模板生效）也必须成立。
 */
class TemplateReuseGateTest {

    private fun reuse(
        templateActive: Boolean = true,
        preparedIndex: Int = 3,
        chapterIndex: Int = 3,
        backendPresent: Boolean = true,
        decoratedRulesVersion: Int = 7,
        currentRulesVersion: Int = 7,
        decoratedManualVersion: Int = 2,
        currentManualVersion: Int = 2
    ) = TemplateReuseGate.shouldReuse(
        templateActive, preparedIndex, chapterIndex, backendPresent,
        decoratedRulesVersion, currentRulesVersion, decoratedManualVersion, currentManualVersion
    )

    @Test
    fun allConditionsMatch_reusesDecoratedContent() {
        assertTrue("全部前置条件与两条版本都一致 ⇒ 可复用", reuse())
    }

    @Test
    fun manualVersionChanged_breaksReuse() {
        assertFalse(
            "划了一条线（highlightsVersion 变化）必须重装饰重渲染",
            reuse(decoratedManualVersion = 2, currentManualVersion = 3)
        )
    }

    @Test
    fun rulesVersionChanged_breaksReuse() {
        assertFalse(
            "改了规则必须重装饰重渲染",
            reuse(decoratedRulesVersion = 7, currentRulesVersion = 8)
        )
    }

    @Test
    fun differentChapter_breaksReuse() {
        assertFalse("换了章不能复用上一章的已装饰正文", reuse(preparedIndex = 3, chapterIndex = 4))
    }

    @Test
    fun backendAbsent_breaksReuse() {
        assertFalse("后端不在场（已降级/未就绪）不能复用", reuse(backendPresent = false))
    }

    @Test
    fun templateInactive_breaksReuse() {
        assertFalse("模板面未生效时该闸不适用（交由 canvas 路径）", reuse(templateActive = false))
    }
}
