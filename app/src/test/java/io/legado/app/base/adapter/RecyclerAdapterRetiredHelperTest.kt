package io.legado.app.base.adapter

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：`RecyclerAdapter.clearItems` 零调用残余退役守护。
 *
 * 退役项：`clearItems()`（全仓除声明外零引用）。
 * 同语义活替代者：`setItems(null)` —— 逐行等价（`items.clear()` → `if (items != null) addAll` 跳过
 * → `notifyDataSetChanged()` → `onCurrentListChanged()`），且活方更完备（同时支持非空列表装载）。
 */
class RecyclerAdapterRetiredHelperTest {

    @Test
    fun `零调用清空入口已退役且活替代者仍在`() {
        val src = SourceFileProbe.sourceText("base/adapter/RecyclerAdapter.kt")
        assertEquals("退役项不得回潮", false, src.contains("fun clearItems("))
        assertEquals("活替代者 setItems(List) 必须保留", true, src.contains("fun setItems(items: List<ITEM>?)"))
        assertEquals("发散装载版 setItems(DiffUtil) 必须保留", true, src.contains("itemCallback: DiffUtil.ItemCallback<ITEM>"))
        assertEquals("空列表判定必须保留", true, src.contains("fun isEmpty() = items.isEmpty()"))
    }
}
