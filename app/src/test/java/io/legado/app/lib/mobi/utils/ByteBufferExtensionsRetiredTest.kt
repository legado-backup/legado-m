package io.legado.app.lib.mobi.utils

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-86 续批 5：`ByteBufferExtensions.readUInt64` 零引用退役守护。
 *
 * 判据：同族 `readUInt32`（含带 `offset` 重载）在活路径，仅 `readUInt64(offset)` 全仓零引用
 * （`ByteBuffer` 扩展函数、无反射 / 注解驱动 / 生成代码引用通道）⇒ 未使用的二进制读取助手 ⇒ 已删。
 * 本用例防其回流，并守住活实现不被误删。
 */
class ByteBufferExtensionsRetiredTest {

    private val src by lazy { SourceFileProbe.sourceText("lib/mobi/utils/ByteBufferExtensions.kt") }

    @Test
    fun `零引用读取助手退役且活实现仍在`() {
        assertEquals("readUInt64 不得回流", false, src.contains("fun ByteBuffer.readUInt64("))
        assertEquals("活实现 readUInt32 必须保留", true, src.contains("fun ByteBuffer.readUInt32("))
    }
}
