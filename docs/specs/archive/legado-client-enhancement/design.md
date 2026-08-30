# Legado Client Enhancement - 技术设计文档

## Technical Approach

### 整体架构

在现有 `legado_client` 包基础上，新增 6 个模块 + 扩展 3 个现有模块。**核心变更**：复用 Legado 已有的 Vue3 前端和 Web 服务 API，测试链路改为真机优先→JAR 仿真回退。

```
legado_client/
├── [现有] cli.py              ← 扩展：新增 fetch/serve/db/import/export 子命令
├── [现有] client/
│   ├── debug_runner.py        ← 扩展：调试前查数据库+优化闭环+降级
│   ├── debug_orchestrator.py  ← [新增] AI 调试闭环编排器（真机优先链路）
│   └── rule_engine_client.py  ← 不变
├── [现有] analyzer/
│   ├── auto_fixer.py          ← 扩展：修复记录输出
│   └── jar_optimizer.py       ← [新增] JAR 仿真优化闭环（分析源码→修复JAR→重测）
├── [现有] utils/
│   └── config.py              ← 扩展：新增数据库/Web/爬取/真机/Legado Web 服务配置
├── [新增] storage/            ← MySQL 存储层
│   ├── __init__.py
│   ├── database.py            ← 连接管理+连接池+降级检测
│   ├── models.py              ← SQLAlchemy ORM 模型（完整字段映射）
│   └── repository.py          ← CRUD 操作
├── [新增] fetcher/            ← 多渠道源获取器
│   ├── __init__.py
│   ├── yckceo_fetcher.py      ← yckceo.com 爬取逻辑
│   ├── url_importer.py        ← URL/GitHub 导入
│   ├── file_importer.py       ← 本地文件导入+目录扫描
│   ├── legado_sync.py         ← Legado 真机同步（通过 LegadoWebClient）
│   └── source_parser.py       ← JSON 解析+去重
├── [新增] server/             ← Web API 服务
│   ├── __init__.py
│   ├── app.py                 ← FastAPI 应用
│   ├── routes/
│   │   ├── sources.py         ← 源管理 API
│   │   ├── collections.py     ← 合集管理 API
│   │   ├── debug.py           ← 调试 API + WebSocket
│   │   ├── import_export.py   ← 导入导出 API
│   │   ├── device.py          ← 真机推送 API
│   │   ├── legado_proxy.py    ← [新增] Legado Web 服务代理 API（26 HTTP + 3 WS）
│   │   └── stats.py           ← 统计 API
│   ├── schemas.py             ← Pydantic 请求/响应模型
│   └── jvm_pool.py            ← JVM 实例池管理
├── [新增] device/             ← 真机对接
│   ├── __init__.py
│   └── legado_web_client.py   ← [重构] Legado Web 服务完整客户端（26 HTTP API + 3 WS API）
└── [新增] web/                ← 前端（复用 Legado Vue3 前端 + 管理扩展面板）
    ├── legado-frontend/       ← [新增] Legado 原生前端（git submodule 或构建产物）
    │   └── dist/              ← Legado Vue3 构建产物（书架/阅读/源编辑/源调试）
    ├── admin/                 ← [新增] 管理扩展面板（Vue3 + Element Plus）
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    └── dist/                  ← 管理面板构建产物（FastAPI 挂载）
```

### 架构总览图

```
┌──────────────────────────────────────────────────────────────────────┐
│                        用户接入层                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ AI CLI   │  │ 管理面板 Web │  │ Legado 原生前端（iframe/代理）│  │
│  └────┬─────┘  └──────┬───────┘  └──────────────┬───────────────┘  │
│       │               │                          │                   │
├───────┼───────────────┼──────────────────────────┼───────────────────┤
│       │          FastAPI 服务层 (8080)            │                   │
│       │   ┌──────────┴──────────┐   ┌────────────┴────────────┐    │
│       │   │ 管理API             │   │ Legado Web 代理API       │    │
│       │   │ /api/sources        │   │ /legado/getBookSources   │    │
│       │   │ /api/debug          │   │ /legado/saveBookSource   │    │
│       │   │ /api/collections    │   │ /ws/legado/searchBook    │    │
│       │   │ /api/devices        │   │ /ws/legado/bookSourceDebug│   │
│       │   │ /api/stats          │   │ ... (26 HTTP + 3 WS)     │    │
│       │   └──────────┬──────────┘   └────────────┬────────────┘    │
├───────┼──────────────┼───────────────────────────┼──────────────────┤
│       │          核心服务层                        │                   │
│  ┌────┴─────────────┴────────────────────────────┴──────────────┐  │
│  │              DebugOrchestrator（调试编排器）                    │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ 测试链路：真机优先 → JAR仿真回退 → JAR优化闭环           │ │  │
│  │  │  1. 检查真机配置 → LegadoWebClient 真机测试              │ │  │
│  │  │  2. 真机通过 → JAR仿真对比验证                           │ │  │
│  │  │  3. 真机通过但JAR失败 → JarOptimizer 优化闭环            │ │  │
│  │  │  4. 真机失败 → auto_fixer 修复 → 真机重测                │ │  │
│  │  │  5. 无真机 → JAR仿真测试（现有流程）                     │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────┬──────────────┬──────────────────┬─────────────────────┘  │
│         │              │                  │                          │
│  ┌──────┴──────┐ ┌─────┴──────┐  ┌───────┴────────┐               │
│  │LegadoWeb    │ │ JvmPool    │  │ JarOptimizer   │               │
│  │Client       │ │ (JAR仿真)  │  │ (JAR优化闭环)  │               │
│  │26 HTTP+3WS │ │            │  │                │               │
│  └──────┬──────┘ └────────────┘  └────────────────┘               │
│         │                                                          │
├─────────┼──────────────────────────────────────────────────────────┤
│         │     数据存储层                                           │
│  ┌──────┴──────────────────────────────────────────────────────┐  │
│  │  MySQL (source/collection/debug_result/device_config)       │  │
│  │  + Legado 真机 (HTTP :1122 / WS :1123)                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层次           | 技术             | 理由                                  |
| ------------ | -------------- | ----------------------------------- |
| **Web 框架**   | FastAPI        | 原生 async、WebSocket 支持、自动 OpenAPI 文档 |
| **ORM**      | SQLAlchemy 2.0 | 成熟稳定、异步支持、Python 生态标准               |
| **数据库驱动**    | aiomysql       | 异步 MySQL 驱动，配合 FastAPI async        |
| **数据库迁移**    | Alembic        | SQLAlchemy 官方迁移工具                   |
| **前端框架**     | Vue3 + Vite    | 轻量、响应式、组件化                          |
| **UI 组件库**   | Element Plus   | Vue3 生态成熟组件库，表格/表单/对话框丰富            |
| **HTTP 客户端** | httpx          | 异步支持，替代 requests 用于爬取               |
| **数据验证**     | Pydantic v2    | FastAPI 内置，请求/响应模型                  |
| **配置管理**     | python-dotenv  | .env 文件加载，避免密码硬编码                   |

### 数据流详细设计

#### 1. 源获取流（多渠道统一入口）

```
用户/CLI/AI → Fetcher.fetch(channel, params)
    ↓
channel=yckceo → yckceo_fetcher: 爬列表页→下载JSON→解析入库
channel=url    → url_importer: 下载JSON→解析入库
channel=file   → file_importer: 读取文件→解析入库
channel=device → legado_sync: LegadoWebClient拉取→解析入库
    ↓
SourceParser.parse_and_dedup() → 按 domain_key+source_name 去重
    ↓
Repository.bulk_upsert_sources() → MySQL
```

#### 2. 测试链路流（真机优先 → JAR 仿真回退 → JAR 优化闭环）

> **核心变更**：测试链路从"JVM 仿真优先"改为"真机优先 → JAR 仿真回退"，并新增 JAR 优化闭环。

```
AI/用户触发测试 → DebugOrchestrator.debug_with_db()
    ↓
    检查真机配置（DeviceConfig + LegadoWebClient 连通性测试）
    ↓
    ├─ 真机已配置且可通 → LegadoWebClient 真机调试
    │   │
    │   ├─ 真机测试通过 → JAR 仿真验证（对比结果）
    │   │   ├─ JAR 也通过 → 记录对比结果，更新数据库，完成 ✅
    │   │   └─ JAR 失败 → 触发 JAR 优化闭环 ⬇️
    │   │       JarOptimizer.analyze_divergence(真机结果, JAR结果)
    │   │       → 分析 Legado 源码 → 定位 JAR 缺失功能
    │   │       → 修改 JAR Java 代码 → 重新构建 JAR
    │   │       → 回归测试验证 → 更新 JAR 覆盖率
    │   │
    │   └─ 真机测试失败 → auto_fixer 修复
    │       ├─ 修复成功 → 真机重测 → 更新数据库
    │       └─ 修复失败 → 标记需 AI 介入 → 返回修复建议+错误诊断
    │
    └─ 真机未配置/不可通 → JAR 仿真测试（现有流程）
        ├─ JAR 测试通过 → 更新数据库，完成 ✅
        └─ JAR 测试失败 → auto_fixer 修复 → JAR 重测
            ├─ 修复成功 → 更新数据库 ✅
            └─ 修复失败 → 标记需 AI 介入
```

**真机调试详细流程**：

```
DebugOrchestrator._run_device_debug(source_obj, key)
    ↓
1. LegadoWebClient.push_sources() → 推送源到真机
2. LegadoWebClient.ws_book_source_debug(tag, key) → WebSocket 调试
    ↓ 逐行接收调试日志
3. 解析调试日志 → 提取各阶段结果（搜索/详情/目录/正文）
4. LegadoWebClient.pull_sources() → 拉取真机上的最新源（含修复后状态）
5. 返回 DebugResult（含真机调试详情）
```

**JAR 优化闭环详细流程**：

```
JarOptimizer.optimize(真机结果, JAR结果, source_obj)
    ↓
1. 记录差异：diff_result = compare_results(真机结果, JAR结果)
2. 分析 Legado 源码：
   - 定位 JAR 仿真缺失的类/方法/逻辑
   - 搜索 Legado 源码中对应功能的实现
   - 生成差异分析报告
3. 修改 JAR Java 代码：
   - 在 legado-jvm 项目中补齐缺失功能
   - 更新 Rhino 桥接层
4. 重新构建 JAR：
   - mvn package → legado-jvm.jar
5. 回归测试验证：
   - 用同一源重新 JAR 仿真测试
   - 对比真机结果，确认 JAR 修复有效
6. 更新覆盖率报告
```

#### 3. Web 调试流

```
浏览器 → POST /api/debug/start {source_id, mode: "device"|"jar"|"auto"}
    ↓
mode=auto → DebugOrchestrator 自动选择（真机优先→JAR回退）
mode=device → LegadoWebClient 真机调试
mode=jar → JvmPool JAR 仿真调试
    ↓
WebSocket /ws/debug/{task_id} ← 实时推送调试日志
    ↓
调试完成 → Repository.update_debug_result()
    ↓
WebSocket 推送最终结果 → 浏览器更新UI
```

#### 4. 真机推送流

```
浏览器 → POST /api/devices/{id}/push {source_ids, source_type}
    ↓
LegadoWebClient.push_sources(device_id, sources_json)
    ↓
POST http://{device_ip}:{device_port}/saveBookSources
    ↓
返回推送结果（成功/失败/部分成功）
```

#### 5. Legado Web 服务代理流

```
Legado 原生前端 → /legado/getBookSources
    ↓
FastAPI legado_proxy 路由 → LegadoWebClient.get_book_sources()
    ↓
GET http://{device_ip}:1122/getBookSources
    ↓
返回结果（透传给前端，保持 Legado 原生 API 格式）
```

```
Legado 原生前端 → /ws/legado/bookSourceDebug
    ↓
FastAPI WebSocket 代理 → LegadoWebClient.ws_book_source_debug()
    ↓
WS http://{device_ip}:1123/bookSourceDebug
    ↓
逐行转发调试日志 → 前端 SourceDebug 组件实时展示
```

#### 6. 数据库降级流

```
任何数据库操作 → try/except
    ↓ 连接失败
DatabaseHealthChecker.mark_unavailable()
    ↓
AI调试：跳过数据库查询，正常执行文件模式
Web服务：返回503 + 降级提示
CLI命令：输出警告，继续文件模式
    ↓ 连接恢复
DatabaseHealthChecker.mark_available()
自动恢复数据库功能
```

## Architecture Decisions

### ADR-01: 数据库选型 — MySQL

**上下文**：需要持久化存储大量源数据（预估 5-35 万条），支持复杂查询和并发访问。

**决策**：使用 MySQL 8.0+，连接 `127.0.0.1:3306`。

**理由**：用户明确要求 MySQL；支持全文索引；连接池成熟。

**后果**：

* (+) 性能好，支持复杂查询

* (-) 需要本地安装 MySQL

**缓解**：Docker Compose 一键启动 + 数据库不可用时自动降级。

***

### ADR-02: ORM 选型 — SQLAlchemy 2.0 + async

**上下文**：需要异步数据库操作以配合 FastAPI async 模式。

**决策**：使用 SQLAlchemy 2.0 的 async session + aiomysql 驱动。

**后果**：

* (+) 异步非阻塞，配合 FastAPI

* (-) async session 需注意上下文管理

* (-) 现有同步代码（debug\_runner）需通过 `asyncio.to_thread()` 桥接

***

### ADR-03: 前端技术 — Vue3 + Element Plus

**上下文**：需要提供用户友好的 Web 管理界面。

**决策**：使用 Vue3 + Element Plus + Vite 构建 SPA。

**后果**：

* (+) 开发效率高，组件丰富

* (-) 需要 Node.js 构建环境

**缓解**：提供预构建 dist/ 目录。

***

### ADR-04: 源去重策略 — domain\_key + source\_name 组合匹配

**上下文**：同一网站可能有多个有效源（不同搜索规则、不同解析逻辑），严格去重会丢失有价值信息。

**决策**：按 `domain_key + source_name` 组合去重，同域名允许多个不同名称的源存在。

**规则**：

```python
def normalize_url(url: str) -> str:
    """URL标准化：去协议、去www前缀、去尾部斜杠、去端口"""
    url = url.strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    url = url.rstrip('/')
    url = re.sub(r':80$', '', url)     # 去默认HTTP端口
    url = re.sub(r':443$', '', url)    # 去默认HTTPS端口
    return url.lower()

def extract_domain_key(url: str) -> str:
    """提取域名键（仅域名部分，不含路径）"""
    normalized = normalize_url(url)
    return normalized.split('/')[0]
```

**去重逻辑**：

1. 对每个源提取 `domain_key` + `source_name`
2. 查数据库是否已存在相同 `domain_key + source_name` 的源
3. 已存在：比较 `lastUpdateTime`，保留更新的版本
4. 不存在：直接入库
5. 同域名上限 20 条源（防止某个域名源过多）

**后果**：

* (+) 保留同域名不同规则的有效源

* (+) 同名同域名才视为重复，去重更精准

* (-) 数据量比严格去重大（但更合理）

* (-) 需要同域名上限防止膨胀

***

### ADR-05: JVM 实例管理 — 单实例 + asyncio.to\_thread 桥接

**上下文**：JVM 仿真器是同步阻塞的 stdin/stdout 通信，FastAPI 需要 async。

**决策**：采用单 JVM 实例 + `asyncio.to_thread()` 包装同步调用 + Semaphore 控制并发。

**实现**：

```python
class JvmPool:
    """JVM 实例池，初期单实例

    关键设计：不直接包装 RuleEngineClient 的 _send/_send_streaming 方法，
    而是包装整个 debug 调用链（含回调），避免同步线程与 asyncio 的冲突。
    """
    def __init__(self, max_instances=1):
        self._client: RuleEngineClient | None = None
        self._semaphore = asyncio.Semaphore(max_instances)
        self._lock = asyncio.Lock()
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self):
        """启动 JVM 实例（在 FastAPI lifespan 中调用）"""
        self._client = await asyncio.to_thread(self._start_client)
        self._running = True

    async def stop(self):
        """关闭 JVM 实例（在 FastAPI lifespan 中调用）"""
        self._running = False
        if self._client:
            await asyncio.to_thread(self._client.shutdown)  # RuleEngineClient 用 shutdown() 而非 close()
            self._client = None

    async def debug_book_source(self, source_json: str, key: str,
                                 on_log=None, on_error=None, on_result=None) -> dict:
        """异步调试书源

        将整个 debug_book_source 调用（含回调）包装为异步。
        回调通过 asyncio.Queue 从同步线程传递到异步协程。
        """
        await self._semaphore.acquire()
        try:
            # 确保客户端存活
            if self._client is None or not self._client.is_alive():
                self._client = await asyncio.to_thread(self._start_client)

            # 创建结果 Future
            result_future = asyncio.get_event_loop().create_future()

            # 同步回调 → 异步 Future
            def sync_on_log(state, msg, html):
                if on_log:
                    asyncio.run_coroutine_threadsafe(
                        self._async_callback(on_log, state, msg, html),
                        asyncio.get_event_loop()
                    )

            def sync_on_error(msg, stack_trace, failed_stage):
                if on_error:
                    asyncio.run_coroutine_threadsafe(
                        self._async_callback(on_error, msg, stack_trace, failed_stage),
                        asyncio.get_event_loop()
                    )

            def sync_on_result(success, summary):
                if on_result:
                    asyncio.run_coroutine_threadsafe(
                        self._async_callback(on_result, success, summary),
                        asyncio.get_event_loop()
                    )
                # 设置结果 Future
                if not result_future.done():
                    asyncio.run_coroutine_threadsafe(
                        result_future.set_result({"success": success, "summary": summary}),
                        asyncio.get_event_loop()
                    )

            # 整个 debug 调用包装为异步
            result = await asyncio.to_thread(
                self._client.debug_book_source,
                source_json, key,
                sync_on_log, sync_on_error, sync_on_result
            )

            # 如果流式调用直接返回了结果（而非通过回调），使用该结果
            if result and not result_future.done():
                return result

            # 等待回调设置的结果（带超时）
            try:
                return await asyncio.wait_for(result_future, timeout=120)
            except asyncio.TimeoutError:
                return {"ok": False, "error": "Debug timeout (120s)"}

        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            self._semaphore.release()

    async def _async_callback(self, func, *args):
        """将同步回调桥接到异步"""
        func(*args)

    def _start_client(self) -> RuleEngineClient:
        """启动 JVM 客户端（同步）"""
        client = RuleEngineClient()
        client.start()
        return client
```

**后果**：

* (+) FastAPI async 兼容

* (+) 简单可靠

* (-) 同时只能处理 1 个调试请求

* (-) JVM 调用期间阻塞一个线程

* (-) 回调桥接增加少量复杂度

**风险缓解**：

* `_readline_with_timeout()` 超时 kill 进程后，JvmPool 在下次 `acquire()` 时自动重建实例

* Semaphore 保证同一时间只有一个调试在执行，避免 kill 竞争

***

### ADR-09: debug\_runner 重构 — sys.exit() 改为返回值模式

**上下文**：现有 `debug_runner.run()` 在调试完成后调用 `sys.exit(0/1/2/3)`，导致：

1. 无法在 `run()` 返回后执行数据库更新操作
2. AI 调试闭环流（查库→测试→修复→更新数据库）无法在 `run()` 内部实现
3. `cli.py` 的 `run_debug()` 通过捕获 `SystemExit` 变通处理，但丢失了测试详情

**决策**：将 `debug_runner.run()` 重构为返回值模式，新增 `run_and_return()` 函数。

**实现**：

```python
# legado_client/client/debug_runner.py 新增

class DebugResult:
    """调试结果数据类（替代 sys.exit 退出码）"""
    def __init__(self, success: bool, confidence: str, collector: DebugCollector,
                 source_obj: dict, elapsed: float):
        self.success = success
        self.confidence = confidence  # high/medium/low/unknown
        self.collector = collector
        self.source_obj = source_obj
        self.elapsed = elapsed
        self.errors = collector.errors
        self.stages_passed = collector.stages_passed
        self.stages_failed = collector.stages_failed

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "confidence": self.confidence,
            "stages_passed": self.stages_passed,
            "stages_failed": self.stages_failed,
            "errors": self.errors,
            "elapsed_seconds": round(self.elapsed, 2),
        }


def run_and_return(args, source_obj: dict) -> DebugResult:
    """调试入口（返回值模式，不调用 sys.exit）。

    与 run() 功能完全相同，但返回 DebugResult 而非 sys.exit()。
    供数据库闭环、Web API、AI 调试等需要获取返回值的场景使用。

    Args:
        args: Namespace 参数对象
        source_obj: 源对象字典

    Returns:
        DebugResult: 调试结果（含 collector、source_obj、confidence 等）
    """
    # ... 与 run() 相同的逻辑，但将所有 sys.exit() 替换为 return DebugResult ...
    # 成功: return DebugResult(success=True, confidence=confidence, ...)
    # 失败: return DebugResult(success=False, confidence="low", ...)
    # 异常: return DebugResult(success=False, confidence="unknown", ...)


def run(args, source_obj: dict) -> None:
    """调试入口（CLI 兼容模式，保留 sys.exit 行为）。

    内部调用 run_and_return()，根据结果调用 sys.exit()。
    保持向后兼容，现有 CLI 和脚本无需修改。
    """
    result = run_and_return(args, source_obj)
    if result.success:
        sys.exit(0)
    elif result.errors:
        sys.exit(1)
    else:
        sys.exit(2)
```

**后果**：

* (+) AI 闭环和 Web API 可获取完整调试结果

* (+) 向后兼容（run() 保留 sys.exit 行为）

* (-) 需要重构 run() 函数，将 sys.exit 替换为 return

* (-) 需要同步修改所有 sys.exit 调用点

***

### ADR-10: AI 调试闭环入口 — DebugOrchestrator

**上下文**：AI 调试闭环需要"查库→测试→修复→更新数据库"的完整流程，但现有 `debug_runner.run()` 是面向 CLI 的单次执行模式，不适合编排多步骤流程。

**决策**：新增 `DebugOrchestrator` 类，作为 AI 调试闭环的编排层。

**实现**：

```python
# legado_client/client/debug_orchestrator.py 新增

class DebugOrchestrator:
    """AI 调试闭环编排器

    编排"查库→测试→修复→更新数据库"完整流程。
    不替代 debug_runner，而是组合 debug_runner + storage + auto_fixer。
    """

    def __init__(self, storage_repo=None, jvm_pool=None, skip_db=False, db_only=False):
        self.storage = storage_repo  # StorageRepository 实例，None 时跳过数据库
        self.jvm_pool = jvm_pool    # JvmPool 实例（Web 模式）或 None（CLI 模式）
        self.skip_db = skip_db      # --skip-db-lookup
        self.db_only = db_only      # --db-only

    async def debug_with_db(self, source_obj: dict, source_type: str,
                             key: str, timeout: int = 30) -> dict:
        """AI 调试闭环主入口

        流程：
        1. 提取域名 → 查数据库
        2. 命中+测试通过 → 直接返回
        3. 命中+测试失败 → 取出源 → 测试 → 修复 → 重测 → 更新
        4. 未命中 → 正常调试 → 结果入库

        Returns:
            dict: {
                "hit": bool,           # 是否命中数据库
                "source": dict,        # 最终源对象
                "debug_result": DebugResult,
                "fix_applied": bool,   # 是否应用了自动修复
                "fix_detail": dict,    # 修复详情
                "db_updated": bool,    # 是否更新了数据库
            }
        """
        domain_key = extract_domain_key(
            source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")
        )
        result = {"hit": False, "source": source_obj, "fix_applied": False,
                  "fix_detail": None, "db_updated": False}

        # 步骤1: 查数据库
        if not self.skip_db and self.storage:
            try:
                existing = await self.storage.find_by_domain(domain_key, source_type)
                if existing:
                    result["hit"] = True
                    # 步骤2: 命中+测试通过 → 直接返回
                    passed = [s for s in existing if s.last_test_result == "pass"]
                    if passed and not self.db_only:
                        result["source"] = json.loads(passed[0].source_json)
                        result["debug_result"] = _cached_result(passed[0])
                        return result

                    # 步骤3: 命中+测试失败/未测试 → 取出源 → 测试
                    if self.db_only:
                        result["sources_from_db"] = [
                            {"id": s.id, "name": s.source_name,
                             "test_result": s.last_test_result}
                            for s in existing
                        ]
                        return result

                    # 取最新的源进行测试
                    latest = max(existing, key=lambda s: s.updated_at or datetime.min)
                    source_obj = json.loads(latest.source_json)
            except Exception as e:
                print(f"[WARN] 数据库查询失败，降级到文件模式: {e}")

        # 步骤4: JVM 测试
        debug_result = await self._run_debug(source_obj, source_type, key, timeout)
        result["debug_result"] = debug_result
        result["source"] = source_obj

        # 步骤5: 测试失败 → 自动修复
        if not debug_result.success and debug_result.errors:
            fix_result = self._try_auto_fix(source_obj, debug_result)
            if fix_result:
                result["fix_applied"] = True
                result["fix_detail"] = fix_result["detail"]
                result["source"] = fix_result["source"]

                # 修复后重测
                retest_result = await self._run_debug(
                    fix_result["source"], source_type, key, timeout
                )
                result["debug_result"] = retest_result
                if retest_result.success:
                    result["source"] = fix_result["source"]

        # 步骤6: 结果入库
        if self.storage and not self.skip_db:
            try:
                await self.storage.upsert_source(
                    source_type=source_type,
                    source_json=json.dumps(result["source"], ensure_ascii=False),
                    domain_key=domain_key,
                    test_result="pass" if result["debug_result"].success else "fail",
                    test_confidence=result["debug_result"].confidence,
                    test_detail=result["debug_result"].to_dict(),
                    fix_detail=result["fix_detail"],
                )
                result["db_updated"] = True
            except Exception as e:
                print(f"[WARN] 数据库更新失败: {e}")

        return result

    async def _run_debug(self, source_obj, source_type, key, timeout) -> 'DebugResult':
        """执行 JVM 调试（Web 模式用 JvmPool，CLI 模式用 run_and_return）"""
        if self.jvm_pool:
            # Web 模式：通过 JvmPool 异步调用
            source_json = json.dumps(source_obj, ensure_ascii=False)
            if source_type == "book":
                raw_result = await self.jvm_pool.debug_book_source(source_json, key)
            else:
                raw_result = await self.jvm_pool.debug_rss_source(source_json, key)
            return self._raw_to_debug_result(raw_result, source_obj)
        else:
            # CLI 模式：通过 run_and_return 同步调用
            args = _build_debug_args(source_obj, source_type, "all", timeout)
            return run_and_return(args, source_obj)

    def _try_auto_fix(self, source_obj, debug_result) -> dict | None:
        """尝试自动修复

        Returns:
            {"source": dict, "detail": dict} 或 None
        """
        from legado_client.analyzer.auto_fixer import auto_fix_error

        if not debug_result.errors:
            return None

        error = debug_result.errors[0]
        source_json = json.dumps(source_obj, ensure_ascii=False)
        html = None  # 从 debug_result.collector.html_sources 获取

        fix_result = auto_fix_error(error, source_json, html=html)

        if not fix_result.get("fixes_applied"):
            return None

        fixed_source = fix_result.get("fixed_source")
        if not fixed_source:
            return None

        # 构建修复详情
        detail = {
            "fixes_applied": fix_result.get("fixes_applied", []),
            "remaining_errors": fix_result.get("remaining_errors", []),
            "fix_count": len(fix_result.get("fixes_applied", [])),
            "timestamp": datetime.now().isoformat(),
        }

        return {"source": fixed_source, "detail": detail}
```

**后果**：

* (+) AI 闭环逻辑集中管理，不侵入现有 debug\_runner

* (+) 支持数据库降级（storage=None 时跳过数据库）

* (+) 支持 Web 模式（JvmPool）和 CLI 模式（run\_and\_return）

* (-) 新增一个编排层，增加少量复杂度

**上下文**：BookSource 有 40+ 字段，RssSource 有 30+ 字段。需要支持按关键字段查询，同时保留完整 JSON。

**决策**：搜索/筛选/排序关键字段拆分为独立列 + 原始 JSON 存储为 JSON 列。

**后果**：

* (+) 关键字段可索引查询

* (+) 完整 JSON 保留不丢失

* (-) 存在数据冗余

* (-) 更新时需同步两处

**缓解**：通过 Repository 层封装确保一致性；更新时同步更新独立列和 JSON 列。

***

### ADR-07: 密码安全 — 环境变量/.env 文件

**上下文**：MySQL 密码不应硬编码在源码中。

**决策**：使用 python-dotenv 加载 `.env` 文件，默认值为空字符串，必须通过环境变量或 `.env` 文件提供。

**实现**：

```python
# .env 文件（不提交到 Git）
LEGADO_DB_HOST=127.0.0.1
LEGADO_DB_PORT=3306
LEGADO_DB_USER=root
LEGADO_DB_PASSWORD=200868
LEGADO_DB_NAME=legado_sources

# config.py
from dotenv import load_dotenv
load_dotenv()

class Config:
    db_host: str = os.getenv("LEGADO_DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("LEGADO_DB_PORT", "3306"))
    db_user: str = os.getenv("LEGADO_DB_USER", "root")
    db_password: str = os.getenv("LEGADO_DB_PASSWORD", "")  # 默认空，必须配置
    db_name: str = os.getenv("LEGADO_DB_NAME", "legado_sources")
```

**后果**：

* (+) 密码不在源码中

* (+) 灵活配置

* (-) 需要额外创建 .env 文件

**缓解**：首次运行时自动生成 `.env.example` 模板文件。

***

### ADR-08: 数据库降级策略

**上下文**：MySQL 可能未启动或连接失败，系统不应因此完全不可用。

**决策**：数据库操作全部通过 `DatabaseHealthChecker` 包装，失败时自动降级。

**实现**：

```python
class DatabaseHealthChecker:
    _available: bool = True
    _last_check: float = 0
    _check_interval: float = 30.0  # 30秒重试一次

    @classmethod
    async def check(cls) -> bool:
        if not cls._available:
            if time.time() - cls._last_check > cls._check_interval:
                # 尝试重连
                cls._available = await cls._try_connect()
                cls._last_check = time.time()
        return cls._available

    @classmethod
    def mark_unavailable(cls):
        cls._available = False
        cls._last_check = time.time()
```

**降级行为**：

* AI 调试：跳过数据库查询，正常执行文件模式

* Web 服务：API 返回 503 + 降级提示

* CLI 命令：输出警告，继续文件模式

## Database Schema

### Source 表（统一存储 BookSource 和 RssSource）

```sql
CREATE TABLE source (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_type     ENUM('book', 'rss') NOT NULL,     -- 源类型
    -- 标识字段
    source_name     VARCHAR(200) NOT NULL,             -- bookSourceName / sourceName
    source_url      VARCHAR(500) NOT NULL,             -- bookSourceUrl / sourceUrl
    domain_key      VARCHAR(200) NOT NULL,             -- 标准化域名（去重+查询用）
    source_group    VARCHAR(500),                       -- bookSourceGroup / sourceGroup
    -- BookSource 特有字段（rss类型为NULL）
    book_source_type INT DEFAULT 0,                    -- 0文本/1音频/2图片/3文件/4视频（与Legado源码一致）
    -- 注意：content_type 已移除。BookSource 和 RssSource 的类型编码体系不同
    -- （BookSource: 0文本/1音频/2图片/3文件/4视频 vs RssSource: 0网页/1图片/2视频），
    -- 简单合并会导致同值不同义（如 content_type=1 在 book=音频，在 rss=图片）。
    -- 前端筛选时需按 source_type + book_source_type/rss_type 组合查询，
    -- API 层 SourceListRequest 已提供 book_source_type 和 rss_type 独立参数。
    enabled_explore  BOOLEAN DEFAULT TRUE,             -- 启用发现（BookSource 特有，RssSource 为 NULL）
    search_url      VARCHAR(1000),                     -- 搜索URL（BookSource 和 RssSource 均有此字段）
    explore_url     TEXT,                              -- 发现URL（BookSource 特有）
    explore_screen  TEXT,                              -- 发现筛选规则（BookSource 特有）
    book_url_pattern VARCHAR(500),                     -- 详情页URL正则（BookSource 特有）
    rule_search     TEXT,                              -- BookSource 搜索规则（ruleSearch JSON字符串）
    rule_book_info  TEXT,                              -- BookSource 书籍信息规则（ruleBookInfo JSON字符串）
    rule_toc        TEXT,                              -- BookSource 目录规则（ruleToc JSON字符串）
    rule_explore    TEXT,                              -- BookSource 发现规则（ruleExplore JSON字符串）
    rule_review     TEXT,                              -- BookSource 评论规则（ruleReview JSON字符串）
    -- RssSource 特有字段（book类型为NULL）
    rss_type        INT DEFAULT 0,                     -- 0网页/1图片/2视频
    sort_url        TEXT,                              -- 分类URL
    article_style   INT DEFAULT 0,                     -- 列表样式（0三图/1大图/2双排/3单图/4无图，RssSource.articleStyle）
    rule_articles   TEXT,                              -- RssSource 文章列表规则（ruleArticles，String 类型非 JSON）
    -- RssSource WebView/显示相关字段（book 类型为 NULL）
    rule_title      VARCHAR(500),                     -- 标题规则（RssSource 特有，高频查询）
    rule_image      VARCHAR(500),                     -- 图片规则（RssSource 特有）
    rule_link       VARCHAR(500),                     -- 链接规则（RssSource 特有）
    rule_next_page  VARCHAR(500),                     -- 下一页规则（RssSource 特有）
    rule_pub_date   VARCHAR(500),                     -- 发布日期规则（RssSource 特有）
    rule_description VARCHAR(500),                    -- 描述规则（RssSource 特有）
    single_url      BOOLEAN DEFAULT FALSE,             -- 单URL源
    -- 通用字段
    enabled         BOOLEAN DEFAULT TRUE,              -- 是否启用
    has_login       BOOLEAN DEFAULT FALSE,             -- 是否有登录URL
    login_url       VARCHAR(500),                      -- 登录地址
    login_ui        TEXT,                              -- 登录UI（BaseSource 接口字段，BookSource/RssSource 共有）
    login_check_js  TEXT,                              -- 登录检测JS（注意：源码字段名是 loginCheckJs，不是 loginCheckUrl）
    cover_decode_js TEXT,                              -- 封面解密JS
    rule_content    TEXT,                              -- 正文规则（BookSource ruleContent / RssSource ruleContent，JSON字符串）
    header          VARCHAR(500),                      -- 请求头
    concurrent_rate VARCHAR(50),                       -- 并发率
    last_update_time BIGINT DEFAULT 0,                 -- 源自身更新时间
    respond_time    BIGINT DEFAULT 180000,             -- 响应时间（默认 180000ms = 3分钟，RssSource 无此字段）
    weight          INT DEFAULT 0,                     -- 智能排序权重（RssSource 无此字段）
    custom_order    INT DEFAULT 0,                     -- 手动排序
    source_icon     VARCHAR(500),                      -- 图标URL（RssSource 有 sourceIcon，BookSource 无此字段）
    source_comment  TEXT,                              -- 注释
    variable_comment TEXT,                             -- 自定义变量说明
    enabled_cookie_jar BOOLEAN DEFAULT FALSE,          -- 启用CookieJar
    js_lib          TEXT,                              -- JS库
    event_listener  BOOLEAN DEFAULT FALSE,              -- 是否监听事件来执行回调规则（源码 BookSource.eventListener: Boolean）
    custom_button   BOOLEAN DEFAULT FALSE,              -- 由书源控制的自定义按钮（源码 BookSource.customButton: Boolean）
    notes           TEXT,                              -- 备注/修复经验摘要（AI闭环写入）
    -- 测试相关
    last_test_time  DATETIME,                          -- 最后测试时间
    last_test_result ENUM('pass', 'fail', 'timeout', 'untested') DEFAULT 'untested',
    test_mode       ENUM('jar', 'device', 'auto') DEFAULT 'auto',  -- 最后测试使用的模式
    test_confidence VARCHAR(20),                       -- high/medium/low/unverifiable
    test_detail     JSON,                              -- 各阶段测试结果详情
    device_jar_diff JSON,                              -- 真机vs JAR对比差异（仅对比测试时填充）
    fix_count       INT DEFAULT 0,                     -- 自动修复次数
    last_fix_detail JSON,                              -- 最近一次修复详情
    jar_optimization_count INT DEFAULT 0,              -- JAR 仿真优化次数
    last_jar_diff   DATETIME,                          -- 最近一次真机vs JAR差异时间
    -- 来源追踪
    collection_id   INT,                               -- 关联合集
    import_source   VARCHAR(50),                       -- 导入来源(yckceo/github/file/device/manual)
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- 完整 JSON
    source_json     JSON NOT NULL,                     -- 完整 BookSource/RssSource JSON

    INDEX idx_domain_key (domain_key),
    INDEX idx_source_type_result (source_type, last_test_result),
    INDEX idx_source_name (source_name),
    INDEX idx_source_group (source_group(191)),
    INDEX idx_book_source_type (book_source_type),        -- BookSource 按内容类型筛选
    INDEX idx_rss_type (rss_type),                        -- RssSource 按内容类型筛选
    INDEX idx_domain_name (domain_key, source_name),   -- 去重+查询组合索引
    FOREIGN KEY (collection_id) REFERENCES collection(id) ON DELETE SET NULL,  -- 合集删除时置NULL
    UNIQUE INDEX uk_domain_name_type (domain_key, source_name, source_type)  -- 去重唯一键
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Collection 表

```sql
CREATE TABLE collection (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    type            ENUM('book', 'rss') NOT NULL,
    remote_id       INT NOT NULL,                      -- yckceo.com 上的合集ID
    title           VARCHAR(200) NOT NULL,
    user            VARCHAR(100),
    source_count    INT DEFAULT 0,                     -- 合集声称的源数量
    actual_count    INT DEFAULT 0,                     -- 实际入库的源数量
    downloads       INT DEFAULT 0,
    date            VARCHAR(20),                       -- 上传日期
    fetched_at      DATETIME,                          -- 下载时间
    json_url        VARCHAR(500),                      -- JSON下载URL

    UNIQUE INDEX uk_remote_id_type (remote_id, type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### DebugResult 表

```sql
CREATE TABLE debug_result (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_id       INT NOT NULL,                      -- 关联source表
    `key`           VARCHAR(200),                      -- 调试使用的搜索关键词（书源搜索关键词/RSS源URL）
    trigger         ENUM('ai', 'web', 'cli') DEFAULT 'web',  -- 触发方式
    stage           VARCHAR(20),                       -- 失败阶段
    status          ENUM('pass', 'fail', 'timeout', 'error') NOT NULL,
    message         TEXT,                              -- 结果消息
    search_status   ENUM('pass', 'fail', 'skip') DEFAULT 'skip',
    detail_status   ENUM('pass', 'fail', 'skip') DEFAULT 'skip',
    toc_status      ENUM('pass', 'fail', 'skip') DEFAULT 'skip',
    content_status  ENUM('pass', 'fail', 'skip') DEFAULT 'skip',
    confidence      VARCHAR(20),                       -- 可信度
    test_mode       ENUM('jar', 'device', 'auto') DEFAULT 'auto',  -- 测试模式
    device_jar_diff JSON,                              -- 真机vs JAR对比差异（仅对比测试时填充）
    fix_applied     JSON,                              -- 应用的修复详情
    started_at      DATETIME,
    finished_at     DATETIME,
    duration_ms     INT,                               -- 耗时
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间

    INDEX idx_source_id (source_id),
    INDEX idx_status (status),
    FOREIGN KEY (source_id) REFERENCES source(id) ON DELETE CASCADE,  -- 级联删除
    INDEX idx_created_at (created_at)                  -- 按时间排序（调试历史）
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### DeviceConfig 表（真机连接配置）

> **注意**：Legado Web 服务的 HTTP 和 WebSocket 使用不同端口。
> 源码 `WebService.kt` 第167行：`webSocketServer = WebSocketServer(port + 1)`，
> 即 WebSocket 端口 = HTTP 端口 + 1（默认 HTTP:1122, WS:1123）。
> WebSocket URL 为 `ws://{ip}:{port+1}/{endpoint}`。

```sql
CREATE TABLE device_config (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,             -- 设备名称
    ip              VARCHAR(100) NOT NULL,             -- IP地址（与 API/Schema 字段名统一）
    port            INT DEFAULT 1122,                  -- Legado Web 服务 HTTP 端口
    -- WebSocket 端口 = port + 1（Legado 源码硬编码，无需独立字段）
    auth_token      VARCHAR(200),                      -- 认证token（Legado Web 验证码，当前版本未启用，预留）
    is_default      BOOLEAN DEFAULT FALSE,
    last_test_status VARCHAR(20),                     -- 最近连接测试结果（online/offline/error）
    last_sync_at    DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## API Design

### RESTful API 端点

#### 源管理

| 方法     | 路径                          | 说明                                   |
| ------ | --------------------------- | ------------------------------------ |
| GET    | `/api/sources`              | 源列表（分页+筛选+搜索）                        |
| GET    | `/api/sources/{id}`         | 源详情                                  |
| PUT    | `/api/sources/{id}`         | 更新源（JSON编辑）                          |
| DELETE | `/api/sources/{id}`         | 删除源                                  |
| PATCH  | `/api/sources/{id}/toggle`  | 启用/禁用切换                              |
| GET    | `/api/sources/by-domain`    | 按域名查询源列表（domain\_key 在 query）        |
| POST   | `/api/sources/batch-action` | 批量操作（test/export/delete/push/toggle） |
| GET    | `/api/sources/groups`       | 获取已有分组列表（去重，用于前端下拉选择）         |

#### 导入导出

| 方法   | 路径                          | 说明          |
| ---- | --------------------------- | ----------- |
| POST | `/api/import/url`           | URL 导入      |
| POST | `/api/import/file`          | 文件上传导入      |
| POST | `/api/import/github`        | GitHub 仓库导入 |
| POST | `/api/import/device`        | 从真机拉取       |
| POST | `/api/sources/{id}/export`  | 导出单个源 JSON  |
| POST | `/api/sources/batch-export` | 批量导出源 JSON  |

#### 合集管理

| 方法     | 路径                               | 说明       |
| ------ | -------------------------------- | -------- |
| GET    | `/api/collections`               | 合集列表     |
| GET    | `/api/collections/remote`        | 获取远程合集列表 |
| POST   | `/api/collections/{id}/download` | 下载指定合集   |
| POST   | `/api/collections/fetch-all`     | 全量获取     |
| POST   | `/api/collections/incremental`   | 增量更新     |
| DELETE | `/api/collections/{id}`          | 删除合集     |

#### 调试测试

| 方法   | 路径                    | 说明                                   |
| ---- | --------------------- | ------------------------------------ |
| POST | `/api/debug/start`    | 启动调试                                 |
| POST | `/api/debug/optimize` | 触发优化（测试失败→自动修复→重测，source\_id 在 body） |
| GET  | `/api/debug/status`   | 查询调试状态（task\_id 在 query）             |
| POST | `/api/debug/batch`    | 批量调试                                 |
| POST | `/api/debug/cancel`   | 取消调试（task\_id 在 body）                |
| GET  | `/api/debug/history`  | 调试历史                                 |
| WS   | `/ws/debug/{task_id}` | 调试日志实时推送                             |

#### 真机对接

| 方法     | 路径                       | 说明     |
| ------ | ------------------------ | ------ |
| GET    | `/api/devices`           | 设备列表   |
| POST   | `/api/devices`           | 添加设备   |
| PUT    | `/api/devices/{id}`      | 更新设备配置 |
| DELETE | `/api/devices/{id}`      | 删除设备   |
| POST   | `/api/devices/{id}/test` | 测试设备连接 |
| POST   | `/api/devices/{id}/push` | 推送源到设备 |
| POST   | `/api/devices/{id}/pull` | 从设备拉取源 |

#### 统计

| 方法  | 路径                        | 说明     |
| --- | ------------------------- | ------ |
| GET | `/api/stats/overview`     | 总览统计   |
| GET | `/api/stats/test-result`  | 测试结果分布 |
| GET | `/api/stats/group`        | 分组分布   |
| GET | `/api/stats/content-type` | 内容类型分布 |

#### 系统

| 方法  | 路径            | 说明           |
| --- | ------------- | ------------ |
| GET | `/api/health` | 健康检查（含数据库状态） |
| GET | `/api/config` | 获取配置信息       |

### WebSocket 消息格式

```json
// 调试日志推送
{"type": "log", "state": 10, "stage": "search", "message": "正在搜索...", "html": null}
// 调试错误
{"type": "error", "stage": "search", "message": "搜索结果为空", "stack_trace": null}
// 调试完成
{"type": "result", "success": false, "summary": {"search": "pass", "detail": "pass", "toc": "fail", "content": "untested"}}
// 修复通知
{"type": "fix", "fix_type": "css_selector", "description": "修复CSS选择器", "before": "...", "after": "..."}
// 批量进度
{"type": "batch_progress", "current": 5, "total": 20, "source_name": "xxx", "result": "pass"}
```

## Frontend Design

## 前端详细设计

### 全局布局

```
┌─────────────────────────────────────────────────────────┐
│  Logo  Legado Client 3.0          [数据库状态] [暗色切换] │  ← 顶栏 (64px)
├────────┬────────────────────────────────────────────────┤
│        │                                                │
│ 源管理  │              主内容区                           │
│  源列表  │                                                │
│ 合集    │                                                │
│ 导入    │                                                │
│ 测试    │                                                │
│ 真机    │                                                │
│ 统计    │                                                │
│        │                                                │
├────────┴────────────────────────────────────────────────┤
│  状态栏: 源总数 X | 通过率 X% | JVM: 空闲/忙碌           │  ← 底栏 (32px)
└─────────────────────────────────────────────────────────┘
```

* 侧边栏：可折叠，宽度 200px（展开）/ 64px（折叠）

* 顶栏：固定，含全局操作

* 底栏：固定，显示全局状态

### 路由与菜单映射

| 菜单   | 图标             | 路由                    | 组件                 | 说明                |
| ---- | -------------- | --------------------- | ------------------ | ----------------- |
| 源列表  | `List`         | `/admin/sources`      | `SourceListPage`   | 核心页面，源CRUD+搜索筛选   |
| 源详情  | -              | `/admin/sources/:id`  | `SourceDetailPage` | 源详情+编辑+测试（从列表页跳转） |
| 合集管理 | `FolderOpened` | `/admin/collections`  | `CollectionPage`   | yckceo 合集下载管理     |
| 源导入  | `Upload`       | `/admin/import`       | `ImportPage`       | 多渠道导入源            |
| 测试面板 | `Monitor`      | `/admin/debug`        | `DebugPage`        | 单源/批量测试+实时日志      |
| 真机管理 | `Cellphone`    | `/admin/devices`      | `DevicePage`       | Legado 真机推送/拉取    |
| 统计面板 | `DataAnalysis` | `/admin/stats`        | `StatsPage`        | 数据可视化             |
| Legado 原生 | `Reading` | `/legado/vue/#/`      | Legado 原生前端       | 书架/源编辑/阅读（iframe或代理）|

**共 8 个一级菜单，9 个路由（源详情为子路由，Legado 原生为外部集成路由）**

> **路由分区说明**：
> - `/admin/*`：管理扩展面板路由（Vue3 + Element Plus，Hash 模式）
> - `/legado/*`：Legado 原生前端路由（MPA + Vue3 Hash 路由，反向代理到真机 Web 服务或静态文件）**

### 页面一：源列表页 `/admin/sources`

**用途**：源管理的核心入口，查看/搜索/筛选/批量操作所有源

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ [搜索框____________] [类型▾] [内容类型▾] [测试结果▾] [分组▾] [重置] │  ← 筛选栏
├──────────────────────────────────────────────────────┤
│ ☐ | 名称 | URL | 类型 | 分组 | 测试结果 | 最后测试 | 启用 | 操作 │  ← 表头
│---|------|-----|------|------|---------|---------|-----|------│
│ ☐ | 笔趣阁 | bqg.cc | 书源 | 常用 | ✅通过 | 2h前 | ● | ⚙️📋🗑️│
│ ☐ | 知乎 | zhihu.com | 订阅 | - | ❌失败 | 1d前 | ● | ⚙️📋🗑️│
│ ☐ | ... | ... | ... | ... | ... | ... | ... | ...  │
├──────────────────────────────────────────────────────┤
│ 已选 3 项 [批量测试] [批量导出] [批量删除] [批量推送] [批量启用/禁用] │  ← 批量操作栏
├──────────────────────────────────────────────────────┤
│ 共 1234 条  < 1 2 3 ... 50 >  每页 [20▾] 条          │  ← 分页栏
└──────────────────────────────────────────────────────┘
```

#### 列定义

| 列    | 字段                           | 宽度    | 排序 | 说明                    |
| ---- | ---------------------------- | ----- | -- | --------------------- |
| 复选框  | -                            | 40px  | -  | 批量选择                  |
| 名称   | source\_name                 | 自适应   | ✅  | 点击跳转详情                |
| URL  | source\_url                  | 200px | -  | 显示域名，hover 显示完整 URL   |
| 类型   | source\_type                 | 80px  | ✅  | 标签：书源(蓝)/订阅(绿)        |
| 内容类型 | book\_source\_type/rss\_type | 80px  | -  | 标签：文本/音频/图片/视频        |
| 分组   | source\_group                | 120px | ✅  | 标签组                   |
| 测试结果 | last\_test\_result           | 100px | ✅  | 图标+文字：✅通过/❌失败/⏱超时/❓未测 |
| 最后测试 | last\_test\_time             | 120px | ✅  | 相对时间（2h前/1d前）         |
| 启用   | enabled                      | 80px  | -  | Switch 开关             |
| 操作   | -                            | 160px | -  | 测试/复制JSON/删除          |

#### 筛选器

| 筛选器  | 类型     | 选项                |
| ---- | ------ | ----------------- |
| 搜索框  | Input  | 按名称/URL 模糊搜索      |
| 类型   | Select | 全部/书源/订阅源         |
| 内容类型 | Select | 全部/文本/音频/图片/视频/文件 |
| 测试结果 | Select | 全部/通过/失败/超时/未测试   |
| 分组   | Select | 动态加载已有分组列表        |
| 有无登录 | Select | 全部/有登录/无登录        |

#### 批量操作

| 操作      | 图标           | API                              | 说明             |
| ------- | ------------ | -------------------------------- | -------------- |
| 批量测试    | `VideoPlay`  | `POST /api/debug/batch`          | 选中源排队测试        |
| 批量导出    | `Download`   | `POST /api/sources/batch-export` | 下载选中源的 JSON 文件 |
| 批量删除    | `Delete`     | `POST /api/sources/batch-action` | action=delete  |
| 批量推送    | `Cellphone`  | `POST /api/devices/{id}/push`    | 选择目标设备后推送      |
| 批量启用/禁用 | `Open/Close` | `POST /api/sources/batch-action` | action=toggle  |

#### 功能点清单

| #   | 功能      | 交互             | API                                      |
| --- | ------- | -------------- | ---------------------------------------- |
| F1  | 搜索      | 输入后 300ms 防抖搜索 | `GET /api/sources?search=xxx`            |
| F2  | 筛选      | 选择后立即刷新列表      | `GET /api/sources?source_type=book&test_result=fail` |
| F3  | 排序      | 点击列头切换升/降序     | `GET /api/sources?sort_by=name&sort_order=asc` |
| F4  | 分页      | 切换页码/每页条数      | `GET /api/sources?page=2&page_size=20`        |
| F5  | 启用/禁用   | 点击 Switch 切换   | `PATCH /api/sources/{id}/toggle`         |
| F6  | 复制 JSON | 点击后复制到剪贴板      | 前端 `navigator.clipboard`                 |
| F7  | 删除      | 确认弹窗后删除        | `DELETE /api/sources/{id}`               |
| F8  | 跳转详情    | 点击名称跳转         | 路由 `/sources/{id}`                       |
| F9  | 批量选择    | 全选/部分选         | 前端状态                                     |
| F10 | 批量操作    | 选中后显示操作栏       | 各批量 API                                  |

***

### 页面二：源详情页 `/admin/sources/:id`

**用途**：查看/编辑单个源的完整信息，执行测试和优化

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ ← 返回列表  |  笔趣阁 (bqg.cc)  |  [测试] [优化] [导出] [推送] [删除] │  ← 顶栏
├──────────────────────────────────────────────────────┤
│ ┌─ 基本信息 ──────────────────────────────────────┐  │
│ │ 名称: 笔趣阁    URL: https://www.bqg.cc         │  │
│ │ 类型: 书源(文本)  分组: 常用  启用: [●]          │  │
│ │ 最后测试: 2h前   可信度: high   修复次数: 0      │  │
│ └─────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│ ┌─ 测试结果 ──────────────────────────────────────┐  │
│ │ 搜索 ✅ → 详情 ✅ → 目录 ✅ → 正文 ✅            │  │
│ │ 可信度: high  耗时: 3.2s                         │  │
│ └─────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│ [JSON 编辑] [测试历史] [同域名源]                      │  ← Tab 切换
├──────────────────────────────────────────────────────┤
│ ┌─ Tab: JSON 编辑 ────────────────────────────────┐  │
│ │ {                                                │  │
│ │   "bookSourceName": "笔趣阁",                    │  │
│ │   "bookSourceUrl": "https://www.bqg.cc",         │  │
│ │   ...                                            │  │
│ │ }                                                │  │
│ │                           [格式化] [保存] [重置]  │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ Tab: 测试历史 ────────────────────────────────┐  │
│ │ 2026-06-24 14:30  ✅通过  high  3.2s  [查看日志] │  │
│ │ 2026-06-23 10:15  ❌失败  low   1.1s  [查看日志] │  │
│ │   └ 修复: CSS选择器修正 class.list→.book-list    │  │
│ │ 2026-06-22 09:00  ❌失败  low   0.8s  [查看日志] │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ Tab: 同域名源 ────────────────────────────────┐  │
│ │ 笔趣阁2  ✅通过  [切换到此源]                    │  │
│ │ 笔趣阁3  ❌失败  [切换到此源]                    │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### Tab 页定义

| Tab     | 组件           | 说明                   |
| ------- | ------------ | -------------------- |
| JSON 编辑 | `CodeMirror` | JSON 语法高亮+编辑+格式化+保存  |
| 测试历史    | `Timeline`   | 按时间倒序显示测试记录，含修复记录    |
| 同域名源    | `Table`      | 同 domain\_key 的其他源列表 |

#### 操作按钮

| 按钮 | 图标           | API                             | 说明         |
| -- | ------------ | ------------------------------- | ---------- |
| 测试 | `VideoPlay`  | `POST /api/debug/start`         | 启动 JVM 调试  |
| 优化 | `MagicStick` | `POST /api/debug/optimize`      | 测试+自动修复+重测 |
| 导出 | `Download`   | `POST /api/sources/{id}/export` | 下载单个源 JSON |
| 推送 | `Cellphone`  | `POST /api/devices/{id}/push`   | 选择设备后推送    |
| 删除 | `Delete`     | `DELETE /api/sources/{id}`      | 确认弹窗后删除    |

#### 功能点清单

| #   | 功能       | 交互            | API                                     |
| --- | -------- | ------------- | --------------------------------------- |
| F1  | JSON 编辑  | CodeMirror 编辑 | 前端状态                                    |
| F2  | JSON 格式化 | 点击格式化按钮       | 前端 `JSON.parse+stringify`               |
| F3  | JSON 保存  | 点击保存按钮        | `PUT /api/sources/{id}`                 |
| F4  | JSON 重置  | 点击重置按钮        | 恢复原始值                                   |
| F5  | 启动测试     | 点击测试按钮        | `POST /api/debug/start`                 |
| F6  | 启动优化     | 点击优化按钮        | `POST /api/debug/optimize`              |
| F7  | 查看测试日志   | 点击历史记录的"查看日志" | `GET /api/debug/history?source_id={id}` |
| F8  | 切换同域名源   | 点击"切换到此源"     | 路由跳转                                    |
| F9  | 推送到真机    | 选择设备弹窗        | `POST /api/devices/{id}/push`           |
| F10 | 导出 JSON  | 下载文件          | `POST /api/sources/{id}/export`         |

***

### 页面三：合集管理页 `/admin/collections`

**用途**：管理 yckceo.com 书源/订阅源合集的下载和更新

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ [书源▾] [获取远程列表] [全量获取] [增量更新]              │  ← 操作栏
├──────────────────────────────────────────────────────┤
│ 标题 | 用户 | 源数量 | 下载量 | 日期 | 状态 | 操作      │  ← 表头
│------|------|--------|--------|------|------|--------│
│ 746书源合集 | 张三 | 746 | 12.3k | 06-20 | ✅已下载 | [更新][删除] │
│ 精选100源 | 李四 | 100 | 8.5k | 06-18 | ⬇未下载 | [下载] │
│ ...  | ...  | ...   | ...   | ...  | ...  | ...    │
├──────────────────────────────────────────────────────┤
│ 共 87 条  < 1 2 3 ... 9 >  每页 [10▾] 条              │  ← 分页
└──────────────────────────────────────────────────────┘
```

#### 列定义

| 列   | 字段              | 宽度    | 排序 | 说明                      |
| --- | --------------- | ----- | -- | ----------------------- |
| 标题  | title           | 自适应   | ✅  | 合集标题                    |
| 用户  | user            | 100px | -  | 上传用户                    |
| 源数量 | source\_count   | 80px  | ✅  | 合集内源数量                  |
| 下载量 | downloads       | 80px  | ✅  | 下载次数                    |
| 日期  | date            | 120px | ✅  | 上传日期                    |
| 状态  | status          | 100px | -  | 已下载(绿)/未下载(灰)/下载中(蓝+进度) |
| 操作  | -               | 160px | -  | 下载/更新/删除                |

#### 功能点清单

| #  | 功能     | 交互            | API                                   |
| -- | ------ | ------------- | ------------------------------------- |
| F1 | 获取远程列表 | 点击按钮，显示加载状态   | `GET /api/collections/remote`         |
| F2 | 全量获取   | 确认弹窗后逐个下载     | `POST /api/collections/fetch-all`     |
| F3 | 增量更新   | 仅下载新增/更新的合集   | `POST /api/collections/incremental`   |
| F4 | 下载单个合集 | 点击下载按钮        | `POST /api/collections/{id}/download` |
| F5 | 更新合集   | 重新下载并覆盖       | `POST /api/collections/{id}/download` |
| F6 | 删除合集   | 确认弹窗后删除       | `DELETE /api/collections/{id}`        |
| F7 | 类型切换   | 书源/订阅源 Tab 切换 | `GET /api/collections?source_type=book/rss`  |
| F8 | 进度显示   | 下载中显示进度条      | WebSocket progress 消息                 |

***

### 页面四：源导入页 `/admin/import`

**用途**：从多种渠道导入源到数据库

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ ┌─ URL 导入 ──────────────────────────────────────┐  │
│ │ [输入 JSON URL________________________] [导入]   │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ 文件上传 ──────────────────────────────────────┐  │
│ │ ┌─────────────────────────────────────────────┐  │  │
│ │ │         拖拽 JSON 文件到此处                  │  │  │
│ │ │         或 [点击选择文件]                     │  │  │
│ │ └─────────────────────────────────────────────┘  │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ GitHub 导入 ───────────────────────────────────┐  │
│ │ [输入仓库 URL________________________] [导入]     │  │
│ │ 示例: https://github.com/xxx/legado-source       │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ 真机同步 ──────────────────────────────────────┐  │
│ │ 设备: [选择设备▾]  类型: [书源▾]  [拉取]         │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ 导入结果 ──────────────────────────────────────┐  │
│ │ ✅ 新增: 120   ⏭️ 跳过(已存在): 30   ❌ 失败: 5  │  │
│ │ 失败详情:                                       │  │
│ │   - source_xxx.json: JSON 格式错误              │  │
│ │   - source_yyy.json: 字段缺失                   │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### 功能点清单

| #  | 功能        | 交互              | API                       |
| -- | --------- | --------------- | ------------------------- |
| F1 | URL 导入    | 输入 URL → 点击导入   | `POST /api/import/url`    |
| F2 | 文件上传      | 拖拽/选择文件 → 自动上传  | `POST /api/import/file`   |
| F3 | GitHub 导入 | 输入仓库 URL → 点击导入 | `POST /api/import/github` |
| F4 | 真机拉取      | 选择设备+类型 → 点击拉取  | `POST /api/import/device` |
| F5 | 导入结果展示    | 导入完成后显示统计       | API 返回结果                  |
| F6 | 失败详情      | 展开失败列表          | API 返回结果                  |

***

### 页面五：测试面板页 `/admin/debug`

**用途**：执行源测试/优化，查看实时日志和历史记录

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ [单源测试] [批量测试] [优化测试]                         │  ← Tab 切换
├──────────────────────────────────────────────────────┤
│ ┌─ Tab: 单源测试 ─────────────────────────────────┐  │
│ │ 源: [搜索选择源▾]  阶段: [全部▾]  [开始测试]     │  │
│ │ ┌─ 实时日志 ──────────────────────────────────┐ │  │
│ │ │ [14:30:01] 🔍 搜索阶段开始...                │ │  │
│ │ │ [14:30:02] ✅ 搜索到 5 本书                  │ │  │
│ │ │ [14:30:03] 📖 详情阶段开始...                │ │  │
│ │ │ [14:30:04] ✅ 详情页解析成功                  │ │  │
│ │ │ [14:30:05] 📑 目录阶段开始...                │ │  │
│ │ │ [14:30:06] ✅ 获取到 120 章                  │ │  │
│ │ │ [14:30:07] 📄 正文阶段开始...                │ │  │
│ │ │ [14:30:08] ✅ 正文获取成功                    │ │  │
│ │ │                                              │ │  │
│ │ │ ── 测试结果 ──────────────────────────────   │ │  │
│ │ │ ✅ 通过  可信度: high  耗时: 7.2s            │ │  │
│ │ └──────────────────────────────────────────────┘ │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ Tab: 批量测试 ─────────────────────────────────┐  │
│ │ 选择: [全部源▾] [测试失败的源▾] [指定分组▾]       │  │
│ │ [开始测试] [取消]                                 │  │
│ │ ┌─ 进度 ──────────────────────────────────────┐ │  │
│ │ │ ████████████░░░░░░░░ 60/100  5/10 通过      │ │  │
│ │ └──────────────────────────────────────────────┘ │  │
│ │ ┌─ 结果列表 ──────────────────────────────────┐ │  │
│ │ │ 笔趣阁  ✅通过  3.2s                         │ │  │
│ │ │ 知乎    ❌失败  1.1s  [优化]                  │ │  │
│ │ │ ...                                          │ │  │
│ │ └──────────────────────────────────────────────┘ │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ Tab: 优化测试 ─────────────────────────────────┐  │
│ │ 选择: [测试失败的源]  [开始优化]                  │  │
│ │ ┌─ 优化结果 ──────────────────────────────────┐ │  │
│ │ │ 笔趣阁  修复: CSS选择器修正  ✅重测通过       │ │  │
│ │ │   ┌ diff ─────────────────────────────────┐  │ │  │
│ │ │   │ - "ruleBookList": ".list"             │  │ │  │
│ │ │   │ + "ruleBookList": ".book-list"        │  │ │  │
│ │ │   └───────────────────────────────────────┘  │ │  │
│ │ │ 知乎  修复: URL模板修正  ❌重测仍失败         │ │  │
│ │ └──────────────────────────────────────────────┘ │  │
│ └─────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│ ┌─ 测试历史 ──────────────────────────────────────┐  │
│ │ 最近 20 条测试记录（时间/源名/结果/耗时/操作）    │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### 功能点清单

| #  | 功能         | 交互                    | API                            |
| -- | ---------- | --------------------- | ------------------------------ |
| F1 | 单源测试       | 选择源+阶段 → 开始测试         | `POST /api/debug/start`        |
| F2 | 实时日志       | WebSocket 推送          | `ws://host/ws/debug/{task_id}` |
| F3 | 批量测试       | 选择范围 → 开始 → 进度条       | `POST /api/debug/batch`        |
| F4 | 批量进度       | WebSocket progress 消息 | 同上                             |
| F5 | 取消测试       | 点击取消按钮                | `POST /api/debug/cancel`       |
| F6 | 优化测试       | 选择失败源 → 自动修复+重测       | `POST /api/debug/optimize`     |
| F7 | 修复 diff 展示 | 展开修复详情                | API 返回 fix\_detail             |
| F8 | 测试历史       | 底部列表                  | `GET /api/debug/history`       |
| F9 | 查看历史日志     | 点击记录查看                | WebSocket 重放 / 日志详情弹窗          |

***

### 页面六：真机管理页 `/admin/devices`

**用途**：管理 Legado 真机设备，推送/拉取源

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ [添加设备]                                             │  ← 操作栏
├──────────────────────────────────────────────────────┤
│ ┌─ 设备卡片 ──────────────────────────────────────┐  │
│ │ 📱 我的小米手机                    [编辑] [删除] │  │
│ │ IP: 192.168.1.100:1122  认证: auth_token        │  │
│ │ 状态: ✅已连接  最后同步: 2026-06-24 10:30       │  │
│ │ [测试连接] [推送源] [拉取源]                      │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ 设备卡片 ──────────────────────────────────────┐  │
│ │ 📱 我的华为平板                    [编辑] [删除] │  │
│ │ IP: 192.168.1.101:1122  认证: 无                │  │
│ │ 状态: ❌不可达  最后同步: -                       │  │
│ │ [测试连接] [推送源] [拉取源]                      │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### 添加/编辑设备弹窗

| 字段       | 类型          | 必填 | 说明                     |
| -------- | ----------- | -- | ---------------------- |
| 设备名称     | Input       | 是  | 自定义名称                  |
| IP 地址    | Input       | 是  | 如 192.168.1.100        |
| 端口       | InputNumber | 是  | 默认 1122                |
| 认证 Token | Input       | 否  | Legado Web 验证码，留空表示无认证 |

#### 功能点清单

| #  | 功能   | 交互        | API                           |
| -- | ---- | --------- | ----------------------------- |
| F1 | 添加设备 | 弹窗表单      | `POST /api/devices`           |
| F2 | 编辑设备 | 弹窗表单      | `PUT /api/devices/{id}`       |
| F3 | 删除设备 | 确认弹窗      | `DELETE /api/devices/{id}`    |
| F4 | 测试连接 | 点击按钮，显示结果 | `POST /api/devices/{id}/test` |
| F5 | 推送源  | 弹窗选择源+类型  | `POST /api/devices/{id}/push` |
| F6 | 拉取源  | 选择类型+确认   | `POST /api/devices/{id}/pull` |

***

### 页面七：统计面板页 `/admin/stats`

**用途**：数据可视化，展示源的整体状况

#### 布局

```
┌──────────────────────────────────────────────────────┐
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                 │
│ │ 1234 │ │ 78%  │ │ 890  │ │ 344  │                 │  ← 概览卡片
│ │ 源总数│ │通过率 │ │ 书源 │ │ 订阅 │                 │
│ └──────┘ └──────┘ └──────┘ └──────┘                 │
├──────────────────────────────────────────────────────┤
│ ┌─ 测试结果分布 ──────┐ ┌─ 内容类型分布 ──────────┐  │
│ │    🟢 通过 78%      │ │  文本 ████████ 650      │  │
│ │    🔴 失败 15%      │ │  音频 ███      120      │  │
│ │    🟡 超时  5%      │ │  图片 ██        80      │  │
│ │    ⚪ 未测  2%      │ │  视频 █         44      │  │
│ │   (饼图)            │ │  (横向柱状图)           │  │
│ └─────────────────────┘ └─────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│ ┌─ 分组分布 ──────────────────────────────────────┐  │
│ │ 常用   ████████████████  450                     │  │
│ │ 网文   ██████████        300                     │  │
│ │ 漫画   ██████            180                     │  │
│ │ 其他   ████              120                     │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### 功能点清单

| #  | 功能      | 交互            | API                           |
| -- | ------- | ------------- | ----------------------------- |
| F1 | 概览卡片    | 页面加载时获取       | `GET /api/stats/overview`     |
| F2 | 测试结果饼图  | ECharts 饼图    | `GET /api/stats/test-result`  |
| F3 | 内容类型柱状图 | ECharts 横向柱状图 | `GET /api/stats/content-type` |
| F4 | 分组分布    | ECharts 横向柱状图 | `GET /api/stats/group`        |

***

### 全局组件

| 组件               | 用途                  | 复用页面      |
| ---------------- | ------------------- | --------- |
| `SourceSelect`   | 源搜索选择器（远程搜索+下拉）     | 测试面板、推送弹窗 |
| `DeviceSelect`   | 设备选择器               | 推送弹窗、导入页  |
| `JsonEditor`     | CodeMirror JSON 编辑器 | 源详情页      |
| `DebugLogPanel`  | 实时日志面板（WebSocket）   | 测试面板、源详情页 |
| `ProgressDialog` | 进度弹窗（批量操作）          | 合集页、测试面板  |
| `ConfirmDialog`  | 确认弹窗（删除等危险操作）       | 全局        |
| `ResultSummary`  | 导入/导出结果统计           | 导入页       |

***

### 前端技术规范

| 项目        | 选型                | 说明                                 |
| --------- | ----------------- | ---------------------------------- |
| 框架        | Vue 3.4+          | Composition API + `<script setup>` |
| 构建        | Vite 5            | 开发热更新+生产构建                         |
| UI 库      | Element Plus 2.5+ | 表格/表单/弹窗/标签/开关等                    |
| 图表        | ECharts 5         | 饼图/柱状图                             |
| JSON 编辑   | CodeMirror 6      | 语法高亮+编辑+格式化                        |
| 路由        | Vue Router 4      | Hash 模式（兼容静态文件部署）                  |
| 状态        | Pinia             | 全局状态（设备列表/JVM状态等）                  |
| HTTP      | Axios             | API 请求                             |
| WebSocket | 原生 WebSocket      | 调试日志推送                             |

### 前端状态管理（Pinia Stores）

| Store         | 状态               | 说明     |
| ------------- | ---------------- | ------ |
| `sourceStore` | 筛选条件/分页/选中项      | 源列表页状态 |
| `debugStore`  | task\_id/日志列表/进度 | 测试面板状态 |
| `deviceStore` | 设备列表/选中设备        | 真机管理状态 |
| `appStore`    | 数据库状态/JVM状态/暗色模式 | 全局状态   |

***

### 前端功能点汇总

| 页面     | 功能点数   | P0     | P1     | P2    |
| ------ | ------ | ------ | ------ | ----- |
| 源列表页   | 10     | 10     | 0      | 0     |
| 源详情页   | 10     | 8      | 2      | 0     |
| 合集管理页  | 8      | 6      | 2      | 0     |
| 源导入页   | 6      | 5      | 1      | 0     |
| 测试面板页  | 9      | 8      | 1      | 0     |
| 真机管理页  | 6      | 5      | 1      | 0     |
| 统计面板页  | 4      | 1      | 3      | 0     |
| **合计** | **53** | **43** | **10** | **0** |

### 前端组件文件结构

```
legado_client/web/src/
├── App.vue
├── main.ts
├── router/
│   └── index.ts              ← 7 个路由定义
├── stores/
│   ├── source.ts
│   ├── debug.ts
│   ├── device.ts
│   └── app.ts
├── api/
│   ├── sources.ts            ← 源管理 API
│   ├── collections.ts        ← 合集 API
│   ├── debug.ts              ← 调试 API
│   ├── import.ts             ← 导入 API
│   ├── device.ts             ← 真机 API
│   └── stats.ts              ← 统计 API
├── components/
│   ├── SourceSelect.vue      ← 源搜索选择器
│   ├── DeviceSelect.vue      ← 设备选择器
│   ├── JsonEditor.vue        ← JSON 编辑器
│   ├── DebugLogPanel.vue     ← 实时日志面板
│   ├── ProgressDialog.vue    ← 进度弹窗
│   └── ResultSummary.vue     ← 结果统计
├── views/
│   ├── SourceListPage.vue    ← 源列表页
│   ├── SourceDetailPage.vue  ← 源详情页
│   ├── CollectionPage.vue    ← 合集管理页
│   ├── ImportPage.vue        ← 源导入页
│   ├── DebugPage.vue         ← 测试面板页
│   ├── DevicePage.vue        ← 真机管理页
│   └── StatsPage.vue         ← 统计面板页
├── layouts/
│   └── MainLayout.vue        ← 侧边栏+顶栏+底栏
└── styles/
    └── variables.scss         ← Element Plus 主题变量
```

## 前端架构重构设计（覆盖原 Frontend Design）

> **核心变更**：原前端设计从零构建 SPA，现改为复用 Legado 已有的 Vue3 前端 + 新增管理扩展面板。以下内容覆盖原有 `## Frontend Design` 和 `## 前端详细设计` 章节。

### 前端架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                     Legado Client 前端架构                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              管理扩展面板 (Vue3 + Element Plus)              ││
│  │  端口: 8080 (FastAPI 直接服务)                               ││
│  │  路由: /admin/*                                             ││
│  │  功能: 源列表管理/合集管理/导入导出/统计/真机管理/测试面板      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Legado 原生前端 (Vue3 + TypeScript + Element Plus) ││
│  │  集成方式: 反向代理（推荐）或 iframe                          ││
│  │  路由: /legado/*                                            ││
│  │  功能: 书架/阅读/源编辑器/源调试面板                           ││
│  │  API代理: /legado/* → LegadoWebClient → 真机 :1122/:1123    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Legado 原生前端集成方案

**Legado 已有前端能力**（源码位于 Legado 项目 `app/src/main/assets/web/` 目录）：

> **重要**：Legado 前端是 **MPA（多页面应用）** 结构，不是单一 SPA。
> - `index.html`：导航首页
> - `vue/index.html`：Vue3 SPA 入口（使用 **Hash 路由**，如 `#/bookSource`、`#/rssSource`）
> - `uploadBook/index.html`：WiFi 传书页面（独立页面，jQuery）
> - `help/`：帮助文档目录
>
> Vue3 SPA 的路由使用 `createWebHashHistory`（Hash 模式），不是 History 模式。
> 这意味着所有 Vue 路由都在 `vue/index.html#/` 下，无需服务端路由回退。

**Legado Vue3 SPA 页面路由**（Hash 模式）：

| Hash 路由 | 组件 | 功能 |
|-----------|------|------|
| `#/` | `BookShelf.vue` | 书架展示 |
| `#/bookSource` | `SourceEditor.vue` | 书源编辑器（含 JSON 编辑+调试面板） |
| `#/rssSource` | `SourceEditor.vue` | RSS 编辑器（同组件，不同数据源） |

**关键组件**：
- `SourceEditor.vue`：源编辑+JSON编辑+调试面板，功能完整
- `SourceDebug.vue`：WebSocket 调试面板，连接 `ws://{host}:{port}/bookSourceDebug`
- 前端 baseURL 优先级：`VITE_API` > `localStorage.remoteUrl` > `location.origin`

**集成方式**：反向代理（推荐）

```python
# legado_client/server/app.py

# Legado 原生前端：通过反向代理集成
# 前端构建产物放在 web/legado-frontend/ 目录（保持 MPA 原始结构）
# API 请求通过 /legado/ 前缀代理到真机 Legado Web 服务

LEGADO_WEB_DIR = Path(__file__).parent.parent / "web" / "legado-frontend"
if LEGADO_WEB_DIR.exists():
    # 挂载静态资源目录（保持 MPA 结构）
    # index.html → 导航首页
    # vue/ → Vue3 SPA（Hash 路由，无需服务端回退）
    # uploadBook/ → WiFi 传书页面
    # help/ → 帮助文档
    app.mount("/legado", StaticFiles(directory=LEGADO_WEB_DIR, html=True), name="legado_frontend")
```

**为什么选反向代理而非 iframe**：
- 反向代理：前后端同域，无跨域问题；API 请求自动走代理；URL 统一管理
- iframe：跨域问题需额外处理；通信需 postMessage；调试体验差
- 降级方案：如反向代理有问题，可退回 iframe 方案（`<iframe src="http://{device_ip}:1122/">`）

**MPA 集成注意事项**：
1. 使用 `StaticFiles(html=True)` 确保 `index.html` 自动解析
2. Vue3 SPA 使用 Hash 路由，无需配置 SPA 回退（所有路由在 `#/` 后）
3. API 代理需拦截 `/legado/` 前缀的非静态文件请求，转发到 LegadoWebClient
4. WebSocket 代理路径：`/ws/legado/*` → Legado 设备 `ws://{ip}:{port}/*`

### 管理扩展面板路由变更

原设计路由从 `/sources` 改为 `/admin/sources`，新增 Legado 原生前端路由 `/legado/*`：

| 菜单 | 图标 | 路由 | 说明 |
|------|------|------|------|
| 源列表 | `List` | `/admin/sources` | 源CRUD+搜索筛选 |
| 源详情 | - | `/admin/sources/:id` | 源详情+编辑+测试+真机vs JAR对比 |
| 合集管理 | `FolderOpened` | `/admin/collections` | yckceo 合集下载管理 |
| 源导入 | `Upload` | `/admin/import` | 多渠道导入源 |
| 测试面板 | `Monitor` | `/admin/debug` | 单源/批量测试+实时日志+真机/JAR对比 |
| 真机管理 | `Cellphone` | `/admin/devices` | Legado 真机推送/拉取/调试 |
| 统计面板 | `DataAnalysis` | `/admin/stats` | 数据可视化 |
| ──── | ──── | ──── | ──── |
| Legado 书架 | `Reading` | `/legado/vue/#/` | Legado 原生书架页面（MPA+Hash路由） |
| Legado 源编辑 | `Edit` | `/legado/vue/#/bookSource` | Legado 原生书源编辑器 |
| Legado RSS编辑 | `Edit` | `/legado/vue/#/rssSource` | Legado 原生RSS源编辑器 |
| Legado 传书 | `Upload` | `/legado/uploadBook/` | WiFi 传书页面 |

### 源详情页新增 Tab：真机 vs JAR 对比

在原有 3 个 Tab（JSON 编辑/测试历史/同域名源）基础上新增第 4 个 Tab：

| Tab | 组件 | 说明 |
|-----|------|------|
| 真机vs JAR对比 | `DeviceJarDiffTable` | 真机测试结果与 JAR 仿真结果的逐阶段对比 |

对比表格结构：

| 阶段 | 真机结果 | JAR结果 | 差异说明 |
|------|---------|---------|---------|
| 搜索 | ✅通过 | ✅通过 | - |
| 详情 | ✅通过 | ❌失败 | JAR缺少XXX功能 |
| 目录 | ✅通过 | ⏭跳过 | 详情失败无法继续 |
| 正文 | ✅通过 | ⏭跳过 | 详情失败无法继续 |

底部操作：`[触发JAR优化闭环]` → `POST /api/debug/jar-optimize`

### 测试面板页新增 Tab：真机 vs JAR 对比

在原有 3 个 Tab（单源测试/批量测试/优化测试）基础上新增第 4 个 Tab：

- 选择源 → 运行对比测试（同时触发真机调试和 JAR 仿真）
- 展示对比结果表格
- 差异行高亮，提供"触发JAR优化闭环"操作

### 管理面板前端文件结构

```
legado_client/web/admin/src/
├── App.vue
├── main.ts
├── router/
│   └── index.ts              ← 管理面板路由（/admin/*）
├── stores/
│   ├── source.ts
│   ├── debug.ts              ← 新增 test_mode 字段（auto/device/jar）
│   ├── device.ts             ← 新增 default_device 字段
│   └── app.ts                ← 新增 device_online 字段
├── api/
│   ├── sources.ts
│   ├── collections.ts
│   ├── debug.ts              ← 新增 compare/jar-optimize API
│   ├── import.ts
│   ├── device.ts
│   ├── stats.ts              ← 新增 test-mode 统计 API
│   └── legado-proxy.ts       ← [新增] Legado Web 代理 API
├── components/
│   ├── SourceSelect.vue
│   ├── DeviceSelect.vue
│   ├── JsonEditor.vue
│   ├── DebugLogPanel.vue
│   ├── ProgressDialog.vue
│   ├── ResultSummary.vue
│   └── DeviceJarDiffTable.vue ← [新增] 真机vs JAR对比表格
├── views/
│   ├── SourceListPage.vue
│   ├── SourceDetailPage.vue  ← 新增"真机vs JAR对比"Tab
│   ├── CollectionPage.vue
│   ├── ImportPage.vue
│   ├── DebugPage.vue         ← 新增"真机vs JAR对比"Tab + 测试方式选择
│   ├── DevicePage.vue        ← 新增"打开Legado前端"按钮 + WS端口配置
│   └── StatsPage.vue         ← 新增"测试方式分布"图表
├── layouts/
│   └── MainLayout.vue        ← 侧边栏新增"Legado前端"菜单项
└── styles/
    └── variables.scss

legado_client/web/legado-frontend/
└── dist/                      ← Legado 原生前端构建产物（直接复用）
    ├── index.html
    └── assets/
```

***

## LegadoWebClient 设计

> **核心变更**：将原有简单的 `legado_client.py`（仅 push/pull/test_connection）重构为完整的 Legado Web 服务客户端，封装 26 个 HTTP API + 3 个 WebSocket API。

### 文件位置

`legado_client/device/legado_web_client.py`

### Legado Web 服务 API 清单

#### HTTP API（端口 1122，26 个端点）

**书源相关**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/getBookSources` | GET | 获取所有书源 | - |
| `/getBookSource` | GET | 获取单个书源 | `?url=xxx` |
| `/saveBookSource` | POST | 保存单个书源 | Body: BookSource JSON |
| `/saveBookSources` | POST | 批量保存书源 | Body: BookSource[] JSON |
| `/deleteBookSources` | POST | 批量删除书源 | Body: BookSource[] JSON |

**RSS源相关**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/getRssSources` | GET | 获取所有RSS源 | - |
| `/getRssSource` | GET | 获取单个RSS源 | `?url=xxx` |
| `/saveRssSource` | POST | 保存单个RSS源 | Body: RssSource JSON |
| `/saveRssSources` | POST | 批量保存RSS源 | Body: RssSource[] JSON |
| `/deleteRssSources` | POST | 批量删除RSS源 | Body: RssSource[] JSON |

**书籍相关**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/getBookshelf` | GET | 获取书架 | - |
| `/getChapterList` | GET | 获取章节列表 | `?url=xxx` |
| `/getBookContent` | GET | 获取正文内容 | `?url=xxx&index=0` |
| `/saveBook` | POST | 保存书籍 | Body: Book JSON |
| `/deleteBook` | POST | 删除书籍 | Body: Book JSON |

**替换规则**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/getReplaceRules` | GET | 获取所有替换规则 | - |
| `/saveReplaceRule` | POST | 保存替换规则 | Body: ReplaceRule JSON |
| `/deleteReplaceRule` | POST | 删除替换规则 | Body: ReplaceRule JSON |
| `/testReplaceRule` | POST | 测试替换规则 | Body: ReplaceRule JSON |

**书籍进度与配置**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/saveBookProgress` | POST | 保存阅读进度 | Body: Book JSON（含 durChapterTitle/durChapterIndex/durChapterPos） |
| `/addLocalBook` | POST | 添加本地书籍 | multipart: parameters + files（特殊参数格式，非标准 JSON） |
| `/saveReadConfig` | POST | 保存阅读配置 | Body: ReadConfig JSON |
| `/getReadConfig` | GET | 获取阅读配置 | - |

**书籍刷新与图片**：

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/refreshToc` | GET | 刷新目录 | `?url=xxx` |
| `/cover` | GET | 获取封面图片 | `?url=xxx`（返回 Bitmap/PNG，非 JSON） |
| `/image` | GET | 获取图片 | `?url=xxx`（返回 Bitmap/PNG，非 JSON） |

> **注意**：`/cover` 和 `/image` 返回的是二进制图片数据（Bitmap → PNG），
> 不是 JSON。LegadoWebClient 中这两个方法需要特殊处理（返回 bytes 而非 dict）。
> `/addLocalBook` 使用 multipart form-data 而非 JSON，参数格式特殊。

**统一响应格式**：`{isSuccess: bool, errorMsg: string, data: any}`

#### WebSocket API（独立端口，3 个端点）

> **重要**：Legado Web 服务的 HTTP 和 WebSocket 使用不同端口。
> 源码 `WebService.kt` 第167行：`webSocketServer = WebSocketServer(port + 1)`，
> 即 WebSocket 端口 = HTTP 端口 + 1（默认 HTTP:1122, WS:1123）。
> WebSocket URL 格式为 `ws://{host}:{http_port+1}/{endpoint}`。

| 端点 | 说明 | 发送消息 | 接收消息 | 结束标志 |
|------|------|---------|---------|---------|
| `/searchBook` | 书籍搜索 | `{key: "关键词"}` | JSON 数组 `SearchBook[]`（逐批） | WebSocket 关闭帧 |
| `/bookSourceDebug` | 书源调试 | `{tag: "bookSourceUrl", key: "搜索词"}` | **纯文本**调试日志（逐行） | WebSocket 关闭帧 |
| `/rssSourceDebug` | RSS源调试 | `{tag: "sourceUrl"}` | **纯文本**调试日志（逐行） | WebSocket 关闭帧 |

> **协议注意**：调试 WebSocket 返回的是**纯文本**日志（非 JSON），调试结束通过
> WebSocket 关闭帧表示（非 JSON 字段）。搜索 WebSocket 返回 JSON 数组。
> 详见源码 `BookSourceDebugWebSocket.printLog()` 和 `BookSearchWebSocket.onSearchSuccess()`。

### LegadoWebClient 类设计

```python
# legado_client/device/legado_web_client.py

class LegadoWebClient:
    """Legado Web 服务完整客户端

    封装 Legado 的 26 个 HTTP API + 3 个 WebSocket API。
    支持认证、连接测试、源推送/拉取、源调试、书籍搜索。

    重要：Legado Web 服务的 HTTP 和 WebSocket 使用不同端口。
    WebSocket 端口 = HTTP 端口 + 1（源码 WebService.kt 第167行硬编码）。
    默认 HTTP:1122, WS:1123。
    """

    def __init__(self, host: str, port: int = 1122,
                 auth_token: str = ""):
        """
        Args:
            host: Legado 设备 IP
            port: Legado Web 服务 HTTP 端口（WebSocket 端口 = port + 1）
            auth_token: 认证 token（当前 Legado 版本未启用 HTTP 认证，预留字段）
        """
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port + 1}"  # WebSocket 端口 = HTTP端口 + 1
        self.auth_token = auth_token
        self._http_client: httpx.AsyncClient | None = None

    # === 响应解析 ===

    def _parse_response(self, resp: httpx.Response) -> dict:
        """解析 Legado ReturnData 响应格式

        Legado 统一响应格式：{isSuccess: bool, errorMsg: str, data: any}
        所有 HTTP API 均返回此格式，需提取 data 字段获取实际数据。
        """
        if resp.status_code != 200:
            return {"isSuccess": False, "errorMsg": f"HTTP {resp.status_code}", "data": None}
        try:
            result = resp.json()
            if isinstance(result, dict) and "isSuccess" in result:
                return result
            # 兼容非标准响应
            return {"isSuccess": True, "errorMsg": "", "data": result}
        except Exception as e:
            return {"isSuccess": False, "errorMsg": str(e), "data": None}

    # === 连接管理 ===

    async def test_connection(self) -> dict:
        """测试设备连接

        Returns:
            {"connected": bool, "auth_required": bool, "source_count": int}
        """
        try:
            resp = await self._get("/getBookSources")
            if resp.status_code == 200:
                result = self._parse_response(resp)
                if result.get("isSuccess"):
                    data = result.get("data", [])
                    source_count = len(data) if isinstance(data, list) else 0
                    return {"connected": True, "auth_required": False,
                            "source_count": source_count}
                return {"connected": True, "auth_required": False, "source_count": 0}
            elif resp.status_code == 401:
                return {"connected": True, "auth_required": True, "source_count": 0}
            return {"connected": False, "auth_required": False, "source_count": 0}
        except Exception:
            return {"connected": False, "auth_required": False, "source_count": 0}

    # === 书源 API ===

    async def get_book_sources(self) -> list[dict]:
        """获取所有书源"""
        resp = await self._get("/getBookSources")
        result = self._parse_response(resp)
        return result.get("data", []) if result.get("isSuccess") else []

    async def get_book_source(self, url: str) -> dict | None:
        """获取单个书源"""
        resp = await self._get(f"/getBookSource?url={url}")
        result = self._parse_response(resp)
        return result.get("data") if result.get("isSuccess") else None

    async def save_book_source(self, source: dict) -> bool:
        """保存单个书源"""
        resp = await self._post("/saveBookSource", json=source)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def save_book_sources(self, sources: list[dict]) -> bool:
        """批量保存书源"""
        resp = await self._post("/saveBookSources", json=sources)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def delete_book_sources(self, sources: list[dict]) -> bool:
        """批量删除书源"""
        resp = await self._post("/deleteBookSources", json=sources)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    # === RSS源 API ===

    async def get_rss_sources(self) -> list[dict]:
        """获取所有RSS源"""
        resp = await self._get("/getRssSources")
        result = self._parse_response(resp)
        return result.get("data", []) if result.get("isSuccess") else []

    async def get_rss_source(self, url: str) -> dict | None:
        """获取单个RSS源"""
        resp = await self._get(f"/getRssSource?url={url}")
        result = self._parse_response(resp)
        return result.get("data") if result.get("isSuccess") else None

    async def save_rss_source(self, source: dict) -> bool:
        """保存单个RSS源"""
        resp = await self._post("/saveRssSource", json=source)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def save_rss_sources(self, sources: list[dict]) -> bool:
        """批量保存RSS源"""
        resp = await self._post("/saveRssSources", json=sources)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def delete_rss_sources(self, sources: list[dict]) -> bool:
        """批量删除RSS源"""
        resp = await self._post("/deleteRssSources", json=sources)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    # === 书籍 API ===

    async def get_bookshelf(self) -> list[dict]:
        """获取书架"""
        resp = await self._get("/getBookshelf")
        result = self._parse_response(resp)
        return result.get("data", []) if result.get("isSuccess") else []

    async def get_chapter_list(self, url: str) -> list[dict]:
        """获取章节列表"""
        resp = await self._get(f"/getChapterList?url={url}")
        result = self._parse_response(resp)
        return result.get("data", []) if result.get("isSuccess") else []

    async def get_book_content(self, url: str, index: int = 0) -> str:
        """获取正文内容"""
        resp = await self._get(f"/getBookContent?url={url}&index={index}")
        result = self._parse_response(resp)
        return result.get("data", "") if result.get("isSuccess") else ""

    async def save_book(self, book: dict) -> bool:
        """保存书籍"""
        resp = await self._post("/saveBook", json=book)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def delete_book(self, book: dict) -> bool:
        """删除书籍"""
        resp = await self._post("/deleteBook", json=book)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    # === 替换规则 API ===

    async def get_replace_rules(self) -> list[dict]:
        """获取所有替换规则"""
        resp = await self._get("/getReplaceRules")
        result = self._parse_response(resp)
        return result.get("data", []) if result.get("isSuccess") else []

    async def save_replace_rule(self, rule: dict) -> bool:
        """保存替换规则"""
        resp = await self._post("/saveReplaceRule", json=rule)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def delete_replace_rule(self, rule: dict) -> bool:
        """删除替换规则"""
        resp = await self._post("/deleteReplaceRule", json=rule)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def test_replace_rule(self, rule: dict) -> dict:
        """测试替换规则"""
        resp = await self._post("/testReplaceRule", json=rule)
        result = self._parse_response(resp)
        return result.get("data", {}) if result.get("isSuccess") else {}

    # === 书籍进度与配置 API ===

    async def save_book_progress(self, book: dict) -> bool:
        """保存阅读进度

        Args:
            book: Book JSON（含 durChapterTitle/durChapterIndex/durChapterPos）
        """
        resp = await self._post("/saveBookProgress", json=book)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def add_local_book(self, parameters: dict, files: dict) -> bool:
        """添加本地书籍

        注意：此端点使用 multipart form-data 而非 JSON。
        参数格式特殊，非标准 JSON body。

        Args:
            parameters: 参数字典
            files: 文件字典
        """
        client = await self._get_http_client()
        resp = await client.post(
            "/addLocalBook",
            data=parameters,
            files=files,
        )
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def save_read_config(self, config: dict) -> bool:
        """保存阅读配置

        Args:
            config: ReadConfig JSON
        """
        resp = await self._post("/saveReadConfig", json=config)
        result = self._parse_response(resp)
        return result.get("isSuccess", False)

    async def get_read_config(self) -> dict:
        """获取阅读配置"""
        resp = await self._get("/getReadConfig")
        result = self._parse_response(resp)
        return result.get("data", {}) if result.get("isSuccess") else {}

    # === 书籍刷新与图片 API ===

    async def refresh_toc(self, url: str) -> dict:
        """刷新目录

        Args:
            url: 书籍URL
        """
        resp = await self._get(f"/refreshToc?url={url}")
        result = self._parse_response(resp)
        return result.get("data", {}) if result.get("isSuccess") else {}

    async def get_cover(self, url: str) -> bytes | None:
        """获取封面图片

        注意：返回二进制 PNG 数据，非 JSON。
        源码 HttpServer.kt: 当 returnData.data 是 Bitmap 时，
        压缩为 PNG 后返回 image/png 响应。

        Args:
            url: 封面图片URL

        Returns:
            PNG 图片字节数据，失败返回 None
        """
        client = await self._get_http_client()
        resp = await client.get(f"/cover?url={url}")
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            return resp.content
        return None

    async def get_image(self, url: str) -> bytes | None:
        """获取图片

        注意：同 get_cover，返回二进制 PNG 数据，非 JSON。

        Args:
            url: 图片URL

        Returns:
            PNG 图片字节数据，失败返回 None
        """
        client = await self._get_http_client()
        resp = await client.get(f"/image?url={url}")
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            return resp.content
        return None

    # === WebSocket API ===

    async def ws_search_book(self, key: str,
                              on_result=None, on_complete=None) -> list[dict]:
        """书籍搜索（WebSocket）

        协议：发送 {"key":"关键词"}，接收 JSON 数组（SearchBook[]），
        搜索完成通过 WebSocket 关闭帧表示（非 JSON 字段）。
        详见源码 BookSearchWebSocket.onSearchSuccess() / onSearchFinish()。
        """
        results = []
        try:
            async with websockets.connect(f"{self.ws_url}/searchBook") as ws:
                await ws.send(json.dumps({"key": key}))
                async for message in ws:
                    # 消息是 JSON 数组：SearchBook[]
                    try:
                        batch = json.loads(message)
                        if isinstance(batch, list):
                            results.extend(batch)
                            if on_result:
                                await on_result(batch)
                    except json.JSONDecodeError:
                        pass  # 忽略非 JSON 消息
        except websockets.ConnectionClosed:
            pass  # 正常关闭，搜索完成
        if on_complete:
            await on_complete(results)
        return results

    async def ws_book_source_debug(self, tag: str, key: str,
                                     on_log=None, on_complete=None) -> dict:
        """书源调试（WebSocket）

        协议：发送 {"tag":"bookSourceUrl","key":"搜索词"}，
        接收纯文本调试日志（非 JSON），调试结束通过 WebSocket 关闭帧表示。
        状态码：-1=错误结束, 1000=正常结束。
        详见源码 BookSourceDebugWebSocket.printLog()。
        """
        logs = []
        try:
            async with websockets.connect(f"{self.ws_url}/bookSourceDebug") as ws:
                await ws.send(json.dumps({"tag": tag, "key": key}))
                async for message in ws:
                    # 消息是纯文本调试日志，不是 JSON
                    logs.append(message)
                    if on_log:
                        await on_log(message)
        except websockets.ConnectionClosed:
            pass  # 正常关闭，调试结束
        result = self._parse_debug_logs(logs)
        if on_complete:
            await on_complete(result)
        return result

    async def ws_rss_source_debug(self, tag: str,
                                    on_log=None, on_complete=None) -> dict:
        """RSS源调试（WebSocket）

        协议：发送 {"tag":"sourceUrl"}，
        接收纯文本调试日志（非 JSON），调试结束通过 WebSocket 关闭帧表示。
        详见源码 RssSourceDebugWebSocket.printLog()。
        """
        logs = []
        try:
            async with websockets.connect(f"{self.ws_url}/rssSourceDebug") as ws:
                await ws.send(json.dumps({"tag": tag}))
                async for message in ws:
                    logs.append(message)
                    if on_log:
                        await on_log(message)
        except websockets.ConnectionClosed:
            pass  # 正常关闭，调试结束
        result = self._parse_debug_logs(logs)
        if on_complete:
            await on_complete(result)
        return result

    # === 代理方法（供 FastAPI legado_proxy 路由使用）===
    # 注意：以下方法需要 FastAPI 的 Request 和 WebSocket 类型，
    # 在实际模块中通过 from fastapi import Request, WebSocket 导入，
    # LegadoWebClient 本身不直接依赖 FastAPI，代理方法仅在 Web 服务模式下使用。

    async def proxy_request(self, path: str, request: "Request") -> dict:
        """代理 HTTP 请求到 Legado Web 服务"""
        method = request.method.lower()
        if method == "get":
            resp = await self._get(f"/{path}", params=dict(request.query_params))
        else:
            body = await request.body()
            resp = await self._post(f"/{path}", content=body)
        return resp.json()

    async def proxy_websocket(self, websocket: WebSocket, endpoint: str):
        """代理 WebSocket 连接到 Legado Web 服务"""
        await websocket.accept()
        async with websockets.connect(f"{self.ws_url}/{endpoint}") as ws:
            # 双向转发
            async def forward_to_legado():
                while True:
                    data = await websocket.receive_text()
                    await ws.send(data)

            async def forward_to_client():
                while True:
                    data = await ws.recv()
                    await websocket.send_text(data)

            await asyncio.gather(forward_to_legado(), forward_to_client(),
                                 return_exceptions=True)

    # === 内部方法 ===

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            # 注意：当前 Legado Web 服务版本（截至 2026-06）不支持 HTTP 认证，
            # HttpServer.kt / WebSocketServer.kt 无 Authorization 校验逻辑。
            # 此 header 不会被服务端校验，预留用于未来版本。
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=30
            )
        return self._http_client

    async def _get(self, path: str, params: dict = None) -> httpx.Response:
        client = await self._get_http_client()
        return await client.get(path, params=params)

    async def _post(self, path: str, json=None, content=None) -> httpx.Response:
        client = await self._get_http_client()
        return await client.post(path, json=json, content=content)

    def _parse_debug_logs(self, logs: list[str]) -> dict:
        """解析纯文本调试日志，提取各阶段结果

        Legado 调试日志格式：每行纯文本，包含时间戳和阶段信息。
        示例："[00:01.234] 开始搜索..." / "[00:02.345] 搜索到 3 个结果"
        注意：日志是纯文本而非 JSON，需通过关键词匹配判断阶段和结果。
        详见源码 BookSourceDebugWebSocket.printLog() — send(msg)。
        """
        stages = {"search": "untested", "detail": "untested",
                  "toc": "untested", "content": "untested"}
        for log_line in logs:
            # 根据日志文本关键词判断阶段
            if "搜索" in log_line or "search" in log_line.lower():
                if "搜索到" in log_line or "成功" in log_line:
                    stages["search"] = "pass"
                elif "失败" in log_line or "错误" in log_line:
                    stages["search"] = "fail"
            elif "详情" in log_line or "信息" in log_line:
                if "成功" in log_line:
                    stages["detail"] = "pass"
                elif "失败" in log_line:
                    stages["detail"] = "fail"
            elif "目录" in log_line or "章节" in log_line:
                if "成功" in log_line:
                    stages["toc"] = "pass"
                elif "失败" in log_line:
                    stages["toc"] = "fail"
            elif "正文" in log_line or "内容" in log_line:
                if "成功" in log_line:
                    stages["content"] = "pass"
                elif "失败" in log_line:
                    stages["content"] = "fail"
        success = all(v == "pass" for v in stages.values() if v != "untested")
        return {"success": success, "stages": stages, "raw_logs": logs}

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
```

### LegadoWebClient 在 DebugOrchestrator 中的使用

```python
# DebugOrchestrator 新增方法

async def _run_device_debug(self, source_obj: dict, source_type: str,
                              key: str) -> 'DebugResult':
    """通过 LegadoWebClient 执行真机调试

    流程：
    1. 获取默认设备的 LegadoWebClient
    2. 推送源到真机
    3. 通过 WebSocket 调试
    4. 解析调试结果
    """
    client = self._get_default_legado_client()
    if not client:
        raise RuntimeError("未配置真机设备")

    source_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")

    # 推送源到真机
    if source_type == "book":
        await client.save_book_source(source_obj)
    else:
        await client.save_rss_source(source_obj)

    # WebSocket 调试
    if source_type == "book":
        result = await client.ws_book_source_debug(tag=source_url, key=key)
    else:
        result = await client.ws_rss_source_debug(tag=source_url)

    # 转换为 DebugResult
    return self._device_result_to_debug_result(result, source_obj)

async def _check_device_available(self) -> bool:
    """检查真机是否可用"""
    client = self._get_default_legado_client()
    if not client:
        return False
    result = await client.test_connection()
    if not result.get("connected", False):
        return False
    # 需要认证但未配置 token → 不可用
    if result.get("auth_required", False) and not client.auth_token:
        return False
    return True

    async def _get_default_legado_client(self) -> LegadoWebClient | None:
    """获取默认设备的 LegadoWebClient"""
    if not self.storage:
        return None
    # 从数据库获取默认设备配置（异步查询）
    device = await self.storage.get_default_device()
    if not device:
        return None
    return LegadoWebClient(
        host=device.ip,
        port=device.port,  # HTTP 端口；WebSocket 端口 = port + 1（LegadoWebClient 内部自动计算）
        auth_token=device.auth_token or ""
    )
```

***

## JAR 优化闭环设计

> **核心变更**：新增 JAR 优化闭环模块。当真机测试通过但 JAR 仿真失败时，自动分析差异、定位 JAR 缺失功能、修复 JAR 代码、回归验证。

### 文件位置

`legado_client/analyzer/jar_optimizer.py`

### JarOptimizer 类设计

```python
# legado_client/analyzer/jar_optimizer.py

class JarOptimizer:
    """JAR 仿真优化闭环

    当真机测试通过但 JAR 仿真失败时：
    1. 记录差异：真机结果 vs JAR 结果
    2. 分析 Legado 源码中对应功能的实现
    3. 定位 JAR 仿真缺失的功能
    4. 修改 JAR Java 代码补齐功能
    5. 重新构建 JAR
    6. 回归测试验证
    """

    def __init__(self, legado_source_dir: str = None, jar_project_dir: str = None):
        """
        Args:
            legado_source_dir: Legado 源码目录（用于分析缺失功能）
            jar_project_dir: legado-jvm 项目目录（用于修改和构建 JAR）
        """
        self.legado_source_dir = legado_source_dir
        self.jar_project_dir = jar_project_dir

    async def optimize(self, device_result: dict, jar_result: dict,
                        source_obj: dict) -> dict:
        """JAR 优化闭环主入口

        Args:
            device_result: 真机调试结果（DebugResult.to_dict()）
            jar_result: JAR 仿真调试结果（DebugResult.to_dict()）
            source_obj: 源对象

        Returns:
            {
                "diff_found": bool,
                "diff_detail": dict,          # 差异详情
                "source_analysis": dict,       # Legado 源码分析结果
                "jar_fix_applied": bool,       # 是否修复了 JAR
                "jar_fix_detail": dict,        # JAR 修复详情
                "regression_passed": bool,     # 回归测试是否通过
                "coverage_change": float,      # 覆盖率变化
            }
        """
        result = {
            "diff_found": False, "diff_detail": None,
            "source_analysis": None, "jar_fix_applied": False,
            "jar_fix_detail": None, "regression_passed": False,
            "coverage_change": 0.0,
        }

        # 步骤1: 记录差异
        diff = self._compare_results(device_result, jar_result)
        if not diff["has_diff"]:
            return result
        result["diff_found"] = True
        result["diff_detail"] = diff

        # 步骤2: 分析 Legado 源码
        if self.legado_source_dir:
            analysis = self._analyze_legado_source(diff, source_obj)
            result["source_analysis"] = analysis

        # 步骤3: 修改 JAR Java 代码（需要人工确认或 AI 辅助）
        if self.jar_project_dir and result["source_analysis"]:
            fix_result = await self._fix_jar(result["source_analysis"], diff)
            result["jar_fix_applied"] = fix_result["applied"]
            result["jar_fix_detail"] = fix_result

            # 步骤4: 重新构建 JAR
            if fix_result["applied"]:
                build_ok = await self._rebuild_jar()
                if build_ok:
                    # 步骤5: 回归测试（由调用方执行）
                    result["regression_passed"] = False  # 待回归测试后更新

        return result

    def _compare_results(self, device_result: dict, jar_result: dict) -> dict:
        """对比真机结果和 JAR 结果

        Returns:
            {
                "has_diff": bool,
                "stages": {
                    "search": {"device": "pass", "jar": "pass", "diff": False},
                    "detail": {"device": "pass", "jar": "fail", "diff": True,
                               "device_detail": "...", "jar_detail": "..."},
                    ...
                },
                "failed_stages": ["detail", "toc", "content"],
            }
        """
        stages = {}
        failed_stages = []
        for stage in ["search", "detail", "toc", "content"]:
            d_status = device_result.get("stages", {}).get(stage, "untested")
            j_status = jar_result.get("stages", {}).get(stage, "untested")
            has_diff = d_status != j_status
            stages[stage] = {
                "device": d_status,
                "jar": j_status,
                "diff": has_diff,
            }
            if has_diff:
                failed_stages.append(stage)
        return {
            "has_diff": len(failed_stages) > 0,
            "stages": stages,
            "failed_stages": failed_stages,
        }

    def _analyze_legado_source(self, diff: dict, source_obj: dict) -> dict:
        """分析 Legado 源码，定位 JAR 缺失功能

        策略：
        1. 根据失败阶段，确定涉及的 Legado 类
        2. 搜索 Legado 源码中对应类的实现
        3. 对比 JAR 仿真代码，找出缺失部分
        4. 生成差异分析报告

        Returns:
            {
                "missing_classes": [...],
                "missing_methods": [...],
                "missing_features": [...],
                "analysis_report": str,
            }
        """
        # 阶段 → Legado 类映射（基于源码实际类名）
        # 源码路径：app/src/main/java/io/legado/app/
        stage_class_map = {
            "search": ["model/webBook/WebBook", "model/webBook/BookList"],
            "detail": ["model/webBook/WebBook", "model/webBook/BookInfo"],
            "toc": ["model/webBook/WebBook", "model/webBook/BookChapterList"],
            "content": ["model/webBook/WebBook", "model/webBook/BookContent"],
        }
        # 通用依赖类（所有阶段都可能涉及）
        common_classes = [
            "data/entities/BookSource",           # BookSource 实体
            "data/entities/rule/SearchRule",      # 搜索规则
            "data/entities/rule/BookInfoRule",    # 书籍信息规则
            "data/entities/rule/BookListRule",    # 搜索列表规则（接口，非 data class）
            "data/entities/rule/TocRule",          # 目录规则（data class，对应 BookSource.ruleToc）
            "data/entities/rule/ContentRule",      # 正文规则（data class，对应 BookSource.ruleContent）
            "model/analyzeRule/AnalyzeRule",      # 核心规则引擎
            "model/analyzeRule/AnalyzeUrl",       # URL 解析
            "model/webBook/BookModel",            # Book 数据模型
        ]

        missing = {"missing_classes": [], "missing_methods": [],
                    "missing_features": [], "analysis_report": ""}

        for stage in diff.get("failed_stages", []):
            classes = stage_class_map.get(stage, [])
            missing["missing_classes"].extend(classes)

        # 生成分析报告（AI 辅助或模板化）
        missing["analysis_report"] = (
            f"JAR 仿真在以下阶段与真机结果不一致: {diff.get('failed_stages', [])}\n"
            f"可能缺失的 Legado 类: {missing['missing_classes']}\n"
            f"建议检查 legado-jvm 项目中这些类的实现完整性。"
        )

        return missing

    async def _fix_jar(self, analysis: dict, diff: dict) -> dict:
        """修改 JAR Java 代码

        注意：此步骤可能需要人工确认或 AI 辅助，不自动执行。
        生成修复建议和代码补丁，由开发者审核后应用。

        Returns:
            {"applied": bool, "patches": [...], "report": str}
        """
        return {
            "applied": False,
            "patches": [],
            "report": f"基于分析结果，建议修复以下类: {analysis.get('missing_classes', [])}。"
                       "请开发者审核后手动应用修复。"
        }

    async def _rebuild_jar(self) -> bool:
        """重新构建 JAR

        在 jar_project_dir 中执行 mvn package

        Returns:
            构建是否成功
        """
        if not self.jar_project_dir:
            return False
        # 执行构建命令
        # result = subprocess.run(["mvn", "package", "-f", self.jar_project_dir], ...)
        # return result.returncode == 0
        return False  # 需要实际实现
```

### JAR 优化闭环触发流程

```
真机测试通过 → JAR 仿真验证 → JAR 失败
    ↓
DebugOrchestrator 检测到差异
    ↓
1. 调用 JarOptimizer.optimize(device_result, jar_result, source_obj)
2. JarOptimizer._compare_results() → 记录差异
3. JarOptimizer._analyze_legado_source() → 分析源码
4. JarOptimizer._fix_jar() → 生成修复建议（需人工确认）
5. 人工确认后 → _rebuild_jar() → 重新构建
6. 回归测试 → 验证修复有效
    ↓
更新 JAR 覆盖率报告
```

### 数据库新增字段支持 JAR 优化闭环

在 `debug_result` 表新增字段：

```sql
ALTER TABLE debug_result ADD COLUMN test_mode ENUM('device', 'jar', 'auto') DEFAULT 'auto';
ALTER TABLE debug_result ADD COLUMN device_jar_diff JSON COMMENT '真机vs JAR对比差异';
```

在 `source` 表新增字段：

```sql
ALTER TABLE source ADD COLUMN jar_optimization_count INT DEFAULT 0 COMMENT 'JAR优化次数';
ALTER TABLE source ADD COLUMN last_jar_diff JSON COMMENT '最近一次真机vs JAR差异';
```

***

## Legado Web 服务代理 API 端点规范

> **新增**：FastAPI 代理路由，将 Legado 原生前端的请求转发到真机 Legado Web 服务。

### 文件位置

`legado_client/server/routes/legado_proxy.py`

### HTTP 代理端点

| 方法 | 路径 | 说明 | 代理目标 |
|------|------|------|---------|
| GET | `/legado/getBookSources` | 获取所有书源 | `GET /getBookSources` |
| GET | `/legado/getBookSource` | 获取单个书源 | `GET /getBookSource?url=xxx` |
| POST | `/legado/saveBookSource` | 保存单个书源 | `POST /saveBookSource` |
| POST | `/legado/saveBookSources` | 批量保存书源 | `POST /saveBookSources` |
| POST | `/legado/deleteBookSources` | 批量删除书源 | `POST /deleteBookSources` |
| GET | `/legado/getRssSources` | 获取所有RSS源 | `GET /getRssSources` |
| GET | `/legado/getRssSource` | 获取单个RSS源 | `GET /getRssSource?url=xxx` |
| POST | `/legado/saveRssSource` | 保存单个RSS源 | `POST /saveRssSource` |
| POST | `/legado/saveRssSources` | 批量保存RSS源 | `POST /saveRssSources` |
| POST | `/legado/deleteRssSources` | 批量删除RSS源 | `POST /deleteRssSources` |
| GET | `/legado/getBookshelf` | 获取书架 | `GET /getBookshelf` |
| GET | `/legado/getChapterList` | 获取章节列表 | `GET /getChapterList?url=xxx` |
| GET | `/legado/getBookContent` | 获取正文内容 | `GET /getBookContent?url=xxx&index=0` |
| POST | `/legado/saveBook` | 保存书籍 | `POST /saveBook` |
| POST | `/legado/deleteBook` | 删除书籍 | `POST /deleteBook` |
| GET | `/legado/getReplaceRules` | 获取替换规则 | `GET /getReplaceRules` |
| POST | `/legado/saveReplaceRule` | 保存替换规则 | `POST /saveReplaceRule` |
| POST | `/legado/deleteReplaceRule` | 删除替换规则 | `POST /deleteReplaceRule` |
| POST | `/legado/testReplaceRule` | 测试替换规则 | `POST /testReplaceRule` |
| POST | `/legado/saveBookProgress` | 保存阅读进度 | `POST /saveBookProgress` |
| POST | `/legado/addLocalBook` | 添加本地书籍 | `POST /addLocalBook`（multipart） |
| POST | `/legado/saveReadConfig` | 保存阅读配置 | `POST /saveReadConfig` |
| GET | `/legado/getReadConfig` | 获取阅读配置 | `GET /getReadConfig` |
| GET | `/legado/refreshToc` | 刷新目录 | `GET /refreshToc?url=xxx` |
| GET | `/legado/cover` | 获取封面图片 | `GET /cover?url=xxx`（返回 image/png） |
| GET | `/legado/image` | 获取图片 | `GET /image?url=xxx`（返回 image/png） |

### WebSocket 代理端点

| 方法 | 路径 | 说明 | 代理目标 |
|------|------|------|---------|
| WS | `/ws/legado/searchBook` | 书籍搜索 | `WS /searchBook` |
| WS | `/ws/legado/bookSourceDebug` | 书源调试 | `WS /bookSourceDebug` |
| WS | `/ws/legado/rssSourceDebug` | RSS源调试 | `WS /rssSourceDebug` |

### 代理路由实现

```python
# legado_client/server/routes/legado_proxy.py

from fastapi import APIRouter, Request, WebSocket
from legado_client.device.legado_web_client import LegadoWebClient

router = APIRouter(prefix="/legado", tags=["legado-proxy"])

def _get_client() -> LegadoWebClient | None:
    """获取默认设备的 LegadoWebClient（从 app.state 获取）"""
    # 实现从数据库获取默认设备配置并创建客户端
    ...

# HTTP 代理：通用路由
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_legado_http(path: str, request: Request):
    """代理 Legado HTTP API 请求到真机"""
    client = _get_client()
    if not client:
        return {"isSuccess": False, "errorMsg": "未配置真机设备"}
    return await client.proxy_request(path, request)

# WebSocket 代理
@router.websocket("/ws/{endpoint}")
async def proxy_legado_ws(websocket: WebSocket, endpoint: str):
    """代理 Legado WebSocket 请求到真机"""
    client = _get_client()
    if not client:
        await websocket.close(code=4001, reason="未配置真机设备")
        return
    await client.proxy_websocket(websocket, endpoint)
```

### 新增调试 API 端点

在原有调试 API 基础上新增：

| 方法 | 路径 | 请求 | 响应 | 说明 |
|------|------|------|------|------|
| POST | `/api/debug/compare` | `{source_id: int, key: str}` | `{task_id: str, device_result: dict, jar_result: dict, diff: dict}` | 真机vs JAR对比测试 |
| POST | `/api/debug/jar-optimize` | `{source_id: int}` | `{ok: bool, diff_found: bool, jar_fix_applied: bool}` | 触发 JAR 优化闭环 |

### 新增统计 API 端点

| 方法 | 路径 | 请求 | 响应 | 说明 |
|------|------|------|------|------|
| GET | `/api/stats/test-mode` | - | `{device: int, jar: int, auto: int}` | 测试方式分布 |

***

## 新增 ADR

### ADR-16: 测试链路 — 真机优先 → JAR 仿真回退

**上下文**：JAR 仿真器覆盖率 85-90%，部分源在 JAR 中无法正确运行但真机可以。现有设计仅依赖 JAR 仿真，导致误判源为"失败"。

**决策**：测试链路改为真机优先 → JAR 仿真回退。真机可用时优先使用真机测试，真机不可用时回退到 JAR 仿真。

**理由**：
- 真机是 Legado 的实际运行环境，测试结果最准确
- JAR 仿真是为了在没有真机时也能测试
- 真机测试通过但 JAR 失败，说明 JAR 仿真有缺陷，应优化 JAR

**后果**：
* (+) 测试结果更准确，减少误判
* (+) 真机 vs JAR 对比可发现 JAR 仿真的不足
* (+) JAR 优化闭环持续提升 JAR 覆盖率
* (-) 真机测试需要配置设备，增加使用门槛
* (-) 真机测试依赖网络，可能较慢

**缓解**：真机为可选项，未配置时自动回退到 JAR 仿真。

***

### ADR-17: 前端架构 — 复用 Legado Vue3 前端 + 管理扩展面板

**上下文**：Legado 已有完整的 Vue3 前端（书架/阅读/源编辑/源调试），重新构建相同功能是重复造轮子。

**决策**：复用 Legado 已有的 Vue3 前端，通过反向代理集成；新增管理扩展面板（源列表/合集/导入/统计/真机管理/测试面板）。

**理由**：
- Legado 原生前端功能完整且经过验证
- 源编辑器和调试面板是核心功能，重写成本高且容易出错
- 管理功能（批量操作/统计/合集管理）是 Legado 前端没有的，需要新增

**后果**：
* (+) 避免重复造轮子，开发量大幅减少
* (+) 源编辑器和调试面板与 Legado App 行为一致
* (-) 依赖 Legado 前端构建产物，需定期同步更新
* (-) 反向代理增加一层网络开销

**缓解**：Legado 前端构建产物随项目分发；反向代理延迟通常 < 5ms（局域网）。

***

### ADR-18: LegadoWebClient — 完整封装 Legado Web 服务 API

**上下文**：原有 `LegadoDeviceClient` 仅封装 push/pull/test_connection 3 个方法，无法支持真机调试、书籍搜索等功能。

**决策**：重构为 `LegadoWebClient`，完整封装 Legado 的 26 个 HTTP API + 3 个 WebSocket API。

**理由**：
- 真机调试需要 WebSocket API（`bookSourceDebug`/`rssSourceDebug`）
- Legado 原生前端代理需要完整的 HTTP API 转发
- 书籍搜索（`searchBook`）可用于验证源功能

**后果**：
* (+) 支持真机调试和前端代理
* (+) API 完整，后续扩展无需修改客户端
* (-) 代码量增加（约 300 行）
* (-) WebSocket 代理的双向转发增加复杂度

**缓解**：WebSocket 代理使用 `asyncio.gather` 简化实现；HTTP 代理使用通用路由。

***

### ADR-19: JAR 优化闭环 — 真机通过但 JAR 失败时优化 JAR

**上下文**：JAR 仿真器覆盖率 85-90%，当真机测试通过但 JAR 仿真失败时，说明 JAR 仿真有缺陷。应利用这种差异持续优化 JAR。

**决策**：新增 `JarOptimizer` 模块，当检测到真机 vs JAR 差异时，自动分析 Legado 源码、定位 JAR 缺失功能、生成修复建议。

**理由**：
- 真机 vs JAR 差异是 JAR 仿真的宝贵测试用例
- 自动化分析可加速 JAR 优化
- JAR 覆盖率提升后，无真机时的测试准确性也提升

**后果**：
* (+) JAR 仿真覆盖率持续提升
* (+) 减少"真机通过但 JAR 失败"的误判
* (-) JAR 代码修改需要人工审核（安全考虑）
* (-) JAR 重新构建需要 Maven 环境

**缓解**：JAR 修复默认不自动应用，需人工确认；Maven 构建失败不影响主流程。

## File Changes

### 新增文件

| 文件                                             | 说明                 | 行数估计   |
| ---------------------------------------------- | ------------------ | ------ |
| `legado_client/storage/__init__.py`            | 存储层包入口             | 5      |
| `legado_client/storage/database.py`            | MySQL 连接管理+降级检测    | 120    |
| `legado_client/storage/models.py`              | ORM 模型定义（完整字段映射）   | 200    |
| `legado_client/storage/repository.py`          | CRUD 操作            | 400    |
| `legado_client/fetcher/__init__.py`            | 获取器包入口             | 5      |
| `legado_client/fetcher/yckceo_fetcher.py`      | yckceo.com 爬取      | 200    |
| `legado_client/fetcher/url_importer.py`        | URL/GitHub 导入      | 100    |
| `legado_client/fetcher/file_importer.py`       | 本地文件导入+目录扫描        | 120    |
| `legado_client/fetcher/legado_sync.py`         | Legado 真机同步        | 100    |
| `legado_client/fetcher/source_parser.py`       | JSON 解析+去重         | 150    |
| `legado_client/server/__init__.py`             | 服务层包入口             | 5      |
| `legado_client/server/app.py`                  | FastAPI 应用         | 100    |
| `legado_client/server/schemas.py`              | Pydantic 模型        | 200    |
| `legado_client/server/jvm_pool.py`             | JVM 实例池            | 120    |
| `legado_client/server/routes/sources.py`       | 源管理路由              | 200    |
| `legado_client/server/routes/collections.py`   | 合集管理路由             | 150    |
| `legado_client/server/routes/debug.py`         | 调试路由+WebSocket     | 250    |
| `legado_client/server/routes/import_export.py` | 导入导出路由             | 150    |
| `legado_client/server/routes/device.py`        | 真机推送路由             | 120    |
| `legado_client/server/routes/stats.py`         | 统计路由               | 80     |
| `legado_client/device/__init__.py`             | 真机对接包入口            | 5      |
| `legado_client/device/legado_web_client.py`   | Legado Web 服务完整客户端（26 HTTP + 3 WS） | 300    |
| `legado_client/analyzer/jar_optimizer.py`     | JAR 仿真优化闭环 | 150    |
| `legado_client/server/routes/legado_proxy.py` | Legado Web 服务代理路由 | 80     |
| `legado_client/web/`                           | Vue3 前端项目（管理面板 + Legado 原生前端） | \~2500 |
| `alembic.ini`                                  | 数据库迁移配置            | 30     |
| `alembic/`                                     | 迁移脚本目录             | -      |
| `docker-compose.yml`                           | MySQL 一键启动         | 25     |
| `.env.example`                                 | 环境变量模板             | 15     |

### 修改文件

| 文件                                     | 修改内容                                | 影响范围  |
| -------------------------------------- | ----------------------------------- | ----- |
| `legado_client/cli.py`                 | 新增 fetch/serve/db/import/export 子命令 | 扩展    |
| `legado_client/client/debug_runner.py` | 数据库查询+优化闭环+降级+结果入库+真机优先链路 | 新增步骤  |
| `legado_client/analyzer/auto_fixer.py` | 修复记录输出（fix\_detail）                 | 扩展返回值 |
| `legado_client/utils/config.py`        | 新增数据库/Web/爬取/真机配置+.env加载            | 扩展    |
| `scripts/requirements.txt`             | 新增依赖                                | 追加    |
| `scripts/setup.py`                     | 新增依赖声明+版本号3.0.0                     | 扩展    |
| `legado_client/__init__.py`            | 版本号统一为 3.0.0                        | 修复    |

### 依赖变更

| 新增依赖                  | 版本       | 用途                       |
| --------------------- | -------- | ------------------------ |
| `fastapi`             | ≥0.104.0 | Web 框架                   |
| `uvicorn[standard]`   | ≥0.24.0  | ASGI 服务器                 |
| `websockets`          | ≥12.0    | WebSocket 支持             |
| `sqlalchemy[asyncio]` | ≥2.0.0   | ORM                      |
| `aiomysql`            | ≥0.2.0   | 异步 MySQL 驱动              |
| `pymysql`             | ≥1.1.0   | 同步 MySQL 驱动（Alembic 迁移用） |
| `alembic`             | ≥1.12.0  | 数据库迁移                    |
| `httpx`               | ≥0.25.0  | 异步 HTTP 客户端              |
| `pydantic`            | ≥2.0.0   | 数据验证                     |
| `python-dotenv`       | ≥1.0.0   | .env 文件加载                |
| `slowapi`             | ≥0.1.9   | API 频率限制（可选）             |

## 配置设计

### .env 文件模板

```bash
# MySQL 数据库配置
LEGADO_DB_HOST=127.0.0.1
LEGADO_DB_PORT=3306
LEGADO_DB_USER=root
LEGADO_DB_PASSWORD=200868
LEGADO_DB_NAME=legado_sources
LEGADO_DB_POOL_MIN=2
LEGADO_DB_POOL_MAX=10

# Web 服务配置
LEGADO_WEB_HOST=127.0.0.1
LEGADO_WEB_PORT=8080

# 源获取配置
LEGADO_FETCH_BASE_URL=https://www.yckceo.com
LEGADO_FETCH_INTERVAL=1.0
LEGADO_FETCH_USER_AGENT=LegadoClient/3.0
LEGADO_FETCH_TIMEOUT=30

# JVM 池配置
LEGADO_JVM_POOL_SIZE=1

# Legado 真机默认配置
LEGADO_DEVICE_HOST=
LEGADO_DEVICE_HTTP_PORT=1122
# 注意：WebSocket 端口无需配置，由 Legado 源码硬编码为 HTTP 端口 + 1（默认 1123）
LEGADO_DEVICE_AUTH_TOKEN=

# Legado Web 服务代理配置
LEGADO_LEGADO_PROXY_ENABLED=true
```

### Config 扩展

```python
# legado_client/utils/config.py 新增配置项

class Config:
    # ... 现有配置不变 ...

    # MySQL 数据库配置（从环境变量/.env加载）
    db_host: str = os.getenv("LEGADO_DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("LEGADO_DB_PORT", "3306"))
    db_user: str = os.getenv("LEGADO_DB_USER", "root")
    db_password: str = os.getenv("LEGADO_DB_PASSWORD", "")  # 默认空，必须配置
    db_name: str = os.getenv("LEGADO_DB_NAME", "legado_sources")
    db_pool_min: int = int(os.getenv("LEGADO_DB_POOL_MIN", "2"))
    db_pool_max: int = int(os.getenv("LEGADO_DB_POOL_MAX", "10"))

    # Web 服务配置
    web_host: str = os.getenv("LEGADO_WEB_HOST", "127.0.0.1")
    web_port: int = int(os.getenv("LEGADO_WEB_PORT", "8080"))

    # 源获取配置
    fetch_base_url: str = os.getenv("LEGADO_FETCH_BASE_URL", "https://www.yckceo.com")
    fetch_interval: float = float(os.getenv("LEGADO_FETCH_INTERVAL", "1.0"))
    fetch_user_agent: str = os.getenv("LEGADO_FETCH_USER_AGENT", "LegadoClient/3.0")
    fetch_timeout: int = int(os.getenv("LEGADO_FETCH_TIMEOUT", "30"))

    # JVM 池配置
    jvm_pool_size: int = int(os.getenv("LEGADO_JVM_POOL_SIZE", "1"))

    # Legado 真机默认配置
    device_host: str = os.getenv("LEGADO_DEVICE_HOST", "")
    device_port: int = int(os.getenv("LEGADO_DEVICE_PORT", "1122"))  # HTTP 端口；WebSocket 端口 = port + 1（LegadoWebClient 内部计算）
    device_auth_token: str = os.getenv("LEGADO_DEVICE_AUTH_TOKEN", "")

    # Legado Web 服务代理配置
    legado_proxy_enabled: bool = os.getenv("LEGADO_LEGADO_PROXY_ENABLED", "true").lower() == "true"
```

***

## 补充架构决策

### ADR-11: yckceo\_fetcher 反爬与健壮性策略

**上下文**：yckceo.com 是社区书源分享平台，HTML 结构可能变化，且可能有反爬机制。

**决策**：采用"列表页 HTML 解析 + 详情页 JSON API"双层策略，配合容错机制。

**实现**：

```python
# legado_client/fetcher/yckceo_fetcher.py

class YckceoFetcher:
    """yckceo.com 源获取器

    双层策略：
    1. 列表页：HTML 解析获取合集元数据（标题/ID/下载量/日期）
    2. 详情页：直接 JSON API `/yuedu/{type}/json/id/{id}.json` 下载源数据
    """

    # 列表页解析容错：多套 CSS 选择器
    LIST_SELECTORS = {
        "title": ["h3 a", ".card-title a", ".title a", "a.title"],
        "link": ["h3 a", ".card-title a", ".title a", "a.title"],
        "user": [".user-name", ".author", ".username"],
        "count": [".source-count", ".count"],
        "downloads": [".downloads", ".download-count"],
        "date": [".date", ".upload-date", "time"],
    }

    async def fetch_list(self, source_type: str = "book") -> list[dict]:
        """获取合集列表（HTML 解析 + 容错）

        策略：
        1. 请求列表页 HTML
        2. 用第一套选择器解析
        3. 解析失败 → 降级到下一套选择器
        4. 全部失败 → 输出警告，返回空列表（不抛异常）
        """
        ...

    async def fetch_collection_json(self, collection_id: int,
                                     source_type: str = "book") -> list[dict]:
        """下载合集源数据（JSON API）

        直接请求 /yuedu/{type}/json/id/{id}.json
        返回 BookSource[] 或 RssSource[] JSON 数组
        """
        url = f"{self.base_url}/yuedu/{source_type}s/json/id/{collection_id}.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def fetch_all(self, source_type: str = "book",
                        on_progress=None) -> dict:
        """全量获取（列表+下载+入库）

        流程：
        1. fetch_list() 获取合集列表
        2. 对比数据库已有合集（增量：跳过已下载且未更新的）
        3. 逐个 fetch_collection_json() 下载
        4. SourceParser.parse_and_dedup() 去重入库
        5. 请求间隔 ≥ 1秒，User-Agent 设置
        """
        ...
```

**反爬应对**：

* 请求间隔 ≥ 1 秒（可配置）

* 设置 User-Agent（可配置）

* 超时处理：单次请求超时 30s，失败后跳过该合集

* HTML 结构变化容错：多套 CSS 选择器 + 降级

* 增量更新：对比 `remote_id + date`，仅下载新增/更新的合集

**后果**：

* (+) 健壮性高，HTML 变化不会导致完全失败

* (+) 增量更新减少请求量

* (-) 多套选择器维护成本

***

### ADR-12: Web 前端部署策略

**上下文**：Vue3 SPA 需要构建后部署，FastAPI 需要同时提供 API 和静态文件。

**决策**：前端代码放在 `legado_client/web/` 目录，构建产物输出到 `legado_client/web/dist/`，FastAPI 挂载静态文件。

**实现**：

```python
# legado_client/server/app.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Legado Client", version="3.0.0")

# API 路由
app.include_router(sources_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(debug_router, prefix="/api")
app.include_router(import_export_router, prefix="/api")
app.include_router(device_router, prefix="/api")
app.include_router(stats_router, prefix="/api")

# 静态文件挂载（构建产物）
WEB_DIST = Path(__file__).parent.parent / "web" / "dist"
if WEB_DIST.exists():
    # 挂载静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    # SPA 回退：所有非 /api 路径返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = WEB_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIST / "index.html")
```

**开发模式**：

* 前端开发：`cd legado_client/web && npm run dev`（Vite dev server，端口 5173）

* 后端开发：`legado-client serve`（FastAPI，端口 8080）

* 跨域处理：Vite 配置 `proxy: { '/api': 'http://127.0.0.1:8080' }`

**生产模式**：

* `cd legado_client/web && npm run build` → 输出到 `dist/`

* `legado-client serve` → FastAPI 同时提供 API + 静态文件

* 用户只需访问 `http://127.0.0.1:8080`

**后果**：

* (+) 开发体验好（前后端独立开发+热更新）

* (+) 生产部署简单（单端口）

* (-) 需要 Node.js 构建环境

* (-) 预构建 dist/ 需要随代码分发

***

### ADR-13: WebSocket 调试日志推送协议

**上下文**：Web 前端需要实时查看调试日志和进度。

**决策**：定义标准 WebSocket 消息格式。

**协议定义**：

```json
// 1. 调试日志消息
{
  "type": "log",
  "task_id": "uuid-string",
  "state": 10,           // JVM state 整数
  "stage": "search",     // 映射后的阶段名
  "message": "搜索到 5 本书",
  "html_length": 12345   // HTML 长度（可选）
}

// 2. 错误消息
{
  "type": "error",
  "task_id": "uuid-string",
  "stage": "detail",
  "message": "详情页解析失败",
  "stack_trace": "...",
  "suggestion": {         // 修复建议（可选）
    "summary": "CSS选择器未匹配",
    "tips": ["检查选择器是否正确"]
  }
}

// 3. 结果消息
{
  "type": "result",
  "task_id": "uuid-string",
  "success": true,
  "summary": {
    "stages": "搜索→详情→目录→正文",
    "confidence": "high"
  }
}

// 4. 进度消息（批量调试）
{
  "type": "progress",
  "task_id": "uuid-string",
  "current": 5,
  "total": 100,
  "source_name": "笔趣阁",
  "status": "pass"       // pass/fail/timeout
}

// 5. 完成消息
{
  "type": "complete",
  "task_id": "uuid-string",
  "success_count": 80,
  "fail_count": 20,
  "duration_ms": 30000
}
```

**task\_id 生成规则**：

* `POST /api/debug/start` 返回 `{"task_id": "uuid-string"}`

* 前端用 task\_id 连接 `ws://127.0.0.1:8080/ws/debug/{task_id}`

* task\_id 使用 UUID4 格式

**重连策略**：

* WebSocket 断开后自动重连（前端指数退避：1s/2s/4s/8s/最大30s）

* 重连后发送 `{"type": "reconnect", "task_id": "..."}` 获取最新状态

* 服务端维护最近 60s 的消息缓存，重连时补发

***

### ADR-14: Legado 真机 Web API 认证

**上下文**：Legado 真机 Web API 可能需要认证。

**决策**：支持两种认证模式，优先使用 auth\_token。

**认证流程**：

```python
# legado_client/device/legado_client.py

class LegadoDeviceClient:
    """Legado 真机 Web API 客户端

    注意：当前 Legado 版本（截至 2026-06）Web 服务不支持 HTTP 认证，
    HttpServer.kt 和 WebSocketServer.kt 均无 Authorization header 校验逻辑。
    auth_token 为预留字段，用于未来 Legado 可能新增的认证机制。

    WebSocket 端口 = HTTP 端口 + 1（源码 WebService.kt 第167行硬编码）。
    """

    def __init__(self, host: str, port: int = 1122, auth_token: str = ""):
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port + 1}"  # WebSocket 端口 = HTTP端口 + 1
        self.auth_token = auth_token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            # 注意：当前 Legado Web 服务版本不支持 HTTP 认证，
            # 此 header 不会被服务端校验，预留用于未来版本。
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def test_connection(self) -> dict:
        """测试设备连接

        Returns:
            {"connected": bool, "version": str, "auth_required": bool}
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/getBookSources",
                                         headers=self._headers())
                if resp.status_code == 200:
                    return {"connected": True, "auth_required": False}
                elif resp.status_code == 401:
                    return {"connected": True, "auth_required": True}
                else:
                    return {"connected": False, "auth_required": False}
        except Exception:
            return {"connected": False, "auth_required": False}

    async def push_sources(self, sources_json: str,
                            source_type: str = "book") -> dict:
        """推送源到设备"""
        endpoint = "/saveBookSources" if source_type == "book" else "/saveRssSource"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{endpoint}",
                content=sources_json,
                headers=self._headers()
            )
            return {"success": resp.status_code == 200,
                    "status_code": resp.status_code}

    async def pull_sources(self, source_type: str = "book") -> list[dict]:
        """从设备拉取源"""
        endpoint = "/getBookSources" if source_type == "book" else "/getRssSources"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self._headers()
            )
            if resp.status_code == 200:
                return resp.json()
            return []
```

***

### ADR-15: 数据库初始化与迁移流程

**上下文**：首次使用时需要建表+导入数据，后续升级需要迁移。

**决策**：明确初始化流程和 Alembic 迁移的关系。

**流程**：

```
legado-client db init
    ↓
1. 检查 MySQL 连接 → 失败则输出错误并退出
2. Alembic 迁移（创建/更新表结构）
    ↓ 成功
3. 扫描 output/ 目录 → 导入已有源文件
    ↓
4. 输出统计信息

legado-client db migrate
    ↓
1. 仅执行 Alembic 迁移（不导入数据）

legado-client db import-dir --dir output/
    ↓
1. 扫描指定目录 → 导入源文件（可重复执行，自动去重）

legado-client db reset
    ↓
1. 删除所有表 → 重新建表 → 导入 output/
```

**初始化时机**：

* `db init`：显式命令，用户手动执行

* `serve` 启动时：自动检查数据库连接，但不自动建表（避免意外操作）

* AI 调试时：自动检查数据库连接，不可用时降级到文件模式

**MySQL 未安装时**：

* `db init` 输出：`错误: 无法连接 MySQL (127.0.0.1:3306)，请先安装或使用 docker-compose up -d`

* `serve` 启动时输出警告，API 返回 503

* AI 调试时自动降级到文件模式

***

## 补充：目录结构更新

```
legado_client/
├── [现有] cli.py              ← 扩展：新增 fetch/serve/db/import/export 子命令
├── [现有] client/
│   ├── debug_runner.py        ← 扩展：新增 run_and_return() + DebugResult
│   ├── debug_orchestrator.py  ← [新增] AI 调试闭环编排器（真机优先链路）
│   └── rule_engine_client.py  ← 不变
├── [现有] analyzer/
│   ├── auto_fixer.py          ← 扩展：修复记录输出
│   └── jar_optimizer.py       ← [新增] JAR 仿真优化闭环
├── [现有] utils/
│   └── config.py              ← 扩展：新增数据库/Web/爬取/真机/Legado Web 服务配置
├── [新增] storage/            ← MySQL 存储层
│   ├── __init__.py
│   ├── database.py            ← 连接管理+连接池+降级检测
│   ├── models.py              ← SQLAlchemy ORM 模型（完整字段映射，含 ruleArticles/ruleContent）
│   └── repository.py          ← CRUD 操作
├── [新增] fetcher/            ← 多渠道源获取器
│   ├── __init__.py
│   ├── yckceo_fetcher.py      ← yckceo.com 爬取（双层策略+容错）
│   ├── url_importer.py        ← URL/GitHub 导入
│   ├── file_importer.py       ← 本地文件导入+目录扫描
│   ├── legado_sync.py         ← Legado 真机同步（通过 LegadoWebClient）
│   └── source_parser.py       ← JSON 解析+去重
├── [新增] server/             ← Web API 服务
│   ├── __init__.py
│   ├── app.py                 ← FastAPI 应用（含静态文件挂载+SPA 回退+Legado 前端代理）
│   ├── routes/
│   │   ├── sources.py         ← 源管理 API
│   │   ├── collections.py     ← 合集管理 API
│   │   ├── debug.py           ← 调试 API + WebSocket（标准协议+真机/JAR对比）
│   │   ├── import_export.py   ← 导入导出 API
│   │   ├── device.py          ← 真机推送 API
│   │   ├── legado_proxy.py    ← [新增] Legado Web 服务代理 API（26 HTTP + 3 WS）
│   │   └── stats.py           ← 统计 API
│   ├── schemas.py             ← Pydantic 请求/响应模型
│   └── jvm_pool.py            ← JVM 实例池管理（含回调桥接+重建机制）
├── [新增] device/             ← 真机对接
│   ├── __init__.py
│   └── legado_web_client.py   ← [重构] Legado Web 服务完整客户端（26 HTTP + 3 WS）
└── [新增] web/                ← 前端（复用 Legado Vue3 前端 + 管理扩展面板）
    ├── legado-frontend/       ← [新增] Legado 原生前端构建产物
    │   └── dist/
    ├── admin/                 ← [新增] 管理扩展面板（Vue3 + Element Plus）
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    └── dist/                  ← 管理面板构建产物（FastAPI 挂载）
```

***

## 补充：API 端点规范

### 源管理 API (`routes/sources.py`)

| 方法     | 路径                          | 请求                                                                                                                                              | 响应                                                             | 说明                    | <br /> | <br />                                        | <br />                       | <br /> |
| ------ | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------------------- | ------ | --------------------------------------------- | ---------------------------- | ------ |
| GET    | `/api/sources`              | `?page=1&page_size=20&source_type=book&book_source_type=0&rss_type=0&test_result=pass&group=xxx&has_login=true&search=xxx&sort_by=name&sort_order=asc` | `{items: [SourceItem], total: int, page: int, page_size: int}` | 源列表（分页+筛选+搜索+排序）      | <br /> | <br />                                        | <br />                       | <br /> |
| GET    | `/api/sources/{id}`         | -                                                                                                                                               | `SourceDetail`                                                 | 源详情（含完整 source\_json） | <br /> | <br />                                        | <br />                       | <br /> |
| PUT    | `/api/sources/{id}`         | `{source_json: str, source_name: str, source_url: str, group: str}`                                                                             | `SourceDetail`                                                 | 编辑源（JSON+元数据）         | <br /> | <br />                                        | <br />                       | <br /> |
| DELETE | `/api/sources/{id}`         | -                                                                                                                                               | `{ok: bool}`                                                   | 删除源                   | <br /> | <br />                                        | <br />                       | <br /> |
| PATCH  | `/api/sources/{id}/toggle`  | `{enabled: bool}`                                                                                                                               | `{ok: bool}`                                                   | 启用/禁用                 | <br /> | <br />                                        | <br />                       | <br /> |
| GET    | `/api/sources/by-domain`    | `?domain_key=xxx&source_type=book`                                                                                                                     | `[SourceItem]`                                                 | 按域名查询源                | <br /> | <br />                                        | <br />                       | <br /> |
| POST   | `/api/sources/batch-action` | \`{ids: \[int], action: "test"                                                                                                                  | "export"                                                       | "delete"              | "push" | "toggle", enabled?: bool, device\_id?: int}\` | `{ok: bool, results: [...]}` | 批量操作   |
| GET    | `/api/sources/groups`       | `?source_type=book`                                                                                                                             | `["分组1", "分组2", ...]`                                        | 已有分组列表（去重，前端下拉）   | <br /> | <br />                                        | <br />                       | <br /> |
| POST   | `/api/sources/{id}/export`  | -                                                                                                                                               | `Response(JSON文件下载)`                                           | 导出单个源 JSON 文件         | <br /> | <br />                                        | <br />                       | <br /> |
| POST   | `/api/sources/batch-export` | `{ids: [int]}`                                                                                                                                  | `Response(JSON文件下载)`                                           | 批量导出                  | <br /> | <br />                                        | <br />                       | <br /> |
| POST   | `/api/sources/validate`     | `{source_json: str}`                                                                                                                            | `{ok: bool, errors: [str]}`                                      | 验证源 JSON 格式（P1）     | <br /> | <br />                                        | <br />                       | <br /> |

### 合集管理 API (`routes/collections.py`)

| 方法     | 路径                               | 请求                               | 响应                                                     | 说明                      |
| ------ | -------------------------------- | -------------------------------- | ------------------------------------------------------ | ----------------------- |
| GET    | `/api/collections`               | `?source_type=book&page=1&page_size=20` | `{items: [CollectionItem], total: int}`                | 合集列表                    |
| GET    | `/api/collections/remote`        | `?source_type=book`                     | `[RemoteCollection]`                                   | 获取远程合集列表                |
| POST   | `/api/collections/{id}/download` | `{source_type: str}`                    | `{ok: bool, imported: int, skipped: int, failed: int}` | 下载指定合集（按主键id）           |
| POST   | `/api/collections/fetch-all`     | `{source_type: str}`                    | `{ok: bool, task_id: str}`                             | 全量获取（异步，WebSocket 推送进度） |
| POST   | `/api/collections/incremental`   | `{source_type: str}`                    | `{ok: bool, updated: int, new: int}`                   | 增量更新                    |
| DELETE | `/api/collections/{id}`          | -                                | `{ok: bool}`                                           | 删除本地合集记录                |

### 调试 API (`routes/debug.py`)

| 方法   | 路径                    | 请求                                                                               | 响应                                        | 说明                                 | <br />                     | <br /> |
| ---- | --------------------- | -------------------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------- | -------------------------- | ------ |
| POST | `/api/debug/start`    | `{source_id?: int, source_json?: str, source_type: str, key?: str, stage?: str}` | `{ok: bool, task_id: str}`                | 启动单源调试                             | <br />                     | <br /> |
| POST | `/api/debug/batch`    | \`{scope: "all"                                                                  | "failed"                                  | "group", group?: str, type: str}\` | `{ok: bool, task_id: str}` | 启动批量调试 |
| POST | `/api/debug/optimize` | `{source_id: int}`                                                               | `{ok: bool, task_id: str}`                | 启动优化（测试+修复+重测）                     | <br />                     | <br /> |
| POST | `/api/debug/cancel`   | `{task_id: str}`                                                                 | `{ok: bool}`                              | 取消调试任务                             | <br />                     | <br /> |
| GET  | `/api/debug/status`   | `{task_id: str}`                                                                 | `{status: str, progress: float}`          | 查询调试状态                             | <br />                     | <br /> |
| GET  | `/api/debug/history`  | `?source_id=xxx&page=1&page_size=10`                                             | `{items: [DebugHistoryItem], total: int}` | 调试历史                               | <br />                     | <br /> |
| WS   | `/ws/debug/{task_id}` | -                                                                                | `DebugWSMessage`                          | 实时调试日志推送                           | <br />                     | <br /> |

### 导入导出 API (`routes/import_export.py`)

| 方法   | 路径                   | 请求                                | 响应                                                     | 说明        |
| ---- | -------------------- | --------------------------------- | ------------------------------------------------------ | --------- |
| POST | `/api/import/url`    | `{url: str, source_type: str}`           | `{ok: bool, imported: int, skipped: int, failed: int}` | URL 导入    |
| POST | `/api/import/file`   | `multipart/form-data: file, source_type` | `{ok: bool, imported: int, skipped: int, failed: int}` | 文件上传导入    |
| POST | `/api/import/github` | `{repo_url: str, source_type: str}`      | `{ok: bool, imported: int, skipped: int, failed: int}` | GitHub 导入 |
| POST | `/api/import/device` | `{device_id: int, source_type: str}`     | `{ok: bool, imported: int, skipped: int, failed: int}` | 真机拉取导入    |

### 真机 API (`routes/device.py`)

| 方法     | 路径                       | 请求                                                  | 响应                                     | 说明     |
| ------ | ------------------------ | --------------------------------------------------- | -------------------------------------- | ------ |
| GET    | `/api/devices`           | -                                                   | `[DeviceItem]`                         | 设备列表   |
| POST   | `/api/devices`           | `{name: str, ip: str, port: int, auth_token?: str}` | `DeviceItem`                           | 添加设备   |
| PUT    | `/api/devices/{id}`      | `{name?, ip?, port?, auth_token?}`                  | `DeviceItem`                           | 编辑设备   |
| DELETE | `/api/devices/{id}`      | -                                                   | `{ok: bool}`                           | 删除设备   |
| POST   | `/api/devices/{id}/test` | -                                                   | `{ok: bool, status: str}`              | 测试连接   |
| POST   | `/api/devices/{id}/push` | `{source_ids: [int], source_type: str}`                    | `{ok: bool, pushed: int, failed: int}` | 推送源到设备 |
| POST   | `/api/devices/{id}/pull` | `{source_type: str}`                                       | `{ok: bool, imported: int}`            | 从设备拉取源 |

### 统计 API (`routes/stats.py`)

| 方法  | 路径                        | 请求                  | 响应                                                                | 说明                                                         |
| --- | ------------------------- | ------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| GET | `/api/stats/overview`     | -                   | `{total: int, book_count: int, rss_count: int, pass_rate: float}` | 概览统计                                                       |
| GET | `/api/stats/test-result`  | -                   | `{pass: int, fail: int, untested: int}`                           | 测试结果分布                                                     |
| GET | `/api/stats/content-type` | `?source_type=book` | `[{type: str, count: int}]`                                       | 内容类型分布（按 source\_type 分组查询 book\_source\_type 或 rss\_type） |
| GET | `/api/stats/group`        | -                   | `[{group: str, count: int}]`                                      | 分组分布                                                       |

### 系统 API

| 方法  | 路径            | 请求 | 响应                                                                      | 说明   |
| --- | ------------- | -- | ----------------------------------------------------------------------- | ---- |
| GET | `/api/health` | -  | `{status: str, db_connected: bool, jvm_status: str, source_count: int}` | 健康检查 |

### 统一响应格式

```python
# 成功响应
{"ok": True, "data": {...}}

# 错误响应
{"ok": False, "error": {"code": "DB_UNAVAILABLE", "message": "MySQL 连接失败"}}

# 错误码
DB_UNAVAILABLE = "数据库不可用"
SOURCE_NOT_FOUND = "源不存在"
JVM_BUSY = "JVM 正忙，请稍后"
INVALID_JSON = "JSON 格式错误"
DEVICE_UNREACHABLE = "设备不可达"
IMPORT_FAILED = "导入失败"
```

***

## 补充：数据库索引设计

```sql
-- Source 表索引（核心查询性能保障）
CREATE INDEX idx_source_domain_key ON source(domain_key);           -- 按域名查询（AI调试查库）
CREATE INDEX idx_source_type ON source(source_type);                -- 按类型筛选
CREATE INDEX idx_source_test_result ON source(last_test_result);    -- 按测试结果筛选
CREATE INDEX idx_source_group ON source(source_group);              -- 按分组筛选
CREATE INDEX idx_source_enabled ON source(enabled);                 -- 按启用状态筛选
CREATE INDEX idx_source_name ON source(source_name);                -- 按名称搜索
CREATE INDEX idx_source_content_type_book ON source(book_source_type);  -- BookSource 按内容类型筛选
CREATE INDEX idx_source_content_type_rss ON source(rss_type);           -- RssSource 按内容类型筛选
CREATE INDEX idx_source_domain_name ON source(domain_key, source_name);  -- 去重唯一键
CREATE INDEX idx_source_updated_at ON source(updated_at);           -- 按更新时间排序

-- Collection 表索引
CREATE INDEX idx_collection_type ON collection(type);              -- 按类型筛选
CREATE INDEX idx_collection_remote_id ON collection(remote_id);     -- 增量更新对比

-- DebugResult 表索引
CREATE INDEX idx_debug_source_id ON debug_result(source_id);        -- 按源ID查调试历史
CREATE INDEX idx_debug_created_at ON debug_result(created_at);      -- 按时间排序

-- DeviceConfig 表索引（数据量小，无需额外索引）
```

***

## 补充：source\_parser 字段映射

### BookSource JSON → Source ORM 映射

> **源码依据**：`app/src/main/java/io/legado/app/data/entities/BookSource.kt`
> BookSource 无 bookSourceIcon 字段（RssSource 有 sourceIcon），字段 loginCheckJs 不是 loginCheckUrl。

```python
BOOK_SOURCE_MAPPING = {
    # source_json 完整保留
    "source_json": "$",                          # 完整 JSON 字符串

    # 关键字段独立列
    "source_name": "bookSourceName",             # 源名称
    "source_url": "bookSourceUrl",               # 源URL（@PrimaryKey）
    "source_type": lambda _: "book",             # 固定 "book"
    "source_group": "bookSourceGroup",           # 分组
    "book_source_type": "bookSourceType",        # BookSource 内容类型（0文本/1音频/2图片/3文件/4视频）
    "enabled": "enabled",                        # 启用状态（默认 true）
    "enabled_explore": "enabledExplore",         # 启用发现（默认 true）
    "login_url": "loginUrl",                     # 登录URL
    "login_ui": "loginUi",                       # 登录UI（BaseSource 接口，BookSource/RssSource 共有）
    "login_check_js": "loginCheckJs",            # 登录检测JS（注意：不是 loginCheckUrl）
    "cover_decode_js": "coverDecodeJs",          # 封面解密JS
    "search_url": "searchUrl",                   # 搜索URL
    "explore_url": "exploreUrl",                 # 发现URL
    "explore_screen": "exploreScreen",           # 发现筛选规则
    "book_url_pattern": "bookUrlPattern",        # 详情页URL正则
    "last_update_time": "lastUpdateTime",        # 最后更新时间
    "respond_time": "respondTime",               # 响应时间（默认 180000ms = 3分钟）
    "weight": "weight",                          # 智能排序权重
    "custom_order": "customOrder",               # 手动排序
    "concurrent_rate": "concurrentRate",         # 并发率
    "header": "header",                          # 请求头
    "source_icon": lambda _: None,               # BookSource 无图标字段
    "source_comment": "bookSourceComment",       # 注释
    "variable_comment": "variableComment",       # 自定义变量说明
    "enabled_cookie_jar": "enabledCookieJar",    # 启用CookieJar
    "js_lib": "jsLib",                           # JS库
    "event_listener": "eventListener",           # 事件监听
    "custom_button": "customButton",             # 自定义按钮

    # 规则字段（独立列便于筛选，完整规则在 source_json 中）
    # 注意：ruleSearch/ruleBookInfo/ruleToc/ruleContent/ruleExplore/ruleReview
    # 在 BookSource JSON 中是嵌套对象，映射时必须 json.dumps() 序列化为字符串存入 TEXT 列
    "rule_search": lambda obj: json.dumps(obj.get("ruleSearch", {}), ensure_ascii=False) if isinstance(obj.get("ruleSearch"), dict) else obj.get("ruleSearch"),
    "rule_book_info": lambda obj: json.dumps(obj.get("ruleBookInfo", {}), ensure_ascii=False) if isinstance(obj.get("ruleBookInfo"), dict) else obj.get("ruleBookInfo"),
    "rule_toc": lambda obj: json.dumps(obj.get("ruleToc", {}), ensure_ascii=False) if isinstance(obj.get("ruleToc"), dict) else obj.get("ruleToc"),
    "rule_content": lambda obj: json.dumps(obj.get("ruleContent", {}), ensure_ascii=False) if isinstance(obj.get("ruleContent"), dict) else obj.get("ruleContent"),
    "rule_explore": lambda obj: json.dumps(obj.get("ruleExplore", {}), ensure_ascii=False) if isinstance(obj.get("ruleExplore"), dict) else obj.get("ruleExplore"),
    "rule_review": lambda obj: json.dumps(obj.get("ruleReview", {}), ensure_ascii=False) if isinstance(obj.get("ruleReview"), dict) else obj.get("ruleReview"),

    # 计算字段
    "domain_key": lambda obj: extract_domain_key(obj.get("bookSourceUrl", "")),
    "has_login": lambda obj: bool(obj.get("loginUrl") or obj.get("loginCheckJs")),
}
```

### RssSource JSON → Source ORM 映射

> **源码依据**：`app/src/main/java/io/legado/app/data/entities/RssSource.kt`
> RssSource 类型字段名是 `type`（不是 `sourceType`），有 `searchUrl` 字段，无 `respondTime`/`weight` 字段。

```python
RSS_SOURCE_MAPPING = {
    # source_json 完整保留
    "source_json": "$",                          # 完整 JSON 字符串

    # 关键字段独立列
    "source_name": "sourceName",                 # 源名称
    "source_url": "sourceUrl",                   # 源URL（@PrimaryKey）
    "source_type": lambda _: "rss",              # 固定 "rss"
    "source_group": "sourceGroup",               # 分组
    "rss_type": "type",                          # RssSource 内容类型（0网页/1图片/2视频）注意：字段名是 type 不是 sourceType
    "enabled": "enabled",                        # 启用状态（默认 true）
    "enabled_explore": lambda _: None,           # RssSource 无 enabledExplore 字段
    "login_url": "loginUrl",                     # 登录URL
    "login_ui": "loginUi",                       # 登录UI（BaseSource 接口，BookSource/RssSource 共有）
    "login_check_js": "loginCheckJs",            # 登录检测JS（注意：不是 loginCheckUrl，与 BookSource 一致）
    "cover_decode_js": "coverDecodeJs",          # 封面解密JS
    "search_url": "searchUrl",                   # 搜索URL（RssSource 有此字段，不应映射为 None）
    "explore_url": lambda _: None,               # 订阅源无发现URL
    "book_url_pattern": lambda _: None,          # 订阅源无详情页URL正则
    "single_url": "singleUrl",                   # 单URL源
    "sort_url": "sortUrl",                       # 分类URL
    "article_style": "articleStyle",             # 列表样式（0三图/1大图/2双排/3单图/4无图）
    "last_update_time": "lastUpdateTime",        # 最后更新时间
    "respond_time": lambda _: None,              # RssSource 无 respondTime 字段
    "weight": lambda _: None,                    # RssSource 无 weight 字段
    # RssSource 高频查询规则字段（均为 String 类型，非嵌套对象）
    "rule_title": "ruleTitle",                   # 标题规则
    "rule_image": "ruleImage",                   # 图片规则
    "rule_link": "ruleLink",                     # 链接规则
    "rule_next_page": "ruleNextPage",            # 下一页规则
    "rule_pub_date": "rulePubDate",              # 发布日期规则
    "rule_description": "ruleDescription",       # 描述规则
    "custom_order": "customOrder",               # 手动排序
    "concurrent_rate": "concurrentRate",         # 并发率
    "header": "header",                          # 请求头
    "source_icon": "sourceIcon",                 # 图标URL
    "source_comment": "sourceComment",           # 注释
    "variable_comment": "variableComment",       # 自定义变量说明
    "enabled_cookie_jar": "enabledCookieJar",    # 启用CookieJar
    "js_lib": "jsLib",                           # JS库
    "event_listener": lambda _: None,             # RssSource 无此字段（BookSource 特有，Boolean）
    "custom_button": lambda _: None,              # RssSource 无此字段（BookSource 特有，Boolean）

    # 规则字段（注意：RssSource 的规则字段是 String 类型，不是嵌套对象！）
    # 源码 RssSource.kt: ruleArticles: String?, ruleContent: String?
    # 而 BookSource.kt 的规则字段是嵌套对象（SearchRule, ContentRule 等）
    # 因此 RssSource 的规则字段直接取字符串值，不需要 json.dumps
    "rule_articles": "ruleArticles",               # RssSource 规则是 String，非嵌套对象
    "rule_content": "ruleContent",                 # RssSource 规则是 String，非嵌套对象

    # RssSource WebView/显示相关字段（book 类型为 NULL）
    # 以下 14 个字段仅存在于 RssSource，为低频查询字段，不设独立列，
    # 仅通过 source_json 完整保留。如需独立查询可后续迁移。
    # "content_whitelist": "contentWhitelist",    # 正文URL白名单
    # "content_blacklist": "contentBlacklist",    # 正文URL黑名单
    # "should_override_url_loading": "shouldOverrideUrlLoading",  # 跳转URL拦截JS
    # "style": "style",                           # WebView样式
    # "enable_js": "enableJs",                    # 启用JS（默认true）
    # "load_with_base_url": "loadWithBaseUrl",    # 基于URL加载（默认true）
    # "inject_js": "injectJs",                    # 注入JS
    # "preload_js": "preloadJs",                  # 预注入JS
    # "start_html": "startHtml",                  # Web起始页HTML
    # "start_style": "startStyle",                # Web起始页样式
    # "start_js": "startJs",                      # Web起始页JS
    # "show_web_log": "showWebLog",               # 输出Web日志（Boolean，默认false）
    # "preload": "preload",                       # 启用预加载（Boolean，默认false）
    # "cache_first": "cacheFirst",                # 优先缓存（Boolean，默认false）

    # 计算字段
    "domain_key": lambda obj: extract_domain_key(obj.get("sourceUrl", "")),
    "has_login": lambda obj: bool(obj.get("loginUrl") or obj.get("loginCheckJs")),
}
```

***

## 补充：现有模块集成方案

### batch\_runner.py → Web 批量调试

**现状**：`batch_runner.run_batch()` 读取目录下 JSON 文件，逐个调用 `debug_runner.run()`，使用 `sys.exit()` 退出。

**集成方案**：

* Web 批量调试不直接使用 `batch_runner.py`，而是通过 `DebugOrchestrator` 编排

* `DebugOrchestrator.batch_debug()` 从数据库查询源列表（替代文件扫描），逐个调用 `run_and_return()`

* 保留 `batch_runner.py` 的 CLI 入口不变，内部逐步迁移到 `run_and_return()`

* 新增 `batch_runner.run_batch_and_return()` 返回结果列表（不 sys.exit）

```python
# legado_client/client/batch_runner.py 扩展
def run_batch_and_return(source_ids: list[int], storage_repo=None) -> list[DebugResult]:
    """批量调试（返回值模式，供 Web API 使用）

    Args:
        source_ids: 数据库源ID列表
        storage_repo: StorageRepository 实例

    Returns:
        list[DebugResult]: 每个源的调试结果
    """
    results = []
    for source_id in source_ids:
        source = storage_repo.get_by_id(source_id)
        result = run_and_return(args, json.loads(source.source_json))
        results.append(result)
        storage_repo.update_debug_result(source_id, result)
    return results
```

### experience\_manager.py → 数据库经验查询

**现状**：`ExperienceManager.search()` 搜索 `references/troubleshooting/` 目录下的 Markdown 文件。

**集成方案**：

* AI 调试闭环中，`DebugOrchestrator` 在查库后额外调用 `ExperienceManager.search()` 检索经验

* 经验检索结果作为调试上下文传递给 `debug_runner`，辅助修复

* 经验写入仍走 basic-memory MCP（不变）

* 新增：调试成功后，将修复经验关联到 Source 记录的 `notes` 字段

```python
# DebugOrchestrator.debug_with_db() 中新增经验检索步骤
if existing and not passed:
    # 查经验库
    exp_mgr = ExperienceManager()
    experience = exp_mgr.search(source_url, source_name)
    if experience != "无相似案例":
        result["experience_hint"] = experience
```

### obstacle\_resolver.py / crypto\_analyzer.py / interactive\_guide.py

**现状**：`debug_runner.py` 已集成这些模块（`_OBSTACLE_RESOLVER_AVAILABLE` 等标志控制）。

**集成方案**：

* 这些模块在 `debug_runner.run()` / `run_and_return()` 内部自动调用，无需额外集成

* Web 调试流通过 `JvmPool` → `debug_runner.run_and_return()` 间接使用

* `interactive_guide.py` 的交互提示在 Web 模式下通过 WebSocket 推送给前端展示（非阻塞提示，不等待用户输入）

* `webview_handler.py` / `user_interaction.py` 在 Web 模式下降级为日志输出（无法弹出 GUI 窗口）

### source\_validator.py / rule\_precheck.py

**现状**：`debug_runner.py` 在调试前调用 `SourceValidator` 和 `RulePrecheck` 做预检。

**集成方案**：

* Web API 编辑源时（PUT `/api/sources/{id}`），调用 `SourceValidator.validate_source()` 验证 JSON 格式

* Web API 调试前，`RulePrecheck` 作为调试流程的一部分自动执行

* 新增 API：`POST /api/sources/validate` — 独立的源验证端点（前端编辑器实时验证用）

### html\_fetcher.py / fetch\_html.py

**现状**：两个文件功能重叠，`html_fetcher.py` 是完整版，`fetch_html.py` 是简化版。

**集成方案**：

* `yckceo_fetcher.py` 使用 `httpx`（异步 HTTP 客户端）替代 `html_fetcher.py`

* `html_fetcher.py` 保留给 `debug_runner` 的现有逻辑使用（不变）

* `fetch_html.py` 标记为 deprecated，不引入新模块

### confidence\_evaluator.py / error\_diagnoser.py

**现状**：`debug_runner.py` 调用 `evaluate_confidence()` 和 `diagnose_error()`。

**集成方案**：

* `DebugResult` 新增 `confidence` 字段，由 `evaluate_confidence()` 计算

* `error_diagnoser.py` 的诊断结果存入 `DebugResult.errors` 和 `fix_detail`

* Web API 返回调试结果时包含 confidence 和诊断信息

### delegate/ 模块（ocr\_delegate.py / webview\_delegate.py）

**现状**：OCR 和 WebView 代理，需要 GUI 环境。

**集成方案**：

* Web 模式下不启用（服务器无 GUI），`_detect_obstacle_type()` 检测到验证码时标记为需人工处理

* CLI 模式下保持现有行为

* 后续迭代可考虑 headless 浏览器方案

***

## 补充：CORS 配置

```python
# legado_client/server/app.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",    # 生产模式（同源，实际不需要）
        "http://127.0.0.1:5173",    # Vite 开发模式
        "http://localhost:5173",     # Vite 开发模式
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**说明**：生产模式下前端构建产物由 FastAPI 直接服务（同源），CORS 仅在开发模式（Vite dev server :5173 → FastAPI :8080）时需要。

***

## 补充：config.py 扩展设计

```python
# legado_client/utils/config.py 扩展
# 兼容现有 Config.get_instance() 单例模式

from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件

class Config:
    _instance = None

    @classmethod
    def get_instance(cls) -> "Config":
        """现有单例入口，保持向后兼容"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # ... 现有字段 ...

        # === 新增：数据库配置 ===
        self.db_host: str = os.getenv("LEGADO_DB_HOST", "127.0.0.1")
        self.db_port: int = int(os.getenv("LEGADO_DB_PORT", "3306"))
        self.db_user: str = os.getenv("LEGADO_DB_USER", "root")
        self.db_password: str = os.getenv("LEGADO_DB_PASSWORD", "")
        self.db_name: str = os.getenv("LEGADO_DB_NAME", "legado_sources")
        self.db_pool_min: int = int(os.getenv("LEGADO_DB_POOL_MIN", "2"))
        self.db_pool_max: int = int(os.getenv("LEGADO_DB_POOL_MAX", "10"))

        # === 新增：Web 服务配置 ===
        self.web_host: str = os.getenv("LEGADO_WEB_HOST", "127.0.0.1")
        self.web_port: int = int(os.getenv("LEGADO_WEB_PORT", "8080"))

        # === 新增：爬取配置 ===
        self.fetch_interval: float = float(os.getenv("LEGADO_FETCH_INTERVAL", "1.0"))  # 请求间隔（秒）
        self.fetch_timeout: int = int(os.getenv("LEGADO_FETCH_TIMEOUT", "30"))         # 请求超时（秒）
        self.fetch_user_agent: str = os.getenv(
            "LEGADO_FETCH_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.domain_source_limit: int = int(os.getenv("LEGADO_DOMAIN_SOURCE_LIMIT", "20"))  # 同域名源上限

        # === 新增：JVM 配置 ===
        self.jvm_max_instances: int = int(os.getenv("LEGADO_JVM_MAX_INSTANCES", "1"))
        self.jvm_debug_timeout: int = int(os.getenv("LEGADO_JVM_DEBUG_TIMEOUT", "120"))  # 调试超时（秒）

        # === 新增：.env 文件加载 ===
        self._load_dotenv()

    def _load_dotenv(self):
        """从 .env 文件加载环境变量（优先级：环境变量 > .env 文件 > 默认值）"""
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"
            load_dotenv(env_path, override=False)
        except ImportError:
            pass  # python-dotenv 未安装，使用环境变量或默认值

    @property
    def database_url(self) -> str:
        """异步数据库连接 URL"""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    @property
    def database_url_sync(self) -> str:
        """同步数据库连接 URL（Alembic 迁移用）"""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )
```

***

## 补充：Source 表 group 字段设计

Source 表已有 `source_group` 字段（对应 BookSource.bookSourceGroup / RssSource.sourceGroup），但需补充：

1. **分组来源**：源 JSON 中的 `bookSourceGroup` / `sourceGroup` 字段，多个分组用 `,` 或 `;` 分隔
2. **分组格式**：Legado 原生格式为逗号分隔字符串，如 `"小说,精品,中文"`
3. **分组筛选**：API 使用 `LIKE` 查询（`WHERE source_group LIKE '%小说%'`），或使用 FIND\_IN\_SET
4. **分组管理**：前端编辑时可修改 `source_group` 字段（逗号分隔输入）。源详情页基本信息卡片中包含分组标签编辑区域，使用 TagInput 组件，支持：① 直接输入标签名（回车添加）② 从已有分组列表中选择（下拉建议）③ 点击标签 × 按钮移除。保存时自动合并为逗号分隔字符串写入 `source_group` 字段。
5. **分组统计**：统计 API 按分组聚合时，需先拆分再统计

```python
# repository.py 分组查询
async def find_by_group(self, group: str, source_type: str = None) -> list[Source]:
    """按分组查询源（支持逗号分隔的多分组字段）"""
    query = select(Source).where(Source.source_group.contains(group))
    if source_type:
        query = query.where(Source.source_type == source_type)
    return await self._execute_query(query)
```

***

## 补充：Pydantic Schemas 定义

```python
# legado_client/server/schemas.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum, IntEnum

# === 枚举 ===

class SourceType(str, Enum):
    BOOK = "book"
    RSS = "rss"

class BookSourceType(IntEnum):
    """BookSource 内容类型（与 Legado 源码 BookSource.bookSourceType 注释一致：0文本/1音频/2图片/3文件/4视频）"""
    TEXT = 0       # 文本
    AUDIO = 1     # 音频
    IMAGE = 2     # 图片
    FILE = 3      # 文件（类似知轩藏书只提供下载的网站）
    VIDEO = 4     # 视频

class RssType(IntEnum):
    """RssSource 内容类型（与 Legado 源码 RssSource.sourceType 一致）"""
    WEB = 0       # 网页
    IMAGE = 1     # 图片
    VIDEO = 2     # 视频

class TestResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNTESTED = "untested"

# === 请求模型 ===

class SourceListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    source_type: Optional[str] = None    # book / rss
    book_source_type: Optional[int] = None  # BookSource 内容类型（0文本/1音频/2图片/3文件）
    rss_type: Optional[int] = None       # RssSource 内容类型（0网页/1图片/2视频）
    test_result: Optional[str] = None    # pass / fail / untested
    group: Optional[str] = None
    has_login: Optional[bool] = None
    search: Optional[str] = None
    sort_by: str = Field(default="updated_at", pattern="^(name|updated_at|last_test_time|respond_time|weight|custom_order)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

class SourceUpdateRequest(BaseModel):
    source_json: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_group: Optional[str] = None

class DebugStartRequest(BaseModel):
    source_id: Optional[int] = None
    source_json: Optional[str] = None
    source_type: str = "book"
    key: Optional[str] = None
    stage: Optional[str] = "all"

class BatchDebugRequest(BaseModel):
    scope: str = "all"       # all / failed / group
    group: Optional[str] = None
    source_type: str = "book"  # book / rss

class ImportUrlRequest(BaseModel):
    url: str
    source_type: str = "book"  # book / rss

class ImportGithubRequest(BaseModel):
    repo_url: str
    source_type: str = "book"  # book / rss

class ImportDeviceRequest(BaseModel):
    device_id: int
    source_type: str = "book"  # book / rss

class DeviceCreateRequest(BaseModel):
    name: str
    ip: str
    port: int = 1122  # HTTP 端口；WebSocket 端口 = port + 1（Legado 源码硬编码，无需独立字段）
    auth_token: Optional[str] = None

class DeviceUpdateRequest(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    auth_token: Optional[str] = None

class DevicePushRequest(BaseModel):
    source_ids: list[int]
    type: str = "book"

class BatchActionRequest(BaseModel):
    ids: list[int]
    action: str  # test / export / delete / push / toggle
    enabled: Optional[bool] = None
    device_id: Optional[int] = None

# === 响应模型 ===

class SourceItem(BaseModel):
    id: int
    source_name: str
    source_url: str
    source_type: str
    book_source_type: Optional[int] = None  # BookSource 内容类型
    rss_type: Optional[int] = None       # RssSource 内容类型
    source_group: Optional[str] = None
    source_icon: Optional[str] = None    # 图标URL（列表展示用）
    last_test_result: Optional[str] = None
    last_test_time: Optional[datetime] = None
    respond_time: Optional[int] = None
    enabled: bool = True
    has_login: bool = False
    updated_at: Optional[datetime] = None

class SourceDetail(BaseModel):
    id: int
    source_name: str
    source_url: str
    source_type: str
    book_source_type: Optional[int] = None  # BookSource 内容类型
    rss_type: Optional[int] = None       # RssSource 内容类型
    source_group: Optional[str] = None
    source_json: str
    login_url: Optional[str] = None
    login_ui: Optional[str] = None         # 登录UI（BaseSource 接口，BookSource/RssSource 共有）
    login_check_js: Optional[str] = None  # 登录检测JS（注意：不是 loginCheckUrl）
    cover_decode_js: Optional[str] = None  # 封面解密JS
    search_url: Optional[str] = None
    explore_url: Optional[str] = None
    explore_screen: Optional[str] = None  # 发现筛选规则（BookSource 特有）
    book_url_pattern: Optional[str] = None  # 详情页URL正则（BookSource 特有）
    enabled_explore: Optional[bool] = True
    rule_search: Optional[str] = None      # 搜索规则 JSON字符串
    rule_book_info: Optional[str] = None   # 书籍信息规则 JSON字符串
    rule_toc: Optional[str] = None         # 目录规则 JSON字符串
    rule_content: Optional[str] = None     # 正文规则 JSON字符串
    rule_explore: Optional[str] = None     # 发现规则 JSON字符串（BookSource 特有）
    rule_review: Optional[str] = None      # 评论规则 JSON字符串（BookSource 特有）
    rule_articles: Optional[str] = None    # 文章列表规则 JSON字符串
    single_url: Optional[bool] = None      # 单URL源（RssSource 特有）
    sort_url: Optional[str] = None         # 分类URL（RssSource 特有）
    article_style: Optional[int] = None    # 列表样式（RssSource 特有）
    # RssSource WebView/显示规则字段（均为 String，book 类型为 None）
    rule_title: Optional[str] = None       # 标题规则
    rule_image: Optional[str] = None       # 图片规则
    rule_link: Optional[str] = None        # 链接规则
    rule_next_page: Optional[str] = None   # 下一页规则
    rule_pub_date: Optional[str] = None    # 发布日期规则
    rule_description: Optional[str] = None # 描述规则
    variable_comment: Optional[str] = None  # 自定义变量说明
    enabled_cookie_jar: Optional[bool] = None  # 启用CookieJar
    js_lib: Optional[str] = None           # JS库
    event_listener: Optional[bool] = None   # 事件监听（Boolean，非Text）
    custom_button: Optional[bool] = None    # 自定义按钮（Boolean，非Text）
    last_test_result: Optional[str] = None
    last_test_time: Optional[datetime] = None
    test_mode: Optional[str] = None        # jar/device/auto
    test_confidence: Optional[str] = None  # high/medium/low/unverifiable
    test_detail: Optional[dict] = None     # 各阶段测试结果详情
    device_jar_diff: Optional[dict] = None # 真机vs JAR对比差异
    respond_time: Optional[int] = None
    enabled: bool = True
    has_login: bool = False
    weight: int = 0
    custom_order: int = 0
    concurrent_rate: Optional[str] = None
    header: Optional[str] = None
    source_icon: Optional[str] = None
    source_comment: Optional[str] = None
    last_update_time: Optional[int] = None
    domain_key: Optional[str] = None
    notes: Optional[str] = None               # AI闭环修复经验摘要
    import_source: Optional[str] = None       # 导入来源
    collection_id: Optional[int] = None       # 关联合集
    fix_count: int = 0                        # 自动修复次数
    last_fix_detail: Optional[dict] = None    # 最近一次修复详情
    jar_optimization_count: int = 0           # JAR 仿真优化次数
    last_jar_diff: Optional[datetime] = None  # 最近一次真机vs JAR差异时间
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CollectionItem(BaseModel):
    id: int
    remote_id: int
    title: str
    user: Optional[str] = None
    source_count: int = 0
    actual_count: int = 0
    downloads: int = 0
    date: Optional[str] = None
    type: str  # book / rss，与 DDL 字段名一致
    fetched_at: Optional[datetime] = None
    json_url: Optional[str] = None
    status: Optional[str] = None  # 派生字段：downloaded/downloading/not_downloaded（由 fetched_at 和 actual_count 计算）

class DebugHistoryItem(BaseModel):
    id: int
    source_id: int
    status: str  # pass / fail / timeout / error（success 可由 status=='pass' 派生）
    trigger: Optional[str] = None  # ai / web / cli
    stage: Optional[str] = None   # 失败阶段
    confidence: Optional[str] = None
    search_status: Optional[str] = None  # pass / fail / skip
    detail_status: Optional[str] = None
    toc_status: Optional[str] = None
    content_status: Optional[str] = None
    message: Optional[str] = None
    fix_applied: Optional[dict] = None
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class DeviceItem(BaseModel):
    id: int
    name: str
    ip: str
    port: int  # HTTP 端口；WebSocket 端口 = port + 1（Legado 源码硬编码，无需独立字段）
    auth_token: Optional[str] = None
    is_default: bool = False
    last_test_status: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    jvm_status: str
    source_count: int

class ImportResult(BaseModel):
    ok: bool
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = []

# === WebSocket 消息格式 ===

class DebugWSMessage(BaseModel):
    """WebSocket 调试消息（遵循 ADR-13 协议）"""
    type: str        # log / error / result / progress / complete
    task_id: str     # UUID4
    timestamp: float
    data: dict       # 消息体，结构因 type 而异
    # type=log:    {"stage": "search", "message": "..."}
    # type=error:  {"stage": "search", "message": "...", "stack_trace": "..."}
    # type=result: {"success": true, "confidence": "high", "stages_passed": [...], "stages_failed": [...]}
    # type=progress: {"current": 5, "total": 10, "source_name": "..."}
    # type=complete: {"total_tested": 10, "passed": 8, "failed": 2}
```

***

## 补充：服务端日志策略

### 日志配置

```python
# legado_client/server/app.py 中配置

import logging
from logging.handlers import RotatingFileHandler

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = config.output_dir / "server.log"

# 日志级别（可通过环境变量 LEGADO_LOG_LEVEL 配置，默认 INFO）
log_level = os.getenv("LEGADO_LOG_LEVEL", "INFO").upper()

# 根日志配置
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),                              # 控制台输出
        RotatingFileHandler(                                  # 文件轮转
            LOG_FILE, maxBytes=10*1024*1024, backupCount=5   # 10MB/文件，保留5个
        )
    ]
)

# 第三方库日志降级
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

### 请求日志中间件

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录 API 请求日志（跳过 /ws 和 /assets）"""
    if request.url.path.startswith(("/ws", "/assets")):
        return await call_next(request)

    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.0f}ms)")
    return response
```

### 日志级别规范

| 级别      | 使用场景                           |
| ------- | ------------------------------ |
| ERROR   | 数据库连接失败、JVM 崩溃、文件读写异常          |
| WARNING | 数据库降级、请求超时、HTML 解析降级           |
| INFO    | API 请求记录、调试任务启动/完成、源导入结果       |
| DEBUG   | SQL 查询详情、WebSocket 消息、JVM 通信内容 |

***

## 补充：API 安全与限制

### 文件上传限制

```python
# legado_client/server/app.py

# 文件上传大小限制：10MB（单个 JSON 文件通常 < 1MB，10MB 足够覆盖大合集）
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/import/file")
async def import_file(file: UploadFile = File(..., max_length=MAX_UPLOAD_SIZE)):
    ...
```

### API 请求频率限制

```python
# 使用 slowapi 限流（可选依赖）
# 限制：每分钟 60 次请求（单 IP），调试接口每分钟 10 次

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 应用到调试接口
@router.post("/debug/start")
@limiter.limit("10/minute")
async def debug_start(request: Request, ...):
    ...
```

**说明**：由于系统仅绑定 127.0.0.1 本地使用，频率限制为可选安全措施，默认不启用。如需部署到非本地环境，必须启用。
