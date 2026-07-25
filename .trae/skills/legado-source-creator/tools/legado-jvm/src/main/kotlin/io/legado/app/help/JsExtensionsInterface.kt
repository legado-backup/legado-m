package io.legado.app.help

import cn.hutool.crypto.symmetric.SymmetricCrypto
import io.legado.app.help.crypto.AsymmetricCrypto
import io.legado.app.help.crypto.Sign
import io.legado.app.help.http.StrResponse
import io.legado.app.model.analyzeRule.QueryTTF
import io.legado.app.utils.JsURL
import org.jsoup.Connection
import java.io.File

/**
 * JsExtensions 纯接口，无 Android 依赖。
 * 包含 JsExtensions（102方法）+ JsEncodeUtils（30方法）= 132 个方法。
 * 源码参照：app/src/main/java/io/legado/app/help/JsExtensions.kt
 *          app/src/main/java/io/legado/app/help/JsEncodeUtils.kt
 */
@Suppress("unused")
interface JsExtensionsInterface {

    // ==================== 抽象方法（由 Debugger 传入）====================

    fun getSource(): Any?

    fun getTag(): String?

    // ==================== HTTP 方法（18个）====================

    fun ajax(url: Any): String?

    fun ajax(url: Any, callTimeout: Long?): String?

    fun ajaxAll(urlList: Array<String>): Array<StrResponse>

    fun ajaxAll(urlList: Array<String>, skipRateLimit: Boolean): Array<StrResponse>

    fun ajaxTestAll(urlList: Array<String>, timeout: Int): Array<StrResponse>

    fun ajaxTestAll(urlList: Array<String>, timeout: Int, skipRateLimit: Boolean): Array<StrResponse>

    fun connect(urlStr: String): StrResponse

    fun connect(urlStr: String, header: String?): StrResponse

    fun connect(urlStr: String, header: String?, callTimeout: Long?): StrResponse

    fun get(urlStr: String, headers: Map<String, String>): Connection.Response

    fun get(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response

    fun head(urlStr: String, headers: Map<String, String>): Connection.Response

    fun head(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response

    fun post(urlStr: String, body: String, headers: Map<String, String>): Connection.Response

    fun post(urlStr: String, body: String, headers: Map<String, String>, timeout: Int?): Connection.Response

    // ==================== WebView 方法（9个）====================

    fun webView(html: String?, url: String?, js: String?): String?

    fun webView(html: String?, url: String?, js: String?, cacheFirst: Boolean): String?

    fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String): String?

    fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String, cacheFirst: Boolean): String?

    fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String, cacheFirst: Boolean, delayTime: Long): String?

    fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String): String?

    fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String, cacheFirst: Boolean): String?

    fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String, cacheFirst: Boolean, delayTime: Long): String?

    // ==================== UI 方法（不可用，8个）====================

    fun openVideoPlayer(url: String, title: String)

    fun openVideoPlayer(url: String, title: String, isFloat: Boolean)

    fun startBrowser(url: String, title: String)

    fun startBrowser(url: String, title: String, html: String?)

    fun startBrowserAwait(url: String, title: String): StrResponse

    fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean): StrResponse

    fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean, html: String?): StrResponse

    fun getVerificationCode(imageUrl: String): String

    // ==================== Cookie 方法（2个）====================

    fun getCookie(tag: String): String

    fun getCookie(tag: String, key: String?): String

    // ==================== 文件方法（14个）====================

    fun importScript(path: String): String

    fun cacheFile(urlStr: String): String

    fun cacheFile(urlStr: String, saveTime: Int): String

    fun downloadFile(url: String): String

    @Deprecated("Deprecated", ReplaceWith("downloadFile(url)"))
    fun downloadFile(content: String, url: String): String

    fun getFile(path: String): File

    fun readFile(path: String): ByteArray?

    fun readTxtFile(path: String): String

    fun readTxtFile(path: String, charsetName: String): String

    fun deleteFile(path: String): Boolean

    fun unzipFile(zipPath: String): String

    fun un7zFile(zipPath: String): String

    fun unrarFile(zipPath: String): String

    fun unArchiveFile(zipPath: String): String

    fun getTxtInFolder(path: String): String

    // ==================== 压缩方法（9个）====================

    fun getZipStringContent(url: String, path: String): String

    fun getZipStringContent(url: String, path: String, charsetName: String): String

    fun getRarStringContent(url: String, path: String): String

    fun getRarStringContent(url: String, path: String, charsetName: String): String

    fun get7zStringContent(url: String, path: String): String

    fun get7zStringContent(url: String, path: String, charsetName: String): String

    fun getZipByteArrayContent(url: String, path: String): ByteArray?

    fun getRarByteArrayContent(url: String, path: String): ByteArray?

    fun get7zByteArrayContent(url: String, path: String): ByteArray?

    // ==================== Base64 方法（7个）====================

    fun base64Decode(str: String?): String

    fun base64Decode(str: String?, charset: String): String

    fun base64Decode(str: String, flags: Int): String

    fun base64DecodeToByteArray(str: String?): ByteArray?

    fun base64DecodeToByteArray(str: String?, flags: Int): ByteArray?

    fun base64Encode(str: String): String?

    fun base64Encode(str: String, flags: Int): String?

    // ==================== Hex 方法（3个）====================

    fun hexDecodeToByteArray(hex: String): ByteArray?

    fun hexDecodeToString(hex: String): String?

    fun hexEncodeToString(utf8: String): String?

    // ==================== 转换方法（4个）====================

    fun strToBytes(str: String): ByteArray

    fun strToBytes(str: String, charset: String): ByteArray

    fun bytesToStr(bytes: ByteArray): String

    fun bytesToStr(bytes: ByteArray, charset: String): String

    // ==================== 时间方法（2个）====================

    fun timeFormatUTC(time: Long, format: String, sh: Int): String?

    fun timeFormat(time: Long): String

    // ==================== 编码方法（5个）====================

    fun encodeURI(str: String): String

    fun encodeURI(str: String, enc: String): String

    fun htmlFormat(str: String): String

    fun t2s(text: String): String

    fun s2t(text: String): String

    // ==================== 字体方法（5个）====================

    @Deprecated("Deprecated", ReplaceWith("queryTTF(data)"))
    fun queryBase64TTF(data: String?): QueryTTF?

    fun queryTTF(data: Any?, useCache: Boolean): QueryTTF?

    fun queryTTF(data: Any?): QueryTTF?

    fun replaceFont(text: String, errorQueryTTF: QueryTTF?, correctQueryTTF: QueryTTF?, filter: Boolean): String

    fun replaceFont(text: String, errorQueryTTF: QueryTTF?, correctQueryTTF: QueryTTF?): String

    // ==================== 工具方法（9个）====================

    fun toNumChapter(s: String?): String?

    fun toURL(urlStr: String): JsURL

    fun toURL(url: String, baseUrl: String? = null): JsURL

    fun toast(msg: Any?)

    fun longToast(msg: Any?)

    fun log(msg: Any?): Any?

    fun logType(any: Any?)

    fun randomUUID(): String

    fun androidId(): String

    fun getWebViewUA(): String

    // ==================== UI/Url 方法（2个，不可用）====================

    fun openUrl(url: String)

    fun openUrl(url: String, mimeType: String? = null)

    // ==================== 配置方法（5个）====================

    fun getReadBookConfig(): String

    fun getReadBookConfigMap(): Map<String, Any>

    fun getThemeMode(): String

    fun getThemeConfig(): String

    fun getThemeConfigMap(): Map<String, Any?>

    // ==================== JsEncodeUtils 继承方法（30个）====================

    // ----- MD5（2个）-----
    fun md5Encode(str: String): String

    fun md5Encode16(str: String): String

    // ----- 对称加密（4个）-----
    fun createSymmetricCrypto(transformation: String, key: ByteArray?, iv: ByteArray?): SymmetricCrypto

    fun createSymmetricCrypto(transformation: String, key: ByteArray): SymmetricCrypto

    fun createSymmetricCrypto(transformation: String, key: String): SymmetricCrypto

    fun createSymmetricCrypto(transformation: String, key: String, iv: String?): SymmetricCrypto

    // ----- 非对称加密（1个）-----
    fun createAsymmetricCrypto(transformation: String): AsymmetricCrypto

    // ----- 签名（1个）-----
    fun createSign(algorithm: String): Sign

    // ----- AES（8个）-----
    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(str)"))
    fun aesDecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(str)"))
    fun aesDecodeToString(str: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun aesDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(str)"))
    fun aesBase64DecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(str)"))
    fun aesBase64DecodeToString(str: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(data)"))
    fun aesEncodeToByteArray(data: String, key: String, transformation: String, iv: String): ByteArray?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun aesEncodeToString(data: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data).toByteArray()"))
    fun aesEncodeToBase64ByteArray(data: String, key: String, transformation: String, iv: String): ByteArray?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    fun aesEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    fun aesEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?

    // ----- DES（4个）-----
    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun desDecodeToString(data: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun desBase64DecodeToString(data: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encrypt(data)"))
    fun desEncodeToString(data: String, key: String, transformation: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    fun desEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String?

    // ----- 3DES（4个）-----
    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun tripleDESDecodeStr(data: String, key: String, mode: String, padding: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    fun tripleDESDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    fun tripleDESEncodeBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    fun tripleDESEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?

    // ----- 摘要/HMac（4个）-----
    fun digestHex(data: String, algorithm: String): String

    fun digestBase64Str(data: String, algorithm: String): String

    @Suppress("FunctionName")
    fun HMacHex(data: String, algorithm: String, key: String): String

    @Suppress("FunctionName")
    fun HMacBase64(data: String, algorithm: String, key: String): String

}
