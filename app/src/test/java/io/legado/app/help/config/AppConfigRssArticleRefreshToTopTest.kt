package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * add-rss-article-refresh-to-top 配置层配对测试。
 *
 * `AppConfig` 的取值依赖 `appCtx`（Android Context）⇒ 无法在 JVM 单测中直接实例化，
 * 故按本仓既有惯例（如 `AppConfigMangaDefaultsTest`）以**源码契约**固化：
 * 属性存在 + 默认值为老模式（true）+ 读写落到同一 PreferKey。
 */
class AppConfigRssArticleRefreshToTopTest {

    private fun appConfig(): String = SourceFileProbe.sourceText("help/config/AppConfig.kt")

    @Test
    fun propertyExists() {
        assertTrue(
            "必须新增 rssArticleRefreshToTop 属性",
            appConfig().contains("var rssArticleRefreshToTop: Boolean")
        )
    }

    @Test
    fun defaultIsOldModeScrollToTop() {
        assertTrue(
            "默认值必须为 true（老模式 = 刷新后回到顶部）",
            appConfig().contains("getPrefBoolean(PreferKey.rssArticleRefreshToTop, true)")
        )
    }

    @Test
    fun writeBackUsesSameKey() {
        assertTrue(
            "写回必须落同一键（防设置项写入与读取键不一致导致静默失联）",
            appConfig().contains("putPrefBoolean(PreferKey.rssArticleRefreshToTop, value)")
        )
    }
}
