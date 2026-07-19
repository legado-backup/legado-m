package io.legado.app.ui.rss.search

import android.content.Context
import android.content.Intent
import android.view.inputmethod.InputMethodManager
import androidx.activity.addCallback
import androidx.activity.viewModels
import androidx.appcompat.widget.SearchView
import androidx.fragment.app.commit
import io.legado.app.R
import io.legado.app.base.VMBaseActivity
import io.legado.app.databinding.ActivityRssSearchBinding
import io.legado.app.lib.theme.primaryTextColor
import io.legado.app.ui.rss.article.RssArticlesFragment
import io.legado.app.ui.rss.article.RssSortViewModel
import io.legado.app.utils.applyTint
import io.legado.app.utils.startActivity
import io.legado.app.utils.toastOnUi
import io.legado.app.utils.viewbindingdelegate.viewBinding

/**
 * RSS 源内容搜索 Activity（借鉴 Archive 项目，改写为本地主题方案）。
 *
 * 与 RSS-B-05（RssFragment openRssSearch 入口）配套使用：
 *  - RssFragment 菜单触发 → 选源 → RssSearchActivity.start(context, sourceUrl, key)
 *  - 本 Activity 复用现有 RssSortViewModel（仅用 initData 加载源 + searchKey 字段）
 *  - 搜索结果通过 RssArticlesFragment 展示
 *
 * 借鉴源依赖的 TopBarSearchStyle / applyUiBodyTypefaceDeep / uiTypeface 本项目缺失，
 * 已改写为本地 applyTint 方案（参考 RssFragment.initSearchView）。
 *
 * 关联任务：RSS-B-01（P0）
 */
class RssSearchActivity : VMBaseActivity<ActivityRssSearchBinding, RssSortViewModel>() {

    override val binding by viewBinding(ActivityRssSearchBinding::inflate)
    override val viewModel by viewModels<RssSortViewModel>()

    override fun onActivityCreated(savedInstanceState: android.os.Bundle?) {
        binding.titleBar.title = getString(R.string.rss_search_hint)
        setupSearchView()
        initData()
        onBackPressedDispatcher.addCallback(this) {
            finish()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        binding.searchView.setQuery("", false)
        initData()
    }

    private fun initData() {
        viewModel.initData(intent) {
            val source = viewModel.rssSource
            if (source == null || source.searchUrl.isNullOrBlank()) {
                toastOnUi(R.string.rss_source_empty)
                finish()
                return@initData
            }
            val key = intent.getStringExtra("key").orEmpty()
            // RSS-E-03: focusSearch 参数控制是否自动聚焦搜索框（默认 true 与原行为一致）
            val focusSearch = intent.getBooleanExtra("focusSearch", true)
            if (key.isBlank()) {
                if (focusSearch) {
                    binding.searchView.post {
                        binding.searchView.requestFocus()
                        (getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager)
                            ?.showSoftInput(binding.searchView.findFocus(), InputMethodManager.SHOW_IMPLICIT)
                    }
                }
            } else {
                binding.searchView.setQuery(key, false)
                submitSearch(key)
            }
        }
    }

    private fun setupSearchView() {
        // 简化说明: 借鉴源使用 TopBarSearchStyle.apply + applyUiBodyTypefaceDeep(uiTypeface())
        // 本项目 lib/theme/ 无此扩展,改用本地 applyTint 方案(参考 RssFragment.initSearchView)
        binding.searchView.applyTint(primaryTextColor)
        binding.searchView.queryHint = getString(R.string.rss_search_hint)
        binding.searchView.isSubmitButtonEnabled = true
        binding.searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                val key = query?.trim().orEmpty()
                if (key.isNotBlank()) {
                    binding.searchView.clearFocus()
                    submitSearch(key)
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean = false
        })
    }

    private fun submitSearch(key: String) {
        val source = viewModel.rssSource ?: return
        val searchUrl = source.searchUrl ?: return
        viewModel.searchKey = key
        binding.titleBar.title = key
        supportFragmentManager.commit {
            replace(
                R.id.fragment_container,
                RssArticlesFragment(getString(R.string.search), searchUrl, key),
                "rss_search_result"
            )
        }
    }

    companion object {
        /**
         * 启动 RSS 搜索 Activity。
         *
         * @param context 上下文
         * @param sourceUrl 订阅源 URL
         * @param key 初始搜索关键词（null 或空表示无初始关键词）
         * @param focusSearch 是否自动聚焦搜索框并弹起键盘（默认 true，RSS-E-03）
         */
        fun start(context: Context, sourceUrl: String, key: String? = null, focusSearch: Boolean = true) {
            context.startActivity<RssSearchActivity> {
                putExtra("sourceUrl", sourceUrl)
                putExtra("key", key)
                putExtra("focusSearch", focusSearch)
            }
        }
    }
}
