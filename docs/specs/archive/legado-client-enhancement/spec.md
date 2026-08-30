# Legado Client Enhancement - 规格说明书

## Intent

将现有 `legado_client` Python 客户端从「仅 AI 调试工具」升级为「AI + 用户双模式管理平台」，实现四大核心能力：

1. **自动源获取**：从 yckceo.com 社区、GitHub 仓库、URL 链接、本地文件等多渠道自动获取全量书源/订阅源，解析并入库
2. **MySQL 持久化**：所有源数据、调试结果、经验教训统一存储到本地 MySQL，AI 调试时先查库复用
3. **测试-优化闭环**：AI/用户测试源后，失败时自动修复→重测→优化，形成"查库→测试→修复→更新"完整闭环
4. **Web 管理界面**：提供前端页面让用户查看、管理、测试、优化、导入导出书源/订阅源，并支持推送到 Legado 真机

### 核心价值

- **AI 效率提升**：同域名源直接从数据库取出测试优化，避免重复分析网站
- **用户自助管理**：用户无需手动下载 JSON 文件、无需命令行操作，浏览器即可完成全流程
- **数据资产积累**：所有源数据和测试结果持久化，形成可检索的知识库
- **端到端闭环**：从获取源→测试→优化→推送到手机，全链路打通

## Scope

### In Scope

| 模块 | 功能 |
|------|------|
| **源获取器 (Fetcher)** | 多渠道获取源：yckceo.com 社区 + GitHub 仓库 + URL 导入 + 本地文件导入 + Legado 真机同步 |
| **存储层 (Storage)** | MySQL 数据库连接管理 + ORM 模型（完整字段映射）+ CRUD Repository + 数据迁移 |
| **AI 数据库查询+优化闭环** | AI 调试时先查库→命中则测试→失败则自动修复→重测→更新数据库；未命中则从头分析后入库 |
| **Legado Web 服务集成** | 真机 Web 服务调试（WS /bookSourceDebug /rssSourceDebug）优先于 JAR 仿真；真机通过后 JAR 验证；真机通过但 JAR 失败时触发 JAR 优化闭环 |
| **JAR 优化闭环** | 真机通过但 JAR 失败时，自动分析 Legado 源码→定位 JAR 缺失功能→修改 JAR 代码→重新构建→回归测试 |
| **Web API 服务** | FastAPI RESTful API + WebSocket 调试流推送 + 数据库降级策略 + Legado Web 服务代理 |
| **Web 前端页面** | Vue3 SPA：源列表/详情/编辑/测试/优化/合集管理/统计面板/真机推送 |
| **CLI 扩展** | 新增 `fetch`/`serve`/`db`/`import`/`export` 子命令 |
| **真机对接** | 导出 Legado 可导入格式 + 对接 Legado Web API 推送源到手机 |
| **数据迁移** | 首次启动自动扫描 output/ 目录已有源导入数据库 |

### Out of Scope

- 多用户认证/权限系统（单用户本地使用场景）
- 远程部署/云服务（仅本地 127.0.0.1）
- JVM 仿真器改造（保持现有 stdin/stdout 协议不变）
- 移动端适配（桌面浏览器优先）
- 源规则可视化编辑器（后续迭代，本期仅支持 JSON 文本编辑）

## Approach

### 核心架构：三层扩展

```
┌──────────────────────────────────────────────────────┐
│              Web Frontend (Vue3 + Element Plus)       │
│  源列表 / 详情 / 编辑 / 测试 / 优化 / 合集 / 统计    │
├──────────────────────────────────────────────────────┤
│              Web API Layer (FastAPI)                   │
│  RESTful + WebSocket(调试流) + 数据库降级             │
├──────────────────────────────────────────────────────┤
│              Core Services                             │
│  Fetcher ──→ Storage(MySQL) ──→ Debugger(JVM) ──→ 真机│
│  (多渠道获取)  (持久化+降级)    (测试+修复闭环)  (推送)│
└──────────────────────────────────────────────────────┘
```

### 数据流设计

**源获取流（多渠道）**：
```
渠道1: yckceo.com 列表页(HTML) → 解析合集元数据 → 下载JSON → 解析入库
渠道2: GitHub 仓库 URL → 下载 JSON → 解析入库
渠道3: 用户输入 URL → 下载 JSON → 解析入库
渠道4: 本地文件上传/目录扫描 → 解析入库
渠道5: Legado 真机 Web API /getBookSources → 拉取源 → 入库
```

**AI 调试+优化闭环流**：
```
AI 收到调试请求 → 提取域名 → 查数据库 source 表
    ├─ 命中+测试通过：直接返回结果，无需重测
    ├─ 命中+测试失败/未测试：取出源JSON → 测试（真机优先→JAR回退）→ 失败则触发 auto_fixer → 修复后重测
    │   ├─ 修复成功 → 更新数据库源JSON+测试结果
    │   └─ 修复失败 → 标记需AI介入 → 返回修复建议给AI
    └─ 未命中：从头分析网站 → 构建规则 → 测试（真机优先→JAR回退）→ 源+测试结果入库

测试链路（DebugOrchestrator mode=auto）：
    真机已配置且可通 → Legado Web 服务 WS /bookSourceDebug 或 /rssSourceDebug
    真机不可用 → 回退到 JAR 仿真
    真机通过后 → 必须用 JAR 验证，对比差异
    真机通过但 JAR 失败 → 触发 JAR 优化闭环（JarOptimizer）
```

**用户管理+真机推送流**：
```
浏览器 → FastAPI → 源列表/详情/测试/管理操作
    ├─ 列表：分页+筛选+搜索+排序
    ├─ 详情：源JSON查看+编辑+测试历史
    ├─ 测试：触发JVM调试 → WebSocket推送进度 → 结果入库
    ├─ 优化：测试失败 → 触发auto_fixer → 修复后重测
    ├─ 导入导出：JSON文件上传/下载
    └─ 推送真机：选择源 → 生成Legado格式 → 调用真机Web API推送
```

### Alternatives Considered

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| **A. SQLite 替代 MySQL** | 零依赖 | 并发弱，用户要求 MySQL | ❌ |
| **B. 纯 CLI 无 Web** | 开发量小 | 用户体验差 | ❌ |
| **C. Flask 替代 FastAPI** | 更简单 | 无原生 async，WebSocket 弱 | ❌ |
| **D. 前后端不分离（Jinja2）** | 开发快 | 交互差，无法实时推送 | ❌ |
| **E. 同域名严格去重（只保留1条）** | 数据精简 | 丢失不同规则的有效源 | ❌ |
| **F. 同域名宽松去重（domain+name组合）** | 保留多样性 | 数据量略大 | ✅ 采用 |
| **G. 增量更新** | 效率高 | 首次仍需全量 | ✅ 采用 |

### Drawbacks

1. **MySQL 依赖**：用户需本地安装 MySQL
   - 缓解：提供 Docker Compose 一键启动 + 数据库不可用时自动降级到文件模式
2. **Node.js 依赖**：Vue3 前端构建需 Node.js
   - 缓解：提供预构建 dist/ 目录
3. **首次全量下载耗时长**：700+ 书源合集约 15-30 分钟
   - 缓解：后台异步执行，进度可查
4. **JVM 单实例瓶颈**：多用户并发调试时串行限制
   - 缓解：任务队列 + WebSocket 通知 + asyncio.to_thread 包装
5. **密码安全**：MySQL 密码不应硬编码
   - 缓解：默认空值，通过环境变量或 .env 文件提供
6. **Legado Web 服务依赖**：真机调试模式依赖 Legado App 开启 Web 服务，设备需在同一局域网且 Web 服务可用
   - 缓解：真机不可用时自动回退到 JAR 仿真；提供连接测试 API 提前发现不可用情况
7. **JAR 优化复杂度**：真机通过但 JAR 失败时，JAR 优化闭环需分析 Legado 源码并修改 Java 代码，可能涉及 Rhino 扩展函数、jsoup 选择器差异等深层问题
   - 缓解：优化记录持久化避免重复分析；JAR 优化为 P1 优先级，首期可手动触发

## Requirements

### 功能需求

#### FR-01: 源获取器（多渠道）

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-01-01 | 爬取 yckceo.com 书源合集列表（分页，~8页×80条） | P0 |
| FR-01-02 | 爬取 yckceo.com 订阅源合集列表（1页×87条） | P0 |
| FR-01-03 | 下载指定合集的 BookSource[] JSON（`/json/id/{id}.json`） | P0 |
| FR-01-04 | 下载指定订阅源合集的 RssSource[] JSON | P0 |
| FR-01-05 | 合集元数据入库（标题/用户/源数量/下载量/日期/ID） | P0 |
| FR-01-06 | 源数据解析+去重入库（按 domain_key+source_name 组合去重） | P0 |
| FR-01-07 | 增量更新：仅下载新增/更新的合集 | P1 |
| FR-01-08 | 请求频率控制（间隔 ≥ 1秒）+ User-Agent 设置 + HTML 解析容错（多套 CSS 选择器降级） | P0 |
| FR-01-09 | GitHub 仓库源获取：输入仓库 URL → 下载 JSON → 解析入库 | P1 |
| FR-01-10 | URL 直接导入：输入 JSON URL → 下载 → 解析入库 | P0 |
| FR-01-11 | 本地文件导入：上传/扫描 JSON 文件 → 解析入库 | P0 |
| FR-01-12 | Legado 真机同步：通过 Web API `/getBookSources` `/getRssSources` 拉取 | P1 |
| FR-01-13 | CLI `fetch` 命令：`legado-client fetch --type book --all` | P0 |
| FR-01-14 | CLI `import` 命令：`legado-client import --file source.json` | P0 |
| FR-01-15 | CLI `export` 命令：`legado-client export --type book --output sources.json [--ids 1,2,3]` | P0 |
| FR-01-16 | source_parser 字段映射：BookSource JSON → Source ORM（bookSourceName→source_name, bookSourceUrl→source_url, bookSourceType→book_source_type, bookSourceGroup→source_group 等）+ RssSource JSON → Source ORM（sourceName→source_name, sourceUrl→source_url, sourceType→rss_type 等）+ 计算字段（domain_key, has_login） | P0 |

#### FR-02: MySQL 存储层

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-02-01 | MySQL 连接管理（连接池+自动重连+配置化） | P0 |
| FR-02-02 | BookSource 完整字段映射表模型（含 bookSourceType/enabledExplore/loginUrl/searchUrl/exploreUrl/lastUpdateTime/respondTime/weight 等） | P0 |
| FR-02-03 | RssSource 完整字段映射表模型（含 type/singleUrl/sortUrl/articleStyle/ruleArticles/ruleContent 等） | P0 |
| FR-02-04 | Collection 表模型（合集元数据） | P0 |
| FR-02-05 | DebugResult 表模型（调试结果+阶段通过情况+可信度+修复记录） | P0 |
| FR-02-06 | 按域名查询源：`SELECT * FROM source WHERE domain_key = ?` | P0 |
| FR-02-07 | 源 CRUD 操作（增删改查+批量导入导出） | P0 |
| FR-02-08 | 数据库迁移管理（Alembic） | P1 |
| FR-02-09 | CLI `db` 命令：`legado-client db init/migrate/reset/import-dir/stats` | P0 |
| FR-02-10 | 数据库不可用时自动降级到文件模式 | P0 |
| FR-02-11 | 首次启动自动扫描 output/ 目录导入已有源 | P0 |
| FR-02-12 | 数据库备份/恢复：`legado-client db backup/restore` | P2 |
| FR-02-13 | 数据库索引：Source 表 10 个索引（domain_key/type/test_result/group/enabled/name/book_source_type/rss_type/domain_name/updated_at）+ Collection 表 2 个索引 + DebugResult 表 2 个索引 | P0 |
| FR-02-14 | Source 分组字段：source_group 列存储 Legado 原生逗号分隔格式（如 "小说,精品"），支持 LIKE 查询和 FIND_IN_SET | P0 |
| FR-02-15 | Source.notes 字段：AI 闭环修复经验摘要写入 notes 列，供后续调试参考 | P0 |
| FR-02-16 | Source 内容类型：BookSource 用 book_source_type 列（0文本/1音频/2图片/3文件），RssSource 用 rss_type 列（0网页/1图片/2视频），前端按 source_type + 对应类型列组合筛选 | P0 |
| FR-02-17 | DebugResult.created_at 字段：记录创建时间，支持按时间排序查询调试历史 | P0 |

#### FR-03: AI 数据库查询+优化闭环

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-03-01 | debug_runner 调试前自动查数据库同域名源 | P0 |
| FR-03-02 | 命中+测试已通过：直接返回结果，跳过测试 | P0 |
| FR-03-03 | 命中+测试失败/未测试：取出源JSON → JVM测试 → 失败则触发 auto_fixer → 修复后重测 → 更新数据库 | P0 |
| FR-03-04 | 命中+修复失败：标记需AI介入，返回修复建议 | P0 |
| FR-03-05 | 未命中：从头分析网站 → 构建规则 → JVM测试 → 源+结果入库 | P0 |
| FR-03-06 | 测试结果更新到数据库（覆盖旧结果） | P0 |
| FR-03-07 | 修复记录关联到源（修复了什么、修复前后的diff） | P1 |
| FR-03-08 | 经验数据关联到源记录 | P1 |
| FR-03-09 | `--skip-db-lookup` 参数禁用数据库查询（离线模式） | P0 |
| FR-03-10 | `--db-only` 模式：仅查数据库，不触发 JVM 测试 | P1 |
| FR-03-11 | debug_runner 重构：新增 `run_and_return()` 返回值模式（不调用 sys.exit），供 AI 闭环和 Web API 使用 | P0 |
| FR-03-12 | DebugOrchestrator 编排器：组合 debug_runner + storage + auto_fixer，实现"查库→测试→修复→更新"完整闭环 | P0 |
| FR-03-13 | 测试链路优先级：真机已配置且可通时优先使用 Legado Web 服务调试（WS /bookSourceDebug 或 /rssSourceDebug），真机不可用时回退到 JAR 仿真 | P0 |
| FR-03-14 | 真机测试通过后必须用 JAR 仿真验证，对比真机与 JAR 结果差异 | P0 |
| FR-03-15 | 真机通过但 JAR 失败时，触发 JAR 优化闭环：分析 Legado 源码→定位 JAR 缺失功能→修改 JAR Java 代码→重新构建→回归测试 | P1 |
| FR-03-16 | LegadoWebClient 封装：26 个 HTTP API + 3 个 WebSocket API，支持连接测试/源推送/源拉取/源调试/书籍搜索。注意：WebSocket 端口 = HTTP 端口 + 1（源码 WebService.kt 硬编码，默认 HTTP:1122, WS:1123）；调试 WS 返回纯文本日志（非 JSON），通过关闭帧结束；HTTP 响应需解析 ReturnData 格式提取 data 字段；当前 Legado 版本无 HTTP 认证，auth_token 为预留字段 | P0 |
| FR-03-17 | DebugOrchestrator 支持 mode 参数：auto（真机优先→JAR回退）/ device（仅真机）/ jar（仅JAR仿真） | P0 |

#### FR-04: Web API 服务

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-04-01 | FastAPI 应用启动+配置 | P0 |
| FR-04-02 | 源列表 API（分页+筛选+搜索+按类型/分组/测试结果/内容类型筛选） | P0 |
| FR-04-03 | 源详情 API（完整 JSON 查看） | P0 |
| FR-04-04 | 源编辑 API（JSON 文本编辑+更新） | P0 |
| FR-04-05 | 源测试 API（触发 JVM 调试） | P0 |
| FR-04-06 | 源优化 API（测试失败→触发 auto_fixer→修复后重测） | P0 |
| FR-04-07 | 调试进度 WebSocket 推送（标准协议：log/error/result/progress/complete 五种消息类型，UUID4 task_id，断线重连+消息缓存） | P0 |
| FR-04-08 | 合集管理 API（列表/下载/状态） | P0 |
| FR-04-09 | 源导入/导出 API（多渠道） | P0 |
| FR-04-10 | 真机推送 API（选择源→调用 Legado Web API 推送到手机） | P0 |
| FR-04-11 | 统计面板 API（源数量/通过率/分布） | P1 |
| FR-04-12 | 数据库降级：MySQL 不可用时 API 返回降级提示 | P0 |
| FR-04-13 | CLI `serve` 命令：`legado-client serve --host 127.0.0.1 --port 8080` | P0 |
| FR-04-14 | CORS 配置：允许 Vite 开发模式（:5173）跨域访问 API | P0 |
| FR-04-15 | 统一错误响应格式：`{ok: false, error: {code: string, message: string}}`，错误码含 DB_UNAVAILABLE/SOURCE_NOT_FOUND/JVM_BUSY/INVALID_JSON/DEVICE_UNREACHABLE/IMPORT_FAILED | P0 |
| FR-04-16 | 源验证 API：`POST /api/sources/validate` — 前端编辑器实时验证 JSON 格式 | P1 |
| FR-04-17 | API 端点规范：6 个路由模块共 30+ 个端点，详见 design.md API 端点规范章节 | P0 |
| FR-04-18 | 请求日志中间件：记录 API 请求方法/路径/状态码/耗时（跳过 /ws 和 /assets） | P0 |
| FR-04-19 | 服务端日志配置：RotatingFileHandler（10MB×5）+ 环境变量 LEGADO_LOG_LEVEL 控制日志级别 | P0 |
| FR-04-20 | 文件上传大小限制：单文件 ≤ 10MB | P0 |
| FR-04-21 | Legado Web 服务代理 API：HTTP 反向代理 + WebSocket 双向代理，前端可直接操作真机 | P0 |
| FR-04-22 | 调试对比 API：`POST /api/debug/compare` — 同时在真机和 JAR 上测试同一源，返回对比结果 | P1 |
| FR-04-23 | JAR 优化 API：`POST /api/debug/jar-optimize` — 触发 JAR 优化闭环 | P1 |
| FR-04-24 | 测试模式统计 API：`GET /api/stats/test-mode` — 真机 vs JAR 测试结果对比统计 | P2 |

#### FR-05: Web 前端页面

**全局**：7 个一级菜单 + 8 个路由，侧边栏+顶栏+底栏布局，暗色模式切换

| ID | 需求 | 优先级 | 对应页面 |
|----|------|--------|---------|
| FR-05-01 | 源列表页：10 列表格（名称/URL/类型/内容类型/分组/测试结果/最后测试/启用/操作）+ 6 个筛选器（搜索/类型/内容类型/测试结果/分组/有无登录）+ 4 列可排序 + 5 种批量操作（测试/导出/删除/推送/启用禁用） | P0 | `/sources` |
| FR-05-02 | 源详情页：基本信息卡片 + 测试结果步骤条 + 3 个 Tab（JSON编辑/测试历史/同域名源）+ 5 个操作按钮（测试/优化/导出/推送/删除） | P0 | `/sources/:id` |
| FR-05-03 | JSON 编辑器：CodeMirror 6 语法高亮 + 编辑 + 格式化 + 保存 + 重置 | P0 | 源详情页 Tab |
| FR-05-04 | 合集管理页：7 列表格 + 3 个全局操作（获取远程/全量获取/增量更新）+ 下载进度条 | P0 | `/collections` |
| FR-05-05 | 测试面板页：3 个 Tab（单源测试/批量测试/优化测试）+ 实时日志 WebSocket + 进度条 + 取消 + 测试历史 | P0 | `/debug` |
| FR-05-06 | 优化测试：选择失败源 → 自动修复 → 重测 → 修复 diff 展示 | P0 | 测试面板 Tab |
| FR-05-07 | 源导入页：4 种导入方式（URL/文件上传/GitHub/真机拉取）+ 导入结果统计（新增/跳过/失败） | P0 | `/import` |
| FR-05-08 | 源导出：选择源 → 下载 JSON 文件 / 推送到真机 | P0 | 列表页批量+详情页 |
| FR-05-09 | 统计面板页：4 个概览卡片 + 测试结果饼图 + 内容类型柱状图 + 分组分布图 | P1 | `/stats` |
| FR-05-10 | 源启用/禁用：列表页 Switch 开关切换 | P0 | 源列表页 |
| FR-05-11 | 源分组管理：添加/移除分组标签 | P1 | 源详情页 |
| FR-05-12 | 同域名源对比：查看同域名多个源的差异，一键切换 | P2 | 源详情页 Tab |
| FR-05-13 | 源复制 JSON 到剪贴板 | P0 | 源列表页操作列 |
| FR-05-14 | 真机管理页：设备卡片列表 + 添加/编辑设备弹窗（名称/IP/端口/认证Token）+ 测试连接 + 推送/拉取源 | P0 | `/devices` |
| FR-05-15 | 全局状态栏：源总数 + 通过率 + JVM 状态 | P1 | 底栏 |
| FR-05-16 | 数据库状态指示：顶栏显示数据库连接状态 | P0 | 顶栏 |
| FR-05-17 | 7 个全局复用组件：SourceSelect/DeviceSelect/JsonEditor/DebugLogPanel/ProgressDialog/ConfirmDialog/ResultSummary | P0 | 跨页面 |
| FR-05-18 | 复用 Legado Vue3 前端：通过反向代理集成 Legado 原生前端（MPA 结构：导航首页+Vue3 SPA Hash 路由+传书页面），路径 `/legado/*`，Vue3 SPA 路由为 `/legado/vue/#/bookSource` 等 | P0 | `/legado/*` |
| FR-05-19 | 管理面板路由调整：源列表等管理页面路由从 `/sources` 改为 `/admin/sources`，与 Legado 原生前端区分 | P0 | `/admin/sources` |
| FR-05-20 | 源详情页新增"真机 vs JAR 对比"Tab：展示真机和 JAR 仿真测试结果的差异 | P1 | 源详情页 Tab |
| FR-05-21 | 测试面板新增"真机 vs JAR 对比"Tab：同时触发真机和 JAR 调试，实时展示对比日志 | P1 | 测试面板 Tab |
| FR-05-22 | 真机管理页设备配置：HTTP 端口（默认 1122），WebSocket 端口 = HTTP 端口 + 1（源码硬编码，无需独立 WS 端口字段），auth_token 为预留字段（当前 Legado 版本无 HTTP 认证） | P0 | `/devices` |

#### FR-06: JAR 优化闭环

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-06-01 | JarOptimizer 模块：真机通过但 JAR 失败时，自动分析 Legado 源码定位 JAR 缺失功能 | P1 |
| FR-06-02 | JAR 优化记录：DebugResult 表新增 test_mode/device_jar_diff/jar_optimization_count/last_jar_diff 字段 | P1 |
| FR-06-03 | JAR 优化闭环流程：差异记录→源码分析→JAR代码修改→重新构建→回归测试→更新优化记录 | P1 |

#### FR-07: 真机对接

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-07-01 | 导出 Legado 可导入格式（BookSource[]/RssSource[] JSON 文件） | P0 |
| FR-07-02 | 对接 Legado 真机 Web API 推送源（`/saveBookSources`、`/saveRssSource`） | P0 |
| FR-07-03 | 从 Legado 真机拉取源（`/getBookSources`、`/getRssSources`） | P1 |
| FR-07-04 | 真机连接配置（IP+端口+认证token） | P0 |
| FR-07-05 | 真机认证支持：无认证模式 + auth_token 模式（Legado Web 验证码） | P0 |
| FR-07-06 | 真机连接测试：验证设备可达性和认证状态 | P0 |

### 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NFR-01 | 首次全量下载耗时 | ≤ 30 分钟（700+ 合集） |
| NFR-02 | API 响应时间 | 列表查询 ≤ 200ms（1万条源） |
| NFR-03 | 前端首屏加载 | ≤ 2 秒 |
| NFR-04 | 并发调试支持 | 至少 1 个 JVM 实例 + 任务队列 |
| NFR-05 | 数据库连接池 | 最小 2 / 最大 10 连接 |
| NFR-06 | 源去重准确率 | ≥ 99%（domain_key+source_name 组合匹配） |
| NFR-07 | 数据库降级 | MySQL 不可用时 AI 调试流程正常工作（跳过数据库） |
| NFR-08 | 密码安全 | MySQL 密码不得硬编码在源码中，通过环境变量/.env 文件提供 |
| NFR-09 | 本地单用户 | 仅绑定 127.0.0.1，不对外暴露，无认证系统 |
| NFR-10 | XSS 防护 | JSON 编辑器内容不执行脚本，Vue3 默认转义 |
| NFR-11 | 现有模块兼容 | batch_runner/experience_manager/obstacle_resolver/crypto_analyzer/interactive_guide/source_validator/rule_precheck/confidence_evaluator/error_diagnoser 等现有模块保持 CLI 兼容，Web 模式通过 DebugOrchestrator 间接调用 |
| NFR-12 | delegate 模块降级 | ocr_delegate/webview_delegate 在 Web 模式下不启用（无 GUI），降级为日志输出 |
| NFR-13 | 服务端日志 | 请求日志中间件 + RotatingFileHandler（10MB×5）+ 环境变量控制日志级别（LEGADO_LOG_LEVEL） |
| NFR-14 | 文件上传限制 | 单文件上传 ≤ 10MB（覆盖大合集 JSON） |
| NFR-15 | API 频率限制 | 本地模式默认不启用；非本地部署时调试接口 ≤ 10次/分钟 |
| NFR-16 | Source.notes 字段 | AI 闭环修复经验写入 Source.notes 字段，供后续调试参考 |

## Scenarios

### Scenario 1: AI 创建新书源（数据库命中+测试通过）

```
Given: 用户请求为 biquge.com 创建书源
  And: 数据库中已存在 3 个 biquge.com 的书源，其中 1 个测试通过
When: AI 调用 debug_runner
Then: debug_runner 从数据库查询到 3 个同域名源
  And: 选取测试通过的源，直接返回结果
  And: 跳过网站分析和 JVM 测试阶段
```

### Scenario 2: AI 创建新书源（数据库命中+测试失败→自动修复）

```
Given: 用户请求为 biquge.com 创建书源
  And: 数据库中已存在 2 个 biquge.com 的书源，但都测试失败
When: AI 调用 debug_runner
Then: debug_runner 从数据库查询到 2 个同域名源
  And: 取出最新源 → JVM 测试 → 测试失败
  And: 触发 auto_fixer 自动修复 → 修复后重测
  And: 修复成功 → 更新数据库中的源JSON和测试结果
  And: 返回修复后的源给 AI
```

### Scenario 3: AI 创建新书源（数据库命中+修复失败）

```
Given: 用户请求为 biquge.com 创建书源
  And: 数据库中已存在源但测试失败且自动修复也失败
When: AI 调用 debug_runner
Then: 取出源 → JVM 测试 → 失败 → auto_fixer 修复 → 修复后重测 → 仍失败
  And: 标记为需 AI 介入，返回修复建议和错误诊断
  And: AI 可选择从头分析网站构建新规则
```

### Scenario 4: AI 创建新书源（数据库未命中）

```
Given: 用户请求为 new-site.com 创建书源
  And: 数据库中不存在 new-site.com 的书源
When: AI 调用 debug_runner
Then: debug_runner 查询数据库未命中
  And: 从头分析网站 → 构建规则 → JVM 测试
  And: 生成的源 JSON 和测试结果存入数据库
  And: 下次同域名请求可直接复用
```

### Scenario 5: 用户全量获取社区源

```
Given: 用户首次使用，数据库为空
When: 用户在 Web 页面点击「全量获取书源」
Then: 爬取 yckceo.com 所有书源合集列表
  And: 逐个下载 JSON 并解析入库
  And: 实时显示进度（已下载 X/Y 合集，已入库 N 条源）
  And: 按 domain_key+source_name 去重后存储
```

### Scenario 6: 用户 Web 管理源+推送到真机

```
Given: 数据库中有 5000 条书源
When: 用户打开浏览器访问 http://127.0.0.1:8080
Then: 显示源列表页，支持搜索/筛选/排序
  And: 点击某源可查看详情+JSON+编辑
  And: 点击「测试」按钮触发 JVM 调试，WebSocket 实时推送进度
  And: 测试失败时点击「优化」按钮触发自动修复
  And: 选择多个源 → 点击「推送到手机」→ 调用 Legado Web API 推送
```

### Scenario 7: 用户导入本地源文件

```
Given: 用户有本地 BookSource JSON 文件
When: 用户在 Web 页面点击「导入」→ 上传文件
  Or: 用户执行 `legado-client import --file source.json`
Then: 解析 JSON 文件 → 去重 → 入库
  And: 显示导入结果（新增 X 条，跳过 Y 条重复，失败 Z 条）
```

### Scenario 8: 数据库不可用降级

```
Given: MySQL 服务未启动
When: AI 调用 debug_runner
Then: 数据库连接失败 → 自动降级到文件模式
  And: 跳过数据库查询，正常执行调试流程
  And: 输出警告：数据库不可用，结果不会持久化
When: 用户访问 Web 页面
Then: 显示提示：数据库未连接，请先启动 MySQL
  And: 页面显示只读模式或降级提示
```

### Scenario 9: 首次启动数据迁移

```
Given: 用户首次启动系统，output/book/ 和 output/rss/ 中有已有源文件
When: 用户执行 `legado-client db init`
Then: 自动扫描 output/ 目录下的 JSON 文件
  And: 解析并导入到数据库
  And: 显示迁移结果（导入 X 条书源，Y 条订阅源）
```

### Scenario 10: 用户批量测试+取消

```
Given: 数据库中有 5000 条书源，大部分未测试
When: 用户在 Web 页面选择多个源 → 点击「批量测试」
Then: 按队列逐个触发 JVM 调试
  And: 实时显示进度（已测试 X/Y，通过 Z，失败 W）
  And: 用户可点击「取消」中止批量测试
  And: 已完成的测试结果保留在数据库中
```

### Scenario 11: 用户编辑源 JSON 并保存

```
Given: 用户打开某书源详情页，切换到「JSON 编辑」Tab
When: 用户修改 JSON 中的 ruleSearch 字段
  And: 点击「保存」按钮
Then: 前端调用 SourceValidator 验证 JSON 格式
  And: 验证通过 → 调用 PUT /api/sources/{id} 保存
  And: 验证失败 → 显示错误提示，不保存
  And: 保存成功后更新数据库中的 source_json 和独立列字段
```

### Scenario 12: 用户导出源 JSON 文件

```
Given: 用户在源列表页选中 10 个书源
When: 用户点击「批量导出」按钮
Then: 前端调用 POST /api/sources/batch-export {ids: [1,2,...,10]}
  And: 后端生成 BookSource[] JSON 文件
  And: 浏览器下载 sources.json 文件
  And: 文件内容为标准 Legado 可导入格式
```

### Scenario 13: 用户从 Web 触发批量调试

```
Given: 数据库中有 200 个测试失败的书源
When: 用户在测试面板页选择「批量测试」→ 范围选择「测试失败的源」→ 点击「开始测试」
Then: 后端创建批量调试任务，返回 task_id
  And: 前端通过 WebSocket 接收进度消息
  And: 每个源测试完成后推送 progress 消息（当前序号/总数/源名/结果）
  And: 全部完成后推送 complete 消息（成功数/失败数/总耗时）
  And: 测试结果更新到数据库
```
```
