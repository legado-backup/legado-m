package io.legado.app.ui.book.searchContent

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.view.inputmethod.InputMethodManager
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.focus.FocusRequester
import androidx.lifecycle.lifecycleScope
import io.legado.app.R
import io.legado.app.base.VMBaseActivity
import io.legado.app.constant.AppLog
import io.legado.app.constant.EventBus
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.databinding.ActivitySearchContentBinding
import io.legado.app.help.IntentData
import io.legado.app.help.book.BookHelp
import io.legado.app.help.book.isLocal
import io.legado.app.lib.theme.accentColor
import io.legado.app.lib.theme.bottomBackground
import io.legado.app.lib.theme.getPrimaryTextColor
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.ui.widget.components.AppDropdownMenu
import io.legado.app.ui.widget.components.GlassTopAppBar
import io.legado.app.ui.widget.components.MenuAction
import io.legado.app.ui.widget.components.SettingsSearchBar
import io.legado.app.utils.ColorUtils
import io.legado.app.utils.applyNavigationBarMargin
import io.legado.app.utils.getCompatColor
import io.legado.app.utils.hexString
import io.legado.app.utils.invisible
import io.legado.app.utils.observeEvent
import io.legado.app.utils.postEvent
import io.legado.app.utils.viewbindingdelegate.viewBinding
import io.legado.app.utils.visible
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.Job
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import splitties.systemservices.inputMethodManager


class SearchContentActivity :
    VMBaseActivity<ActivitySearchContentBinding, SearchContentViewModel>() {

    override val binding by viewBinding(ActivitySearchContentBinding::inflate)
    override val viewModel by viewModels<SearchContentViewModel>()
    private var durChapterIndex = 0
    private var searchJob: Job? = null
    private var initJob: Job? = null
    // search-content-compose 壳层化：Compose 顶栏状态（搜索词/菜单）
    private var composeSearchQuery by mutableStateOf("")
    private var menuExpanded by mutableStateOf(false)
    private val searchFocusRequester = FocusRequester()
    // search-content-compose 壳层化：结果列表快照（驱动 Compose LazyColumn 重组）+ Compose 列表状态（供底部跳转按钮）
    private var searchResults by mutableStateOf<List<SearchResult>>(emptyList())
    private var searchListState: LazyListState? = null
    private var pendingScrollIndex: Int = 0
    private val searchTextColor: String
        get() = getCompatColor(R.color.primaryText).hexString.substring(2)
    private val searchAccentColor: String
        get() = accentColor.hexString.substring(2)

    // search-content-compose 壳层化：菜单动作 ID（原 R.id.menu_xxx，菜单资源已删除）
    private object MenuId {
        const val ENABLE_REPLACE = 1
        const val ENABLE_REGEX = 2
    }

    override fun onActivityCreated(savedInstanceState: Bundle?) {
        val bbg = bottomBackground
        val btc = getPrimaryTextColor(ColorUtils.isColorLight(bbg))
        binding.llSearchBaseInfo.setBackgroundColor(bbg)
        binding.llSearchBaseInfo.applyNavigationBarMargin()
        binding.tvCurrentSearchInfo.setTextColor(btc)
        binding.ivSearchContentTop.setColorFilter(btc)
        binding.ivSearchContentBottom.setColorFilter(btc)
        val searchResultList = IntentData.get<List<SearchResult>>("searchResultList")
        val position = intent.getIntExtra("searchResultIndex", 0)
        val noSearchResult = searchResultList == null
        initComposeTopBar()
        initComposeList()
        initView()
        val bookUrl = intent.getStringExtra("bookUrl") ?: return
        viewModel.initBook(bookUrl) {
            initSearchResultList(searchResultList, position)
            initBook(noSearchResult)
        }
    }

    // search-content-compose 壳层化：顶栏（GlassTopAppBar 标题 + 搜索 SettingsSearchBar + 更多菜单 AppDropdownMenu）
    private fun initComposeTopBar() {
        binding.composeTopBar.setContent {
            LegadoTheme {
                Column {
                    GlassTopAppBar(
                        title = getString(R.string.search_content),
                        navIcon = Icons.AutoMirrored.Filled.ArrowBack,
                        onNavClick = { finish() },
                        actions = {
                            Box {
                                IconButton(onClick = { menuExpanded = true }) {
                                    Icon(Icons.Default.MoreVert, contentDescription = null)
                                }
                                AppDropdownMenu(
                                    expanded = menuExpanded,
                                    onDismiss = { menuExpanded = false },
                                    actions = buildMenuActions()
                                )
                            }
                        }
                    )
                    SettingsSearchBar(
                        query = composeSearchQuery,
                        onQueryChange = { composeSearchQuery = it },
                        placeholder = getString(R.string.search),
                        onSearch = { startContentSearch(composeSearchQuery.trim()) },
                        focusRequester = searchFocusRequester
                    )
                }
            }
        }
    }

    // search-content-compose 壳层化：更多菜单数据（替换/正则 两个勾选项）
    private fun buildMenuActions(): List<MenuAction> {
        return buildList {
            add(MenuAction(
                Icons.Default.Settings,
                getString(R.string.replace),
                header = true
            ) {})
            add(MenuAction(
                Icons.Default.FindReplace,
                getString(R.string.replace),
                checked = SearchContentViewModel.replaceEnabled,
                onClick = { handleMenuAction(MenuId.ENABLE_REPLACE) }
            ))
            add(MenuAction(
                Icons.Default.Rule,
                getString(R.string.regex),
                checked = SearchContentViewModel.regexReplace,
                onClick = { handleMenuAction(MenuId.ENABLE_REGEX) }
            ))
        }
    }

    // search-content-compose 壳层化：菜单动作统一入口（原 onCompatOptionsItemSelected 逻辑迁移）
    private fun handleMenuAction(actionId: Int) {
        when (actionId) {
            MenuId.ENABLE_REPLACE -> {
                SearchContentViewModel.replaceEnabled = !SearchContentViewModel.replaceEnabled
            }
            MenuId.ENABLE_REGEX -> {
                SearchContentViewModel.regexReplace = !SearchContentViewModel.regexReplace
            }
        }
    }

    private fun initSearchResultList(list: List<SearchResult>?, position: Int) {
        list ?: return
        viewModel.searchResultList.addAll(list)
        viewModel.searchResultCounts = list.size
        searchResults = viewModel.searchResultList.toList()
        // 若 Compose 列表状态已就绪则直接定位，否则挂起等待
        val state = searchListState
        if (state != null) {
            lifecycleScope.launch { state.scrollToItem(position) }
        } else {
            pendingScrollIndex = position
        }
    }

    // search-content-compose 壳层化：主体列表由 RecyclerView 迁移为 Compose LazyColumn
    private fun initComposeList() {
        binding.composeHost.setContent {
            LegadoTheme {
                SearchContentScreen(
                    results = searchResults,
                    durChapterIndex = durChapterIndex,
                    textColor = searchTextColor,
                    accentColor = searchAccentColor,
                    onResultClick = { result, index -> openSearchResult(result, index) },
                    onListStateReady = { state ->
                        searchListState = state
                        if (pendingScrollIndex > 0) {
                            val target = pendingScrollIndex
                            pendingScrollIndex = 0
                            lifecycleScope.launch { state.scrollToItem(target) }
                        }
                    }
                )
            }
        }
    }

    private fun initView() {
        binding.ivSearchContentTop.setOnClickListener {
            searchListState?.let { lifecycleScope.launch { it.scrollToItem(0, 0) } }
        }
        binding.ivSearchContentBottom.setOnClickListener {
            if (searchResults.isNotEmpty()) {
                searchListState?.let {
                    lifecycleScope.launch { it.scrollToItem(searchResults.size - 1, 0) }
                }
            }
        }
        binding.tvCurrentSearchInfo.setOnClickListener {
            searchFocusRequester.requestFocus()
            inputMethodManager.showSoftInput(
                binding.composeTopBar, InputMethodManager.SHOW_IMPLICIT
            )
        }
        binding.fbStop.setOnClickListener {
            searchJob?.cancel()
        }
    }

    @SuppressLint("SetTextI18n")
    private fun initBook(submit: Boolean = true) {
        binding.tvCurrentSearchInfo.text =
            this.getString(R.string.search_content_size) + ": ${viewModel.searchResultCounts}"
        viewModel.book?.let {
            initCacheFileNames(it)
            durChapterIndex = it.durChapterIndex
            intent.getStringExtra("searchWord")?.let { searchWord ->
                composeSearchQuery = searchWord
                if (submit) startContentSearch(searchWord.trim())
            }
        }
    }

    private fun initCacheFileNames(book: Book) {
        initJob = lifecycleScope.launch {
            withContext(IO) {
                viewModel.cacheChapterNames.addAll(BookHelp.getChapterFiles(book))
            }
            // 缓存文件名就绪后强制刷新，使已渲染条目重算命中高亮
            searchResults = viewModel.searchResultList.toList()
        }
    }

    override fun observeLiveBus() {
        observeEvent<Pair<Book, BookChapter>>(EventBus.SAVE_CONTENT) { (book, chapter) ->
            viewModel.book?.bookUrl?.let { bookUrl ->
                if (book.bookUrl == bookUrl) {
                    viewModel.cacheChapterNames.add(chapter.getFileName())
                    searchResults = viewModel.searchResultList.toList()
                }
            }
        }
    }

    @SuppressLint("SetTextI18n")
    fun startContentSearch(query: String) {
        // 按章节搜索内容
        if (query.isBlank()) return
        searchJob?.cancel()
        searchResults = emptyList()
        viewModel.searchResultList.clear()
        viewModel.searchResultCounts = 0
        viewModel.lastQuery = query
        binding.refreshProgressBar.isAutoLoading = true
        binding.fbStop.visible()
        searchJob = lifecycleScope.launch(IO) {
            initJob?.join()
            kotlin.runCatching {
                appDb.bookChapterDao.getChapterList(viewModel.bookUrl).forEach { bookChapter ->
                    ensureActive()
                    val chapterResults = if (isLocalBook
                        || viewModel.cacheChapterNames.contains(bookChapter.getFileName())
                    ) {
                        viewModel.searchChapter(query, bookChapter)
                    } else {
                        return@forEach
                    }
                    ensureActive()
                    if (chapterResults.isNotEmpty()) {
                        viewModel.searchResultList.addAll(chapterResults)
                        binding.tvCurrentSearchInfo.post {
                            binding.tvCurrentSearchInfo.text =
                                this@SearchContentActivity.getString(R.string.search_content_size) + ": ${viewModel.searchResultCounts}"
                            // search-content-compose：由 status 快照驱动 Compose LazyColumn 增量追加
                            searchResults = viewModel.searchResultList.toList()
                        }
                    }
                }
                // 空结果由 SearchContentScreen 空态 EmptyStatePlaceholder 呈现，无需再插入占位条目
            }.onFailure {
                AppLog.put("全文搜索出错\n${it.localizedMessage}", it)
            }
            binding.tvCurrentSearchInfo.post {
                binding.fbStop.invisible()
                binding.refreshProgressBar.isAutoLoading = false
                // 无结果时同步刷新快照触发空态展示
                searchResults = viewModel.searchResultList.toList()
            }
        }
    }

    private val isLocalBook: Boolean
        get() = viewModel.book?.isLocal == true

    fun openSearchResult(searchResult: SearchResult, index: Int) {
        searchJob?.cancel()
        postEvent(EventBus.SEARCH_RESULT, viewModel.searchResultList as List<SearchResult>)
        val searchData = Intent()
        val key = System.currentTimeMillis()
        IntentData.put("searchResult$key", searchResult)
        IntentData.put("searchResultList$key", viewModel.searchResultList)
        searchData.putExtra("key", key)
        searchData.putExtra("index", index)
        setResult(RESULT_OK, searchData)
        finish()
    }

    fun durChapterIndex(): Int {
        return durChapterIndex
    }

}
