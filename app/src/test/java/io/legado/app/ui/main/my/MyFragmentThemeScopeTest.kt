package io.legado.app.ui.main.my

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`MyFragment`（「我的」页内容宿主）主题作用域守护。
 *
 * 该页顶栏由 `MainTopBarView`（View）承担，Compose 宿主仅承载内容区 `MySettingsScreen`；
 * 原 `binding.composeHost.setContent` 无任何主题作用域 ⇒ 内容区（含设置行图标/开关/主题模式行）
 * 在夜间/主题包下回落 M3 默认色板；现上提为唯一主题入口 `LegadoTheme`。
 */
class MyFragmentThemeScopeTest {

    private val rel = "io/legado/app/ui/main/my/MyFragment.kt"

    @Test
    fun `内容根已上提 LegadoTheme（顶层主题作用域）`() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(rel)
        val src = ComposeThemeScopeAssert.sourceText(rel)
        assertEquals(
            "不得再以 LegadoComposeTheme 作内容根",
            0,
            Regex("LegadoComposeTheme\\s*\\{").findAll(src).count()
        )
        assertEquals(
            "内容宿主入口必须唯一（多点 setContent 会绕过作用域守护）",
            1,
            Regex("(?<![A-Za-z0-9_])setContent\\s*\\{").findAll(src).count()
        )
    }
}
