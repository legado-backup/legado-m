package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读页入口引导契约（2026-10-12 用户反馈「我现在都不知道你这个功能入口在哪，怎么用」配对）。
 *
 * 为什么锁定这两条：
 * ①帮助内容新增了入口说明，但 `isLastVersion` **只在版本变化时**才重弹一次 ⇒ 不升版本，
 *   老用户（含抱怨"找不到入口"的这批）**永远不会看到**新增说明（等于没写）；
 * ②帮助必须写明**入口路径与适用范围**，否则"找不到入口 / 不知道支持哪些格式"的原症状会原样复发。
 */
class ReadMenuHelpGuidanceTest {

    private val help = java.io.File("src/main/assets/web/help/md/readMenuHelp.md")

    @Test
    fun `阅读页帮助必须写明模板入口路径与适用范围`() {
        assertTrue("帮助资产缺失：${help.absolutePath}", help.isFile)
        val text = help.readText()
        assertTrue("必须有「阅读页模板」章节", text.contains("阅读页模板"))
        assertTrue("必须给出面板内的入口路径", text.contains("「界面」") && text.contains("「页面模板」"))
        assertTrue("必须写明即时生效（用户反馈过'设置后看不到变化'）", text.contains("立即生效"))
        assertTrue("必须写明适用范围与 EPUB 不适用", text.contains("出版 EPUB 不适用"))
        assertTrue("必须写明可导入 ZIP 主题包（用户反馈过'只支持 json'）", text.contains("ZIP"))
    }

    @Test
    fun `帮助内容更新必须同步提升版本否则老用户永不再见`() {
        val source = SourceFileProbe.sourceText("help/config/LocalConfig.kt")
        assertTrue(
            "readMenuHelpVersion 必须已升到 v2（帮助已新增「阅读页模板」章节）",
            source.contains("isLastVersion(2, \"readMenuHelpVersion\"")
        )
    }
}