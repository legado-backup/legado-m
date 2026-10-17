package io.legado.app.ui.book.source.edit

import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.rule.ReviewRule
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertSame
import org.junit.Test

/**
 * 段评（段落评论）功能**恢复**的护栏（2026-10-17 用户裁定「段评组恢复」）。
 *
 * 背景：段评编辑链此前整体被注释（`BookSource.getReviewRule()`、书源编辑页第 6 Tab 的
 * `reviewEntities` 收集/回填/保存），只留 `ReviewRule` 实体与转换器在跑；随之有 **10 个段评
 * 字符串**长期落在「零引用」清单里待产品裁定。本轮按裁定**恢复**整条编辑链 ⇒ 10 个字符串
 * 全部重新被消费 ⇒ 零引用清点回到 **0**。
 *
 * 本用例双管：①**行为**（`getReviewRule()` 的新建 + 幂等挂回语义）；②**结构 + 反向护栏**
 * （Tab/收集/回填/保存四段接线必须在位；10 个段评字符串**不得**再被当死字符串删除）。
 */
class BookSourceReviewRuleRestoreTest {

    /** 恢复的段评字符串（`values/strings.xml` 必须全部健在，否则功能面文案缺失）。 */
    private val reviewStrings = listOf(
        "rule_review_url", "rule_avatar", "rule_review_content", "rule_post_time", "rule_review_quote",
        "review_vote_up", "review_vote_down", "post_review_url", "post_quote_url", "delete_review_url",
    )

    @Test
    fun `getReviewRule 首次新建并挂回实体 二次返回同一实例`() {
        val source = BookSource()
        assertEquals("初始无段评规则", null, source.ruleReview)
        val first = source.getReviewRule()
        assertNotNull(first)
        assertSame("必须挂回实体（供保存链回填）", first, source.ruleReview)
        val second = source.getReviewRule()
        assertSame("二次调用必须返回同一实例（幂等）", first, second)
        assertEquals("新建规则各字段为空", "", first.reviewUrl.orEmpty())
        assertEquals("实体类型不变", ReviewRule::class.java, source.ruleReview!!::class.java)
    }

    @Test
    fun `书源编辑页四段接线在位`() {
        val src = SourceFileProbe.sourceText("ui/book/source/edit/BookSourceEditActivity.kt")
        listOf(
            "private val reviewEntities: ArrayList<EditEntity> = ArrayList()", // ① 收集容器
            "setText(R.string.review)",                                        // ② 第 7 Tab 入口
            "6 -> reviewEntities",                                             // ② Tab → 编辑项映射
            "val rr = bs.getReviewRule()",                                     // ③ 打开源时回填
            "\"reviewUrl\" -> reviewRule.reviewUrl = it.value",                // ④ 保存：URL 写入
            "\"postQuoteUrl\" -> reviewRule.postQuoteUrl = it.value",          // ④ 保存：其余字段
            "source.ruleReview = reviewRule",                                  // ④ 保存：写回实体
        ).forEach { frag -> assertEquals("编辑链片段必须在位：$frag", true, src.contains(frag)) }
        assertEquals("不得残留注释态收集块", false, src.contains("//        val rr = bs.getReviewRule()"))
        assertEquals("不得残留注释态保存标记", false, src.contains("//        source.ruleReview = reviewRule"))
    }

    @Test
    fun `实体入口已恢复且与内容规则同构`() {
        val src = SourceFileProbe.sourceText("data/entities/BookSource.kt")
        assertEquals("getReviewRule 必须恢复（非注释态）", true, src.contains("fun getReviewRule(): ReviewRule {"))
        assertEquals("与 getContentRule 同构：命中缓存即返回", true, src.contains("ruleReview?.let { return it }"))
        assertEquals("不得残留注释态签名", false, src.contains("//    fun getReviewRule()"))
    }

    @Test
    fun `十个段评字符串必须在位 不得再被当死字符串删除`() {
        val values = SourceFileProbe.resValuesText("strings.xml")
        reviewStrings.forEach { key ->
            assertEquals("段评字符串缺失（功能已恢复 ⇒ 不得再删）：$key", true, values.contains("name=\"$key\""))
        }
    }
}
