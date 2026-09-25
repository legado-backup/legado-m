package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.6（`navIcon` 生效修正 / AD-TB-09）+ **顶栏图标资产统一铁律** 的契约测试（JVM 可跑）。
 *
 * 事实基线（实施前已机检，file:line 可复核）：
 * · `GlassTopAppBar` 原两个分支（自绘分支与 Material `navigationIcon` 分支）条件都是
 *   `navIcon != null && onNavClick != null`，且图标**恒为** `painterResource(R.drawable.ic_back)` ⇒
 *   **传入的 `navIcon` 被完全忽略**（`LogManageScreen` 选择态的 `Icons.Default.Close` 传了也不显示 = 真缺陷）。
 * · 全仓 `navIcon =` 站点 **54 处**：**52 处**传同一 Material `ArrowBack`、1 处传 `Close`（条件表达式）、
 *   1 处按 `onBack != null` 条件传 `ArrowBack`/`null` ⇒ 「有 `onNavClick` 无 `navIcon`」的宿主数 = **0**
 *   ⇒ 把返回位条件改为「只看 `onNavClick`」对现网**像素零变化**。
 *
 * 修法（本批）：返回位条件收敛为 `onNavClick != null`；图标经 [NavIconSlot] 解析——
 * 未传或传「默认返回」（Material `ArrowBack`）⇒ 归一为项目资产 `ic_back`；其余图标按传入值渲染。
 * **为何归一**：若改成「凡传即生效」，52 处会统一切到 Material 粗线资产，违反资产统一铁律。
 *
 * 本测试锁死四件事，防回归（只写文档的约束一律失效）：
 *   ①返回位只由 `onNavClick` 驱动（旧的双条件门槛不得回流）
 *   ②默认返回必须归一为项目资产 `ic_back`（不得渲染 Material ArrowBack）
 *   ③非默认图标必须按传入值渲染（修缺陷成果不得被回退）
 *   ④全仓 `navIcon` 站点仍满足「只有 ArrowBack / Close / 条件 null 三类」的资产基线
 */
class TopBarNavIconContractTest {

    private val page = "ui/widget/components/GlassTopAppBar.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun backSlotDrivenByOnNavClickOnly() {
        val s = src()
        assertFalse(
            "返回位不得再要求 navIcon 非空（旧双条件门槛会吞掉 navIcon 生效修正）",
            s.contains("if (navIcon != null && onNavClick != null)")
        )
        val driven = Regex("if \\(onNavClick != null\\) \\{").findAll(s).count()
        assertTrue(
            "两个渲染分支（自绘 / Material navigationIcon）都须以 onNavClick 驱动返回位（实际 $driven 处）",
            driven >= 2
        )
    }

    @Test
    fun defaultBackIsNormalizedToProjectAsset() {
        val s = src()
        assertTrue("必须有 NavIconSlot 图标解析槽", s.contains("private fun NavIconSlot("))
        assertTrue(
            "默认返回（Material ArrowBack）必须被识别并归一（引用相等判定）",
            s.contains("navIcon !== Icons.AutoMirrored.Filled.ArrowBack")
        )
        assertTrue(
            "归一后必须渲染项目资产——顶栏包 §1.1 起改为**契约取值** `TopBarConfig.Icons.navBack`（禁写死 R.drawable）",
            s.contains("painterResource(TopBarConfig.Icons.navBack)")
        )
        assertFalse(
            "不得在分支内直接硬写 ic_back（会重新退回「忽略 navIcon」的旧实现）",
            s.contains("painter = painterResource(R.drawable.ic_back),\n                                    contentDescription = null,\n                                    modifier = Modifier.size(actionIcon.dp)")
        )
    }

    @Test
    fun customNavIconRendersAsPassed() {
        val s = src()
        val slotStart = s.indexOf("private fun NavIconSlot(")
        val slot = s.substring(slotStart, minOf(slotStart + 700, s.length))
        assertTrue(
            "非默认图标必须按传入值渲染（imageVector = navIcon）",
            slot.contains("imageVector = navIcon")
        )
        assertTrue(
            "归一理由必须留注释（否则后人会「简化」掉这一步而破坏资产统一）",
            SourceFileProbe.rawText(page).contains("违反「顶栏图标资产统一")
        )
    }

    @Test
    fun defaultBackAssetComesFromContractNotHardcode() {
        // 顶栏包 §1.1（2026-09-25）：Compose 顶栏的返回位资产改由契约取值；
        // 若后人「简化」回 R.drawable 字面量，换资产时会漏改（本包归一化的前提是资产单源）。
        val s = src()
        assertTrue("必须引用契约资产", s.contains("TopBarConfig.Icons.navBack"))
        assertFalse(
            "代码内不得再出现 R.drawable.* 图标硬编码（注释里的历史写法已被 stripComments 剥离）",
            s.contains("R.drawable.")
        )
    }

    @Test
    fun repoNavIconSitesKeepAssetBaseline() {
        val iconSites = mutableListOf<String>()
        SourceFileProbe.mainJavaRoot().walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .forEach { f ->
                SourceFileProbe.stripComments(f.readText()).lines()
                    // 只统计**宿主调用点**：组件内部把 navIcon 透传给 NavIconSlot 的那两行不算（§8-⑤ 同类假阳性）
                    .filter { it.contains("navIcon =") && !it.contains("NavIconSlot(") }
                    .forEach { line -> iconSites += line.trim() }
            }
        assertTrue("navIcon 站点数异常（${iconSites.size}）——扫描口径可能失效", iconSites.size >= 40)
        val weird = iconSites.filterNot { line ->
            line.contains("Icons.AutoMirrored.Filled.ArrowBack") ||
                line.contains("Icons.Default.Close") ||
                line.contains("else null")
        }
        assertTrue(
            "除「默认返回 / 选择态 Close / 条件 null」外的 navIcon 传参需显式评审（新增图标资产须走登记）：$weird",
            weird.isEmpty()
        )
    }
}