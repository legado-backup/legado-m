package io.legado.app.ui.association

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 文件关联入口判据单测（spec MD-01「三入口」配对）。
 *
 * 覆盖：①分享（ACTION_SEND）取 `EXTRA_STREAM`；②打开方式（VIEW 等）取 `data`；
 * ③**分享入口缺 `EXTRA_STREAM` 时不回退到 `data`**（防"没拿到文件"被伪装成别的 URI）；
 * ④空/空白 URI 一律不可用；⑤action 为空按 `data` 处理（兼容隐式 VIEW）。
 */
class AssociationIntentPolicyTest {

    private val send = AssociationIntentPolicy.ACTION_SEND

    @Test
    fun `分享入口取 EXTRA_STREAM 而非 data`() {
        val plan = AssociationIntentPolicy.plan(
            action = send,
            dataUri = "content://unrelated/doc/1",
            streamUri = "file:///sdcard/Download/book.md",
        )
        assertEquals(AssociationIntentPolicy.Entry.SHARED_STREAM, plan.entry)
        assertEquals("file:///sdcard/Download/book.md", plan.uri)
    }

    @Test
    fun `分享入口缺 EXTRA_STREAM 时不回退到 data`() {
        val plan = AssociationIntentPolicy.plan(
            action = send,
            dataUri = "content://unrelated/doc/1",
            streamUri = null,
        )
        assertEquals(AssociationIntentPolicy.Entry.SHARED_STREAM, plan.entry)
        assertNull("分享未带文件时必须放弃，不得把 data 当成文件", plan.uri)
    }

    @Test
    fun `打开方式入口取 data`() {
        val plan = AssociationIntentPolicy.plan(
            action = "android.intent.action.VIEW",
            dataUri = "content://com.android.providers.downloads/doc/7",
            streamUri = null,
        )
        assertEquals(AssociationIntentPolicy.Entry.DATA_URI, plan.entry)
        assertEquals("content://com.android.providers.downloads/doc/7", plan.uri)
    }

    @Test
    fun `action 为空按 data 处理`() {
        val plan = AssociationIntentPolicy.plan(action = null, dataUri = "file:///a.md", streamUri = null)
        assertEquals(AssociationIntentPolicy.Entry.DATA_URI, plan.entry)
        assertEquals("file:///a.md", plan.uri)
    }

    @Test
    fun `空白 URI 一律不可用`() {
        assertNull(AssociationIntentPolicy.plan(null, "   ", null).uri)
        assertNull(AssociationIntentPolicy.plan(send, null, "").uri)
        assertNull(AssociationIntentPolicy.plan(null, null, null).uri)
    }
}