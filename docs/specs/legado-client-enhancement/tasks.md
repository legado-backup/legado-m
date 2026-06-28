# Legado Client Enhancement - 任务清单

## 阶段一：基础设施（存储层+配置）

- [ ] 1.1 创建 `.env.example` 环境变量模板文件
- [ ] 1.2 扩展 `legado_client/utils/config.py`：新增数据库/Web/爬取/真机配置项 + python-dotenv 加载
- [ ] 1.3 创建 `legado_client/storage/__init__.py` 包入口
- [ ] 1.4 实现 `legado_client/storage/database.py`：MySQL 连接管理（aiomysql + AsyncSession + 连接池）+ DatabaseHealthChecker 降级检测
- [ ] 1.5 实现 `legado_client/storage/models.py`：SQLAlchemy ORM 模型（Source/Collection/DebugResult/DeviceConfig 四张表，完整字段映射）+ Source 表 notes 字段（AI闭环修复经验）+ book_source_type 和 rss_type 独立列（替代 content_type 生成列，避免编码体系冲突）+ Source 表新增 test_mode ENUM('jar', 'device', 'compare')/device_jar_diff JSON/jar_optimization_count INT/last_jar_diff DATETIME 字段 + 10 个 Source 表索引（含 idx_book_source_type + idx_rss_type）+ 2 个 Collection 表索引 + 2 个 DebugResult 表索引（含 idx_created_at）+ DebugResult 表新增 test_mode ENUM('jar', 'device', 'compare') 字段 + device_jar_diff JSON 字段
- [ ] 1.6 实现 `legado_client/storage/repository.py`：CRUD 操作（find_by_domain / bulk_upsert / update_debug_result / upsert_source / find_by_group 等）+ 分组查询（LIKE/FIND_IN_SET）
- [ ] 1.7 配置 Alembic 数据库迁移（`alembic.ini` + 初始迁移脚本，含索引创建）
- [ ] 1.8 创建 `docker-compose.yml`（MySQL 8.0 一键启动）
- [ ] 1.9 实现 `legado_client/fetcher/source_parser.py`：JSON 解析 + URL 标准化 + domain_key 提取 + 去重逻辑（domain_key+source_name 组合匹配）+ BookSource/RssSource 字段映射（遵循 design.md source_parser 字段映射章节）。注意：BookSource 无 bookSourceIcon 字段，loginCheckJs 不是 loginCheckUrl，eventListener/customButton 是 Boolean 非 Text；RssSource 类型字段名是 type 不是 sourceType，有 searchUrl 字段，无 respondTime/weight 字段，ruleArticles/ruleContent 是 String 非 JSON 对象（不需要 json.dumps），RssSource 高频查询规则字段（ruleTitle/ruleImage/ruleLink/ruleNextPage/rulePubDate/ruleDescription）需独立列映射；loginUi 是 BaseSource 接口字段（BookSource/RssSource 共有）
- [ ] 1.10 实现 CLI `db` 子命令：`init`（建表+扫描 output/ 导入）/ `migrate` / `reset` / `import-dir` / `stats` / `backup` / `restore`
- [ ] 1.11 实现首次启动自动扫描 `output/` 目录导入已有源文件
- [ ] 1.12 实现 CLI `export` 子命令：`legado-client export --type book --output sources.json [--ids 1,2,3]`

**验收标准**：
- `legado-client db init` 成功建表 + 导入 output/ 目录下的源
- `legado-client db stats` 显示正确的源数量统计
- MySQL 不可用时 CLI 输出降级警告

## 阶段二：源获取器（多渠道）

- [ ] 2.1 创建 `legado_client/fetcher/__init__.py` 包入口 + 统一 `fetch()` 调度接口
- [ ] 2.2 实现 `legado_client/fetcher/yckceo_fetcher.py`：爬取 yckceo.com 书源/订阅源合集列表（HTML 解析 + 分页）+ 下载指定合集 JSON（`/json/id/{id}.json`）+ 合集元数据入库 + 多套 CSS 选择器容错降级
- [ ] 2.3 实现 `legado_client/fetcher/url_importer.py`：URL 直接导入 + GitHub 仓库 URL 导入
- [ ] 2.4 实现 `legado_client/fetcher/file_importer.py`：本地文件导入 + 目录扫描导入
- [ ] 2.5 实现 `legado_client/fetcher/legado_sync.py`：通过 LegadoWebClient（`legado_client/device/legado_web_client.py`）拉取真机源数据（`/getBookSources` `/getRssSources`），而非直接 HTTP 请求
- [ ] 2.6 实现 CLI `fetch` 子命令：`--type book/rss --all / --id {id} / --url {url}`
- [ ] 2.7 实现 CLI `import` 子命令：`--file {path} / --url {url}`
- [ ] 2.8 实现请求频率控制（间隔 ≥ 1秒）+ User-Agent 设置 + 超时处理
- [ ] 2.9 实现增量更新：仅下载新增/更新的合集（对比 remote_id + date）

**验收标准**：
- `legado-client fetch --type book --all` 成功爬取 yckceo.com 全量书源合集并入库
- `legado-client import --file source.json` 成功导入本地 JSON 文件
- `legado-client import --url https://xxx/source.json` 成功导入远程 JSON
- 去重逻辑正确：同 domain_key+source_name 的源只保留最新版本
- 请求间隔 ≥ 1 秒，不触发反爬

## 阶段三：AI 数据库查询+优化闭环

- [ ] 3.1 扩展 `legado_client/client/debug_runner.py`：调试前自动查数据库同域名源（`find_by_domain`）
- [ ] 3.2 实现「命中+测试通过」分支：直接返回缓存结果，跳过测试
- [ ] 3.3 实现「命中+测试失败/未测试」分支：取出源JSON → JVM测试 → 失败则触发 auto_fixer → 修复后重测 → 更新数据库
- [ ] 3.4 实现「命中+修复失败」分支：标记需AI介入，返回修复建议+错误诊断
- [ ] 3.5 实现「未命中」分支：正常流程后结果入库（`upsert_source` + `insert_debug_result`）
- [ ] 3.6 扩展 `legado_client/analyzer/auto_fixer.py`：修复记录输出（fix_detail JSON：修复类型/修复前/修复后/diff）
- [ ] 3.7 实现 `--skip-db-lookup` 参数：禁用数据库查询（离线模式）
- [ ] 3.8 实现 `--db-only` 模式：仅查数据库，不触发 JVM 测试
- [ ] 3.9 实现数据库降级：连接失败时自动跳过数据库查询，正常执行文件模式
- [ ] 3.10 重构 `debug_runner.py`：新增 `DebugResult` 数据类 + `run_and_return()` 函数（返回值模式，不调用 sys.exit），保留 `run()` 函数向后兼容
- [ ] 3.11 实现 `legado_client/client/debug_orchestrator.py`：DebugOrchestrator 编排器（组合 debug_runner + storage + auto_fixer，实现"查库→测试→修复→更新"完整闭环）
- [ ] 3.12 实现 DebugOrchestrator 的 Web 模式（JvmPool 异步调用）和 CLI 模式（run_and_return 同步调用）双路径
- [ ] 3.13 集成 experience_manager：DebugOrchestrator 查库后调用 ExperienceManager.search() 检索经验，经验结果作为调试上下文
- [ ] 3.14 扩展 batch_runner：新增 `run_batch_and_return()` 返回值模式（供 Web API 使用），从数据库查询源列表替代文件扫描
- [ ] 3.15 Web 模式下 delegate 模块降级：interactive_guide 交互提示通过 WebSocket 推送（非阻塞），webview_handler/user_interaction 降级为日志输出
- [ ] 3.16 实现 `legado_client/device/legado_web_client.py`：LegadoWebClient 类，封装 Legado Web 服务 26 个 HTTP API + 3 个 WebSocket API（连接测试/源推送/源拉取/源调试/书籍搜索），支持 httpx 异步 + WebSocket。注意：WebSocket 端口 = HTTP 端口 + 1（源码 WebService.kt 硬编码，默认 HTTP:1122, WS:1123），构造函数 ws_url 为 `ws://{host}:{port+1}`；HTTP 响应需解析 ReturnData 格式（`{isSuccess, errorMsg, data}`）提取 data 字段；调试 WS 返回纯文本日志（非 JSON），通过 WebSocket 关闭帧结束；当前 Legado 版本无 HTTP 认证，auth_token 为预留字段
- [ ] 3.17 扩展 DebugOrchestrator：新增 mode 参数（auto/device/jar），auto 模式下真机优先→JAR回退，device 模式仅真机，jar 模式仅 JAR 仿真
- [ ] 3.18 实现真机测试→JAR验证对比流程：真机测试通过后自动触发 JAR 仿真验证，记录差异到 DebugResult.device_jar_diff
- [ ] 3.19 实现 `legado_client/analyzer/jar_optimizer.py`：JarOptimizer 类，真机通过但 JAR 失败时触发优化闭环（差异分析→源码定位→JAR代码修改建议→回归测试）

**验收标准**：
- AI 调试同域名源时，数据库有测试通过的源则直接返回，不触发 JVM
- AI 调试同域名源时，数据库有测试失败的源则取出→测试→失败→自动修复→重测→更新数据库
- AI 调试新域名源时，正常流程后源+测试结果入库
- `--skip-db-lookup` 模式下跳过数据库查询
- MySQL 不可用时 AI 调试正常工作（降级到文件模式）
- LegadoWebClient 可连接真机 Legado Web 服务，26 个 HTTP API + 3 个 WebSocket API 可调用
- DebugOrchestrator mode=auto 时真机优先→JAR 回退，mode=device 时仅真机，mode=jar 时仅 JAR
- 真机测试通过后自动触发 JAR 验证，差异记录到 DebugResult.device_jar_diff
- JarOptimizer 优化闭环可执行：差异分析→源码定位→JAR代码修改建议→回归测试

## 阶段四：Web API 服务

- [ ] 4.1 创建 `legado_client/server/__init__.py` 包入口
- [ ] 4.2 实现 `legado_client/server/app.py`：FastAPI 应用创建 + 中间件（CORS: 允许 :5173 开发模式跨域）+ 异常处理 + 统一错误响应格式（`{ok: false, error: {code, message}}`）+ 静态文件挂载（SPA 回退）+ 生命周期事件（JvmPool start/stop），遵循 ADR-12
- [ ] 4.3 实现 `legado_client/server/schemas.py`：Pydantic 请求/响应模型（SourceListRequest/SourceUpdateRequest/DebugStartRequest/BatchDebugRequest/ImportUrlRequest/DeviceCreateRequest 等 + SourceItem/SourceDetail/CollectionItem/DebugHistoryItem/DeviceItem/HealthResponse/ImportResult/DebugWSMessage 等），详见 design.md Pydantic Schemas 章节
- [ ] 4.4 实现 `legado_client/server/jvm_pool.py`：JVM 实例池管理（单实例 + asyncio.to_thread + Semaphore）
- [ ] 4.5 实现 `legado_client/server/routes/sources.py`：源管理 API（11 个端点：列表/详情/编辑/删除/启用禁用/按域名查询/批量操作/分组列表/单源导出/批量导出/验证JSON格式），遵循 design.md API 端点规范
- [ ] 4.6 实现 `legado_client/server/routes/collections.py`：合集管理 API（6 个端点：列表/远程列表/下载/全量获取/增量更新/删除）
- [ ] 4.7 实现 `legado_client/server/routes/debug.py`：调试 API + WebSocket（7 个端点：启动/批量/优化/取消/状态/历史 + WS），WebSocket 消息格式遵循 ADR-13 协议（log/error/result/progress/complete 五种类型 + UUID4 task_id + 断线重连+60s消息缓存）
- [ ] 4.8 实现 `legado_client/server/routes/import_export.py`：导入导出 API（4 个端点：URL导入/文件上传/GitHub导入/真机拉取）
- [ ] 4.9 创建 `legado_client/device/__init__.py` 包入口
- [ ] 4.10 实现 `legado_client/server/routes/device.py`：真机推送 API（7 个端点：列表/添加/编辑/删除/测试连接/推送/拉取）
- [ ] 4.11 实现 `legado_client/server/routes/stats.py`：统计 API（4 个端点：概览/测试结果分布/内容类型分布/分组分布）
- [ ] 4.12 实现 CLI `serve` 子命令：`--host 127.0.0.1 --port 8080`
- [ ] 4.13 实现数据库降级：MySQL 不可用时 API 返回 503 + 降级提示
- [ ] 4.14 实现 `/api/health` 健康检查端点（含数据库连接状态）
- [ ] 4.15 实现源验证 API：`POST /api/sources/validate`（调用 SourceValidator，前端编辑器实时验证用）
- [ ] 4.16 实现请求日志中间件：记录 API 请求方法/路径/状态码/耗时（跳过 /ws 和 /assets）
- [ ] 4.17 配置 RotatingFileHandler：10MB×5 文件轮转，日志输出到 output/server.log
- [ ] 4.18 实现日志级别环境变量控制：LEGADO_LOG_LEVEL（默认 INFO），第三方库日志降级
- [ ] 4.19 实现文件上传大小限制：单文件 ≤ 10MB
- [ ] 4.20 实现 `legado_client/server/routes/legado_proxy.py`：Legado Web 服务代理路由（19 个 HTTP 代理端点 + 3 个 WebSocket 代理端点），支持动态设备选择
- [ ] 4.21 实现调试对比 API：`POST /api/debug/compare` — 同时在真机和 JAR 上测试同一源，返回对比结果
- [ ] 4.22 实现 JAR 优化 API：`POST /api/debug/jar-optimize` — 触发 JAR 优化闭环
- [ ] 4.23 实现测试模式统计 API：`GET /api/stats/test-mode` — 真机 vs JAR 测试结果对比统计

**验收标准**：
- `legado-client serve` 启动后，`/api/health` 返回 200 + 数据库状态
- `/api/sources` 分页查询正常，支持筛选/搜索/排序
- `/api/debug/start` 触发 JVM 调试，WebSocket 推送实时日志
- `/api/import/file` 上传 JSON 文件导入成功
- MySQL 不可用时 `/api/health` 返回数据库不可用状态
- `/api/debug/compare` 同时在真机和 JAR 上测试同一源，返回对比结果
- `/api/debug/jar-optimize` 触发 JAR 优化闭环，返回优化建议
- `/api/stats/test-mode` 返回真机 vs JAR 测试结果对比统计
- Legado 代理路由可转发 HTTP + WebSocket 请求到真机 Legado Web 服务

## 阶段五：Web 前端页面

### 5.A 基础框架与全局组件

- [ ] 5.1 初始化 Vue3 + Vite + Element Plus + Vue Router + Pinia 项目（`legado_client/web/admin/`），配置 Vite 代理（`/api` → `http://127.0.0.1:8080`，`/legado` → Legado 真机反向代理），遵循 ADR-17
- [ ] 5.2 实现 `MainLayout.vue`：侧边栏（8 个菜单项含"Legado 原生前端"入口，可折叠 200px/64px）+ 顶栏（Logo+数据库状态指示+Legado连接状态+暗色切换）+ 底栏（源总数+通过率+JVM状态）
- [ ] 5.3 实现路由配置：9 个路由（`/admin/sources` → `/admin/sources/:id` → `/admin/collections` → `/admin/import` → `/admin/debug` → `/admin/devices` → `/admin/stats` → `/legado/*`），Hash 模式。管理面板路由统一使用 `/admin/` 前缀，Legado 原生前端使用 `/legado/*` 路由
- [ ] 5.4 实现 Pinia Stores：`appStore`（数据库状态/JVM状态/暗色模式）、`sourceStore`（筛选/分页/选中项）、`debugStore`（task_id/日志/进度）、`deviceStore`（设备列表）
- [ ] 5.5 实现 API 层：`api/sources.ts` + `api/collections.ts` + `api/debug.ts` + `api/import.ts` + `api/device.ts` + `api/stats.ts`（Axios 封装+统一错误处理）
- [ ] 5.6 实现全局组件 `SourceSelect.vue`：远程搜索+下拉选择源
- [ ] 5.7 实现全局组件 `DeviceSelect.vue`：设备下拉选择
- [ ] 5.8 实现全局组件 `JsonEditor.vue`：CodeMirror 6 封装（语法高亮+编辑+格式化）
- [ ] 5.9 实现全局组件 `DebugLogPanel.vue`：WebSocket 连接+实时日志渲染+自动滚动
- [ ] 5.10 实现全局组件 `ProgressDialog.vue`：进度条弹窗
- [ ] 5.11 实现全局组件 `ResultSummary.vue`：导入/导出结果统计（新增/跳过/失败）

### 5.B 源列表页 `/admin/sources`（10 个功能点）

- [ ] 5.12 实现源列表页 `SourceListPage.vue`：10 列表格（复选框/名称/URL/类型/内容类型/分组/测试结果/最后测试/启用/操作）
- [ ] 5.13 实现筛选栏：搜索框（300ms 防抖）+ 6 个筛选器（类型/内容类型/测试结果/分组/有无登录/重置）
- [ ] 5.14 实现排序：名称/测试时间/创建时间/响应时间 4 列可排序
- [ ] 5.15 实现分页：页码切换 + 每页条数选择（10/20/50/100）
- [ ] 5.16 实现批量操作栏：选中后显示 → 批量测试/导出/删除/推送/启用禁用
- [ ] 5.17 实现操作列：测试/复制JSON/删除
- [ ] 5.18 实现启用/禁用 Switch 切换
- [ ] 5.19 实现点击名称跳转详情页

### 5.C 源详情页 `/admin/sources/:id`（10 个功能点）

- [ ] 5.20 实现源详情页 `SourceDetailPage.vue`：顶栏（返回+源名+5 个操作按钮）+ 基本信息卡片 + 测试结果步骤条
- [ ] 5.21 实现 Tab「JSON 编辑」：CodeMirror 编辑 + 格式化 + 保存 + 重置
- [ ] 5.22 实现 Tab「测试历史」：Timeline 组件，按时间倒序，含修复记录
- [ ] 5.23 实现 Tab「同域名源」：同 domain_key 源列表 + 一键切换
- [ ] 5.24 实现操作按钮：测试/优化/导出/推送（选择设备弹窗）/删除（确认弹窗）
- [ ] 5.25 实现分组管理：基本信息卡片中分组标签编辑（TagInput 组件，逗号分隔输入，支持从已有分组列表选择），对应 FR-05-11

### 5.D 合集管理页 `/admin/collections`（8 个功能点）

- [ ] 5.26 实现合集管理页 `CollectionPage.vue`：7 列表格（标题/用户/源数量/下载量/日期/状态/操作）
- [ ] 5.27 实现全局操作：获取远程列表 + 全量获取（确认弹窗）+ 增量更新
- [ ] 5.28 实现单个合集操作：下载/更新/删除
- [ ] 5.29 实现类型切换：书源/订阅源 Tab
- [ ] 5.30 实现下载进度条：WebSocket progress 消息

### 5.E 源导入页 `/admin/import`（6 个功能点）

- [ ] 5.31 实现源导入页 `ImportPage.vue`：4 个导入区块（URL/文件上传/GitHub/真机拉取）
- [ ] 5.32 实现 URL 导入：输入框 + 导入按钮
- [ ] 5.33 实现文件上传：拖拽区域 + 选择文件按钮
- [ ] 5.34 实现 GitHub 导入：仓库 URL 输入框 + 导入按钮
- [ ] 5.35 实现真机拉取：设备选择 + 类型选择 + 拉取按钮
- [ ] 5.36 实现导入结果统计：ResultSummary 组件（新增/跳过/失败 + 失败详情展开）

### 5.F 测试面板页 `/admin/debug`（9 个功能点）

- [ ] 5.37 实现测试面板页 `DebugPage.vue`：3 个 Tab（单源测试/批量测试/优化测试）+ 测试历史
- [ ] 5.38 实现 Tab「单源测试」：SourceSelect 选择源 + 阶段选择 + 开始测试 + DebugLogPanel 实时日志
- [ ] 5.39 实现 Tab「批量测试」：范围选择（全部/失败源/指定分组）+ 开始/取消 + 进度条 + 结果列表
- [ ] 5.40 实现 Tab「优化测试」：选择失败源 + 开始优化 + 修复 diff 展示
- [ ] 5.41 实现测试历史：底部列表，最近 20 条记录
- [ ] 5.42 实现取消测试按钮

### 5.G 真机管理页 `/admin/devices`（6 个功能点）

- [ ] 5.43 实现真机管理页 `DevicePage.vue`：设备卡片列表 + 添加设备按钮
- [ ] 5.44 实现添加/编辑设备弹窗：名称 + IP + 端口（默认1122）+ 认证Token（可选）
- [ ] 5.45 实现测试连接按钮：显示连接结果（可达/不可达/需认证）
- [ ] 5.46 实现推送源：弹窗选择源 + 类型 → 推送
- [ ] 5.47 实现拉取源：选择类型 → 确认拉取
- [ ] 5.48 实现删除设备：确认弹窗

### 5.H 统计面板页 `/admin/stats`（4 个功能点）

- [ ] 5.49 实现统计面板页 `StatsPage.vue`：4 个概览卡片（源总数/通过率/书源数/订阅数）
- [ ] 5.50 实现测试结果饼图：ECharts 饼图
- [ ] 5.51 实现内容类型柱状图：ECharts 横向柱状图
- [ ] 5.52 实现分组分布图：ECharts 横向柱状图

### 5.I 构建与部署

- [ ] 5.53 构建前端：`npm run build` → 输出到 `legado_client/web/dist/`
- [ ] 5.54 FastAPI 挂载静态文件：StaticFiles + SPA 回退（遵循 ADR-12）
- [ ] 5.55 实现 Legado 原生前端集成：反向代理 `/legado/*` 到 Legado 真机 Web 服务，支持 HTTP + WebSocket 双向代理。注意：Legado 前端是 MPA 结构（导航首页+Vue3 SPA Hash 路由+传书页面），使用 `StaticFiles(html=True)` 挂载，Vue3 SPA 路由为 `/legado/vue/#/bookSource` 等
- [ ] 5.56 实现源详情页"真机 vs JAR 对比"Tab：展示真机和 JAR 仿真测试结果的差异，高亮差异点
- [ ] 5.57 实现测试面板"真机 vs JAR 对比"Tab：同时触发真机和 JAR 调试，双栏实时日志对比
- [ ] 5.58 实现真机管理页设备配置：HTTP 端口（默认 1122），WebSocket 端口 = HTTP 端口 + 1（源码硬编码），无需独立 WS 端口字段；auth_token 为预留字段（当前 Legado 版本无 HTTP 认证）

**验收标准**：
- 浏览器访问 `http://127.0.0.1:8080` 显示源列表页
- 侧边栏 8 个菜单项可点击切换（含"Legado 原生前端"入口）
- 源列表页：搜索（300ms防抖）/6个筛选器/4列排序/分页/批量操作正常
- 源详情页：4 个 Tab 切换正常（含"真机 vs JAR 对比"Tab），JSON 编辑器可编辑保存
- 测试面板：WebSocket 实时日志推送，批量测试进度条，"真机 vs JAR 对比"Tab 双栏实时日志
- 优化测试：修复 diff 展示
- 导入页：4 种导入方式正常，结果统计正确
- 真机管理：添加设备/测试连接/推送/拉取正常，HTTP 端口（默认 1122），WebSocket 端口 = HTTP 端口 + 1（源码硬编码，无需独立字段）
- 统计面板：4 个图表正确渲染
- 暗色模式切换正常
- `/legado/*` 反向代理到 Legado 真机 Web 服务正常，HTTP + WebSocket 双向代理

## 阶段六：集成测试+文档

- [ ] 6.1 端到端集成测试：全量获取→入库→Web查看→测试→优化→推送到真机
- [ ] 6.2 数据库降级测试：停止 MySQL → 验证 AI 调试/Web 服务降级行为
- [ ] 6.3 更新 `scripts/requirements.txt`：新增所有依赖（fastapi/uvicorn/sqlalchemy/aiomysql/alembic/python-dotenv/httpx/pymysql/slowapi）
- [ ] 6.4 更新 `scripts/setup.py`：新增依赖声明 + 版本号 3.0.0
- [ ] 6.5 更新 `legado_client/__init__.py`：版本号统一为 3.0.0
- [ ] 6.6 验证 Config.get_instance() 单例模式向后兼容：现有 CLI 命令（debug/batch/verify）无需修改即可使用
- [ ] 6.7 更新 `.trae/skills/legado-source-creator/SKILL.md`：新增数据库查询+优化闭环相关说明
- [ ] 6.8 更新 `.trae/skills/legado-source-creator/AI_README.md`：新增 Web 管理界面和 CLI 新命令说明

**验收标准**：
- 完整流程可跑通：获取源→入库→Web查看→测试→优化→推送真机
- MySQL 不可用时系统正常降级
- 所有新增依赖正确安装
- Skill 文档已更新

---

## AOAdapt 日志

| 日期 | 问题 | 处理 |
|------|------|------|
| 2026-06-24 | 初始设计文档 design.md 内容被覆盖 | 完整重写 design.md，补充所有架构遗漏 |
| 2026-06-24 | BookSource/RssSource 关键字段映射不完整 | 新增完整字段映射：bookSourceType/enabledExplore/loginUrl/searchUrl/exploreUrl 等 |
| 2026-06-24 | 源去重策略过于激进（同域名只保留1条） | 改为 domain_key+source_name 组合去重，同域名上限20条 |
| 2026-06-24 | 缺少源优化闭环设计 | 新增 auto_fixer 自动修复→重测→更新数据库闭环 |
| 2026-06-24 | 缺少真机推送流程 | 新增 Legado Web API 对接 + DeviceConfig 表 + 推送/拉取 API |
| 2026-06-24 | 缺少数据迁移方案 | 新增首次启动扫描 output/ 目录导入 + CLI db import-dir 命令 |
| 2026-06-24 | MySQL 密码硬编码风险 | 改为 .env 环境变量加载，默认空值 |
| 2026-06-24 | 缺少数据库降级策略 | 新增 DatabaseHealthChecker + 30秒重试 + AI/Web/CLI 三层降级行为 |
| 2026-06-24 | debug_runner sys.exit() 阻断闭环流 | ADR-09: 新增 DebugResult + run_and_return() 返回值模式，保留 run() 向后兼容 |
| 2026-06-24 | AI 闭环缺少编排层 | ADR-10: 新增 DebugOrchestrator 编排器，组合 debug_runner + storage + auto_fixer |
| 2026-06-24 | RssSource 缺少 ruleArticles/ruleContent 字段 | 补充到 Source 表模型和 spec.md FR-02-03 |
| 2026-06-24 | yckceo_fetcher 缺少反爬和容错方案 | ADR-11: 双层策略（HTML解析+JSON API）+ 多套CSS选择器容错 |
| 2026-06-24 | 前端部署策略不明确 | ADR-12: Vite 构建 + FastAPI StaticFiles 挂载 + SPA 回退 |
| 2026-06-24 | WebSocket 协议格式未定义 | ADR-13: 五种消息类型 + UUID4 task_id + 断线重连+60s缓存 |
| 2026-06-24 | 真机认证机制不明确 | ADR-14: 无认证/auth_token 双模式 + test_connection 检测 |
| 2026-06-24 | 数据库初始化时机不明确 | ADR-15: db init 显式命令 + serve 不自动建表 + AI 降级 |
| 2026-06-24 | API 端点规范缺失，前端无法对接 | 补充 design.md API 端点规范章节：6 个路由模块 30+ 端点，含方法/路径/请求/响应 |
| 2026-06-24 | source_parser 字段映射缺失 | 补充 design.md source_parser 字段映射章节：BookSource/RssSource → Source ORM 完整映射 |
| 2026-06-24 | 现有模块集成方案缺失 | 补充 design.md 现有模块集成方案章节：batch_runner/experience_manager/obstacle_resolver 等 8 个模块 |
| 2026-06-24 | 数据库索引设计缺失 | 补充 design.md 数据库索引设计：Source 9 索引 + Collection 2 索引 + DebugResult 2 索引 |
| 2026-06-24 | export CLI 命令设计缺失 | 补充 spec.md FR-01-15 + tasks.md 1.12 |
| 2026-06-24 | CORS 配置缺失 | 补充 design.md CORS 配置章节 + spec.md FR-04-14 |
| 2026-06-24 | config.py 扩展设计缺失 | 补充 design.md config.py 扩展设计章节：数据库/Web/爬取/JVM 配置 + .env 加载 |
| 2026-06-24 | Source 分组数据模型缺失 | 补充 design.md group 字段设计 + spec.md FR-02-14 |
| 2026-06-24 | Pydantic schemas 定义缺失 | 补充 design.md Pydantic Schemas 章节：15+ 请求模型 + 8+ 响应模型 |
| 2026-06-24 | 统一错误响应格式缺失 | 补充 design.md 统一响应格式 + spec.md FR-04-15 |
| 2026-06-24 | 安全需求缺失 | 补充 spec.md NFR-09~12：本地单用户/XSS 防护/现有模块兼容/delegate 降级 |
| 2026-06-25 | WebSocket 调试协议完全错误：假设 JSON+isEnd，实际是纯文本+关闭帧 | 修复 LegadoWebClient：ws_book_source_debug/ws_rss_source_debug 改为接收纯文本日志，通过 ConnectionClosed 检测结束 |
| 2026-06-25 | HTTP 响应未解析 ReturnData 封装格式 | 新增 `_parse_response()` 方法，提取 `{isSuccess, errorMsg, data}` 中 data 字段 |
| 2026-06-25 | loginCheckUrl 字段名错误（BookSource/RssSource 均为 loginCheckJs） | 修复数据库表、字段映射、Pydantic 模型：login_check_url → login_check_js |
| 2026-06-25 | BookSource 无 bookSourceIcon 字段 | 修复 BOOK_SOURCE_MAPPING：source_icon 映射为 `lambda _: None` |
| 2026-06-25 | RssSource 无 respondTime/weight 字段 | 修复 RSS_SOURCE_MAPPING：respond_time/weight 映射为 `lambda _: None` |
| 2026-06-25 | RssSource 类型字段名是 type 不是 sourceType | 修复 RSS_SOURCE_MAPPING：rss_type 映射到 `type` |
| 2026-06-25 | RssSource 有 searchUrl 字段（不应映射为 None） | 修复 RSS_SOURCE_MAPPING：search_url 映射到 `searchUrl` |
| 2026-06-25 | 大量源码字段在映射中遗漏 | 补充 coverDecodeJs/exploreScreen/ruleExplore/ruleReview/variableComment/enabledCookieJar/jsLib/eventListener/customButton |
| 2026-06-25 | ~~HTTP 和 WebSocket 共用端口，ws_port 字段多余~~ **此修复有误！** | **2026-06-26 更正**：源码 WebService.kt 第167行 `webSocketServer = WebSocketServer(port + 1)`，WS 端口 = HTTP 端口 + 1。LegadoWebClient.ws_url = `ws://{host}:{port+1}`，DeviceConfig 仍无需 ws_port 字段（由 port 计算得出） |
| 2026-06-26 | WebSocket 端口与 HTTP 端口不同（port+1），设计文档"共用端口"错误 | 修复 LegadoWebClient 构造函数 ws_url = `ws://{host}:{port+1}`；修复 DeviceConfig DDL 注释；修复 spec.md FR-03-16/FR-05-22 |
| 2026-06-26 | Legado Web 服务无 HTTP 认证机制，auth_token 设计虚构 | 标注 auth_token 为预留字段（HttpServer.kt 无 Authorization 校验），_headers() 方法添加注释说明 |
| 2026-06-26 | eventListener/customButton 类型错误：源码 Boolean，DDL 定义为 TEXT | 修复 DDL 为 BOOLEAN DEFAULT FALSE；修复 Pydantic 模型为 Optional[bool] |
| 2026-06-26 | RssSource ruleContent/ruleArticles 是 String 类型，映射用了 json.dumps | 修复 RSS_SOURCE_MAPPING：直接映射字符串，不使用 json.dumps（与 BookSource 嵌套对象不同） |
| 2026-06-26 | Source/DebugResult 表缺少 test_mode/device_jar_diff 字段 | 补充 Source 表 test_mode/device_jar_diff/jar_optimization_count/last_jar_diff；补充 DebugResult 表 test_mode/device_jar_diff |
| 2026-06-26 | loginUi 字段遗漏（BaseSource 接口，BookSource/RssSource 共有） | 补充 Source 表 login_ui 字段；补充 BOOK/RSS_SOURCE_MAPPING 的 login_ui 映射 |
| 2026-06-26 | RssSource 高频查询规则字段缺少独立列 | 补充 rule_title/rule_image/rule_link/rule_next_page/rule_pub_date/rule_description 独立列及映射 |
| 2026-06-25 | Legado 前端是 MPA+Hash 路由，设计文档按 SPA+History 路由处理 | 修复前端集成方案：使用 StaticFiles(html=True) 挂载 MPA，Vue3 SPA 路由改为 `/legado/vue/#/bookSource` |
| 2026-06-25 | JarOptimizer 类名映射不准确（BookSourceManager 等不存在） | 修复 stage_class_map：使用源码实际类名（WebBook/BookList/BookInfo/BookChapterList/BookContent） |
| 2026-06-26 | tasks.md 4.10 与 3.16 重复（均为 LegadoWebClient 实现） | 删除 4.10，重新编号 4.11→4.23 为 4.10→4.23 |
| 2026-06-26 | DebugResult 表缺少搜索关键词字段 | 新增 `key` VARCHAR(200) 字段，记录调试使用的搜索关键词/RSS URL |
| 2026-06-26 | JarOptimizer common_classes 中 BookContentRule 不存在（源码为 ContentRule） | 修复为 ContentRule，补充 TocRule，标注 BookListRule 为接口 |
| 2026-06-26 | 前端路由表中管理面板仍用 /sources 而非 /admin/sources | 统一所有页面路由为 /admin/* 前缀，Legado 原生为 /legado/* |
| 2026-06-26 | .env.example 包含冗余 LEGADO_DEVICE_WS_PORT 配置 | 删除 WS_PORT 行，添加注释说明 WS 端口由 HTTP 端口+1 自动计算 |
| 2026-06-26 | LegadoWebClient.proxy_request 使用 Request 类型但未说明导入方式 | 添加字符串类型注解 "Request" 和导入说明注释 |
| 2026-06-26 | article_style DDL 注释缺少值含义 | 补充注释：0三图/1大图/2双排/3单图/4无图 |
| 2026-06-26 | tasks.md 真机管理页验收标准仍写"HTTP+WebSocket 共用端口" | 修改为"HTTP 端口（默认 1122），WebSocket 端口 = HTTP 端口 + 1" |
