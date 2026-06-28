package io.legado.app.help.http

import io.legado.app.utils.EncodingDetect
import io.legado.app.utils.GSON
import io.legado.app.utils.Utf8BomUtils
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.FormBody
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.ResponseBody
import okhttp3.internal.http.RealResponseBody
import okio.buffer
import okio.source
import java.io.File
import java.io.IOException
import java.nio.charset.Charset
import java.util.zip.ZipInputStream
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

// 源码参照: app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt
// 仿真端已对齐: 集成 EncodingDetect + Utf8BomUtils，编码检测逻辑与真机一致（icu4j fallback 除外）

suspend fun OkHttpClient.newCallResponse(
    retry: Int = 0,
    builder: Request.Builder.() -> Unit
): Response {
    val requestBuilder = Request.Builder()
    requestBuilder.apply(builder)
    var response: Response? = null
    for (i in 0..retry) {
        response = newCall(requestBuilder.build()).await()
        if (response.isSuccessful) {
            return response
        }
    }
    return response!!
}

// 源码参照: app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt:45-50
suspend fun OkHttpClient.newCallResponseBody(
    retry: Int = 0,
    builder: Request.Builder.() -> Unit
): ResponseBody {
    return newCallResponse(retry, builder).body
}

suspend fun OkHttpClient.newCallStrResponse(
    retry: Int = 0,
    builder: Request.Builder.() -> Unit
): StrResponse {
    return newCallResponse(retry, builder).let {
        StrResponse(it, it.body.text())
    }
}

// 源码参照: app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt:61-77
// 仿真端已对齐: invokeOnCancellation 协程取消 + onFailure 在前（与真机一致）
suspend fun Call.await(): Response = suspendCancellableCoroutine { cont ->
    cont.invokeOnCancellation {
        cancel()
    }
    enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            cont.resumeWithException(e)
        }

        override fun onResponse(call: Call, response: Response) {
            cont.resume(response)
        }
    })
}

// 源码参照: app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt ResponseBody.text()
// 仿真端已对齐: 编码检测优先级 encode参数 -> HTTP头contentType -> HTML meta标签 -> UTF-8（真机最后一步用icu4j）
fun ResponseBody.text(encode: String? = null): String {
    val responseBytes = Utf8BomUtils.removeUTF8BOM(bytes())
    var charsetName: String? = encode

    charsetName?.let {
        return String(responseBytes, Charset.forName(it))
    }

    //根据http头判断
    contentType()?.charset()?.let { charset ->
        return String(responseBytes, charset)
    }

    //根据内容判断
    charsetName = EncodingDetect.getHtmlEncode(responseBytes)
    return String(responseBytes, Charset.forName(charsetName))
}

// 源码参照: app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt:97-111
// 处理 application/zip 类型的响应体（如压缩主题文件、TXT规则）
fun ResponseBody.decompressed(): ResponseBody {
    val contentType = contentType()?.toString()
    if (contentType != "application/zip") {
        return this
    }
    val source = ZipInputStream(byteStream()).apply {
        try {
            nextEntry
        } catch (e: Exception) {
            close()
            throw e
        }
    }.source().buffer()
    return RealResponseBody(null, -1, source)
}

fun Request.Builder.addHeaders(headers: Map<String, String>) {
    headers.forEach {
        addHeader(it.key, it.value)
    }
}

fun Request.Builder.get(url: String, queryMap: Map<String, String>, encoded: Boolean = false) {
    val httpBuilder = url.toHttpUrl().newBuilder()
    queryMap.forEach {
        if (encoded) {
            httpBuilder.addEncodedQueryParameter(it.key, it.value)
        } else {
            httpBuilder.addQueryParameter(it.key, it.value)
        }
    }
    url(httpBuilder.build())
}

fun Request.Builder.get(url: String, encodedQuery: String?) {
    val httpBuilder = url.toHttpUrl().newBuilder()
    httpBuilder.encodedQuery(encodedQuery)
    url(httpBuilder.build())
}

private val formContentType = "application/x-www-form-urlencoded".toMediaType()

fun Request.Builder.postForm(encodedForm: String) {
    post(encodedForm.toRequestBody(formContentType))
}

@Suppress("unused")
fun Request.Builder.postForm(form: Map<String, String>, encoded: Boolean = false) {
    val formBody = FormBody.Builder()
    form.forEach {
        if (encoded) {
            formBody.addEncoded(it.key, it.value)
        } else {
            formBody.add(it.key, it.value)
        }
    }
    post(formBody.build())
}

fun Request.Builder.postMultipart(type: String?, form: Map<String, Any>) {
    val multipartBody = MultipartBody.Builder()
    type?.let {
        multipartBody.setType(type.toMediaType())
    }
    form.forEach {
        when (val value = it.value) {
            is Map<*, *> -> {
                val fileName = value["fileName"] as String
                val file = value["file"]
                val mediaType = (value["contentType"] as? String)?.toMediaType()
                val requestBody = when (file) {
                    is File -> {
                        file.asRequestBody(mediaType)
                    }

                    is ByteArray -> {
                        file.toRequestBody(mediaType)
                    }

                    is String -> {
                        file.toRequestBody(mediaType)
                    }

                    else -> {
                        GSON.toJson(file).toRequestBody(mediaType)
                    }
                }
                multipartBody.addFormDataPart(it.key, fileName, requestBody)
            }

            else -> multipartBody.addFormDataPart(it.key, it.value.toString())
        }
    }
    post(multipartBody.build())
}

fun Request.Builder.postJson(json: String?) {
    json?.let {
        val requestBody = json.toRequestBody("application/json; charset=UTF-8".toMediaType())
        post(requestBody)
    }
}
