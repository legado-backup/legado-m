# Legado 延伸版本「页面选择器」功能分析报告

> 分析日期：2026-07-06
> 分析对象：7 个 Legado 延伸版本（已 clone 到 `temp/forks-comparison/`）
> 分析目标：定位用户描述的「订阅源列表上方、搜索框和更多之间的页面选择器」功能

---

## 一、核心结论

| 项目 | 结论 |
|------|------|
| **功能所在版本** | **蛋蛋Max（Legado_Max）** —— 唯一实现完整页面选择器功能的延伸版本 |
| **UI 位置** | RssSortActivity（订阅源文章列表页）的 TitleBar 菜单中，`menu_search`（搜索框）和溢出菜单（"更多"）之间 |
| **UI 组件类型** | MenuItem（`showAsAction="always"`），显示文字"第 X 页"，点击弹出 `NumberPickerDialog` |
| **数据来源** | `RssSource.ruleNextPage` 字段（订阅源规则中的"下一页规则"），有此规则才显示页面选择器 |
| **交互逻辑** | 点击"第 X 页"菜单项 → 弹出 NumberPickerDialog（1~999 页）→ 选择目标页 → `viewModel.skipPage(targetPage)` + `loadArticles(targetPage)` 重新加载 |
| **本项目状态** | **缺失 UI 入口**。但 strings.xml 已有 `menu_page`/`change_page` 字符串、`Rss.getArticles` 已支持 page 参数、`NumberPickerDialog` 已存在、`RssSource.ruleNextPage` 字段已存在 —— 基础设施全部就绪 |
| **借鉴难度** | **低**。仅需新增菜单项 + 在 Activity/Fragment/ViewModel 接入约 50 行代码 |
| **是否建议借鉴** | **强烈建议**。功能实用、实现简洁、与项目现有架构完全兼容、无新依赖 |

---

## 二、7 个延伸版本扫描结果

### 2.1 仓库位置

全部已 clone 到 `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\`：

| 版本 | 目录 | 远程仓库 |
|------|------|---------|
| 蛋蛋Max | `Legado_Max/` | https://github.com/DandanLLab/Legado_Max |
| 阅读NG | `legado_NG/` | https://github.com/joestar817/legado_NG |
| 阅读T | `legadoT/` | https://github.com/skybbk1001/legadoT |
| 阅读Archive | `Rimchars_legado/` | https://github.com/Rimchars/legado |
| 阅读R | `refgd_legado/` | https://github.com/refgd/legado |
| Jingshiro | `Jingshiro_legado/` | https://github.com/Jingshiro/legado |
| 喵公子 | `LegadoTeam_legado/` | https://github.com/LegadoTeam/legado |

### 2.2 页面选择器功能存在性矩阵

扫描关键词：`showPagePicker` / `menu_page`（代码引用）/ `pageLiveData` / `skipPage` / `getCurrentPage`

| 版本 | 代码实现 | menu_page 菜单项 | strings 资源 | 完整功能 |
|------|---------|-----------------|-------------|---------|
| **Legado_Max** | ✅ 3 文件 | ✅ 有 | ✅ 有 | ✅ **完整** |
| legadoT | ❌ | ❌ | ❌ 无 | ❌ |
| legado_NG | ❌ | ❌ | ✅ 有（残留） | ❌ |
| Rimchars_legado | ❌ | ❌ | ✅ 有（残留） | ❌ |
| refgd_legado | ❌ | ❌ | ✅ 有（残留） | ❌ |
| Jingshiro_legado | ❌ | ❌ | ✅ 有（残留） | ❌ |
| LegadoTeam_legado | ❌ | ❌ | ✅ 有（残留） | ❌ |
| **本项目 legado** | ❌ | ❌ | ✅ 有（残留） | ❌ |

**关键发现**：
- 6 个 fork（除 legadoT 外）和本项目的 `strings.xml` 都残留了 `menu_page`/`change_page` 字符串，说明这些仓库的共同祖先（原版 legado-E 或更早版本）曾经有过此功能，但只有 Legado_Max 保留了完整实现。
- legadoT 走了另一条路线：用 `TabLayout + ViewPager2` 切换订阅源的**分类**（sortUrls），而非**翻页**。这是不同维度的功能。

### 2.3 legadoT 的差异（非页面选择器，需区分）

legadoT 的 `RssSortActivity` 用 `TabLayout + ViewPager2` + `TabLayoutMediator` 实现的是**分类切换**（基于 `rssSource.sortUrls()`），不是翻页。用户描述的"页面选择器"指的是**翻页**（第 X 页），对应 Legado_Max 的实现，不是 legadoT。

---

## 三、Legado_Max 页面选择器深度分析

### 3.1 UI 位置（完全匹配用户描述）

**布局位置**：RssSortActivity 的 TitleBar 菜单中

TitleBar 从左到右的菜单项顺序（见 `menu/rss_articles.xml`）：

```
[返回] [标题] [搜索框 menu_search] [第X页 menu_page] [更多(溢出)]
```

- `menu_search`：`showAsAction="always"`，搜索框（始终显示）
- `menu_page`：`showAsAction="always"`，显示"第 X 页"（始终显示）← **这就是页面选择器**
- `menu_login`/`menu_refresh_sort`/...：`showAsAction="never"`，隐藏在"更多"溢出菜单中

**用户描述"搜索框和更多之间"完全匹配**：`menu_page` 正好位于 `menu_search`（搜索框）和溢出菜单（"更多"按钮）之间。

### 3.2 UI 组件类型

**不是** TabLayout / Spinner / 自定义 View，而是一个**菜单项（MenuItem）**：

```xml
<item
    android:id="@+id/menu_page"
    android:title="@string/menu_page"
    app:showAsAction="always" />
```

- 显示文字：`第 %d 页`（动态格式化，如"第 1 页"、"第 5 页"）
- 点击行为：弹出 `NumberPickerDialog`（数字选择对话框，范围 1~999）
- 可见性：仅当 `RssSource.ruleNextPage` 不为空时显示（即订阅源配置了"下一页规则"）

### 3.3 数据来源

| 数据 | 来源 | 说明 |
|------|------|------|
| 当前页码 | `RssArticlesViewModel.page` / `pageLiveData` | LiveData，加载完成后通过 `pageLiveData.postValue(page)` 更新 |
| 是否显示 | `RssSource.ruleNextPage` | 订阅源实体字段，"下一页规则"。非空才显示页面选择器 |
| 最大页数 | 硬编码 `999` | NumberPickerDialog 的 `setMaxValue(999)` |
| 目标页加载 | `Rss.getArticles(scope, sortName, initialSortUrl, rssSource, page, searchKey)` | 底层已支持 page 参数 |

### 3.4 交互逻辑（完整流程）

```
用户点击"第 X 页"菜单项
        ↓
RssSortActivity.onCompatOptionsItemSelected
        → R.id.menu_page → currentArticlesFragment()?.showPagePicker()
        ↓
RssArticlesFragment.showPagePicker()
        → NumberPickerDialog(min=1, max=999, current=getCurrentPage())
        → 用户选择目标页 targetPage
        ↓
        if (targetPage != currentPage) {
            fullRefresh = true
            viewModel.skipPage(targetPage)      // 重置 page、清空 nextPageUrl、postValue 通知
            loadArticles(targetPage)             // 重新加载该页文章
            binding.recyclerView.scrollToPosition(0)  // 滚回顶部
        }
        ↓
RssArticlesViewModel.loadArticles(rssSource, targetPage)
        → page = targetPage
        → nextPageUrl = null
        → Rss.getArticles(..., page, ...)  // 用 page 参数请求
        → pageLiveData.postValue(page)     // 通知 UI 更新菜单文字
        → loadFinallyLiveData.postValue(hasMore)
```

**页码同步机制**：
- `onPageSelected`（ViewPager 切换分类 Tab）时：`updatePageMenu(it.getCurrentPage(), it.showPageMenu())`
- `onMenuOpened`（打开菜单时）：`updatePageMenu(it.getCurrentPage(), it.showPageMenu())`
- `pageLiveData.observe`：页码变化时自动更新菜单文字

### 3.5 涉及的源码文件列表（Legado_Max，相对路径）

| 文件 | 改动类型 | 关键内容 |
|------|---------|---------|
| `app/src/main/res/menu/rss_articles.xml` | 新增 menu_page 项 | `<item android:id="@+id/menu_page" android:title="@string/menu_page" app:showAsAction="always" />` |
| `app/src/main/res/values/strings.xml` | 新增字符串 | `<string name="menu_page">第 %d 页</string>` + `<string name="change_page">选择页数</string>` |
| `app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt` | 新增菜单逻辑 | `menuPage` 字段、`onCompatCreateOptionsMenu` 中 `menuPage = menu.findItem(R.id.menu_page)`、`onCompatOptionsItemSelected` 中 `R.id.menu_page -> currentArticlesFragment()?.showPagePicker()`、`updatePageMenu(page, visible)` 方法、`currentArticlesFragment()` 方法、`onPageSelected`/`onMenuOpened` 回调中调用 `updatePageMenu` |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt` | 新增页码方法 | `getCurrentPage()`、`showPageMenu()`、`showPagePicker()`、`loadArticles(targetPage)` 重载、`observeLiveBus()` 中 `pageLiveData.observe` |
| `app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt` | 新增页码状态 | `pageLiveData` 字段、`initialSortUrl` 字段、`loadArticles(rssSource, targetPage)` 重载、`loadMore` 中 `pageLiveData.postValue(page)`、`skipPage(targetPage)` 方法、`init` 中 `pageLiveData.value = page` |

**无需改动的文件**（基础设施已存在）：
- `app/src/main/java/io/legado/app/ui/widget/number/NumberPickerDialog.kt`（已存在）
- `app/src/main/java/io/legado/app/data/entities/RssSource.kt`（`ruleNextPage` 字段已存在）
- `app/src/main/java/io/legado/app/model/rss/Rss.kt`（`getArticles` 已支持 `page` 参数）

---

## 四、本项目（legado）对比结论

### 4.1 缺失项清单

本项目**只缺 UI 入口**，基础设施全部就绪：

| 检查项 | 本项目状态 | 说明 |
|--------|----------|------|
| `menu_page` 字符串 | ✅ 已有 | `strings.xml:1326 <string name="menu_page">第 %d 页</string>` |
| `change_page` 字符串 | ✅ 已有 | `strings.xml:1327 <string name="change_page">选择页数</string>` |
| `NumberPickerDialog` 组件 | ✅ 已有 | `app/src/main/java/io/legado/app/ui/widget/number/NumberPickerDialog.kt` |
| `RssSource.ruleNextPage` 字段 | ✅ 已有 | `data/entities/RssSource.kt:59` |
| `Rss.getArticles` 的 page 参数 | ✅ 已有 | `model/rss/Rss.kt:21-33` 完整支持 |
| `RssArticlesViewModel.pageLiveData` | ❌ 缺失 | 需新增 |
| `RssArticlesViewModel.skipPage()` | ❌ 缺失 | 需新增 |
| `RssArticlesViewModel.initialSortUrl` | ❌ 缺失 | 需新增（用于翻页时回到原始 URL） |
| `RssArticlesViewModel.loadArticles(rssSource, targetPage)` 重载 | ❌ 缺失 | 需新增 |
| `RssArticlesFragment.getCurrentPage/showPageMenu/showPagePicker` | ❌ 缺失 | 需新增 |
| `RssArticlesFragment.loadArticles(targetPage)` 重载 | ❌ 缺失 | 需新增 |
| `RssArticlesFragment.observeLiveBus` 中 `pageLiveData.observe` | ❌ 缺失 | 需新增 |
| `RssSortActivity` 中 `menuPage`/`updatePageMenu`/`currentArticlesFragment` | ❌ 缺失 | 需新增 |
| `RssSortActivity.onCompatCreateOptionsMenu` 中 `menuPage = menu.findItem(...)` | ❌ 缺失 | 需新增 |
| `RssSortActivity.onCompatOptionsItemSelected` 中 `R.id.menu_page` 分支 | ❌ 缺失 | 需新增 |
| `RssSortActivity.onPageSelected`/`onMenuOpened` 中 `updatePageMenu` 调用 | ❌ 缺失 | 需新增 |
| `menu/rss_articles.xml` 中 `menu_page` 项 | ❌ 缺失 | 需新增 |

### 4.2 本项目当前 `loadArticles` 的差异

本项目 `RssArticlesViewModel.loadArticles(rssSource)` 每次都 `page = 1`，无法跳转到指定页。Legado_Max 版本改为 `page = targetPage.coerceAtLeast(1)`，并保留 `initialSortUrl`（翻页时用原始 URL + page 参数请求，而非 nextPageUrl）。

本项目 `loadMore` 中**没有** `pageLiveData.postValue(page)`，而 Legado_Max 有（用于通知菜单更新页码显示）。

### 4.3 本项目 `RssSortActivity` 已有的多行 Tab

本项目 `RssSortActivity.kt` 已实现了多行标签 Tab（`setupMultiLineTabs`/`createTabView`/`updateTabSelection`），用于切换订阅源**分类**。这部分与页面选择器**不冲突**，页面选择器是在分类内的**翻页**，两者是不同维度。

---

## 五、借鉴难度评估

### 5.1 难度评级：低

| 维度 | 评估 | 说明 |
|------|------|------|
| 代码量 | 约 50 行 | 新增/修改分散在 4 个文件 |
| 依赖项 | 无新增 | `NumberPickerDialog`、`RssSource.ruleNextPage`、`Rss.getArticles(page)` 全部已存在 |
| 架构兼容性 | 完全兼容 | 不改动现有分类 Tab、Adapter、数据库结构 |
| 风险点 | 低 | 唯一注意点：`loadArticles` 改为支持 `targetPage` 时，需保留 `initialSortUrl` 以便翻页时回到原始 URL（而非用 nextPageUrl） |
| 测试复杂度 | 低 | 需找一个有 `ruleNextPage` 的订阅源验证翻页；无此规则的源应不显示菜单 |

### 5.2 借鉴实施步骤建议

1. **menu/rss_articles.xml**：在 `menu_search` 之后、`menu_login` 之前插入 `menu_page` 项（`showAsAction="always"`）
2. **RssArticlesViewModel.kt**：
   - 新增 `pageLiveData = MutableLiveData<Int>()`
   - 新增 `initialSortUrl` 字段，在 `init` 中赋值
   - `loadArticles` 改为 `loadArticles(rssSource, targetPage: Int = 1)`，用 `initialSortUrl` 请求
   - `loadMore` 中补 `pageLiveData.postValue(page)`
   - 新增 `skipPage(targetPage)` 方法
   - `init` 中补 `pageLiveData.value = page`
3. **RssArticlesFragment.kt**：
   - 新增 `getCurrentPage()`、`showPageMenu()`、`showPagePicker()`
   - 新增 `loadArticles(targetPage)` 重载
   - `observeLiveBus()` 中补 `pageLiveData.observe` → 调用 `(activity as? RssSortActivity)?.updatePageMenu(page, showPageMenu())`
4. **RssSortActivity.kt**：
   - 新增 `menuPage` 字段
   - `onCompatCreateOptionsMenu` 中 `menuPage = menu.findItem(R.id.menu_page)`
   - `onCompatOptionsItemSelected` 中新增 `R.id.menu_page -> currentArticlesFragment()?.showPagePicker()`
   - 新增 `updatePageMenu(page, visible)`、`currentArticlesFragment()` 方法
   - `onPageSelected`、`onMenuOpened` 中调用 `updatePageMenu`

### 5.3 注意事项

- `strings.xml` 中 `menu_page`/`change_page` 已存在，**不要重复添加**（否则编译报错）
- `menu_page` 的 `showAsAction="always"` 确保始终显示在 TitleBar，不被挤进溢出菜单
- `NumberPickerDialog` 的 `setMaxValue(999)` 是硬编码，可按需调整
- 当订阅源**没有** `ruleNextPage` 时，`showPageMenu()` 返回 false，`menuPage.isVisible = false`，菜单项隐藏 —— 不会对无分页规则的源造成干扰

---

## 六、是否建议借鉴

**强烈建议借鉴**。理由：

1. **用户需求明确**：用户主动提及此功能"相当实用"
2. **实现成本低**：约 50 行代码，无新依赖，基础设施全部就绪
3. **零破坏性**：对无 `ruleNextPage` 的订阅源无影响（菜单项自动隐藏）
4. **与现有功能协同**：与本项目的多行分类 Tab 正交，不冲突
5. **字符串资源已就绪**：`menu_page`/`change_page` 残留在 strings.xml 中，正好"激活"使用
6. **原版血统**：6 个 fork 和本项目的 strings.xml 都有此字符串，说明是原版功能，借鉴属于"恢复"而非"创新"

---

## 七、附录：关键源码片段

### 7.1 Legado_Max 的 menu_page 菜单项

文件：`app/src/main/res/menu/rss_articles.xml`（第 15-18 行）

```xml
<item
    android:id="@+id/menu_page"
    android:title="@string/menu_page"
    app:showAsAction="always" />
```

### 7.2 Legado_Max 的 showPagePicker 实现

文件：`app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt`（第 267-283 行）

```kotlin
fun showPagePicker() {
    if (!showPageMenu()) return
    val currentPage = getCurrentPage()
    NumberPickerDialog(requireContext())
        .setTitle(getString(R.string.change_page))
        .setMinValue(1)
        .setMaxValue(999)
        .setValue(currentPage)
        .show { targetPage ->
            if (targetPage != currentPage) {
                fullRefresh = true
                viewModel.skipPage(targetPage)
                loadArticles(targetPage)
                binding.recyclerView.scrollToPosition(0)
            }
        }
}
```

### 7.3 Legado_Max 的 skipPage 实现

文件：`app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt`（第 85-89 行）

```kotlin
fun skipPage(targetPage: Int) {
    page = targetPage.coerceAtLeast(1)
    nextPageUrl = null
    pageLiveData.postValue(page)
}
```

### 7.4 Legado_Max 的 updatePageMenu 实现

文件：`app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt`（第 350-355 行）

```kotlin
fun updatePageMenu(page: Int, visible: Boolean) {
    menuPage?.isVisible = visible
    if (visible) {
        menuPage?.title = getString(R.string.menu_page, page)
    }
}
```

---

## 八、报告说明

- 本报告所有结论均基于本地 clone 后的实际源码分析，未使用 GitHub API（避免缓存错误）
- 涉及的 7 个 fork 仓库位于 `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\`
- 本项目对比基线位于 `f:\myself\github\WeAgentChat\temp\legado\`
- 所有文件路径均为相对项目根目录的路径
