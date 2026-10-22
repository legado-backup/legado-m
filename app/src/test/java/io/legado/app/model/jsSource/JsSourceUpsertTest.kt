package io.legado.app.model.jsSource

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 单文件 JS 书源落库前的纯函数边界（ng-js-source-port）。
 *
 * 覆盖三件高风险逻辑：体积/空内容门禁、用户状态保留（启停/分组/排序）、
 * 「仅时间戳差异不算变更」（防止脚本每次保存都判为新版本导致导入去重失效）。
 */
class JsSourceUpsertTest {

    @Test
    fun validatePayload_rejectsEmptyAndTooLarge() {
        assertEquals(JsSourceUpsert.PayloadIssue.EMPTY, JsSourceUpsert.validatePayload(null))
        assertEquals(JsSourceUpsert.PayloadIssue.EMPTY, JsSourceUpsert.validatePayload("  "))
        assertNull(JsSourceUpsert.validatePayload("var config = {bookSourceUrl:'u'};"))
        val tooLarge = "x".repeat(JsSourceUpsert.MAX_SOURCE_BYTES + 1)
        assertEquals(JsSourceUpsert.PayloadIssue.TOO_LARGE, JsSourceUpsert.validatePayload(tooLarge))
    }

    @Test
    fun preserveUserState_keepsEnableGroupOrderAndWeight() {
        val old = BookSource(
            bookSourceUrl = "https://old.invalid",
            bookSourceName = "old",
            bookSourceGroup = "分组A",
            enabled = false,
            enabledExplore = false,
            customOrder = 7,
            weight = 3,
            respondTime = 1234L,
        )
        val fresh = BookSource(
            bookSourceUrl = "https://old.invalid",
            bookSourceName = "new",
            bookSourceGroup = null,
            enabled = true,
            customOrder = 0,
        )
        JsSourceUpsert.preserveUserState(fresh, old)
        assertFalse(fresh.enabled)
        assertFalse(fresh.enabledExplore)
        assertEquals(7, fresh.customOrder)
        assertEquals(1234L, fresh.respondTime)
        assertEquals("分组A", fresh.bookSourceGroup)
        assertEquals("new", fresh.bookSourceName)
    }

    @Test
    fun preserveUserState_keepsExplicitNewGroup() {
        val old = BookSource(bookSourceGroup = "旧分组")
        val fresh = BookSource(bookSourceGroup = "新分组")
        JsSourceUpsert.preserveUserState(fresh, old)
        assertEquals("新分组", fresh.bookSourceGroup)
    }

    @Test
    fun equalIgnoringManagedUpdateTime_ignoresStampOnlyDiff() {
        val scriptA = """var config = { lastUpdateTime: 1 };"""
        val scriptB = """var config = { lastUpdateTime: 999 };"""
        val source = BookSource(bookSourceUrl = "u", bookSourceName = "n", mainJs = scriptA)
        val old = BookSource(bookSourceUrl = "u", bookSourceName = "n", mainJs = scriptB)
        assertTrue(JsSourceUpsert.equalIgnoringManagedUpdateTime(source, old))
    }

    @Test
    fun equalIgnoringManagedUpdateTime_detectsRealRuleChange() {
        val source = BookSource(bookSourceUrl = "u", bookSourceName = "n", searchUrl = "https://a")
        val old = BookSource(bookSourceUrl = "u", bookSourceName = "n", searchUrl = "https://b")
        assertFalse(JsSourceUpsert.equalIgnoringManagedUpdateTime(source, old))
    }

    @Test
    fun equalIgnoringManagedUpdateTime_detectsExploreScreenChange() {
        val source = BookSource(
            bookSourceUrl = "u", bookSourceName = "n",
            mainJs = "var config={};", exploreScreen = "{\"a\":1}",
        )
        val old = source.copy(exploreScreen = "{\"a\":2}")
        assertFalse(JsSourceUpsert.equalIgnoringManagedUpdateTime(source, old))
    }

    @Test
    fun hasTargetConflict_onlyWhenRenamingOntoExistingSource() {
        val opened = BookSource(bookSourceUrl = "https://a")
        val target = BookSource(bookSourceUrl = "https://b")
        assertTrue(JsSourceUpsert.hasTargetConflict(opened, target, "https://b"))
        assertFalse(JsSourceUpsert.hasTargetConflict(opened, target, "https://a"))
        assertFalse(JsSourceUpsert.hasTargetConflict(null, target, "https://b"))
        assertFalse(JsSourceUpsert.hasTargetConflict(opened, null, "https://b"))
    }
}
