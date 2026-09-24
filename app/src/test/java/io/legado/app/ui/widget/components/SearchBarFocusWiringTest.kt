package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 组件层「可选扩展」与「单源语义」的接线不变量（CE 5.2 配对测试，2026-09-24）。
 *
 * 本轮对**共享组件**的改动只有一处新增：`SettingsSearchBar` 补
 * `onFocusChanged: ((Boolean) -> Unit)? = null` —— 书源搜索页（`activity_book_search`）换装后
 * 需要承载原 `SearchView.setOnQueryTextFocusChangeListener` 的「聚焦展示搜索历史 / 失焦且
 * 有结果时收起」语义，而页面侧无法自建第二套输入框（同语义必须单源）。
 *
 * 为什么必须在**组件层**锁死（页面测试替代不了）：
 *   ①**默认值必须保持 null** ⇒ 18 处既有调用点零改动（组件层向后兼容是硬约束）；
 *   ②`Modifier.onFocusChanged` **必须排在 `focusRequester` 之前**——焦点观察节点只能看到
 *     其**之后**的焦点目标；顺序颠倒会**静默失效**（不报错、不崩，只是回调永不触发）。
 */
class SearchBarFocusWiringTest {

    private val searchBar = "ui/widget/components/SettingsSearchBar.kt"
    private val filterChip = "ui/widget/components/AppFilterChip.kt"

    private fun searchBarSrc(): String = SourceFileProbe.sourceText(searchBar)

    @Test
    fun optionalFocusCallbackKeepsBackwardCompatibility() {
        val s = searchBarSrc()
        assertTrue(
            "必须提供可选焦点回调参数且默认 null（既有调用点零改动）",
            s.contains("onFocusChanged: ((Boolean) -> Unit)? = null")
        )
        assertTrue(
            "参数必须真实接线（否则是死参数）",
            s.contains("Modifier.onFocusChanged { onFocusChanged(it.isFocused) }")
        )
        assertTrue(
            "条件接线必须保留可空分支",
            s.contains("if (onFocusChanged != null)")
        )
    }

    @Test
    fun focusObserverPrecedesFocusRequester() {
        val s = searchBarSrc()
        val observerIndex = s.indexOf("Modifier.onFocusChanged")
        val requesterIndex = s.indexOf("Modifier.focusRequester(focusRequester)")
        assertTrue("两处接线必须都存在", observerIndex >= 0 && requesterIndex >= 0)
        assertTrue(
            "onFocusChanged 必须排在 focusRequester 之前（否则焦点观察静默失效）",
            observerIndex < requesterIndex
        )
    }

    /** chip 语义的 Compose 单源实现（原 View 侧同语义实现已随 CE 5.2 删除）。 */
    @Test
    fun filterChipStaysSingleSourceForChipSemantics() {
        val chip = SourceFileProbe.sourceText(filterChip)
        assertTrue("chip 未选中底必须取 chip 面 token", chip.contains("themeUi.tabBackgroundColor"))
        assertTrue("chip 形状必须走形状单源 AppShapes.Capsule", chip.contains("AppShapes.Capsule"))
        assertFalse(
            "chip 不得再引入越界面 token（mutedColor 属面 token 越界）",
            chip.contains("themeMutedColorOrDefault()")
        )
    }
}