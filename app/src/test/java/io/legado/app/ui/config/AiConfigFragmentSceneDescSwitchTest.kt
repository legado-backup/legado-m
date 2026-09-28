package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.2 / REQ-32：设置页「名场面智能描述」切换项**接线不变量**（防「死配置」）。
 *
 * 背景：本主线已多次实证「只加配置不加入口 = 死配置」（`process-gate-architecture.md` 裸奔清单）。
 * 该开关若不渲染在 AI 配置页，用户无法关闭 AI 描述 ⇒ 与 REQ-32 的「可降级」承诺不符。
 *
 * 锁三条：① 条目渲染落在 AI 配置页；② 走 `PreferKey.aiSceneDescEnabled`（与 AppConfig 同键）；
 * ③ 默认值与 `AppConfig` 一致（true），且副标题说明了降级语义。
 */
class AiConfigFragmentSceneDescSwitchTest {

    private val fragment by lazy { SourceFileProbe.sourceText("ui/config/AiConfigFragment.kt") }

    @Test
    fun switchRowIsRenderedInAiConfigPage() {
        assertTrue(
            "须渲染名场面描述开关（否则为死配置）",
            fragment.contains("PreferKey.aiSceneDescEnabled")
        )
        assertTrue(
            "副标题须说明降级语义（关闭或未配置 AI 时仅存原文片段）",
            fragment.contains("仅存原文片段")
        )
    }

    @Test
    fun switchDefaultMatchesAppConfig() {
        val block = fragment.substringAfter("PreferKey.aiSceneDescEnabled")
        assertTrue(
            "默认值须与 AppConfig 一致（true）",
            block.take(400).contains("defaultValue = true")
        )
    }

    @Test
    fun switchRefreshIsHandled() {
        assertTrue(
            "开关变更须触发本页刷新（与其他开关同口径）",
            fragment.contains("PreferKey.aiSceneDescEnabled -> refreshUi()")
        )
    }
}
