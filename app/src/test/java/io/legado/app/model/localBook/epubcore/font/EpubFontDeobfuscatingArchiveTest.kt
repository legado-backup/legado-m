package io.legado.app.model.localBook.epubcore.font

import io.legado.app.model.localBook.epubcore.archive.EpubArchive
import io.legado.app.model.localBook.epubcore.archive.EpubPath
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.security.MessageDigest

/**
 * EPUB 内嵌字体去混淆单测（epub-md-rich-rendering 阶段 1.3 配对）
 *
 * 背景：出版规范允许对**内嵌字体**做前缀 XOR 混淆；不还原则字体加载必然失败。
 * 本测试把「算法/前缀长度/密钥派生/引用归一」全部钉住，并覆盖两条读取通道
 * （[EpubArchive.readBytes] 与 [EpubArchive.openStream]）与**全部降级分支**。
 *
 * 判据要点：
 * - 只还原**前缀**（IDPF 1040 / Adobe 1024），其后字节必须逐字节等于原文件（否则字体损坏）；
 * - 未识别算法 / 无 `encryption.xml` / 标识缺失 / XML 畸形 ⇒ **原样返回同一实例**（零行为变化）；
 * - 引用为外部 URL（含 scheme / 协议相对）⇒ 该条被忽略（不越界读包外资源）。
 */
class EpubFontDeobfuscatingArchiveTest {

    // === 前置与用例数据 ===

    /** 原始 SHA-1（**不做**空白归一），用于构造"错误密钥"以证明归一是必需的。 */
    private fun sha1(text: String): ByteArray =
        MessageDigest.getInstance("SHA-1").digest(text.toByteArray(Charsets.UTF_8))

    /** 规范口径：密钥 = SHA-1(去空白后的标识)。 */
    private fun idpfKey(identifier: String): ByteArray =
        sha1(identifier.filterNot { it in XML_WHITESPACE })

    private fun adobeKey(identifier: String): ByteArray {
        val hex = identifier.removePrefix("urn:uuid:").replace("-", "").lowercase()
        return ByteArray(16) { index -> hex.substring(index * 2, index * 2 + 2).toInt(16).toByte() }
    }

    /** 按算法对前 [prefixLength] 字节做循环 XOR（模拟出版方混淆）。 */
    private fun obfuscate(plain: ByteArray, key: ByteArray, prefixLength: Int): ByteArray {
        val out = plain.copyOf()
        for (index in 0 until minOf(prefixLength, out.size)) {
            out[index] = (out[index].toInt() xor key[index % key.size].toInt()).toByte()
        }
        return out
    }

    private fun plainBytes(size: Int = 1500): ByteArray {
        return ByteArray(size) { index -> (index % 251).toByte() }
    }

    private fun encryptionXml(vararg entries: Pair<String, String>): String {
        val body = entries.joinToString("") { (algorithm, uri) ->
            "<EncryptedData xmlns=\"http://www.w3.org/2001/04/xmlenc#\">" +
                "<EncryptionMethod Algorithm=\"$algorithm\"/>" +
                "<CipherData><CipherReference URI=\"$uri\"/></CipherData>" +
                "</EncryptedData>"
        }
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" +
            "<encryption xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">$body</encryption>"
    }

    /** 内存压缩包；`readBytes` 返回副本，确保装饰器的**就地还原**不会污染底层数据。 */
    private class FakeArchive(private val entries: Map<String, ByteArray>) : EpubArchive {

        override fun exists(path: String): Boolean = entries.containsKey(EpubPath.normalize(path))

        override fun list(): List<String> = entries.keys.toList()

        override fun readBytes(path: String, maxBytes: Long): ByteArray {
            val bytes = entries[EpubPath.normalize(path)] ?: error("EPUB entry not found: $path")
            return bytes.copyOf()
        }

        override fun openStream(path: String): InputStream = ByteArrayInputStream(readBytes(path))

        override fun close() = Unit
    }

    private fun archiveOf(
        fontPath: String,
        fontBytes: ByteArray,
        encryption: String? = null
    ): EpubArchive {
        val entries = linkedMapOf(fontPath to fontBytes)
        if (encryption != null) entries["META-INF/encryption.xml"] = encryption.toByteArray(Charsets.UTF_8)
        return FakeArchive(entries)
    }

    // === 透传/降级分支 ===

    @Test
    fun `未声明 encryption 时原样返回同一实例`() {
        val delegate = archiveOf(FONT_PATH, plainBytes())
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER))
    }

    @Test
    fun `未登记算法时不包装`() {
        val delegate = archiveOf(
            FONT_PATH, plainBytes(),
            encryption = encryptionXml("http://example.invalid/unknown" to FONT_PATH)
        )
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER))
    }

    @Test
    fun `标识为空时无法派生密钥故不包装`() {
        val delegate = archiveOf(
            FONT_PATH, plainBytes(),
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, null))
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, "   "))
    }

    @Test
    fun `encryption 元数据畸形时优雅降级为原样透传`() {
        val delegate = archiveOf(
            FONT_PATH, plainBytes(),
            encryption = "<encryption><EncryptedData>"   // 未闭合
        )
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER))
    }

    @Test
    fun `引用指向外部 URL 的条目被忽略`() {
        val delegate = archiveOf(
            FONT_PATH, plainBytes(),
            encryption = encryptionXml(
                IDPF_ALGORITHM to "https://cdn.invalid/fonts/a.ttf",
                IDPF_ALGORITHM to "//cdn.invalid/fonts/a.ttf",
                IDPF_ALGORITHM to "urn:isbn:1234567890"
            )
        )
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER))
    }

    // === IDPF（SHA-1 密钥 / 1040 前缀）===

    @Test
    fun `IDPF 算法还原前 1040 字节且其后字节逐字节不变`() {
        val plain = plainBytes()
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val wrapped = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER)
        assertNotSame(delegate, wrapped)

        val restored = wrapped.readBytes(FONT_PATH)
        assertArrayEquals(plain, restored)
        // 前缀边界两侧：第 1039 字节被还原、第 1040 字节本就不参与还原
        assertEquals(plain[IDPF_PREFIX - 1], restored[IDPF_PREFIX - 1])
        assertEquals(obfuscated[IDPF_PREFIX], restored[IDPF_PREFIX])
    }

    @Test
    fun `IDPF 算法按去空白后的标识派生密钥`() {
        val identifier = "  urn:uuid:with \t whitespace \n injected  "
        val plain = plainBytes()
        // 释义：去空白后才是规范定义的密钥输入；此处先证"未去空白"的密钥确实不同，
        // 再证按规范口径即可还原（否则该用例可能因两种口径偶然相同而变成空断言）。
        assertFalse(sha1(identifier).contentEquals(idpfKey(identifier)))
        val obfuscated = obfuscate(plain, idpfKey(identifier), IDPF_PREFIX)

        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val wrapped = EpubFontDeobfuscatingArchive.wrap(delegate, identifier)
        assertArrayEquals(plain, wrapped.readBytes(FONT_PATH))
    }

    @Test
    fun `内容短于前缀长度时全量还原且不越界`() {
        val plain = plainBytes(64)
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val restored = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER).readBytes(FONT_PATH)
        assertArrayEquals(plain, restored)
    }

    // === Adobe（UUID 十六进制密钥 / 1024 前缀）===

    @Test
    fun `Adobe 算法按 UUID 十六进制派生密钥还原前 1024 字节`() {
        val plain = plainBytes()
        val obfuscated = obfuscate(plain, adobeKey(ADOBE_IDENTIFIER), ADOBE_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(ADOBE_ALGORITHM to FONT_PATH)
        )
        val restored = EpubFontDeobfuscatingArchive.wrap(delegate, ADOBE_IDENTIFIER).readBytes(FONT_PATH)
        assertArrayEquals(plain, restored)
        assertEquals(obfuscated[ADOBE_PREFIX], restored[ADOBE_PREFIX])
    }

    @Test
    fun `标识非 32 位十六进制时不包装（Adobe 密钥不可派生）`() {
        val invalid = "urn:uuid:not-a-hex-identifier"
        val delegate = archiveOf(
            FONT_PATH, plainBytes(),
            encryption = encryptionXml(ADOBE_ALGORITHM to FONT_PATH)
        )
        assertSame(delegate, EpubFontDeobfuscatingArchive.wrap(delegate, invalid))
    }

    // === openStream 通道（WebView 分段读字体时的真实路径）===

    @Test
    fun `openStream 流式还原与 readBytes 一致且只还原前缀`() {
        val plain = plainBytes()
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val wrapped = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER)

        val streamed = wrapped.openStream(FONT_PATH).use { it.readBytes() }
        assertArrayEquals(plain, streamed)
        assertArrayEquals(wrapped.readBytes(FONT_PATH), streamed)
    }

    @Test
    fun `openStream 跳过后剩余前缀不再重复还原`() {
        val plain = plainBytes()
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val stream = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER).openStream(FONT_PATH)
        stream.use {
            assertEquals(IDPF_PREFIX.toLong(), it.skip(IDPF_PREFIX.toLong()))
            // 跳过了整个前缀 ⇒ 其后字节为原始（未混淆）字节，不得再被 XOR
            assertEquals(obfuscated[IDPF_PREFIX].toInt() and 0xff, it.read())
        }
    }

    @Test
    fun `openStream 支持 mark 与 reset 后重读仍正确`() {
        val plain = plainBytes()
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = archiveOf(
            FONT_PATH, obfuscated,
            encryption = encryptionXml(IDPF_ALGORITHM to FONT_PATH)
        )
        val stream = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER).openStream(FONT_PATH)
        stream.use {
            val buffer = ByteArray(256)
            it.mark(buffer.size)
            assertEquals(buffer.size, it.read(buffer, 0, buffer.size))
            assertArrayEquals(plain.copyOfRange(0, buffer.size), buffer)
            it.reset()
            // reset 后位置回到标记点 ⇒ 再次读取必须仍是"已还原"的前缀字节
            assertEquals(buffer.size, it.read(buffer, 0, buffer.size))
            assertArrayEquals(plain.copyOfRange(0, buffer.size), buffer)
        }
    }

    // === 隔离性与委派 ===

    @Test
    fun `仅登记条目被还原其余条目字节原样透传`() {
        val plain = plainBytes()
        val other = ByteArray(32) { index -> (index + 7).toByte() }
        val obfuscated = obfuscate(plain, idpfKey(IDENTIFIER), IDPF_PREFIX)
        val delegate = FakeArchive(
            linkedMapOf(
                FONT_PATH to obfuscated,
                "OEBPS/Text/ch1.xhtml" to other,
                "META-INF/encryption.xml" to encryptionXml(IDPF_ALGORITHM to FONT_PATH).toByteArray(Charsets.UTF_8)
            )
        )
        val wrapped = EpubFontDeobfuscatingArchive.wrap(delegate, IDENTIFIER)
        assertArrayEquals(plain, wrapped.readBytes(FONT_PATH))
        assertArrayEquals(other, wrapped.readBytes("OEBPS/Text/ch1.xhtml"))
        assertTrue(wrapped.exists(FONT_PATH))
        assertTrue(wrapped.list().contains(FONT_PATH))
        assertTrue(wrapped.entrySize(FONT_PATH) == null)
    }
}

private const val FONT_PATH = "OEBPS/Fonts/embedded.ttf"
private const val IDENTIFIER = "urn:isbn:9781234567890"
private const val ADOBE_IDENTIFIER = "urn:uuid:12345678-9abc-def0-1234-56789abcdef0"
private const val IDPF_ALGORITHM = "http://www.idpf.org/2008/embedding"
private const val ADOBE_ALGORITHM = "http://ns.adobe.com/pdf/enc#RC"

/** 前缀长度与规范同值（IDPF 1040 / Adobe 1024），在此显式钉住防漂移。 */
private const val IDPF_PREFIX = 1040
private const val ADOBE_PREFIX = 1024

/** 与实现同口径的"去空白"集合（防止测试与实现各自演进）。 */
private val XML_WHITESPACE = setOf(' ', '\t', '\r', '\n')