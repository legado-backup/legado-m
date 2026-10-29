package io.legado.app.ui.association

import android.app.Application
import android.net.Uri
import androidx.lifecycle.MutableLiveData
import io.legado.app.R
import io.legado.app.constant.AppLog
import io.legado.app.constant.AppPattern
import io.legado.app.constant.AppPattern.bookFileRegex
import io.legado.app.data.entities.Book
import io.legado.app.model.localBook.LocalBook
import io.legado.app.utils.*
import io.legado.app.utils.compress.ZipUtils
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

class FileAssociationViewModel(application: Application) : BaseAssociationViewModel(application) {
    val importBookLiveData = MutableLiveData<Uri>()
    val importRedThemeLiveData = MutableLiveData<Uri>()
    val importBubbleLiveData = MutableLiveData<Uri>()
    val onLineImportLive = MutableLiveData<Uri>()
    val openBookLiveData = MutableLiveData<Book>()
    val notSupportedLiveData = MutableLiveData<Pair<Uri, String>>()

    fun dispatchIntent(uri: Uri) {
        execute {
            //如果是普通的url，需要根据返回的内容判断是什么
            if (uri.isContentScheme() || uri.isFileScheme()) {
                val fileDoc = FileDoc.fromUri(uri, false)
                val fileName = fileDoc.name
                if (fileName.endsWith(".red", ignoreCase = true)) {
                    importRedThemeLiveData.postValue(fileDoc.uri)
                    return@execute
                }
                if (fileName.matches(AppPattern.archiveFileRegex)) {
                    if (fileName.endsWith(".zip", ignoreCase = true) && isThemeZip(fileDoc)) {
                        importRedThemeLiveData.postValue(fileDoc.uri)
                        return@execute
                    }
                    if (fileName.endsWith(".zip", ignoreCase = true) && isBubbleZip(fileDoc)) {
                        importBubbleLiveData.postValue(fileDoc.uri)
                        return@execute
                    }
                    ArchiveUtils.deCompress(fileDoc, ArchiveUtils.TEMP_PATH) {
                        it.matches(bookFileRegex) || it.endsWith(".red", ignoreCase = true)
                    }.forEach {
                        dispatch(FileDoc.fromFile(it))
                    }
                } else {
                    dispatch(fileDoc)
                }
            } else {
                onLineImportLive.postValue(uri)
            }
        }.onError {
            it.printOnDebug()
            // M6-4（修复 3）：壳内失败文案资源化（原硬编码中文）
            val msg = getApplication<Application>().getString(
                R.string.association_open_file_failed, it.localizedMessage
            )
            errorLive.postValue(msg)
            AppLog.put(msg, it)
        }
    }

    /**
     * 分发外部文件（external-json-open-import-fix / spec R1~R4）。
     *
     * 判定顺序改为**扩展名 → MIME → 内容首部**：原实现只用
     * `openInputStream().getOrNull().isJson()` 做流采样（依赖 `available()` 且要求首尾闭合），
     * 跨进程 Provider（QQ/微信 fileprovider）下会把合法 JSON 判成非 JSON；且流打不开时
     * `getOrNull()` 为 null 被静默当作「非 JSON」，最终误走书籍导入并报空文件。
     */
    private fun dispatch(fileDoc: FileDoc) {
        // 压缩包内解出的 .red 也走这里（dispatchIntent 的解压过滤保留 .red）
        if (fileDoc.name.endsWith(".red", ignoreCase = true)) {
            importRedThemeLiveData.postValue(fileDoc.uri)
            return
        }
        val mime = kotlin.runCatching { context.contentResolver.getType(fileDoc.uri) }.getOrNull()
        when (AssociationFileKindPolicy.kindOf(fileDoc.name, mime)) {
            AssociationFileKindPolicy.Kind.JSON -> {
                importJsonFile(fileDoc)
                return
            }

            AssociationFileKindPolicy.Kind.BOOK -> {
                importBookLiveData.postValue(fileDoc.uri)
                return
            }

            null -> Unit
        }
        // 扩展名与 MIME 都没有结论：读首部兜底（只读首部，不读尾部、不看 available）
        val input = fileDoc.openInputStream().getOrNull()
        if (input == null) {
            notSupportedLiveData.postValue(Pair(fileDoc.uri, displayName(fileDoc)))
            return
        }
        input.use { stream ->
            val head = ByteArray(AssociationFileKindPolicy.HEAD_BYTES)
            val headLen = readFully(stream, head)
            if (!AssociationFileKindPolicy.looksLikeJson(head, headLen)) {
                notSupportedLiveData.postValue(Pair(fileDoc.uri, displayName(fileDoc)))
                return
            }
            // 首部已被读走：把首部续写入缓存后再拷剩余，全程只打开这一次源流
            materializeJson(fileDoc, stream, head, headLen)
        }
    }

    /** 扩展名/MIME 已定性为 JSON：单流打开并物化。 */
    private fun importJsonFile(fileDoc: FileDoc) {
        val input = fileDoc.openInputStream().getOrNull()
        if (input == null) {
            failUnreadable(fileDoc)
            return
        }
        input.use { stream -> materializeJson(fileDoc, stream, null, 0) }
    }

    /**
     * 把 JSON 内容一次性落到应用缓存（spec R4）。
     *
     * 后续 `importJson` 与导入弹层都读缓存文件：规避 Provider 重复打开失败与
     * `DocumentFile.length()` 不可靠（后者正是原路径报 `Unexpected empty File` 的直接触发点）。
     *
     * @param head 首部兜底路径已读出的字节（快路径为 null）
     * @param headLen 首部实际字节数
     */
    private fun materializeJson(
        fileDoc: FileDoc,
        stream: InputStream,
        head: ByteArray?,
        headLen: Int
    ) {
        val cacheDir = File(context.externalFiles, JSON_CACHE_DIR).apply { mkdirs() }
        purgeExpiredCache(cacheDir)
        val target = allocateCacheFile(cacheDir, fileDoc.name)
        var total = 0L
        var oversized = false
        kotlin.runCatching {
            FileOutputStream(target).use { out ->
                if (head != null && headLen > 0) {
                    out.write(head, 0, headLen)
                    total += headLen
                }
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    val read = stream.read(buffer)
                    if (read <= 0) break
                    total += read
                    if (total > AssociationFileKindPolicy.MAX_JSON_BYTES) {
                        oversized = true
                        break
                    }
                    out.write(buffer, 0, read)
                }
            }
        }.onFailure {
            it.printOnDebug()
            target.delete()
            AppLog.put("JSON 物化失败\n${it.localizedMessage}", it)
            failUnreadable(fileDoc)
            return
        }
        when {
            oversized -> {
                target.delete()
                val msg = context.getString(R.string.association_file_too_large, displayName(fileDoc))
                AppLog.put(msg)
                errorLive.postValue(msg)
            }

            total <= 0L -> {
                target.delete()
                failUnreadable(fileDoc)
            }

            else -> importJson(Uri.fromFile(target))
        }
    }

    /** 清理早于 TTL 的旧缓存，防止跨次导入堆积。 */
    private fun purgeExpiredCache(cacheDir: File) {
        val now = System.currentTimeMillis()
        cacheDir.listFiles()?.forEach {
            if (AssociationFileKindPolicy.isCacheExpired(it.lastModified(), now)) it.delete()
        }
    }

    /** 分配缓存文件；同毫秒同名冲突时追加序号，避免覆盖上一次仍在弹层中使用的缓存。 */
    private fun allocateCacheFile(cacheDir: File, name: String?): File {
        val fileName = AssociationFileKindPolicy.cacheFileName(System.currentTimeMillis(), name)
        var target = File(cacheDir, fileName)
        if (!target.exists()) return target
        val base = fileName.removeSuffix(".json")
        var index = 1
        while (target.exists()) {
            target = File(cacheDir, "${base}_$index.json")
            index++
        }
        return target
    }

    /** 读满首部（`InputStream.read` 不保证一次读满）。 */
    private fun readFully(stream: InputStream, buffer: ByteArray): Int {
        var total = 0
        while (total < buffer.size) {
            val read = stream.read(buffer, total, buffer.size - total)
            if (read <= 0) break
            total += read
        }
        return total
    }

    private fun displayName(fileDoc: FileDoc): String =
        fileDoc.name.takeIf { it.isNotBlank() } ?: fileDoc.uri.lastPathSegment.orEmpty()

    /** 已定性为 JSON 但读不到内容（流打不开 / 0 字节）：给出可操作提示，绝不降级为书籍导入。 */
    private fun failUnreadable(fileDoc: FileDoc) {
        val msg = context.getString(R.string.association_file_unreadable, displayName(fileDoc))
        AppLog.put(msg)
        errorLive.postValue(msg)
    }

    private fun isThemeZip(fileDoc: FileDoc): Boolean {
        return kotlin.runCatching {
            fileDoc.openInputStream().getOrThrow().use { input ->
                ZipUtils.getFilesName(input) { true }.any { name ->
                    val normalized = name.replace('\\', '/').trim('/')
                    normalized.endsWith("/theme.json", ignoreCase = true) ||
                        normalized.equals("theme.json", ignoreCase = true) ||
                        normalized.endsWith("/appearance_kit.json", ignoreCase = true) ||
                        normalized.equals("appearance_kit.json", ignoreCase = true)
                }
            }
        }.getOrDefault(false)
    }

    private fun isBubbleZip(fileDoc: FileDoc): Boolean {
        return kotlin.runCatching {
            fileDoc.openInputStream().getOrThrow().use { input ->
                ZipUtils.getFilesName(input) { true }.any { name ->
                    val normalized = name.replace('\\', '/').trim('/')
                    normalized.endsWith("/bubble.json", ignoreCase = true) ||
                        normalized.equals("bubble.json", ignoreCase = true)
                }
            }
        }.getOrDefault(false)
    }

    fun importBook(uri: Uri) {
        val book = LocalBook.importFile(uri)
        openBookLiveData.postValue(book)
    }

    companion object {
        /** JSON 物化缓存目录（应用专属外部目录，无需存储权限）。 */
        private const val JSON_CACHE_DIR = "associationImportCache"
    }
}