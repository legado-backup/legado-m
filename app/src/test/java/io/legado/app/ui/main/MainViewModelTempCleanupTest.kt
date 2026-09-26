package io.legado.app.ui.main

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 Q7（2026-09-26）：启动期「临时书清理」必须走**身份化口径**。
 *
 * `MainViewModel.init` 会在每次冷启动时清理临时书（非书架书，由搜索/发现浏览创建）。
 * 原调用 `deleteNotShelfBook()`（全删）会把「用户从搜索结果直接读过」的书一并删掉 ——
 * 这些书在 `readRecentBooks` 有阅读身份记录，删除即丢失其阅读进度，并留下悬空最近在读行。
 * 现改为 `deleteTempByIdentity()`（DAO 侧排除 `readRecentBooks` 命中的书）。
 */
class MainViewModelTempCleanupTest {

    private fun mainViewModel(): String = SourceFileProbe.sourceText("ui/main/MainViewModel.kt")

    @Test
    fun startupCleanupUsesIdentityAwareApi() {
        val s = mainViewModel()
        assertTrue("启动期必须调用身份化清理", s.contains("deleteTempByIdentity()"))
        assertTrue("必须真正落到 DAO", s.contains("appDb.bookDao.deleteTempByIdentity()"))
        assertFalse("不得再调用已退役的全删 API", s.contains("appDb.bookDao.deleteNotShelfBook()"))
    }

    /** 全仓不得残留旧 API 调用点（残余调用会让「全删」语义从别的入口复活）。 */
    @Test
    fun legacyFullWipeHasNoCallSiteAnywhere() {
        val offenders = SourceFileProbe.mainJavaRoot().walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .filter { SourceFileProbe.stripComments(it.readText()).contains("deleteNotShelfBook()") }
            .map { it.name }
            .sorted()
            .toList()
        assertEquals("不得残留 deleteNotShelfBook() 调用点：$offenders", emptyList<String>(), offenders)
    }
}