package io.legado.app.ui.widget.text

import android.app.Activity
import android.app.Application
import android.content.Context
import android.graphics.drawable.ShapeDrawable
import android.widget.FrameLayout
import androidx.test.core.app.ApplicationProvider
import io.legado.app.lib.theme.ThemeStorePrefKeys
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import splitties.init.injectAsAppCtx

/**
 * B7 · R29 余量「BadgeView 去 init 一次性捕获」的配对测试（Robolectric 行为级）。
 *
 * 缺陷：改造前 `init` 里一次性捕获 `context.accentColor`，此后再无刷新入口 ⇒
 * 主题变更（不重建页面路径）后角标底色停留在旧色。
 * 修复：改为**来源模式**（ACCENT / TAB / EXPLICIT）+ `applyTheme()`，并在 `onAttachedToWindow` 重解析。
 *
 * 本测试同时是 R23 测试底座的**首个行为级用例**（构造真实 View + 真实 SharedPreferences）。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class BadgeViewThemeModeTest {

    private lateinit var context: Context

    private val accentPrefs
        get() = context.getSharedPreferences(ThemeStorePrefKeys.CONFIG_PREFS_KEY_DEFAULT, Context.MODE_PRIVATE)

    private fun setAccent(color: Int) {
        accentPrefs.edit().putInt(ThemeStorePrefKeys.KEY_ACCENT_COLOR, color).commit()
    }

    private fun bgOf(view: BadgeView): Int = (view.background as ShapeDrawable).paint.color

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        // ThemeStore 的伴生对象初始化即读 `appCtx`（splitties 全局应用上下文），
        // 而本测试刻意不加载 `io.legado.app.App`（重初始化）⇒ 需手动注入，否则
        // `ThemeStore.<clinit>` 抛 IllegalStateException: appCtx has not been initialized!
        context.injectAsAppCtx()
    }

    /** ACCENT 模式（默认）：`applyTheme()` 必须重取强调色。 */
    @Test
    fun accentMode_followsAccentChangeOnApplyTheme() {
        val first = 0xFF112233.toInt()
        val second = 0xFFAABBCC.toInt()
        setAccent(first)
        val view = BadgeView(context)
        assertEquals("默认底必须取当前强调色", first, bgOf(view))

        setAccent(second)
        view.applyTheme()
        assertEquals("强调色变更后 applyTheme 必须跟随", second, bgOf(view))
    }

    /** ACCENT 模式下不调 `applyTheme()` 时底色保持旧值（证明「刷新入口」是必要动作）。 */
    @Test
    fun accentMode_keepsOldColorWithoutRefreshCall() {
        val first = 0xFF112233.toInt()
        val second = 0xFFAABBCC.toInt()
        setAccent(first)
        val view = BadgeView(context)

        setAccent(second)
        assertEquals("未调用 applyTheme 时不应自行变化", first, bgOf(view))
    }

    /** `setHighlight(false)` ⇒ TAB 模式：强调色变化不再影响角标底（语义：走 chip 面 token）。 */
    @Test
    fun tabMode_ignoresAccentChange() {
        setAccent(0xFF112233.toInt())
        val view = BadgeView(context)
        view.setHighlight(false)
        val tabColor = bgOf(view)

        setAccent(0xFFAABBCC.toInt())
        view.applyTheme()
        assertEquals("TAB 模式不得被强调色变化影响", tabColor, bgOf(view))
    }

    /** `setHighlight(true)` ⇒ 回到 ACCENT 模式，重新跟随强调色。 */
    @Test
    fun highlightTrue_returnsToAccentMode() {
        setAccent(0xFF112233.toInt())
        val view = BadgeView(context)
        view.setHighlight(false)
        view.setHighlight(true)
        assertEquals("highlight=true 必须回到强调色", 0xFF112233.toInt(), bgOf(view))

        val second = 0xFFAABBCC.toInt()
        setAccent(second)
        view.applyTheme()
        assertEquals("回到 ACCENT 模式后必须重新跟随", second, bgOf(view))
    }

    /** EXPLICIT 模式：宿主显式设色后，主题刷新**不得**覆盖宿主意图。 */
    @Test
    fun explicitMode_ignoresThemeRefresh() {
        setAccent(0xFF112233.toInt())
        val view = BadgeView(context)
        val hostColor = 0xFF00FF00.toInt()
        view.setBackgroundColor(hostColor)
        assertEquals(hostColor, bgOf(view))

        setAccent(0xFFAABBCC.toInt())
        view.applyTheme()
        assertEquals("EXPLICIT 模式必须无视主题刷新", hostColor, bgOf(view))
    }

    /** 公开 `setBackground(dipRadius, color)` 亦登记为 EXPLICIT。 */
    @Test
    fun explicitSetBackground_ignoresThemeRefresh() {
        val view = BadgeView(context)
        val hostColor = 0xFF123456.toInt()
        view.setBackground(8f, hostColor)
        assertEquals(hostColor, bgOf(view))

        setAccent(0xFFAABBCC.toInt())
        view.applyTheme()
        assertEquals("显式 setBackground 后不得被主题刷新覆盖", hostColor, bgOf(view))
    }

    /**
     * 生产路径：视图重新入窗（`onAttachedToWindow`）时必须重解析 ⇒
     * 主题在视图创建之后变更时，重新入窗即可拿到新色。
     */
    @Test
    fun onAttachedToWindow_reResolvesColor() {
        val first = 0xFF112233.toInt()
        val second = 0xFFAABBCC.toInt()
        setAccent(first)

        val activity = Robolectric.buildActivity(Activity::class.java).setup().get()
        val container = FrameLayout(activity)
        val view = BadgeView(activity)
        container.addView(view)
        activity.setContentView(container)
        assertEquals(first, bgOf(view))

        // 模拟「主题变更 + 视图重新入窗」（不重建 View 实例）
        setAccent(second)
        container.removeView(view)
        container.addView(view)
        assertEquals("重新入窗必须重解析底色", second, bgOf(view))
        assertNotEquals("必须与旧值不同（否则说明仍是 init 一次性捕获）", first, bgOf(view))
    }
}
