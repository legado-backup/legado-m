package io.legado.app.ui.book.source.edit

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.activity.result.ActivityResult
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.withStateAtLeast
import androidx.viewbinding.ViewBinding
import io.legado.app.R
import io.legado.app.base.BaseActivity
import io.legado.app.base.attachComposeContent
import io.legado.app.base.composeShell
import io.legado.app.constant.AppLog
import io.legado.app.data.appDb
import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.JsSourceUpsert
import io.legado.app.ui.book.source.debug.BookSourceDebugActivity
import io.legado.app.ui.code.CodeEditActivity
import io.legado.app.ui.code.CodeEditSessionStore
import io.legado.app.ui.login.SourceLoginActivity
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.utils.StartActivityContract
import io.legado.app.utils.startActivity
import io.legado.app.utils.toastOnUi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * JS 单文件书源的**编排页**（2026-10-23 对齐 NG `JsSourceEditActivity`）。
 *
 * ### 为什么需要
 * 一期把 JS 源编辑做成「管理页直接拉起统一编辑器 + Intent 直传正文」：
 * ① 没有「保存 → 调试 → 登录 → 回编辑器」的编排（能力半残）；
 * ② 正文经 `Intent` 走 Binder，作者级大脚本（真机实测 162908 字符起步，NG 作者源更大）
 * 有 `TransactionTooLargeException` 风险，叠加 256MB 小堆 ⇒ 编辑页卡死/闪退。
 *
 * ### 形态
 * 本页**只承载编排与状态机**，真正的界面是统一编辑器 [CodeEditActivity]；
 * 正文出入一律走 [CodeEditSessionStore] 会话通道（零 Binder），本页自身只显示一个进度指示器。
 * 编排语义与 NG 一一对应（见 [JsSourceEditFlow]）。
 */
class JsSourceEditActivity : BaseActivity<ViewBinding>(imageBg = false) {

    private companion object {
        const val STATE_OPENED_SOURCE_URL = "openedSourceUrl"
        const val STATE_EDIT_SESSION_ID = "editSessionId"
        const val STATE_STAGE = "stage"

        /** 新建 JS 源时载入的内置模板资产。 */
        const val TEMPLATE_ASSET = "js_source_template.js"
    }

    override val binding: ViewBinding by lazy { composeShell(this) }

    private var openedSourceUrl: String? = null
    private var pendingText: String? = null
    private var editSessionId: String? = null
    private var stage = JsSourceEditStage.READY
    private var editorOpening = false

    private val debugResult = registerForActivityResult(
        StartActivityContract(BookSourceDebugActivity::class.java)
    ) {
        stage = stage.afterDebugResult()
        pendingText?.let(::openEditor) ?: finish()
    }

    private val editorResult = registerForActivityResult(
        StartActivityContract(CodeEditActivity::class.java)
    ) { result -> onEditorResult(result) }

    private val loginResult = registerForActivityResult(
        StartActivityContract(SourceLoginActivity::class.java)
    ) {
        stage = stage.afterLoginResult()
        pendingText?.let(::openEditor) ?: finish()
    }

    override fun onActivityCreated(savedInstanceState: Bundle?) {
        binding.root.attachComposeContent {
            LegadoTheme {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            }
        }
        openedSourceUrl = savedInstanceState?.getString(STATE_OPENED_SOURCE_URL)
            ?: intent.getStringExtra("sourceUrl")
        editSessionId = savedInstanceState?.getString(STATE_EDIT_SESSION_ID)
        stage = savedInstanceState?.getString(STATE_STAGE)
            ?.let { runCatching { JsSourceEditStage.valueOf(it) }.getOrNull() }
            ?: JsSourceEditStage.READY
        lifecycleScope.launch {
            // 进程被杀留下的陈旧会话兜底清理（当次会话文件都是新的，不受影响）
            withContext(Dispatchers.IO) { CodeEditSessionStore.app.cleanupStale() }
            val text = withContext(Dispatchers.IO) {
                editSessionId?.let(CodeEditSessionStore.app::read)
                    ?: openedSourceUrl?.let { appDb.bookSourceDao.getBookSource(it)?.mainJs }
                    ?: assets.open(TEMPLATE_ASSET).bufferedReader().use { it.readText() }
            }
            pendingText = text
            when (stage.restoreAction()) {
                JsSourceEditRestoreAction.OPEN_EDITOR -> openEditor(text)
                JsSourceEditRestoreAction.SAVE_AND_FINISH -> saveSource(text)
                JsSourceEditRestoreAction.SAVE_FOR_DEBUG -> saveForDebug(text)
                JsSourceEditRestoreAction.SAVE_FOR_LOGIN -> saveForLogin(text)
                JsSourceEditRestoreAction.LAUNCH_DEBUG -> launchDebugWhenResumed()
                JsSourceEditRestoreAction.LAUNCH_LOGIN -> launchLoginWhenResumed()
                JsSourceEditRestoreAction.AWAIT_RESULT -> Unit
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString(STATE_OPENED_SOURCE_URL, openedSourceUrl)
        outState.putString(STATE_EDIT_SESSION_ID, editSessionId)
        outState.putString(STATE_STAGE, stage.name)
    }

    override fun onDestroy() {
        // 流程结束才清理会话（进程重建时 editSessionId 仍需可用 ⇒ 只在真正 finish 时删）
        if (isFinishing) {
            editSessionId?.let(CodeEditSessionStore.app::delete)
        }
        super.onDestroy()
    }

    /** 编辑器返回：解析动作 + 会话正文，再决定保存/调试/登录。 */
    private fun onEditorResult(result: ActivityResult) {
        val data = result.data
        val returnedSessionId = data?.getStringExtra(CodeEditSessionStore.ExtraSessionId)
        val legacyText = data?.getStringExtra("text")
        if (result.resultCode != Activity.RESULT_OK ||
            returnedSessionId == null && legacyText == null
        ) {
            // 用户放弃编辑（无改动或明确不保存）⇒ 直接结束，不落库
            stage = JsSourceEditStage.READY
            finish()
            return
        }
        returnedSessionId?.let { editSessionId = it }
        val action = data?.getStringExtra(CodeEditActivity.EXTRA_RESULT_ACTION)
        val textChanged = data?.getBooleanExtra(CodeEditActivity.EXTRA_RESULT_TEXT_CHANGED, true) ?: true
        val debugRequested = action == CodeEditActivity.RESULT_ACTION_DEBUG_SOURCE
        val loginRequested = action == CodeEditActivity.RESULT_ACTION_LOGIN_SOURCE
        stage = stageForEditorResult(debugRequested, loginRequested)
        lifecycleScope.launch {
            val text = try {
                legacyText ?: withContext(Dispatchers.IO) {
                    returnedSessionId?.let(CodeEditSessionStore.app::read)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("JS 书源会话读取失败", e)
                toastOnUi(e.localizedMessage)
                null
            }
            if (text == null) {
                stage = JsSourceEditStage.READY
                finish()
                return@launch
            }
            pendingText = text
            when {
                debugRequested -> saveForDebug(text)
                loginRequested -> saveForLogin(text)
                else -> saveSource(text, showSuccessToast = textChanged)
            }
        }
    }

    /** 打开统一编辑器（会话通道 + 编排页专属开关）。 */
    private fun openEditor(text: String) {
        if (stage == JsSourceEditStage.EDITOR_OPEN || editorOpening || isFinishing) return
        editorOpening = true
        lifecycleScope.launch {
            try {
                val sessionId = withContext(Dispatchers.IO) {
                    editSessionId?.also { CodeEditSessionStore.app.write(it, text) }
                        ?: CodeEditSessionStore.app.create(text)
                }
                editSessionId = sessionId
                if (isFinishing) return@launch
                stage = JsSourceEditStage.EDITOR_OPEN
                editorResult.launch {
                    putExtra(CodeEditSessionStore.ExtraSessionId, sessionId)
                    putExtra(
                        "title",
                        getString(
                            if (openedSourceUrl == null) R.string.js_source_new
                            else R.string.js_source_edit
                        )
                    )
                    putExtra("languageName", "source.js")
                    putExtra(CodeEditActivity.EXTRA_RETURN_UNCHANGED_TEXT, true)
                    putExtra(CodeEditActivity.EXTRA_SHOW_DEBUG_SOURCE, true)
                    putExtra(CodeEditActivity.EXTRA_SHOW_LOGIN_SOURCE, true)
                    // 新建源退出时先确认再走保存（避免误触退出丢掉刚写的脚本）
                    putExtra(CodeEditActivity.EXTRA_CONFIRM_SAVE_ON_EXIT, openedSourceUrl == null)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("JS 书源编辑器打开失败", e)
                stage = JsSourceEditStage.READY
                toastOnUi(e.localizedMessage)
                finish()
            } finally {
                editorOpening = false
            }
        }
    }

    private fun saveForDebug(text: String) {
        saveSource(text, showSuccessToast = false, finishAfterSave = false) {
            launchDebugWhenResumed()
        }
    }

    private fun launchDebugWhenResumed() {
        val sourceUrl = openedSourceUrl ?: run {
            val text = pendingText ?: return finish()
            stage = JsSourceEditStage.SAVING_FOR_DEBUG
            saveForDebug(text)
            return
        }
        lifecycleScope.launch {
            lifecycle.withStateAtLeast(Lifecycle.State.RESUMED) {
                if (stage != JsSourceEditStage.DEBUG_READY) return@withStateAtLeast
                stage = JsSourceEditStage.DEBUG_OPEN
                debugResult.launch { putExtra("key", sourceUrl) }
            }
        }
    }

    private fun saveForLogin(text: String) {
        saveSource(text, showSuccessToast = false, finishAfterSave = false) { source ->
            if (!source.loginUrl.isNullOrBlank() || !source.loginUi.isNullOrBlank()) {
                launchLoginWhenResumed()
            } else {
                stage = JsSourceEditStage.READY
                toastOnUi(R.string.source_no_login)
                pendingText?.let(::openEditor) ?: finish()
            }
        }
    }

    private fun launchLoginWhenResumed() {
        val sourceUrl = openedSourceUrl ?: run {
            val text = pendingText ?: return finish()
            stage = JsSourceEditStage.SAVING_FOR_LOGIN
            saveForLogin(text)
            return
        }
        lifecycleScope.launch {
            lifecycle.withStateAtLeast(Lifecycle.State.RESUMED) {
                if (stage != JsSourceEditStage.LOGIN_READY) return@withStateAtLeast
                stage = JsSourceEditStage.LOGIN_OPEN
                loginResult.launch {
                    putExtra("type", "bookSource")
                    putExtra("key", sourceUrl)
                }
            }
        }
    }

    private fun saveSource(
        text: String,
        showSuccessToast: Boolean = true,
        finishAfterSave: Boolean = true,
        onSuccess: ((BookSource) -> Unit)? = null,
    ) {
        lifecycleScope.launch {
            try {
                val source = JsSourceUpsert.save(text, openedSourceUrl)
                openedSourceUrl = source.bookSourceUrl
                stage = stage.afterSuccessfulSave()
                pendingText = source.mainJs ?: text
                editSessionId?.let { sessionId ->
                    withContext(Dispatchers.IO) {
                        CodeEditSessionStore.app.write(sessionId, pendingText.orEmpty())
                    }
                }
                if (showSuccessToast) toastOnUi(R.string.success)
                setResult(Activity.RESULT_OK, Intent().putExtra("origin", source.bookSourceUrl))
                onSuccess?.invoke(source)
                if (finishAfterSave) finish()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("JS 书源保存失败", e)
                stage = JsSourceEditStage.READY
                toastOnUi(e.localizedMessage ?: getString(R.string.js_source_save_error))
                // 保存失败不丢编辑现场：回到编辑器让用户改（与 NG 同口径）
                openEditor(text)
            }
        }
    }
}
