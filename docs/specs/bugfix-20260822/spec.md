# 20260822 真机反馈 Bug 修复 — 需求规格（spec.md）

## Intent

修复用户 2026-08-22 持最新测试包（`io.legado.miss.app.debug`）实测反馈的 6 类问题，并对 `Downloadslogs(1).zip` 全量日志做**零遗漏深度分析**后逐项修复。核心目标：

1. 备份恢复页、订阅管理、主题顶栏 UI 全面**对齐 Archive**（`archive-ref/legado-08172114/`）
2. 消除 12 处 FATAL 崩溃 + 2 类应用代码运行时缺陷
3. 统计信息框隐藏但不删码
4. 修复完成立即打测试包，供用户验证

## Scope

### 做（In Scope）

- **备份恢复页**：`BackupConfigFragment` 从 `PreferenceFragment` → `ComposeSettingFragment`（样式对齐 Archive，含 WebDAV/S3 云存储、主题同步等设置项）
- **我的页统计框**：头部四框（书架书籍/使用书源/订阅源/累计阅读）隐藏，代码保留（`if(false)` 包裹）
- **FATAL 崩溃修复**：
  - `BookSourceActivity` 返回键递归 StackOverflow
  - `VideoPagerAdapter` ViewPager2 IndexOutOfBounds
  - `ThemeManageActivity` / `BookInfoComposeActivity` Manifest 未注册
- **应用代码运行时缺陷**：
  - `SourceNetworkClient.requestWithLoginCheck` `ClassCastException`（String→StrResponse）
  - `AnalyzeByJSonPath.getStringList` `NullPointerException`
- **订阅页管理设置**：新版/经典订阅切换生效（读 `AppConfig.modernRssPage`，RssFragment 双形态渲染，对齐 Archive）
- **主题设置顶栏管理**：行为对齐 Archive
- 修复后编译门禁 + 打测试包

### 不做（Out of Scope）

- **书源/订阅源本身的 JS 规则错误**（EcmaError/JSONPath 不匹配等，属书源数据质量问题，非应用代码缺陷）——仅在日志分析中记录统计，不修改书源
- **网络层异常**（DNS 解析失败/DoH 故障/连接重置等）：已确认多为环境/站点可达性问题，Cronet 已有自动降级 OkHttp 兜底，不属本次应用缺陷修复范围
- **不真机测试**（用户明确要求：本次全力修复，测试包由用户验证）

## Approach

### Selected Approach：对齐 Archive + 精准缺陷修复

1. **UI 对齐**：直接以 `archive-ref/legado-08172114/` 对应文件为蓝本，将本项目半迁移壳/旧实现升级为 Archive Compose 实现（备份页、订阅页、主题顶栏）
2. **崩溃修复**：按日志调用栈精准定位（onBackPressed 递归断环、ViewPager2 adapter 稳定 ID、Manifest 补注册）
3. **类型/空值容错**：对 JS 返回值做类型判断（`is StrResponse`/`is String`），对 JSONPath 解析结果判空
4. **编译门禁**：`./gradlew assembleAppDebug`（测试包 `io.legado.miss.app.debug`），通过后 `build-legado.bat` 打包

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 备份页保持 `PreferenceFragment` 不迁移 | 用户明确要求"样式没从 archive 搬迁过来"，不迁移=不满足需求 |
| 统计框直接删除 `MetricGrid`/`loadMetrics` | 用户明确"别删代码，后期优化"，必须保留代码 |
| 恢复旧 `onBackPressed` 逻辑但加防重入标志 | Archive 本身不覆写该方法，断环最优解是删除覆写，保留标志是过度设计 |
| `BookInfoComposeActivity`/`ThemeManageActivity` 用隐式 Intent | 两 Activity 是本项目/Archive 明确存在的 Compose 页面，正确做法是 Manifest 显式注册 |
| modernRssPage 仅改配置不搬渲染 | PreferKey 已存在但无消费方，只改配置=无效；必须搬 RssFragment 双形态渲染 |

### Drawbacks

- **备份页 Compose 化**：改动面较大（依赖 ComposeSettingFragment 体系 + 云存储设置项），存在少量 string/array 资源需补齐，编译期可能暴露缺失引用
- **modernRssPage 双形态**：RssFragment 需维护经典/现代两套渲染路径，复杂度上升；但 Archive 已有一致实现可整体对齐，风险可控
- **统计框 `if(false)`**：保留死代码块，存在轻微可读性代价，但满足"不删码"硬约束

### Prior Art

- Archive `archive-ref/legado-08172114/`：`ui/config/BackupConfigFragment.kt`、`ui/main/rss/RssFragment.kt`（modernRssPage 双形态）、`ui/config/ThemeManageActivity.kt`
- 本项目大迁移设计 `docs/specs/archive-ui-migration-202608/`

## Requirements

### FR-1 备份恢复页对齐 Archive
- FR-1.1 `BackupConfigFragment` 继承 `ComposeSettingFragment` 并实现 `buildPageSpec()`
- FR-1.2 设置项覆盖 Archive：云存储类型（WebDAV/S3）、WebDAV 配置、S3 配置、自动备份、主题同步等
- FR-1.3 缺失 string/array 资源补齐（`cloud_storage_types` 等）

### FR-2 我的页统计框隐藏
- FR-2.1 `MetricGrid` 渲染代码保留但以 `if(false)` 包裹
- FR-2.2 `MyFragment.loadMetrics()` 不调用（注释保留）

### FR-3 FATAL 崩溃消除
- FR-3.1 `BookSourceActivity` 删除 `initComposeHost`/`onBackPressed` 覆写（断递归环）
- FR-3.2 `VideoPagerAdapter` 覆写 `getItemId`/`containsItem` 保证 ID 稳定
- FR-3.3 Manifest 注册 `ThemeManageActivity` + `BookInfoComposeActivity`

### FR-4 应用代码缺陷修复
- FR-4.1 `SourceNetworkClient` 对 `evalJS` 返回值做 `analyzeLoginResult` 类型容错
- FR-4.2 `AnalyzeByJSonPath.getStringList` NPE 判空

### FR-5 订阅页管理设置生效 + 新版/经典切换
- FR-5.1 `AppConfig.modernRssPage` 读取属性落地
- FR-5.2 `RssFragment` 依据 `usingModernRss` 切换经典/现代渲染形态（对齐 Archive）
- FR-5.3 订阅页管理设置项生效（对齐 Archive `menu_rss_config` 入口行为）

### FR-6 主题设置顶栏管理对齐 Archive
- FR-6.1 顶栏管理行为（管理入口/行为）与 Archive 一致

### FR-7 编译门禁 + 打测试包
- FR-7.1 `./gradlew assembleAppDebug` BUILD SUCCESSFUL
- FR-7.2 `build-legado.bat` 产出测试包

## Scenarios

### S-1 备份恢复页
1. 用户进入 我的 → 设置 → 备份与恢复
2. 页面以 Compose 设置列表渲染（非旧 Preference 样式），云存储类型可选 WebDAV/S3
3. 设置项点击/切换正常无崩溃

### S-2 我的页统计框
1. 用户进入"我的"页
2. 头部不再显示四框统计信息，其余功能正常
3. （后期优化）将 `if(false)` 改回 `true` 即可恢复统计框

### S-3 书源管理页返回
1. 用户进入 书源管理
2. 点击系统返回键 → 正常退出页面，无 StackOverflow 崩溃
3. Compose BackHandler 行为正常

### S-4 视频播放器滑动
1. 用户打开视频播放器，上下滑动切换
2. 无 IndexOutOfBoundsException 崩溃

### S-5 主题管理入口
1. 用户进入 主题设置 → 点击主题管理
2. 正常跳转 ThemeManageActivity，无 ActivityNotFoundException
3. 顶栏管理行为与 Archive 一致

### S-6 探索页书籍详情
1. 用户点击探索页书籍条目
2. 正常打开 BookInfoComposeActivity，无 ActivityNotFoundException

### S-7 订阅页切换
1. 用户进入 订阅页
2. 设置中切换"新版订阅/经典订阅" → 页面形态立即切换
3. 订阅页管理设置生效

### S-8 登录校验书源
1. 用户对含 loginCheckJs 的书源发起请求
2. JS 返回 String 时正常处理，无 ClassCastException

### S-9 JSONPath 解析
1. 书源规则 JSONPath 指向缺失路径
2. `getStringList` 返回空/不崩溃，无 NPE
