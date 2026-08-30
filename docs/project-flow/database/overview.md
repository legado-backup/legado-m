# 数据库概览

## 基本信息

| 项目 | 值 |
|------|------|
| 数据库名 | legado.db |
| 数据库引擎 | SQLite |
| ORM | Room (AndroidX) |
| 当前版本 | 108（以 AppDatabase.kt version 字段为准） |
| 实体表数量 | 21 |
| 视图数量 | 1 |
| Schema 目录 | app/schemas/io.legado.app.data.AppDatabase/ |
| 迁移方式 | AutoMigration (v43+) + 手动迁移 |

## 设计原则

- **位标志（Bit Flags）**：`books.type` 和 `books.group` 使用位运算，高效支持多类型/多分组查询
- **JSON 存储**：规则字段、复杂配置以 JSON 文本存储，Room 通过 `@TypeConverter` 序列化/反序列化
- **级联删除**：关联数据（章节、搜索结果）在外键上配置 `ON DELETE CASCADE`
- **复合主键**：多对多关系表使用复合主键

---

## 实体关系总览

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
erDiagram
    books ||--o{ chapters : "bookUrl FK CASCADE"
    books ||--o{ bookmarks : "逻辑关联(bookName+bookAuthor)"
    books ||--o{ readRecord : "逻辑关联(bookName)"
    book_sources ||--o{ searchBooks : "origin FK CASCADE"
    rssSources ||--o{ rssArticles : "逻辑关联(origin)"
    rssArticles ||--o{ rssReadRecords : "逻辑关联(record)"
    rssArticles ||--o{ rssStars : "逻辑关联(link)"

    books {
        string bookUrl PK
        long group "FK→book_groups(逻辑引用)"
    }
    book_groups {
        long groupId PK
    }
    chapters {
        string url PK
        string bookUrl PK_FK
    }
    book_sources {
        string bookSourceUrl PK
    }
    searchBooks {
        string bookUrl PK
        string origin FK
    }
    rssSources {
        string sourceUrl PK
    }
    rssArticles {
        string origin PK
        string link PK
        string sort PK
    }
    rssStars {
        string origin PK
        string link PK
    }
    rssReadRecords {
        string record PK
    }
    replace_rules {
        int id PK
    }
    httpTTS {
        int id PK
    }
    cookies {
        string url PK
    }
    caches {
        string key PK
    }
    search_keywords {
        string word PK
    }
    dictRules {
        string name PK
    }
    txtTocRules {
        int id PK
    }
    ruleSubs {
        int id PK
    }
    keyboardAssists {
        int type PK
        string key PK
    }
    servers {
        int id PK
    }
    readRecord {
        string deviceId PK
        string bookName PK
    }
```

> **注意**：Room 实际只对 `chapters→books` 和 `searchBooks→book_sources` 声明了外键约束。`books.group` 与 `book_groups.groupId`、`rssArticles.origin` 与 `rssSources.sourceUrl` 为逻辑关联，无数据库级外键约束。

---

## 核心接口定义

### BaseBook 接口

所有书籍相关实体（Book、SearchBook）实现此接口：

| 字段 | 类型 | 说明 |
|------|------|------|
| `bookUrl` | String | 书籍唯一标识（URL 或本地文件路径） |
| `name` | String | 书名 |
| `author` | String | 作者 |
| `kind` | String? | 分类 |
| `wordCount` | String? | 字数（字符串形式，如"12.3 万字"） |
| `variable` | String? | 自定义变量 JSON（`HashMap<String,String>`） |
| `infoHtml` | String? | 书籍信息页 HTML（运行时，不持久化） |
| `tocHtml` | String? | 目录页 HTML（运行时，不持久化） |

### BaseSource 接口

所有"源"实体（BookSource、RssSource、HttpTTS）实现此接口：

| 字段 | 类型 | 说明 |
|------|------|------|
| `jsLib` | String? | JS 库代码 |
| `enabledCookieJar` | Boolean? | 启用 OkHttp CookieJar 自动保存 Cookie |
| `concurrentRate` | String? | 并发率控制（JSON 或数字） |
| `header` | String? | 自定义请求头 JSON |
| `loginUrl` | String? | 登录地址或登录 JS |
| `loginUi` | String? | 登录 UI 配置 JSON |

### BookListRule 接口

书籍列表规则接口，用于书源发现和搜索结果解析：

| 字段 | 类型 | 说明 |
|------|------|------|
| `bookList` | String? | 书籍列表规则 |
| `name` | String? | 书名规则 |
| `author` | String? | 作者规则 |
| `intro` | String? | 简介规则 |
| `kind` | String? | 分类规则 |
| `lastChapter` | String? | 最后章节规则 |
| `updateTime` | String? | 更新时间规则 |
| `bookUrl` | String? | 书籍 URL 规则 |
| `coverUrl` | String? | 封面 URL 规则 |
| `wordCount` | String? | 字数规则 |

---

## 常量与枚举

### BookType — 书籍类型位标志

书籍类型使用**二进制位标志**（Bit Flags），每本书可以同时拥有多个类型。

```kotlin
const val video      = 0b0000000100  // = 4   视频
const val text       = 0b0000001000  // = 8   文本
const val updateError= 0b0000010000  // = 16  更新失败
const val audio      = 0b0000100000  // = 32  音频
const val image      = 0b0001000000  // = 64  图片
const val webFile    = 0b0010000000  // = 128 仅下载（文件类）
const val local      = 0b0100000000  // = 256 本地书籍
const val archive    = 0b1000000000  // = 512 压缩包
const val notShelf   = 0b10000000000 // = 1024 未正式加入书架
```

**位运算查询**：

```sql
-- 查询所有文本类书籍
SELECT * FROM books WHERE (type & 8) > 0;

-- 查询所有音频或视频类书籍
SELECT * FROM books WHERE (type & (4 | 32)) > 0;
```

**组合常量**：

| 常量名 | 值 | 含义 |
|--------|-----|------|
| `allBookType` | `4 \| 8 \| 64 \| 32 \| 128` = 236 | 所有可从书源转换的类型 |
| `allBookTypeLocal` | `236 \| 256` = 492 | 所有类型（含本地） |

### BookGroup — 内置分组常量

`books.group` 字段使用 `Long` 类型，与 `book_groups.groupId` 匹配。系统内置分组：

| 常量名 | 值 | 说明 |
|--------|-----|------|
| `IdRoot` | `-100` | 根分组（代码内部使用） |
| `IdAll` | `-1` | 全部书籍 |
| `IdLocal` | `-2` | 本地书籍 |
| `IdAudio` | `-3` | 音频书籍 |
| `IdNetNone` | `-4` | 网络书籍-未分组 |
| `IdLocalNone` | `-5` | 本地书籍-未分组 |
| `IdVideo` | `-6` | 视频书籍 |
| `IdError` | `-11` | 更新失败 |

> **用户自定义分组**使用正数（从 `0b1` 开始，即 2 的幂次方）。

**分组位掩码查询算法**：

```sql
-- 查询属于某个分组的所有书籍（位与运算）
SELECT * FROM books WHERE (books.group & :groupId) > 0;

-- 查询属于多个分组的书籍
SELECT * FROM books WHERE (books.group & (:groupA | :groupB)) > 0;

-- 查询不属于任何分组的书籍（未分组）
SELECT * FROM books WHERE books.group = 0;
```

---

## 完整表清单

| 表名 | 实体类 | 主键 | 说明 |
|------|--------|------|------|
| books | Book | bookUrl | 书籍 |
| book_groups | BookGroup | groupId | 书籍分组 |
| book_sources | BookSource | bookSourceUrl | 书源 |
| chapters | BookChapter | (url, bookUrl) | 章节 |
| bookmarks | Bookmark | time | 书签 |
| replace_rules | ReplaceRule | id | 替换净化规则 |
| rssSources | RssSource | sourceUrl | RSS 源 |
| rssArticles | RssArticle | (origin, link, sort) | RSS 文章 |
| rssStars | RssStar | (origin, link) | RSS 收藏 |
| rssReadRecords | RssReadRecord | record | RSS 阅读记录 |
| httpTTS | HttpTTS | id | HTTP TTS 引擎 |
| searchBooks | SearchBook | bookUrl | 搜索结果缓存 |
| search_keywords | SearchKeyword | word | 搜索关键词历史 |
| readRecord | ReadRecord | (deviceId, bookName) | 阅读时间记录 |
| cookies | Cookie | url | Cookie 存储 |
| dictRules | DictRule | name | 字典规则 |
| txtTocRules | TxtTocRule | id | TXT 目录规则 |
| ruleSubs | RuleSub | id | 规则订阅 |
| caches | Cache | key | 缓存键值 |
| keyboardAssists | KeyboardAssist | (type, key) | 键盘辅助 |
| servers | Server | id | 远程服务器配置 |

---

## 索引设计总览

| 表名 | 索引名 | 类型 | 列 | 用途 |
|------|--------|------|----|------|
| `books` | `index_books_name_author` | UNIQUE | `name, author` | 防止重复添加同一本书 |
| `chapters` | `index_chapters_bookUrl` | 普通 | `bookUrl` | 按书籍查询章节 |
| `chapters` | `index_chapters_bookUrl_index` | UNIQUE | `bookUrl, index` | 确保章节序号不重复 |
| `book_sources` | `index_book_sources_bookSourceUrl` | 普通 | `bookSourceUrl` | 按 URL 查询书源 |
| `replace_rules` | `index_replace_rules_id` | 普通 | `id` | 规则排序 |
| `searchBooks` | `index_searchBooks_bookUrl` | UNIQUE | `bookUrl` | 搜索结果去重 |
| `searchBooks` | `index_searchBooks_origin` | 普通 | `origin` | 按书源查询搜索结果 |
| `search_keywords` | `index_search_keywords_word` | UNIQUE | `word` | 关键词唯一 |
| `cookies` | `index_cookies_url` | UNIQUE | `url` | Cookie 按域名唯一 |
| `rssSources` | `index_rssSources_sourceUrl` | 普通 | `sourceUrl` | 按 URL 查询 RSS 源 |
| `rssReadRecords` | `index_rssReadRecords_origin` | 普通 | `origin` | 按源查询阅读记录 |
| `bookmarks` | `index_bookmarks_bookName_bookAuthor` | 普通 | `bookName, bookAuthor` | 按书籍查询书签 |
| `caches` | `index_caches_key` | UNIQUE | `key` | 缓存键唯一 |

---

## 视图

### book_sources_part

书源的部分字段视图，用于书源列表的高效查询。

```sql
CREATE VIEW book_sources_part AS
SELECT
    bookSourceUrl,
    bookSourceName,
    bookSourceGroup,
    customOrder,
    enabled,
    enabledExplore,
    (loginUrl is not null and trim(loginUrl) <> '') hasLoginUrl,
    lastUpdateTime,
    respondTime,
    weight,
    (exploreUrl is not null and trim(exploreUrl) <> '') hasExploreUrl,
    eventListener,
    bookSourceType
FROM book_sources;
```

---

## DAO 列表

| DAO | 核心方法 |
|------|----------|
| BookDao | observeAll(Flow), getBook, insert(REPLACE), delete, update, search |
| BookChapterDao | getChapterList, insert, delete, getChapter |
| BookSourceDao | getByKey, insert(REPLACE), delete, update, search, observeAll(Flow) |
| BookGroupDao | getGroup, insert, delete, update, observeAll(Flow) |
| BookmarkDao | getBookmark, insert, delete, update, getByBook |
| ReplaceRuleDao | insert, delete, update, observeAll(Flow) |
| SearchBookDao | insert, delete, search, getByOrigin |
| RssSourceDao | getByKey, insert, delete, update, search |
| RssArticleDao | getArticle, insert, delete, update, getByOrigin |
| RssStarDao | getStar, insert, delete |
| RssReadRecordDao | get, insert, delete, getByOrigin |
| CookieDao | getByUrl, insert, delete |
| CacheDao | get, insert, delete |
| ReadRecordDao | get, insert, delete, getByBook |
| HttpTTSDao | get, insert, delete, update |
| DictRuleDao | get, insert, delete, update |
| TxtTocRuleDao | get, insert, delete, update |
| RuleSubDao | get, insert, delete, update |
| KeyboardAssistDao | get, insert, delete |
| ServerDao | get, insert, delete, update |
| SearchKeywordDao | get, insert, delete |

---

## 迁移策略

### Room 数据库迁移

Legado 使用 Room 的 `Migration` 机制进行数据库版本升级。每次数据库结构变更（增/删/改表或字段）时：

1. **递增版本号**：在 `AppDatabase.kt` 中更新 `version` 值
2. **编写 Migration**：每个版本迁移对应一个 `Migration(startVersion, endVersion)` 对象
3. **添加迁移到列表**：将新的 Migration 添加到 `databaseBuilder.addMigrations()` 的参数中

### AutoMigration (v43 起)

绝大多数迁移使用 AutoMigration，只需声明 from/to：

```kotlin
autoMigrations = [
    AutoMigration(from = 43, to = 44),
    AutoMigration(from = 44, to = 45),
    // ... 共 46 个
    AutoMigration(from = 88, to = 89)
]
```

### 手动 Migration Spec（共 5 个）

部分版本升级涉及复杂结构变更，AutoMigration 无法自动处理，需通过 `@AutoMigration` 的 `spec` 参数指定手动迁移规范：

| Spec 类 | 版本范围 | 说明 |
|---------|---------|------|
| `Migration_54_55` | 54→55 | 复杂结构变更 |
| `Migration_64_65` | 64→65 | 复杂结构变更 |
| `Migration_80_81` | 80→81 | 复杂结构变更 |
| `Migration_83_84` | 83→84 | 复杂结构变更 |
| `Migration_84_85` | 84→85 | 复杂结构变更 |

### Schema JSON 导出

每次构建时 Room 将当前数据库 Schema 导出到 `app/schemas/io.legado.app.data.AppDatabase/` 目录，文件名为 `{version}.json`。当前最新版本为 **89**。

Schema JSON 文件记录了每个版本的完整表结构，用于：
- 编写迁移脚本时参考旧版本结构
- 对比验证迁移后的数据库结构是否正确
- 自动生成迁移测试

### 常见迁移模式

```kotlin
// 例：新增字段（兼容旧数据）
val MIGRATION_XX_YY = object : Migration(xx, yy) {
    override fun migrate(database: SupportSQLiteDatabase) {
        database.execSQL("ALTER TABLE books ADD COLUMN new_column INTEGER NOT NULL DEFAULT 0")
    }
}

// 例：新增表
val MIGRATION_XX_YY = object : Migration(xx, yy) {
    override fun migrate(database: SupportSQLiteDatabase) {
        database.execSQL("""
            CREATE TABLE IF NOT EXISTS new_table (
                id INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL
            )
        """.trimIndent())
    }
}
```

> **注意**：SQLite 的 `ALTER TABLE` 仅支持 `ADD COLUMN` 和 `RENAME TO`。复杂变更（如修改列类型）需要新建表 + 数据迁移 + 删除旧表的三步操作。

### 破坏性变更流程

对于需要修改列类型或删除列的"破坏性变更"，Room 的推荐流程：

1. 创建临时表（新结构）
2. `INSERT INTO temp_table SELECT ... FROM old_table` 迁移数据（含默认值处理）
3. `DROP TABLE old_table`
4. `ALTER TABLE temp_table RENAME TO old_table`

---

## 相关代码锚点

| 功能 | 文件 |
|------|------|
| AppDatabase 定义 | [AppDatabase.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt) |
| AutoMigration 列表 | [AppDatabase.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt) |
| BookType 位标志 | [BookType.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BookType.kt) |
| BookGroup 常量 | [BookGroup.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BookGroup.kt) |
| Schema v108 | [108.json](file:///f:/myself/github/WeAgentChat/temp/legado/app/schemas/io.legado.app.data.AppDatabase/108.json) |

---

## Python 重构参考

> 数据库层 Python 重构技术选型建议

### SQLAlchemy ORM 映射

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Book(Base):
    __tablename__ = 'books'
    name = Column(String, default='')
    author = Column(String, default='')
    bookUrl = Column(String, primary_key=True)
    origin = Column(String, default='')
    type = Column(Integer, default=0)
    # ... 其他字段参考 tables.md
```

### 迁移策略（Alembic）

```python
# alembic/env.py
from alembic import context
from sqlalchemy import engine_from_config

# 使用 Room Schema JSON 作为迁移基准
# AutoMigration 对应 Alembic autogenerate
```

### 位运算查询

```python
# BookType 位标志查询
from sqlalchemy import and_

# 查询所有文本类型书籍
text_books = session.query(Book).filter(Book.type.op('&')(8) != 0).all()

# 查询本地音频书
local_audio = session.query(Book).filter(
    and_(Book.type.op('&')(256) != 0, Book.type.op('&')(32) != 0)
).all()
```
