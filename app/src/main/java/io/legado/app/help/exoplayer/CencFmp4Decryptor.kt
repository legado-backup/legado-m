package io.legado.app.help.exoplayer

import io.legado.app.constant.AppLog
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * CENC(AES-CTR) fMP4 **离线软件解密**（设计 AD-04 降级路径）。
 *
 * 适用：设备 `MediaDrm` 不支持 ClearKey（部分模拟器/定制 ROM），硬件解密不可用时，
 * 先把媒体下载到本地，逐样本用已注入的 key 解密，并把加密信令盒降级为 `free`，
 * 得到等价明文 fMP4 后按普通本地文件播放（保留 seek/倍速/缓存）。
 *
 * 关键实现选择：**不改任何盒长度** —— `encv/enca` 改为 `frma` 里的原始编码四字码（等长），
 * `sinf/senc/saiz/saio/pssh` 的 box type 改成 `free`（等长）⇒ 无需重算 moov/moof 尺寸与 chunk offset。
 *
 * 仅支持标准 `cenc`（AES-CTR、full-sample 或 subsample）片；`cbc1/cens/cbc2` 返回 0 样本（不处理）。
 */
internal object CencFmp4Decryptor {

    data class Stats(val trackCount: Int, val sampleCount: Int, val patchedBoxes: Int)

    data class Result(val bytes: ByteArray, val stats: Stats)

    private data class TrackCrypto(val originalFormat: String, val ivSize: Int)

    private const val FOURCC_FREE = "free"

    /**
     * 解密 + **重写盒结构**：原地解密样本后，删除加密信令盒（`sinf/senc/saiz/saio/pssh/mfra`），
     * 并把 `encv/enca` 样本入口恢复为原始编码四字码（尺寸随删除而缩小）。
     *
     * 为什么必须重写而非仅改类型（2026-10-27 真机铁证）：只把盒类型改成 `free` 时，
     * Media3 `FragmentedMp4Extractor` 仍判定轨道加密并在 `outputSampleEncryptionData` 抛
     * `ArrayIndexOutOfBoundsException`（ffmpeg 可正常解码）⇒ 必须彻底移除加密盒。
     */
    fun decrypt(data: ByteArray, key: ByteArray): Result {
        val stats = decryptInPlace(data, key, markFree = false)
        if (stats.sampleCount <= 0) return Result(data, stats)
        val rewritten = rewriteWithoutEncryptionBoxes(data)
        return Result(rewritten, stats)
    }

    /**
     * 原地解密 [data]（长度与盒布局保持不变）。
     *
     * @param key 16 字节内容密钥
     * @param markFree true 时把加密信令盒类型就地改成 `free`（调试/对照用）；伪装路径走重写，不再需要
     * @return 解密统计；`sampleCount == 0` 表示未发现可解密的加密样本
     */
    fun decryptInPlace(data: ByteArray, key: ByteArray, markFree: Boolean = true): Stats {
        var patched = 0
        val tracks = HashMap<Long, TrackCrypto>()
        forEachBox(data, 0, data.size) { type, boxStart, headerSize, boxSize ->
            if (type == "moov") {
                patched += parseMoov(data, boxStart + headerSize, boxStart + boxSize, tracks, markFree)
            }
        }
        var samples = 0
        forEachBox(data, 0, data.size) { type, boxStart, _, boxSize ->
            if (type == "moof") {
                val result = parseMoof(data, boxStart, boxSize, tracks, key, markFree)
                samples += result.first
                patched += result.second
            }
        }
        return Stats(tracks.size, samples, patched)
    }

    // ------------------------------------------------------------ 重写（删除加密盒）

    private val DROP_IN_CONTAINER = setOf("sinf", "senc", "saiz", "saio", "pssh")

    /**
     * 顶层重写：重建 moov/moof（删除加密盒、缩小尺寸），丢弃 mfra（其内部为绝对偏移，缩放后失效）。
     * 其余顶层盒原样拷贝（mdat 已解密）。
     */
    private fun rewriteWithoutEncryptionBoxes(data: ByteArray): ByteArray {
        val out = ByteArrayOutputStream(data.size)
        forEachBox(data, 0, data.size) { type, boxStart, headerSize, boxSize ->
            when (type) {
                "moov" -> out.write(
                    box(type, rebuildContainer(data, boxStart + headerSize, boxStart + boxSize))
                )

                "moof" -> {
                    val payload = rebuildContainer(data, boxStart + headerSize, boxStart + boxSize)
                    // moof 缩小后 mdat 同步前移：trun.data_offset / tfhd.base_data_offset 需加同一增量
                    patchMoofOffsets(payload, (8 + payload.size) - boxSize)
                    out.write(box(type, payload))
                }

                "mfra" -> Unit
                else -> out.write(data, boxStart, boxSize)
            }
        }
        return out.toByteArray()
    }

    private fun rebuildContainer(data: ByteArray, start: Int, end: Int): ByteArray {
        val out = ByteArrayOutputStream(end - start)
        var offset = start
        while (offset + 8 <= end) {
            val size = readUInt32(data, offset).toInt()
            if (size < 8 || offset + size > end) break
            val type = readType(data, offset + 4)
            when {
                type in DROP_IN_CONTAINER -> Unit
                type == "stsd" -> out.write(rebuildStsd(data, offset, size))
                type in CONTAINER_BOXES || type == "traf" ->
                    out.write(box(type, rebuildContainer(data, offset + 8, offset + size)))

                else -> out.write(data, offset, size)
            }
            offset += size
        }
        return out.toByteArray()
    }

    /** 重写 stsd：`encv/enca` 恢复原始编码四字码，并删除样本入口内的 `sinf` */
    private fun rebuildStsd(data: ByteArray, boxStart: Int, boxSize: Int): ByteArray {
        val out = ByteArrayOutputStream(boxSize)
        val payloadStart = boxStart + 8
        val end = boxStart + boxSize
        out.write(data, payloadStart, 8) // version/flags + entry_count
        var offset = payloadStart + 8
        while (offset + 8 <= end) {
            val size = readUInt32(data, offset).toInt()
            if (size < 8 || offset + size > end) break
            val type = readType(data, offset + 4)
            if (type == "encv" || type == "enca") {
                val childStart = offset + 8 + if (type == "encv") 78 else 28
                val sinf = findBox(data, childStart, offset + size, "sinf")
                val originalFormat = sinf?.let { (sinfStart, sinfSize) ->
                    findBox(data, sinfStart + 8, sinfStart + sinfSize, "frma")
                        ?.let { (frmaStart, _) -> readType(data, frmaStart + 8) }
                } ?: if (type == "encv") "avc1" else "mp4a"
                val prefixLength = childStart - (offset + 8)
                val children = rebuildContainer(data, childStart, offset + size)
                val payload = ByteArray(prefixLength + children.size)
                System.arraycopy(data, offset + 8, payload, 0, prefixLength)
                System.arraycopy(children, 0, payload, prefixLength, children.size)
                out.write(box(originalFormat, payload))
            } else {
                out.write(data, offset, size)
            }
            offset += size
        }
        return box("stsd", out.toByteArray())
    }

    private fun box(type: String, payload: ByteArray): ByteArray {
        val buffer = ByteBuffer.allocate(8 + payload.size).order(ByteOrder.BIG_ENDIAN)
        buffer.putInt(8 + payload.size)
        buffer.put(type.toByteArray(Charsets.US_ASCII))
        buffer.put(payload)
        return buffer.array()
    }

    /** 修正 moof 内绝对/相对数据偏移（moof 尺寸变化后 mdat 位置整体平移） */
    private fun patchMoofOffsets(moofPayload: ByteArray, delta: Int) {
        forEachBox(moofPayload, 0, moofPayload.size) { type, boxStart, headerSize, boxSize ->
            if (type != "traf") return@forEachBox
            val end = boxStart + boxSize
            findBox(moofPayload, boxStart + headerSize, end, "tfhd")?.let { (tfhdStart, _) ->
                val payloadStart = tfhdStart + 8
                val flags = readUInt32(moofPayload, payloadStart) and 0xFFFFFF
                if (flags and 0x000001L != 0L) {
                    val value = readUInt64(moofPayload, payloadStart + 8) + delta
                    writeUInt64(moofPayload, payloadStart + 8, value)
                }
            }
            findBox(moofPayload, boxStart + headerSize, end, "trun")?.let { (trunStart, _) ->
                val payloadStart = trunStart + 8
                val flags = readUInt32(moofPayload, payloadStart) and 0xFFFFFF
                if (flags and 0x000001L != 0L) {
                    val old = readUInt32(moofPayload, payloadStart + 8).toInt()
                    writeUInt32(moofPayload, payloadStart + 8, old + delta)
                }
            }
        }
    }

    private fun writeUInt32(data: ByteArray, offset: Int, value: Int) {
        data[offset] = (value ushr 24).toByte()
        data[offset + 1] = (value ushr 16).toByte()
        data[offset + 2] = (value ushr 8).toByte()
        data[offset + 3] = value.toByte()
    }

    private fun writeUInt64(data: ByteArray, offset: Int, value: Long) {
        writeUInt32(data, offset, (value ushr 32).toInt())
        writeUInt32(data, offset + 4, value.toInt())
    }

    // ---------------------------------------------------------------- moov

    private fun parseMoov(
        data: ByteArray,
        start: Int,
        end: Int,
        tracks: MutableMap<Long, TrackCrypto>,
        markFree: Boolean
    ): Int {
        var patched = 0
        forEachBox(data, start, end) { type, boxStart, headerSize, boxSize ->
            when (type) {
                "pssh" -> {
                    // 无 pssh 的 CENC 流不需要它；有 pssh 时硬件路径用，软件路径降级为 free
                    if (markFree) {
                        markFree(data, boxStart + 4)
                        patched++
                    }
                }

                "trak" -> patched += parseTrak(
                    data, boxStart + headerSize, boxStart + boxSize, tracks, markFree
                )
            }
        }
        return patched
    }

    private fun parseTrak(
        data: ByteArray,
        start: Int,
        end: Int,
        tracks: MutableMap<Long, TrackCrypto>,
        markFree: Boolean
    ): Int {
        val trackId = findBoxDeep(data, start, end, "tkhd")?.let { (tkhdStart, tkhdSize) ->
            readTrackId(data, tkhdStart, tkhdSize)
        } ?: return 0
        val stsd = findBoxDeep(data, start, end, "stsd") ?: return 0
        var patched = 0
        val (stsdStart, stsdSize) = stsd
        val payloadStart = stsdStart + 8
        val payloadEnd = stsdStart + stsdSize
        if (payloadStart + 8 > payloadEnd) return 0
        val entryCount = readUInt32(data, payloadStart + 4).toInt()
        var offset = payloadStart + 8
        var index = 0
        while (index < entryCount && offset + 8 <= payloadEnd) {
            val entrySize = readUInt32(data, offset).toInt()
            if (entrySize < 8 || offset + entrySize > payloadEnd) break
            val entryType = readType(data, offset + 4)
            if (entryType == "encv" || entryType == "enca") {
                // 子盒起点：视觉 = 8 盒头 + 78（含 6 reserved+2 data_ref），音频 = 8 盒头 + 28（28 已含前 8）
                val childStart = offset + 8 + if (entryType == "encv") 78 else 28
                val sinf = findBox(data, childStart, offset + entrySize, "sinf")
                if (sinf != null) {
                    val (sinfStart, sinfSize) = sinf
                    val original = findBox(data, sinfStart + 8, sinfStart + sinfSize, "frma")
                        ?.let { (frmaStart, _) -> readType(data, frmaStart + 8) }
                    val ivSize = findBox(data, sinfStart + 8, sinfStart + sinfSize, "schi")
                        ?.let { (schiStart, schiSize) ->
                            findBox(data, schiStart + 8, schiStart + schiSize, "tenc")
                                ?.let { (tencStart, tencSize) ->
                                    if (tencSize >= 8 + 8) data[tencStart + 8 + 7].toInt() and 0xFF else 0
                                }
                        } ?: 0
                    if (original != null && original.length == 4 && original != FOURCC_FREE) {
                        if (markFree) {
                            writeType(data, offset + 4, original)
                            markFree(data, sinfStart + 4)
                            patched++
                        }
                        tracks[trackId] = TrackCrypto(original, ivSize)
                    }
                }
            }
            offset += entrySize
            index++
        }
        return patched
    }

    private fun readTrackId(data: ByteArray, boxStart: Int, boxSize: Int): Long? {
        if (boxSize < 8 + 4) return null
        val payload = boxStart + 8
        val version = data[payload].toInt() and 0xFF
        val idOffset = payload + if (version == 1) 20 else 12
        if (idOffset + 4 > boxStart + boxSize) return null
        return readUInt32(data, idOffset)
    }

    // ---------------------------------------------------------------- moof

    private fun parseMoof(
        data: ByteArray,
        moofStart: Int,
        moofSize: Int,
        tracks: Map<Long, TrackCrypto>,
        key: ByteArray,
        markFree: Boolean
    ): Pair<Int, Int> {
        var samples = 0
        var patched = 0
        forEachBox(data, moofStart + 8, moofStart + moofSize) { type, trafStart, headerSize, trafSize ->
            if (type != "traf") return@forEachBox
            val trafEnd = trafStart + trafSize
            val tfhd = findBox(data, trafStart + headerSize, trafEnd, "tfhd")
                ?: return@forEachBox
            val tfhdInfo = parseTfhd(data, tfhd.first, tfhd.second) ?: return@forEachBox
            val crypto = tracks[tfhdInfo.trackId]
            val trun = findBox(data, trafStart + headerSize, trafEnd, "trun")
            val senc = findBox(data, trafStart + headerSize, trafEnd, "senc")
            if (trun != null && senc != null && crypto != null && crypto.ivSize in 8..16) {
                val base = tfhdInfo.baseDataOffset ?: moofStart.toLong()
                val encryptedSamples = decryptTrafSamples(
                    data, base, tfhdInfo, trun.first, trun.second,
                    senc.first, senc.second, crypto, key
                )
                samples += encryptedSamples
            }
            // 加密信令盒一律降级为 free（长度不变 ⇒ 无需重算 chunk offset）
            if (markFree) {
                listOf("senc", "saiz", "saio").forEach { boxType ->
                    findBox(data, trafStart + headerSize, trafEnd, boxType)?.let { (boxStart, _) ->
                        markFree(data, boxStart + 4)
                        patched++
                    }
                }
            }
        }
        return samples to patched
    }

    private data class TfhdInfo(
        val trackId: Long,
        val baseDataOffset: Long?,
        val defaultSampleSize: Int
    )

    private fun parseTfhd(data: ByteArray, boxStart: Int, boxSize: Int): TfhdInfo? {
        if (boxSize < 8 + 8) return null
        val payload = boxStart + 8
        val flags = readUInt32(data, payload) and 0xFFFFFF
        val trackId = readUInt32(data, payload + 4)
        var cursor = payload + 8
        var baseDataOffset: Long? = null
        if (flags and 0x000001L != 0L) {
            if (cursor + 8 > boxStart + boxSize) return null
            baseDataOffset = readUInt64(data, cursor)
            cursor += 8
        }
        if (flags and 0x000002L != 0L) cursor += 4
        var defaultSampleSize = 0
        if (flags and 0x000008L != 0L) cursor += 4
        if (flags and 0x000010L != 0L) {
            if (cursor + 4 > boxStart + boxSize) return null
            defaultSampleSize = readUInt32(data, cursor).toInt()
            cursor += 4
        }
        return TfhdInfo(trackId, baseDataOffset, defaultSampleSize)
    }

    private data class TrunInfo(
        val sampleCount: Int,
        val dataOffset: Long,
        val sizes: IntArray
    )

    private fun decryptTrafSamples(
        data: ByteArray,
        base: Long,
        tfhd: TfhdInfo,
        trunStart: Int,
        trunSize: Int,
        sencStart: Int,
        sencSize: Int,
        crypto: TrackCrypto,
        key: ByteArray
    ): Int {
        val trun = parseTrun(data, trunStart, trunSize, tfhd.defaultSampleSize) ?: return 0
        val sencPayload = sencStart + 8
        if (sencPayload + 8 > sencStart + sencSize) return 0
        val sencFlags = readUInt32(data, sencPayload) and 0xFFFFFF
        val sencCount = readUInt32(data, sencPayload + 4).toInt()
        if (sencCount != trun.sampleCount) {
            AppLog.putWarn("CencDecrypt: senc/trun 样本数不一致 ${sencCount}/${trun.sampleCount}")
            return 0
        }
        var sampleOffset = base + trun.dataOffset
        var sencCursor = sencPayload + 8
        var decrypted = 0
        for (index in 0 until trun.sampleCount) {
            val iv = ByteArray(16)
            if (crypto.ivSize == 16) {
                System.arraycopy(data, sencCursor, iv, 0, 16)
                sencCursor += 16
            } else {
                // 8 字节 IV：高 8 字节为 IV，低 8 字节为块计数器（从 0 开始）
                System.arraycopy(data, sencCursor, iv, 0, 8)
                sencCursor += 8
            }
            val subsampleCount = if (sencFlags and 0x000002L != 0L) {
                readUInt16(data, sencCursor).also { sencCursor += 2 }
            } else 0
            val subsamples = if (subsampleCount > 0) {
                IntArray(subsampleCount * 2).also { pairs ->
                    for (i in 0 until subsampleCount) {
                        pairs[i * 2] = readUInt16(data, sencCursor).also { sencCursor += 2 }
                        pairs[i * 2 + 1] = readUInt32(data, sencCursor).toInt().also { sencCursor += 4 }
                    }
                }
            } else null
            val sampleSize = trun.sizes[index]
            if (sampleSize <= 0) {
                sampleOffset += sampleSize
                continue
            }
            val sampleStart = sampleOffset.toInt()
            if (sampleStart < 0 || sampleStart + sampleSize > data.size) {
                AppLog.putWarn("CencDecrypt: 样本越界 offset=$sampleStart size=$sampleSize")
                return decrypted
            }
            if (subsamples == null) {
                decryptRange(data, sampleStart, sampleSize, key, iv)
            } else {
                // subsample：clear 段跳过，encrypted 段按同一 keystream 连续解密
                val cipher = newCipher(key, iv)
                var cursor = sampleStart
                var pairIndex = 0
                while (pairIndex < subsamples.size / 2) {
                    val clearBytes = subsamples[pairIndex * 2]
                    val encryptedBytes = subsamples[pairIndex * 2 + 1]
                    cursor += clearBytes
                    if (encryptedBytes > 0) {
                        if (cursor + encryptedBytes > data.size) break
                        val plain = cipher.update(data, cursor, encryptedBytes)
                        System.arraycopy(plain, 0, data, cursor, plain.size)
                        cursor += encryptedBytes
                    }
                    pairIndex++
                }
            }
            sampleOffset += sampleSize
            decrypted++
        }
        return decrypted
    }

    private fun parseTrun(
        data: ByteArray,
        boxStart: Int,
        boxSize: Int,
        defaultSampleSize: Int
    ): TrunInfo? {
        if (boxSize < 8 + 8) return null
        val payload = boxStart + 8
        val flags = readUInt32(data, payload) and 0xFFFFFF
        val sampleCount = readUInt32(data, payload + 4).toInt()
        var cursor = payload + 8
        var dataOffset = 0L
        if (flags and 0x000001L != 0L) {
            if (cursor + 4 > boxStart + boxSize) return null
            dataOffset = readUInt32(data, cursor).toLong()
            // data_offset 是 signed int32
            if (dataOffset > Int.MAX_VALUE) dataOffset -= 0x1_0000_0000L
            cursor += 4
        }
        if (flags and 0x000004L != 0L) cursor += 4
        val sizes = IntArray(sampleCount) { defaultSampleSize }
        for (i in 0 until sampleCount) {
            if (flags and 0x000100L != 0L) cursor += 4
            if (flags and 0x000200L != 0L) {
                if (cursor + 4 > boxStart + boxSize) return null
                sizes[i] = readUInt32(data, cursor).toInt()
                cursor += 4
            }
            if (flags and 0x000400L != 0L) cursor += 4
            if (flags and 0x000800L != 0L) cursor += 4
        }
        return TrunInfo(sampleCount, dataOffset, sizes)
    }

    // ------------------------------------------------------------- crypto

    private fun decryptRange(data: ByteArray, offset: Int, length: Int, key: ByteArray, iv: ByteArray) {
        val cipher = newCipher(key, iv)
        val plain = cipher.update(data, offset, length)
        System.arraycopy(plain, 0, data, offset, plain.size)
    }

    private fun newCipher(key: ByteArray, iv: ByteArray): Cipher {
        val cipher = Cipher.getInstance("AES/CTR/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), IvParameterSpec(iv))
        return cipher
    }

    // -------------------------------------------------------------- utils

    private inline fun forEachBox(
        data: ByteArray,
        start: Int,
        end: Int,
        action: (type: String, boxStart: Int, headerSize: Int, boxSize: Int) -> Unit
    ) {
        var offset = start
        while (offset + 8 <= end) {
            val size32 = readUInt32(data, offset)
            var header = 8
            var size = size32
            if (size32 == 1L) {
                if (offset + 16 > end) return
                size = readUInt64(data, offset + 8)
                header = 16
            } else if (size32 == 0L) {
                size = (end - offset).toLong()
            }
            if (size < header || size > Int.MAX_VALUE || offset + size > end) return
            action(readType(data, offset + 4), offset, header, size.toInt())
            offset += size.toInt()
        }
    }

    private fun findBox(data: ByteArray, start: Int, end: Int, type: String): Pair<Int, Int>? {
        var result: Pair<Int, Int>? = null
        forEachBox(data, start, end) { boxType, boxStart, _, boxSize ->
            if (result == null && boxType == type) result = boxStart to boxSize
        }
        return result
    }

    /** 受限深度递归查找：用于 moov 内部层级（trak>mdia>minf>stbl>stsd 等） */
    private fun findBoxDeep(
        data: ByteArray,
        start: Int,
        end: Int,
        type: String,
        depth: Int = 0
    ): Pair<Int, Int>? {
        var result: Pair<Int, Int>? = null
        forEachBox(data, start, end) { boxType, boxStart, headerSize, boxSize ->
            if (result != null) return@forEachBox
            if (boxType == type) {
                result = boxStart to boxSize
                return@forEachBox
            }
            if (depth < 6 && boxType in CONTAINER_BOXES) {
                findBoxDeep(data, boxStart + headerSize, boxStart + boxSize, type, depth + 1)
                    ?.let { result = it }
            }
        }
        return result
    }

    private val CONTAINER_BOXES = setOf(
        "moov", "trak", "mdia", "minf", "stbl", "mvex", "edts", "dinf", "udta", "sinf", "schi"
    )

    private fun readType(data: ByteArray, offset: Int): String =
        String(data, offset, 4, Charsets.US_ASCII)

    private fun writeType(data: ByteArray, offset: Int, type: String) {
        val bytes = type.toByteArray(Charsets.US_ASCII)
        if (bytes.size == 4) System.arraycopy(bytes, 0, data, offset, 4)
    }

    private fun markFree(data: ByteArray, typeOffset: Int) = writeType(data, typeOffset, FOURCC_FREE)

    private fun readUInt32(data: ByteArray, offset: Int): Long =
        ((data[offset].toLong() and 0xFF) shl 24) or
            ((data[offset + 1].toLong() and 0xFF) shl 16) or
            ((data[offset + 2].toLong() and 0xFF) shl 8) or
            (data[offset + 3].toLong() and 0xFF)

    private fun readUInt64(data: ByteArray, offset: Int): Long =
        (readUInt32(data, offset) shl 32) or readUInt32(data, offset + 4)

    private fun readUInt16(data: ByteArray, offset: Int): Int =
        ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
}
