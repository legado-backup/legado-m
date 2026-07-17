# Issues Found - v3.26.0717 真机测试

> 状态统计：总计 6，已修复 0，进行中 0，搁置 0

## Issue-1：订阅源编辑页解析并发显示 0

- **状态**：进行中
- **优先级**：中
- **现象**：订阅源编辑页"解析并发"显示为 0 或空
- **根因**：`RssSourceEditActivity.kt:303-305` 当 `parseConcurrency=0` 时显示空，未显示继承的系统配置值
- **设计**：未配置时显示系统配置值并标注"（继承全局）"
- **修复位置**：`RssSourceEditActivity.kt`

## Issue-2：高亮规则颜色选择器暗色主题下预设色块全显示白色

- **状态**：进行中
- **优先级**：高
- **现象**：暗色主题下点击颜色按钮，弹出的 ColorPickerDialog 中 6 个预设色块全部显示白色
- **根因**：`ColorPickerDialog` 第三方库内部主题不适配暗色主题，预设色块文字/边框在暗色主题下变白色
- **设计**：用 ContextWrapper 包装亮色主题传给 ColorPickerDialog
- **修复位置**：`HighlightRuleEditDialog.kt:createColorPickerDialog`

## Issue-3：替换规则崩溃 ConcurrentModificationException

- **状态**：进行中
- **优先级**：最高
- **现象**：阅读小说时使用替换规则，弹框崩溃
- **根因**：`ReadBook.kt:ruleMatchesOfChapter` 中 `highlightRules.map {}` 迭代 ArrayList 时，另一线程调用 `loadHighlightRules` 修改引用触发 `ConcurrentModificationException`
- **证据**：`crash-2026-07-16-22-27-36-1784212056748.log`
- **设计**：在 `ruleMatchesOfChapter` 入口处创建本地副本 `highlightRules.toList()`
- **修复位置**：`ReadBook.kt:ruleMatchesOfChapter`

## Issue-4：其他设置 rss/图片并发下方文字不显示当前值

- **状态**：进行中
- **优先级**：中
- **现象**：rss 解析并发、图片加载并发的 summary 显示固定文案，不显示当前设置数
- **根因**：`OtherConfigFragment.kt:293-297` 使用固定字符串 `R.string.rss_parse_concurrency_summary`，未把 value 拼入
- **设计**：改用带占位符的字符串模板（与 threadCount 一致）
- **修复位置**：`OtherConfigFragment.kt` + `strings.xml`

## Issue-5：域名分组/智能排序/反序三类问题

- **状态**：进行中
- **优先级**：高
- **现象**：
  - 5.1 域名分组展示 "http"/"https" 作为分组名
  - 5.2 搜索过滤"校验成功"后，域名分组仍显示失败书源
  - 5.3 智能排序不按权重从高到低，校验失败的还能排在前面
  - 5.4 勾选反序复选框，智能排序列表无任何变化
- **根因**：
  - `BookSourceActivity.kt:899-909 getSourceHost` 对异常 URL 返回协议名
  - `BookSourceActivity.kt:514-518` 域名分组排序使用 `compareBy().thenBy().thenByDescending(lastUpdateTime)`，不含 Weight
  - 域名分组排序未传入 `sortAscending` 参数
- **设计**：
  - getSourceHost 增加 http/https 协议名过滤
  - 域名分组排序新增 weight 字段
  - 域名分组支持 sortAscending 反序
- **修复位置**：`BookSourceActivity.kt`

## Issue-6：书源/订阅源视图布局与书架对齐问题

- **状态**：进行中
- **优先级**：中
- **现象**：列表/紧凑列表/网格视图效果与书架布局差异大
- **根因**：待评估（需对比 BookSourceAdapterCompact/Grid 与书架 BooksAdapterListByGrid 的布局 XML）
- **设计**：先评估列清单，再根据用户确认修复
- **修复位置**：`BookSourceAdapterCompact.kt` / `BookSourceAdapterGrid.kt` / `RssSourceAdapterCompact.kt` / `RssSourceAdapterGrid.kt`
