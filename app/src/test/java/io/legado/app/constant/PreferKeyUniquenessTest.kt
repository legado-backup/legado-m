package io.legado.app.constant

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 配置键唯一性不变量测试。
 *
 * 为什么值得测：`PreferKey` 里所有键最终落到同一个 SharedPreferences 文件，
 * **两个不同常量若取同一字符串值**（复制粘贴/改名遗漏）会互相覆盖 —— 表现为
 * 「改 A 设置却影响 B」的静默串扰，且编译期无任何提示。此处把该不变量固化为断言。
 *
 * 本次连带覆盖：B1·R5 新增 `pageTurnAnimSpeed` 键的登记（键名与注释齐备）。
 */
class PreferKeyUniquenessTest {

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/constant/PreferKey.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun allPrefKeysHaveUniqueStringValues() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toList()
        assertTrue("应解析出足量配置键（当前 ${pairs.size}）", pairs.size > 300)

        val byValue = pairs.groupBy({ it.second }, { it.first })
        val dup = byValue.filter { it.value.size > 1 }
        assertTrue(
            "存在取同一字符串值的配置键（会造成设置串扰）：" +
                dup.entries.joinToString("; ") { "${it.key} <- ${it.value}" },
            dup.isEmpty()
        )
    }

    @Test
    fun r5PageTurnAnimSpeedKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("pageTurnAnimSpeed", pairs["pageTurnAnimSpeed"])
    }

    /** B3 新增键登记（R16 书架未读强调）。未登记即编译不过，此处固化**取值**防改名漏改。 */
    @Test
    fun b3BookshelfUnreadEmphasisKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("bookshelfUnreadEmphasis", pairs["bookshelfUnreadEmphasis"])
    }

    /**
     * 主题失守修复配套（2026-09-24）：两个「首装标志」**必须分开**。
     *
     * 事故背景：`theme_first_install_done` 的语义是「本机为全新安装」（迁移后长期为 true），
     * 却被当成「已完成首装」用 ⇒ 每次启动重复套用外观套件、把用户主题还原。
     * 若两者将来被合并/取同值，该缺陷会立刻复发 ⇒ 此处固化「键名与取值都不同」。
     */
    @Test
    fun appearanceKitAutoApplyFlag_isDistinctFromThemeFirstInstallDone() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        val autoApply = pairs["appearanceKitAutoApplyDone"]
        val firstInstall = pairs["themeFirstInstallDone"]
        assertEquals("appearanceKitAutoApplyDone", autoApply)
        assertEquals("theme_first_install_done", firstInstall)
        assertTrue(
            "两个首装标志语义不同，取值不得相同（否则重复套用缺陷复发）",
            autoApply != firstInstall
        )
    }

    /** B4 新增键登记（R18 书源查询短时缓存开关）。未登记即编译不过，此处固化取值防改名漏改。 */
    @Test
    fun b4SourceQueryCacheKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("sourceQueryCacheEnabled", pairs["sourceQueryCacheEnabled"])
    }

    /**
     * W2 / REQ-14：嗅探赛马化开关登记。
     *
     * 为何固化「键名 == 取值」：该键是赛马的**唯一回滚点**（关闭即回落原串行链），
     * 若被改名而消费点未同步，会出现「设置无效」的静默失联（编译期无提示）。
     */
    @Test
    fun w2SniffRaceKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("sniffRaceEnabled", pairs["sniffRaceEnabled"])
    }

    /**
     * W7 8.2 / REQ-30：文章级离线预取开关登记。
     *
     * 该键被 `AppConfig.imageArticlePrefetch` 与 `pref_config_other.xml` **双处消费**
     * （后者供设置搜索收录）⇒ 改名漏改会造成「设置无效」的静默失联（编译期无提示）。
     */
    @Test
    fun w7ImageArticlePrefetchKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("imageArticlePrefetch", pairs["imageArticlePrefetch"])
    }

    /**
     * W8 9.2 / REQ-32：名场面 AI 描述开关登记。
     *
     * 该键被 `AppConfig.aiSceneDescEnabled`、`AiSceneDescService.isAvailable()` 与设置页切换项
     * **三处消费** ⇒ 改名漏改会造成「打标仍走 AI / 设置无效」的静默失联（编译期无提示）。
     */
    @Test
    fun w8SceneDescKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("aiSceneDescEnabled", pairs["aiSceneDescEnabled"])
    }

    /**
     * 四期 §2.1 / REQ-4-110：S7「一键断电」待补吊销标记登记。
     *
     * 该键是「中继离线断电 → 下次连接补吊销」的**唯一开关**，被 `RelayKernel`（读/写）消费
     * ⇒ 改名漏改会造成「补吊销永不触发」的静默失联（编译期无提示）；取值与键名固化为同一口径。
     */
    @Test
    fun s7RelayRevokePendingKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("publicWebRelayRevokePending", pairs["publicWebRelayRevokePending"])
    }
}