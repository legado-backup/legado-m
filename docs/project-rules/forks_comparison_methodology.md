# 延伸版本对比方法论规范

> 本文档已收敛：延伸版本清单与活跃度数据统一以 [forks-reference.md](./forks-reference.md) 为唯一权威源（本文档旧域名 momo-b5a.pages.dev 已失效、27+ 版本数据已过时，勿再引用）。
>
> 当 AI 对 Legado（阅读M）项目进行网络层/前端/协程/WebView/数据管理等组件优化或功能借鉴时，**必须**遵循本规范对比开源阅读生态的其他延伸版本，避免闭门造车。
>
> 本规范由 2026-07-06 的"网络性能与稳定性深度分析"任务沉淀而来，固化对比方法论与踩坑经验；版本清单、活跃度快照、对比优先级矩阵见 forks-reference.md。

---

## 一、适用场景

### 1.1 强制触发条件

满足以下任一条件，必须按本规范执行延伸版本对比：

| 场景 | 说明 | 对比深度 |
|------|------|----------|
| **网络组件优化** | OkHttp/Cronet/拦截器/Cookie/重试/代理/DNS/缓存 | 全量对比（见 3.1） |
| **协程/多线程改造** | Coroutine 封装/线程池/锁/Dispatcher/runBlocking | 全量对比 |
| **WebView 组件改造** | BackstageWebView/WebViewPool/JS 桥/登录 | 全量对比 |
| **前端功能新增** | modules/web/ 下的 Vue3 功能新增或重构 | 全量对比 |
| **数据管理功能** | 备份/恢复/导入导出/书架管理 | 全量对比 |
| **阅读体验功能** | TTS/翻页/排版/主题/手势 | 选择性对比（按功能点） |

### 1.2 可跳过条件

以下场景无需对比延伸版本：
- 纯 Bug 修复（仅修本项目代码，无架构改动）
- 纯文档变更
- Skill 内部优化（legado-source-creator 等）
- 书源/订阅源创建（使用 legado-source-creator Skill 即可）

---

## 二、版本清单与优先级矩阵（引用）

延伸版本清单（主线/Max 系列/独立分支/独立项目）、上游活跃度快照、**对比优先级矩阵**统一见 [forks-reference.md](./forks-reference.md)，本文档不再维护副本。对比前以该文件为准选择 3-5 个优先对比版本。

## 仓库可达性预检

**强制规则**：对比前必须先验证仓库可达性，避免基于失效仓库做分析。仓库列表以 forks-reference.md 为准。

```bash
# 预检脚本（PowerShell），将 $repos 替换为 forks-reference.md 中的目标仓库
$repos = @("owner1/repo1", "owner2/repo2")
foreach ($repo in $repos) {
    $code = (Invoke-WebRequest "https://api.github.com/repos/$repo" -Method Head -SkipHttpErrorCheck).StatusCode
    Write-Host "$repo => $code"
}
```

> 注：仓库状态会变化（404 可能是删除/私有/改名/owner 改名），每次对比前必须重新预检；404 仓库跳过，不要基于缓存数据做分析。

---

## 三、对比方法论（五阶段）

### Phase 1: 准备阶段（5 分钟）

#### 3.1.1 确定对比目标

根据优化领域，从 forks-reference.md 的优先级矩阵选择 3-5 个优先对比版本。

#### 3.1.2 创建临时对比目录

```bash
mkdir -p temp/forks-comparison
cd temp/forks-comparison
```

#### 3.1.3 浅克隆目标版本

```bash
# 浅克隆，只取最新提交，节省时间
git clone --depth 1 https://github.com/{owner}/{repo}.git {别名}
```

**重要**：
- 使用 `--depth 1` 浅克隆，避免下载完整历史
- 克隆失败时记录失败原因，不要臆测
- 仓库 404 时跳过，不要基于缓存数据做分析

### Phase 2: 分类对比（按组件维度）

#### 3.2.1 网络层对比清单

| 文件 | 对比维度 |
|------|----------|
| `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` | SSL 配置、DNS 缓存、Cronet 加载、拦截器链、代理实现 |
| `app/src/main/java/io/legado/app/help/http/OkHttpUtils.kt` | 重定向处理、decompressed() 实现、日志标记 |
| `app/src/main/java/io/legado/app/help/http/CronetInterceptor.kt` | HTTP→HTTPS Referer 修正 |
| `app/src/main/java/io/legado/app/help/http/CronetCoroutineInterceptor.kt` | Cookie 处理逻辑、内部 API 依赖、异常处理 |
| `app/src/main/java/io/legado/app/help/http/DecompressInterceptor.kt` | Brotli 支持、promisesBody 实现 |
| `app/src/main/java/io/legado/app/help/http/CookieManager.kt` | runBlocking 使用、Cookie 同步逻辑 |
| `app/src/main/java/io/legado/app/help/http/CookieStore.kt` | Cookie 淘汰策略、线程安全 |
| `app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt` | CancellationException 处理 |
| `app/src/main/java/io/legado/app/help/ConcurrentRateLimiter.kt` | 数据结构、锁机制、fetchEnd |
| `app/src/main/java/io/legado/app/help/http/SSLHelper.kt` | SSL 配置 |
| `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` | runBlocking、回调清理、SSL 错误处理 |
| `app/src/main/java/io/legado/app/lib/cronet/*.kt` | Cronet 完整实现 |

#### 3.2.2 协程/多线程对比清单

| 文件 | 对比维度 |
|------|----------|
| `app/src/main/java/io/legado/app/help/coroutine/Coroutine.kt` | CancellationException 处理、cancel 回调、超时处理 |
| `app/src/main/java/io/legado/app/help/coroutine/CompositeCoroutine.kt` | 组合协程管理 |
| `app/src/main/java/io/legado/app/utils/FlowExtensions.kt` | 并行 Flow 扩展 |
| `app/src/main/java/io/legado/app/data/dao/BookSourceExtensions.kt` | mutexMap 线程安全 |

#### 3.2.3 WebView 对比清单

| 文件 | 对比维度 |
|------|----------|
| `app/src/main/java/io/legado/app/help/webView/WebViewPool.kt` | 池化策略、容量、清理、销毁重试 |
| `app/src/main/java/io/legado/app/help/webView/PooledWebView.kt` | 上下文切换 |
| `app/src/main/java/io/legado/app/help/webView/WebJsExtensions.kt` | JS 桥设计 |
| `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt` | 复用回调、closed 标志、isActiveWebView |

#### 3.2.4 前端对比清单

| 文件 | 对比维度 |
|------|----------|
| `modules/web/package.json` | 依赖版本 |
| `modules/web/vite.config.ts` | 构建配置、chunk 拆分 |
| `modules/web/src/main.ts` | 入口逻辑 |
| `modules/web/src/App.vue` | 根组件 |
| `modules/web/src/router/*.ts` | 路由组织 |
| `modules/web/src/views/*.vue` | 页面清单 |
| `modules/web/src/api/*.ts` | API 封装 |
| `modules/web/src/store/*.ts` | 状态管理 |

### Phase 3: 差异识别（逐文件对比）

#### 3.3.1 对比命令

```bash
# 单文件对比（本项目 vs 目标版本）
diff -u app/src/main/java/io/legado/app/help/http/HttpHelper.kt \
        ../{别名}/app/src/main/java/io/legado/app/help/http/HttpHelper.kt

# 目录对比（前端 src）
diff -rq modules/web/src/ ../{别名}/modules/web/src/
```

#### 3.3.2 差异记录格式

每个差异必须记录：

```markdown
### X.Y 文件名差异

**版本**：{延伸版本名}
**文件**：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
**差异类型**：新增 / 修改 / 删除

**本项目实现**：
\`\`\`kotlin
// 引用本项目源码（带行号）
\`\`\`

**延伸版本实现**：
\`\`\`kotlin
// 引用延伸版本源码
\`\`\`

**差异分析**：
- 收益：XXX
- 风险：XXX
- 是否值得借鉴：是/否
```

#### 3.3.3 关键约束

1. **必须引用实际源码**，不能只描述差异
2. **必须标注文件路径和行号**
3. **必须评估收益和风险**
4. **不能信任 GitHub git trees API**（见 forks-reference.md 踩坑警示）

### Phase 4: 价值评估

#### 3.4.1 评估维度

| 维度 | 评分（1-5） | 说明 |
|------|------------|------|
| **用户价值** | 1=无关紧要，5=解决核心痛点 | 是否解决用户实际遇到的问题 |
| **实现复杂度** | 1=简单（<50行），5=复杂（>500行） | 实现工作量 |
| **风险等级** | 1=无风险，5=可能导致功能不可用 | 对现有功能的影响 |
| **架构兼容性** | 1=完全冲突，5=无缝集成 | 与现有架构的契合度 |
| **维护成本** | 1=一次性，5=持续高维护 | 后续维护负担 |

#### 3.4.2 借鉴决策矩阵

| 综合评分 | 决策 | 说明 |
|----------|------|------|
| 用户价值≥4 且 风险≤2 | **强烈推荐借鉴** | 高价值低风险，优先实施 |
| 用户价值≥3 且 风险≤3 | **推荐借鉴** | 中等价值，可规划实施 |
| 用户价值≥3 且 风险≥4 | **谨慎借鉴** | 需充分测试，分阶段实施 |
| 用户价值≤2 | **不建议借鉴** | 投入产出比低 |

### Phase 5: 借鉴决策与输出

#### 3.5.1 输出文档

对比分析结果写入 `docs/specs/{功能名}/` 下的 design.md 对应章节，格式：

```markdown
# Legado 延伸版本 {领域} 对比分析

## 1. 延伸版本概览（表格）
## 2. 逐文件对比矩阵（表格）
## 3. 各版本独有优化清单
## 4. 可借鉴的优化汇总（按收益/风险排序）
## 5. 本项目相对于延伸版本的缺失
## 6. 借鉴建议（优先级分级）
```

#### 3.5.2 决策输出

对每个可借鉴项，输出：

```markdown
| 优化项 | 来源 | 收益 | 风险 | 建议 | 实施步骤 |
|--------|------|------|------|------|----------|
| XXX | {版本名} | ⭐⭐⭐ | 低 | 推荐借鉴 | 1. ... 2. ... |
```

---

## 四、对比维度深度清单

### 4.1 网络层必查项

- [ ] OkHttp 配置（SSL/DNS/Cronet/拦截器链/代理）
- [ ] 重定向处理（301/302/303/307/308）
- [ ] Cookie 管理（同步逻辑/淘汰策略/线程安全）
- [ ] 解压支持（gzip/deflate/br）
- [ ] 代理实现（HTTP/SOCKS4/SOCKS5/认证）
- [ ] 限流器（数据结构/锁/fetchEnd）
- [ ] 异常处理（CancellationException/IOException 包装）
- [ ] Cronet 集成（Cookie 双路径/内部 API 依赖）
- [ ] 日志拦截器（请求/响应/耗时/来源标记）

### 4.2 协程/多线程必查项

- [ ] CancellationException 处理（是否 rethrow）
- [ ] cancel 回调协程作用域（是否泄漏）
- [ ] 超时处理（TimeoutCancellationException 语义）
- [ ] 线程池数量与容量
- [ ] @Synchronized 使用是否合理
- [ ] Mutex 使用是否合理
- [ ] 并发集合选择是否正确（HashMap vs ConcurrentHashMap）
- [ ] runBlocking 使用（主线程阻塞风险）
- [ ] Dispatcher 选择（IO/Main/Default）

### 4.3 WebView 必查项

- [ ] 池化策略（容量/复用/清理/销毁重试）
- [ ] 复用回调错乱防护（closed 标志/isActiveWebView）
- [ ] mHandler 清理（removeCallbacksAndMessages）
- [ ] SSL 错误处理（是否 proceed）
- [ ] runBlocking 使用（主线程阻塞）
- [ ] JS 桥设计（接口名随机化/结果中转/ Promise 模式）
- [ ] 上下文切换（MutableContextWrapper）

### 4.4 前端必查项

- [ ] 依赖版本（package.json）
- [ ] 构建配置（vite.config.ts）
- [ ] 路由组织（router/*.ts）
- [ ] 页面清单（views/*.vue）
- [ ] API 封装（api/*.ts）
- [ ] 状态管理（store/*.ts）
- [ ] 主题系统
- [ ] 响应式设计
- [ ] 性能优化（代码分割/虚拟滚动/懒加载）
- [ ] 无障碍（ARIA/对比度/键盘焦点）

---

## 五、踩坑经验（强制阅读）

> 通用踩坑警示（git trees API 缓存、仓库 404 语义、前端源码位置、PowerShell curl 别名）见 [forks-reference.md](./forks-reference.md)「关键踩坑警示」，此处仅保留本规范独有条目。

### 5.1 WebFetch 对 raw.githubusercontent.com 失败

**现象**：WebFetch 工具获取 `raw.githubusercontent.com` 上的文件经常失败。

**应对**：
- 改用 `git clone --depth 1` 浅克隆整个仓库
- 或用 `curl.exe -sL https://raw.githubusercontent.com/...`
- 或用 `Invoke-WebRequest -Uri ... -OutFile ...` 下载后 Read

### 5.2 "网络层有改动" 的过度估计

**现象**：假设所有延伸版本都有网络层改动。

**真相**：2026-07-06 实测 9 个对比版本中，仅 3 个有实质网络层改动，其余与本项目 fork 源完全一致。

**应对**：
- 先 `diff -rq` 快速判断是否有差异
- 无差异的版本跳过，节省时间
- 不要为了"对比"而对比

### 5.3 并行 TaskOutput 调用丢失

**现象**：并行调用多个 TaskOutput 时，部分返回 "The toolcall result is missing."

**应对**：
- 改为串行调用 TaskOutput
- 或使用 `block=false` + 短超时重试
- 子代理优先使用 `run_in_background: true` 异步执行

---

## 六、输出规范

### 6.1 分析文档

- 位置：`docs/specs/{功能名}/` 下的 design.md 对应章节
- 命名：在 design.md 中以章节形式组织
- 行数上限：1000 行（超过说明分组过大，应拆分）
- 必须包含：数据来源、对比方法、差异矩阵、借鉴建议

### 6.2 借鉴决策表

每个对比任务必须输出决策表：

```markdown
| 排名 | 优化项 | 来源版本 | 收益 | 风险 | 建议 |
|------|--------|----------|------|------|------|
| 1 | XXX | {版本名} | ⭐⭐⭐⭐⭐ | 中 | 强烈推荐借鉴 |
| 2 | XXX | {版本名} | ⭐⭐⭐ | 低 | 推荐借鉴 |
```

### 6.3 与权威源/主规范的关系

- **forks-reference.md**：延伸版本清单、活跃度数据、对比优先级矩阵的唯一权威源
- **本规范**：详细对比方法论和踩坑经验（执行指南）
- **临时分析文档**：记录每次对比的具体结果（执行证据）

三者关系：forks-reference.md 提供对比对象，本规范指导生成临时分析文档，临时分析文档支撑 OpenSpec 四文档设计。

---

## 七、与 OpenSpec 工作流的集成

当延伸版本对比用于 OpenSpec 设计任务时：

1. **Phase 1（需求分析）**：识别是否需要延伸版本对比（按 1.1 触发条件）
2. **Phase 2（生成四文档）**：spec.md 的 "Alternatives Considered" 必须引用对比结果
3. **Phase 3（用户审查）**：design.md 的 "Architecture Decisions" 必须基于对比决策
4. **Phase 4（实施）**：实施时引用对比文档中的源码示例
5. **Phase 5（文档同步）**：将对比结论沉淀到本规范（如有新踩坑）

### 7.1 spec.md 必须包含

```markdown
## Alternatives Considered

### 方案A：借鉴 {版本名} 的 XXX
- 来源：design.md 对比分析章节
- 收益：XXX
- 风险：XXX

### 方案B：借鉴 {版本名} 的 XXX
- ...
```

### 7.2 design.md 必须包含

```markdown
## Architecture Decisions

### ADR-001：采用 XXX 方案（借鉴 {版本名}）

**Context**：本项目当前 XXX 存在 YYY 问题
**Concern**：ZZZ
**Decision**：借鉴 {版本名} 的 XXX 实现
**Goal**：AAA
**Tradeoff**：BBB
**Status**：Accepted
```

---

## 八、检查清单

对比任务完成后，必须核对：

- [ ] 是否预检了仓库可达性？
- [ ] 是否使用 `git clone --depth 1` 获取源码？
- [ ] 是否以 git clone 实测为准（而非 API）？
- [ ] 是否引用了实际源码（带文件路径和行号）？
- [ ] 是否评估了每个差异的收益和风险？
- [ ] 是否输出了借鉴决策表？
- [ ] 是否记录了新的踩坑经验（如有）？
- [ ] 是否将对比结论写入 design.md 对应章节？
- [ ] 是否在 OpenSpec 四文档中引用了对比结果？
- [ ] 版本清单/活跃度是否引用 forks-reference.md（而非本文档副本）？

---

## 九、参考案例

> 以下案例原位于 `docs/temp-analysis/`，已清理。分析结论已沉淀到对应功能的设计文档中。

- **网络层对比案例**：已沉淀至 [network-perf-stability/design.md](../specs/network-perf-stability/design.md)
- **前端对比案例**：已沉淀至对应 specs/ 设计文档
- **Cronet 深度分析案例**：已沉淀至 [network-perf-stability/design.md](../specs/network-perf-stability/design.md)
- **多线程深度分析案例**：已沉淀至 [app-stability-round2/design.md](../specs/app-stability-round2/design.md)

---

**版本历史**

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-06 | 1.0 | 初版，由网络性能与稳定性深度分析任务沉淀 |
| 2026-08-30 | 2.0 | 删旧保新收敛为薄壳：版本清单/活跃度/优先级矩阵移交 forks-reference.md 唯一权威源，删除失效域名与过时数据，保留独有方法论 |
