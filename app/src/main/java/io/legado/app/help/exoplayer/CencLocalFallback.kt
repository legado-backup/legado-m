package io.legado.app.help.exoplayer

import android.media.MediaDrm
import androidx.media3.common.C
import io.legado.app.constant.AppLog
import io.legado.app.help.http.okHttpClient
import io.legado.app.utils.MD5Utils
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.withContext
import okhttp3.Request
import splitties.init.appCtx
import java.io.File

/**
 * CENC 软件降级入口（设计 AD-04）：设备不支持 ClearKey 时，先本地解密再按普通文件播放。
 *
 * 触发条件（全部满足才生效，其余零影响）：
 * 1. 书源声明 `encryption=cenc-aes-ctr` 且有合法 kid；
 * 2. 本机 `MediaDrm` 不支持 ClearKey 方案；
 * 3. `CencKeyProvider` 能拿到 16 字节 key。
 *
 * 解密结果按 `url+kid` 摘要缓存到 `cacheDir/cenc/`，跨集/重播复用；失败一律返回 null（回落到原路径）。
 */
object CencLocalFallback {

    /** 单文件上限：软件解密需整段驻留内存，短剧单集 10~80MB，留足余量但不无限吃内存 */
    private const val MAX_BYTES = 192L * 1024 * 1024

    /**
     * 缓存文件版本盐：参与文件名摘要。
     * 必须随「解密重写算法」变更递增 —— 否则同名旧产物会被 ExoPlayer 的 SimpleCache（按 URI 键）
     * 命中旧字节，导致明明已重写的新文件仍按旧结构解析（2026-10-27 真机铁证）。
     */
    private const val CACHE_VERSION = "cenc-rw2"

    /** 本机是否具备 ClearKey MediaDrm（不支持才需要软件降级） */
    fun isClearKeySupported(): Boolean =
        kotlin.runCatching { MediaDrm.isCryptoSchemeSupported(C.CLEARKEY_UUID) }.getOrDefault(false)

    /** 是否需要走软件降级 */
    fun isRequired(kid: String?, encryption: String?): Boolean =
        CencDrmSessionProvider.isCencEncryption(encryption) &&
            CencDrmSessionProvider.normalizeKid(kid) != null &&
            !isClearKeySupported()

    /**
     * 下载 + 解密 + 落盘缓存。
     *
     * @return 明文 fMP4 本地文件；任何前置条件不满足或失败返回 null（调用方保持原逻辑）
     */
    suspend fun prepare(
        url: String,
        headers: Map<String, String>,
        kid: String,
        key: ByteArray
    ): File? = withContext(IO) {
        val normalizedKid = CencDrmSessionProvider.normalizeKid(kid) ?: return@withContext null
        val dir = File(appCtx.cacheDir, "cenc").apply { mkdirs() }
        val target = File(dir, MD5Utils.md5Encode("$CACHE_VERSION|$url|$normalizedKid") + ".mp4")
        if (target.isFile && target.length() > 0) {
            AppLog.put("CencFallback: 命中本地解密缓存, size=${target.length()}")
            return@withContext target
        }
        val bytes = download(url, headers) ?: return@withContext null
        val result = kotlin.runCatching { CencFmp4Decryptor.decrypt(bytes, key) }.getOrElse { error ->
            AppLog.put("CencFallback: 解密失败 ${error.javaClass.simpleName}", error)
            return@withContext null
        }
        val stats = result.stats
        if (stats.sampleCount <= 0) {
            AppLog.putWarn("CencFallback: 未发现可解密样本（可能非 cenc 或盒结构不支持）")
            return@withContext null
        }
        val plainBytes = result.bytes
        val temp = File(dir, target.name + ".tmp")
        kotlin.runCatching {
            temp.writeBytes(plainBytes)
            if (target.exists()) target.delete()
            if (!temp.renameTo(target)) {
                temp.copyTo(target, overwrite = true)
                temp.delete()
            }
        }.onFailure {
            AppLog.put("CencFallback: 落盘失败 ${it.javaClass.simpleName}", it)
            temp.delete()
            return@withContext null
        }
        AppLog.put(
            "CencFallback: 本地解密完成, tracks=${stats.trackCount}, samples=${stats.sampleCount}, " +
                "patched=${stats.patchedBoxes}, size=${target.length()}"
        )
        target
    }

    private fun download(url: String, headers: Map<String, String>): ByteArray? {
        val builder = Request.Builder().url(url)
        headers.forEach { (name, value) ->
            // Host/Content-Length 等由 OkHttp 自管，避免非法 header
            if (name.equals("Host", true) || name.equals("Content-Length", true)) return@forEach
            kotlin.runCatching { builder.header(name, value) }
        }
        val response = kotlin.runCatching { okHttpClient.newCall(builder.build()).execute() }
            .getOrElse {
                AppLog.put("CencFallback: 下载请求失败 ${it.javaClass.simpleName}")
                return null
            }
        response.use { resp ->
            if (!resp.isSuccessful) {
                AppLog.putWarn("CencFallback: 下载失败 code=${resp.code}")
                return null
            }
            val body = resp.body ?: return null
            val declared = body.contentLength()
            if (declared > MAX_BYTES) {
                AppLog.putWarn("CencFallback: 媒体过大(${declared})，放弃软件解密")
                return null
            }
            val stream = body.byteStream()
            val output = java.io.ByteArrayOutputStream(if (declared > 0) declared.toInt() else 1 shl 20)
            val buffer = ByteArray(64 * 1024)
            var total = 0L
            while (true) {
                val read = stream.read(buffer)
                if (read < 0) break
                total += read
                if (total > MAX_BYTES) {
                    AppLog.putWarn("CencFallback: 媒体超限($total)，放弃软件解密")
                    return null
                }
                output.write(buffer, 0, read)
            }
            return output.toByteArray()
        }
    }
}
