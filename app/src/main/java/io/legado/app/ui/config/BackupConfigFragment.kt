package io.legado.app.ui.config

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.view.ViewGroup
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.ComposeView
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.fragment.app.Fragment
import io.legado.app.R
import io.legado.app.constant.AppLog
import io.legado.app.constant.PreferKey
import io.legado.app.databinding.DialogEditTextBinding
import io.legado.app.exception.NoStackTraceException
import io.legado.app.help.AppWebDav
import io.legado.app.help.config.AppConfig
import io.legado.app.help.config.LocalConfig
import io.legado.app.help.coroutine.Coroutine
import io.legado.app.help.storage.Backup
import io.legado.app.help.storage.BackupConfig
import io.legado.app.help.storage.ImportOldData
import io.legado.app.help.storage.Restore
import io.legado.app.lib.dialogs.alert
import io.legado.app.lib.dialogs.selector
import io.legado.app.lib.permission.Permissions
import io.legado.app.lib.permission.PermissionsCompat
import io.legado.app.lib.webdav.WebDavException
import io.legado.app.ui.about.AppLogDialog
import io.legado.app.ui.file.HandleFileContract
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.ui.widget.components.MenuAction
import io.legado.app.ui.widget.dialog.WaitDialog
import io.legado.app.utils.FileDoc
import io.legado.app.utils.checkWrite
import io.legado.app.utils.defaultSharedPreferences
import io.legado.app.utils.getPrefBoolean
import io.legado.app.utils.getPrefString
import io.legado.app.utils.isContentScheme
import io.legado.app.utils.launch
import io.legado.app.utils.putPrefBoolean
import io.legado.app.utils.putPrefString
import io.legado.app.utils.requestInputMethod
import io.legado.app.utils.showDialogFragment
import io.legado.app.utils.showHelp
import io.legado.app.utils.toastOnUi
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.Dispatchers.Main
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import splitties.init.appCtx

/**
 * 备份与恢复（P3-2b 配置子页 Compose 化，对齐 OtherConfigFragment 双轨范式）。
 *
 * 内容区全 Compose（[BackupConfigScreen]），设置项零裁剪迁移：
 * 编辑框（WebDAV 地址/账户/密码/子目录/设备名）、文件选择（备份路径/备份目录/恢复文档/导入旧数据）、
 * WebDAV 备份/恢复/重命名/删除、忽略设置等副作用保留本 Fragment；
 * 「恢复」行长按 → 本地恢复（[onRestoreLongClick]，原版 onLongClick 隐藏功能）。
 */
class BackupConfigFragment : Fragment(),
    SharedPreferences.OnSharedPreferenceChangeListener {

    private val viewModel by activityViewModels<ConfigViewModel>()
    private val waitDialog by lazy { WaitDialog(requireContext()) }
    private var backupJob: Job? = null
    private var restoreJob: Job? = null

    // Compose 桥接状态（延迟初始化：构造期 requireContext 未 attach 会崩，真实值在 onCreateView 赋值）
    private var webDavUrl by mutableStateOf("")
    private var webDavAccount by mutableStateOf("")
    private var webDavPassword by mutableStateOf("")
    private var webDavDir by mutableStateOf("legado")
    private var webDavDeviceName by mutableStateOf("")
    private var syncBookProgress by mutableStateOf(true)
    private var syncBookProgressPlus by mutableStateOf(false)
    private var backupPath by mutableStateOf("")
    private var onlyLatestBackup by mutableStateOf(true)
    private var autoCheckNewBackup by mutableStateOf(true)

    private val selectBackupPath = registerForActivityResult(HandleFileContract()) {
        it.uri?.let { uri ->
            if (uri.isContentScheme()) {
                AppConfig.backupPath = uri.toString()
            } else {
                AppConfig.backupPath = uri.path
            }
        }
    }
    private val backupDir = registerForActivityResult(HandleFileContract()) { result ->
        result.uri?.let { uri ->
            if (uri.isContentScheme()) {
                AppConfig.backupPath = uri.toString()
                backup(uri.toString())
            } else {
                uri.path?.let { path ->
                    AppConfig.backupPath = path
                    backup(path)
                }
            }
        }
    }
    private val restoreDoc = registerForActivityResult(HandleFileContract()) {
        it.uri?.let { uri ->
            waitDialog.setText("恢复中…")
            waitDialog.show()
            val task = Coroutine.async {
                Restore.restore(appCtx, uri)
            }.onFinally {
                waitDialog.dismiss()
            }
            waitDialog.setOnCancelListener {
                task.cancel()
            }
        }
    }
    private val restoreOld = registerForActivityResult(HandleFileContract()) {
        it.uri?.let { uri ->
            ImportOldData.importUri(appCtx, uri)
        }
    }

    override fun onCreateView(
        inflater: android.view.LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        // 延迟初始化：真实值（构造期 requireContext 未 attach）
        webDavUrl = getPrefString(PreferKey.webDavUrl) ?: ""
        webDavAccount = getPrefString(PreferKey.webDavAccount) ?: ""
        webDavPassword = getPrefString(PreferKey.webDavPassword) ?: ""
        webDavDir = getPrefString(PreferKey.webDavDir, "legado") ?: "legado"
        webDavDeviceName = getPrefString(PreferKey.webDavDeviceName, Build.MODEL) ?: Build.MODEL
        syncBookProgress = getPrefBoolean(PreferKey.syncBookProgress, true)
        syncBookProgressPlus = getPrefBoolean(PreferKey.syncBookProgressPlus, false)
        backupPath = AppConfig.backupPath ?: ""
        onlyLatestBackup = getPrefBoolean(PreferKey.onlyLatestBackup, true)
        autoCheckNewBackup = getPrefBoolean(PreferKey.autoCheckNewBackup, true)
        return ComposeView(requireContext()).apply {
            setContent {
                LegadoTheme {
                    BackupConfigScreen(
                        state = BackupConfigState(
                            webDavUrl = webDavUrl,
                            webDavAccount = webDavAccount,
                            webDavPassword = webDavPassword,
                            webDavDir = webDavDir,
                            webDavDeviceName = webDavDeviceName,
                            syncBookProgress = syncBookProgress,
                            syncBookProgressPlus = syncBookProgressPlus,
                            backupPath = backupPath,
                            onlyLatestBackup = onlyLatestBackup,
                            autoCheckNewBackup = autoCheckNewBackup
                        ),
                        onToggleChange = { key, value -> onToggleChange(key, value) },
                        onItemClick = { key -> onItemClick(key) },
                        onRestoreLongClick = { restoreFromLocal() }
                    )
                }
            }
        }
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        activity?.setTitle(R.string.backup_restore)
        requireContext().defaultSharedPreferences.registerOnSharedPreferenceChangeListener(this)
        // L-E1 S2 改造：菜单迁移至 ConfigActivity Compose 顶栏（原 MenuProvider menu_backup_restore）
        (activity as? ConfigActivity)?.setTopBarMenu(
            listOf(
                MenuAction(
                    icon = Icons.Filled.HelpOutline,
                    title = getString(R.string.help),
                    onClick = { showHelp("webDavHelp") }
                ),
                MenuAction(
                    icon = Icons.Filled.Info,
                    title = getString(R.string.log),
                    onClick = { showDialogFragment<AppLogDialog>() }
                )
            )
        )
        if (!LocalConfig.backupHelpVersionIsLast) {
            showHelp("webDavHelp")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        context?.defaultSharedPreferences?.unregisterOnSharedPreferenceChangeListener(this)
    }

    /**
     * 开关项：写偏好 + 更新 Compose 状态（副作用经 onSharedPreferenceChanged 统一处理，避免双重执行）。
     */
    private fun onToggleChange(key: String, value: Boolean) {
        when (key) {
            PreferKey.syncBookProgress -> {
                syncBookProgress = value
                putPrefBoolean(PreferKey.syncBookProgress, value)
            }

            PreferKey.syncBookProgressPlus -> {
                syncBookProgressPlus = value
                putPrefBoolean(PreferKey.syncBookProgressPlus, value)
            }

            PreferKey.onlyLatestBackup -> {
                onlyLatestBackup = value
                putPrefBoolean(PreferKey.onlyLatestBackup, value)
            }

            PreferKey.autoCheckNewBackup -> {
                autoCheckNewBackup = value
                putPrefBoolean(PreferKey.autoCheckNewBackup, value)
            }
        }
    }

    /**
     * 点击项：保留原 PreferenceFragment.onPreferenceTreeClick 全部副作用。
     */
    private fun onItemClick(key: String) {
        when (key) {
            PreferKey.webDavUrl -> showEditTextDialog(
                PreferKey.webDavUrl, getString(R.string.web_dav_url), getPrefString(PreferKey.webDavUrl) ?: ""
            )

            PreferKey.webDavAccount -> showEditTextDialog(
                PreferKey.webDavAccount, getString(R.string.web_dav_account), getPrefString(PreferKey.webDavAccount) ?: ""
            )

            PreferKey.webDavPassword -> showEditTextDialog(
                PreferKey.webDavPassword, getString(R.string.web_dav_pw),
                getPrefString(PreferKey.webDavPassword) ?: "", isPassword = true
            )

            PreferKey.webDavDir -> showEditTextDialog(
                PreferKey.webDavDir, getString(R.string.sub_dir), webDavDir
            )

            PreferKey.webDavDeviceName -> showEditTextDialog(
                PreferKey.webDavDeviceName, getString(R.string.webdav_device_name), webDavDeviceName
            )

            PreferKey.backupPath -> selectBackupPath.launch()
            PreferKey.restoreIgnore -> backupIgnore()
            "web_dav_backup" -> backup()
            "web_dav_restore" -> restore()
            "import_old" -> restoreOld.launch()
        }
    }

    /**
     * WebDAV 编辑项（地址/账户/密码/子目录/设备名）对话框，保留原 EditTextPreference 编辑语义。
     */
    private fun showEditTextDialog(key: String, title: String, value: String, isPassword: Boolean = false) {
        alert(title) {
            val alertBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.hint = title
                editView.setText(value)
                if (isPassword) {
                    editView.inputType =
                        InputType.TYPE_TEXT_VARIATION_PASSWORD or InputType.TYPE_CLASS_TEXT
                }
                editView.setSelection(value.length)
            }
            customView { alertBinding.root }
            okButton {
                putPrefString(key, alertBinding.editView.text?.toString().orEmpty())
            }
            cancelButton()
        }
    }

    override fun onSharedPreferenceChanged(sharedPreferences: SharedPreferences?, key: String?) {
        when (key) {
            PreferKey.backupPath -> backupPath = AppConfig.backupPath ?: ""

            PreferKey.webDavUrl,
            PreferKey.webDavAccount,
            PreferKey.webDavPassword,
            PreferKey.webDavDir -> {
                webDavUrl = getPrefString(PreferKey.webDavUrl) ?: ""
                webDavAccount = getPrefString(PreferKey.webDavAccount) ?: ""
                webDavPassword = getPrefString(PreferKey.webDavPassword) ?: ""
                webDavDir = getPrefString(PreferKey.webDavDir, "legado") ?: "legado"
                viewModel.upWebDavConfig()
            }

            PreferKey.webDavDeviceName ->
                webDavDeviceName = getPrefString(PreferKey.webDavDeviceName, Build.MODEL) ?: Build.MODEL

            PreferKey.syncBookProgress -> syncBookProgress = getPrefBoolean(PreferKey.syncBookProgress, true)
            PreferKey.syncBookProgressPlus -> syncBookProgressPlus = getPrefBoolean(PreferKey.syncBookProgressPlus, false)
            PreferKey.onlyLatestBackup -> onlyLatestBackup = getPrefBoolean(PreferKey.onlyLatestBackup, true)
            PreferKey.autoCheckNewBackup -> autoCheckNewBackup = getPrefBoolean(PreferKey.autoCheckNewBackup, true)
        }
    }

    /**
     * 备份忽略设置
     */
    private fun backupIgnore() {
        val checkedItems = BooleanArray(BackupConfig.ignoreKeys.size) {
            BackupConfig.ignoreConfig[BackupConfig.ignoreKeys[it]] ?: false
        }
        alert(R.string.restore_ignore) {
            multiChoiceItems(BackupConfig.ignoreTitle, checkedItems) { _, which, isChecked ->
                BackupConfig.ignoreConfig[BackupConfig.ignoreKeys[which]] = isChecked
            }
            onDismiss {
                BackupConfig.saveIgnoreConfig()
            }
        }
    }


    fun backup() {
        val backupPath = AppConfig.backupPath
        if (backupPath.isNullOrEmpty()) {
            backupDir.launch()
        } else {
            if (backupPath.isContentScheme()) {
                lifecycleScope.launch {
                    val canWrite = withContext(IO) {
                        FileDoc.fromDir(backupPath).checkWrite()
                    }
                    if (canWrite) {
                        backup(backupPath)
                    } else {
                        backupDir.launch()
                    }
                }
            } else {
                backupUsePermission(backupPath)
            }
        }
    }

    private fun backup(backupPath: String) {
        waitDialog.setText("备份中…")
        waitDialog.setOnCancelListener {
            backupJob?.cancel()
        }
        waitDialog.show()
        backupJob?.cancel()
        backupJob = lifecycleScope.launch {
            try {
                Backup.backupLocked(requireContext(), backupPath)
                appCtx.toastOnUi(R.string.backup_success)
            } catch (e: Throwable) {
                ensureActive()
                AppLog.put("备份出错\n${e.localizedMessage}", e)
                appCtx.toastOnUi(
                    appCtx.getString(
                        R.string.backup_fail,
                        e.localizedMessage
                    )
                )
            } finally {
                ensureActive()
                waitDialog.dismiss()
            }
        }
    }

    private fun backupUsePermission(path: String) {
        PermissionsCompat.Builder()
            .addPermissions(*Permissions.Group.STORAGE)
            .rationale(R.string.tip_perm_request_storage)
            .onGranted {
                backup(path)
            }
            .request()
    }

    fun restore() {
        waitDialog.setText(R.string.loading)
        waitDialog.setOnCancelListener {
            restoreJob?.cancel()
        }
        waitDialog.show()
        Coroutine.async {
            restoreJob = coroutineContext[Job]
            showRestoreDialog(requireContext())
        }.onError {
            AppLog.put("恢复备份出错WebDavError\n${it.localizedMessage}", it)
            if (context == null) {
                return@onError
            }
            alert {
                setTitle(R.string.restore)
                setMessage("WebDavError\n${it.localizedMessage}\n将从本地备份恢复。")
                okButton {
                    restoreFromLocal()
                }
                cancelButton()
            }
        }.onFinally {
            waitDialog.dismiss()
        }
    }

    private suspend fun showRestoreDialog(context: Context) {
        val names = withContext(IO) { AppWebDav.getBackupNames() }
        if (AppWebDav.isJianGuoYun && names.size > 700) {
            context.toastOnUi("由于坚果云限制列出文件数量，部分备份可能未显示，请及时清理旧备份")
        }
        if (names.isNotEmpty()) {
            currentCoroutineContext().ensureActive()
            withContext(Main) {
                context.selector(
                    title = context.getString(R.string.select_restore_file),
                    items = names,
                    onClick = { _, index ->
                        if (index in 0 until names.size) {
                            view?.post {
                                restoreWebDav(names[index])
                            }
                        }
                    },
                    onLongClick = { _, index ->
                        if (index in 0 until names.size) {
                            showBackupNameOptions(names[index])
                        }
                    }
                )
            }
        } else {
            throw NoStackTraceException("Web dav no back up file")
        }
    }

    private fun showBackupNameOptions(name: String) {
        context?.selector(
            title = name,
            items = arrayListOf(
                getString(R.string.delete),
                getString(R.string.rename)
            )
        ) { _, index ->
            when (index) {
                0 -> confirmDeleteBackup(name)
                1 -> showRenameDialog(name)
            }
        }
    }

    private fun confirmDeleteBackup(name: String) {
        alert(
            title = getString(R.string.delete_alert),
            message = getString(R.string.sure_del_any, name)
        ) {
            yesButton {
                Coroutine.async {
                    AppWebDav.deleteBackup(name)
                }.onSuccess {
                    appCtx.toastOnUi(getString(R.string.delete_backup_success))
                }.onError {
                    AppLog.put("删除备份失败\n${it.localizedMessage}", it)
                    appCtx.toastOnUi("删除备份失败\n${it.localizedMessage}")
                }
            }
            noButton()
        }
    }

    private fun showRenameDialog(oldName: String) {
        alert(title = getString(R.string.rename_backup)) {
            val alertBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.setHint(R.string.input_new_name)
                editView.setText(oldName)
            }
            customView { alertBinding.root }
            okButton {
                val newName = alertBinding.editView.text?.toString()
                if (!newName.isNullOrBlank() && newName != oldName) {
                    renameBackup(oldName, newName)
                }
            }
            cancelButton()
        }.requestInputMethod()
    }

    private fun renameBackup(oldName: String, newName: String) {
        Coroutine.async {
            AppWebDav.renameBackup(oldName, newName)
        }.onSuccess {
            appCtx.toastOnUi(getString(R.string.rename_backup_success))
        }.onError {
            AppLog.put("重命名备份出错\n${it.localizedMessage}", it)
            if (it is WebDavException) {
                val msg = it.localizedMessage ?: ""
                if (msg.contains("405") || msg.contains("501")
                    || msg.contains("Method Not Allowed")
                    || msg.contains("Not Implemented")
                ) {
                    appCtx.toastOnUi(R.string.webdav_move_not_supported)
                } else {
                    appCtx.toastOnUi(
                        appCtx.getString(R.string.rename_backup_fail, it.localizedMessage)
                    )
                }
            } else {
                appCtx.toastOnUi(
                    appCtx.getString(R.string.rename_backup_fail, it.localizedMessage)
                )
            }
        }
    }

    private fun restoreWebDav(name: String) {
        waitDialog.setText("恢复中…")
        waitDialog.show()
        val task = Coroutine.async {
            AppWebDav.restoreWebDav(name)
        }.onError {
            AppLog.put("WebDav恢复出错\n${it.localizedMessage}", it)
            appCtx.toastOnUi("WebDav恢复出错\n${it.localizedMessage}")
        }.onFinally {
            waitDialog.dismiss()
        }
        waitDialog.setOnCancelListener {
            task.cancel()
        }
    }

    private fun restoreFromLocal() {
        restoreDoc.launch {
            title = getString(R.string.select_restore_file)
            mode = HandleFileContract.FILE
            allowExtensions = arrayOf("zip")
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        waitDialog.dismiss()
    }

}
