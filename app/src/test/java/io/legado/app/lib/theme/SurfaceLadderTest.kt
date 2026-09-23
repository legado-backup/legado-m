package io.legado.app.lib.theme

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 面 token「运行时推导」层单测（2026-09-23 用户实证缺陷）。
 *
 * 缺陷：`ui-standards/color.md` §一 声明的三层取色优先级「用户自定义 key → **运行时推导** → R.color 兜底」
 * 中，**中间层缺失** —— 未自定义面时直接落静态 `R.color.background_card`/`background_menu`（固定灰，
 * 与主题背景色无关）⇒ 改主题色时标签 / 芯片 / Tab / 次级表面颜色不跟随
 * （书架、订阅源「标签」布局模式下的标签颜色即此症状；亦违反 K3 判据「T2 自定义主题色态必须变色」）。
 *
 * 不变量：
 * 1) 出厂默认主题（T1 日间 / T4 夜间）阶梯结果与既有静态灰资源一致（±3 色阶）⇒ 观感零变化；
 * 2) 换主题背景色后各面**必然**随之变化（T2 生效）；
 * 3) 阶梯方向正确（日间压暗 / 夜间提亮，且步进单调）。
 */
class SurfaceLadderTest {

    private fun channelDelta(a: Int, b: Int): Int {
        val dr = kotlin.math.abs((a shr 16 and 0xFF) - (b shr 16 and 0xFF))
        val dg = kotlin.math.abs((a shr 8 and 0xFF) - (b shr 8 and 0xFF))
        val db = kotlin.math.abs((a and 0xFF) - (b and 0xFF))
        return maxOf(dr, dg, db)
    }

    // ---- 1) 出厂默认主题零变化 ----
    @Test
    fun t1_dayDefaults_matchLegacyStaticResources() {
        val mdGrey100 = 0xFFF5F5F5.toInt()   // 出厂背景色（colorBackground 默认）
        val mdGrey200 = 0xFFEEEEEE.toInt()   // 旧静态兜底 R.color.background_menu
        val card = SurfaceLadder.derive(mdGrey100, night = false, step = SurfaceLadder.cardStep(false))
        val secondary =
            SurfaceLadder.derive(mdGrey100, night = false, step = SurfaceLadder.secondaryStep(false))
        assertEquals("日间卡片面必须等于出厂背景色（= 旧 background_card）", mdGrey100, card)
        assertTrue(
            "日间次级面必须≈旧 background_menu(#EEEEEE)，实际=${Integer.toHexString(secondary)}",
            channelDelta(secondary, mdGrey200) <= 3
        )
    }

    @Test
    fun t4_nightDefaults_matchLegacyStaticResources() {
        val mdGrey900 = 0xFF212121.toInt()   // 出厂夜间背景色
        val mdGrey850 = 0xFF303030.toInt()   // 旧 background_card 夜间值
        val mdGrey800 = 0xFF424242.toInt()   // 旧 background_menu 夜间值
        val card = SurfaceLadder.derive(mdGrey900, night = true, step = SurfaceLadder.cardStep(true))
        val secondary =
            SurfaceLadder.derive(mdGrey900, night = true, step = SurfaceLadder.secondaryStep(true))
        assertTrue(
            "夜间卡片面必须≈旧 background_card(#303030)，实际=${Integer.toHexString(card)}",
            channelDelta(card, mdGrey850) <= 3
        )
        assertTrue(
            "夜间次级面必须≈旧 background_menu(#424242)，实际=${Integer.toHexString(secondary)}",
            channelDelta(secondary, mdGrey800) <= 3
        )
    }

    // ---- 2) 随主题联动（本次修复的核心诉求）----
    @Test
    fun t2_surfaces_followThemeBackgroundColor() {
        val customDay = 0xFFE8D9F5.toInt()
        val customNight = 0xFF3B2A55.toInt()
        val daySecondary =
            SurfaceLadder.derive(customDay, night = false, step = SurfaceLadder.secondaryStep(false))
        val nightSecondary =
            SurfaceLadder.derive(customNight, night = true, step = SurfaceLadder.secondaryStep(true))
        assertNotEquals(
            "换主题背景色后次级面必须改变（否则标签/芯片仍不随主题）",
            0xFFEEEEEE.toInt(),
            daySecondary
        )
        assertNotEquals(0xFF424242.toInt(), nightSecondary)
        // 推导面必须由**主题背景色驱动**：底色的通道高低必须被推导结果保留（色相不漂移）
        assertTrue(
            "日间推导必须保留底色色相（B>R>G）",
            (daySecondary shr 16 and 0xFF) > (daySecondary shr 8 and 0xFF) &&
                (daySecondary and 0xFF) > (daySecondary shr 16 and 0xFF)
        )
        assertTrue(
            "夜间推导必须保留底色色相（B>R>G）",
            (nightSecondary shr 16 and 0xFF) > (nightSecondary shr 8 and 0xFF) &&
                (nightSecondary and 0xFF) > (nightSecondary shr 16 and 0xFF)
        )
        // 通道级单调依赖：底色某通道更高 ⇒ 推导结果同通道也更高（证明由主题驱动而非常量）
        val lowGreen = SurfaceLadder.derive(0xFF302010.toInt(), night = true, step = 2)
        val highGreen = SurfaceLadder.derive(0xFF304010.toInt(), night = true, step = 2)
        assertTrue(
            "推导结果必须随底色通道单调变化",
            (highGreen shr 8 and 0xFF) > (lowGreen shr 8 and 0xFF)
        )
    }

    // ---- 3) 阶梯方向与单调性 ----
    @Test
    fun ladder_directionAndMonotonicity() {
        val day = 0xFFF5F5F5.toInt()
        val night = 0xFF212121.toInt()
        val day1 = SurfaceLadder.derive(day, night = false, step = 1)
        val day2 = SurfaceLadder.derive(day, night = false, step = 2)
        val night1 = SurfaceLadder.derive(night, night = true, step = 1)
        val night2 = SurfaceLadder.derive(night, night = true, step = 2)
        assertTrue("日间必须压暗", day1 < day)
        assertTrue("日间阶梯单调（步进越大越暗）", day2 < day1)
        assertTrue("夜间必须提亮", night1 > night)
        assertTrue("夜间阶梯单调（步进越大越亮）", night2 > night1)
        assertEquals(
            "step<=0 必须返回背景色本身（卡片面日间口径）",
            day,
            SurfaceLadder.derive(day, night = false, step = 0)
        )
    }

    /**
     * 接线不变量：四个面 token 的兜底必须走「运行时推导」，禁止回退到静态灰资源，
     * 否则本缺陷会静默复发（规范 `ui-standards/color.md` §一 三层优先级的中间层）。
     */
    @Test
    fun surfaceTokenDefaults_mustUseRuntimeDerivation() {
        val rel = "src/main/java/io/legado/app/lib/theme/ThemeUiPalette.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val file = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        val code = file.readLines()
            .filterNot { it.trimStart().startsWith("*") || it.trimStart().startsWith("//") }
            .joinToString("\n")

        listOf(
            "themeCardColorOrDefault",
            "themeMutedColorOrDefault",
            "themeTabBackgroundColorOrDefault",
            "themeSearchFieldBackgroundColorOrDefault"
        ).forEach { fn ->
            val start = code.indexOf("fun Context.$fn(")
            assertTrue("未定位到 $fn", start >= 0)
            val body = code.substring(start, code.indexOf("\n}", start))
            assertTrue("$fn 必须走运行时推导 deriveSurfaceColor", body.contains("deriveSurfaceColor"))
            assertTrue(
                "$fn 不得回退静态灰资源（background_card/background_menu）",
                !body.contains("R.color.background_card") && !body.contains("R.color.background_menu")
            )
        }
    }
}