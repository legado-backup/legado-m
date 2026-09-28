package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.2 / REQ-32：`AppConfig.aiSceneDescEnabled` 开关的**读写口径与默认值**。
 *
 * 为什么不跑运行期断言：`AppConfig` 依赖 `appCtx`（Application 上下文），JVM 单测无法构造；
 * 本仓既有口径为「对配置读写做源码结构不变量」（见 `SourceQueryCacheSwitchTest` 等同族用例）。
 *
 * 锁三条：
 * ① **默认开**（未写过任何值时须生效，否则新装用户功能静默关闭）；
 * ② 读路径消费同一 `PreferKey`（改名漏改 ⇒ 设置无效且编译期无提示）；
 * ③ 写路径落同一键（防止「读 A 写 B」的静默串扰）。
 */
class AppConfigSceneDescSwitchTest {

    private val src by lazy { SourceFileProbe.sourceText("help/config/AppConfig.kt") }

    @Test
    fun switchIsDeclaredWithDefaultOn() {
        assertTrue(
            "须声明布尔开关属性",
            src.contains("var aiSceneDescEnabled: Boolean")
        )
        assertTrue(
            "默认值必须为 true（新装即生效）",
            src.contains("getPrefBoolean(PreferKey.aiSceneDescEnabled, true)")
        )
    }

    @Test
    fun readAndWriteUseTheSamePreferKey() {
        assertTrue(
            "写路径须落同一键",
            src.contains("putPrefBoolean(PreferKey.aiSceneDescEnabled, value)")
        )
    }

    @Test
    fun switchSitsWithTheSummaryModelItReuses() {
        val summaryAt = src.indexOf("val aiSummaryModelConfig: AiModelConfig?")
        val switchAt = src.indexOf("var aiSceneDescEnabled: Boolean")
        assertTrue("两个落点都应存在", summaryAt > 0 && switchAt > 0)
        assertTrue(
            "名场面描述复用「文章总结」模型 ⇒ 配置项应与其相邻（同族分组）",
            switchAt - summaryAt in 1..900
        )
    }
}
