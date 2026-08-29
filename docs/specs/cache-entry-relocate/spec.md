# Spec: "我的"页功能归堆重构（缓存管理入口迁移 + 诊断三件套迁移 + 全量归堆）

## Intent

对"我的"页做一次系统性归堆重构，而非点状修补：

1. **缓存管理入口迁移**：从"同步与服务"迁入精准管理聚合页（存储管理与下载管理之间），消除"缓存管理 vs 存储管理"混淆与分组语义错位
2. **诊断三件套迁移**：崩溃日志/保存日志/创建堆转储从"关于 → 其他"整体迁入精准管理页新"日志与诊断"卡片，关于页瘦身为纯信息类
3. **全量归堆（6 组框架）**："我的"页 24 行按功能域重组为 6 组，名实一致（高亮规则归规则组、AI 设置归工具组、关于/退出独立成组），并消除网址记录双入口

页面能力本体（各 Activity/Dialog）零改动，零功能增删。

## Scope

### In（本次实现）

- `ui/main/my/MySettingsData.kt`：
  - 分组重排为 6 组（内容与规则/外观/同步与服务/工具/精准管理/关于）
  - `highlightRule` 行迁入"内容与规则"组；`ai_setting` 行迁入"工具"组
  - 同步与服务组移除 `cacheManage` 行；工具组移除 `urlRecord` 行（消双入口）
  - `handleSettingsRowClick` 移除 `"cacheManage"`、`"urlRecord"` 路由分支与对应 import
  - 新增"关于"分组（about/exit），精准管理独立成组（组标题复用 `R.string.precise_manage`）
- `ui/config/PreciseManageFragment.kt`：新增 `onCacheManageClick` 回调；平移 AboutFragment 五个诊断私有方法（saveLog/createHeapDump/copyLogs/copyHeapDump/dumpLogcat）与 waitDialog
- `ui/config/PreciseManageScreen.kt`：数据管理卡片加"数据管理"标题并插入"缓存管理"行（存储管理与下载管理之间）；新增"日志与诊断"标题卡片 3 行（崩溃日志/保存日志/创建堆转储）
- `ui/about/AboutFragment.kt`："其他"分区删除三件套三行 + 删除五个诊断私有方法 + 删对应 KEY 常量 + 清理无用 import
- `values/strings.xml` + `values-zh/strings.xml`：
  - 改值 2 条：`config_category_appearance` "外观与 AI"→"外观"；`config_category_tools` "工具与关于"→"工具"
  - 新增 2 条：`config_category_about`（"关于"）；`log_diagnostics`（"日志与诊断"）

### Out（明确不做）

- 各功能页本体零改动：CacheManageActivity / StorageManageActivity / CrashLogsDialog / UrlRecordActivity / 其余全部行目标页
- 分组标题 `config_category_content`（"内容与规则"）与 `config_category_sync`（"同步与服务"）名实已符，不改
- 书签/阅读记录保持一级直达，不进精准管理二级页、不单独成组
- MainActivity 崩溃提示直达 CrashLogsDialog 链路（L2255）、音频缓存通知直达 CacheManageActivity 链路（AudioCacheTaskManager L410）——均不经入口行
- 旧版 CacheActivity（WebDavTaskService 通知遗留指向，独立问题不扩大）
- AboutFragment 其余功能与 checkUpdate/showMdFile/waitDialog（checkUpdate 仍用）

## Approach

### Selected Approach

**6 组归堆 + 入口迁移 + 诊断方法平移**（6 文件改动，全部为入口层/数据构建层）。理由：

1. 现状组名已含归堆意图（"内容与规则"/"外观与 AI"）但行归位未跟上，本方案把名实一致补完，不是发明新框架
2. 全部改动点经过 C1-C10 十项源码核查（分组标题引用面/搜索零假设/路由 key/组件签名/直达路径），无未知风险
3. 诊断方法平移（AboutFragment 全删、PreciseManageFragment 承接）避免单调用方共享抽象；行为逐字节一致
4. 零数据流/零数据库/零功能增删，编译+模拟器 L2 即可全量验证

### Alternatives Considered

| 替代方案 | 否决理由 |
|----------|---------|
| 方案二（保守微调）：不动分组框架，只做缓存迁出/诊断迁入/网址记录消双入口/高亮归组/AI 归位 | 五件事做完后"工具与关于"仍有 9 行混杂（记录/工具/聚合/信息/退出），"关于"埋在工具组尾部，P4/P5 问题不解决；用户已明确要全量归堆 |
| 方案一变体（7 组）：书签/阅读记录独立"我的记录"组 | 为 2 行单开组头收益低；"工具"组语义可容纳功能与记录；组数越多扫视成本越高 |
| 深度融合：缓存管理并入存储管理页 | 两套 ViewModel 与交互模式（任务列表 vs 空间统计）完全不同，回归风险高收益低 |
| 保留网址记录双入口 | 与 bugfix-20260824 ⑥ 文件管理双入口清理先例冲突；双入口造成用户困惑与维护漂移 |
| 诊断方法抽共享 helper | AboutFragment 侧全删后仅剩单调用方，共享抽象属过度设计 |
| 只迁崩溃日志+保存日志，堆转储留关于页 | 拆散诊断三件套，留下"关于页孤行堆转储"的更差形态 |
| 缓存管理行放"工具与关于"顶层（不入精准管理） | 与精准管理聚合页定位冲突；"我的"页顶层行数膨胀 |

### Drawbacks

| 已知缺点 | 接受理由 |
|----------|---------|
| 老用户需重新熟悉入口位置 | 6 组语义同质，一次学习成本；设置搜索自动跟随可兜底查找 |
| 设置搜索不再索引"缓存管理"行（与精准管理现有 4 子项行为一致） | 聚合页子项本就不被索引，非新增退化 |
| 缓存管理"上传云端"与同步分组关联减弱 | 上传云端是缓存管理次级能力，主体语义归位优先 |
| "工具"组 7 行仍含功能+记录两类语义 | 6 组约束下的最优折中；若用户后续觉得杂可升级 7 组（独立"我的记录"），纯数据构建改动 |
| "外观"组从 4 行减至 3 行、关于组仅 2 行 | 组行数不均是语义归堆的正常结果，非问题 |

### Prior Art

- `docs/specs/precise-manage/`：精准管理聚合页（借鉴 Legado_Max），本次接入缓存行与诊断卡片
- `docs/specs/bugfix-20260824/` ⑥：文件管理双入口清理先例，本次网址记录对齐同样处理
- `MySettingsData.kt` 头注释（header-search-unify AD-03/AD-05）：两宿主共用数据构建+路由防漂移，归堆重构天然继承
- 现状组名"内容与规则"/"外观与 AI"：前一轮归堆意识的名字遗存，本方案补完行归位

## Requirements

- R1: "我的"页呈 6 组：内容与规则/外观/同步与服务/工具/精准管理/关于（顺序固定）
- R2: "内容与规则"组含 书源管理/订阅源管理/TXT目录规则/替换净化/辞典规则/高亮规则（高亮自工具组迁入）
- R3: "外观"组含 主题模式/外观套件/主题设置（AI 设置迁出，组名改"外观"）
- R4: "同步与服务"组含 备份与恢复/公共Web中继/Web服务（缓存管理迁出）
- R5: "工具"组含 AI设置/自动任务/订阅搜索/我的精选书籍/书签/阅读记录/其它设置（组名改"工具"）
- R6: "精准管理"组仅精准管理聚合入口行；页内数据管理卡片（带"数据管理"标题）含 网址记录/存储管理/缓存管理/下载管理/文件管理（缓存行在存储与下载之间）
- R7: 精准管理页新增"日志与诊断"卡片（带标题）：崩溃日志→CrashLogsDialog / 保存日志→saveLog 平移 / 创建堆转储→createHeapDump 平移，行为与原关于页逐字节一致
- R8: "关于"组含 关于/退出
- R9: 工具组"网址记录"一级行删除（消双入口），UrlRecordActivity 仅从精准管理进入
- R10: 设置搜索页与我的页行为一致（共用 buildSettingsSections 自动跟随 6 组结构）
- R11: 字符串变更：改值 2 条（appearance/tools 组名）+ 新增 2 条（about 组名/log_diagnostics 卡片标题），其余复用
- R12: MainActivity 崩溃提示直达与音频缓存通知直达链路不变

## Scenarios

| # | 场景 | 预期 |
|---|------|------|
| S1 | 我的页总览 | 6 组按序：内容与规则(6行)/外观(3行)/同步与服务(3行)/工具(7行)/精准管理(1行)/关于(2行) |
| S2 | 内容与规则组点击高亮规则 | 打开 HighlightRuleActivity（与迁移前行为一致） |
| S3 | 工具组点击 AI 设置 | 打开 AI_CONFIG 配置页（与迁移前行为一致） |
| S4 | 精准管理 → 数据管理卡片 → 点击"缓存管理" | 打开 CacheManageActivity 三 Tab 正常 |
| S5 | 同步与服务组 | 仅 备份与恢复/公共Web中继/Web服务 三行 |
| S6 | 精准管理 → 日志与诊断卡片 → 崩溃日志/保存日志/创建堆转储 | 三项行为与原关于页一致 |
| S7 | 关于组 | 仅 关于/退出 两行；进入关于页"其他"分区无三件套 |
| S8 | 全局查找网址记录入口 | 仅精准管理数据管理卡片一处（工具组无该行） |
| S9 | 设置搜索页搜索"高亮"/"缓存"/"AI" | 归属分组正确显示，行为与我的页一致 |
| S10 | 音频缓存通知点击 / App 崩溃后点击提示 | 分别直达 CacheManageActivity / CrashLogsDialog，不受影响 |
| S11 | 存储/缓存两行分别点击 | 分别进 StorageManageActivity / CacheManageActivity，互不串扰 |
| S12 | 保存日志未设置备份目录 | toast 提示行为与原一致 |
