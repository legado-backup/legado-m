# 快速参考卡

## 构建 & 运行

| 操作 | 命令 |
|------|------|
| 构建 Debug | `./gradlew assembleDebug` |
| 构建 Release | `./gradlew assembleRelease` |
| 运行测试 | `./gradlew test` |
| Lint 检查 | `./gradlew lint` |
| 清理构建 | `./gradlew clean` |
| Vue3 开发 | `npm run dev`（legado-web 目录下） |
| Vue3 构建 | `npm run build`（legado-web 目录下，含 type-check + sync.js） |
| Vue3 类型检查 | `npm run type-check`（legado-web 目录下） |

## 关键文件速查

| 用途 | 文件路径 |
|------|----------|
| 应用入口 | `app/src/main/java/io/legado/app/App.kt` |
| 主界面 | `app/src/main/java/io/legado/app/ui/main/MainActivity.kt` |
| 规则引擎 | `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` |
| 网络书核心 | `app/src/main/java/io/legado/app/model/webBook/WebBook.kt` |
| 阅读核心 | `app/src/main/java/io/legado/app/model/ReadBook.kt` |
| Web 服务 | `app/src/main/java/io/legado/app/web/controller/` |
| 书源实体 | `app/src/main/java/io/legado/app/data/entities/BookSource.kt` |
| 数据库定义 | `app/src/main/java/io/legado/app/data/AppDatabase.kt` |
| ProGuard | `app/proguard-rules.pro` |
| 依赖版本 | `gradle/libs.versions.toml` |

## 版本锁定依赖

| 依赖 | 版本 | 原因 |
|------|------|------|
| jsoup | 1.16.2 | 新版有破坏性变更（jsoup#2017） |
| rhino | 1.8.1 | API 33 以下不可用的 VarHandle（desugaring 不覆盖） |
| hutool | 5.8.22 | 书源加解密依赖，不可升级 |
| commons-text | 1.13.1 | API 24 以下不可用的 Arrays.setAll（desugaring 不覆盖） |
| protobuf | 4.26.1 | 兼容性锁定 |

## 数据库

| 项目 | 值 |
|------|------|
| 名称 | legado.db |
| 版本 | 89 |
| ORM | Room |
| 实体数 | 21 |
| DAO 数 | 21 |
| Schema | app/schemas/ |

## Web API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /getBookshelf | 获取书架 |
| GET | /getBookSources | 获取全部书源 |
| GET | /getChapterList | 获取章节列表 |
| GET | /getBookContent | 获取正文内容 |
| POST | /saveBookSource | 保存书源 |
| POST | /saveBookSources | 批量保存书源 |
| POST | /deleteBookSources | 删除书源 |
| POST | /saveBook | 保存书籍 |
| POST | /saveRssSource | 保存 RSS 源 |
