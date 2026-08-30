# 数据库主线程查询迁移清单

> 生成时间: 2026-07-05
> 基于 appDb.allowMainThreadQueries() 的全面扫描结果

## 迁移策略

1. **高危 - 写操作** (insert/update/delete) → 必须用 `withContext(IO)` 或 `Coroutine.async`
2. **高危 - 读操作** (get/query) → 必须用 `withContext(IO)` 或 `lifecycleScope.launch(IO)`
3. **中危 - Flow 缺少 flowOn(IO)** → 添加 `.flowOn(IO)`
4. **中危 - 实体方法内 DAO 调用** → 调用方确保在 IO 线程

---

## P0: 高危 - 确认在主线程直接调用 DAO（按影响排序）

### 1. ReadBookActivity（阅读页面 - 高频操作）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 481 | `appDb.bookChapterDao.getChapter(...)` | `lifecycleScope.launch` (默认 Main) | → `lifecycleScope.launch(IO)` |
| 1293 | `appDb.bookChapterDao.getChapter(...)` | `payAction()` 直接主线程 | → `Coroutine.async` + `withContext(IO)` |

### 2. ReadMenu（阅读菜单 - 高频操作）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 449 | `appDb.bookChapterDao.getChapter(...)` | 点击回调 | → `lifecycleScope.launch(IO)` |
| 463 | `appDb.bookChapterDao.getChapter(...)` | 长按回调 | → `lifecycleScope.launch(IO)` |

### 3. WelcomeActivity（启动页 - 影响启动速度）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 103 | `appDb.bookDao.lastReadBook` | `startMainActivity()` | → `withContext(IO)` 或预加载 |

### 4. BookInfoActivity（书籍详情页）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 184 | `appDb.bookSourceDao.getBookSource(book.origin)` | Activity 回调 | → `lifecycleScope.launch(IO)` |
| 796 | `appDb.bookSourceDao.has(book.origin)` | 点击回调 | → `lifecycleScope.launch(IO)` |

### 5. EffectiveReplacesDialog（替换规则弹窗 - 写操作）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 111 | `appDb.replaceRuleDao.insert(item)` | 关闭按钮回调 | → `Coroutine.async` |

### 6. KeyboardAssistsConfig（辅助键盘 - 批量写操作）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 132 | `appDb.keyboardAssistsDao.maxSerialNo` | 确认回调 | → `withContext(IO)` |
| 133 | `appDb.keyboardAssistsDao.insert(...)` | 确认回调 | → `withContext(IO)` |
| 136 | `appDb.keyboardAssistsDao.delete(...)` | 确认回调 | → `withContext(IO)` |
| 137 | `appDb.keyboardAssistsDao.insert(...)` | 确认回调 | → `withContext(IO)` |

### 7. RssFavoritesFragment/Activity（RSS 收藏 - 删除操作）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| Fragment:78 | `appDb.rssStarDao.delete(...)` | yesButton 回调 | → `lifecycleScope.launch(IO)` |
| Activity:145 | `appDb.rssStarDao.deleteByGroup(group)` | yesButton 回调 | → `lifecycleScope.launch(IO)` |
| Activity:158 | `appDb.rssStarDao.deleteAll()` | yesButton 回调 | → `lifecycleScope.launch(IO)` |

### 8. ReadRecordActivity（阅读记录 - 清除/删除）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 104 | `appDb.readRecordDao.clear()` | yesButton 回调 | → `lifecycleScope.launch(IO)` |
| 210 | `appDb.readRecordDao.deleteByName(...)` | yesButton 回调 | → `lifecycleScope.launch(IO)` |

### 9. ImportBookActivity/BaseImportBookActivity/RemoteBookActivity（本地导入）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| Import:314 | `appDb.bookDao.getBookByFileName(...)` | startRead() | → `withContext(IO)` |
| Import:318 | `appDb.bookDao.insert(it)` | startRead() | → `withContext(IO)` |
| BaseImport:95 | `appDb.bookDao.getBookByFileName(name)` | onArchiveFileClick | → `withContext(IO)` |
| BaseImport:112 | `appDb.bookDao.getBookByFileName(name)` | selector 回调 | → `withContext(IO)` |
| Remote:230 | `appDb.bookDao.getBookByFileName(...)` | startRead() | → `withContext(IO)` |

### 10. BookshelfManageActivity / CacheActivity

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| Manage:293 | `appDb.bookGroupDao.getByName(...)` | 菜单回调 | → `lifecycleScope.launch(IO)` |
| Cache:222 | `appDb.bookGroupDao.getByName(...)` | 菜单回调 | → `lifecycleScope.launch(IO)` |

### 11. RuleSubActivity

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 57 | `appDb.ruleSubDao.maxOrder` | 菜单回调 | → `lifecycleScope.launch(IO)` |

### 12. ChangeBookSourceDialog

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 394 | `appDb.bookSourceDao.getBookSource(book.origin)` | changeSource() | → `withContext(IO)` |

### 13. SpeakEngineDialog

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 335 | `appDb.httpTTSDao.delete(httpTTS)` | yesButton 回调 | → `lifecycleScope.launch(IO)` |

### 14. GroupManageDialog（书籍分组）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 96 | `appDb.bookGroupDao.canAddGroup` | 菜单回调 | → `withContext(IO)` |

### 15. BottomWebViewDialog

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 463 | `appDb.bookSourceDao.getBookSource(sourceKey)` | lifecycleScope.launch (默认 Main) | → 添加 IO 调度 |

### 16. ExploreAdapter

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 139 | `appDb.bookSourceDao.getBookSource(sourceUrl)` | Adapter convert | → 预加载或缓存 |

### 17. TextChapterLayout

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 497 | `appDb.bookChapterDao.upWordCount(...)` | 排版过程 | → 确认线程上下文 |

### 18. ReadRss（RSS 阅读 object）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 50 | `appDb.rssReadRecordDao.insertRecord(...)` | Fragment 生命周期 | → `withContext(IO)` |
| 76 | `appDb.rssSourceDao.getByKey(...)` | readNoHtml | → `withContext(IO)` |
| 101 | `appDb.rssSourceDao.getByKey(...)` | readNoHtml | → `withContext(IO)` |

### 19. RssJsExtensions（JS 扩展 - 多处）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 108 | `appDb.bookSourceDao.getBookSource(o)` | lifecycleScope.launch (Main) | → 添加 IO |
| 138 | `appDb.rssSourceDao.getByKey(o)` | 同上 | → 添加 IO |
| 153 | `appDb.rssSourceDao.getByKey(o)` | 同上 | → 添加 IO |
| 198 | `appDb.rssStarDao.get(...)` | 同上 | → 添加 IO |
| 205 | `appDb.rssReadRecordDao.insertRecord(...)` | 同上 | → 添加 IO |
| 220 | `appDb.bookSourceDao.getBookSource(o)` | 同上 | → 添加 IO |
| 231 | `appDb.bookSourceDao.getBookSource(o)` | 同上 | → 添加 IO |
| 253 | `appDb.bookChapterDao.getChapter(...)` | 同上 | → 添加 IO |

### 20. SearchScope（搜索范围 - 同步方法）

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 111 | `appDb.bookSourceDao.allEnabledPart` | 同步方法 | → 改为 suspend + withContext(IO) |
| 115 | `appDb.bookSourceDao.getBookSourcePart(it)` | 同上 | → 同上 |
| 122 | `appDb.bookSourceDao.getEnabledPartByGroup(it)` | 同上 | → 同上 |
| 133 | `appDb.bookSourceDao.allEnabledPart` | 同上 | → 同上 |

### 21. MediaButtonReceiver

| 行号 | 调用 | 上下文 | 修复方式 |
|------|------|--------|----------|
| 108 | `appDb.bookDao.lastReadBook` | BroadcastReceiver onReceive | → goAsync + IO |

---

## P1: Flow 缺少 flowOn(IO)

| 文件 | DAO Flow | 修复 |
|------|----------|------|
| BookSourceActivity:408 | `flowGroups()` | 添加 `.flowOn(IO)` |
| ChangeBookSourceDialog:262 | `flowEnabledGroups()` | 添加 `.flowOn(IO)` |
| ChangeChapterSourceDialog:242 | `flowEnabledGroups()` | 添加 `.flowOn(IO)` |
| ReplaceRuleActivity:230 | `flowGroups()` | 添加 `.flowOn(IO)` |
| GroupManageDialog(书源):64 | `flowGroups()` | 添加 `.flowOn(IO)` |
| GroupManageDialog(替换):64 | `flowGroups()` | 添加 `.flowOn(IO)` |
| GroupManageDialog(RSS):66 | `flowGroups()` | 添加 `.flowOn(IO)` |
| GroupSelectDialog:90 | `flowSelect()` | 添加 `.flowOn(IO)` |
| RssSourceActivity:223 | `flowGroups()` | 添加 `.flowOn(IO)` |
| SearchActivity:311 | `flowEnabledGroups()` | 添加 `.flowOn(IO)` |

---

## P2: 实体方法内 DAO 调用（调用方决定线程）

| 文件 | 方法 | DAO 调用 | 说明 |
|------|------|----------|------|
| Book.kt | `save()` | `appDb.bookDao.has/update/insert` | 调用方确保 IO |
| Book.kt | `delete()` | `appDb.bookDao.delete(this)` | 调用方确保 IO |
| BookChapter.kt | `update()` | `appDb.bookChapterDao.update(this)` | 调用方确保 IO |
| BookSourcePart.kt | `getBookSource()` | `appDb.bookSourceDao.getBookSource(...)` | 调用方确保 IO |

---

## 统计

| 类别 | 数量 |
|------|------|
| 高危 - 主线程 DAO 写操作 | ~25 处 |
| 高危 - 主线程 DAO 读操作 | ~30 处 |
| 中危 - Flow 缺少 flowOn(IO) | ~11 处 |
| 中危 - 实体方法内 DAO | ~5 处 |
| **总计** | **~71 处** |
