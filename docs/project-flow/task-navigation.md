# 开发任务导航（按任务类型索引）

> **使用方法**：接手任务时，先定位任务类型，再读取对应 Wiki 文档和代码锚点。
> **来源**：从 AGENTS.md 外移，主规范仅保留链接。

---

## 新增/修改书源规则

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 理解规则引擎架构 | [architecture/rule-engine.md](./architecture/rule-engine.md) | - |
| 规则前缀解析逻辑 | `model/analyzeRule/AnalyzeRule.kt` | L601-631 |
| 规则分割(&&/\|\|/%%) | `model/analyzeRule/RuleAnalyzer.kt` | L165-237 |
| CSS选择器解析 | `model/analyzeRule/AnalyzeByJSoup.kt` | L72-123 |
| JSONPath解析 | `model/analyzeRule/AnalyzeByJSonPath.kt` | L31-71 |
| XPath解析 | `model/analyzeRule/AnalyzeByXPath.kt` | L52-133 |
| JS执行(Rhino) | `modules/rhino/.../RhinoScriptEngine.kt` | L88-125 |
| 书源实体/规则字段 | `data/entities/BookSource.kt` | L32-98 |
| 搜索规则定义 | `data/entities/rule/SearchRule.kt` | L12-25 |
| 正文规则定义 | `data/entities/rule/ContentRule.kt` | L12-24 |

## 新增/修改搜索功能

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 搜索并发调度 | `model/webBook/SearchModel.kt` | L52-114 |
| 搜索结果聚合去重 | `model/webBook/SearchModel.kt` | L116-197 |
| 单书源搜索 | `model/webBook/WebBook.kt` | L49-107 |
| 搜索结果解析 | `model/webBook/BookList.kt` | L35-151 |
| 搜索界面 | `ui/book/search/SearchActivity.kt` | L66-70 |

## 新增/修改阅读功能

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 阅读核心(文字) | `model/ReadBook.kt` | L61, L534-596 |
| 翻页/跳章 | `model/ReadBook.kt` | L304-419 |
| 内容加载完成 | `model/ReadBook.kt` | L693-783 |
| 阅读界面 | `ui/book/read/ReadBookActivity.kt` | L151-166 |
| 漫画阅读 | `model/ReadManga.kt` | L45, L154-240 |
| 音频播放 | `model/AudioPlay.kt` | L38, L171-222 |

## 新增/修改 Web API

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 路由定义 | `web/HttpServer.kt` | L25-146 |
| 书籍控制器 | `api/controller/BookController.kt` | L36 |
| 书源控制器 | `api/controller/BookSourceController.kt` | L13 |
| Vue3前端 | `modules/web/src/` | - |

## 新增/修改数据库

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 数据库定义(版本89) | `data/AppDatabase.kt` | L69-149 |
| AutoMigration列表 | `data/AppDatabase.kt` | L78-125 |
| Book实体 | `data/entities/Book.kt` | L34-38 |
| BookChapter实体 | `data/entities/BookChapter.kt` | L30-42 |
| BookDao | `data/dao/BookDao.kt` | L18-19 |
| BookSourceDao | `data/dao/BookSourceDao.kt` | L20-21 |

## 新增/修改本地书籍解析

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 本地书入口(类型分发) | `model/localBook/LocalBook.kt` | L69, L120-213 |
| TXT解析(编码+目录规则) | `model/localBook/TextFile.kt` | L26, L89-154 |
| EPUB解析 | `model/localBook/EpubFile.kt` | L35, L125-359 |

## 新增/修改 UI 界面

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| UI 层架构总览 | [architecture/android-ui.md](./architecture/android-ui.md) | - |
| 主界面/MainActivity | `ui/main/MainActivity.kt` | L70-503 |
| 阅读界面 | `ui/book/read/ReadBookActivity.kt` | L151-166 |
| 搜索界面 | `ui/book/search/SearchActivity.kt` | L66-70 |
| 书源编辑界面 | `ui/book/source/edit/BookSourceEditActivity.kt` | - |
| 自定义 Widget 体系 | `ui/widget/` 目录 | - |

## 新增/修改网络请求

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 网络层架构 | [architecture/network-layer.md](./architecture/network-layer.md) | - |
| OkHttp 构建+拦截器 | `help/http/HttpHelper.kt` | L51-127 |
| SSL 证书处理 | `help/http/SSLHelper.kt` | L20-194 |
| Cookie 管理 | `help/http/CookieManager.kt` | - |
| Cronet 加速 | `help/http/Cronet.kt` | - |
| WebView 后台请求 | `help/http/BackstageWebView.kt` | - |

## 新增/修改配置项

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 配置系统架构 | [modules/config-system.md](./modules/config-system.md) | - |
| 全局配置 | `help/config/AppConfig.kt` | L29-825 |
| 阅读排版配置 | `help/config/ReadBookConfig.kt` | L40-100 |
| 主题配置 | `help/config/ThemeConfig.kt` | L48-79 |
| 书源评分 | `help/config/SourceConfig.kt` | L7-45 |
| 本地状态 | `help/config/LocalConfig.kt` | - |

## 新增/修改后台 Service

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| Service 层架构 | [modules/android-services.md](./modules/android-services.md) | - |
| 朗读服务基类 | `service/BaseReadAloudService.kt` | L72-783 |
| TTS 朗读 | `service/TTSReadAloudService.kt` | - |
| HTTP 朗读 | `service/HttpReadAloudService.kt` | - |
| 音频播放 | `service/AudioPlayService.kt` | - |
| 书籍缓存 | `service/CacheBookService.kt` | - |
| 书籍导出 | `service/ExportBookService.kt` | - |
| 书源检验 | `service/CheckSourceService.kt` | - |

## 新增/修改备份恢复

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 备份恢复系统 | [modules/backup-restore.md](./modules/backup-restore.md) | - |
| 备份核心 | `help/storage/Backup.kt` | L54-315 |
| 恢复核心 | `help/storage/Restore.kt` | L65-80 |
| AES 加密 | `help/storage/BackupAES.kt` | - |
| WebDAV 同步 | `help/AppWebDav.kt` | - |

## 新增/修改工具类/协程/加密

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 工具与辅助层总览 | [modules/tools-infrastructure.md](./modules/tools-infrastructure.md) | - |
| 编码检测 | `utils/EncodingDetect.kt` | L18-50 |
| 简繁转换 | `utils/ChineseUtils.kt` | L6-49 |
| Canvas录制(翻页) | `utils/canvasrecorder/CanvasRecorder.kt` | L5-27 |
| 对象池 | `utils/objectpool/ObjectPool.kt` | L3-11 |
| 压缩工具 | `utils/compress/ZipUtils.kt` | L26-40 |
| 链式协程 | `help/coroutine/Coroutine.kt` | L26-252 |
| 对称加密 | `help/crypto/SymmetricCryptoAndroid.kt` | L13-40 |
| 媒体按键接收器 | `receiver/MediaButtonReceiver.kt` | L27-121 |
| 网络变化监听 | `receiver/NetworkChangedListener.kt` | L17-77 |

## 新增/修改自定义库（MOBI/WebDAV/主题）

| 步骤 | 读取文件 | 行号 |
|------|----------|------|
| 自定义库层总览 | [modules/custom-libraries.md](./modules/custom-libraries.md) | - |
| MOBI解析入口 | `lib/mobi/MobiReader.kt` | L16-50 |
| MOBI基类(解压+索引) | `lib/mobi/MobiBook.kt` | L33-99 |
| KF8章节处理 | `lib/mobi/KF8Book.kt` | L21-272 |
| KF6章节处理 | `lib/mobi/KF6Book.kt` | L1-140 |
| PDB文件容器 | `lib/mobi/PDBFile.kt` | L1-48 |
| WebDAV客户端 | `lib/webdav/WebDav.kt` | L41-456 |
| 主题存储 | `lib/theme/ThemeStore.kt` | L20-352 |
| 视图着色引擎 | `lib/theme/TintHelper.kt` | L36-487 |

## 修复 Bug

1. 定位 Bug 所属模块 → 参考上方任务导航表
2. 读取对应 Wiki 文档了解设计思想
3. 查看代码锚点定位核心逻辑
4. 修改后运行 `./gradlew test` 验证
