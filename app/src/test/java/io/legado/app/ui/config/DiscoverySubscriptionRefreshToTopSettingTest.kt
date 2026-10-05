package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * add-rss-article-refresh-to-top 设置层配对测试。
 *
 * 锁三件事：
 * ① 订阅设置页（Compose `SettingPageSpec`）确有「刷新后回到顶部」开关项且键与开关同源；
 * ② `pref_config_discovery_subscription.xml`（**仅作设置搜索索引**）收录该键 ⇒ 设置可被全局搜索到；
 * ③ 文案**双语同加**（`values/` 英文 base + `values-zh/` 简中）—— 缺一即中文环境回退英文。
 */
class DiscoverySubscriptionRefreshToTopSettingTest {

    private fun fragment(): String =
        SourceFileProbe.sourceText("ui/config/DiscoverySubscriptionConfigFragment.kt")

    private fun prefXml(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/xml/pref_config_discovery_subscription.xml")

    @Test
    fun settingsPageExposesRefreshToTopSwitch() {
        val s = fragment()
        assertTrue(
            "订阅设置页必须新增开关项且键取自 PreferKey 单源",
            s.contains("SettingSwitchSpec(") && s.contains("key = PreferKey.rssArticleRefreshToTop")
        )
        assertTrue(
            "开关初值必须读同一键（默认 true = 老模式回顶）",
            s.contains("booleanSetting(PreferKey.rssArticleRefreshToTop, true)")
        )
        assertTrue(
            "开关写回必须经 updateBooleanSetting",
            s.contains("updateBooleanSetting(PreferKey.rssArticleRefreshToTop, it)")
        )
        assertTrue(
            "标题与摘要必须引用新增文案资源",
            s.contains("R.string.rss_article_refresh_to_top") &&
                s.contains("R.string.rss_article_refresh_to_top_summary")
        )
    }

    @Test
    fun searchIndexXmlContainsKey() {
        val xml = prefXml()
        assertTrue(
            "搜索索引 XML 必须收录该键（否则全局设置搜索不到）",
            xml.contains("android:key=\"rssArticleRefreshToTop\"")
        )
        assertTrue(
            "索引项默认值须与 AppConfig 默认一致（true）",
            xml.contains("android:defaultValue=\"true\"")
        )
        assertTrue(
            "索引项标题须指向同一文案（键名/文案双处一致）",
            xml.contains("android:title=\"@string/rss_article_refresh_to_top\"")
        )
    }

    @Test
    fun stringsAddedInBothBaseAndChinese() {
        val base = SourceFileProbe.resValuesText("strings.xml")
        assertTrue(
            "英文 base 必须含开关标题",
            base.contains("<string name=\"rss_article_refresh_to_top\">")
        )
        assertTrue(
            "英文 base 必须含开关摘要",
            base.contains("<string name=\"rss_article_refresh_to_top_summary\">")
        )
        val zh = SourceFileProbe.sourceTextByPath("src/main/res/values-zh/strings.xml")
        assertTrue(
            "简体中文必须同加开关标题（否则中文环境回退英文）",
            zh.contains("<string name=\"rss_article_refresh_to_top\">")
        )
        assertTrue(
            "简体中文必须同加开关摘要",
            zh.contains("<string name=\"rss_article_refresh_to_top_summary\">")
        )
    }
}
