package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * unify-changelog-and-release 配置层配对测试。
 *
 * `LocalConfig` 依赖 `appCtx`（Android Context）⇒ 无法在 JVM 直接实例化，
 * 按本仓既有惯例（如 `AppConfigRssArticleRefreshToTopTest`）以**源码契约**固化：
 * 属性存在 + 键名常量 + 读写落到同一键。
 */
class AppVersionNamePersistTest {

    private fun localConfig(): String = SourceFileProbe.sourceText("help/config/LocalConfig.kt")

    @Test
    fun propertyExistsWithKeyConstant() {
        val src = localConfig()
        assertTrue(
            "必须新增 appVersionName 属性",
            src.contains("var appVersionName: String")
        )
        assertTrue(
            "必须声明版本名键常量（值须为 appVersionName）",
            src.contains("versionNameKey = \"appVersionName\"")
        )
    }

    @Test
    fun readWriteUseSameKey() {
        val src = localConfig()
        assertTrue(
            "读取须走 versionNameKey 且默认空串",
            src.contains("getString(versionNameKey, \"\")")
        )
        assertTrue(
            "写入须落同一 versionNameKey",
            src.contains("putString(versionNameKey, value)")
        )
    }
}