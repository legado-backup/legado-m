# spec.md - 日志系统升级改造

## Intent

让测试包（debug）日志默认达到 AI 解析所需的详细程度，并为用户提供系统级的日志管理能力（统一入口、搜索、多选删除、详情查看、导出、一键清除），替代当前碎片化的日志管理形态。

## Scope

**包含**：
- `recordLog` 默认值按包类型区分（debug=true / release=false）
- DEBUG 级日志在 recordLog 开启时完整记录（内存+文件）
- 内存日志容量 100 → 500
- 新增全屏「日志管理」页：应用日志 / 崩溃日志 / 文件日志 / 堆转储 4 Tab
- 关键字搜索、级别筛选、多选删除、单条详情、分享导出、一键清除（二次确认）
- 精准管理页「日志与诊断」区入口整合

**不包含**：
- 不引入第三方日志库（Timber 等项目禁用）
- 不迁移/改造现有 20 处 AppLogDialog 入口与 AppLogDialog、CrashLogsDialog 本身
- 不提供应用内 .hprof 解析查看器
- 不改变 release 包默认日志行为与现有 Tag 体系（30+ 模块 Tag 保持不变）
- 无数据库变更

## Approach

### Selected Approach

复用 AppLog 现有四级体系（ERROR/WARN/INFO/DEBUG）与 LogUtils 文件基础设施，做**守卫逻辑调整**（最小侵入）：recordLog 默认值按 `BuildConfig.DEBUG` 区分；`putDebug/putDebugWithTag` 的丢弃分支改为「recordLog 开启即记录」。UI 层新建 Compose 全屏 LogActivity，4 个 Tab 分别对接现有数据源（AppLog.mLogs / crash 目录 / logs 目录 / heapDump 目录），操作全部经 `Coroutine.async` 走 IO 线程。理由：日志基础设施（LogUtils 轮转清理、NetworkLog 脱敏、CrashHandler 双写、saveLog 打包）均已成熟可用，仅需接线与守卫调整，改动面可控。

### Alternatives Considered

| 备选方案 | 否决理由 |
|---------|---------|
| 引入 Timber/自研日志库全量替换 | 项目 Code Style 明确禁用 Timber；全量替换 1195 处 AppLog 调用点，改动面与回归风险极大，收益仅为等价能力 |
| 在现有 Dialog 内修补（不建统一页） | 碎片化依旧；多选删除/文件列表/一键清除等交互在 Dialog 形态承载极差；悬浮球注释已自认 Dialog 上限 |
| 日志级别改为 5 级（新增 VERBOSE） | 现有四级已够用，AI 解析依赖的是 Tag 体系而非更细级别；加级别需全量梳理调用点，违背最小改动 |

### Drawbacks

- **内存占用增加**：日志容量 100→500，按单条 2KB 上限估算约 1MB 峰值，可接受；`truncateSafely` 截断保护保持不变。
- **debug 包磁盘写入增加**：recordLog 默认开启后持续写盘；已有 7 天自动清理 + AsyncFileHandler 异步写盘兜底，风险可控。
- **风险点**：LogActivity 大文件查看可能 OOM → 兜底预案：文件日志查看仅读取尾部 500 行并截断。
- **风险点**：一键清除误删仍有价值的崩溃现场 → 兜底预案：二次确认弹窗列出将清除的文件数量与总大小。

## Requirements

### Requirement: 测试包默认详细日志
`recordLog` 配置在无用户显式设置时的默认值：debug 包为 true，release 包为 false。用户显式设置后以设置为准（两包行为一致）。

### Requirement: DEBUG 级日志完整记录
recordLog 开启时，`putDebug/putDebugWithTag` 产生的日志进入内存列表并写入文件；release 包下 DEBUG 级 logcat 输出行为保持现状（BuildConfig.DEBUG 守卫）。

### Requirement: 内存日志容量
AppLog 内存日志上限由 100 提升至 500，淘汰策略不变（最新在前，超限移除最旧）。

### Requirement: 日志管理中心
新增全屏日志管理页，含 4 个 Tab：
- **应用日志**：内存日志列表，支持 ERROR/WARN/INFO/DEBUG 级别筛选、关键字搜索、多选删除、单条详情（含 Throwable 完整堆栈）、单条复制
- **崩溃日志**：列出 crash 目录文件（文件名+大小+时间），支持查看全文、单删、多选删除、系统分享
- **文件日志**：列出 logs 目录文件（appLog-*.txt、network-log-*.txt），支持查看（尾部 500 行截断）、删除
- **堆转储**：列出 heapDump 目录 .hprof 文件（文件名+大小+时间），支持删除（不提供应用内打开）

### Requirement: 一键清除
日志管理页提供一键清除入口，弹确认框（列出各类日志条数/文件数），确认后清空内存日志 + logs 目录 + crash 目录 + heapDump 目录。

### Requirement: 日志导出
日志管理页提供导出入口，复用现有 saveLog 逻辑（logcat.txt + logs/ + crash/ 打包 logs.zip）。

### Requirement: 入口整合
精准管理页「日志与诊断」区新增「日志管理」入口；原「崩溃日志」入口改为跳转日志管理页崩溃 Tab；「保存日志」「创建堆转储」保留原逻辑。

## Scenarios

#### Scenario: 测试包默认记录调试日志
- **WHEN** 全新安装 debug 包且用户未修改记录日志设置
- **THEN** recordLog 为 true，putDebug/putDebugWithTag 日志进入内存并写入 logs 目录文件，AI 可通过 logs.zip 或 adb logcat 采集到 DEBUG 级内容

#### Scenario: 正式包默认行为不变
- **WHEN** 全新安装 release 包且用户未修改记录日志设置
- **THEN** recordLog 为 false，DEBUG 级日志不进内存不写文件，与改造前一致

#### Scenario: 用户显式设置优先
- **WHEN** 用户在设置中手动开启/关闭记录日志
- **THEN** 两类包均以用户设置为准，包类型不再影响

#### Scenario: 内存日志搜索与多选删除
- **WHEN** 用户在应用日志 Tab 输入关键字并进入多选模式删除选中项
- **THEN** 仅匹配关键字的日志参与筛选展示，选中的日志从内存列表移除，未选中项保留

#### Scenario: 崩溃日志单条分享
- **WHEN** 用户在崩溃日志 Tab 点击某条日志的分享操作
- **THEN** 调起系统分享该 crash 文件（FileProvider），无需先导出整包

#### Scenario: 大文件日志查看防 OOM
- **WHEN** 用户查看超过 500 行的文件日志
- **THEN** 仅展示尾部 500 行并提示已截断

#### Scenario: 一键清除需确认
- **WHEN** 用户点击一键清除并确认
- **THEN** 清空内存日志、logs/crash/heapDump 目录文件，操作在 IO 线程执行，完成后刷新各 Tab 列表

#### Scenario: 空态展示
- **WHEN** 任一 Tab 对应数据源为空（无日志/无文件）
- **THEN** 展示空态占位，不崩溃不白屏
