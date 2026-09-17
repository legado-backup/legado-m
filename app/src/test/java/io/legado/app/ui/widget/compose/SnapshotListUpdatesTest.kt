package io.legado.app.ui.widget.compose

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 同位写回门禁语义单测。
 *
 * 背景：项目内 Room 实体（BookSourcePart/RssSource/RuleSub/DictRule/TxtTocRule/ReplaceRule）
 * 的 equals 多为 key-only，若用内容等值做写回门禁，会把「同 key、字段已变」的新实例判为相同，
 * 导致乐观更新与 DB 回灌都落不进列表（界面定格）。
 */
class SnapshotListUpdatesTest {

    /** 模拟项目实体语义：equals/hashCode 仅按主键 */
    private data class KeyOnlyItem(val key: String, val enabled: Boolean) {
        override fun equals(other: Any?): Boolean =
            other is KeyOnlyItem && other.key == key

        override fun hashCode(): Int = key.hashCode()
    }

    @Test
    fun sameKeyWithChangedContentMustNotSkip() {
        val current = KeyOnlyItem("a", false)
        val next = KeyOnlyItem("a", true)
        // 内容等值判定为真（key-only），但写回不得被跳过
        assertTrue(current == next)
        assertFalse(current === next)
        assertFalse(shouldSkipSameIndexWrite(current, next))
    }

    @Test
    fun identicalInstanceMustSkip() {
        val current = KeyOnlyItem("a", false)
        assertTrue(shouldSkipSameIndexWrite(current, current))
    }

    @Test
    fun differentKeyNewInstanceMustNotSkip() {
        val current = KeyOnlyItem("a", true)
        val next = KeyOnlyItem("b", true)
        assertFalse(shouldSkipSameIndexWrite(current, next))
    }
}