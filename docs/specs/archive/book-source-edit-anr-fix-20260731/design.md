# 技术设计：BookSourceEditAdapter ANR 闪退修复

> 功能名称：`book-source-edit-anr-fix-20260731`
> 文档版本：1.1（2026-07-31 源码核实后修正）
> 创建时间：2026-07-31
> 关联：[spec.md](./spec.md)

---

## 一、Technical Approach（技术方案）

### 1.1 方案总览

采用**文本截断显示（P0）+ PrecomputedText 异步预计算（P1）**组合方案：

```
┌─────────────────────────────────────────────────────────┐
│  onBindViewHolder → holder.bind(editEntity)             │
│                                                         │
│  ① 取 editEntity.value（原始完整值）                     │
│  ② 判断长度：                                            │
│     ├─ null 或 ≤ 5000 → 直接 setText（原逻辑）           │
│     └─ > 5000 → 截断前 5000 字符 + 截断提示文案          │
│  ③ 标记 isTruncated 到 R.id.tag3                         │
│  ④ TextWatcher.afterTextChanged 检查 isTruncated：       │
│     ├─ false → 回写 editEntity.value（原逻辑）           │
│     └─ true → 不回写，保留 editEntity.value 原始完整值   │
│                                                         │
│  ⑤（P1 增强）对 501~5000 字符文本，PrecomputedText 预计算│
└─────────────────────────────────────────────────────────┘
```

### 1.2 截断阈值设计

| 参数 | 值 | 依据 |
|------|-----|------|
| `MAX_DISPLAY_LENGTH` | 5000 字符 | 参考 CodeView.highlight 的 4096 保护阈值（CodeView.kt:221），略放宽；5000 字符 setText 实测 <100ms |
| `TRUNCATE_HINT` | `"\n\n...(文本过长，已截断显示，请点击右上角全屏编辑按钮查看完整内容)"` | 明确引导用户使用已有的 `onFullEditClicked()`（BookSourceEditActivity.kt:144-159）全屏编辑 |

### 1.3 PrecomputedText 兼容性（FR-2，源码+官方文档核实）

| 条件 | 处理 |
|------|------|
| API 28+ | 使用原生 `PrecomputedText` 优化（`PrecomputedTextCompat` 内部调用） |
| API 23-27（minSdk=23） | `PrecomputedTextCompat` 内部降级为 `StaticLayout` 优化（**仍有性能收益，非直接 setText**） |
| API < 23 | 不适用（项目 minSdk=23） |
| 项目依赖 | androidx.core 1.18.0（libs.versions.toml L10）+ appcompat 1.7.1（L7）→ 完全支持 |
| CodeView 支持 | ✅ 继承链到 `AppCompatTextView`，支持 `setTextFuture()` |

> **决策**：FR-2 作为 P1 增强，在 FR-1 截断方案验证通过后实施。截断方案已能消除 ANR，PrecomputedText 是滚动流畅度的进一步增强。
> **修正**：原方案中"API < 28 降级为直接 setText"不准确。实际 API 23-27 仍可用 `StaticLayout` 优化（通过 `PrecomputedTextCompat`），无需降级为直接 setText。

---

## 二、Architecture Decisions（架构决策记录 ADR）

### ADR-1：截断字段 TextWatcher 不回写，保留原始值

**决策**：截断显示的字段，`TextWatcher.afterTextChanged` 不回写 `editEntity.value`，保留原始完整值。

**背景**：原代码（BookSourceEditAdapter.kt:89-91）：
```kotlin
override fun afterTextChanged(s: Editable?) {
    editEntity.value = (s?.toString())  // 回写显示文本到 entity
}
```
若截断显示，TextWatcher 会把截断后的文本（含截断提示）回写到 `editEntity.value`，导致：
1. 保存时保存截断文本（数据丢失）
2. 滚动回来显示截断文本（非原始完整文本）

**方案对比**：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| a. 截断字段不回写，保留原值 | 简单；数据不丢失；保存正确 | 截断字段在列表内无法编辑 | ✅ 选定 |
| b. 截断字段设为只读 + 点击跳全屏 | UX 清晰 | 改动大；影响 focus 逻辑 | ❌ |
| c. 截断字段保留原值备份，仍回写 | 可编辑 | 复杂；截断提示文案会被编辑打乱 | ❌ |

**实现**：用 `R.id.tag3` 标记 `isTruncated: Boolean`，TextWatcher 据此决定是否回写。

**影响**：
- 截断字段在列表内显示为只读（用户编辑无效，但不会报错）
- 用户需点击全屏编辑按钮（已有 `onFullEditClicked`）修改大字段
- 保存时 `getSource()`（BookSourceEditActivity.kt:425-631）读取 `editEntity.value`，得到完整原值

### ADR-2：截断阈值 5000 字符

**决策**：`MAX_DISPLAY_LENGTH = 5000`。

**依据**：
- CodeView.highlight 保护阈值是 4096（CodeView.kt:221：`if (editable.length !in 1..4096) return editable`）
- 闪退分析报告建议 5000
- 5000 字符的 `setText` + `LineBreaker` 计算通常 <100ms（不会 ANR）
- 实际触发 ANR 的文本通常 >>5000（日志显示卡死 >10s，推测文本数十 KB~MB 级别）

### ADR-3：R.id.tag3 新增

**决策**：在 `ids.xml` 新增 `<item name="tag3" type="id" />`。

**背景**：项目已用 `tag`/`tag1`/`tag2`（ids.xml:4-6），需新增 `tag3` 用于标记截断状态。ids.xml L25 已有 `text_watcher`，无命名冲突。

**文件**：`app/src/main/res/values/ids.xml`

### ADR-4：FR-2 PrecomputedText 作为 P1 增强，非 P0 必做

**决策**：FR-1 截断方案已能消除 ANR 根因，FR-2 PrecomputedText 作为滚动流畅度增强。

**依据**：
- 截断后 setText <100ms，已无 ANR 风险
- PrecomputedText 引入异步复杂度（Future 取消、ViewHolder 复用处理）
- 虽然项目依赖完全支持（androidx.core 1.18.0 + appcompat 1.7.1），但仍作为增强而非必做

---

## 三、Data Flow（数据流）

### 3.1 修复后数据流

```
用户打开大书源 JSON
  │
  ▼
FileAssociationActivity 解析 JSON → BookSource 对象
  │  (bookSourceComment = 100KB 超大文本)
  ▼
BookSourceEditActivity.upSourceView(bookSource)  (L293)
  │  创建 EditEntity("bookSourceComment", 100KB文本, ...)  (L317)
  │  editEntity.value = 100KB 原始完整值
  ▼
RecyclerView.onBindViewHolder → adapter.bind(editEntity)
  │
  ├─ rawValue = editEntity.value  (100KB)
  ├─ isTruncated = rawValue.length(100KB) > 5000 → true
  ├─ displayValue = rawValue.substring(0,5000) + TRUNCATE_HINT
  ├─ editText.setText(displayValue)  (5000+提示，<100ms)
  ├─ editText.setTag(R.id.tag3, true)  (标记截断)
  │
  ▼
用户滚动/查看（无 ANR）
  │
  ├─ 若用户编辑截断字段 → TextWatcher 检查 tag3=true → 不回写 → editEntity.value 保持 100KB 原值
  │
  ├─ 若用户点击全屏编辑 → onFullEditClicked() → CodeEditActivity
  │    ├─ 传入 editEntity.value 原始值（非 view.text 截断显示值）
  │    └─ 见 ADR-5
  │
  ▼
用户保存 → getSource()  (L425)
  │  sourceEntities.forEach { editEntity.value → source.bookSourceComment }  (L445)
  │  editEntity.value 仍是 100KB 原值（未回写）→ 正确保存
  ▼
保存成功，数据无丢失
```

### ADR-5：全屏编辑需传入原始值而非显示文本

**问题**：`BookSourceEditActivity.onFullEditClicked()`（L144-159）当前实现：
```kotlin
private fun onFullEditClicked() {  // L144
    val view = window.decorView.findFocus()
    if (view is EditText) {
        val hint = findParentTextInputLayout(view)?.hint?.toString()
        val currentText = view.text.toString()  // L148: 截断字段时这是截断文本！
        val intent = Intent(this, CodeEditActivity::class.java).apply {
            putExtra("text", currentText)  // 传入截断文本，丢失原值
        }
        textEditLauncher.launch(intent)
    }
}
```

**修复**：截断字段的全屏编辑需传入 `editEntity.value` 原始值，而非 `view.text` 显示文本。

**方案**：在 `onFullEditClicked` 中，检查当前 focus 的 EditText 是否截断（`getTag(R.id.tag3)`），若截断则从对应的 `editEntity` 取原值。

**实现**（见 4.3 文件变更 BookSourceEditActivity.kt）。

### 3.2 全屏编辑回写数据流

```
用户点击全屏编辑（截断字段）
  │
  ▼
onFullEditClicked()  (L144)
  ├─ view = findFocus() (EditText/CodeView)
  ├─ isTruncated = view.getTag(R.id.tag3) == true
  ├─ currentText = if (isTruncated) editEntity.value else view.text.toString()
  │                ↑ 从 adapter.editEntities 找到对应 entity 取原值
  ▼
CodeEditActivity 编辑完整内容
  │
  ▼
返回结果 → textEditLauncher  (L128)
  ├─ result.getStringExtra("text") = 编辑后的完整文本
  ├─ view = findFocus() (EditText)
  ├─ view.setText(编辑后文本)
  │    ⚠️ 若编辑后仍 >5000，setText 会再次卡死！
  └─ 需处理：全屏编辑返回后，截断字段仍需截断显示 + 更新 editEntity.value
  ▼
textEditLauncher 回调中：
  ├─ 对返回文本截断显示（若 >5000）
  ├─ 临时移除 TextWatcher 避免 setText 触发回写截断文本
  ├─ view.setText(displayText)
  ├─ 重新添加 TextWatcher
  └─ 截断字段：更新 editEntity.value 为编辑后的完整值（非截断显示值）
```

> **注意**：全屏编辑返回后的 setText 也需截断处理，否则编辑后的大文本返回仍会卡死。见 4.3 文件变更。

---

## 四、File Changes（文件变更）

### 4.1 新增 R.id.tag3

**文件**：`app/src/main/res/values/ids.xml`

**当前内容**（源码核实 L4-6）：
```xml
<item name="tag" type="id" />
<item name="tag1" type="id" />
<item name="tag2" type="id" />
```

**变更**：新增 tag3
```xml
<item name="tag" type="id" />
<item name="tag1" type="id" />
<item name="tag2" type="id" />
<item name="tag3" type="id" />
```

### 4.2 BookSourceEditAdapter.kt（P0 核心修复）

**文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditAdapter.kt`

**当前代码**（源码核实 L18-100，关键 L73 和 L89-91）：
```kotlin
class BookSourceEditAdapter : RecyclerView.Adapter<BookSourceEditAdapter.MyViewHolder>() {

    val editEntityMaxLine = AppConfig.sourceEditMaxLine

    var editEntities: ArrayList<EditEntity> = ArrayList()
        @SuppressLint("NotifyDataSetChanged")
        set(value) {
            field = value
            notifyDataSetChanged()
        }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MyViewHolder {
        val binding = ItemSourceEditBinding
            .inflate(LayoutInflater.from(parent.context), parent, false)
        binding.editText.addLegadoPattern()
        binding.editText.addJsonPattern()
        binding.editText.addJsPattern()
        return MyViewHolder(binding)
    }

    override fun onBindViewHolder(holder: MyViewHolder, position: Int) {
        holder.bind(editEntities[position])
    }

    override fun getItemCount(): Int {
        return editEntities.size
    }

    inner class MyViewHolder(val binding: ItemSourceEditBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(editEntity: EditEntity) = binding.run {
            editText.setTag(R.id.tag, editEntity.key)
            editText.maxLines = editEntityMaxLine
            if (editText.getTag(R.id.tag1) == null) {
                val listener = object : View.OnAttachStateChangeListener {
                    override fun onViewAttachedToWindow(v: View) {
                        editText.isCursorVisible = false
                        editText.isCursorVisible = true
                        editText.isFocusable = true
                        editText.isFocusableInTouchMode = true
                    }
                    override fun onViewDetachedFromWindow(v: View) {}
                }
                editText.addOnAttachStateChangeListener(listener)
                editText.setTag(R.id.tag1, listener)
            }
            editText.getTag(R.id.tag2)?.let {
                if (it is TextWatcher) {
                    editText.removeTextChangedListener(it)
                }
            }
            editText.setText(editEntity.value)  // ← L73 问题代码
            textInputLayout.hint = editEntity.hint
            val textWatcher = object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    editEntity.value = (s?.toString())  // ← L90 回写
                }
            }
            editText.addTextChangedListener(textWatcher)
            editText.setTag(R.id.tag2, textWatcher)
            editText.clearFocus()
        }
    }
}
```

**修复后代码**：
```kotlin
class BookSourceEditAdapter : RecyclerView.Adapter<BookSourceEditAdapter.MyViewHolder>() {

    val editEntityMaxLine = AppConfig.sourceEditMaxLine

    var editEntities: ArrayList<EditEntity> = ArrayList()
        @SuppressLint("NotifyDataSetChanged")
        set(value) {
            field = value
            notifyDataSetChanged()
        }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MyViewHolder {
        val binding = ItemSourceEditBinding
            .inflate(LayoutInflater.from(parent.context), parent, false)
        binding.editText.addLegadoPattern()
        binding.editText.addJsonPattern()
        binding.editText.addJsPattern()
        return MyViewHolder(binding)
    }

    override fun onBindViewHolder(holder: MyViewHolder, position: Int) {
        holder.bind(editEntities[position])
    }

    override fun getItemCount(): Int {
        return editEntities.size
    }

    inner class MyViewHolder(val binding: ItemSourceEditBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(editEntity: EditEntity) = binding.run {
            editText.setTag(R.id.tag, editEntity.key)
            editText.maxLines = editEntityMaxLine
            if (editText.getTag(R.id.tag1) == null) {
                val listener = object : View.OnAttachStateChangeListener {
                    override fun onViewAttachedToWindow(v: View) {
                        editText.isCursorVisible = false
                        editText.isCursorVisible = true
                        editText.isFocusable = true
                        editText.isFocusableInTouchMode = true
                    }
                    override fun onViewDetachedFromWindow(v: View) {}
                }
                editText.addOnAttachStateChangeListener(listener)
                editText.setTag(R.id.tag1, listener)
            }
            editText.getTag(R.id.tag2)?.let {
                if (it is TextWatcher) {
                    editText.removeTextChangedListener(it)
                }
            }
            // 修复：大文本截断显示，避免 LineBreaker.nComputeLineBreaksWithHelperIndex 卡死主线程
            val rawValue = editEntity.value
            val isTruncated = rawValue != null && rawValue.length > MAX_DISPLAY_LENGTH
            val displayValue = if (isTruncated) {
                rawValue!!.substring(0, MAX_DISPLAY_LENGTH) + TRUNCATE_HINT
            } else {
                rawValue
            }
            editText.setText(displayValue)
            editText.setTag(R.id.tag3, isTruncated)
            textInputLayout.hint = editEntity.hint
            val textWatcher = object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    // 截断字段不回写，保留 editEntity.value 原始完整值
                    val truncated = editText.getTag(R.id.tag3) as? Boolean ?: false
                    if (!truncated) {
                        editEntity.value = (s?.toString())
                    }
                }
            }
            editText.addTextChangedListener(textWatcher)
            editText.setTag(R.id.tag2, textWatcher)
            editText.clearFocus()
        }
    }

    companion object {
        // 截断阈值：超过此长度的文本截断显示，避免 LineBreaker native 计算卡死主线程
        // 依据：CodeView.highlight 保护阈值 4096，略放宽至 5000（实测 <100ms）
        const val MAX_DISPLAY_LENGTH = 5000
        const val TRUNCATE_HINT =
            "\n\n...(文本过长，已截断显示，请点击右上角全屏编辑按钮查看完整内容)"
    }
}
```

**变更摘要**：
1. L73 `editText.setText(editEntity.value)` → 截断判断 + `setText(displayValue)`
2. 新增 `editText.setTag(R.id.tag3, isTruncated)` 标记截断状态
3. L90 `afterTextChanged` 增加 `isTruncated` 检查，截断时不回写
4. 新增 `companion object` 定义 `MAX_DISPLAY_LENGTH` 和 `TRUNCATE_HINT`（`const val` 以便 Activity 访问）

### 4.3 BookSourceEditActivity.kt（全屏编辑传值修复）

**文件**：`app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt`

**当前代码**（源码核实 L128-159）：
```kotlin
private val textEditLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
    if (result.resultCode == RESULT_OK) {
        val view = window.decorView.findFocus()
        if (view is EditText) {
            result.data?.getStringExtra("text")?.let {
                view.setText(it)  // ← L133 全屏编辑返回 setText（大文本会卡死）
            }
            result.data?.getIntExtra("cursorPosition", -1)?.takeIf { it in 0 ..< view.text.length }?.let {
                view.setSelection(it)
            }
        } else {
            toastOnUi(R.string.focus_lost_on_textbox)
        }
    }
}

private fun onFullEditClicked() {  // L144
    val view = window.decorView.findFocus()
    if (view is EditText) {
        val hint = findParentTextInputLayout(view)?.hint?.toString()
        val currentText = view.text.toString()  // ← L148 截断字段时这是截断文本
        val intent = Intent(this, CodeEditActivity::class.java).apply {
            putExtra("text", currentText)
            putExtra("title", hint)
            putExtra("cursorPosition", view.selectionStart)
        }
        textEditLauncher.launch(intent)
    } else {
        toastOnUi(R.string.please_focus_cursor_on_textbox)
    }
}
```

**修复后代码**：
```kotlin
private val textEditLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
    if (result.resultCode == RESULT_OK) {
        val view = window.decorView.findFocus()
        if (view is EditText) {
            result.data?.getStringExtra("text")?.let { newText ->
                // 修复：全屏编辑返回的大文本仍需截断显示
                val isTruncated = view.getTag(R.id.tag3) as? Boolean ?: false
                val displayText = if (isTruncated && newText.length > BookSourceEditAdapter.MAX_DISPLAY_LENGTH) {
                    newText.substring(0, BookSourceEditAdapter.MAX_DISPLAY_LENGTH) + BookSourceEditAdapter.TRUNCATE_HINT
                } else {
                    newText
                }
                // 临时移除 TextWatcher 避免 setText 触发回写截断文本
                val tag2 = view.getTag(R.id.tag2)
                if (tag2 is TextWatcher) {
                    view.removeTextChangedListener(tag2)
                }
                view.setText(displayText)
                if (tag2 is TextWatcher) {
                    view.addTextChangedListener(tag2)
                }
                // 截断字段：更新 editEntity.value 为编辑后的完整值（非截断显示值）
                if (isTruncated) {
                    updateEditEntityValue(view, newText)
                }
            }
            result.data?.getIntExtra("cursorPosition", -1)?.takeIf { it in 0 ..< view.text.length }?.let {
                view.setSelection(it)
            }
        } else {
            toastOnUi(R.string.focus_lost_on_textbox)
        }
    }
}

private fun onFullEditClicked() {
    val view = window.decorView.findFocus()
    if (view is EditText) {
        val hint = findParentTextInputLayout(view)?.hint?.toString()
        // 修复：截断字段传入 editEntity.value 原始完整值，而非 view.text 截断显示值
        val isTruncated = view.getTag(R.id.tag3) as? Boolean ?: false
        val currentText = if (isTruncated) {
            findEditEntityValueByView(view) ?: view.text.toString()
        } else {
            view.text.toString()
        }
        val intent = Intent(this, CodeEditActivity::class.java).apply {
            putExtra("text", currentText)
            putExtra("title", hint)
            putExtra("cursorPosition", view.selectionStart)
        }
        textEditLauncher.launch(intent)
    } else {
        toastOnUi(R.string.please_focus_cursor_on_textbox)
    }
}

// 辅助：从 adapter.editEntities 中查找当前 view 对应的 editEntity.value
private fun findEditEntityValueByView(view: View): String? {
    val key = view.getTag(R.id.tag) as? String ?: return null
    val entities = adapter.editEntities
    return entities.find { it.key == key }?.value
}

// 辅助：更新当前 view 对应的 editEntity.value
private fun updateEditEntityValue(view: View, newValue: String) {
    val key = view.getTag(R.id.tag) as? String ?: return
    val entities = adapter.editEntities
    entities.find { it.key == key }?.let { entity ->
        entity.value = newValue
    }
}
```

**变更摘要**：
1. `textEditLauncher` 回调：全屏编辑返回的大文本截断显示 + 更新 `editEntity.value` 为完整值
2. `onFullEditClicked`：截断字段传入 `editEntity.value` 原始值
3. 新增 `findEditEntityValueByView` / `updateEditEntityValue` 辅助方法
4. `MAX_DISPLAY_LENGTH` 和 `TRUNCATE_HINT` 在 `BookSourceEditAdapter.companion object` 中定义为 `const val`（非 private），以便 Activity 访问

### 4.4 RssSourceEditAdapter.kt（P2 同模式修复）

**文件**：`app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditAdapter.kt`

**当前代码**（源码核实 L76-126，关键 L102 和 L118-120）：
```kotlin
inner class EditTextViewHolder(val binding: ItemSourceEditBinding) :
    RecyclerView.ViewHolder(binding.root) {

    fun bind(editEntity: EditEntity) = binding.run {
        editText.maxLines = editEntityMaxLine
        if (editText.getTag(R.id.tag1) == null) {
            // ... OnAttachStateChangeListener（与 BookSourceEditAdapter 相同）
        }
        editText.getTag(R.id.tag2)?.let {
            if (it is TextWatcher) {
                editText.removeTextChangedListener(it)
            }
        }
        editText.setText(editEntity.value)  // ← L102 问题代码
        textInputLayout.hint = editEntity.hint
        val textWatcher = object : TextWatcher {
            // ...
            override fun afterTextChanged(s: Editable?) {
                editEntity.value = (s?.toString())  // ← L119 回写
            }
        }
        editText.addTextChangedListener(textWatcher)
        editText.setTag(R.id.tag2, textWatcher)
        editText.clearFocus()
    }
}
```

**修复**：与 BookSourceEditAdapter.kt 相同的截断逻辑（L102 截断 + L119 检查 isTruncated）。

**变更摘要**：
1. L102 `editText.setText(editEntity.value)` → 截断判断 + `setText(displayValue)`
2. 新增 `editText.setTag(R.id.tag3, isTruncated)`
3. L119 `afterTextChanged` 增加 `isTruncated` 检查
4. 新增 `companion object`（或复用 BookSourceEditAdapter 的常量）

> **实施建议**：提取截断逻辑到 `CodeView` 扩展函数（如 `EditText.setSafeText(value: String?)`），避免两个 Adapter 重复代码。见 4.5。

### 4.5（可选）CodeView 扩展函数提取

**文件**：`app/src/main/java/io/legado/app/ui/widget/code/CodeViewExt.kt`（新增）或追加到 `CodeViewExtensions.kt`

**目的**：提取截断逻辑为扩展函数，避免 BookSourceEditAdapter / RssSourceEditAdapter 重复代码。

**设计**：
```kotlin
// CodeViewExt.kt（新增文件）或追加到 CodeViewExtensions.kt
package io.legado.app.ui.widget.code

import android.widget.EditText
import io.legado.app.R

/**
 * 安全设置文本：对超大文本截断显示，避免 LineBreaker native 计算卡死主线程。
 *
 * @param value 原始文本值
 * @return true=已截断（调用方应跳过 TextWatcher 回写），false=未截断
 */
fun EditText.setSafeText(value: String?): Boolean {
    val isTruncated = value != null && value.length > MAX_DISPLAY_LENGTH
    val displayValue = if (isTruncated) {
        value!!.substring(0, MAX_DISPLAY_LENGTH) + TRUNCATE_HINT
    } else {
        value
    }
    setText(displayValue)
    setTag(R.id.tag3, isTruncated)
    return isTruncated
}

const val MAX_DISPLAY_LENGTH = 5000
const val TRUNCATE_HINT = "\n\n...(文本过长，已截断显示，请点击右上角全屏编辑按钮查看完整内容)"
```

> **决策**：实施时评估是否提取。若两个 Adapter 改动一致，提取扩展函数更优（DRY 原则）。若提取，BookSourceEditAdapter 的 `companion object` 常量可移除，改为引用扩展函数所在文件的顶层常量。

### 4.6 HttpTtsEditDialog.kt（P2 评估修复）

**文件**：`app/src/main/java/io/legado/app/ui/book/read/config/HttpTtsEditDialog.kt`

**当前代码**（源码核实 L89-99）：
```kotlin
fun initView(httpTTS: HttpTTS) {  // L89
    binding.tvName.setText(httpTTS.name)  // L90
    binding.tvUrl.setText(httpTTS.url)  // L91
    binding.tvContentType.setText(httpTTS.contentType)  // L92
    binding.tvConcurrentRate.setText(httpTTS.concurrentRate)  // L93
    binding.tvLoginUrl.setText(httpTTS.loginUrl)  // L94
    binding.tvLoginUi.setText(httpTTS.loginUi)  // L95
    binding.tvLoginCheckJs.setText(httpTTS.loginCheckJs)  // L96
    binding.tvHeaders.setText(httpTTS.header)  // L97
    binding.tvJsLib.setText(httpTTS.jsLib)  // L98
}
```

**字段类型核实**（dialog_http_tts_edit.xml 核实）：
- `tv_name`：`ThemeEditText`（普通 EditText，XML L42-46）
- 其余 8 个（tv_url/tv_content_type/tv_concurrent_rate/tv_login_url/tv_login_ui/tv_login_check_js/tv_headers/tv_jsLib）：`CodeView`（XML L56/70/84/98/112/126/140/154）

**风险评估**：
- `tv_name`/`tv_url`/`tv_content_type`/`tv_concurrent_rate`：通常 <500 字符，低风险
- `tv_login_url`/`tv_login_ui`/`tv_login_check_js`/`tv_headers`/`tv_js_lib`：理论上可能较大（header/json/js），中风险

**修复**：对可能超大的字段（header/jsLib/loginUi/loginCheckJs）应用 `setSafeText` 扩展函数：
```kotlin
fun initView(httpTTS: HttpTTS) {
    binding.tvName.setText(httpTTS.name)
    binding.tvUrl.setText(httpTTS.url)
    binding.tvContentType.setText(httpTTS.contentType)
    binding.tvConcurrentRate.setText(httpTTS.concurrentRate)
    binding.tvLoginUrl.setSafeText(httpTTS.loginUrl)
    binding.tvLoginUi.setSafeText(httpTTS.loginUi)
    binding.tvLoginCheckJs.setSafeText(httpTTS.loginCheckJs)
    binding.tvHeaders.setSafeText(httpTTS.header)
    binding.tvJsLib.setSafeText(httpTTS.jsLib)
}
```

**HttpTtsEditDialog 实现差异**（源码核实）：
- `onFullEditClicked`（L118-133）用 `focusedEditText` 缓存（L46/L122），而非 `findFocus()`
- `textEditLauncher`（L102-117）回调用 `focusedEditText`（L104），非 `findFocus()`
- `dataFromView()`（L172-185）直接从 `view.text.toString()` 读取（截断后会保存截断文本）

**dataFromView 修复**：截断字段需从原始数据或标记读取，避免保存截断文本。两种方案：
- 方案 a：`dataFromView` 检查 `view.getTag(R.id.tag3)`，截断字段从 `viewModel.httpTTS`（原始数据）读取
- 方案 b：截断字段保留原值到 `tag4`，`dataFromView` 从 `tag4` 读取

> **实施建议**：HttpTtsEditDialog 改动较复杂（需同步修复 dataFromView + focusedEditText 缓存逻辑），作为 P2 评估后实施。优先完成 P0/P1。

---

## 五、状态管理

### 5.1 截断字段状态

| 状态 | 存储 | 用途 |
|------|------|------|
| `isTruncated: Boolean` | `editText.getTag(R.id.tag3)` | TextWatcher 据此决定是否回写；onFullEditClicked 据此决定传值 |
| `editEntity.value`（原始完整值） | `EditEntity.value` | 保存时读取；全屏编辑传入；不被截断 TextWatcher 覆盖 |
| `displayValue`（截断显示值） | 仅 UI 显示 | setText 的参数，不持久化 |

### 5.2 状态流转

```
editEntity.value = 100KB（原始）
  ↓ bind()
editText.tag3 = true, editText.text = 截断显示值, editEntity.value = 100KB（不变）
  ↓ 用户编辑截断字段（不回写）
editEntity.value = 100KB（不变）
  ↓ 用户点击全屏编辑
onFullEditClicked → 传入 editEntity.value(100KB) → CodeEditActivity
  ↓ 用户编辑后返回
textEditLauncher → newText = 80KB
  ↓ 截断显示 + 更新 editEntity.value
editText.text = 截断显示值, editEntity.value = 80KB（更新）, editText.tag3 = true
  ↓ 保存
getSource() → source.comment = editEntity.value = 80KB（正确）
```

---

## 六、错误处理

| 场景 | 处理 |
|------|------|
| `editEntity.value` 为 null | `isTruncated = false`，直接 `setText(null)`（原行为） |
| 截断后 `substring` 越界 | 不会发生：`length > 5000` 保证 `substring(0, 5000)` 合法 |
| 全屏编辑返回 null | `result.data?.getStringExtra("text")?.let {}` 不执行（原行为） |
| ViewHolder 复用时 tag3 残留 | 每次 `bind()` 都重新 `setTag(R.id.tag3, isTruncated)`，覆盖旧值 |
| PrecomputedText 预计算被取消 | FR-2 实施时，ViewHolder 复用取消 FutureTask（onViewRecycled） |
| `findEditEntityValueByView` 找不到 entity | 返回 null，`onFullEditClicked` 回退为 `view.text.toString()`（原行为） |

---

## 七、测试设计

### 7.1 单元测试（可选）

| 测试项 | 方法 |
|--------|------|
| 截断逻辑正确性 | 构造 100KB 字符串，验证 `setSafeText` 返回 true 且显示值长度 = 5000 + 提示长度 |
| 边界值 | 长度 = 5000（不截断）、5001（截断）、0（不截断）、null（不截断） |

> 单元测试需 Mock EditText，或提取纯函数 `truncateText(value: String?): Pair<String, Boolean>` 测试。

### 7.2 真机测试（必做）

| 测试场景 | 步骤 | 预期 |
|---------|------|------|
| 大书源打开不闪退 | 构造 100KB comment 的书源 JSON，文件关联打开，滚动到 comment | 无 ANR，显示截断文本+提示 |
| 截断字段全屏编辑 | 点击截断字段的全屏编辑按钮 | CodeEditActivity 显示完整 100KB 文本 |
| 全屏编辑返回 | 在 CodeEditActivity 编辑后返回 | 列表显示截断文本，editEntity.value 更新 |
| 保存正确性 | 编辑后保存，重新打开 | 数据正确（非截断文本） |
| 小文本不变 | 编辑 bookSourceName | 行为与修复前一致 |
| RSS 源同样测试 | 构造大 RSS 源 | 无 ANR |
| HttpTTS 对话框 | 构造大 header 的 HttpTTS | 对话框正常打开 |

### 7.3 测试脚本

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/quick_build_install.py` | 编译+安装+L1 验证 |
| `ai_tests/scripts/import_rss_source.py` | 导入测试源（可改造为导入大书源） |
| `ai_tests/scripts/swipe_test_log.py` | 滑动日志分析（验证无 ANR） |

### 7.4 测试包

- **测试包**：`io.legado.miss.app.debug`（项目代码优化用测试包）
- 依据：AGENTS.md「真机测试包选择规范」——代码优化任务用测试包（debug 构建，含调试日志+未混淆）

---

## 八、性能影响评估

| 指标 | 修复前 | 修复后 | 影响 |
|------|--------|--------|------|
| 大文本 setText 耗时 | >10s（ANR） | <100ms（截断后） | ✅ 显著改善 |
| 小文本 setText 耗时 | <10ms | <10ms（不变） | 无影响 |
| 内存占用 | 大文本全文加载到 EditText | 截断后仅 5000 字符在 EditText | ✅ 略有改善 |
| 滚动帧率 | 卡死 | 流畅 | ✅ 显著改善 |
| PrecomputedText（FR-2） | N/A | 后台线程预计算 | 中等文本滚动更流畅 |

---

## 九、回滚策略

### 9.1 回滚条件

若修复后出现以下问题，考虑回滚：
1. 截断显示导致用户无法查看完整内容（UX 不可接受）
2. 全屏编辑传值/回写逻辑有 bug 导致数据丢失
3. 编译失败或运行时崩溃

### 9.2 回滚方法

```
git revert <commit-hash>
```

或手动还原以下文件：
1. `BookSourceEditAdapter.kt` → 还原 L73 `editText.setText(editEntity.value)` + L90 回写
2. `RssSourceEditAdapter.kt` → 同上
3. `BookSourceEditActivity.kt` → 还原 onFullEditClicked / textEditLauncher
4. `HttpTtsEditDialog.kt` → 还原 initView
5. `ids.xml` → 移除 tag3（可选，保留无害）

### 9.3 回滚验证

回滚后验证：
1. 编译通过
2. 小文本编辑正常
3. 大文本恢复 ANR（确认回滚生效，作为基线）

---

## 十、依赖与兼容性

| 依赖 | 版本要求 | 项目现状 | 兼容性 |
|------|---------|---------|--------|
| AndroidX Core（FR-2 PrecomputedTextCompat） | androidx.core 1.1.0+ | 1.18.0（libs.versions.toml L10） | ✅ 完全支持 |
| AndroidX AppCompat（setTextFuture） | appcompat 1.1.0+ | 1.7.1（libs.versions.toml L7） | ✅ 完全支持 |
| minSdk | 14+（PrecomputedTextCompat） | 23（build.gradle L74） | ✅ 满足 |
| R.id.tag3 | 新增 ids.xml | 无依赖 | ✅ 无冲突 |
| CodeView 继承链 | 需为 AppCompatTextView 子类 | CodeView → ... → AppCompatTextView | ✅ 支持 setTextFuture() |

> **结论**：FR-1（截断方案）无新增依赖，完全兼容 minSdk 23。FR-2（PrecomputedText）项目依赖完全支持，API 23-27 通过 StaticLayout 优化（非降级为直接 setText），API 28+ 用原生 PrecomputedText。
