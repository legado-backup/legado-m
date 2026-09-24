package io.legado.app.lib.theme.view

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `ThemeCheckBox`**程序化构造**路径的结构不变量（JVM 可跑）。
 *
 * 背景（CE 5.2 `activity_rss_source_edit` 换装时暴露）：
 *   原签名 `ThemeCheckBox(context: Context, attrs: AttributeSet)` 的 **attrs 为非空** ⇒ 页面 XML 退役后
 *   若要在代码里建这个组件，只能「伪造 AttributeSet」（如 `Xml.asAttributeSet` 造空 attrs），
 *   这与 XML 膨胀路径**行为不等价**且极易被后人误用。
 *   处置 = 放宽为 `attrs: AttributeSet? = null`（`@JvmOverloads`）：
 *   `AppCompatCheckBox` 的 2 参构造本就接受 null ⇒ 程序化路径可用；XML 路径（attrs 非空）行为一字不变。
 *
 * 本测试锁死三件事，防回归（只写文档的约束一律失效）：
 *   ①构造签名必须保持「attrs 可空 + 默认值」（否则程序化构造再次不可用）
 *   ②组件自身的语义未被削弱（accent tint 在 init 内施加 / 用户操作判定 / 用户态监听接口）
 *   ③仍继承 `AppCompatCheckBox`（换基类会改变主题适配行为）
 */
class ThemeCheckBoxProgrammaticCtorTest {

    private val page = "lib/theme/view/ThemeCheckBox.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun ctorAcceptsNullAttrsWithDefault() {
        val s = src()
        assertTrue(
            "构造必须保持 `@JvmOverloads` + `attrs: AttributeSet? = null`（程序化构造入口）",
            s.contains("@JvmOverloads constructor(") && s.contains("attrs: AttributeSet? = null")
        )
        assertFalse(
            "不得退回非空 attrs 签名（会让程序化构造只能靠伪造 AttributeSet）",
            s.contains("attrs: AttributeSet) : AppCompatCheckBox(context, attrs)")
        )
    }

    @Test
    fun baseClassAndSemanticsPreserved() {
        val s = src()
        assertTrue("必须仍继承 AppCompatCheckBox", s.contains(": AppCompatCheckBox(context, attrs)"))
        assertTrue("accent tint 必须在 init 内施加", s.contains("applyTint(context.accentColor)"))
        assertTrue("用户操作判定标志必须保留", s.contains("isUserAction"))
        assertTrue(
            "用户态勾选监听接口必须保留（与系统回调区分）",
            s.contains("fun setOnUserCheckedChangeListener(")
        )
    }
}