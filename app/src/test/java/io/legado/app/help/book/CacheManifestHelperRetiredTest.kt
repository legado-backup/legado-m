package io.legado.app.help.book

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-86 续批 5：`CacheManifestHelper.hasManifest` 零引用退役守护。
 *
 * 判据：活路径用 `manifestFile(book)` / `read(book)` / `read(file)`（后者内部已含 `file.isFile` 判空），
 * 而 `hasManifest(cacheDir)` 这条「裸目录存在性」便利方法**全仓零引用** ⇒ 已删。
 * 本用例防其回流，并守住活实现不被误删。
 */
class CacheManifestHelperRetiredTest {

    private val src by lazy { SourceFileProbe.sourceText("help/book/CacheManifestHelper.kt") }

    @Test
    fun `零引用便利方法退役且活实现仍在`() {
        assertEquals("hasManifest 不得回流", false, src.contains("fun hasManifest("))
        assertEquals("活实现 manifestFile 必须保留", true, src.contains("fun manifestFile("))
        assertEquals("活实现 read 必须保留", true, src.contains("fun read("))
    }
}
