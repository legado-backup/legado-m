package io.legado.app.ui.main.bookshelf.style1

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.1.5 `Q6` 接线不变量（源码文本断言）：style1 书架的数据源必须是
 * 「快照优先 + 失效回源」——先读快照填首帧，DB flow 到达后覆盖并回写。
 */
class BookshelfFragment1SnapshotTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/main/bookshelf/style1/BookshelfFragment1.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun upConnectReadsSnapshotBeforeDbFlow() {
        val t = code()
        assertTrue("必须读快照", t.contains("BookshelfSnapshotStore.read(snapshotKey)"))
        assertTrue("必须回写快照", t.contains("BookshelfSnapshotStore.save(snapshotKey, it)"))
        assertTrue(
            "读快照必须早于 DB flow 收集（快照优先）",
            t.indexOf("BookshelfSnapshotStore.read(snapshotKey)") <
                t.indexOf("flowByGroup(selectedGroupId)")
        )
    }

    @Test
    fun snapshotKeyCarriesStyleGroupSortAndGroups() {
        val t = code()
        assertTrue("style1 键须带样式前缀", t.contains("""private const val STYLE_KEY = "style1""""))
        listOf("style = STYLE_KEY", "groupId = selectedGroupId", "sort = sortType", "groups = groupList")
            .forEach { assertTrue("键参数缺失：$it", t.contains(it)) }
    }

    @Test
    fun snapshotWriteIsOffMainThread() {
        val t = code()
        assertTrue(
            "快照写盘必须走 IO 调度器（flow 高频发射时不得阻塞主线程）",
            t.indexOf("withContext(Dispatchers.IO)") in 1 until
                t.indexOf("BookshelfSnapshotStore.save(snapshotKey, it)")
        )
    }
}