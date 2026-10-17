package io.legado.app.data.entities

import android.app.Application
import io.legado.app.data.entities.rule.ReviewRule
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * 书源「段评（书评）规则」DB 转换器**数据保真**护栏。
 *
 * 背景：`BookSource.Converters` 里 `stringToReviewRule` 与 `reviewRuleToString` 曾被**桩死**
 * （分别 `= null` / `= "null"`）。这两个函数带 `@TypeConverter`，由 **Room 生成代码调用**，
 * 因此在源码里**看不到调用点**（用"零引用"判据会误判成死代码）——实际后果是：
 * 书源 `ruleReview` 在 DB 持久化时**写入字面量 `null`、读出恒 `null`** ⇒
 * 导入/导出/备份/保存路径中段评规则**被静默丢弃**。
 *
 * 本文件按 sibling 语义（`GSON.toJson` / `GSON.fromJsonObject().getOrNull()`）锁定往返保真；
 * 桩形态下 `roundTrip_keepsAllFields` 与 `storedJsonIsNotLiteralNull` **先红**。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class BookSourceReviewRuleConverterTest {

    private val conv = BookSource.Converters()

    private val full = ReviewRule(
        reviewUrl = "u", avatarRule = "a", contentRule = "c", postTimeRule = "t",
        reviewQuoteUrl = "q", voteUpUrl = "vu", voteDownUrl = "vd",
        postReviewUrl = "pr", postQuoteUrl = "pq", deleteUrl = "d",
    )

    @Test
    fun roundTrip_keepsAllFields() {
        val json = conv.reviewRuleToString(full)
        val back = conv.stringToReviewRule(json)
        assertEquals("段评规则经 DB 转换器往返不得丢字段", full, back)
    }

    @Test
    fun storedJsonIsNotLiteralNull() {
        val json = conv.reviewRuleToString(full)
        assertNotEquals("不得写入字面量 null（否则读出恒 null ⇒ 静默丢数据）", "null", json)
        assertTrue("序列化结果应含段评 URL 字段名", json.contains("reviewUrl"))
    }

    @Test
    fun legacyLiteralNullStillReadsAsNull() {
        // 历史行里可能已存了字面量 null ⇒ 修复后必须仍能安全读回 null（向后兼容，不清库）
        assertNull(conv.stringToReviewRule("null"))
        assertNull(conv.stringToReviewRule(null))
    }

    @Test
    fun nullRuleWritesJsonNull() {
        assertEquals("null", conv.reviewRuleToString(null))
    }

    /**
     * 段评编辑链**恢复**（2026-10-17 用户裁定）后，实体入口 `getReviewRule()` 的语义：
     * 与 `getContentRule` 同构——未配置时新建空规则并**挂回实体**（保证编辑页保存链可回填），
     * 且二次调用幂等返回同一实例。
     */
    @Test
    fun getReviewRule_createsAndPinsThenIdempotent() {
        val source = BookSource()
        assertNull("初始无段评规则", source.ruleReview)
        val first = source.getReviewRule()
        assertEquals("新建规则各字段为空默认", "", first.reviewUrl.orEmpty())
        assertSame("必须挂回实体（供保存链回填）", first, source.ruleReview)
        assertSame("二次调用必须返回同一实例（幂等）", first, source.getReviewRule())
    }
}
