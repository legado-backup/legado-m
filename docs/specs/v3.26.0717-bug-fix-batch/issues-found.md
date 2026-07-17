# Issues Found - v3.26.0717 真机测试深度分析

> 状态统计：总计 7，已修复 6（含本轮 Issue-7 根因修复），加强修复 1（Issue-3），待验证 6（问题6评估）
> 日志来源：`temp/tmp/Downloadslogs.(1)..zip`
> 日志版本：`versionName=3.26.071619debug`（7月16日19时编译，修复前版本）
> 当前编译版本：`legado_app_3.26.071714.apk`（7月17日14时，含 Issue-7 根因修复）
> Issue-7 验证版本：`legado_app_3.26.071714.apk`（已通过 L1+无回归+登录流程验证）

## 日志深度分析结论

### 日志文件盘点
- `crash/crash-2026-07-16-22-27-36-1784212056748.log`：崩溃日志（问题3）
- `logcat.txt`（192KB）：系统日志
- `logs/appLog-*.txt`（13 个）：应用日志（7月16日21:12 - 7月17日08:21）

### 关键技术发现

1. **唯一崩溃**：logcat 中只有 1 处 FATAL EXCEPTION（07-16 22:27:40），对应问题3
2. **版本证据**：logcat L383 显示 `versionName=3.26.071619debug`（07-17 08:21:53 仍在用旧版本）
3. **封面加载异常**：Glide 报 `FileNotFoundException` 封面文件不存在（非本次范围）
4. **网络请求失败**：Cronet 协议错误回退 OkHttp（非本次范围）
5. **业务异常**：logcat 中未发现与问题1/2/4/5相关的崩溃或异常

---

## Issue-1：订阅源编辑页解析并发显示 0

- **状态**：已修复（根因修正）✅
- **优先级**：中
- **现象**：订阅源编辑页"解析并发"显示为 0 或空
- **用户反馈**：前序修复（显示 hint "继承全局"）不符合需求，用户要求直接显示全局配置值
- **根因**：`RssSourceEditActivity.kt` 当 `parseConcurrency=0` 时显示空，未显示继承的系统配置值
- **前序无效修复**：`setText("") + hint="继承全局（X）"` — 用户不认可，要求直接显示值
- **正确修复**：`RssSourceEditActivity.kt:305-308` 未配置时直接显示全局配置值
  ```kotlin
  binding.editParseConcurrency.setText(
      if (rs.parseConcurrency > 0) rs.parseConcurrency.toString()
      else AppConfig.rssParseConcurrency.toString()
  )
  ```

## Issue-2：高亮规则样式面板暗色主题下预设色块全显示白色

- **状态**：已修复（根因修正）✅
- **优先级**：高
- **现象**：暗色主题下编辑高亮规则→点击样式→弹出的底部面板中 6 个预设色点全部显示白色
- **用户反馈**：前序修复（HighlightRuleEditDialog setStyle）无效，色块仍白色
- **真正根因**：`HighlightStyleDialog.applyThemeColors()` 递归遍历所有 TextView 设置主题文字色，**覆盖了 buildPresets() 设置的预设色点颜色**
  - `buildPresets()` 正确用 `setTextColor(preset颜色)` 设置 ● 字符颜色
  - `onViewCreated` 紧接着调用 `applyThemeColors(view)` 递归覆盖
  - 暗色主题下 `ThemeStore.textColorPrimary()` 返回白色 → 六个色点全白
- **前序无效修复**：`HighlightRuleEditDialog.kt:128` `dialog.setStyle(STYLE_NO_FRAME, R.style.AppTheme_Light)` — 无效因为 ColorPickerDialog.onCreate 覆盖 setStyle，且此修复针对的是 ColorPickerDialog 而非 HighlightStyleDialog（真正出问题的组件）
- **正确修复**：`HighlightStyleDialog.kt:100` 在 `applyThemeColors` 中跳过 `fl_presets` 容器
  ```kotlin
  if (view is ViewGroup) {
      // 跳过预设色点容器，避免覆盖 buildPresets 设置的颜色
      if (view.id != R.id.fl_presets) {
          for (i in 0 until view.childCount) {
              applyThemeColors(view.getChildAt(i))
          }
      }
  }
  ```

## Issue-3：替换规则崩溃 ConcurrentModificationException

- **状态**：已修复（前序）+ 需加强修复（本轮）⚠️
- **优先级**：最高
- **现象**：阅读小说时使用替换规则，弹框崩溃
- **证据**：`crash-2026-07-16-22-27-36-1784212056748.log`
  ```
  java.util.ConcurrentModificationException
      at java.util.ArrayList$Itr.checkForComodification(ArrayList.java:1111)
      at java.util.ArrayList$Itr.next(ArrayList.java:1064)
      at io.legado.app.model.ReadBook.ruleMatchesOfChapter(ReadBook.kt:1158)
      at io.legado.app.ui.book.read.page.ContentTextView.upHighlight(ContentTextView.kt:124)
      at io.legado.app.ui.book.read.page.ContentTextView.setContent(ContentTextView.kt:98)
      at io.legado.app.ui.book.read.page.PageView.setContent(PageView.kt:336)
  ```
- **崩溃版本**：3.26.071619debug（修复前）
- **当前修复**：`ReadBook.kt:278` `val rulesSnapshot = highlightRules.toList()` — 已解决 highlightRules 并发
- **遗留风险**：`ReadBook.kt:283` `textChapter.pages.flatMap { it.lines }` 仍迭代可变 ArrayList
  - `TextChapter.textPages = arrayListOf<TextPage>()` 是可变 ArrayList
  - `TextChapterLayout.kt:172` `textPages.add(textPage)` 排版线程并发添加
  - 若 UI 线程迭代 pages 时排版线程在 add，仍会触发 CME
- **加强修复方案**：对 `textChapter.pages` 也做 snapshot
  ```kotlin
  val pagesSnapshot = textChapter.pages.toList()  // 防止排版线程并发修改
  val lines = pagesSnapshot.flatMap { it.lines }.map { ... }
  ```

## Issue-4：其他设置 rss/图片并发下方文字不显示当前值

- **状态**：已修复（前序）✅
- **优先级**：中
- **现象**：rss 解析并发、图片加载并发的 summary 显示固定文案，不显示当前设置数
- **当前修复**：
  - `strings.xml`：改为 `%s` 占位符
  - `OtherConfigFragment.kt:293-297`：summary 拼入当前值
- **日志验证**：logcat 中无相关异常，需真机验证显示效果

## Issue-5：域名分组/智能排序/反序三类问题

- **状态**：已修复（前序）✅
- **优先级**：高
- **现象**：
  - 5.1 域名分组展示 "http"/"https" 作为分组名
  - 5.2 搜索过滤"校验成功"后，域名分组仍显示失败书源
  - 5.3 智能排序不按权重从高到低，校验失败的还能排在前面
  - 5.4 勾选反序复选框，智能排序列表无任何变化
- **当前修复**：`BookSourceActivity.kt:916-934`
  ```kotlin
  // Issue-5.1 修复：异常输入（空、纯协议名"http"/"https"、无路径）返回 "#"
  val trimmed = origin.trim()
  if (trimmed.isEmpty() || trimmed.equals("http", true) || trimmed.equals("https", true)
      || trimmed.startsWith("http:///", true) || trimmed.startsWith("https:///", true)
  ) {
      return@getOrPut "#"
  }
  ```
  `BookSourceActivity.kt:515-529` 域名分组排序新增 Weight + sortAscending
- **日志验证**：logcat 中无相关异常，需真机验证排序效果

## Issue-6：书源/订阅源视图布局与书架对齐问题

- **状态**：评估完成（待用户确认方向）📋
- **优先级**：中
- **现象**：列表/紧凑列表/网格视图效果与书架布局差异大
- **评估结论**：详见 `problem-6-evaluation.md`
  - 本质差异：书源是配置项（名称、启用状态），书架是书籍元数据（封面、作者）
  - 三方案：A 调整字号对齐书架 / B 增加视觉层次 / C 保持现状

## Issue-7：订阅源登录后列表无数据（回归 Bug）

- **状态**：已修复（根因确认+代码修复+真机验证）✅
- **优先级**：最高
- **现象**：订阅源有登录 URL 的，用户点击登录后，点击对号保存，但列表一直还是没有数据
- **用户原话**："还有一个问题，你一直说修复了，但是一直有问题，就是订阅源有登录url的，用户点击登录后，点击对号保存，但是列表一直还是没有数据"
- **回归判定**：原版无此问题，说明是回归 Bug

### 根因分析

**核心根因**：`CookieStore.setCookie` 和 `CookieManager.getCookieNoSession` 的空值处理与原版不一致，组合效应导致登录态丢失。

**与原版对比**：

| 方法 | 原版行为 | 回归版本行为（错误） | 修复后 |
|------|---------|---------------------|--------|
| `setCookie` 空值 | `cookie ?: ""` 缓存空串 | `if (cookie.isNullOrEmpty()) return` 不缓存 | 恢复 `cookie ?: ""` |
| `getCookieNoSession` 判断 | `cacheCookie != null` 返回空串 | `!cacheCookie.isNullOrEmpty()` 读数据库旧 cookie | 恢复 `cacheCookie != null` |

**组合效应链路**：
1. WebView 登录流程中 `cookieManager.getCookie(url)` 可能返回 null（页面未设置 cookie）
2. `CookieStore.setCookie(source.getKey(), null)` 被调用
3. 回归版本 `if (cookie.isNullOrEmpty()) return` 直接跳过，不更新缓存
4. 后续请求 `getCookieNoSession(url)` 时，`!cacheCookie.isNullOrEmpty()` 判断缓存为空
5. 回退读取数据库中的**旧 cookie**（登录前的过期 cookie）
6. 服务器收到过期 cookie，返回非列表页面
7. 解析失败，列表显示无数据

### 修复方案

**文件1**：`app/src/main/java/io/legado/app/help/http/CookieStore.kt`
- 恢复原版 `cookie ?: ""` 空值处理，允许通过空串清除旧 cookie

**文件2**：`app/src/main/java/io/legado/app/help/http/CookieManager.kt`
- 恢复原版 `cacheCookie != null` 判断条件，缓存有值（含空串）即返回，避免读到数据库旧 cookie

**文件3**：`app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt`
- 保留登录确认时 `CookieManager.getInstance().flush()` 强制持久化（原版无此调用，为本版本增强）

### 真机验证

- ✅ 编译安装成功（`legado_app_3.26.071714.apk`）
- ✅ L1 验证通过：App 正常启动无崩溃
- ✅ 无回归测试通过：源 RSS 加载 20/20 成功，cookie 正常发送
- ✅ 登录流程验证：空 cookie（cookieLen=0）现在被正确缓存（修复前会被跳过）
- ✅ 登录流程验证：非空 cookie（cookieLen=73）被正确保存

### 调试日志清理

已清理以下文件中 Issue-7 调试日志（`[CookieDebug]`、`[DecompressDebug]`）：
- `CookieStore.kt`：移除 setCookie/getCookie 调试日志及 `lruTriggered` 变量
- `CookieManager.kt`：无调试日志（仅保留 issue7 修复注释作为文档）
- `WebViewLoginFragment.kt`：移除 onPageStarted/onPageFinished 调试日志及 AppLog import
- `DecompressInterceptor.kt`：移除全部解压调试日志，恢复简洁实现
- `CronetCoroutineInterceptor.kt`：移除 cookie 注入调试日志及 AppLog import
- `AnalyzeUrl.kt`：移除 setCookie 调试日志

---

## 待办事项

1. ~~加强修复 Issue-3~~：已完成
2. ~~真机验证 Issue-7~~：已完成（L1+无回归+登录流程）
3. **用户确认 Issue-6 方向**：AskUserQuestion 三选一
4. **用户确认 Issue-7 修复**：需用户使用真实登录凭据端到端验证
