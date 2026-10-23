package io.legado.app.ui.code

import java.io.File
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * 代码编辑会话载荷存储（2026-10-23 js-source-parity-and-crash-fix R2）。
 *
 * 关键不变量：
 * ① 正文只落磁盘、跨 Activity 只传 id（防 Binder 事务超限导致的"点编辑直接崩"）；
 * ② 写是**原子替换**（进程在写入中途被杀 ⇒ 要么旧内容、要么新内容，不能是半截）；
 * ③ 会话 id 必须是 UUID（防路径穿越）。
 */
class CodeEditSessionStoreTest {

    private lateinit var dir: File
    private lateinit var store: CodeEditSessionStore

    @Before
    fun setUp() {
        dir = File(System.getProperty("java.io.tmpdir"), "code_edit_session_test_${System.nanoTime()}")
        store = CodeEditSessionStore(dir)
    }

    @After
    fun tearDown() {
        dir.deleteRecursively()
    }

    @Test
    fun createReadWriteDeleteRoundTrip() {
        val id = store.create("第一版脚本")
        assertEquals("第一版脚本", store.read(id))

        store.write(id, "第二版脚本（更长）")
        assertEquals("第二版脚本（更长）", store.read(id))

        store.delete(id)
        assertNull("删除后必须读不到", store.read(id))
    }

    @Test
    fun writeIsAtomicViaRename() {
        val id = store.create("old")
        store.write(id, "new")
        // 原子替换的中间产物必须全部清理（.new / .bak 残留会让下次进入读到错误版本）
        val leftovers = dir.listFiles().orEmpty().filter { it.name.startsWith(id) && it.extension != "txt" }
        assertTrue("不得残留 .new/.bak：${leftovers.map { it.name }}", leftovers.isEmpty())
        assertEquals("new", store.read(id))
    }

    @Test
    fun backupRestoredWhenMainFileMissing() {
        val id = store.create("payload")
        // 模拟"rename 前进程被杀"：主文件丢失、备份仍在
        val main = dir.listFiles().orEmpty().first { it.name == "$id.txt" }
        val backup = File(dir, "$id.bak")
        assertTrue(main.renameTo(backup))

        assertEquals("备份应被当作完整内容恢复", "payload", store.read(id))
        assertTrue("恢复后主文件必须存在", File(dir, "$id.txt").isFile)
    }

    @Test
    fun invalidSessionIdRejected() {
        // 防路径穿越：非 UUID 形态一律拒绝
        assertThrows(IllegalArgumentException::class.java) { store.read("../../etc/passwd") }
        assertThrows(IllegalArgumentException::class.java) { store.write("../x", "y") }
        assertThrows(IllegalArgumentException::class.java) { store.delete("not-a-uuid") }
    }

    @Test
    fun cleanupStaleRemovesOnlyExpired() {
        val expired = store.create("expired")
        val fresh = store.create("fresh")
        val expiredFile = dir.listFiles().orEmpty().first { it.name == "$expired.txt" }
        assertTrue(expiredFile.setLastModified(System.currentTimeMillis() - 48L * 60 * 60 * 1000))

        store.cleanupStale()

        assertNull("24h 前的残留必须清理", store.read(expired))
        assertEquals("当次会话不得受影响", "fresh", store.read(fresh))
    }
}
