package io.legado.app.ui.main.explore

import android.app.Application
import io.legado.app.base.BaseViewModel
import io.legado.app.data.appDb
import io.legado.app.data.entities.BookSourcePart
import io.legado.app.help.config.SourceConfig
import io.legado.app.help.source.SourceHelp

class ExploreViewModel(application: Application) : BaseViewModel(application) {

    fun topSource(bookSource: BookSourcePart) {
        execute {
            val minXh = appDb.bookSourceDao.minOrder
            bookSource.customOrder = minXh - 1
            appDb.bookSourceDao.upOrder(bookSource)
        }
    }

    fun deleteSource(source: BookSourcePart) {
        execute {
            SourceHelp.deleteBookSource(source.bookSourceUrl)
        }
    }

    // P1-3b 问题4：批量移入/移出分组（对齐管理页 BookSourceViewModel 模式）
    fun selectionAddToGroups(sources: List<BookSourcePart>, groups: String) {
        execute {
            val array = sources.map {
                it.copy().apply {
                    addGroup(groups)
                }
            }
            appDb.bookSourceDao.upGroup(array)
        }
    }

    fun selectionRemoveFromGroups(sources: List<BookSourcePart>, groups: String) {
        execute {
            val array = sources.map {
                it.copy().apply {
                    removeGroup(groups)
                }
            }
            appDb.bookSourceDao.upGroup(array)
        }
    }

}