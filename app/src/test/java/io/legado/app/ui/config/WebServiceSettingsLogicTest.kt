package io.legado.app.ui.config

import io.legado.app.web.TokenManager
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 一期 §6 纯逻辑回归（`WebServiceSettingsLogic`）。
 *
 * 这些判据直接决定用户看到什么，且**不需要 Android 运行时** ⇒ 用真实调用而非源码文本断言，
 * 是"改行为必被拦"的最强证据形态。
 */
class WebServiceSettingsLogicTest {

    // ---------------------------------------------------------------- S2 首启引导（任务 6.3 / SC-1-18）

    @Test
    fun firstLaunchGuide_showsOnlyWhenServiceRunningAndFlagUnset() {
        assertTrue(
            "服务运行中且首启标志未置位 ⇒ 首次要弹",
            WebServiceSettingsLogic.shouldShowFirstLaunchGuide(
                firstLaunchDone = false,
                serviceRunning = true
            )
        )
        assertFalse(
            "标志已置位 ⇒ 二次不弹",
            WebServiceSettingsLogic.shouldShowFirstLaunchGuide(
                firstLaunchDone = true,
                serviceRunning = true
            )
        )
        assertFalse(
            "服务未运行 ⇒ 不弹（引导卡三个动作全部依赖服务在跑，弹了是误导）",
            WebServiceSettingsLogic.shouldShowFirstLaunchGuide(
                firstLaunchDone = false,
                serviceRunning = false
            )
        )
        assertFalse(
            "服务未运行 + 标志已置位 ⇒ 不弹",
            WebServiceSettingsLogic.shouldShowFirstLaunchGuide(
                firstLaunchDone = true,
                serviceRunning = false
            )
        )
    }

    // ---------------------------------------------------------------- 摘要措辞（设置页 / 地址活字牌 / 我的页共用）

    @Test
    fun serviceSummary_prefersAddressWhenRunning() {
        assertEquals(
            "运行中且有地址 ⇒ 显示地址",
            "http://192.168.0.2:1122",
            WebServiceSettingsLogic.serviceSummaryText(
                serviceRunning = true,
                hostAddress = "http://192.168.0.2:1122",
                stoppedText = "已停止",
                pendingText = "正在获取地址…"
            )
        )
    }

    @Test
    fun serviceSummary_neverRendersBlankWhenAddressNotReady() {
        // 回归护栏：旧实现（`if (isRun) hostAddress else desc`）在此分支会渲染成**空行**
        assertEquals(
            "运行中但地址未就绪 ⇒ 必须给占位文案，不得为空",
            "正在获取地址…",
            WebServiceSettingsLogic.serviceSummaryText(
                serviceRunning = true,
                hostAddress = "",
                stoppedText = "已停止",
                pendingText = "正在获取地址…"
            )
        )
        assertEquals(
            "空白地址同样按未就绪处理",
            "正在获取地址…",
            WebServiceSettingsLogic.serviceSummaryText(
                serviceRunning = true,
                hostAddress = "   ",
                stoppedText = "已停止",
                pendingText = "正在获取地址…"
            )
        )
    }

    @Test
    fun serviceSummary_fallsBackToStoppedTextWhenServiceOff() {
        assertEquals(
            "未运行 ⇒ 给调用方传入的离线文案（设置页=「已停止」/ 我的页=原离线描述）",
            "已停止",
            WebServiceSettingsLogic.serviceSummaryText(
                serviceRunning = false,
                hostAddress = "http://192.168.0.2:1122",
                stoppedText = "已停止",
                pendingText = "正在获取地址…"
            )
        )
    }

    // ---------------------------------------------------------------- 令牌状态（任务 6.4）

    @Test
    fun tokenStatus_nullOrNonPositiveMeansNeverGenerated() {
        val never = "未生成"
        listOf(null, 0L, -1L).forEach { raw ->
            assertEquals(
                "generatedAt=$raw ⇒ 未生成",
                never,
                WebServiceSettingsLogic.tokenStatusText(raw, never) { "不应被调用" }
            )
        }
    }

    @Test
    fun tokenStatus_formatsWhenGenerated() {
        assertEquals(
            "已生成 ⇒ 交调用方格式化",
            "已生成于 <fmt>",
            WebServiceSettingsLogic.tokenStatusText(1_700_000_000_000L, "未生成") { "已生成于 <fmt>" }
        )
    }

    @Test
    fun generatedAtFormatIsTwoDigitMonthDayAndTime() {
        val text = WebServiceSettingsLogic.formatGeneratedAt(
            millis = 1_700_000_000_000L,
            locale = Locale.CHINA
        )
        // 时区随设备而变 ⇒ 只断言格式（MM-dd HH:mm），不断言具体时刻
        assertTrue("格式应为 MM-dd HH:mm，实际=$text", Regex("""\d{2}-\d{2} \d{2}:\d{2}""").matches(text))
    }

    // ---------------------------------------------------------------- 级别映射（任务 6.4）

    @Test
    fun levelTitlesAreDistinctForAllGeneratableLevels() {
        val levels = WebServiceSettingsLogic.tokenLevelsInDisplayOrder()
        val titles = levels.map { WebServiceSettingsLogic.levelTitleRes(it) }
        assertEquals("三级必须各有标题资源", 3, titles.size)
        assertEquals("三条标题资源不得重复", 3, titles.toSet().size)
        assertNotEquals("readonly 与 admin 不得同资源", titles[0], titles[2])
    }

    @Test
    fun noneLevelIsNotRenderable() {
        val thrown = runCatching { WebServiceSettingsLogic.levelTitleRes(TokenManager.Level.NONE) }
            .exceptionOrNull()
        assertTrue("NONE 不是可渲染级别，应判为编程错误，实际=$thrown", thrown is IllegalStateException)
    }

    @Test
    fun displayOrderIsAscendingByPrivilege() {
        val levels = WebServiceSettingsLogic.tokenLevelsInDisplayOrder()
        assertEquals(
            "展示顺序 = 权限升序（readonly → manage → admin）",
            listOf(TokenManager.Level.READONLY, TokenManager.Level.MANAGE, TokenManager.Level.ADMIN),
            levels
        )
        assertEquals(
            "且必须与 ordinal 升序一致（WebAuth.allow 依赖 ordinal 比较）",
            levels.map { it.ordinal }.sorted(),
            levels.map { it.ordinal }
        )
    }
}
