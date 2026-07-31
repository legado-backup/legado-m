# BookSourceEditAdapter ANR 闪退修复

> 功能名称：`book-source-edit-anr-fix-20260731`
> 创建时间：2026-07-31
> 状态：📋 规划中
> 来源：用户报告"打开一个大书源软件闪退了"（logs(10).zip）

---

## 一、功能概述

修复打开大书源 JSON 时，`BookSourceEditAdapter` 在主线程 `onBindViewHolder` 中对 `CodeView`（继承 `EditText`）执行 `setText(超大文本)`，触发 `LineBreaker.nComputeLineBreaksWithHelperIndex` native 文本换行计算耗时 >10 秒，导致主线程阻塞 ANR，系统 kill 进程后重启（表现为"闪退"）。

### 崩溃链路（基于真实日志）

```
FileAssociationActivity onCreate（文件关联打开书源 JSON）
  → BookSourceEditActivity onCreate（进入书源编辑页）
    → RecyclerView 布局/滚动
      → BookSourceEditAdapter.onBindViewHolder
        → holder.bind(editEntity)
          → editText.setText(editEntity.value)  ← L73 主线程同步 setText 大文本
            → DynamicLayout.reflow
              → StaticLayout.generate
                → LineBreaker.nComputeLineBreaksWithHelperIndex  ← native 换行计算 >10s
                  → 主线程阻塞 → ANR 9916ms → 系统 kill 进程 → 重启
```

### ANR 主线程 backtrace 关键帧

```
android.graphics.text.LineBreaker.nComputeLineBreaksWithHelperIndex(Native Method)
android.widget.EditText.setText(EditText.java:196)
android.widget.TextView.setText(TextView.java:7298)
BookSourceEditAdapter.bind  ← 混淆: zr.f.r
RecyclerView.onLayout
```

ANR Message 对象：`io.legado.app.ui.widget.code.CodeView{... app:id/editText ...}`

### 关键根因分析（源码核实）

> **重要**：`CodeView.highlight()` 方法的 `1..4096` 长度保护（CodeView.kt:221）**不在 setText 路径上**。
> - `highlight()` 仅在 `mUpdateRunnable`（postDelayed 500ms 后）和 `setTextHighlighted()` 中调用
> - `BookSourceEditAdapter` L73 调用的是 `EditText` 原生 `setText()`，触发 `DynamicLayout.reflow → StaticLayout.generate → LineBreaker`
> - 即使有 highlight 保护，setText 本身仍会卡死。这是根因分析的关键点。

---

## 二、核心能力（FR 列表）

| FR | 优先级 | 名称 | 修复点 |
|----|--------|------|--------|
| FR-1 | P0 | BookSourceEditAdapter 文本截断显示 | `BookSourceEditAdapter.kt:73` 对超大文本截断显示 |
| FR-2 | P1 | PrecomputedText 异步预计算 | `BookSourceEditAdapter.kt` 引入 AndroidX PrecomputedTextCompat |
| FR-3 | P2 | RssSourceEditAdapter 同模式修复 | `RssSourceEditAdapter.kt:102` 同样应用截断+预计算 |
| FR-4 | P2 | HttpTTS 编辑对话框评估修复 | `HttpTtsEditDialog.kt:89-99` 评估并应用截断显示 |

---

## 三、修复目标

1. **消除 ANR 闪退**：打开任意大小的书源 JSON 不再触发主线程阻塞 ANR
2. **保留编辑能力**：截断显示的字段仍可通过全屏编辑器（`CodeEditActivity`）查看和编辑完整内容
3. **同模式覆盖**：覆盖书源编辑、RSS 源编辑、HttpTTS 编辑三个同模式风险点
4. **不破坏现有功能**：小文本字段的展示和编辑行为不变

---

## 四、文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 概述（本文档） | [README.md](./README.md) | 功能概述、FR 列表、修复目标 |
| 需求规格 | [spec.md](./spec.md) | Intent、Scope、Approach、Requirements、Scenarios、验收标准 |
| 技术设计 | [design.md](./design.md) | 技术方案、ADR、数据流、文件变更、测试设计、回滚策略 |
| 任务清单 | [tasks.md](./tasks.md) | 阶段划分、任务列表、依赖关系、验收清单 |

---

## 五、源码核实锚点

> 以下路径均为 2026-07-31 源码核实确认的真实路径（已用 Read 工具逐行核实）。

| 文件 | 真实路径 | 关键行 | 核实结论 |
|------|---------|--------|---------|
| BookSourceEditAdapter.kt | `app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt` | L73 setText; L90 回写 | `editText.setText(editEntity.value)` 在主线程 onBindViewHolder 中执行；L90 `afterTextChanged` 回写到 `editEntity.value` |
| BookSourceEditActivity.kt | `app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt` | L74 sourceEntities; L128 textEditLauncher; L144 onFullEditClicked; L293 upSourceView; L425 getSource | `upSourceView` 创建 EditEntity 列表（L312-327），含 comment/jsLib/coverDecodeJs 等可能超大字段；`onFullEditClicked` L148 `view.text.toString()` 取显示文本；`textEditLauncher` L133 `view.setText(it)` 回写 |
| RssSourceEditAdapter.kt | `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditAdapter.kt` | L102 setText; L119 回写 | `editText.setText(editEntity.value)` 同模式问题；L119 `afterTextChanged` 回写 |
| CodeView.kt | `app/src/main/java/io/legado/app/ui/widget/code/CodeView.kt` | L24-25 继承; L41-44 mUpdateRunnable; L219-232 highlight; L240-247 setTextHighlighted | 继承 ScrollMultiAutoCompleteTextView→AppCompatMultiAutoCompleteTextView；highlight 有 `1..4096` 长度保护但**不在 setText 路径上**（highlight 由 mUpdateRunnable postDelayed 500ms 后触发） |
| CodeViewExtensions.kt | `app/src/main/java/io/legado/app/ui/widget/code/CodeViewExtensions.kt` | L19-30 | `addLegadoPattern`/`addJsonPattern`/`addJsPattern` 扩展函数定义于此 |
| ScrollMultiAutoCompleteTextView.kt | `app/src/main/java/io/legado/app/ui/widget/text/ScrollMultiAutoCompleteTextView.kt` | L22-25 | 继承 `AppCompatMultiAutoCompleteTextView`，确认继承链到 AppCompatTextView（支持 `setTextFuture()`） |
| item_source_edit.xml | `app/src/main/res/layout/item_source_edit.xml` | L9-14 | 确认 `editText` 类型是 `io.legado.app.ui.widget.code.CodeView` |
| EditEntity.kt | `app/src/main/java/io/legado/app/ui/widget/text/EditEntity.kt` | L5-9 | `data class EditEntity(var key, var value: String?, var hint, val viewType)` |
| AppConfig.kt | `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | L863-873 | `sourceEditMaxLine` 默认 `Int.MAX_VALUE`（不限制行数） |
| ids.xml | `app/src/main/res/values/ids.xml` | L4-6 | 已有 `tag`/`tag1`/`tag2`，需新增 `tag3`（L25 有 `text_watcher`，无冲突） |
| dialog_http_tts_edit.xml | `app/src/main/res/layout/dialog_http_tts_edit.xml` | L42-46, L56, L70, L84, L98, L112, L126, L140, L154 | 共 9 个输入框：`tv_name` 是 `ThemeEditText`（普通 EditText），其余 8 个（tv_url/tv_content_type/tv_concurrent_rate/tv_login_url/tv_login_ui/tv_login_check_js/tv_headers/tv_jsLib）是 `CodeView` |
| HttpTtsEditDialog.kt | `app/src/main/java/io/legado/app/ui/book/read/config/HttpTtsEditDialog.kt` | L89-99 initView; L102-117 textEditLauncher; L118-133 onFullEditClicked; L172-185 dataFromView | `initView` 9 个 setText（L90-98）；`onFullEditClicked` 用 `focusedEditText` 缓存（L46/L122）而非 `findFocus()`；`dataFromView` 直接从 `view.text` 读取（截断后会保存截断文本） |
| app/build.gradle | `app/build.gradle` | L74 minSdk 23; L260 core-ktx; L261 appcompat | `minSdk 23` 确认；依赖 `libs.core.ktx` + `libs.appcompat.appcompat` |
| gradle/libs.versions.toml | `gradle/libs.versions.toml` | L7 appcompat=1.7.1; L10 core=1.18.0 | androidx.core 1.18.0 + appcompat 1.7.1，完全支持 `PrecomputedTextCompat` |

---

## 六、PrecomputedText 兼容性结论（源码+官方文档核实）

| 项目 | 结论 |
|------|------|
| **PrecomputedTextCompat 最低 API** | API 14+（通过 AndroidX Jetpack，非原生 API 28+） |
| **项目 minSdk** | 23（build.gradle L74 确认）→ **满足要求** |
| **androidx.core 版本** | 1.18.0（libs.versions.toml L10）→ 完全支持 |
| **appcompat 版本** | 1.7.1（libs.versions.toml L7）→ 完全支持 |
| **API 28+ 行为** | 使用原生 `PrecomputedText` 优化 |
| **API 23-27 行为** | `PrecomputedTextCompat` 内部降级为 `StaticLayout` 优化（仍有性能收益） |
| **CodeView 是否支持 setTextFuture()** | ✅ 支持。继承链：CodeView → ScrollMultiAutoCompleteTextView → AppCompatMultiAutoCompleteTextView → AppCompatAutoCompleteTextView → AppCompatEditText → AppCompatTextView（`setTextFuture` 是 AppCompatTextView 的方法） |
| **结论** | FR-2 无需"降级为直接 setText"，API 23-27 仍可用 StaticLayout 优化。但仍作为 P1 增强（截断方案已消除 ANR） |

---

## 七、闪退分析报告引用

完整根因分析详见：`docs/issues/user/temp/20260731/002/extracted_10/crash_analysis_report.md`

关键证据摘要：
- ANR backtrace 指向 `LineBreaker.nComputeLineBreaksWithHelperIndex`（native 文本换行计算）
- ANR Message 对象是 `CodeView`（id=editText），位于 RecyclerView item 中
- backtrace 经过 `RecyclerView.onLayout` → `onBindViewHolder`
- 主线程连续卡死 ≥ 9916ms（MIUIScout ANR 记录）
- 旧进程被 kill，新进程重启（pid 变更）
