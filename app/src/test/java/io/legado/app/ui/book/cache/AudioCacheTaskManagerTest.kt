package io.legado.app.ui.book.cache

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * `AudioCacheTaskManager` 纯别名式包装退役守护。
 *
 * 缺陷背景：`hasTask(bookUrl)`（= `_states.value[bookUrl]?.active == true`）全仓零消费者；
 * 活路径一律走**状态快照**读法 —— `snapshot(bookUrl)`（`CacheManageActivityViewModel:794`、
 * `CacheManageActivity:624/627`，并以 `locksCacheActions()` 判可否操作）与 `states` StateFlow
 * 订阅（`CacheManageActivity:236`）⇒ 该布尔别名属**未用包装**（同族有活体），已退役。
 *
 * 本类守护：①别名不得回流；②活体读法（`snapshot` / `states`）必须保留。
 */
class AudioCacheTaskManagerTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val main = "src/main/java/io/legado/app/ui/book/cache/"

    @Test
    fun `纯别名 hasTask 已退役`() {
        assertEquals("纯别名不得回流", false, code(main + "AudioCacheTaskManager.kt").contains("fun hasTask("))
    }

    @Test
    fun `活体状态读法必须保留且被消费`() {
        val mgr = code(main + "AudioCacheTaskManager.kt")
        assertEquals("快照读法必须保留", true, mgr.contains("fun snapshot(bookUrl: String)"))
        assertEquals("状态流必须保留", true, mgr.contains("val states: StateFlow<Map<String, AudioCacheTaskState>>"))
        assertEquals("快照读法必须仍被活路径消费", true, code(main + "CacheManageActivity.kt").contains("AudioCacheTaskManager.snapshot("))
    }
}
