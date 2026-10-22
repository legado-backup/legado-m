package io.legado.app.ui.book.source.debug

import android.content.Intent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * 调试页复用实例（launchMode=singleTop）时的重绑定契约。
 *
 * 回归背景：Activity 原先只实现 onActivityCreated 的 init，不处理 onNewIntent ⇒
 * 从外部再次打开不同书源时页面仍调试旧源（真机实测：5 个 JS 源连续启动全部返回同一结果）。
 */
@RunWith(RobolectricTestRunner::class)
class BookSourceDebugRebindKeyTest {

    private fun intentWithKey(key: String?) = Intent().apply {
        if (key != null) putExtra("key", key)
    }

    @Test
    fun nonBlankKeyTriggersRebind() {
        assertEquals("https://example.test/source", BookSourceDebugActivity.rebindKey(intentWithKey("https://example.test/source")))
    }

    @Test
    fun blankOrMissingKeyKeepsCurrentSession() {
        assertNull("空白 key 不应打断当前调试", BookSourceDebugActivity.rebindKey(intentWithKey("   ")))
        assertNull("无 key 的 Intent 不应改动当前调试", BookSourceDebugActivity.rebindKey(intentWithKey(null)))
    }
}
