# 测试技术方案：rss-concurrency-and-checksource-optimization 真机测试

## Technical Approach

### 整体架构

```
verify_all_features.py v4
├── test_1: 并发配置修改生效（补充验证）
│   └── UI操作 + SharedPreferences 查询
├── test_2: domainCheckMode 交互（修复测试3）
│   └── 勾选域名CheckBox → 验证RadioGroup显示
├── test_3: 书源校验执行（真实数据）
│   ├── UI操作（长按→全选→校验）
│   ├── logcat 抓取 CheckSourceService 日志
│   └── 数据库 weight 查询
├── test_4: 订阅源校验执行（真实数据）
│   ├── UI操作（长按→全选→校验）
│   ├── logcat 抓取 CheckRssSourceService 日志（关键）
│   └── 数据库 weight 查询
├── test_5: 深度日志分析
│   └── 过滤 CheckSourceService/CheckRssSourceService/SourceWeightCalculator
└── test_6: 数据库 weight 验证
    └── pull DB + Python sqlite3 查询
```

### 关键技术点

#### 1. domainCheckMode RadioGroup 显示逻辑

**根因分析**（测试3 FAIL 的原因）：
- `dialog_check_source_config.xml` L62-81：`domain_check_mode_group` RadioGroup 默认 `android:visibility="gone"`
- `CheckSourceConfig.kt` L46-47：`domainCheckModeGroup.visibility = if (checkDomain.isChecked) View.VISIBLE else View.GONE`

**修复方案**：测试脚本中点击"校验设置"后，先勾选"域名"CheckBox（resource-id=`check_domain`），再 dump XML 验证 RadioGroup 显示。

#### 2. 数据库 weight 验证（设备无 sqlite3）

**问题**：MEmu 模拟器 `/system/bin` 无 sqlite3 二进制
**方案**：用 ADB pull DB 到本地，用 Python sqlite3 查询
- pull `/data/data/{PKG}/databases/legado.db` 到临时文件
- 同时 pull WAL/SHM 文件（Room WAL 模式）
- 用 `PRAGMA wal_checkpoint(TRUNCATE)` 合并 WAL
- 查询 `SELECT COUNT(*) FROM book_sources WHERE weight > 0`

#### 3. logcat 日志过滤策略

**过滤关键词**（只搜技术关键词，不搜业务数据）：
- `CheckSourceService` - 书源校验Service
- `CheckRssSourceService` - 订阅源校验Service
- `SourceWeightCalculator` - 权重计算器
- `weight` - weight 回填（搜函数名/变量名，不搜业务数据）
- `AppLog:V` - App 自定义日志
- `AndroidRuntime:E` - 崩溃日志

**输出安全**：日志分析只输出技术结论（Service是否启动/weight是否回填），不输出源名称/URL/域名。

#### 4. 真实数据状态确认

用户已将 `temp/output/book/groups/` 下的真实书源导入模拟器。测试前先确认数据存在：
- UI 检查：书源管理列表是否有数据
- 数据库检查：pull DB 查询 `SELECT COUNT(*) FROM book_sources`

## Architecture Decisions

### AD-01: 分层测试方案选择
- **Context**: 需要验证 UI+Service+数据三层，且要深度分析日志
- **Concern**: 单一测试方式覆盖度不足
- **Decision**: 采用分层综合测试（UI+logcat+DB）
- **Goal**: 全覆盖验证所有24项变更功能项
- **Tradeoff**: 测试时间较长（20-30分钟），但覆盖度最完整
- **Status**: Accepted

### AD-02: domainCheckMode 需勾选域名CheckBox
- **Context**: 测试3 FAIL，RadioGroup 默认 gone
- **Concern**: 直接 dump XML 看不到 RadioGroup
- **Decision**: 测试脚本先勾选域名CheckBox，再验证RadioGroup
- **Goal**: 准确验证 domainCheckMode UI交互
- **Tradeoff**: 增加一步UI操作，但符合真实用户操作路径
- **Status**: Accepted

### AD-03: pull DB 查询 weight（设备无sqlite3）
- **Context**: MEmu 设备无 sqlite3 二进制
- **Concern**: 无法直接在设备上查询数据库
- **Decision**: pull DB 到本地用 Python sqlite3 查询
- **Goal**: 验证 weight 字段回填
- **Tradeoff**: 需要处理 WAL/SHM 文件，但查询更灵活
- **Status**: Accepted

### AD-04: 日志过滤只搜技术关键词
- **Context**: logcat 日志可能含源名称/URL等敏感信息
- **Concern**: 输出敏感信息会触发审查中断
- **Decision**: 只搜技术关键词（Service名/类名/函数名），不搜业务数据
- **Goal**: 遵守 output-safety.md 规范
- **Tradeoff**: 可能遗漏部分业务日志，但技术验证足够
- **Status**: Accepted

### AD-05: 问题发现→记录→修复闭环（用户反馈强制）
- **Context**: 用户担心测试中发现问题后压缩上下文导致丢失，要求先记录到OpenSpec再修复
- **Concern**: 上下文压缩后可能忘记待修复的问题
- **Decision**: 测试中每发现一个问题立即追加到 `rss-concurrency-and-checksource-optimization/issues-found.md`
- **Goal**: 防止问题丢失，确保所有发现的问题都有追踪记录和修复状态
- **Tradeoff**: 增加文档维护成本，但保证问题不丢失
- **Status**: Accepted

## 问题发现→记录→修复闭环流程（AD-05 详细）

### 流程

```
[测试执行中发现问题]
  ↓ 立即（禁止"先继续测试后面再补"）
[追加到 issues-found.md]
  ├── 问题描述（现象+复现步骤）
  ├── 根因分析（代码层面）
  ├── 修复方案（具体修改点）
  ├── 验证结果（待验证/已验证PASS）
  └── 状态（待修复/修复中/已修复）
  ↓
[继续测试或立即修复]
  ├── 如阻断后续测试 → 立即修复
  └── 如非阻断 → 继续测试，最后统一修复
  ↓
[修复完成后]
  └── 回填 issues-found.md 状态为"已修复" + 验证结果
```

### 问题记录格式（issues-found.md）

```markdown
## Issue-{N}: {问题简述}

- **发现时间**：{YYYY-MM-DD HH:MM}
- **发现测试**：{测试N - 测试名}
- **问题描述**：{现象+复现步骤}
- **根因分析**：{代码层面分析}
- **修复方案**：{具体修改点}
- **涉及文件**：{文件路径}
- **状态**：待修复 / 修复中 / 已修复
- **验证结果**：待验证 / 已验证PASS / 已验证FAIL
- **备注**：{其他需要记录的信息}
```

### 权威源补充

- **主权威源**：tasks.md（任务状态）
- **补充权威源**：issues-found.md（问题清单，防止压缩丢失）
- **压缩恢复后**：必须读取 tasks.md + issues-found.md 才能完整恢复任务状态

## Data Flow

```
[测试执行]
  ↓
test_1: UI操作 → SharedPreferences查询
  ↓
test_2: UI操作（勾选域名）→ dump XML → 验证RadioGroup
  ↓
test_3: 书源校验执行
  ├── clear_logcat
  ├── UI操作（长按→全选→校验）
  ├── 等待执行（90秒）
  ├── 抓取 logcat（CheckSourceService/SourceWeightCalculator）
  └── 检查崩溃日志（AndroidRuntime:E）
  ↓
test_4: 订阅源校验执行（同 test_3，关键词改为 CheckRssSourceService）
  ↓
test_5: 深度日志分析
  ├── 抓取完整 logcat
  ├── 过滤 CheckSourceService
  ├── 过滤 CheckRssSourceService
  ├── 过滤 SourceWeightCalculator
  └── 过滤 weight 回填
  ↓
test_6: 数据库 weight 验证
  ├── pull legado.db（含WAL/SHM）
  ├── PRAGMA wal_checkpoint(TRUNCATE)
  ├── SELECT COUNT(*) FROM book_sources WHERE weight > 0
  └── SELECT COUNT(*) FROM rss_sources WHERE weight > 0
  ↓
[结果汇总 + 经验沉淀]
```

## File Changes

### 修改文件

| 文件 | 变更内容 |
|------|---------|
| `ai_tests/scripts/verify_all_features.py` | 重写为v4：修复test_3（勾选域名）、test_4-6用真实数据、增加weight验证和深度logcat分析 |

### 新建文件

| 文件 | 内容 |
|------|------|
| `ai_tests/docs/feature_test_lessons.md` | 测试经验教训沉淀（Python or陷阱、英文关键词、domainCheckMode需勾选域名、pull DB查询weight等） |
| `docs/specs/rss-concurrency-and-checksource-optimization/issues-found.md` | 测试发现的问题清单（问题发现→记录→修复闭环，防止压缩丢失） |

### 复用已有文件

| 文件 | 复用内容 |
|------|---------|
| `ai_tests/scripts/import_rss_source.py` | pull_db/push_db 逻辑（WAL模式处理） |
| `ai_tests/config.py` | ADB_PATH/MEMU_ADB_HOST/PACKAGE 常量 |
