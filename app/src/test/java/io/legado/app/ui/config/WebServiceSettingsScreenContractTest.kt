package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「Web 服务与 AI 接入」页的**真机缺陷防回归**（2026-09-29 实测沉淀，详见 `../issues-found.md`）。
 *
 * 为何用源码不变量：这两条都是"渲染出来才看得见"的视觉缺陷（按钮与卡面同色 / 重复文案），
 * 单测无法覆盖像素，但**成因是取色与文案的接线错误**，可用源码断言精确锁死。
 */
class WebServiceSettingsScreenContractTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val screen by lazy {
        read("src/main/java/io/legado/app/ui/config/WebServiceSettingsScreen.kt")
    }
    private val strings by lazy { read("src/main/res/values/strings.xml") }
    private val stringsZh by lazy { read("src/main/res/values-zh/strings.xml") }

    @Test
    fun secondaryButtonFaceIsNotTheCardFace() {
        // IF-01：卡面上的次级按钮若沿用 miuix.surfaceVariant（= colors.row，与卡面同色）会完全不可见；
        // 换 rowPressed 亦无效（不透明主题下二者同值）⇒ 终版必须用与卡面必然异值的面 token。
        assertTrue(
            "次级按钮底须换成页面面（与卡面 row 必然异值）",
            screen.contains("palette.miuix.copy(surfaceVariant = palette.settings.page)")
        )
        assertFalse(
            "不得回退到 rowPressed（layoutAlpha=1 时与 row 同值 ⇒ 按钮仍不可见）",
            screen.contains("surfaceVariant = Color(palette.settings.rowPressed)")
        )
    }

    @Test
    fun offStateAddressCardDoesNotRepeatSameText() {
        // IF-02：未开启时标题与副标题不得复用同一句文案
        assertTrue(
            "未开启时副标题须给可操作提示（独立文案键）",
            screen.contains("R.string.web_address_hint_when_off")
        )
        listOf(strings, stringsZh).forEach { file ->
            assertTrue("文案键须存在于两份 strings", file.contains("""name="web_address_hint_when_off""""))
        }
    }

    /** 设置页宿主的**危险动作确认**契约（四期 REQ-4-404 / §2.1 S7）。 */
    private val activity by lazy {
        read("src/main/java/io/legado/app/ui/config/WebServiceSettingsActivity.kt")
    }

    /**
     * 四期 REQ-4-403 / REQ-4-404：令牌生成的"分级确认"不得退化为"一律直接生成"。
     *
     * - readonly = 只读无风险 ⇒ 直接生成；
     * - manage / admin = 写权限 ⇒ **生成前二次确认**（降级即把写权限令牌一键发出去，属安全默认失守）。
     */
    @Test
    fun writeLevelTokens_requireConfirmBeforeGenerate() {
        assertTrue("须存在只读直通分支", activity.contains("if (level == TokenManager.Level.READONLY)"))
        assertTrue(
            "写级令牌生成须走确认弹窗（含专属文案键）",
            activity.contains("R.string.web_token_generate_confirm_title") &&
                activity.contains("R.string.web_token_generate_confirm_message"),
        )
        assertTrue("确认后必须回到真实生成（doGenerateToken）", activity.contains("doGenerateToken(level)"))
        listOf(strings, stringsZh).forEach { file ->
            assertTrue(
                "确认文案键须两份 strings 齐备",
                file.contains("""name="web_token_generate_confirm_title"""") &&
                    file.contains("""name="web_token_generate_confirm_message""""),
            )
        }
    }

    /**
     * 四期 §2.1 S7：一键断电**必须先吊销令牌再停服务/清中继身份**（漏吊销即"假断电"）。
     */
    @Test
    fun shutdownRevokesTokensBeforeKernelShutdown() {
        val revokeAt = activity.indexOf("TokenManager.revokeAll()")
        val shutdownAt = activity.indexOf("RelayKernel.shutdown()")
        assertTrue("设置页须调用令牌全量吊销", revokeAt >= 0)
        assertTrue("设置页须调用内核断电", shutdownAt >= 0)
        assertTrue("令牌吊销必须排在断电之前", revokeAt < shutdownAt)
        assertTrue("断电属危险动作，必须走危险样式确认弹窗", activity.contains("dangerPositive = true"))
    }

    @Test
    fun secondaryButtonsAllUseTheActionPalette() {
        // 所有非主按钮都必须走 actionPalette；漏传会静默退回不可见的 miuix.surfaceVariant
        val buttonCalls = Regex("""LegadoMiuixActionButton\(""").findAll(screen).count()
        val paletteArgs = Regex("""palette = buttons,""").findAll(screen).count()
        assertTrue("本页按钮数应 ≥ 9（地址 1 / 令牌 3 / 引导 4 / 中继 1）", buttonCalls >= 9)
        assertTrue(
            "每个按钮都须用 actionPalette（实际 $paletteArgs / $buttonCalls）",
            paletteArgs >= buttonCalls
        )
    }

    /**
     * 四期 §2.1（S7 一键断电）/ §2.2（帮助入口）/ §3（公网中继卡片）新增区块的**文案与接线**回归。
     *
     * 为何基线化：中文字面量与资源键必须**两份 strings 齐备**，漏一份即英文/繁中环境显示资源键名；
     * 断电按钮若漏 `danger` 会退化成普通按钮 ⇒ 不可逆动作失去视觉警示。
     */
    @Test
    fun relayHelpAndShutdownSections_areFullyWired() {
        val keys = listOf(
            "web_section_relay", "web_relay_state_off", "web_relay_state_paired",
            "web_relay_state_connected", "web_relay_open_settings",
            "web_section_help", "web_help_open",
            "web_shutdown_title", "web_shutdown_summary",
            "web_shutdown_confirm_title", "web_shutdown_confirm_message",
            "web_shutdown_confirm_positive", "web_shutdown_done",
        )
        keys.forEach { key ->
            listOf(strings, stringsZh).forEach { file ->
                assertTrue("文案键 $key 须同时存在于 values 与 values-zh", file.contains("""name="$key""""))
            }
        }
        assertTrue(
            "断电按钮必须标记 danger（红色警示不可逆动作）",
            Regex("""R\.string\.web_shutdown_title[\s\S]{0,300}?danger = true""").containsMatchIn(screen)
        )
        assertTrue(
            "中继卡片须提供跳原中继设置页的按钮",
            screen.contains("R.string.web_relay_open_settings")
        )
    }
}
