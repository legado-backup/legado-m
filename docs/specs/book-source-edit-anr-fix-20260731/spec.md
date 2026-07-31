# 需求规格：BookSourceEditAdapter ANR 闪退修复

> 功能名称：`book-source-edit-anr-fix-20260731`
> 文档版本：1.1（2026-07-31 源码核实后修正）
> 创建时间：2026-07-31

---

## 一、Intent（用户反馈与问题分解）

### 1.1 用户反馈

> "打开一个大书源软件闪退了"

用户提供日志 `logs(10).zip`（正式包 `io.legado.miss.app.release` v3.26.073121）。

### 1.2 问题分解

| 层级 | 问题 | 证据 |
|------|------|------|
| **现象层** | 应用闪退重启 | logcat 显示旧进程 pid=18209 被 kill，新进程 pid=21025 启动 |
| **类型层** | ANR（非 SIGABRT/JNI 崩溃） | MIUIScout 记录 `ANR: duration=9916ms`，主线程连续卡死 |
| **根因层** | 主线程 `setText(超大文本)` 触发 native 换行计算 | backtrace 指向 `LineBreaker.nComputeLineBreaksWithHelperIndex` |
| **代码层** | `BookSourceEditAdapter.kt:73` `editText.setText(editEntity.value)` | 主线程 onBindViewHolder 同步 setText，无长度保护 |
| **触发层** | 文件关联打开大书源 JSON → 进入编辑页 → 滚动 | `FileAssociationActivity onCreate` → `BookSourceEditActivity onCreate` → 滚动触发 onBindViewHolder |

### 1.3 根因定位（源码核实）

**核心问题代码**（`BookSourceEditAdapter.kt` L73，已 Read 核实）：

```kotlin
// onBindViewHolder → holder.bind(editEntity) 中（L49-96）
editText.setText(editEntity.value)  // L73: 主线程同步 setText，无长度保护
```

**关键事实**（源码逐行核实）：

1. `editText` 实际类型是 `CodeView`（`item_source_edit.xml` L9-14 确认）
2. `CodeView` 继承链（CodeView.kt L24-25 + ScrollMultiAutoCompleteTextView.kt L22-25 核实）：
   `CodeView` → `ScrollMultiAutoCompleteTextView` → `AppCompatMultiAutoCompleteTextView` → `AppCompatAutoCompleteTextView` → `AppCompatEditText` → `AppCompatTextView` → `TextView` → `EditText`
3. **`CodeView.highlight()` 方法有 `1..4096` 长度保护（CodeView.kt:221），但 `BookSourceEditAdapter` L73 调用的是 `EditText` 原生 `setText()`，不经过 highlight 保护**
   - `highlight()` 仅在 `mUpdateRunnable`（CodeView.kt L41-44，postDelayed 500ms 后）和 `setTextHighlighted()`（L240-247）中调用
   - `setText()` 触发的是 `DynamicLayout.reflow → StaticLayout.generate → LineBreaker.nComputeLineBreaksWithHelperIndex`
   - 即使有 highlight 保护，setText 本身仍会卡死。这是根因分析的关键点
4. `AppConfig.sourceEditMaxLine` 默认 `Int.MAX_VALUE`（不限制行数），`editText.maxLines` 设置无效（maxLines 不能阻止 setText 内部的 LineBreaker 计算）
5. `BookSourceEditActivity` 已有 `onFullEditClicked()`（L144-159）跳转 `CodeEditActivity` 全屏编辑器，可作为截断后的完整内容查看入口
6. `upSourceView()`（L293-423）创建 EditEntity 列表，其中可能超大的字段：`bookSourceComment`(L317)/`coverDecodeJs`(L321)/`header`(L323)/`jsLib`(L326) 以及各类 rule 字段

---

## 二、Scope（范围）

### 2.1 In Scope（本次修复范围）

| # | 范围 | 文件 | 说明 |
|---|------|------|------|
| 1 | 书源编辑页 Adapter | `BookSourceEditAdapter.kt` | P0 核心修复：setText 截断 + PrecomputedText |
| 2 | RSS 源编辑页 Adapter | `RssSourceEditAdapter.kt` | P2 同模式修复：setText 截断 + PrecomputedText |
| 3 | HttpTTS 编辑对话框 | `HttpTtsEditDialog.kt` | P2 评估修复：initView 中 9 个 setText 截断 |
| 4 | 书源编辑页 Activity | `BookSourceEditActivity.kt` | P0 配套修复：onFullEditClicked 传值 + textEditLauncher 回写 |
| 5 | CodeView 扩展函数 | `CodeViewExt.kt`（新增）或 `CodeViewExtensions.kt` | 视方案需要，提取安全 setText 扩展 |

### 2.2 Out of Scope（不在本次修复范围）

| # | 范围 | 原因 |
|---|------|------|
| 1 | FileAssociationActivity 导入大书源的保护 | 属于导入流程优化，非本次 ANR 根因修复，可作为后续优化 |
| 2 | CodeEditActivity 全屏编辑器性能优化 | 全屏编辑器已有，且本次修复依赖它作为完整内容查看入口，无需改动 |
| 3 | Cronet 网络层 SIGABRT 崩溃 | 日志中 07:23~08:25 的 Cronet 子线程崩溃与本次 ANR 无关（独立问题） |
| 4 | 数据库 CursorWindow 读取异常 | 伴随现象，非本次 ANR 根因 |
| 5 | RecyclerView 替换为虚拟滚动列表 | 改动过大，截断+预计算已能解决问题 |

---

## 三、Approach（方案选择）

### 3.1 方案对比

| 方案 | 描述 | 优点 | 缺点 | 适用性 |
|------|------|------|------|--------|
| **A. 文本截断显示**（选定） | 对 >5000 字符的文本截断显示前 5000 字符，附"点击全屏编辑查看完整内容"提示 | 改动最小；立即消除 ANR；复用已有 CodeEditActivity | 截断后无法在列表内直接查看完整内容（需点击跳转） | ✅ P0 必做 |
| **B. PrecomputedText 异步预计算** | 使用 AndroidX `PrecomputedTextCompat` 在后台线程预计算文本布局 | 不截断内容；主线程不阻塞 | 增加异步复杂度；超大文本预计算本身仍耗时（后台线程可接受） | ✅ P1 增强 |
| **C. 大文本字段改用专用全屏编辑器** | RecyclerView 中超长字段仅显示摘要+"点击编辑"按钮 | 彻底解决；UX 清晰 | 改动大；需修改 EditEntity/布局/Activity 逻辑 | ❌ 暂不采用（改动过大） |
| **D. 禁用 CodeView 高亮** | 移除 addLegadoPattern 等高亮配置 | 减少 setText 后的 reflow | 不解决 LineBreaker 根因（setText 本身触发 LineBreaker）；损失高亮功能 | ❌ 不采用 |

### 3.2 选定方案：A + B 组合

- **P0（方案 A）**：立即对 `BookSourceEditAdapter` / `RssSourceEditAdapter` / `HttpTtsEditDialog` 应用文本截断显示，消除 ANR 根因
- **P1（方案 B）**：对截断后仍较大（但 ≤阈值）的文本，使用 `PrecomputedTextCompat` 异步预计算，进一步优化滚动流畅度

### 3.3 方案缺点与缓解

| 缺点 | 缓解措施 |
|------|---------|
| 截断后列表内无法查看完整内容 | 复用已有 `onFullEditClicked()` → `CodeEditActivity` 全屏编辑器；截断提示文案明确引导用户点击全屏编辑 |
| PrecomputedText 异步预计算增加复杂度 | 仅对 >500 字符且 ≤5000 字符的文本启用预计算；小文本直接同步 setText |
| 截断阈值需平衡可用性与性能 | 阈值 5000 字符：参考 CodeView.highlight 的 4096 保护阈值，略放宽；5000 字符 setText 通常 <100ms |

---

## 四、Requirements（详细需求）

### FR-1（P0）：BookSourceEditAdapter 文本截断显示

**需求**：在 `BookSourceEditAdapter.kt` 的 `bind()` 方法中（L49-96），对 `editEntity.value` 超过阈值（5000 字符）的文本进行截断显示。

**验收标准**：
1. 当 `editEntity.value` 为 null 或长度 ≤ 5000 时，行为与原代码一致（直接 `setText`）
2. 当 `editEntity.value` 长度 > 5000 时，显示前 5000 字符 + 截断提示文案
3. 截断提示文案明确引导用户通过全屏编辑查看完整内容
4. 截断显示不影响 `editEntity.value` 的原始值（TextWatcher 回写的是截断后的显示文本，需用 `R.id.tag3` 标记避免回写——见 design.md ADR-1）
5. 打开包含超大 comment 字段（如 100KB）的书源 JSON，滚动到该字段不再 ANR

**代码位置**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt:73`

### FR-2（P1）：PrecomputedText 异步预计算

**需求**：对截断后仍较大（>500 且 ≤5000 字符）的文本，使用 AndroidX `PrecomputedTextCompat` 在后台线程预计算文本布局后，再设置到 CodeView。

**兼容性结论（源码+官方文档核实）**：
- `PrecomputedTextCompat` 支持 API 14+（通过 AndroidX Jetpack）
- 项目 minSdk=23（build.gradle L74）→ **满足要求**
- androidx.core 1.18.0 + appcompat 1.7.1（libs.versions.toml L7/L10）→ **完全支持**
- API 28+：使用原生 `PrecomputedText` 优化
- API 23-27：`PrecomputedTextCompat` 内部降级为 `StaticLayout` 优化（仍有性能收益，**非直接 setText**）
- CodeView 继承自 `AppCompatTextView`（通过继承链），支持 `setTextFuture()`

**验收标准**：
1. 文本长度 ≤ 500：直接同步 `setText`（小文本无需预计算）
2. 文本长度 501~5000：使用 `PrecomputedTextCompat.getTextFuture()` 异步预计算，完成后 `setTextFuture()`
3. 预计算期间不阻塞主线程
4. RecyclerView 滚动时，已预计算的 item 复用缓存
5. ViewHolder 复用时，取消未完成的预计算任务（避免回调到已复用的 ViewHolder）
6. API 23-27 仍有性能收益（StaticLayout 优化），非完全降级

**代码位置**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt`

### FR-3（P2）：RssSourceEditAdapter 同模式修复

**需求**：对 `RssSourceEditAdapter.kt` 的 `EditTextViewHolder.bind()` 方法（L79-125）应用与 FR-1 相同的截断显示修复。

**验收标准**：
1. `RssSourceEditAdapter` L102 `editText.setText(editEntity.value)` 应用截断逻辑
2. L119 `afterTextChanged` 回写增加 `isTruncated` 检查
3. 行为与 FR-1 一致
4. 打开包含超大字段的 RSS 源，滚动到该字段不再 ANR

**代码位置**：`app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditAdapter.kt:102`

### FR-4（P2）：HttpTTS 编辑对话框评估修复

**需求**：评估 `HttpTtsEditDialog.kt` 的 `initView()` 方法（L89-99）中 9 个字段的 `setText` 风险，对可能超大的字段应用截断显示。

**字段核实**（dialog_http_tts_edit.xml + HttpTtsEditDialog.kt 核实）：
- `tv_name`（ThemeEditText，普通 EditText）：通常 <500 字符，低风险
- `tv_url`/`tv_content_type`/`tv_concurrent_rate`（CodeView）：通常 <500 字符，低风险
- `tv_login_url`/`tv_login_ui`/`tv_login_check_js`/`tv_headers`/`tv_jsLib`（CodeView）：理论上可能较大（header/json/js），中风险

**验收标准**：
1. 评估 HttpTTS 实体各字段的最大可能长度
2. 对可能超大的字段（header/jsLib/loginUi/loginCheckJs）应用截断显示
3. 截断后仍可通过全屏编辑查看完整内容（HttpTtsEditDialog L118-133 已有 `onFullEditClicked`，用 `focusedEditText` 缓存）
4. `dataFromView()`（L172-185）需同步修复：截断字段需从原始数据或标记读取，避免保存截断文本
5. 打开包含超大 header/jsLib 的 HttpTTS 配置不卡顿

**代码位置**：`app/src/main/java/io/legado/app/ui/book/read/config/HttpTtsEditDialog.kt:89-99`

### FR-5（P0 配套）：BookSourceEditActivity 全屏编辑传值与回写修复

**需求**：修复 `BookSourceEditActivity.kt` 的 `onFullEditClicked()`（L144-159）和 `textEditLauncher`（L128-142），确保截断字段的全屏编辑传入原始完整值、返回后正确处理大文本。

**验收标准**：
1. `onFullEditClicked`：截断字段传入 `editEntity.value` 原始值，而非 `view.text` 截断显示值
2. `textEditLauncher` 回调：全屏编辑返回的大文本仍需截断显示（避免 setText 再次卡死）
3. 截断字段的全屏编辑返回后，`editEntity.value` 更新为编辑后的完整值（非截断显示值）
4. 临时移除 TextWatcher 避免 setText 触发回写截断文本

**代码位置**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt:128-159`

---

## 五、Scenarios（场景分析）

### 场景 1：文件关联打开大书源 JSON（用户报告场景）

**前置条件**：用户从文件管理器点击一个包含超大 comment 字段（如 100KB）的书源 JSON 文件

**操作路径**：
1. `FileAssociationActivity` 解析 JSON → 创建 `BookSource`
2. 启动 `BookSourceEditActivity` → `upSourceView()`（L293）创建 EditEntity 列表
3. 用户滚动到"备注"字段（`bookSourceComment`，upSourceView L317）
4. `BookSourceEditAdapter.onBindViewHolder` → `bind()` → `setText`

**修复前**：`setText(100KB 文本)` → LineBreaker 卡死 >10s → ANR → 闪退重启
**修复后**：`setText(前5000字符 + 截断提示)` → LineBreaker 计算 <100ms → 正常显示，用户可点击全屏编辑查看完整内容

### 场景 2：书源列表内编辑小文本字段

**前置条件**：用户在书源编辑页编辑 `bookSourceName`（通常 <100 字符）

**操作**：滚动到"书源名称"字段

**修复后**：文本长度 ≤ 5000，直接 `setText`，行为与原代码完全一致

### 场景 3：RSS 源编辑页滚动超大字段

**前置条件**：用户打开包含超大 `sourceComment` 或 rule 字段的 RSS 源

**操作**：滚动到超大字段

**修复前**：`RssSourceEditAdapter` L102 `setText` 同样卡死
**修复后**：应用截断逻辑，正常显示

### 场景 4：HttpTTS 编辑对话框

**前置条件**：用户编辑一个 header/jsLib 字段超大的 HttpTTS 配置

**操作**：打开 HttpTTS 编辑对话框

**修复前**：`initView` 中 9 个 `setText` 同步执行，超大字段可能卡顿
**修复后**：超大字段截断显示，对话框正常打开

### 场景 5：截断后编辑回写

**前置条件**：用户在截断显示的字段中编辑文本

**操作**：修改截断后的显示文本

**风险**：TextWatcher `afterTextChanged`（BookSourceEditAdapter L90）会将截断后的显示文本回写到 `editEntity.value`，导致原始完整内容丢失

**缓解**（见 design.md ADR-1）：
- 用 `R.id.tag3` 标记 `isTruncated`
- TextWatcher 检查 `isTruncated`，截断字段不回写，保留 `editEntity.value` 原始完整值

### 场景 6：RecyclerView 快速滚动

**前置条件**：书源编辑页有多个超大字段，用户快速滚动

**操作**：快速滚动 RecyclerView

**修复后**：截断显示确保每个 item 的 setText 都 <100ms；PrecomputedText（FR-2）进一步优化中等长度文本的预计算

### 场景 7：全屏编辑返回大文本

**前置条件**：用户在 CodeEditActivity 编辑截断字段的完整内容后返回

**操作**：编辑后返回 BookSourceEditActivity

**风险**：`textEditLauncher`（L128-142）L133 `view.setText(it)` 若返回文本仍 >5000，会再次卡死

**缓解**（见 design.md ADR-5）：
- `textEditLauncher` 回调对返回文本截断显示
- 临时移除 TextWatcher 避免 setText 触发回写截断文本
- 更新 `editEntity.value` 为编辑后的完整值

---

## 六、验收标准

### 6.1 功能验收

| # | 验收项 | 验证方法 |
|---|--------|---------|
| 1 | 打开包含 100KB comment 字段的书源 JSON 不闪退 | 构造测试书源，文件关联打开，滚动到 comment 字段 |
| 2 | 截断提示文案正确显示 | 观察 UI 是否显示"文本过长，已截断"类提示 |
| 3 | 点击全屏编辑可查看完整内容 | 点击截断字段的全屏编辑按钮，确认 CodeEditActivity 显示完整文本（非截断文本） |
| 4 | 小文本字段行为不变 | 编辑 bookSourceName 等小字段，确认正常编辑 |
| 5 | RSS 源编辑页同样不闪退 | 构造大 RSS 源，打开编辑页滚动 |
| 6 | HttpTTS 对话框不卡顿 | 构造大 header/jsLib 的 HttpTTS，打开编辑对话框 |
| 7 | 全屏编辑返回后正确截断显示 | 编辑后返回，列表显示截断文本，editEntity.value 为完整值 |
| 8 | 保存数据正确 | 编辑后保存，重新打开确认数据完整（非截断） |

### 6.2 性能验收

| # | 验收项 | 阈值 |
|---|--------|------|
| 1 | 单次 onBindViewHolder 耗时 | < 100ms（截断后） |
| 2 | 主线程无 ANR | 无 MIUIScout ANR 告警 |
| 3 | 滚动帧率 | 无明显掉帧（>5 帧/s 丢帧） |

### 6.3 回归验收

| # | 验收项 | 验证方法 |
|---|--------|---------|
| 1 | 书源保存功能正常 | 编辑后保存，重新打开确认数据正确 |
| 2 | 书源复制/分享功能正常 | 复制书源 JSON，确认完整 |
| 3 | 全屏编辑回写正常 | CodeEditActivity 编辑后返回，确认内容回写到列表 |
| 4 | 自动补全功能正常 | 确认 CodeView 的 addLegadoPattern 等高亮/补全仍工作 |

### 6.4 真机测试要求

- 测试包：`io.legado.miss.app.debug`（项目代码优化用测试包）
- 测试设备：模拟器/真机
- 测试脚本：`ai_tests/scripts/` 下脚本（详见 tasks.md）
