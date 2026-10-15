package io.legado.app.ui.book.changesource

import io.legado.app.data.entities.SearchBook
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

/**
 * NEW-19 回归护栏：换源候选行的**行身份**是（源 + 书址），不是 `bookUrl`。
 *
 * 镜像源/同站多源会返回同一个 `bookUrl`，列表里两个源的行并存（这正是 `addSearchBook`
 * 与 LazyColumn key 都按 (origin, bookUrl) 判定的原因）；若行级移除误用 `SearchBook.equals`
 * （只比 `bookUrl`），消失的会是**另一个源**的行，而目标行仍在列表里 ⇒ 点击必然取不到书源。
 */
class ChangeSourceCandidateIdentityTest {

    private fun book(origin: String, url: String) = SearchBook(bookUrl = url, origin = origin)

    @Test
    fun entityEquality_isBookUrlOnly_henceUnusableForRowIdentity() {
        val a = book("A", "U")
        val b = book("B", "U")
        // 语言层事实：equals 只比 bookUrl（"不能用 remove(searchBook) 做行级移除"的根因）
        assertEquals(a, b)
        // 行身份键能区分二者
        assertNotEquals(a.primaryStr(), b.primaryStr())
    }

    @Test
    fun equalsBasedRemoval_removesWrongSourceRow() {
        // 修复前的写法：List.remove 走 equals（仅 bookUrl）
        val candidates = arrayListOf(book("A", "U"), book("B", "U"))
        candidates.remove(book("B", "U"))
        // 留下的不是目标行 B，而是另一个源 A 的行 ⇒ 目标行仍在列表里、无害行被误删
        assertEquals(1, candidates.size)
        assertEquals("B", candidates.single().origin)
    }

    @Test
    fun removeCandidate_keepsOtherSourceRowWithSameBookUrl() {
        val candidates = arrayListOf(book("A", "U"), book("B", "U"))
        removeCandidate(candidates, book("B", "U"))
        assertEquals(listOf("A"), candidates.map { it.origin })
    }

    @Test
    fun removeCandidate_removesAllRowsOfSameIdentity() {
        val candidates = arrayListOf(book("A", "U"), book("B", "U"), book("B", "U"))
        removeCandidate(candidates, book("B", "U"))
        assertEquals(1, candidates.size)
        assertEquals("A", candidates.single().origin)
    }

    @Test
    fun removeCandidate_keepsOtherBookUrlOfSameSource() {
        val candidates = arrayListOf(book("A", "U1"), book("A", "U2"))
        removeCandidate(candidates, book("A", "U1"))
        assertEquals(listOf("U2"), candidates.map { it.bookUrl })
    }
}
