package io.legado.app.ui.book.read.epub.loading

import io.legado.app.help.config.EpubLoadingTemplate
import io.legado.app.help.config.Scene
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 首屏模板**几何/排版纯函数**单测（reader-theme-family 3.12 配对）。
 *
 * 为什么这些算术必须被钉住：插画比例、insets 夹取、文字缩放一旦算错，真机表现是
 * 「插画被拉扁 / 首屏被刘海吃掉半屏 / 题记被裁一半」——都属于"看一眼以为没事、换个设备就崩"的类别，
 * 只能在纯函数层预先证明。
 */
class LoadingTemplateChromeTest {

    @Test
    fun `宽屏判定按 dp 与宽高比双条件`() {
        // 本机模拟器实例（1600x1000 / density≈1.875）＝宽屏
        assertTrue("横屏大屏应判宽屏", LoadingTemplateChrome.isWide(1600, 1000, 1.875f))
        // 竖屏手机（1080x1920 / density=3）
        assertFalse("竖屏应判非宽屏", LoadingTemplateChrome.isWide(1080, 1920, 3f))
        // 足够宽但接近方形（宽高比 1.1 < 1.25）⇒ 不判宽屏
        assertFalse("宽高比不足不得判宽屏", LoadingTemplateChrome.isWide(1200, 1100, 1f))
        // 窄屏（360dp 宽）
        assertFalse("窄屏不判宽屏", LoadingTemplateChrome.isWide(360, 200, 1f))
        // 非法入参
        assertFalse(LoadingTemplateChrome.isWide(0, 100, 1f))
        assertFalse(LoadingTemplateChrome.isWide(100, 100, 0f))
    }

    @Test
    fun `insets 正常值直通 越界值被夹取`() {
        val normal = LoadingTemplateChrome.clampInsets(20, 20, 40, 40, 1000, 800)
        assertNotNull(normal)
        assertEquals(20, normal!!.left)
        assertEquals(40, normal.bottom)

        // 单侧超大（如折叠屏悬停）⇒ 夹到上界
        val huge = LoadingTemplateChrome.clampInsets(900, 900, 700, 700, 1000, 800)
        assertNotNull(huge)
        assertTrue("左侧须夹到 40% 以内", huge!!.left <= (1000 * LoadingTemplateChrome.INSET_MAX_WIDTH_RATIO).toInt())
        assertTrue("上侧须夹到 35% 以内", huge.top <= (800 * LoadingTemplateChrome.INSET_MAX_HEIGHT_RATIO).toInt())
        assertTrue("夹取后内容区必须为正", 1000 - huge.width > 0 && 800 - huge.height > 0)

        // 双侧各自都没越界但相加超过半屏 ⇒ 按比例回缩（内容区恒为正）
        val both = LoadingTemplateChrome.clampInsets(390, 390, 270, 270, 1000, 800)
        assertNotNull(both)
        assertTrue("双侧合计不得超过半屏", both!!.width <= 500 && both.height <= 400)
        assertTrue("回缩后各侧仍非负", both.left >= 0 && both.right >= 0 && both.top >= 0 && both.bottom >= 0)

        assertNull("非法视口 ⇒ null（绘制侧据此回落）", LoadingTemplateChrome.clampInsets(0, 0, 0, 0, 0, 0))
        assertNull(LoadingTemplateChrome.clampInsets(0, 0, 0, 0, -10, 100))
    }

    @Test
    fun `插画比例恒定且随 artScale 单调`() {
        val small = LoadingTemplateChrome.artGeometry(1000f, 800f, 0.7f, wide = true)
        val big = LoadingTemplateChrome.artGeometry(1000f, 800f, 1.2f, wide = true)
        assertNotNull(small)
        assertNotNull(big)
        assertEquals("比例恒等于场景基准", Scene.ART_ASPECT, small!!.aspect, 0.0001f)
        assertEquals("比例不随 artScale 变化", Scene.ART_ASPECT, big!!.aspect, 0.0001f)
        assertTrue("artScale 越大插画越大", big.width > small.width)

        // 越界 artScale 被夹取（与模型区间单源）
        val clampedLow = LoadingTemplateChrome.artGeometry(1000f, 800f, 0.1f, wide = true)
        val clampedHigh = LoadingTemplateChrome.artGeometry(1000f, 800f, 5f, wide = true)
        assertEquals(
            "低于下限须夹到下限", small.width, clampedLow!!.width, 0.001f
        )
        assertEquals(
            "高于上限须夹到上限", big.width, clampedHigh!!.width, 0.001f
        )
        assertEquals(
            "夹取仍保持比例", Scene.ART_ASPECT, clampedHigh.aspect, 0.0001f
        )
    }

    @Test
    fun `插画不得溢出可用区且非法入参回落`() {
        val geometry = LoadingTemplateChrome.artGeometry(200f, 120f, 1.2f, wide = false)
        assertNotNull(geometry)
        assertTrue("宽度不得超可用宽", geometry!!.width <= 200f + 0.01f)
        assertTrue("高度不得超可用高", geometry.height <= 120f + 0.01f)
        assertNull("零面积 ⇒ null", LoadingTemplateChrome.artGeometry(0f, 100f, 1f, wide = false))
        assertNull(LoadingTemplateChrome.artGeometry(100f, -1f, 1f, wide = true))
    }

    @Test
    fun `文字缩放只在超宽时收缩且不裁剪`() {
        assertEquals("未超宽 ⇒ 不缩放", 1f, LoadingTemplateChrome.textScale(300f, 400f), 0.0001f)
        val scale = LoadingTemplateChrome.textScale(500f, 400f)
        assertTrue("超宽 ⇒ 缩放小于 1", scale < 1f)
        assertTrue("缩放后不得超出可用宽（不裁剪）", 500f * scale <= 400f + 0.01f)
        assertEquals("非法入参 ⇒ 1", 1f, LoadingTemplateChrome.textScale(0f, 100f), 0.0001f)
    }

    @Test
    fun `基准画幅与模型区间同源`() {
        assertEquals("插画基准宽高比", 336f / 360f, Scene.ART_ASPECT, 0.0001f)
        assertEquals(0.7f, EpubLoadingTemplate.ART_SCALE_RANGE.start, 0.0001f)
        assertEquals(1.2f, EpubLoadingTemplate.ART_SCALE_RANGE.endInclusive, 0.0001f)
    }
}
