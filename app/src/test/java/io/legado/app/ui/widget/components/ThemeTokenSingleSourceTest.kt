package io.legado.app.ui.widget.components

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 标签/芯片/徽标取色单源不变量回归测试（B7 R28/R31，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 为什么是「源码不变量」而不是渲染断言：本批缺陷是**取色来源**错误（用了 M3 派生键、直读非
 * Compose 状态、同语义多套口径、刷新依赖宿主手动补），而本项目单测无 Robolectric
 * （`app/build.gradle` 设 `unitTests.returnDefaultValues = true` ⇒ android.graphics 全桩化，
 * 无法对真实颜色做渲染断言）。故按**结构不变量**形态固化——与 `ai_tests/testsets/regressions`
 * 中 invariant 型样本同思路：把「曾经失守的具体写法」变成永久可断言的禁令。
 *
 * ⚠ 断言必须跑在**去注释后的代码文本**上（[code]）：「改造前如何」的说明性注释会合法地
 * 出现旧符号名，若对整文件断言会产生误报（首次运行即踩到）。
 */
class ThemeTokenSingleSourceTest {

    private fun locate(relUnderAppPackage: String): File {
        val rel = "src/main/java/io/legado/app/$relUnderAppPackage"
        // Gradle 单测工作目录可能是 app/ 或仓库根，逐一尝试
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        return candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
    }

    /** 去掉纯注释行后的代码文本（KDoc 的星号续行、双斜杠行注释、块注释起始行）。 */
    private fun code(relUnderAppPackage: String): String =
        locate(relUnderAppPackage).readLines()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("*") || t.startsWith("//") || t.startsWith("/*")
            }
            .joinToString("\n")

    private fun src(relUnderAppPackage: String): String = locate(relUnderAppPackage).readText()

    /** R28：`TagChip` 底必须走 chip 面 token，且不得回退到 settings 行的 `rowPressed`。 */
    @Test
    fun tagChip_usesChipFaceToken() {
        val text = code("ui/widget/components/TagChip.kt")
        assertTrue("TagChip 底应取面 token tabBackgroundColor", text.contains("tabBackgroundColor"))
        assertFalse("TagChip 底不得回退到 rowPressed", text.contains("rowPressed"))
    }

    /** R28：`BadgeDot` 底必须走 danger 语义色单源；R31：自建亮度公式已删除并改用 contrastOn。 */
    @Test
    fun badgeDot_usesDangerSingleSourceAndContrastSingleSource() {
        val text = code("ui/widget/components/BadgeDot.kt")
        assertTrue("BadgeDot 底应走 AppUiTokens.danger", text.contains("AppUiTokens.danger"))
        assertTrue("BadgeDot 字色应走 contrastOn 单源", text.contains("contrastOn("))
        assertFalse("自建兜底 badgeTextBright 应已删除", src("ui/widget/components/BadgeDot.kt").contains("badgeTextBright"))
    }

    /** R28：`AppFilterChip` 与 View 侧同语义 chip 必须同取 tabBackgroundColor；且不得直读非 Compose 状态。 */
    @Test
    fun appFilterChip_convergedToChipTokenAndComposeSafe() {
        val text = code("ui/widget/components/AppFilterChip.kt")
        assertTrue("AppFilterChip 底应取 tabBackgroundColor", text.contains("tabBackgroundColor"))
        assertFalse("AppFilterChip 底不得再取 rowPressed", text.contains("rowPressed"))
        assertFalse(
            "不得直读 AppConfig.isNightTheme（非 Compose 状态 ⇒ 宿主未包主题时不刷新）",
            text.contains("AppConfig.isNightTheme")
        )
    }

    /** R28/AD-14：M3 error 键必须收敛到 danger 语义色单源（改造前为硬编码浅红/深红字面值）。 */
    @Test
    fun themeSpec_errorUsesDangerSingleSource() {
        val text = code("ui/widget/components/ThemeSpec.kt")
        assertTrue("ThemeSpec.error 应取 AppSemanticColors.Danger", text.contains("AppSemanticColors.Danger"))
        assertTrue("onError 应走 contrastOn", text.contains("val onError = contrastOn("))
    }

    /** R31：Compose 侧 contrastOn 必须转发到 View/Compose 共用真值，不得就地重写亮度判据。 */
    @Test
    fun contrastOn_delegatesToSharedSingleSource() {
        val text = code("ui/widget/components/ThemeSpec.kt")
        assertTrue("contrastOn 应转发 ColorUtils.contrastOnColor", text.contains("contrastOnColor("))
    }

    /** R31：View 侧标签栏的对比度兜底必须走同一单源（原三套并存之一）。 */
    @Test
    fun roundedTagBarView_contrastFallbackUsesSingleSource() {
        val text = code("ui/widget/RoundedTagBarView.kt")
        assertTrue("标签栏对比度兜底应走 contrastOnColor", text.contains("contrastOnColor("))
        assertFalse(
            "regular 风格兜底色不得再用硬编码白色字面值",
            text.contains("Color.WHITE")
        )
    }

    /** R28/J3：`GroupHeader`（曾被设计裁定为复用目标）自身取色必须走面 token，不得用 M3 派生键。 */
    @Test
    fun groupHeader_usesFaceTokensNotM3DerivedKeys() {
        val text = code("ui/widget/components/GroupHeader.kt")
        assertTrue("GroupHeader 应走 palette 面 token", text.contains("AppUiTokens.settingPalette()"))
        assertTrue("计数徽标底应取 chip 面 token", text.contains("tabBackgroundColor"))
    }

    /** R28：组件层 M3 派生键（surfaceVariant / surface / outline）必须收口到面 token。 */
    @Test
    fun componentLayer_convergedOffM3DerivedKeys() {
        val metric = code("ui/widget/components/MetricGrid.kt")
        assertTrue("MetricGrid 底应走 tabBackgroundColor", metric.contains("tabBackgroundColor"))
        assertFalse("MetricGrid 不得再用 surfaceVariant", metric.contains("colorScheme.surfaceVariant"))

        val skeleton = code("ui/widget/components/ShelfGridSkeleton.kt")
        assertTrue("骨架屏底应走 tabBackgroundColor", skeleton.contains("tabBackgroundColor"))
        assertFalse("骨架屏不得再用 surfaceVariant", skeleton.contains("colorScheme.surfaceVariant"))

        val scrollbar = code("ui/widget/components/VerticalScrollbar.kt")
        assertTrue("滚动条应走面 token", scrollbar.contains("tabBackgroundColor") && scrollbar.contains("dividerColor"))
        assertFalse("滚动条不得再用 surface/outline 派生键",
            scrollbar.contains("colorScheme.surface") || scrollbar.contains("colorScheme.outline"))
    }

    /** R31：取色器预设色上的对勾字色必须走对比度兜底单源。 */
    @Test
    fun colorPickerSheet_usesContrastSingleSource() {
        val text = code("ui/widget/components/ColorPickerSheet.kt")
        assertTrue("对勾字色应走 contrastOn 单源", text.contains("contrastOn("))
        assertFalse("不得再自建 isColorLight 黑白推导", text.contains("ColorUtils.isColorLight(preset)"))
    }

    /**
     * R28：分隔线/描边必须走面 token `dividerColor`，不得用 M3 派生键 `outlineVariant`
     * （= `outline.copy(alpha)`，由 B7 收口时实测发现的**规则缺口**，已补入机读禁用集）。
     */
    @Test
    fun dividersUseDividerTokenNotOutlineVariant() {
        for (rel in listOf(
            "ui/widget/components/ColorPickerSheet.kt",
            "ui/widget/components/HighlightStyleSheet.kt",
            "ui/widget/components/AppMenuSheet.kt"
        )) {
            val t = code(rel)
            assertFalse("$rel 不得再用 outlineVariant", t.contains("outlineVariant"))
            assertTrue("$rel 分隔线/描边应走 dividerColor", t.contains("dividerColor"))
        }
    }
}