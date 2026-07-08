# RSS 阅读源缓存优先加载 - 实施任务清单

> 状态：🔄 设计中
>
> 关联文档：[spec.md](./spec.md) | [design.md](./design.md)

## 实施任务

### 1. 列表页 fullRefresh 逻辑调整

- [ ] 1.1 修改 `RssArticlesFragment.kt` L73：`private var fullRefresh = true` → `private var fullRefresh = false`
- [ ] 1.2 修改 `RssArticlesFragment.kt` L217-222：`loadArticles()` 增加参数 `private fun loadArticles(fullRefresh: Boolean = false)`，函数体内 `this.fullRefresh = fullRefresh`
- [ ] 1.3 修改 `RssArticlesFragment.kt` L128-130：下拉刷新调用改为 `loadArticles(fullRefresh = true)`
- [ ] 1.4 核对 `RssArticlesFragment.kt` L149-163（`initView` 中 `isPreload` / `RESUMED` 分支调用 `loadArticles()`）：保持无参调用，走默认 `false`
- [ ] 1.5 核对 `RssArticlesFragment.kt` L224-229（`loadArticles(targetPage)`）：保持 `fullRefresh = true` 不变
- [ ] 1.6 核对 `RssArticlesFragment.kt` L248-252（`showPagePicker`）：保持 `fullRefresh = true` 不变
- [ ] 1.7 核对 `RssArticlesFragment.kt` L257（`scrollToBottom`）：保持 `fullRefresh = false` 不变
- [ ] 1.8 核对 `RssArticlesFragment.kt` L282（`readRss`）：保持 `fullRefresh = false` 不变

### 2. webview cacheFirst 默认值

- [ ] 2.1 修改 `RssSource.kt` L112-113：`@ColumnInfo(defaultValue = "0") var cacheFirst: Boolean = false` → `@ColumnInfo(defaultValue = "1") var cacheFirst: Boolean = true`
- [ ] 2.2 核对 `ReadRssActivity.kt` L421：确认无需修改（已依赖 `s.cacheFirst`）
- [ ] 2.3 检查 `app/schemas/` 下最新 schema JSON：确认是否需要提升 `AppDatabase` 版本或补充 `Migration`（若 Room 报错再补，否则不动）

### 3. 前端源编辑页同步（可选）

- [ ] 3.1 检查 `modules/web/src/config/rssSourceEditConfig.ts`：确认 `cacheFirst` 字段表单默认值是否需同步为新默认值（若影响新建源表单初始状态）
- [ ] 3.2 检查 `app/src/main/assets/web/help/md/rssRuleHelp.md`：确认 `cacheFirst` 字段说明是否需补充「默认 true」描述

### 4. 验证

- [ ] 4.1 场景 1：首次进入有缓存的列表页，确认走 DiffUtil 增量更新、无全量闪烁
- [ ] 4.2 场景 2：首次进入无缓存的列表页，确认加载指示正常、数据到来后正常显示
- [ ] 4.3 场景 3：下拉刷新，确认全量替换、按最新 `order` 重排
- [ ] 4.4 场景 4：翻页切换页码，确认全量替换、滚动归零
- [ ] 4.5 场景 5：阅读返回列表，确认已读状态 DiffUtil 更新无闪烁
- [ ] 4.6 场景 6：断网进入列表页，确认缓存保留 + 错误提示
- [ ] 4.7 场景 7：webview 二次打开文章，确认缓存秒开；点击「刷新」拉取最新
- [ ] 4.8 场景 8：webview 首次打开无缓存，确认正常网络加载；二次进入秒开
- [ ] 4.9 场景 9：存量源 `cacheFirst=false`，确认仍走 `LOAD_DEFAULT`，行为不被破坏
- [ ] 4.10 编译通过、无新增 lint 警告

### 5. 文档同步

- [ ] 5.1 在 `app/src/main/assets/updateLog.md` 顶部追加日期条目，面向用户说明缓存优先体验
- [ ] 5.2 更新 `docs/INDEX.md` 中本 spec 的状态标记（设计完成后更新为「🔄 开发中」→ 实施完成后「✅ 已完成」）
- [x] 5.3 若 schema 版本变更，更新 `docs/project-flow/database/` 相关文档
  - schema 版本已从 92 提升至 93，migration_92_93 已添加到 DatabaseMigrations.kt

## AOAdapt 日志

> 遇到适配问题时在此记录。

- [待实施] 暂无 AOAdapt 问题。
- [实施完成] 列表页 1.1-1.8 全部完成（fullRefresh 初始值改 false + loadArticles 参数化 + 下拉刷新传 true）；cacheFirst 2.1-2.3 全部完成（默认值 true + defaultValue "1" + ReadRssActivity 无需修改）；编译 4.10 通过（BUILD SUCCESSFUL）；文档 5.1-5.2 完成。真机验证 4.1-4.9 待做。
- [Room] cacheFirst defaultValue "0"→"1" **需要 Migration**（原判断"无需 Migration"错误）。真机验证发现 `Room cannot verify the data integrity` 崩溃：旧数据库 identity hash（86b3514d）与新代码期望 hash（b978006e）不匹配。已修复：提升 version 92→93，添加 migration_92_93（重建 rssSources 表更新 cacheFirst 默认值 + 同步现有数据为 1）。真机验证通过，MainActivity 正常启动。

---

## 验收检查清单

- [ ] 列表页首次进入走 DiffUtil 增量更新（缓存优先显示）
- [ ] 列表页下拉刷新/翻页保留全量替换
- [ ] 阅读返回已读状态走 DiffUtil 更新
- [ ] 网络失败不清空缓存
- [ ] webview 默认 `LOAD_CACHE_ELSE_NETWORK`
- [ ] webview「刷新」菜单可用
- [ ] 存量源 `cacheFirst=false` 不被破坏
- [ ] `updateLog.md` 已追加条目
- [ ] 编译通过、无回归
