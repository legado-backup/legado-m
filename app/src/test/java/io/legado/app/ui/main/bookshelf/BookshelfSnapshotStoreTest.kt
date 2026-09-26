package io.legado.app.ui.main.bookshelf

import android.app.Application
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import io.legado.app.constant.BookType
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookGroup
import io.legado.app.help.book.readProgress
import java.io.File
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import splitties.init.injectAsAppCtx

/**
 * R 批 §3.1.5 `Q6` 书架快照存储（Robolectric 行为级）。
 *
 * 为什么必须 Robolectric：`BookshelfSnapshotStore` 的根目录取 `appCtx.filesDir`、键派生读
 * `AppConfig`（走 prefs），纯 JVM 下 `appCtx` 未初始化会直接抛 `IllegalStateException`
 * （本项目既有教训，见 `BadgeViewThemeModeTest`）⇒ 用例内手动 `injectAsAppCtx()`。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class BookshelfSnapshotStoreTest {

    private lateinit var context: Context

    private val style = "style1"

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        context.injectAsAppCtx()
        BookshelfSnapshotStore.resetForTest()
    }

    private fun group(id: Long, name: String = "组$id", order: Int = 0) =
        BookGroup(groupId = id, groupName = name, order = order)

    private fun key(
        groupId: Long = 1L,
        sort: Int = 0,
        tagFilter: String = "",
        groups: List<BookGroup> = listOf(group(1L))
    ) = BookshelfSnapshotStore.buildKey(style, groupId, sort, tagFilter, groups)

    private fun book(url: String, name: String = "书$url") =
        Book(bookUrl = url, name = name, totalChapterNum = 10, durChapterIndex = 3)

    private fun snapshotDir(): File = File(context.filesDir, "bookshelfSnapshots")

    private fun snapshotFile(key: String): File =
        File(snapshotDir(), "${key.replace(Regex("[^A-Za-z0-9_.-]"), "_")}.json")

    // ---- 键派生：同输入稳定 / 任一因素变化即失效 ----

    @Test
    fun sameInputs_produceStableKey() {
        assertEquals(key(), key())
        assertTrue("键须带样式前缀", key().startsWith("$style-"))
    }

    @Test
    fun groupSortOrTagChange_invalidatesKey() {
        assertNotEquals("换分组必须失效", key(), key(groupId = 2L))
        assertNotEquals("换排序必须失效", key(), key(sort = 3))
        assertNotEquals("换标签筛选必须失效", key(), key(tagFilter = "追更"))
    }

    @Test
    fun groupSignatureChange_invalidatesKey() {
        val base = key(groups = listOf(group(1L, "旧名")))
        val renamed = key(groups = listOf(group(1L, "新名")))
        assertNotEquals("分组签名变化（改名/排序/开关）必须失效", base, renamed)
        // 分组顺序不影响签名（内部先按 order+groupId 归一排序）
        assertEquals(
            "分组集合顺序不应改变签名",
            BookshelfSnapshotStore.buildKey(style, 1L, 0, "", listOf(group(1L), group(2L))),
            BookshelfSnapshotStore.buildKey(style, 1L, 0, "", listOf(group(2L), group(1L)))
        )
    }

    @Test
    fun differentStyles_neverShareKey() {
        val a = BookshelfSnapshotStore.buildKey("style1", 1L, 0, "", listOf(group(1L)))
        val b = BookshelfSnapshotStore.buildKey("style2", 1L, 0, "", listOf(group(1L)))
        assertNotEquals(a, b)
    }

    // ---- 读写：内存 + 磁盘全链路 ----

    @Test
    fun saveThenRead_returnsSameBooks() {
        val k = key()
        val books = listOf(book("u1"), book("u2"))
        BookshelfSnapshotStore.save(k, books)
        val read = BookshelfSnapshotStore.read(k)
        assertEquals(listOf("u1", "u2"), read?.map { it.bookUrl })
        assertEquals("书u1", read?.first()?.name)
    }

    @Test
    fun readWithoutDiskSnapshot_returnsNull() {
        assertNull("从未写过 ⇒ 必须回源 DB", BookshelfSnapshotStore.read(key()))
    }

    /** 本仓相对上游的差异点：落盘用渲染投影（不含 readConfig）⇒ 含 LocalDate 的书也必须能安全往返。 */
    @Test
    fun bookWithReadConfig_serializesSafely() {
        val k = key()
        val start = LocalDate.of(2026, 9, 1)
        val source = book("u1").apply {
            readConfig = Book.ReadConfig(
                readSimulating = true,
                startDate = start,
                startChapter = 0,
                dailyChapters = 5
            )
        }
        // 若快照直接序列化 Book 实体，Gson 会为 LocalDate 解反射适配器并抛
        // JsonIOException: Failed making field 'java.time.LocalDate#year' accessible（2026-09-26 实证）
        BookshelfSnapshotStore.save(k, listOf(source))
        val read = BookshelfSnapshotStore.read(k)
        assertEquals(listOf("u1"), read?.map { it.bookUrl })
        assertNull("readConfig 按设计不入快照（避免 LocalDate 反射）", read?.first()?.readConfig)
    }

    /** 渲染关键字段必须逐项还原（缺一项 ⇒ 首帧渲染走样）。 */
    @Test
    fun renderFields_surviveRoundTrip() {
        val k = key()
        BookshelfSnapshotStore.save(
            k,
            listOf(
                book("u1").apply {
                    origin = "https://站点A"
                    originName = "源甲"
                    author = "作者甲"
                    totalChapterNum = 100
                    durChapterIndex = 7
                    durChapterTitle = "第8章"
                    latestChapterTitle = "第100章"
                    latestChapterTime = 111L
                    durChapterTime = 222L
                    lastCheckCount = 3
                    customTag = "追更"
                    type = BookType.text
                }
            )
        )
        val b = BookshelfSnapshotStore.read(k)?.single()!!
        assertEquals("源甲", b.originName)
        assertEquals("作者甲", b.author)
        assertEquals(100, b.totalChapterNum)
        assertEquals(7, b.durChapterIndex)
        assertEquals("第8章", b.durChapterTitle)
        assertEquals("第100章", b.latestChapterTitle)
        assertEquals(111L, b.latestChapterTime)
        assertEquals(222L, b.durChapterTime)
        assertEquals(3, b.lastCheckCount)
        assertEquals("追更", b.customTag)
        assertEquals(92, b.getUnreadChapterNum())
        assertEquals(7f / 99f, b.readProgress()!!, 1e-6f)
    }

    @Test
    fun savingEmptyList_removesSnapshot() {
        val k = key()
        BookshelfSnapshotStore.save(k, listOf(book("u1")))
        assertTrue(snapshotFile(k).isFile)
        BookshelfSnapshotStore.save(k, emptyList())
        assertNull("空列表 ⇒ 快照必须清除（避免重启后展示空书架）", BookshelfSnapshotStore.read(k))
        assertFalse("磁盘文件也应删除", snapshotFile(k).isFile)
    }

    // ---- 失效判定：磁盘上的脏数据必须被拒绝 ----

    @Test
    fun diskSnapshotWithMismatchedKey_isRejected() {
        val k = key()
        snapshotFile(k).writeText(
            """{"version":1,"key":"other-key","savedAt":0,"books":[]}""",
            Charsets.UTF_8
        )
        assertNull("键不匹配 ⇒ 视为失效回源", BookshelfSnapshotStore.read(k))
    }

    @Test
    fun diskSnapshotWithOldVersion_isRejected() {
        val k = key()
        snapshotFile(k).writeText(
            """{"version":99,"key":"$k","savedAt":0,"books":[]}""",
            Charsets.UTF_8
        )
        assertNull("版本漂移 ⇒ 视为失效回源", BookshelfSnapshotStore.read(k))
    }

    @Test
    fun corruptedSnapshotFile_isRejected() {
        val k = key()
        snapshotFile(k).writeText("{不是合法 JSON", Charsets.UTF_8)
        assertNull("脏文件不得抛异常，必须回落 null", BookshelfSnapshotStore.read(k))
    }

    // ---- 磁盘上限 ----

    @Test
    fun diskSnapshots_areTrimmedToLimit() {
        repeat(26) { index ->
            BookshelfSnapshotStore.save(key(groupId = index + 1L), listOf(book("u$index")))
        }
        val files = snapshotDir().listFiles()
            ?.filter { it.extension == "json" && !it.name.endsWith(".tmp.json") } ?: emptyList()
        assertEquals("磁盘快照上限 24", 24, files.size)
    }
}