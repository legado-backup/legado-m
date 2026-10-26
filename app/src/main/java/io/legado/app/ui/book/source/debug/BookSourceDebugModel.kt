package io.legado.app.ui.book.source.debug

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import io.legado.app.base.BaseViewModel
import io.legado.app.data.appDb
import io.legado.app.data.entities.BookSource
import io.legado.app.help.source.exploreKinds
import io.legado.app.model.Debug
import io.legado.app.model.jsSource.isJsSource

/**
 * debug-page-redesign：书源调试 VM（不再实现 Debug.Callback——UI 改为 collectAsState 订阅
 * Debug.events 结构化事件流；响应源码即事件卡片点击全文，无需 printLog 分流缓存）。
 */
class BookSourceDebugModel(application: Application) : BaseViewModel(application) {

    var bookSource: BookSource? = null
        private set

    var sourceName: String by mutableStateOf("")
        private set

    /** 示例快捷项：checkKeyWord（缺省"我的"）+ "系统" + 发现分类（AD-04/MD3 对标） */
    var examples: List<DebugExample> by mutableStateOf(emptyList())
        private set

    fun init(sourceUrl: String?, finally: () -> Unit) {
        // 切换源（onNewIntent）时必须先清掉旧绑定，避免读库失败后仍调试上一个源
        bookSource = null
        sourceName = ""
        examples = emptyList()
        sourceUrl?.let {
            execute {
                bookSource = appDb.bookSourceDao.getBookSource(sourceUrl)
                sourceName = bookSource?.bookSourceName.orEmpty()
                buildExamples()
            }.onFinally {
                finally.invoke()
            }
        }
    }

    private suspend fun buildExamples() {
        val source = bookSource ?: return
        val kinds = runCatching { source.exploreKinds() }.getOrDefault(emptyList())
        examples = buildDebugExamples(source, kinds.map { it.title to it.url.orEmpty() })
    }

    /** 新会话开始：清事件流后启动调试链路（事件经 Debug.events 下发给 Screen） */
    fun startDebug(key: String, onError: () -> Unit) {
        val source = bookSource ?: run {
            onError.invoke()
            return
        }
        Debug.clearEvents()
        execute {
            Debug.startDebug(this, source, key)
        }.onError {
            onError.invoke()
        }
    }

    /** FAB 停止：cancelDebug → tasks.clear() 逐个 cancel（CompositeCoroutine 语义已核实） */
    fun stopDebug() {
        Debug.cancelDebug()
    }

    /** 顶栏「清空」：事件流 + 会话文本缓冲一并清空 */
    fun clearLogs() {
        Debug.clearEvents()
        Debug.clearSessionLogs()
    }

    override fun onCleared() {
        super.onCleared()
        Debug.cancelDebug(true)
    }
}

/**
 * 生成调试示例（A-1 / AD-02）—— 抽成**纯函数**以便 JVM 单测直接断言（无需 Android/Room）。
 *
 * 规则：
 * 1. 声明优先：`checkKeyWord`（缺省「我的」）+ 固定「系统」→ 两条搜索示例；声明式发现分类 → 发现示例；
 * 2. **JS 单文件源补齐占位**：其声明式规则字段可能全空 ⇒ 用源地址为 发现/详情/目录/正文 四档各补一条，
 *    保证五档都有可运行入口（值只存原始 URL，魔法前缀由 `buildKey` 在该边界拼装，AD-04）；
 * 3. 去重按 `target + value`，且**已存在的档位不覆盖**（声明优先不被占位挤掉）。
 */
internal fun buildDebugExamples(
    source: BookSource,
    kinds: List<Pair<String, String>>,
): List<DebugExample> {
    val list = mutableListOf<DebugExample>()
    val keyword = source.ruleSearch?.checkKeyWord?.takeIf { it.isNotBlank() } ?: "我的"
    list.add(DebugExample(keyword, BookDebugTarget.SEARCH, keyword))
    list.add(DebugExample("系统", BookDebugTarget.SEARCH, "系统"))
    kinds.filter { it.second.isNotBlank() }.forEach { (title, url) ->
        list.add(DebugExample(title.ifBlank { "分类" }, BookDebugTarget.EXPLORE, url))
    }
    if (source.isJsSource()) {
        val base = source.bookSourceUrl
        listOf(
            "发现（占位）" to BookDebugTarget.EXPLORE,
            "详情（占位）" to BookDebugTarget.INFO,
            "目录（占位）" to BookDebugTarget.TOC,
            "正文（占位）" to BookDebugTarget.CONTENT,
        ).forEach { (label, target) ->
            if (list.none { it.target == target }) {
                list.add(DebugExample(label, target, base))
            }
        }
    }
    return list.distinctBy { it.target to it.value }
}
