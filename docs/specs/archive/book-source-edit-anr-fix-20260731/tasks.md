# 任务清单：BookSourceEditAdapter ANR 闪退修复

> 功能名称：`book-source-edit-anr-fix-20260731`
> 文档版本：1.1（2026-07-31 源码核实后修正）
> 创建时间：2026-07-31
> 关联：[spec.md](./spec.md) | [design.md](./design.md)

---

## 一、阶段划分

| 阶段 | 名称 | 任务数 | 优先级 | 依赖 |
|------|------|--------|--------|------|
| 1 | 准备 | 1 | P0 | 无 |
| 2 | P0 核心修复（BookSourceEditAdapter + Activity） | 4 | P0 | 阶段 1 |
| 3 | P2 同模式修复（RssSourceEditAdapter + HttpTtsEditDialog） | 3 | P2 | 阶段 2 |
| 4 | P1 增强（PrecomputedText） | 2 | P1 | 阶段 2 |
| 5 | 编译验证 | 1 | P0 | 阶段 2-4 |
| 6 | 真机测试 | 5 | P0 | 阶段 5 |
| 7 | 交付 | 2 | P0 | 阶段 6 |

---

## 二、任务列表

### 阶段 1：准备

#### T1.1 新增 R.id.tag3
- **文件**：`app/src/main/res/values/ids.xml`
- **变更**：在 `<item name="tag2" type="id" />`（L6）后新增 `<item name="tag3" type="id" />`
- **依据**：design.md ADR-3；项目已用 tag/tag1/tag2（ids.xml:4-6），需 tag3 标记截断状态；L25 有 `text_watcher` 无冲突
- **复杂度**：低
- **依赖**：无

---

### 阶段 2：P0 核心修复（BookSourceEditAdapter + Activity）

#### T2.1 BookSourceEditAdapter 截断显示 + TextWatcher 不回写
- **文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt`
- **变更**：
  1. L73 `editText.setText(editEntity.value)` → 截断判断 + `setText(displayValue)`
  2. 新增 `editText.setTag(R.id.tag3, isTruncated)` 标记截断状态
  3. L90 `afterTextChanged` 增加 `isTruncated` 检查，截断时不回写
  4. 新增 `companion object` 定义 `MAX_DISPLAY_LENGTH=5000` 和 `TRUNCATE_HINT`（`const val` 非 private，以便 Activity 访问）
- **依据**：design.md §4.2；spec.md FR-1
- **代码片段**：见 design.md §4.2 修复后代码
- **复杂度**：中
- **依赖**：T1.1

#### T2.2 BookSourceEditActivity onFullEditClicked 传值修复
- **文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt`
- **变更**：
  1. `onFullEditClicked()`（L144-159）：截断字段传入 `editEntity.value` 原始值，而非 `view.text`（L148）截断显示值
  2. 检查 `view.getTag(R.id.tag3)` 判断是否截断
  3. 新增 `findEditEntityValueByView(view)` 辅助方法（从 `adapter.editEntities` 按 `R.id.tag` 的 key 查找）
- **依据**：design.md §3.2 ADR-5；spec.md FR-5；修复全屏编辑传入截断文本的问题
- **代码片段**：见 design.md §4.3 修复后代码
- **复杂度**：中
- **依赖**：T2.1

#### T2.3 BookSourceEditActivity textEditLauncher 回写修复
- **文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt`
- **变更**：
  1. `textEditLauncher` 回调（L128-142）：全屏编辑返回的大文本截断显示（L133 `view.setText(it)` 改为截断处理）
  2. 临时移除 TextWatcher（`R.id.tag2`）避免 setText 触发回写截断文本
  3. 重新添加 TextWatcher
  4. 截断字段更新 `editEntity.value` 为编辑后的完整值（非截断显示值）
  5. 新增 `updateEditEntityValue(view, newValue)` 辅助方法
- **依据**：design.md §3.2；spec.md FR-5；修复全屏编辑返回后 setText 再次卡死 + 数据回写
- **代码片段**：见 design.md §4.3 修复后代码
- **复杂度**：中
- **依赖**：T2.2

#### T2.4（可选）CodeView 扩展函数提取
- **文件**：`app/src/main/java/io/legado/app/ui/widget/code/CodeViewExt.kt`（新增）或追加到 `CodeViewExtensions.kt`
- **变更**：提取 `EditText.setSafeText(value: String?): Boolean` 扩展函数 + 顶层常量 `MAX_DISPLAY_LENGTH`/`TRUNCATE_HINT`
- **依据**：design.md §4.5；DRY 原则，避免 BookSourceEditAdapter / RssSourceEditAdapter 重复代码
- **决策**：若 T2.1 和 T3.1 改动一致，提取扩展函数；否则跳过（各 Adapter 自带 companion object）
- **复杂度**：低
- **依赖**：T2.1

---

### 阶段 3：P2 同模式修复（RssSourceEditAdapter + HttpTtsEditDialog）

#### T3.1 RssSourceEditAdapter 截断显示
- **文件**：`app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditAdapter.kt`
- **变更**：
  1. L102 `editText.setText(editEntity.value)` → 截断判断 + `setText(displayValue)`
  2. 新增 `editText.setTag(R.id.tag3, isTruncated)`
  3. L119 `afterTextChanged` 增加 `isTruncated` 检查
  4. 新增 `companion object` 或复用扩展函数常量
- **依据**：design.md §4.4；spec.md FR-3
- **注意**：RssSourceEditAdapter 有 `visibleEntities` 过滤（L35-40），但 EditTextViewHolder.bind（L79-125）逻辑与 BookSourceEditAdapter 一致
- **复杂度**：中
- **依赖**：T2.1（参考实现模式）或 T2.4（复用扩展函数）

#### T3.2 HttpTtsEditDialog initView 截断修复
- **文件**：`app/src/main/java/io/legado/app/ui/book/read/config/HttpTtsEditDialog.kt`
- **变更**：
  1. `initView()`（L89-99）：对 header/jsLib/loginUi/loginCheckJs/loginUrl 字段应用 `setSafeText`（L94-98）
  2. `dataFromView()`（L172-185）：截断字段需从原始数据或标记读取，避免保存截断文本
- **依据**：design.md §4.6；spec.md FR-4
- **注意**：
  - HttpTtsEditDialog 是 DialogFragment（非 RecyclerView），9 个 setText（L90-98）
  - `tv_name` 是 `ThemeEditText`（普通 EditText），其余 8 个是 `CodeView`
  - `onFullEditClicked`（L118-133）用 `focusedEditText` 缓存（L46/L122），非 `findFocus()`
  - `dataFromView` 直接读 `view.text`（L175-183），截断后会保存截断文本，必须同步修复
- **复杂度**：中
- **依赖**：T2.4（若提取扩展函数）或 T2.1（参考实现）

#### T3.3 HttpTtsEditDialog dataFromView 修复
- **文件**：`app/src/main/java/io/legado/app/ui/book/read/config/HttpTtsEditDialog.kt`
- **变更**：`dataFromView()`（L172-185）截断字段从 `viewModel.httpTTS`（原始数据）读取，或从 `tag4` 读取备份原值
- **依据**：design.md §4.6；避免保存截断文本导致数据丢失
- **复杂度**：中
- **依赖**：T3.2

---

### 阶段 4：P1 增强（PrecomputedText）

#### T4.1 确认 androidx.core 版本兼容性（已核实）
- **操作**：已核实 `gradle/libs.versions.toml`
- **结论**：
  - androidx.core 1.18.0（L10）→ ✅ 完全支持 `PrecomputedTextCompat`
  - appcompat 1.7.1（L7）→ ✅ 完全支持 `setTextFuture()`
  - minSdk 23（build.gradle L74）→ ✅ 满足 PrecomputedTextCompat 要求（API 14+）
  - CodeView 继承链到 `AppCompatTextView` → ✅ 支持 `setTextFuture()`
  - API 28+ 用原生 PrecomputedText，API 23-27 用 StaticLayout 优化（非降级为直接 setText）
- **依据**：design.md §1.3；README §六
- **复杂度**：低（已完成核实）
- **依赖**：阶段 2 完成

#### T4.2 PrecomputedText 实现
- **条件**：T4.1 确认通过（已确认）
- **文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt`
- **变更**：
  1. 对 501~5000 字符文本，使用 `PrecomputedTextCompat.getTextFuture()` 后台预计算
  2. 调用 `editText.setTextFuture(future)`（AppCompatTextView 方法，CodeView 继承链支持）
  3. API 23-27 自动通过 StaticLayout 优化（PrecomputedTextCompat 内部降级，无需手动处理）
  4. ViewHolder 复用时取消未完成的预计算任务（`onViewRecycled`）
- **依据**：design.md §1.3；spec.md FR-2
- **注意**：
  - 所有 TextView 布局属性必须在创建 Params 对象前设置（否则 IllegalArgumentException）
  - RecyclerView 需启用预取（Prefetch）才能充分发挥 PrecomputedText 效果
  - 文本 ≤500 字符直接同步 setText（小文本无需预计算）
- **复杂度**：高
- **依赖**：T4.1, T2.1

---

### 阶段 5：编译验证

#### T5.1 编译 debug 包
- **命令**：`./gradlew :app:assembleAppDebug`（或 `gradlew.bat :app:assembleAppDebug`）
- **验证**：编译通过，无错误
- **复杂度**：低
- **依赖**：阶段 2-4 完成

---

### 阶段 6：真机测试

#### T6.1 大书源打开不闪退测试
- **步骤**：
  1. 构造包含 100KB comment 字段的书源 JSON
  2. 安装测试包 `io.legado.miss.app.debug`
  3. 文件管理器打开该 JSON → 进入 BookSourceEditActivity
  4. 滚动到 comment 字段
- **预期**：无 ANR，显示截断文本+"已截断"提示
- **脚本**：`ai_tests/scripts/quick_build_install.py` + 手动构造测试 JSON
- **复杂度**：中
- **依赖**：T5.1

#### T6.2 全屏编辑测试
- **步骤**：
  1. 在 T6.1 基础上，点击截断字段的全屏编辑按钮
  2. 确认 CodeEditActivity 显示完整 100KB 文本（非截断文本）
  3. 编辑后返回
- **预期**：全屏显示完整内容；返回后列表显示截断文本
- **复杂度**：中
- **依赖**：T6.1

#### T6.3 保存正确性测试
- **步骤**：
  1. 在 T6.2 基础上，保存书源
  2. 重新打开该书源
  3. 检查 comment 字段是否为完整内容（非截断）
- **预期**：数据正确保存，无丢失
- **复杂度**：中
- **依赖**：T6.2

#### T6.4 RSS 源测试
- **步骤**：
  1. 构造包含超大字段的 RSS 源
  2. 打开 RSS 源编辑页
  3. 滚动到超大字段
- **预期**：无 ANR，截断显示
- **脚本**：`ai_tests/scripts/import_rss_source.py`（可改造为导入大 RSS 源）
- **复杂度**：中
- **依赖**：T5.1, T3.1

#### T6.5 HttpTTS 对话框测试
- **步骤**：
  1. 构造包含超大 header/jsLib 的 HttpTTS 配置
  2. 打开 HttpTTS 编辑对话框
- **预期**：对话框正常打开，无卡顿
- **复杂度**：低
- **依赖**：T5.1, T3.2

---

### 阶段 7：交付

#### T7.1 updateLog.md 更新
- **文件**：`assets/updateLog.md`
- **变更**：基于 `git diff` 分析真实代码变更，生成用户可感知的更新日志
- **依据**：AGENTS.md「版本交付同步」强制规则
- **要求**：通俗语言描述，不暴露内部技术术语；逐文件审计不遗漏
- **复杂度**：低
- **依赖**：阶段 6 完成

#### T7.2 文档同步
- **检查项**：
  1. `docs/INDEX.md` 是否需要添加新 spec 条目
  2. issues-found.md 是否记录测试中发现的问题
  3. project_memory（`.trae/memory/ai_memory_main.md`）是否更新任务状态
- **依据**：AGENTS.md「任务完成前强制检查清单」
- **复杂度**：低
- **依赖**：T7.1

---

## 三、依赖关系图

```
T1.1 (新增 tag3)
  │
  ▼
T2.1 (Adapter 截断) ──────────────────┐
  │                                   │
  ├─▶ T2.2 (onFullEditClicked 传值)   │
  │     │                             │
  │     └─▶ T2.3 (textEditLauncher)   │
  │                                   │
  ├─▶ T2.4 (扩展函数提取，可选)        │
  │                                   │
  ├─▶ T3.1 (RssSource 截断)           │
  │     │                             │
  │     └─▶ T3.2 (HttpTTS initView)   │
  │           │                       │
  │           └─▶ T3.3 (dataFromView) │
  │                                   │
  └─▶ T4.1 (已核实兼容性)             │
        │                             │
        └─▶ T4.2 (PrecomputedText)    │
                                      │
                 T5.1 (编译) ◀────────┘
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
       T6.1      T6.4      T6.5
         │
         ▼
       T6.2
         │
         ▼
       T6.3
         │
         ▼
       T7.1 → T7.2
```

---

## 四、验收清单

### 4.1 代码验收

| # | 验收项 | 验证方法 | 对应任务 |
|---|--------|---------|---------|
| 1 | R.id.tag3 已添加 | Grep `name="tag3"` ids.xml | T1.1 |
| 2 | BookSourceEditAdapter L73 已截断 | Read BookSourceEditAdapter.kt 确认 | T2.1 |
| 3 | BookSourceEditAdapter TextWatcher 不回写截断字段 | Read afterTextChanged 确认 `isTruncated` 检查 | T2.1 |
| 4 | companion object 常量定义正确 | Read 确认 `MAX_DISPLAY_LENGTH=5000`（const val 非 private） | T2.1 |
| 5 | onFullEditClicked 传原始值 | Read BookSourceEditActivity.kt 确认 `findEditEntityValueByView` | T2.2 |
| 6 | textEditLauncher 截断显示+更新原值 | Read textEditLauncher 确认截断处理 + `updateEditEntityValue` | T2.3 |
| 7 | RssSourceEditAdapter 已截断 | Read RssSourceEditAdapter.kt L102 确认 | T3.1 |
| 8 | HttpTtsEditDialog initView 已截断 | Read HttpTtsEditDialog.kt L89-99 确认 | T3.2 |
| 9 | HttpTtsEditDialog dataFromView 不保存截断文本 | Read dataFromView 确认 | T3.3 |
| 10 | 无调试日志残留 | Grep `android.util.Log.d\|android.util.Log.e` | 全部 |

### 4.2 编译验收

| # | 验收项 | 验证方法 |
|---|--------|---------|
| 1 | debug 包编译通过 | `./gradlew :app:assembleAppDebug` 成功 |
| 2 | 无新增 lint 错误 | 编译输出无 error |

### 4.3 功能验收（真机）

| # | 验收项 | 阈值 | 对应任务 |
|---|--------|------|---------|
| 1 | 100KB comment 书源打开不闪退 | 无 ANR | T6.1 |
| 2 | 截断提示显示 | UI 可见提示文案 | T6.1 |
| 3 | 全屏编辑显示完整内容 | CodeEditActivity 显示 100KB | T6.2 |
| 4 | 全屏编辑返回后截断显示 | 列表显示截断文本 | T6.2 |
| 5 | 保存数据正确 | 重新打开 comment 完整 | T6.3 |
| 6 | 小文本编辑不变 | bookSourceName 正常编辑 | T6.1 |
| 7 | RSS 源不闪退 | 无 ANR | T6.4 |
| 8 | HttpTTS 对话框不卡顿 | 对话框正常打开 | T6.5 |

### 4.4 性能验收

| # | 验收项 | 阈值 |
|---|--------|------|
| 1 | 单次 onBindViewHolder 耗时 | < 100ms |
| 2 | 无 MIUIScout ANR 告警 | logcat 无 ANR 记录 |
| 3 | 无 DispatchersMonitor Main 超时 | logcat 无 Main timed out |

### 4.5 交付验收

| # | 验收项 | 对应规范 |
|---|--------|---------|
| 1 | updateLog.md 已更新 | version-delivery-sync.md |
| 2 | 文档同步已检查 | INDEX/issues-found/project_memory |
| 3 | 调试日志已清理 | logging-during-refactoring.md |
| 4 | 问题清单已记录 | real-device-test-reuse.md |

---

## 五、风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 全屏编辑传值/回写逻辑有 bug 导致数据丢失 | 高 | T2.2/T2.3 重点测试；T6.3 保存正确性验证 |
| 截断字段在列表内编辑无效（用户困惑） | 中 | 截断提示文案明确引导"点击全屏编辑"；可考虑拦截编辑并 toast 提示 |
| HttpTtsEditDialog dataFromView 保存截断文本 | 中 | T3.3 同步修复 dataFromView；T6.5 验证 |
| PrecomputedText 兼容性问题 | 低 | 已核实 androidx.core 1.18.0 + appcompat 1.7.1 完全支持；API 23-27 用 StaticLayout 优化 |
| PrecomputedText TextView 属性变更导致 IllegalArgumentException | 低 | T4.2 实施时确保所有布局属性在创建 Params 前设置 |
| RssSourceEditAdapter 改动遗漏 | 中 | T3.1 参照 BookSourceEditAdapter 模式；T6.4 验证 |
| 编译失败（R.id.tag3 未生成） | 低 | T1.1 先行；T5.1 编译验证 |

---

## 六、工作量估算

| 阶段 | 估算工时 | 说明 |
|------|---------|------|
| 阶段 1 准备 | 0.5h | 新增一行 xml |
| 阶段 2 P0 核心修复 | 2.5h | 4 个任务，含全屏编辑传值+回写修复 |
| 阶段 3 P2 同模式 | 2h | RssSource + HttpTTS initView + dataFromView |
| 阶段 4 P1 增强 | 2h | 已核实兼容性 + PrecomputedText 实现 |
| 阶段 5 编译验证 | 0.5h | 编译 debug 包 |
| 阶段 6 真机测试 | 2h | 5 个测试场景 |
| 阶段 7 交付 | 0.5h | updateLog + 文档同步 |
| **合计** | **10h** | 不含 P1 增强约 8h |

---

## 七、关键约束

1. **测试包**：`io.legado.miss.app.debug`（代码优化任务用测试包，非正式包）
2. **Python 环境**：`ai_tests\venv\Scripts\python.exe`（禁止公共 Python）
3. **测试脚本**：`ai_tests/scripts/` 下脚本（禁止 temp/ 临时脚本）
4. **调试日志**：用 `AppLog.put()`，禁止 `android.util.Log`
5. **异常处理**：用 `kotlin.runCatching`，禁止 `try/catch` 裸块
6. **编译前更新 updateLog.md**：基于 `git diff` 真实变更生成
7. **真机测试必做**：禁止只改代码不测试
8. **CodeView 路径**：`app/src/main/java/io/legado/app/ui/widget/code/CodeView.kt`（非 `lib/codeview/`）
9. **addPattern 扩展函数位置**：`app/src/main/java/io/legado/app/ui/widget/code/CodeViewExtensions.kt`
