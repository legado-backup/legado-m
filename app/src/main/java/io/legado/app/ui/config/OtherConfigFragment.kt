package io.legado.app.ui.config

import android.annotation.SuppressLint
import android.content.ComponentName
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.ComposeView
import androidx.core.view.postDelayed
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.jeremyliao.liveeventbus.LiveEventBus
import io.legado.app.R
import io.legado.app.constant.EventBus
import io.legado.app.constant.PreferKey
import io.legado.app.databinding.DialogEditCodeBinding
import io.legado.app.databinding.DialogEditTextBinding
import io.legado.app.help.AppFreezeMonitor
import io.legado.app.help.DebugFloatBallManager
import io.legado.app.help.DispatchersMonitor
import io.legado.app.help.config.AppConfig
import io.legado.app.help.config.LocalConfig
import io.legado.app.lib.dialogs.alert
import io.legado.app.model.CheckSource
import io.legado.app.model.ImageProvider
import io.legado.app.receiver.SharedReceiverActivity
import io.legado.app.service.WebService
import io.legado.app.ui.debug.DebugToolsActivity
import io.legado.app.ui.file.HandleFileContract
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.ui.video.config.SettingsDialog
import io.legado.app.ui.widget.code.addJsonPattern
import io.legado.app.ui.widget.number.NumberPickerDialog
import io.legado.app.utils.LogUtils
import io.legado.app.utils.defaultSharedPreferences
import io.legado.app.utils.getPrefBoolean
import io.legado.app.utils.getPrefString
import io.legado.app.utils.isJsonObject
import io.legado.app.utils.postEvent
import io.legado.app.utils.putPrefBoolean
import io.legado.app.utils.putPrefString
import io.legado.app.utils.removePref
import io.legado.app.utils.restart
import io.legado.app.utils.showDialogFragment
import io.legado.app.utils.startActivity
import splitties.init.appCtx

/**
 * 其它设置（P3-2 配置子页 Compose 化，对齐 ThemeConfigScreen/CoverConfigScreen 范式）。
 *
 * 内容区全 Compose（[OtherConfigScreen]），设置项零裁剪迁移：
 * 语言/默认首页/更新渠道走 AppSelectDialog 单选；数字选择/编辑框/文件选择/系统弹窗等副作用保留本 Fragment。
 */
class OtherConfigFragment : Fragment(),
    SharedPreferences.OnSharedPreferenceChangeListener {

    private val viewModel by activityViewModels<ConfigViewModel>()
    private val packageManager = appCtx.packageManager
    private val componentName = ComponentName(
        appCtx,
        SharedReceiverActivity::class.java.name
    )
    private val localBookTreeSelect = registerForActivityResult(HandleFileContract()) {
        it.uri?.let { treeUri ->
            AppConfig.defaultBookTreeUri = treeUri.toString()
        }
    }

    // Compose 桥接状态（延迟初始化：构造期 requireContext 未 attach 会崩，真实值在 onCreateView 赋值）
    private var language by mutableStateOf("auto")
    private var languageLabel by mutableStateOf("")
    private var autoRefresh by mutableStateOf(false)
    private var onlyUpdateRead by mutableStateOf(false)
    private var defaultToRead by mutableStateOf(false)
    private var showDiscovery by mutableStateOf(true)
    private var showRss by mutableStateOf(true)
    private var defaultHomePage by mutableStateOf("bookshelf")
    private var defaultHomePageLabel by mutableStateOf("")
    private var webServiceWakeLock by mutableStateOf(false)
    private var defaultBookTreeUri by mutableStateOf("")
    private var sourceEditMaxLine by mutableStateOf(Int.MAX_VALUE)
    private var checkSourceSummary by mutableStateOf("")
    private var cronet by mutableStateOf(false)
    private var antiAlias by mutableStateOf(false)
    private var bitmapCacheSize by mutableStateOf(50)
    private var imageRetainNum by mutableStateOf(0)
    private var preDownloadNum by mutableStateOf(2)
    private var replaceEnableDefault by mutableStateOf(true)
    private var mediaButtonOnExit by mutableStateOf(true)
    private var readAloudByMediaButton by mutableStateOf(false)
    private var ignoreAudioFocus by mutableStateOf(false)
    private var autoClearExpired by mutableStateOf(true)
    private var showAddToShelfAlert by mutableStateOf(true)
    private var updateToVariant by mutableStateOf("default_version")
    private var updateToVariantLabel by mutableStateOf("")
    private var autoUpdateVariant by mutableStateOf(true)
    private var showMangaUi by mutableStateOf(true)
    private var webPort by mutableStateOf(1122)
    private var searchThreadCount by mutableStateOf(32)
    private var updateCacheThreadCount by mutableStateOf(16)
    private var rssParseConcurrency by mutableStateOf(3)
    private var imageLoadConcurrency by mutableStateOf(5)
    private var processText by mutableStateOf(true)
    private var recordLog by mutableStateOf(false)
    private var debugLogFloatingBall by mutableStateOf(false)
    private var sourceRecycleBinEnabled by mutableStateOf(false)
    private var recordHeapDump by mutableStateOf(false)

    override fun onCreateView(
        inflater: android.view.LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        putPrefBoolean(PreferKey.processText, isProcessTextEnabled())
        // 延迟初始化：真实值（构造期 requireContext 未 attach）
        language = getPrefString(PreferKey.language, "auto") ?: "auto"
        languageLabel = labelOf(R.array.language, R.array.language_value, language)
        autoRefresh = getPrefBoolean(PreferKey.autoRefresh, false)
        onlyUpdateRead = getPrefBoolean(PreferKey.onlyUpdateRead, false)
        defaultToRead = getPrefBoolean(PreferKey.defaultToRead, false)
        showDiscovery = getPrefBoolean(PreferKey.showDiscovery, true)
        showRss = getPrefBoolean(PreferKey.showRss, true)
        defaultHomePage = AppConfig.defaultHomePage ?: "bookshelf"
        defaultHomePageLabel = labelOf(R.array.default_home_page, R.array.default_home_page_value, defaultHomePage)
        webServiceWakeLock = getPrefBoolean(PreferKey.webServiceWakeLock, false)
        defaultBookTreeUri = AppConfig.defaultBookTreeUri ?: ""
        sourceEditMaxLine = AppConfig.sourceEditMaxLine
        checkSourceSummary = CheckSource.summary
        cronet = getPrefBoolean(PreferKey.cronet, false)
        antiAlias = getPrefBoolean(PreferKey.antiAlias, false)
        bitmapCacheSize = AppConfig.bitmapCacheSize
        imageRetainNum = AppConfig.imageRetainNum
        preDownloadNum = AppConfig.preDownloadNum
        replaceEnableDefault = getPrefBoolean(PreferKey.replaceEnableDefault, true)
        mediaButtonOnExit = AppConfig.mediaButtonOnExit
        readAloudByMediaButton = getPrefBoolean(PreferKey.readAloudByMediaButton, false)
        ignoreAudioFocus = getPrefBoolean(PreferKey.ignoreAudioFocus, false)
        autoClearExpired = getPrefBoolean(PreferKey.autoClearExpired, true)
        showAddToShelfAlert = getPrefBoolean(PreferKey.showAddToShelfAlert, true)
        updateToVariant = getPrefString(PreferKey.updateToVariant, "default_version") ?: "default_version"
        updateToVariantLabel = labelOf(R.array.default_app_variant, R.array.default_app_variant_value, updateToVariant)
        autoUpdateVariant = AppConfig.autoUpdateVariant
        showMangaUi = getPrefBoolean(PreferKey.showMangaUi, true)
        webPort = AppConfig.webPort
        searchThreadCount = AppConfig.searchThreadCount
        updateCacheThreadCount = AppConfig.updateCacheThreadCount
        rssParseConcurrency = AppConfig.rssParseConcurrency
        imageLoadConcurrency = AppConfig.imageLoadConcurrency
        processText = getPrefBoolean(PreferKey.processText, true)
        recordLog = AppConfig.recordLog
        debugLogFloatingBall = getPrefBoolean(PreferKey.debugLogFloatingBall, false)
        sourceRecycleBinEnabled = getPrefBoolean(PreferKey.sourceRecycleBinEnabled, false)
        recordHeapDump = getPrefBoolean(PreferKey.recordHeapDump, false)
        return ComposeView(requireContext()).apply {
            setContent {
                LegadoTheme {
                    OtherConfigScreen(
                        state = OtherConfigState(
                            language = language,
                            languageLabel = languageLabel,
                            autoRefresh = autoRefresh,
                            onlyUpdateRead = onlyUpdateRead,
                            defaultToRead = defaultToRead,
                            showDiscovery = showDiscovery,
                            showRss = showRss,
                            defaultHomePage = defaultHomePage,
                            defaultHomePageLabel = defaultHomePageLabel,
                            webServiceWakeLock = webServiceWakeLock,
                            defaultBookTreeUri = defaultBookTreeUri,
                            sourceEditMaxLine = sourceEditMaxLine,
                            checkSourceSummary = checkSourceSummary,
                            cronet = cronet,
                            antiAlias = antiAlias,
                            bitmapCacheSize = bitmapCacheSize,
                            imageRetainNum = imageRetainNum,
                            preDownloadNum = preDownloadNum,
                            replaceEnableDefault = replaceEnableDefault,
                            mediaButtonOnExit = mediaButtonOnExit,
                            readAloudByMediaButton = readAloudByMediaButton,
                            ignoreAudioFocus = ignoreAudioFocus,
                            autoClearExpired = autoClearExpired,
                            showAddToShelfAlert = showAddToShelfAlert,
                            updateToVariant = updateToVariant,
                            updateToVariantLabel = updateToVariantLabel,
                            autoUpdateVariant = autoUpdateVariant,
                            showMangaUi = showMangaUi,
                            webPort = webPort,
                            searchThreadCount = searchThreadCount,
                            updateCacheThreadCount = updateCacheThreadCount,
                            rssParseConcurrency = rssParseConcurrency,
                            imageLoadConcurrency = imageLoadConcurrency,
                            processText = processText,
                            recordLog = recordLog,
                            debugLogFloatingBall = debugLogFloatingBall,
                            sourceRecycleBinEnabled = sourceRecycleBinEnabled,
                            recordHeapDump = recordHeapDump
                        ),
                        onToggleChange = { key, value -> onToggleChange(key, value) },
                        onItemClick = { key -> onItemClick(key) },
                        onLanguageSelect = { value ->
                            language = value
                            languageLabel = labelOf(R.array.language, R.array.language_value, value)
                            putPrefString(PreferKey.language, value)
                        },
                        onHomePageSelect = { value ->
                            defaultHomePage = value
                            defaultHomePageLabel = labelOf(
                                R.array.default_home_page, R.array.default_home_page_value, value
                            )
                            putPrefString(PreferKey.defaultHomePage, value)
                        },
                        onVariantSelect = { value ->
                            updateToVariant = value
                            updateToVariantLabel = labelOf(
                                R.array.default_app_variant, R.array.default_app_variant_value, value
                            )
                            putPrefString(PreferKey.updateToVariant, value)
                        }
                    )
                }
            }
        }
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        activity?.setTitle(R.string.other_setting)
        requireContext().defaultSharedPreferences.registerOnSharedPreferenceChangeListener(this)
        // 老用户线程数配置迁移后首次进入提示
        if (AppConfig.migratedThreadCountJustDone) {
            AppConfig.migratedThreadCountJustDone = false
            context?.let { Toast.makeText(it, R.string.migrated_thread_count_toast, Toast.LENGTH_LONG).show() }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        context?.defaultSharedPreferences?.unregisterOnSharedPreferenceChangeListener(this)
    }

    /**
     * 开关项：写偏好 + 更新 Compose 状态。
     * 副作用（recordLog/debugLogFloatingBall/processText/showDiscovery 等）统一收敛到 [onSharedPreferenceChanged]。
     */
    private fun onToggleChange(key: String, value: Boolean) {
        when (key) {
            PreferKey.autoRefresh -> {
                autoRefresh = value
                putPrefBoolean(PreferKey.autoRefresh, value)
            }

            PreferKey.onlyUpdateRead -> {
                onlyUpdateRead = value
                putPrefBoolean(PreferKey.onlyUpdateRead, value)
            }

            PreferKey.defaultToRead -> {
                defaultToRead = value
                putPrefBoolean(PreferKey.defaultToRead, value)
            }

            PreferKey.showDiscovery -> {
                showDiscovery = value
                putPrefBoolean(PreferKey.showDiscovery, value)
            }

            PreferKey.showRss -> {
                showRss = value
                putPrefBoolean(PreferKey.showRss, value)
            }

            PreferKey.webServiceWakeLock -> {
                webServiceWakeLock = value
                putPrefBoolean(PreferKey.webServiceWakeLock, value)
            }

            PreferKey.cronet -> {
                cronet = value
                putPrefBoolean(PreferKey.cronet, value)
            }

            PreferKey.antiAlias -> {
                antiAlias = value
                putPrefBoolean(PreferKey.antiAlias, value)
            }

            PreferKey.replaceEnableDefault -> {
                replaceEnableDefault = value
                putPrefBoolean(PreferKey.replaceEnableDefault, value)
            }

            "mediaButtonOnExit" -> {
                mediaButtonOnExit = value
                putPrefBoolean("mediaButtonOnExit", value)
            }

            PreferKey.readAloudByMediaButton -> {
                readAloudByMediaButton = value
                putPrefBoolean(PreferKey.readAloudByMediaButton, value)
            }

            PreferKey.ignoreAudioFocus -> {
                ignoreAudioFocus = value
                putPrefBoolean(PreferKey.ignoreAudioFocus, value)
            }

            PreferKey.autoClearExpired -> {
                autoClearExpired = value
                putPrefBoolean(PreferKey.autoClearExpired, value)
            }

            PreferKey.showAddToShelfAlert -> {
                showAddToShelfAlert = value
                putPrefBoolean(PreferKey.showAddToShelfAlert, value)
            }

            "autoUpdateVariant" -> {
                autoUpdateVariant = value
                putPrefBoolean("autoUpdateVariant", value)
            }

            PreferKey.showMangaUi -> {
                showMangaUi = value
                putPrefBoolean(PreferKey.showMangaUi, value)
            }

            PreferKey.processText -> {
                processText = value
                putPrefBoolean(PreferKey.processText, value)
            }

            PreferKey.recordLog -> {
                recordLog = value
                putPrefBoolean(PreferKey.recordLog, value)
            }

            PreferKey.debugLogFloatingBall -> {
                debugLogFloatingBall = value
                putPrefBoolean(PreferKey.debugLogFloatingBall, value)
            }

            PreferKey.sourceRecycleBinEnabled -> {
                sourceRecycleBinEnabled = value
                putPrefBoolean(PreferKey.sourceRecycleBinEnabled, value)
            }

            PreferKey.recordHeapDump -> {
                recordHeapDump = value
                putPrefBoolean(PreferKey.recordHeapDump, value)
            }
        }
    }

    /**
     * 点击项：保留原 PreferenceFragment.onPreferenceTreeClick 全部副作用。
     */
    @SuppressLint("InflateParams")
    private fun onItemClick(key: String) {
        when (key) {
            PreferKey.userAgent -> showUserAgentDialog()
            PreferKey.customHosts -> showCustomHostsDialog()
            PreferKey.videoSetting -> showDialogFragment(SettingsDialog(requireActivity()))
            PreferKey.defaultBookTreeUri -> localBookTreeSelect.launch {
                title = getString(R.string.select_book_folder)
                mode = HandleFileContract.DIR_SYS
            }

            PreferKey.preDownloadNum -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.pre_download))
                .setMaxValue(9999)
                .setMinValue(0)
                .setValue(AppConfig.preDownloadNum)
                .show {
                    AppConfig.preDownloadNum = it
                }

            PreferKey.searchThreadCount -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.search_thread_count_title))
                .setMaxValue(128)
                .setMinValue(1)
                .setValue(AppConfig.searchThreadCount)
                .show {
                    AppConfig.searchThreadCount = it
                }

            PreferKey.updateCacheThreadCount -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.update_cache_thread_count_title))
                .setMaxValue(64)
                .setMinValue(1)
                .setValue(AppConfig.updateCacheThreadCount)
                .show {
                    AppConfig.updateCacheThreadCount = it
                }

            PreferKey.rssParseConcurrency -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.rss_parse_concurrency))
                .setMaxValue(20)
                .setMinValue(1)
                .setValue(AppConfig.rssParseConcurrency)
                .show {
                    AppConfig.rssParseConcurrency = it
                }

            PreferKey.imageLoadConcurrency -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.image_load_concurrency))
                .setMaxValue(20)
                .setMinValue(1)
                .setValue(AppConfig.imageLoadConcurrency)
                .show {
                    AppConfig.imageLoadConcurrency = it
                }

            PreferKey.webPort -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.web_port_title))
                .setMaxValue(60000)
                .setMinValue(1024)
                .setValue(AppConfig.webPort)
                .show {
                    AppConfig.webPort = it
                }

            PreferKey.cleanCache -> clearCache()
            PreferKey.uploadRule -> showDialogFragment<DirectLinkUploadConfig>()
            PreferKey.checkSource -> showDialogFragment<CheckSourceConfig>()
            PreferKey.bitmapCacheSize -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.bitmap_cache_size))
                .setMaxValue(1024)
                .setMinValue(1)
                .setValue(AppConfig.bitmapCacheSize)
                .show {
                    AppConfig.bitmapCacheSize = it
                    ImageProvider.bitmapLruCache.resize(ImageProvider.cacheSize)
                }

            PreferKey.imageRetainNum -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.image_retain_number))
                .setMaxValue(999)
                .setMinValue(0)
                .setValue(AppConfig.imageRetainNum)
                .show {
                    AppConfig.imageRetainNum = it
                }

            PreferKey.sourceEditMaxLine -> NumberPickerDialog(requireContext())
                .setTitle(getString(R.string.source_edit_text_max_line))
                .setMaxValue(Int.MAX_VALUE)
                .setMinValue(10)
                .setValue(AppConfig.sourceEditMaxLine)
                .show {
                    AppConfig.sourceEditMaxLine = it
                }

            PreferKey.clearWebViewData -> clearWebViewData()
            "localPassword" -> alertLocalPassword()
            PreferKey.shrinkDatabase -> shrinkDatabase()
            "debug_tools" -> startActivity<DebugToolsActivity>()
        }
    }

    override fun onSharedPreferenceChanged(sharedPreferences: SharedPreferences?, key: String?) {
        when (key) {
            PreferKey.preDownloadNum -> preDownloadNum = AppConfig.preDownloadNum
            PreferKey.searchThreadCount -> {
                searchThreadCount = AppConfig.searchThreadCount
                postEvent(PreferKey.searchThreadCount, "")
                context?.let { Toast.makeText(it, R.string.search_thread_count_toast, Toast.LENGTH_SHORT).show() }
            }

            PreferKey.updateCacheThreadCount -> {
                updateCacheThreadCount = AppConfig.updateCacheThreadCount
                postEvent(PreferKey.updateCacheThreadCount, "")
                context?.let { Toast.makeText(it, R.string.update_cache_thread_count_toast, Toast.LENGTH_SHORT).show() }
            }

            PreferKey.rssParseConcurrency -> rssParseConcurrency = AppConfig.rssParseConcurrency
            PreferKey.imageLoadConcurrency -> imageLoadConcurrency = AppConfig.imageLoadConcurrency

            PreferKey.webPort -> {
                webPort = AppConfig.webPort
                if (WebService.isRun) {
                    WebService.stop(requireContext())
                    WebService.start(requireContext())
                }
            }

            PreferKey.defaultBookTreeUri -> defaultBookTreeUri = AppConfig.defaultBookTreeUri ?: ""
            PreferKey.recordLog -> {
                recordLog = appCtx.getPrefBoolean(PreferKey.recordLog)
                AppConfig.recordLog = appCtx.getPrefBoolean(PreferKey.recordLog)
                LogUtils.upLevel()
                LogUtils.logDeviceInfo()
                LiveEventBus.config().enableLogger(AppConfig.recordLog)
                AppFreezeMonitor.init(appCtx)
                DispatchersMonitor.init()
            }

            PreferKey.debugLogFloatingBall -> {
                debugLogFloatingBall = sharedPreferences?.getBoolean(key, false) ?: false
                if (debugLogFloatingBall) {
                    DebugFloatBallManager.onActivityResumed(requireActivity())
                } else {
                    DebugFloatBallManager.updateState(false)
                }
            }

            PreferKey.processText -> {
                processText = sharedPreferences?.getBoolean(key, true) ?: true
                setProcessTextEnable(processText)
            }

            PreferKey.showDiscovery, PreferKey.showRss -> postEvent(EventBus.NOTIFY_MAIN, true)
            PreferKey.language -> {
                language = getPrefString(PreferKey.language, "auto") ?: "auto"
                languageLabel = labelOf(R.array.language, R.array.language_value, language)
                view?.postDelayed(1000) {
                    appCtx.restart()
                }
            }

            PreferKey.autoRefresh -> autoRefresh = getPrefBoolean(PreferKey.autoRefresh, false)
            PreferKey.checkSource -> checkSourceSummary = CheckSource.summary
            PreferKey.bitmapCacheSize -> bitmapCacheSize = AppConfig.bitmapCacheSize
            PreferKey.imageRetainNum -> imageRetainNum = AppConfig.imageRetainNum
            PreferKey.sourceEditMaxLine -> sourceEditMaxLine = AppConfig.sourceEditMaxLine

            PreferKey.defaultHomePage -> {
                defaultHomePage = AppConfig.defaultHomePage ?: "bookshelf"
                defaultHomePageLabel = labelOf(
                    R.array.default_home_page, R.array.default_home_page_value, defaultHomePage
                )
            }

            PreferKey.updateToVariant -> {
                updateToVariant = getPrefString(PreferKey.updateToVariant, "default_version") ?: "default_version"
                updateToVariantLabel = labelOf(
                    R.array.default_app_variant, R.array.default_app_variant_value, updateToVariant
                )
            }
        }
    }

    /** 在 value 数组中定位当前值，返回对应的 label 展示（供 Screen 的 value 行显示）。 */
    private fun labelOf(arrayRes: Int, valueRes: Int, value: String): String {
        val labels = requireContext().resources.getStringArray(arrayRes)
        val values = requireContext().resources.getStringArray(valueRes)
        val index = values.indexOf(value)
        return if (index >= 0) labels[index] else ""
    }

    @SuppressLint("InflateParams")
    private fun showUserAgentDialog() {
        alert(getString(R.string.user_agent)) {
            val alertBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.hint = getString(R.string.user_agent)
                editView.setText(AppConfig.userAgent)
            }
            customView { alertBinding.root }
            okButton {
                val userAgent = alertBinding.editView.text?.toString()
                if (userAgent.isNullOrBlank()) {
                    removePref(PreferKey.userAgent)
                } else {
                    putPrefString(PreferKey.userAgent, userAgent)
                }
            }
            cancelButton()
        }
    }

    @SuppressLint("InflateParams")
    private fun showCustomHostsDialog() {
        alert(getString(R.string.custom_hosts)) {
            val alertBinding = DialogEditCodeBinding.inflate(layoutInflater).apply {
                editViewC.hint = getString(R.string.json_format)
                editView.addJsonPattern()
                editView.setText(AppConfig.customHosts)
            }
            customView { alertBinding.root }
            okButton {
                val customHosts = alertBinding.editView.text?.toString()
                if (customHosts.isJsonObject()) {
                    putPrefString(PreferKey.customHosts, customHosts!!)
                } else {
                    removePref(PreferKey.customHosts)
                }
            }
            cancelButton()
        }
    }

    private fun clearCache() {
        requireContext().alert(
            titleResource = R.string.clear_cache,
            messageResource = R.string.sure_del
        ) {
            okButton {
                viewModel.clearCache()
            }
            noButton()
        }
    }

    private fun shrinkDatabase() {
        alert(R.string.sure, R.string.shrink_database) {
            okButton {
                viewModel.shrinkDatabase()
            }
            noButton()
        }
    }

    private fun clearWebViewData() {
        alert(R.string.clear_webview_data, R.string.sure_del) {
            okButton {
                viewModel.clearWebViewData()
            }
            noButton()
        }
    }

    private fun isProcessTextEnabled(): Boolean {
        return packageManager.getComponentEnabledSetting(componentName) != PackageManager.COMPONENT_ENABLED_STATE_DISABLED
    }

    private fun setProcessTextEnable(enable: Boolean) {
        if (enable) {
            packageManager.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP
            )
        } else {
            packageManager.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP
            )
        }
    }

    private fun alertLocalPassword() {
        context?.alert(R.string.set_local_password, R.string.set_local_password_summary) {
            val editTextBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.setHint(R.string.password)
            }
            customView {
                editTextBinding.root
            }
            okButton {
                LocalConfig.password = editTextBinding.editView.text.toString()
            }
            cancelButton()
        }
    }

}
