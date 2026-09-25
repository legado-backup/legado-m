package io.legado.app.ui.widget.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2（2026-09-25）：`LegadoMiuixChoiceRow` 的**图标源三态契约**结构不变量（JVM 可跑）。
 *
 * 背景（实测缺口，file:line 已核）：`MenuAction` 是**双源**模型（`icon: ImageVector?` 与
 * `iconRes: Int?` 二选一），而本组件原只接 `leadingIcon: ImageVector?` ⇒ 走
 * `AppDropdownMenu` 渲染的 **iconRes-only 动作静默无图标**（顶栏一级路径
 * `AppManagementScaffold` 已正确，缺口只在**溢出菜单**路径）。
 *
 * 修法 = 组件补 `leadingIconRes` 参数 + 与 ImageVector 分支**同尺寸同间距**的
 * `painterResource` 分支；`AppDropdownMenu` 侧补透传（见同批
 * `MenuActionIconResPassthroughTest`）。
 *
 * 本测试锁死四件事，防回归（只写文档的约束一律失效）：
 *   ①参数必须是 `leadingIconRes: Int? = null`（可空 + 默认值 ⇒ 既有调用点零改动）
 *   ②必须存在 `painter = painterResource(leadingIconRes)` 分支（不是只有 imageVector）
 *   ③三态**优先级顺序**：`leadingIcon` > `leadingIconRes` > `leadingIconName`（不得颠倒）
 *   ④drawable 分支的**尺寸/间距与 ImageVector 分支逐字一致**（22dp + 9/12dp），避免「图标有了但大小不对」
 */
class LegadoMiuixChoiceRowIconSourceTest {

    private val page = "ui/widget/compose/LegadoMiuixComponents.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    /** 注释断言专用：`sourceText` 会剥掉 `//` 行与 KDoc 星号行 ⇒ 断言注释内容必须用原文（§8-⑤）。 */
    private fun raw(): String = SourceFileProbe.rawText(page)

    @Test
    fun leadingIconResParamIsOptional() {
        val s = src()
        assertTrue(
            "必须提供可空且有默认值的 leadingIconRes 形参（既有调用点零改动）",
            s.contains("leadingIconRes: Int? = null")
        )
        assertTrue(
            "参数须带用途注释（缺失会让后人误以为是冗余参数）",
            raw().contains("iconRes-only 动作静默无图标")
        )
    }

    @Test
    fun drawableBranchRendersViaPainterResource() {
        val s = src()
        assertTrue(
            "必须有 drawable 源渲染分支（painter = painterResource(leadingIconRes)）",
            s.contains("painter = painterResource(leadingIconRes)")
        )
        assertTrue("painterResource 必须已导入", s.contains("import androidx.compose.ui.res.painterResource"))
        assertFalse(
            "drawable 分支不得误用 imageVector 参数（类型不符，且说明没走新分支）",
            s.contains("imageVector = leadingIconRes")
        )
    }

    @Test
    fun precedenceIsIconThenIconResThenIconName() {
        val s = src()
        val iIcon = s.indexOf("if (leadingIcon != null)")
        val iRes = s.indexOf("else if (leadingIconRes != null)")
        val iName = s.indexOf("leadingIconName?.let")
        assertTrue("三个图标分支必须都存在（icon=$iIcon, iconRes=$iRes, name=$iName）", iIcon > 0 && iRes > 0 && iName > 0)
        assertTrue("优先级必须为 icon → iconRes → iconName（不得颠倒）", iIcon < iRes && iRes < iName)
    }

    @Test
    fun drawableBranchMatchesImageVectorGeometry() {
        val s = src()
        // 逐字对齐 ImageVector 分支的 22dp 图标 + compact 9dp / 非 compact 12dp 间距
        val resBranchStart = s.indexOf("else if (leadingIconRes != null)")
        val resBranch = s.substring(resBranchStart, minOf(resBranchStart + 600, s.length))
        assertTrue("drawable 分支图标尺寸必须为 22dp（与 ImageVector 分支一致）", resBranch.contains("Modifier.size(22.dp)"))
        assertTrue(
            "drawable 分支间距必须与 ImageVector 分支同口径（compact 9dp / 常规 12dp）",
            resBranch.contains("if (compact) 9.dp else 12.dp")
        )
        assertTrue(
            "drawable 分支 tint 口径必须一致（tint 覆盖 → 否则继承内容色）",
            resBranch.contains("tint = tint ?: LocalContentColor.current")
        )
    }
}