package io.legado.app.ui.main.bookshelf

import io.legado.app.data.entities.Book
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.File

/**
 * 书架封面渲染路径行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 背景（issues-found NEW-18）：书架书目项封面原为 `AndroidView + ImageView` —— 每个可见项都要
 * 创建传统 View，并在滚动进出屏幕时反复创建/销毁。真机 A/B（同机同手势）实测改前
 * **90 分位 73ms / 慢 UI 线程 234 帧**，改用既有 Compose 原生封面后 **12ms / 3 帧**。
 */
class BookshelfCoverComposePathTest {

    private fun book(name: String) = Book(name = name, bookUrl = "unit://$name", author = "作者")

    @Test
    fun coverColor_isStableForSameTitle() {
        assertEquals(coverColorForBook(book("同一本书")), coverColorForBook(book("同一本书")))
    }

    @Test
    fun coverColor_isBoundedToPalette() {
        val titles = listOf(
            "红楼梦", "三体", "活着", "围城", "边城", "平凡的世界", "白鹿原", "尘埃落定",
            "文化苦旅", "万历十五年", "江城", "寻路中国", "乡土中国", "人间词话", "经典常谈",
            "呼兰河传", "骆驼祥子", "月牙儿", "四世同堂", "茶馆"
        )
        val colors = titles.map { coverColorForBook(book(it)) }.toSet()
        assertTrue("同一调色板内取色，颜色种类应有界（≤8）", colors.size <= 8)
        assertTrue("不同书名不应全部退化到同一色", colors.size >= 2)
    }

    @Test
    fun bookshelfItemCover_mustNotUseAndroidViewPerItem() {
        // 回归锁：封面不得退回「每个书目项一个 AndroidView」
        // （该实现是书架滚动卡顿的根因，见 NEW-18 的真机 A/B 量化）
        val candidates = listOf(
            File("src/main/java/io/legado/app/ui/main/bookshelf/BookshelfItems.kt"),
            File("app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfItems.kt")
        )
        val source = candidates.firstOrNull { it.isFile }?.readText()
            ?: fail("未找到 BookshelfItems.kt 源码（候选路径均不存在）").let { "" }
        assertFalse(
            "书架书目项封面不得使用 AndroidView（会随滚动反复创建/销毁传统 View）",
            source.contains("AndroidView(")
        )
    }
}
