# 书源/订阅源一键互转 - 任务清单

> 状态: 待实施（V3 - 含JS库弥补方案）
> 依赖: design.md (V3 - JS库弥补方案版), spec.md

## Task Summary

| ID | 任务 | 优先级 | 复杂度 | 依赖 | 说明 |
|----|------|--------|--------|------|------|
| T1 | SourceConverter核心转换逻辑+可用性评估 | P0 | 高 | 无 | 含智能TocRule生成+4场景可用性评估+JS弥补replaceRegex |
| T2 | SourceConvertDialog预览对话框 | P0 | 中 | T1 | 含可用性星级显示+低可用性二次确认+JS弥补提示 |
| T3 | 书源单项菜单"转为订阅源" | P1 | 低 | T1,T2 | |
| T4 | 订阅源单项菜单"转为书源" | P1 | 低 | T1,T2 | |
| T5 | 书源批量菜单"转为订阅源" | P2 | 低 | T1,T2 | |
| T6 | 订阅源批量菜单"转为书源" | P2 | 低 | T1,T2 | |
| T7 | 字符串资源与UI优化 | P2 | 低 | T3-T6 | |
| T8 | 真机测试：转换后源可用性验证 | P0 | 高 | T1-T7 | **核心验证：转换后的源能不能用** |

---

## T1: SourceConverter核心转换逻辑+可用性评估

**优先级**: P0 | **复杂度**: 高 | **依赖**: 无

### 实施内容

1. 新建 `app/src/main/java/io/legado/app/data/entities/SourceConverter.kt`
2. 实现 `Usability` 枚举（HIGH/MEDIUM/LOW/UNUSABLE）
3. 实现 `Impact` 枚举（NONE/MINOR/MAJOR/CRITICAL）
4. 实现 `ConvertResult`/`FieldMapping`/`FieldLoss` 数据类
5. 实现 `bookSourceToRssSource(bookSource: BookSource): ConvertResult`
   - 基础字段直接映射（19个字段）
   - 类型映射：bookSourceType → RssSource.type
   - 规则映射：优先ExploreRule，其次SearchRule → 扁平规则
   - ContentRule映射：content→ruleContent, nextContentUrl→ruleNextPage
   - 丢失字段收集：含Impact评估
   - **可用性评估逻辑**：
     - 文本书源 → HIGH（有replaceRegex时V3版通过JS弥补保持HIGH）
     - 图片书源 → HIGH（单章完美，多章部分可用）
     - 视频书源 → MEDIUM（多线路不可用）
   - **V3新增：replaceRegex JS弥补**：
     - 当ContentRule.replaceRegex非空时：
       a. 解析replaceRegex为正则对列表 `parseReplaceRegex()`
       b. 生成JS清理函数 `buildJsCleanFunction()` 写入jsLib
       c. 修改ruleContent为 `<js>_convert_cleanContent(java.getString('原始规则',result))</js>`
       d. 函数命名加前缀 `_convert_` 避免与现有jsLib冲突
     - 当replaceRegex包含`@js:`内嵌JS时：标记为MAJOR（无法自动转换）
6. 实现 `rssSourceToBookSource(rssSource: RssSource): ConvertResult`
   - 基础字段直接映射（19个字段）
   - 类型映射：RssSource.type → bookSourceType
   - 规则映射：扁平规则 → SearchRule + ExploreRule
   - **智能TocRule生成**：ruleArticles→chapterList, ruleTitle→chapterName, ruleLink→chapterUrl
   - **视频单线路TocRule**：当type=2且ruleEpisodes非空时，用ruleEpisodes替代ruleArticles生成TocRule（将{routeIndex}替换为0）
   - BookInfoRule智能生成：用SearchRule字段填充
   - 丢失字段收集：含Impact评估
   - **可用性评估逻辑**：
     - 有智能TocRule + 文本/图片订阅源 → HIGH
     - 有智能TocRule + 视频订阅源 → LOW（多线路不可用，单线路可用）
     - 无智能TocRule → UNUSABLE
7. 实现 `generateSmartTocRule(rssSource: RssSource): TocRule?`
   - ruleArticles → chapterList
   - ruleTitle → chapterName
   - ruleLink → chapterUrl
   - ruleArticles为空时返回null
8. **V3新增：实现 `parseReplaceRegex(replaceRegex: String): List<Pair<String, String>>`**
   - 解析 `##regex##replacement##` 格式的replaceRegex
   - 支持 `&&` 分隔的多规则组合
   - 支持 `###` 三井号（replaceFirst）标记
9. **V3新增：实现 `buildJsCleanFunction(regexPairs: List<...>): String`**
   - 生成 `_convert_cleanContent(content)` JS函数
   - 将每对正则转换为 JS `content.replace(/pattern/g, 'replacement')`
   - 处理Java正则→JS正则的兼容性转换

### 验收标准

- [ ] 文本书源→订阅源：可用性=HIGH，核心流程可用
- [ ] **有replaceRegex的书源→订阅源：JS弥补后正文清洁度恢复，可用性=HIGH**
- [ ] 图片书源→订阅源：可用性=HIGH，图片查看流程可用
- [ ] 视频书源→订阅源：可用性=MEDIUM，多线路不可用警告
- [ ] 文本订阅源→书源：有智能TocRule时可用性=HIGH
- [ ] 图片订阅源→书源：有智能TocRule时可用性=HIGH
- [ ] 视频订阅源→书源：可用性=LOW，CRITICAL标记
- [ ] 无ruleArticles的订阅源→书源：可用性=UNUSABLE
- [ ] 空规则源转换不崩溃
- [ ] **V3新增：JS函数命名带 `_convert_` 前缀不与现有jsLib冲突**
- [ ] **V3新增：复杂replaceRegex（含@js:）标记为MAJOR而非自动转换**

### 涉及文件

| 文件 | 操作 |
|------|------|
| `data/entities/SourceConverter.kt` | 新建 |

---

## T2: SourceConvertDialog预览对话框

**优先级**: P0 | **复杂度**: 中 | **依赖**: T1

### 实施内容

1. 新建 `app/src/main/java/io/legado/app/ui/source/SourceConvertDialog.kt`
2. 继承 `BottomSheetDialogFragment`
3. 布局设计：
   - 顶部：转换方向 + 可用性星级（颜色标记：绿/黄/红）
   - 低可用性/UNUSABLE时：醒目红色警告区域，说明核心问题
   - 可映射字段区：绿色✓标记，折叠/展开
   - 丢失字段区：按Impact分级显示
     - CRITICAL/MAJOR：红色标记+影响说明
     - MINOR：灰色标记
     - NONE：隐藏
   - 注意事项区：关键警告
   - 底部按钮：
     - 可用性>=MEDIUM：[取消] [确认转换]
     - 可用性=LOW：[取消] [仍要转换]
     - 可用性=UNUSABLE：[取消] [仍要转换（不推荐）]
4. 批量模式：支持"全部确认"跳过后续预览
5. 确认回调：返回目标源实体列表
6. **V3新增：JS弥补提示区域**：
   - 当replaceRegex已编码为JS时：显示"已自动通过JS库弥补：正文替换规则"
   - 当imageDecode/imageStyle等不可弥补时：显示"不可弥补：图片解密/图片样式（架构限制）"
   - 当视频多线路不可弥补时：显示"不可弥补：多线路多集（数据结构限制）"

### 验收标准

- [ ] 可用性星级颜色正确（绿/黄/红）
- [ ] LOW/UNUSABLE时显示醒目警告
- [ ] CRITICAL/MAJOR丢失字段红色标记+影响说明
- [ ] 批量模式"全部确认"跳过后续预览
- [ ] 适配暗色/亮色主题

### 涉及文件

| 文件 | 操作 |
|------|------|
| `ui/source/SourceConvertDialog.kt` | 新建 |
| `res/layout/dialog_source_convert.xml` | 新建 |

---

## T3: 书源单项菜单"转为订阅源"

**优先级**: P1 | **复杂度**: 低 | **依赖**: T1, T2

### 实施内容

1. 在 `book_source_item.xml` 添加：
   ```xml
   <item android:id="@+id/menu_convert_to_rss" android:title="@string/convert_to_rss_source" />
   ```
2. 在 `BookSourceAdapter.showMenu()` 中添加点击处理：
   - 获取完整BookSource（非BookSourcePart，需要完整的规则字段）
   - 调用 `SourceConverter.bookSourceToRssSource(source)`
   - 弹出 `SourceConvertDialog`
   - 确认后写入数据库
   - Toast提示结果

### 注意事项

- BookSourceAdapter使用的是BookSourcePart（精简版，不含规则字段），需要额外查询完整BookSource
- 通过 `appDb.bookSourceDao().getByKey(source.bookSourceUrl)` 获取完整数据

### 涉及文件

| 文件 | 操作 |
|------|------|
| `res/menu/book_source_item.xml` | 修改 |
| `ui/book/source/manage/BookSourceAdapter.kt` | 修改 |

---

## T4: 订阅源单项菜单"转为书源"

**优先级**: P1 | **复杂度**: 低 | **依赖**: T1, T2

### 实施内容

1. 在 `rss_source_item.xml` 添加：
   ```xml
   <item android:id="@+id/menu_convert_to_book" android:title="@string/convert_to_book_source" />
   ```
2. 在 `RssSourceAdapter.showMenu()` 中添加点击处理：
   - 调用 `SourceConverter.rssSourceToBookSource(source)`
   - 弹出 `SourceConvertDialog`
   - 确认后写入数据库

### 涉及文件

| 文件 | 操作 |
|------|------|
| `res/menu/rss_source_item.xml` | 修改 |
| `ui/rss/source/manage/RssSourceAdapter.kt` | 修改 |

---

## T5: 书源批量菜单"转为订阅源"

**优先级**: P2 | **复杂度**: 低 | **依赖**: T1, T2

### 实施内容

1. 在 `book_source_sel.xml` 添加菜单项
2. 在 `BookSourceActivity.onMenuItemClick()` 中处理
3. 批量获取完整BookSource → 逐个转换 → 收集结果 → 批量预览确认

### 涉及文件

| 文件 | 操作 |
|------|------|
| `res/menu/book_source_sel.xml` | 修改 |
| `ui/book/source/manage/BookSourceActivity.kt` | 修改 |

---

## T6: 订阅源批量菜单"转为书源"

**优先级**: P2 | **复杂度**: 低 | **依赖**: T1, T2

### 实施内容

1. 在 `rss_source_sel.xml` 添加菜单项
2. 在 `RssSourceActivity.onMenuItemClick()` 中处理

### 涉及文件

| 文件 | 操作 |
|------|------|
| `res/menu/rss_source_sel.xml` | 修改 |
| `ui/rss/source/manage/RssSourceActivity.kt` | 修改 |

---

## T7: 字符串资源与UI优化

**优先级**: P2 | **复杂度**: 低 | **依赖**: T3-T6

### 实施内容

1. `strings.xml` 添加字符串资源：
   - `convert_to_rss_source`: "转为订阅源"
   - `convert_to_book_source`: "转为书源"
   - `convert_usability_high`: "可用性：高 - 核心功能可用"
   - `convert_usability_medium`: "可用性：中 - 部分功能需手动补充"
   - `convert_usability_low`: "可用性：低 - 核心功能缺失"
   - `convert_usability_unusable`: "转换后几乎不可用"
   - `convert_confirm`: "确认转换"
   - `convert_force_confirm`: "仍要转换"
   - `convert_force_confirm_not_recommended`: "仍要转换（不推荐）"
   - `convert_success`: "转换成功"
   - `convert_batch_success`: "成功转换 %1$d 个源，%2$d 个需手动补充规则"
   - `convert_warning_replace_regex`: "正文替换规则丢失，正文可能含广告或杂乱内容"
   - `convert_warning_video_routes`: "视频多线路/多集规则丢失，仅支持单线路播放"
   - `convert_warning_smart_toc`: "已自动生成目录规则，可能需要调整"
   - `convert_warning_explore_priority`: "搜索规则已忽略，使用发现规则映射"
   - `convert_mapped_fields`: "已映射字段"
   - `convert_lost_fields`: "将丢失字段"

### 涉及文件

| 文件 | 操作 |
|------|------|
| `res/values/strings.xml` | 修改 |

---

## T8: 真机测试：转换后源可用性验证

**优先级**: P0 | **复杂度**: 高 | **依赖**: T1-T7

> **这是最关键的测试**：转换后的源能不能用，才是用户最关心的。

### 测试用例

| # | 场景 | 操作 | 预期结果 | 可用性 |
|---|------|------|---------|--------|
| 1 | 文本书源→订阅源 | 转换后打开订阅源，浏览分类，查看文章内容 | 列表正常，正文可读 | HIGH |
| 2 | 有replaceRegex的书源→订阅源 | 同上 | **V3：JS弥补后正文无广告**，预览中显示"已自动弥补" | HIGH |
| 3 | 图片书源→订阅源 | 转换后打开订阅源，查看图片文章 | 图片列表正常显示 | HIGH |
| 4 | 视频书源→订阅源 | 转换后打开订阅源，浏览视频列表 | 列表正常，单线路可播放 | MEDIUM |
| 5 | 文本订阅源→书源 | 转换后搜索，查看搜索结果，进入详情 | 搜索结果正常显示 | HIGH |
| 6 | 文本订阅源→书源（阅读） | 转换后搜索→进入详情→查看目录→阅读章节 | 智能TocRule生效，可进入阅读 | HIGH |
| 7 | 图片订阅源→书源 | 转换后搜索→进入详情→查看目录→查看图片 | 智能TocRule生效，图片正常显示 | HIGH |
| 8 | 视频订阅源→书源 | 转换后搜索→查看目录 | 有TocRule但多线路不可用 | LOW |
| 9 | 无ruleArticles的订阅源→书源 | 尝试转换 | 预览显示UNUSABLE，需二次确认 | UNUSABLE |
| 10 | 空规则源转换 | 转换无规则的源 | 不崩溃，可用性=UNUSABLE | UNUSABLE |
| 11 | 已存在同URL源 | 转换后确认 | 覆盖成功 | - |
| 12 | 批量转换5个源 | 批量操作 | 逐个/全部确认，正确生成 | - |
| 13 | 转换后编辑源 | 转换后点击编辑 | 可正常打开编辑页面 | - |
| 14 | 智能TocRule准确性 | 订阅源→书源，验证目录列表 | 目录项与原订阅源文章列表一致 | - |
| **V3新增** 15 | JS弥补replaceRegex | 有replaceRegex的书源转订阅源后查看正文 | 正文无广告，JS函数`_convert_cleanContent`在jsLib中 | HIGH |
| **V3新增** 16 | 复杂replaceRegex不自动转换 | 含`@js:`的replaceRegex的书源转订阅源 | 预览中MAJOR标记，不自动生成JS，提示用户手动处理 | HIGH(有警告) |
| **V3新增** 17 | jsLib不冲突 | 原jsLib有同名函数的书源转订阅源 | `_convert_`前缀避免冲突，不影响原有jsLib函数 | - |
| **V3新增** 18 | 视频单线路TocRule | 视频订阅源(type=2+ruleEpisodes)转书源 | TocRule用ruleEpisodes生成，单线路目录正确 | LOW |

### 重点验证项

1. **场景6是核心验证**：文本订阅源→书源后能否完成完整阅读流程（搜索→详情→目录→正文）
2. **场景7是图片验证**：图片订阅源→书源后图片查看流程是否正常
3. **智能TocRule有效性**：自动生成的TocRule能否被BookChapterList正确解析
4. **视频单线路播放**：视频书源→订阅源后，无多线路时能否播放默认线路

### 验收标准

- [ ] 场景1-8的核心流程可用（含图片类型）
- [ ] 智能TocRule生成的书源可正常阅读（文本+图片）
- [ ] 图片订阅源→书源后图片查看流程正常
- [ ] **V3新增：有replaceRegex的书源→订阅源，JS弥补后正文无广告（场景15）**
- [ ] **V3新增：复杂replaceRegex不自动转换，MAJOR标记提示（场景16）**
- [ ] **V3新增：JS函数`_convert_`前缀不与现有jsLib冲突（场景17）**
- [ ] 可用性评估与实际体验一致
- [ ] 无崩溃、无ANR
- [ ] 预览对话框正确显示所有映射/丢失/警告/JS弥补信息

---

## Implementation Order

```
Phase 1: 核心逻辑 (T1) — 含可用性评估+智能TocRule
    │
Phase 2: 预览对话框 (T2) — 含可用性星级+低可用性警告
    │
Phase 3: UI入口 (T3, T4 并行)
    │
Phase 4: 批量入口 (T5, T6 并行)
    │
Phase 5: 字符串与UI优化 (T7)
    │
Phase 6: 真机测试 (T8) — 核心验证转换后源能否使用
```
