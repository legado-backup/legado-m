package io.legado.app.ui.main.ai

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N3：`AiProviderConfig` 的余额字段必须以**带默认值**的形式声明。
 *
 * 为什么锁死「默认值」：本仓 AI 配置走 Gson 按属性名序列化（无 `@SerializedName` 短键），
 * 旧偏好里没有该字段 ⇒ 反序列化时缺省值必须存在，否则老用户升级后配置直接解析失败。
 * 同时确认 `@Keep` 仍在（R8 × Gson 泛型签名门禁，AGENTS 规则 7）。
 */
class AiProviderConfigBalanceFieldTest {

    private fun modelSource(): String = SourceFileProbe.sourceText("ui/main/ai/AiConfigModels.kt")

    @Test
    fun providerConfig_declaresBalanceFieldsWithDefaults() {
        val source = modelSource()
        assertTrue(
            "balanceUrl 必须有默认值（旧偏好无该键）",
            source.contains("val balanceUrl: String = \"\"")
        )
        assertTrue(
            "balanceJsonPath 必须有默认值（旧偏好无该键）",
            source.contains("val balanceJsonPath: String = \"\"")
        )
    }

    @Test
    fun providerConfig_staysKeepAnnotated() {
        val source = modelSource()
        val index = source.indexOf("data class AiProviderConfig")
        assertTrue("未找到 AiProviderConfig（口径漂移）", index > 0)
        assertTrue("@Keep 注解缺失（R8 会剥掉反序列化签名）", source.substring(0, index).contains("@Keep"))
    }

    @Test
    fun providerConfig_newFieldsAreAppendedAfterExistingOnes() {
        val source = modelSource()
        val promptCacheIndex = source.indexOf("val promptCache: Boolean = false")
        val balanceIndex = source.indexOf("val balanceUrl: String = \"\"")
        assertTrue("字段顺序改变会让 copy/构造调用点全部错位", balanceIndex > promptCacheIndex)
    }

    @Test
    fun providerConfig_defaultsMatchBlankSemantics() {
        // 默认空串 ⇒ 未配置余额接口；编辑页/查询动作以 isBlank 判定「未填写」
        val config = AiProviderConfig(name = "p", baseUrl = "https://example.com/v1")
        assertEquals("", config.balanceUrl)
        assertEquals("", config.balanceJsonPath)
        assertTrue(config.balanceUrl.isBlank())
    }
}