package io.legado.app.help.exoplayer

import androidx.media3.common.C
import androidx.media3.common.DataReader
import androidx.media3.common.DrmInitData
import androidx.media3.common.Format
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.ParsableByteArray
import androidx.media3.common.util.UnstableApi
import androidx.media3.extractor.Extractor
import androidx.media3.extractor.ExtractorInput
import androidx.media3.extractor.ExtractorOutput
import androidx.media3.extractor.ExtractorsFactory
import androidx.media3.extractor.PositionHolder
import androidx.media3.extractor.SeekMap
import androidx.media3.extractor.TrackOutput
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * CENC 初始化段补丁：为「无 pssh」的 CENC fMP4 合成 ClearKey PSSH（设计 AD-04 前置能力）。
 *
 * 背景（2026-10-27 逆向/抓流铁证）：目标流为标准 CENC（`tenc`+`senc`），但 **moov 内没有 pssh**。
 * Media3 `DefaultDrmSessionManager` 在 `DrmInitData` 无匹配 schemeData 时会抛
 * `MissingSchemeDataException` ⇒ 即使有正确 key 也无法建会话。
 *
 * 方案（不重写字节流、不改 DataSource）：在 Extractor 输出侧给 `Format` 补一条
 * `SchemeData(CLEARKEY_UUID, "video/mp4", 合成 pssh)`；kid 由书源声明（服务端下发），无需解包敏感数据。
 * 该包装仅对**声明 CENC 的 progressive fMP4** 挂载，其余播放路径完全不变。
 */
@OptIn(UnstableApi::class)
internal class CencDrmInitInjectingExtractorsFactory(
    private val delegate: ExtractorsFactory,
    private val kidHex: String
) : ExtractorsFactory {

    override fun createExtractors(): Array<Extractor> =
        delegate.createExtractors().map { CencDrmInitInjectingExtractor(it, kidHex) }.toTypedArray()
}

@OptIn(UnstableApi::class)
internal class CencDrmInitInjectingExtractor(
    private val delegate: Extractor,
    kidHex: String
) : Extractor {

    private val pssh: ByteArray = buildClearKeyPssh(kidHex)

    override fun sniff(input: ExtractorInput): Boolean = delegate.sniff(input)

    override fun init(output: ExtractorOutput) {
        delegate.init(object : ExtractorOutput {
            override fun track(id: Int, type: Int): TrackOutput =
                CencDrmInitInjectingTrackOutput(output.track(id, type), pssh)

            override fun endTracks() = output.endTracks()

            override fun seekMap(seekMap: SeekMap) = output.seekMap(seekMap)
        })
    }

    override fun read(input: ExtractorInput, seekPosition: PositionHolder): Int =
        delegate.read(input, seekPosition)

    override fun seek(position: Long, timeUs: Long) = delegate.seek(position, timeUs)

    override fun release() = delegate.release()
}

@OptIn(UnstableApi::class)
private class CencDrmInitInjectingTrackOutput(
    private val delegate: TrackOutput,
    private val pssh: ByteArray
) : TrackOutput {

    override fun format(format: Format) {
        delegate.format(format.withClearKeyDrmInitData(pssh))
    }

    override fun sampleData(input: DataReader, length: Int, allowEndOfInput: Boolean, sampleDataPart: Int): Int =
        delegate.sampleData(input, length, allowEndOfInput, sampleDataPart)

    override fun sampleData(data: ParsableByteArray, length: Int, sampleDataPart: Int) =
        delegate.sampleData(data, length, sampleDataPart)

    override fun sampleMetadata(
        timeUs: Long,
        flags: Int,
        size: Int,
        offset: Int,
        cryptoData: TrackOutput.CryptoData?
    ) = delegate.sampleMetadata(timeUs, flags, size, offset, cryptoData)
}

/**
 * 若 Format 已含 ClearKey schemeData 则不重复注入；否则把合成 pssh 与既有 schemeData 合并。
 */
@OptIn(UnstableApi::class)
internal fun Format.withClearKeyDrmInitData(pssh: ByteArray): Format {
    val existing = drmInitData
    if (existing != null) {
        for (index in 0 until existing.schemeDataCount) {
            if (existing.get(index).matches(C.CLEARKEY_UUID)) return this
        }
    }
    val schemeData = ArrayList<DrmInitData.SchemeData>(1 + (existing?.schemeDataCount ?: 0))
    schemeData.add(DrmInitData.SchemeData(C.CLEARKEY_UUID, MimeTypes.VIDEO_MP4, pssh))
    if (existing != null) {
        for (index in 0 until existing.schemeDataCount) {
            schemeData.add(existing.get(index))
        }
    }
    return buildUpon().setDrmInitData(DrmInitData(schemeData)).build()
}

/**
 * 合成 W3C ClearKey PSSH（version 1，含 kid 列表）。
 *
 * 布局：size(4) + 'pssh'(4) + version/flags(4=0x01000000) + systemId(16) + kidCount(4) + kid(16*n)
 * systemId 使用 [C.CLEARKEY_UUID]（e2719d58-a985-b3c9-781a-b030af78d30e，Android ClearKey 插件可识别）。
 */
internal fun buildClearKeyPssh(kidHex: String): ByteArray {
    val kid = hexToBytesOrNull(kidHex) ?: ByteArray(16)
    val size = 8 + 4 + 16 + 4 + kid.size
    val buffer = ByteBuffer.allocate(size).order(ByteOrder.BIG_ENDIAN)
    buffer.putInt(size)
    buffer.put("pssh".toByteArray(Charsets.US_ASCII))
    buffer.putInt(0x01000000)
    buffer.putLong(C.CLEARKEY_UUID.mostSignificantBits)
    buffer.putLong(C.CLEARKEY_UUID.leastSignificantBits)
    buffer.putInt(1)
    buffer.put(kid)
    return buffer.array()
}
