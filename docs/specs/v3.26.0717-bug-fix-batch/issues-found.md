# Issues Found - v3.26.0717 真机测试深度分析

> 状态统计：总计 6，已修复 5（前序），加强修复 1（本轮），待验证 6（问题6评估）
> 日志来源：`temp/tmp/Downloadslogs.(1)..zip`
> 日志版本：`versionName=3.26.071619debug`（7月16日19时编译，修复前版本）
> 当前编译版本：`legado_app_3.26.071709.apk`（7月17日9时，已含前序修复）

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

- **状态**：已修复（前序）✅
- **优先级**：中
- **现象**：订阅源编辑页"解析并发"显示为 0 或空
- **根因**：`RssSourceEditActivity.kt:303-305` 当 `parseConcurrency=0` 时显示空，未显示继承的系统配置值
- **设计**：未配置时显示系统配置值并标注"（继承全局）"
- **当前修复**：`RssSourceEditActivity.kt:306-311`
  ```kotlin
  if (rs.parseConcurrency > 0) {
      binding.editParseConcurrency.setText(rs.parseConcurrency.toString())
  } else {
      binding.editParseConcurrency.setText("")
      binding.editParseConcurrency.hint = "继承全局（${AppConfig.rssParseConcurrency}）"
  }
  ```
- **日志验证**：logcat 中无相关异常，需真机验证显示效果

## Issue-2：高亮规则颜色选择器暗色主题下预设色块全显示白色

- **状态**：已修复（前序）✅
- **优先级**：高
- **现象**：暗色主题下点击颜色按钮，弹出的 ColorPickerDialog 中 6 个预设色块全部显示白色
- **根因**：`ColorPickerDialog` 第三方库内部 `setStyle(STYLE_NO_FRAME, 0)`，0 表示用 Activity 主题（暗色）
- **当前修复**：`HighlightRuleEditDialog.kt:128`
  ```kotlin
  dialog.setStyle(androidx.fragment.app.DialogFragment.STYLE_NO_FRAME, R.style.AppTheme_Light)
  ```
- **依赖验证**：`styles.xml:6` 确认 `<style name="AppTheme.Light" parent="Base.AppTheme">` 存在 ✅
- **日志验证**：logcat 中无相关异常，需真机验证色块显示

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

---

## 待办事项

1. **加强修复 Issue-3**：对 `textChapter.pages` 做 snapshot（本轮新增）
2. **真机验证全部修复**：安装 3.26.071709 或更新版本，验证问题 1-5
3. **用户确认 Issue-6 方向**：AskUserQuestion 三选一
