package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.3（REQ-32）：选区菜单「加入名场面」的**配置页白名单登记**不变量。
 *
 * 缺陷型（B2.5 划线 / R14 编辑此处 / Q-N4 净化已三次踩过同一坑）：`ContentSelectMenuConfigDialog`
 * 的 `sanitizeActionIds` 白名单由 `actionItems` 派生 —— 新增动作若**未登记**在此，用户在选区菜单
 * 配置页保存一次后该动作会被**静默剔除**、菜单里永久消失（表现「功能做完了但用户看不到」）。
 *
 * 本文件只锁白名单与配置页文案两项；菜单链路其余三处（XML / 常量 / itemId 映射）见
 * `ui/book/read/SceneBookmarkEntryWiringTest`。
 */
class ContentSelectSceneBookmarkActionTest {

    private val configDialog by lazy {
        SourceFileProbe.sourceText("ui/book/read/config/ContentSelectMenuConfigDialog.kt")
    }

    @Test
    fun sceneBookmarkAction_isRegisteredInWhitelist() {
        assertTrue(
            "「加入名场面」必须登记在 actionItems（否则保存配置后会被静默剔除）",
            configDialog.contains("ActionItem(ContentSelectConfig.ACTION_SCENE_BOOKMARK")
        )
        assertTrue(
            "配置页条目文案须有字符串资源",
            configDialog.contains("R.string.scene_bookmark_add")
        )
    }
}
