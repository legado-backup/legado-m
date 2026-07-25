package io.legado.app.utils

import cn.hutool.core.lang.Validator
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.SocketException
import java.net.URL
import java.util.BitSet
import java.util.Enumeration

// 源码参照: app/src/main/java/io/legado/app/utils/NetworkUtils.kt#L1-L298
// 简化说明: 移除 Android ConnectivityManager/Build，PublicSuffixDatabase 简化为直接返回 host | 已知上限: getSubDomain 无法处理多级 TLD | 升级路径: 引入 PublicSuffixDatabase 或 Guava InternetDomainName

@Suppress("unused", "MemberVisibilityCanBePrivate")
object NetworkUtilsStub {

    // 内联源码 AppPattern.dataUriRegex
    private val dataUriRegex = Regex("^data:.*?;base64,(.*)")

    /**
     * 判断是否联网
     * 简化说明：JVM 环境假定网络可用 | 已知上限：无法检测真实网络状态 | 升级路径：使用 java.net.NetworkInterface 检测
     */
    fun isAvailable(): Boolean {
        return true
    }

    private val notNeedEncodingQuery: BitSet by lazy {
        val bitSet = BitSet(256)
        for (i in 'a'.code..'z'.code) {
            bitSet.set(i)
        }
        for (i in 'A'.code..'Z'.code) {
            bitSet.set(i)
        }
        for (i in '0'.code..'9'.code) {
            bitSet.set(i)
        }
        for (char in "!$&()*+,-./:;=?@[\\]^_`{|}~") {
            bitSet.set(char.code)
        }
        return@lazy bitSet
    }

    private val notNeedEncodingForm: BitSet by lazy {
        val bitSet = BitSet(256)
        for (i in 'a'.code..'z'.code) {
            bitSet.set(i)
        }
        for (i in 'A'.code..'Z'.code) {
            bitSet.set(i)
        }
        for (i in '0'.code..'9'.code) {
            bitSet.set(i)
        }
        for (char in "*-._") {
            bitSet.set(char.code)
        }
        return@lazy bitSet
    }

    /**
     * 支持JAVA的URLEncoder.encode出来的string做判断。 即: 将' '转成'+'
     * 0-9a-zA-Z保留 <br></br>
     * ! * ' ( ) ; : @ & = + $ , / ? # [ ] 保留
     * 其他字符转成%XX的格式，X是16进制的大写字符，范围是[0-9A-F]
     */
    fun encodedQuery(str: String): Boolean {
        var needEncode = false
        var i = 0
        while (i < str.length) {
            val c = str[i]
            if (notNeedEncodingQuery.get(c.code)) {
                i++
                continue
            }
            if (c == '%' && i + 2 < str.length) {
                // 判断是否符合urlEncode规范
                val c1 = str[++i]
                val c2 = str[++i]
                if (isDigit16Char(c1) && isDigit16Char(c2)) {
                    i++
                    continue
                }
            }
            // 其他字符，肯定需要urlEncode
            needEncode = true
            break
        }

        return !needEncode
    }

    fun encodedForm(str: String): Boolean {
        var needEncode = false
        var i = 0
        while (i < str.length) {
            val c = str[i]
            if (notNeedEncodingForm.get(c.code)) {
                i++
                continue
            }
            if (c == '%' && i + 2 < str.length) {
                // 判断是否符合urlEncode规范
                val c1 = str[++i]
                val c2 = str[++i]
                if (isDigit16Char(c1) && isDigit16Char(c2)) {
                    i++
                    continue
                }
            }
            // 其他字符，肯定需要urlEncode
            needEncode = true
            break
        }

        return !needEncode
    }

    /**
     * 判断c是否是16进制的字符
     */
    private fun isDigit16Char(c: Char): Boolean {
        return c in '0'..'9' || c in 'A'..'F' || c in 'a'..'f'
    }

    /**
     * 获取绝对地址
     */
    fun getAbsoluteURL(baseURL: String?, relativePath: String): String {
        if (baseURL.isNullOrEmpty()) return relativePath.trim()
        var absoluteUrl: URL? = null
        try {
            absoluteUrl = URL(baseURL.substringBefore(","))
        } catch (e: Exception) {
            // 简化说明：printOnDebug 替换为 println | 已知上限：无 | 升级路径：接入日志框架
            println(e)
        }
        return getAbsoluteURL(absoluteUrl, relativePath)
    }

    /**
     * 获取绝对地址
     */
    fun getAbsoluteURL(baseURL: URL?, relativePath: String): String {
        val relativePathTrim = relativePath.trim()
        if (baseURL == null) return relativePathTrim
        if (relativePathTrim.isAbsUrl()) return relativePathTrim
        if (relativePathTrim.isDataUrl()) return relativePathTrim
        if (relativePathTrim.startsWith("javascript")) return ""
        var relativeUrl = relativePathTrim
        try {
            val parseUrl = URL(baseURL, relativePath)
            relativeUrl = parseUrl.toString()
            return relativeUrl
        } catch (e: Exception) {
            // 简化说明：AppLog.put 替换为 println | 已知上限：无 | 升级路径：接入日志框架
            println("网址拼接出错\n${e.localizedMessage}")
        }
        return relativeUrl
    }

    fun getBaseUrl(url: String?): String? {
        url ?: return null
        if (url.startsWith("http://", true)
            || url.startsWith("https://", true)
        ) {
            val index = url.indexOf("/", 9)
            return if (index == -1) {
                url
            } else url.substring(0, index)
        }
        return null
    }

    /**
     * 获取域名，供cookie保存和读取，处理失败返回传入的url
     * http://1.2.3.4 => 1.2.3.4
     * https://www.example.com =>  example.com
     * http://www.biquge.com.cn => biquge.com.cn
     * http://www.content.example.com => example.com
     *
     * 修复 GAP-38: 对齐真机 PublicSuffixDatabase.getEffectiveTldPlusOne 行为
     * 简化说明: 使用 takeLast(2) 提取基础域名，不引入 PublicSuffixDatabase 依赖 | 已知上限: 不处理多级TLD(.co.uk/.com.cn) | 升级路径: 引入 PublicSuffixDatabase
     */
    fun getSubDomain(url: String): String {
        val baseUrl = getBaseUrl(url) ?: return url
        return kotlin.runCatching {
            val mURL = URL(baseUrl)
            val host: String = mURL.host
            //mURL.scheme https/http
            //判断是否为ip
            if (isIPAddress(host)) return host
            // 修复 GAP-38: 取最后两部分作为基础域名，对齐真机 getEffectiveTldPlusOne 行为
            val parts = host.split(".")
            return if (parts.size >= 2) parts.takeLast(2).joinToString(".") else host
        }.getOrDefault(baseUrl)
    }

    fun getSubDomainOrNull(url: String): String? {
        val baseUrl = getBaseUrl(url) ?: return null
        return kotlin.runCatching {
            val mURL = URL(baseUrl)
            val host: String = mURL.host
            //mURL.scheme https/http
            //判断是否为ip
            if (isIPAddress(host)) return host
            // 修复 GAP-38: 取最后两部分作为基础域名，对齐真机 getEffectiveTldPlusOne 行为
            val parts = host.split(".")
            return if (parts.size >= 2) parts.takeLast(2).joinToString(".") else host
        }.getOrDefault(null)
    }

    fun getDomain(url: String): String {
        val baseUrl = getBaseUrl(url) ?: return url
        return kotlin.runCatching {
            URL(baseUrl).host
        }.getOrDefault(baseUrl)
    }

    /**
     * Get local Ip address.
     */
    fun getLocalIPAddress(): List<InetAddress> {
        val enumeration: Enumeration<NetworkInterface>
        try {
            enumeration = NetworkInterface.getNetworkInterfaces()
        } catch (e: SocketException) {
            // 简化说明：printOnDebug 替换为 println | 已知上限：无 | 升级路径：接入日志框架
            println(e)
            return emptyList()
        }

        val addressList = mutableListOf<InetAddress>()

        while (enumeration.hasMoreElements()) {
            val nif = enumeration.nextElement()
            val addresses = nif.inetAddresses ?: continue
            while (addresses.hasMoreElements()) {
                val address = addresses.nextElement()
                if (!address.isLoopbackAddress && isIPv4Address(address.hostAddress)) {
                    addressList.add(address)
                }
            }
        }
        return addressList
    }

    /**
     * Check if valid IPV4 address.
     *
     * @param input the address string to check for validity.
     * @return True if the input parameter is a valid IPv4 address.
     */
    fun isIPv4Address(input: String?): Boolean {
        return input != null && input.isNotEmpty()
                && input[0] in '1'..'9'
                && input.count { it == '.' } == 3
                && Validator.isIpv4(input)
    }

    /**
     * Check if valid IPV6 address.
     */
    fun isIPv6Address(input: String?): Boolean {
        return input != null && input.contains(":") && Validator.isIpv6(input)
    }

    /**
     * Check if valid IP address.
     */
    fun isIPAddress(input: String?): Boolean {
        return isIPv4Address(input) || isIPv6Address(input)
    }

    // ===== 以下为内联的 StringExtensions 扩展函数 =====
    // 源码参照: app/src/main/java/io/legado/app/utils/StringExtensions.kt#L38-L46

    private fun String?.isAbsUrl(): Boolean =
        this?.let {
            it.startsWith("http://", true) || it.startsWith("https://", true)
        } ?: false

    private fun String?.isDataUrl(): Boolean =
        this?.let {
            dataUriRegex.matches(it)
        } ?: false
}
