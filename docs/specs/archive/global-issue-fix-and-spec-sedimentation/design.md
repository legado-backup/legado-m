# Design: 全局问题修复与规范沉淀

## Technical Approach

### 整体架构：分层修复 + 规范先行

```
┌─────────────────────────────────────────────────────────────┐
│  规范层（先建）                                              │
│  global-thinking-checklist.md + spec-sedimentation-mechanism │
└──────────────────────────┬──────────────────────────────────┘
                           │ 约束
┌──────────────────────────▼──────────────────────────────────┐
│  数据库层（P0 阻塞，先修）                                  │
│  migration_96_97: DROP+CREATE VIEW                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ 装得上
┌──────────────────────────▼──────────────────────────────────┐
│  崩溃修复（P0）                                             │
│  MaterialButton → AppCompatButton                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ 不崩
┌──────────────────────────▼──────────────────────────────────┐
│  功能闭环（P1）                                             │
│  lastHost 三层回填 + 域名分组复合键                          │
│  校验逻辑重构（参考 Debug 模型）                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ 功能对
┌──────────────────────────▼──────────────────────────────────┐
│  UI Bug 修复（P1）                                          │
│  播放器菜单+返回+单源线程数+弹框样式                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ 体验好
┌──────────────────────────▼──────────────────────────────────┐
│  规范沉淀（P2 收尾）                                        │
│  本次错误沉淀到子规范，AGENTS.md 引用                        │
└─────────────────────────────────────────────────────────────┘
```

### 关键技术决策

#### 1. 数据库升级方案：version 97 + migration_96_97

**问题**：version=96 的有 bug 版本已执行 migration_95_96（只 ALTER TABLE 没 DROP+CREATE VIEW），view 结构是旧的。覆盖安装新 96 版本时 Room 不执行 migration（version 相同），但 schema 校验发现 view 不匹配，抛 IllegalStateException。

**方案**：
```kotlin
// AppDatabase.kt
@Database(version = 97, ...)

// DatabaseMigrations.kt
private val migration_96_97 = object : Migration(96, 97) {
    override fun migrate(db: SupportSQLiteDatabase) {
        // 强制重建 view，无论之前是 bug 版还是修复版
        db.execSQL("DROP VIEW IF EXISTS book_sources_part")
        db.execSQL("""CREATE VIEW book_sources_part AS
            select bookSourceUrl, ..., bookSourceType, lastHost
            from book_sources""")
    }
}
```

**为什么不用 fallbackToDestructiveMigrationFrom(96)**：会清空用户全部书源数据，不可接受。

#### 2. 高亮规则崩溃方案：MaterialButton → AppCompatButton

**问题**：dialog_highlight_rule_edit.xml 用 `MaterialButton` + `Widget.Material3.Button.TextButton` 样式，但项目主题是 `Theme.AppCompat.DayNight.NoActionBar`（非 Material 主题）。MaterialButton 构造时 ThemeEnforcement 校验失败抛 IllegalArgumentException。

**日志确认**（2026-07-16）：4 次 FATAL EXCEPTION 堆栈完全一致，全部为 `ThemeEnforcement.checkTheme:249` → `MaterialButton.<init>:300`，触发位置 `dialog_highlight_rule_edit` 第 89 行。确定性复现的致命崩溃。

**方案**：4 个布局的 `MaterialButton` 改为 `Button`（AppCompatButton），移除 `style="@style/Widget.Material3..."`。用 `?attr/borderlessButtonStyle` 或自定义样式保持视觉一致。

**为什么不改主题为 Material3**：影响全局所有页面，风险大，改组件类型更安全。

**备选方案**（日志分析建议，备选不优先）：
- 在 DialogFragment 的 `onCreate` 中 `setStyle(STYLE_NORMAL, R.style.Theme_MaterialComponents_Dialog)` 显式指定 Material 主题
- 或在 inflate 时用 `ContextThemeWrapper` 包装 Context 强制套用 Material 主题
- 这两种方案只影响该 DialogFragment，不影响全局，但比直接改组件类型复杂，作为备选

#### 3. 校验逻辑重构方案：参考 Debug 模型

**问题**：当前 doCheckSource 内部串行执行各维度，权重基于 hasGroup 二元判断，拿不到真实域名。

**方案**：
- 参考 `BookSourceDebugActivity` / `Debug` 模型的"分步骤收集结果"机制
- 单源内部各维度（搜索/发现/详情/目录/正文）可并发执行（受 concurrentRate 约束）
- 每个维度请求完成后，从 AnalyzeUrl 提取真实域名回填 lastHost
- 权重计算改为接收"关键元素获取结果"（如搜索结果数、详情字段完整度），按维度加权

```
doCheckSource(source) - 重构后
  ├─ 域名校验（可选，checkDomain 控制开关）
  │   └─ 回填 lastHost
  ├─ 维度并发（coroutineScope { async {} } 并发执行）
  │   ├─ 搜索维度：WebBook.searchBookAwait → 回填 lastHost + 收集结果数
  │   ├─ 发现维度：WebBook.exploreBookAwait → 回填 lastHost + 收集结果数
  │   └─ 详情维度：checkBook → 回填 lastHost + 收集字段完整度
  └─ 权重计算：基于关键元素获取结果加权（非 hasGroup 二元判断）
```

#### 4. lastHost 三层回填方案

**回填点扩展**：

| 层级 | 回填点 | 实现方式 |
|------|--------|---------|
| 真实使用层 | WebBook.searchBookAwait / getBookInfoAwait / getChapterListAwait / getContentAwait | AnalyzeUrl 创建后提取 host，异步回填 |
| 真实使用层 | Rss.getArticlesAwait / getContentAwait | 同上 |
| 调试层 | BookSourceDebugActivity / Debug 模型 | 请求回调中回填 |
| 校验层 | CheckSourceService / CheckRssSourceService | 已有，保持 |

**持久化策略**：`source.lastHost != newHost` 时才 update DB，避免每次请求都写。用内存缓存 + 批量持久化（如每 10 次变化或 App 退出时批量写）。

#### 5. 域名分组复合键方案

**BookSourceActivity**：
```kotlin
// 修改前：只按 host
compareBy<BookSourcePart> { getSourceHost(it.lastHost ?: it.bookSourceUrl) }

// 修改后：按 (host, type) 复合键
compareBy<BookSourcePart> { getSourceHost(it.lastHost ?: it.bookSourceUrl) }
    .thenBy { it.bookSourceType }
```

**RssSourceActivity**：补齐 `groupSourcesByDomain` 开关 + `getSourceHost` 方法，分组键 `(host, type)`。

#### 6. UI Bug 修复具体方案（基于子代理深度分析）

**问题 #1 菜单丢失**：
- `res/menu/video_play.xml` 添加 `<item android:id="@+id/menu_rss_refresh" ... />` 和 `<item android:id="@+id/menu_browser_open" ... />`（参考 `rss_read.xml` L5-8, L34-36 结构）
- `VideoPlayerActivity.onCompatOptionsItemSelected` 添加对应 when 分支
- 菜单可见性根据 `isRssSource` 条件显示

**问题 #2 返回按钮不生效**：
- 移除 `activity_video_player.xml` L16-19/L36-39 中**重复的 TitleBar**（只保留一个）
- 在保留的 TitleBar 上调用 `setNavigationOnClickListener { finish() }`（绕过 BaseActivity L127-133 final 方法的时序问题）
- 删除 `VideoPlayerActivity.onSupportNavigateUp` 死代码（L248-251）
- `switchToViewPagerMode` 改为同步执行或确保在 `onCreate` 完成前执行完毕

**问题 #4 单源线程数配置**：
- `activity_rss_source_edit.xml` 在"高级设置"折叠区添加 `EditText` 控件（inputType="number"，范围 1-32）
- `RssSourceEditActivity.kt` 在 `initView()` 绑定控件，在 `saveSource()` 保存到 `rssSource.parseConcurrency`
- 加载时读取 `parseConcurrency ?: AppConfig.rssParseConcurrency` 显示

**问题 #5 弹框样式不搭**：
- `bg_settings_panel.xml` 改为 `?attr/colorBackground`
- `bg_panel_button.xml` 改为 `?attr/colorControlHighlight`
- `styles.xml` L148 `VideoPanelButton` textColor 改为 `?attr/textColorPrimary`
- `layout_video_settings_panel.xml` 中9处硬编码颜色全部替换为 `?attr/*` 或 `@color/*` 引用

## Architecture Decisions

### AD-01: 数据库升级用 version+1 而非 fallbackToDestructiveMigration
- **Context**: migration_95_96 已执行但 view 未重建，覆盖安装失败
- **Concern**: 如何让已装 bug 版的用户能覆盖升级
- **Decision**: version 96→97，新增 migration_96_97 强制重建 view
- **Goal**: 覆盖安装成功，数据不丢失
- **Tradeoff**: 多一次 migration，但保证数据安全
- **Status**: Accepted

### AD-02: MaterialButton 改组件类型而非改主题
- **Context**: MaterialButton 需要 Material 主题，项目用 AppCompat 主题
- **Concern**: 如何修复崩溃且影响最小
- **Decision**: 4 个布局的 MaterialButton 改为 Button/AppCompatButton
- **Goal**: 崩溃修复，不影响全局主题
- **Tradeoff**: 视觉样式可能略有变化，用 borderlessButtonStyle 补偿
- **Status**: Accepted

### AD-03: 校验逻辑参考 Debug 模型而非完全重写
- **Context**: 当前校验和原来没区别，用户要求像调试模式一样
- **Concern**: 如何在风险可控下重构校验
- **Decision**: 复用 Debug 模型的分步骤收集结果机制，扩展 lastHost 回填
- **Goal**: 校验真正触发真实请求，拿到真实域名
- **Tradeoff**: 改动面较大，需充分测试
- **Status**: Accepted（根因已确认：doCheckSource 串行执行+权重二元判断，参考 Debug.kt L22-385 的 tasks.add 并发机制）

### AD-04: lastHost 持久化用"变化才写"策略
- **Context**: 真实使用时每次请求都回填会有性能问题
- **Concern**: 如何平衡实时性和性能
- **Decision**: 内存缓存 lastHost，变化时才写 DB，App 退出时批量持久化
- **Goal**: 回填实时可见，DB 写入开销可控
- **Tradeoff**: App 异常退出可能丢失少量未持久化的 lastHost（可接受）
- **Status**: Accepted（回填点已盘点：WebBook 4个方法+Rss 2个方法+Debug 5个步骤+校验已有）

### AD-05: 域名分组按 (host, type) 复合键
- **Context**: 用户要求一个域名可有多个类型的源
- **Concern**: 如何分组显示
- **Decision**: 分组键改为 (getSourceHost(lastHost ?: sourceUrl), bookSourceType)
- **Goal**: 站点A的文本源和音频源分开显示
- **Tradeoff**: 分组数变多，但符合用户期望
- **Status**: Accepted

### AD-06: 规范沉淀用"错误→沉淀→子规范→主规范引用"闭环
- **Context**: 同类错误反复犯（数据库升级、真机测试流程）
- **Concern**: 如何防止下次再犯
- **Decision**: 每次修复错误后，在 spec-sedimentation-mechanism.md 记录规则，AGENTS.md 引用
- **Goal**: AI 下次遇到同类场景时强制加载规范
- **Tradeoff**: 规范文件增多，但主规范保持精简（只引用不内联）
- **Status**: Accepted

### AD-07: 全局思考检查清单作为开发前置门禁
- **Context**: 改功能时不评估前端入口/后端接口/数据库/覆盖安装影响
- **Concern**: 如何强制全局思考
- **Decision**: 新建 global-thinking-checklist.md，在 OpenSpec 步骤1（需求分析）强制执行
- **Goal**: 开发前盘点所有影响范围
- **Tradeoff**: 增加设计阶段时间，但减少返工
- **Status**: Accepted

## Data Flow

### 数据库升级数据流（覆盖安装）

```
用户已装 version=96 (bug版, view无lastHost)
    ↓ 覆盖安装
新包 version=97
    ↓ App启动
Room 校验: 96 < 97, 执行 migration_96_97
    ↓
migration_96_97:
    DROP VIEW IF EXISTS book_sources_part
    CREATE VIEW book_sources_part AS ... (含lastHost)
    ↓
Room schema 校验: view结构 == @DatabaseView注解 → 通过
    ↓
App 正常启动, 书源数据保留
```

### lastHost 三层回填数据流

```
用户搜索书籍
    ↓
WebBook.searchBookAwait(source, query)
    ↓
内部创建 AnalyzeUrl(sourceUrl, ...)
    ↓
AnalyzeUrl 解析真实URL (处理jslib/注释/#规避)
    ↓
提取 host = URI(analyzeUrl.url).host
    ↓
内存缓存: sourceLastHostCache[sourceUrl] = host
    ↓ 变化才写DB
if (source.lastHost != host) {
    appDb.bookSourceDao.updateLastHost(sourceUrl, host)
}
    ↓
下次域名分组: getSourceHost(source.lastHost) → 真实域名
```

### 校验逻辑重构数据流

```
用户校验所选 (勾选"域名"CheckBox + AnalyzeUrl模式)
    ↓
CheckSourceService.doCheckSource(source)
    ↓
coroutineScope {
    async { 搜索维度 → 回填lastHost + 收集结果数 }
    async { 发现维度 → 回填lastHost + 收集结果数 }
    async { 详情维度 → 回填lastHost + 收集字段完整度 }
}
    ↓
SourceWeightCalculator.calculate(维度结果集)
    ↓ 基于关键元素获取程度加权
source.weight = 计算结果
    ↓
回填 weight 到 DB
```

## File Changes

### 数据库层（P0）
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/data/AppDatabase.kt` | 修改 | version 96→97 |
| `app/src/main/java/io/legado/app/data/DatabaseMigrations.kt` | 修改 | 新增 migration_96_97 |

### 崩溃修复（P0）
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/res/layout/dialog_highlight_rule_edit.xml` | 修改 | MaterialButton→Button |
| `app/src/main/res/layout/dialog_highlight_rule_group_manage.xml` | 修改 | MaterialButton→Button |
| `app/src/main/res/layout/dialog_highlight_note.xml` | 修改 | MaterialButton→Button |
| `app/src/main/res/layout/item_highlight_rule_group.xml` | 修改 | MaterialButton→Button |

### 功能闭环（P1）
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/model/webBook/WebBook.kt` | 修改 | 请求后回填 lastHost |
| `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 修改 | 请求后回填 lastHost |
| `app/src/main/java/io/legado/app/ui/book/source/debug/BookSourceDebugActivity.kt` | 修改 | 调试时回填 lastHost |
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt` | 修改 | 分组复合键 |
| `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt` | 修改 | 补齐域名分组 |
| `app/src/main/java/io/legado/app/service/CheckSourceService.kt` | 修改 | 校验逻辑重构 |
| `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 修改 | 校验逻辑重构 |
| `app/src/main/java/io/legado/app/model/SourceWeightCalculator.kt` | 修改 | 权重计算细化 |

### UI Bug 修复（P1）
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 修改 | 菜单+返回按钮修复 |
| `app/src/main/res/menu/video_player_menu.xml` | 修改 | 恢复刷新+浏览器打开 |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` | 修改 | 单源线程数配置 |
| `app/src/main/res/layout/activity_rss_source_edit.xml` | 修改 | 添加线程数配置控件 |

### 规范沉淀（P2）
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `docs/project-rules/spec-sedimentation-mechanism.md` | 新增 | 错误沉淀机制 |
| `docs/project-rules/global-thinking-checklist.md` | 新增 | 全局思考检查清单 |
| `docs/project-rules/database-migration-safety.md` | 新增 | 数据库升级安全规范 |
| `docs/project-rules/real-device-test-reuse.md` | 新增 | 真机测试流程复用规范 |
| `AGENTS.md` | 修改 | 引用新增子规范 |
| `assets/updateLog.md` | 修改 | 更新日志 |

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| migration_96_97 执行失败 | 低 | 阻塞用户 | runCatching 包裹+日志 |
| 校验逻辑重构引入新bug | 中 | 校验不准 | 充分真机测试 |
| lastHost 回增性能问题 | 低 | 卡顿 | 变化才写策略 |
| 域名分组复合键显示异常 | 低 | UI 错乱 | 真机验证显示 |
| MaterialButton 改样式视觉变化 | 低 | 样式不搭 | 用 borderlessButtonStyle 补偿 |
