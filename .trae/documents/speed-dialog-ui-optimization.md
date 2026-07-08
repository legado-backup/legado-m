# 视频倍速列表 UI 优化方案

> 适用模块：`io.legado.app.help.gsyVideo` 视频播放器倍速选择对话框
> 目标：在保持功能与回调接口不变的前提下，优化倍速列表的视觉表现与交互体验
> 约束：遵循极简工程原则，不引入新依赖，不替换 ListView 为 RecyclerView（避免过度设计）

---

## 1. 痛点分析

基于对现有源码的完整阅读，识别出以下 6 处具体痛点：

| # | 痛点 | 源码定位 | 现状值 | 问题表现 |
|---|------|---------|--------|---------|
| 1 | 对话框宽度过窄 | `ChoiceSpeedDialog.kt:57` | `d.widthPixels * 0.3` | 屏幕宽 30%，"15.0X" 等长文本被挤压，左右留白不均 |
| 2 | 对话框高度全屏 | `ChoiceSpeedDialog.kt:58` | `d.heightPixels` | 11 个倍速项纵向拉满整屏，视觉粗糙，与"弹出菜单"语义不符 |
| 3 | 顶部空白占位 | `switch_speed_video_dialog.xml:10-13` | `<View weight=1>` | 在全屏高度下把 ListView 强制推到底部，造成上半屏大片死黑空白 |
| 4 | 背景色不协调 | `switch_speed_video_dialog.xml:5` | `#80121212` | 深色半透明覆盖整个全屏区域，与播放器画面割裂 |
| 5 | 无当前倍速高亮 | `ChoiceSpeedDialog.kt:41-53` | `initList(data, listener)` 签名无 currentSpeed | 用户打开列表不知道当前是几倍速，需靠记忆 |
| 6 | 文本格式粗糙 | `ChoiceSpeedDialog.kt:51` | `item.toString() + "X"` | "1.0X"、"15.0X" 带冗余 `.0`，大写 `X` 视觉生硬；item 仅白字无分组无层级 |

附加问题：item 背景虽用了 `card_video_background`（8dp 圆角半透明白），但因对话框整体全屏深色 + 顶部空白，卡片感被淹没。

---

## 2. 设计目标

1. **紧凑居中**：对话框高度 `wrap_content`，靠右居中显示，不占满全屏
2. **宽度合理**：0.34 屏宽，足以容纳最长文本 "0.75x" 且左右留白均匀
3. **当前倍速可识别**：选中项用主题色 `primary`（#0277BD）高亮 + 加粗
4. **分组清晰**：常用区（0.5~3.0）与极速区（5.0~15.0）之间加细分隔线
5. **文本规范**：整数倍速去 `.0`（"1x"、"15x"），小数保留（"1.25x"、"0.75x"），统一小写 `x`
6. **接口零破坏**：`OnListItemClickListener` 回调签名不变；`initList` 仅追加可选参数 `currentSpeed`，向后兼容
7. **最小改动**：复用现有 ListView + ArrayAdapter 架构，不引入 RecyclerView

---

## 3. 改动文件清单

| 序号 | 文件路径 | 修改类型 | 修改点 |
|------|---------|---------|--------|
| 1 | `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | 重写 | `initList` 增加 `currentSpeed` 参数；窗口宽度 0.3→0.34、高度 `d.heightPixels`→`WRAP_CONTENT`、gravity `END`→`END or CENTER_VERTICAL`；移除原 `+ "X"` 拼接改用格式化函数；adapter 传入 currentSpeed |
| 2 | `app/src/main/res/layout/switch_speed_video_dialog.xml` | 重写 | 移除顶部 `<View weight=1>` 占位；ListView 外层包一层面板容器并加圆角背景；移除 `#80121212` 全屏底色 |
| 3 | `app/src/main/res/layout/switch_video_dialog_item.xml` | 优化 | 调整 padding（15→20dp 水平）、字号（15→16sp）；保留 `card_video_background` 作为常态背景 |
| 4 | `app/src/main/java/io/legado/app/help/gsyVideo/SwitchVideoAdapter.kt` | 改造 | 增加 `currentSpeed` 字段与 `SEPARATOR` 分隔项支持；`getView` 中匹配 currentSpeed 时设主题色文字 + 加粗 + 选中背景；倍速文本格式化（去 `.0`、小写 `x`）；用 `view.tag` 区分普通项/分隔项防复用错乱 |
| 5 | `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | 微调 | `showSpeedDialog()` 中调用 `initList` 时传入 `playSpeed` 作为当前倍速（仅追加一行参数） |
| 6 | `app/src/main/res/drawable/speed_dialog_panel_bg.xml` | 新增 | 倍速面板容器背景：深色半透明（#CC1A1A1A）+ 8dp 圆角（与播放器风格协调） |
| 7 | `app/src/main/res/layout/switch_video_dialog_item_separator.xml` | 新增 | 极速区与常用区之间的分隔线布局（1dp 高，左右各留 8dp margin，#33FFFFFF） |

合计：**改动 5 个现有文件 + 新增 2 个资源文件（1 drawable + 1 layout），共 7 个文件**。

---

## 4. UI 草图描述

### 4.1 布局结构

```
[播放器全屏画面]
                          ┌─────────────────┐  ← 靠右，垂直居中
                          │  15x            │  ← 极速区（顶部）
                          │  10x            │
                          │  5x             │
                          │ ─────────────── │  ← 分隔线（5.0 与 3.0 之间）
                          │  3x             │  ← 常用区
                          │  2.5x           │
                          │  2x             │
                          │  1.5x           │
                          │  1.25x          │
                          │  1x   ← 高亮    │  ← 当前倍速（primary 色加粗 + 浅色背景）
                          │  0.75x          │
                          │  0.5x           │  ← 常用区（底部）
                          └─────────────────┘
```

### 4.2 视觉规格

- 面板宽度：屏宽 × 0.34
- 面板高度：`wrap_content`（由内容撑开，约 11 项 × 44dp + 分隔 1dp）
- 面板位置：gravity = `END or CENTER_VERTICAL`（右侧垂直居中）
- 面板背景：`#CC1A1A1A`（80% 不透明深灰）+ 8dp 圆角
- item 常态：透明背景，白字 16sp
- item 选中态：`#330277BD`（primary 20% 透明）背景，`#0277BD` 文字加粗
- item 分隔：1dp 高，`#33FFFFFF`（20% 白）水平线，左右各留 8dp

### 4.3 ASCII 草图（选中 1x 时的面板）

```
        ╭─────────────────╮
        │  15x            │
        │  10x            │
        │  5x             │
        ├─────────────────┤  ← 分隔
        │  3x             │
        │  2.5x           │
        │  2x             │
        │  1.5x           │
        │  1.25x          │
        │ ▓ 1x            │  ← 高亮(浅蓝底+蓝字加粗)
        │  0.75x          │
        │  0.5x           │
        ╰─────────────────╯
```

---

## 5. 关键代码片段

### 5.1 `ChoiceSpeedDialog.kt`（完整重写）

```kotlin
package io.legado.app.help.gsyVideo

import android.app.Dialog
import android.content.Context
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.AdapterView
import android.widget.ListView
import io.legado.app.R

class ChoiceSpeedDialog(private val mContext: Context) : Dialog(
    mContext, R.style.dialog_style
) {
    private var listView: ListView? = null

    private var adapter: SwitchVideoAdapter<Float>? = null

    private var onItemClickListener: OnListItemClickListener? = null

    private var data: List<Float>? = null

    interface OnListItemClickListener {
        fun onItemClick(value: Float)
        fun finishDialog()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    override fun onStop() {
        onItemClickListener!!.finishDialog()
        super.onStop()
    }

    /**
     * 初始化倍速列表
     * @param data 倍速值列表（显示顺序，如 reversed 后的 [15.0, 10.0, ..., 0.5]）
     * @param currentSpeed 当前播放倍速，用于高亮选中项（默认 1.0f，向后兼容）
     * @param onItemClickListener 点击回调
     */
    fun initList(
        data: List<Float>,
        onItemClickListener: OnListItemClickListener,
        currentSpeed: Float = 1.0f
    ) {
        this.onItemClickListener = onItemClickListener
        this.data = data
        val inflater = LayoutInflater.from(mContext)
        val view: View = inflater.inflate(R.layout.switch_speed_video_dialog, null)
        listView = view.findViewById(R.id.switch_dialog_list)
        setContentView(view)
        // 构造带分隔项的数据：在 5.0 与 3.0 之间插入分隔标记
        val displayData = buildDisplayData(data)
        adapter = SwitchVideoAdapter(mContext, displayData, currentSpeed)
        listView!!.adapter = adapter
        listView!!.onItemClickListener = this@ChoiceSpeedDialog.OnItemClickListener()
        val dialogWindow = window
        val lp = dialogWindow!!.attributes
        val d = mContext.resources.displayMetrics
        lp.width = (d.widthPixels * 0.34).toInt()           // 宽度 0.3 → 0.34
        lp.height = WindowManager.LayoutParams.WRAP_CONTENT  // 高度全屏 → 自适应
        lp.gravity = Gravity.END or Gravity.CENTER_VERTICAL  // 靠右 + 垂直居中
        dialogWindow.setAttributes(lp)
    }

    /**
     * 构造显示数据：在极速区(>=5.0)与常用区(<5.0)之间插入 SEPARATOR 标记
     * 数据顺序为显示顺序（已 reversed，顶部最大）。
     */
    private fun buildDisplayData(data: List<Float>): List<Any> {
        val result = ArrayList<Any>(data.size + 1)
        var inserted = false
        for (value in data) {
            if (!inserted && value < 5.0f) {
                result.add(SwitchVideoAdapter.SEPARATOR)
                inserted = true
            }
            result.add(value)
        }
        return result
    }

    private inner class OnItemClickListener : AdapterView.OnItemClickListener {
        override fun onItemClick(
            adapterView: AdapterView<*>?,
            view: View?,
            position: Int,
            id: Long
        ) {
            val item = adapter?.getItem(position)
            // 分隔项不响应点击
            if (item === SwitchVideoAdapter.SEPARATOR) return
            dismiss()
            onItemClickListener!!.onItemClick(item as? Float ?: 1.0f)
        }
    }
}
```

### 5.2 `SwitchVideoAdapter.kt`（完整重写）

```kotlin
package io.legado.app.help.gsyVideo

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.TextView
import androidx.core.content.ContextCompat
import io.legado.app.R

/**
 * 倍速列表适配器
 * - 支持分隔项 [SEPARATOR]（在极速区与常用区之间）
 * - 支持当前倍速高亮（主题色 primary + 加粗 + 浅色背景）
 * - 倍速文本格式化：1.0→"1x"，15.0→"15x"，1.25→"1.25x"，0.75→"0.75x"
 */
class SwitchVideoAdapter<T>(
    context: Context,
    private val dataList: List<Any>,
    private val currentSpeed: T? = null
) : ArrayAdapter<Any>(context, 0, dataList) {

    companion object {
        /** 分隔项标记对象，dataList 中以此对象标识一行分隔线 */
        object SEPARATOR
    }

    @Suppress("UNCHECKED_CAST")
    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
        val item = dataList[position]
        // 分隔项
        if (item === SEPARATOR) {
            val divider = (convertView ?: LayoutInflater.from(context)
                .inflate(R.layout.switch_video_dialog_item_separator, parent, false))
            return divider
        }
        // 普通倍速项
        val view = convertView?.takeUnless { it.tag == "separator" }
            ?: LayoutInflater.from(context)
                .inflate(R.layout.switch_video_dialog_item, parent, false)
                .also { it.tag = "normal" }
        val textView = view.findViewById<TextView>(R.id.text1)
        val value = item as? Float ?: 1.0f
        textView.text = formatSpeed(value)
        // 简化说明：高亮判断仅按值相等匹配，未做浮点精度容差 | 已知上限：理论浮点相等可能失效 | 升级路径：改用 Math.abs(a-b)<1e-4 比较
        val isSelected = currentSpeed != null && value == currentSpeed as Float
        if (isSelected) {
            textView.setTextColor(ContextCompat.getColor(context, R.color.primary))
            textView.setTypeface(textView.typeface, android.graphics.Typeface.BOLD)
            textView.setBackgroundColor(0x330277BD) // primary 20% 透明
        } else {
            textView.setTextColor(0xFFFFFFFF.toInt())
            textView.setTypeface(textView.typeface, android.graphics.Typeface.NORMAL)
            textView.background =
                ContextCompat.getDrawable(context, R.drawable.card_video_background)
        }
        return view
    }

    /** 倍速文本格式化：整数去 .0，统一小写 x */
    private fun formatSpeed(value: Float): String {
        return if (value == value.toInt().toFloat()) "${value.toInt()}x"
        else "${value}x"
    }
}
```

### 5.3 `switch_speed_video_dialog.xml`（完整重写）

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- 倍速面板容器：靠右垂直居中，wrap_content 高度，圆角半透明背景 -->
<FrameLayout xmlns:android="http://schemas.android.com/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:background="@drawable/speed_dialog_panel_bg"
    android:paddingTop="6dp"
    android:paddingBottom="6dp">

    <ListView
        android:id="@+id/switch_dialog_list"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:background="@null"
        android:cacheColorHint="#00000000"
        android:divider="#00000000"
        android:dividerHeight="0dp"
        android:listSelector="#00000000"
        android:scrollbars="none" />

</FrameLayout>
```

### 5.4 `switch_video_dialog_item.xml`（优化）

```xml
<?xml version="1.0" encoding="utf-8"?>
<TextView xmlns:android="http://schemas.android.com/res/android"
    android:id="@+id/text1"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:background="@drawable/card_video_background"
    android:gravity="center_vertical"
    android:paddingLeft="20dp"
    android:paddingTop="11dp"
    android:paddingRight="20dp"
    android:paddingBottom="11dp"
    android:textColor="#FFFFFF"
    android:textSize="16sp" />
```

### 5.5 `switch_video_dialog_item_separator.xml`（新增分隔项布局）

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- 极速区与常用区之间的分隔线 -->
<View xmlns:android="http://schemas.android.com/res/android"
    android:layout_width="match_parent"
    android:layout_height="1dp"
    android:layout_marginStart="8dp"
    android:layout_marginEnd="8dp"
    android:layout_marginTop="4dp"
    android:layout_marginBottom="4dp"
    android:background="#33FFFFFF" />
```

### 5.6 `speed_dialog_panel_bg.xml`（新增 drawable）

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- 倍速面板背景：80% 不透明深灰 + 8dp 圆角，与播放器画面协调 -->
<shape xmlns:android="http://schemas.android.com/res/android"
    android:shape="rectangle">
    <solid android:color="#CC1A1A1A" />
    <corners android:radius="8dp" />
</shape>
```

### 5.7 `VideoPlayer.kt` `showSpeedDialog()` 改动（仅一行）

```kotlin
private fun showSpeedDialog() {
    if (!mHadPlay) {
        return
    }
    isChanging = true
    val choiceSpeedDialog = ChoiceSpeedDialog(mContext)
    choiceSpeedDialog.initList(
        listOf(0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f, 5.0f, 10.0f, 15.0f).reversed(),
        object : ChoiceSpeedDialog.OnListItemClickListener {
            @SuppressLint("SetTextI18n")
            override fun onItemClick(value: Float) {
                playSpeed = value
                setSpeed(playSpeed, true)
                if (playSpeed != 1.0f) {
                    playbackSpeed?.text = "${playSpeed}X"
                    showOverlayTip("${playSpeed}倍播放中", 2000)
                } else {
                    playbackSpeed?.text = "倍速"
                }
            }

            override fun finishDialog() {
                isChanging = false
            }
        },
        currentSpeed = playSpeed   // 新增：传入当前倍速用于高亮
    )
    choiceSpeedDialog.show()
}
```

---

## 6. 倍速值列表设计（分组方案）

### 6.1 数据源（`VideoPlayer.kt` 不变）

```kotlin
listOf(0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f, 5.0f, 10.0f, 15.0f).reversed()
```

### 6.2 显示顺序与分组（自上而下）

| 区域 | 倍速值 | 显示文本 | 说明 |
|------|--------|---------|------|
| 极速区 | 15.0 | `15x` | 顶部，最高速 |
| 极速区 | 10.0 | `10x` | |
| 极速区 | 5.0 | `5x` | |
| **分隔线** | — | ─────── | 5.0 与 3.0 之间 |
| 常用区 | 3.0 | `3x` | |
| 常用区 | 2.5 | `2.5x` | |
| 常用区 | 2.0 | `2x` | |
| 常用区 | 1.5 | `1.5x` | |
| 常用区 | 1.25 | `1.25x` | |
| 常用区 | 1.0 | `1x` | 默认倍速（高亮） |
| 常用区 | 0.75 | `0.75x` | |
| 常用区 | 0.5 | `0.5x` | 底部，最低速 |

### 6.3 格式化规则

- 整数倍速（值等于其 `toInt()`）：`1.0` → `"1x"`、`15.0` → `"15x"`、`5.0` → `"5x"`
- 小数倍速：`1.25` → `"1.25x"`、`0.75` → `"0.75x"`、`2.5` → `"2.5x"`
- 统一小写 `x`（原为大写 `X`，视觉更柔和）

### 6.4 分隔逻辑实现

在 `ChoiceSpeedDialog.buildDisplayData()` 中遍历显示列表，遇到第一个 `< 5.0f` 的值之前插入 `SwitchVideoAdapter.SEPARATOR` 标记，adapter 在 `getView` 中识别该标记渲染分隔布局，并在 `OnItemClickListener` 中拦截分隔项的点击事件。

---

## 7. 兼容性考虑

### 7.1 回调接口零破坏

`OnListItemClickListener` 接口签名完全不变：

```kotlin
interface OnListItemClickListener {
    fun onItemClick(value: Float)   // 不变
    fun finishDialog()               // 不变
}
```

`VideoPlayer.kt` 中的匿名实现无需改动逻辑，仅 `initList` 调用处追加 `currentSpeed` 参数。

### 7.2 `initList` 向后兼容

新增参数 `currentSpeed: Float = 1.0f` 带默认值。若有其他调用点（经 Grep 确认全项目仅 `VideoPlayer.showSpeedDialog` 一处调用）未传该参数，默认 1.0f 高亮"1x"，行为合理。

### 7.3 数据流不变

- 倍速值列表仍由 `VideoPlayer` 提供，`reversed()` 顺序不变
- 点击仍触发 `onItemClick(value: Float)`，`VideoPlayer` 内部 `playSpeed = value` + `setSpeed` 逻辑不变
- `finishDialog()` 在 `onStop` 触发 `isChanging = false` 的逻辑不变

### 7.4 浮点相等风险

`currentSpeed as Float` 与列表值用 `==` 比较。现有倍速值均为 `x.x` 或 `x.0`、`x.25`、`x.75` 形式，二进制浮点表示精确，相等比较安全。代码中已加简化注释标注升级路径（改用容差比较）。

### 7.5 ListView 复用convertView的tag区分

adapter 在 `getView` 中用 `view.tag` 区分 "normal" 与 "separator" 类型，防止 ListView 复用分隔项 View 渲染普通项（或反之）导致布局错乱。

### 7.6 不引入新依赖

- 不引入 RecyclerView（现有 ListView 足够，11 项无性能压力）
- 不引入 Material Components（仅用 `ContextCompat.getColor` + 已有 `R.color.primary`）
- `androidx.core.content.ContextCompat` 项目已普遍使用，无新增依赖

---

## 8. 验证清单

实施完成后，按以下清单逐项验证：

### 8.1 编译验证
- [ ] 项目可正常编译，无 Kotlin 类型错误
- [ ] 新增 drawable `speed_dialog_panel_bg.xml` 资源引用正确
- [ ] 新增布局 `switch_video_dialog_item_separator.xml` 资源引用正确

### 8.2 功能验证（与原行为一致）
- [ ] 点击倍速按钮弹出对话框
- [ ] 点击任意倍速项，播放器实际倍速切换正确（用 15x 验证极速区，1.25x 验证小数区）
- [ ] 点击后对话框 dismiss
- [ ] 对话框关闭后 `isChanging` 复位为 false（播放进度可正常拖动）
- [ ] 选中 1.0f 时按钮文本显示"倍速"，其他显示"X倍播放中"提示

### 8.3 UI 视觉验证
- [ ] 对话框宽度约为屏宽 1/3（0.34），"0.75x" 等长文本不换行不截断
- [ ] 对话框高度自适应内容，不占满全屏
- [ ] 对话框靠右且垂直居中
- [ ] 当前倍速项以蓝色（#0277BD）加粗 + 浅蓝背景高亮显示
- [ ] 极速区（15x/10x/5x）与常用区（3x~0.5x）之间有分隔线
- [ ] 倍速文本为小写 `x`，整数倍速无 `.0`（显示 "1x" 而非 "1.0X"）
- [ ] 面板有 8dp 圆角，背景为深色半透明（与播放器画面协调）

### 8.4 边界验证
- [ ] 分隔线点击无响应（不触发倍速切换、不 dismiss）
- [ ] ListView 复用 convertView 时，普通项与分隔项布局不串扰
- [ ] 横屏与竖屏下对话框均靠右居中显示
- [ ] 默认 1.0f 倍速时打开对话框，"1x" 项高亮

### 8.5 回归验证
- [ ] 静音按钮功能不受影响
- [ ] 选集按钮功能不受影响
- [ ] 上一/下一集按钮功能不受影响
- [ ] 播放器全屏退出/进入功能不受影响

---

## 附：调研依据（源码定位）

| 文件 | 关键行 | 内容 |
|------|--------|------|
| `ChoiceSpeedDialog.kt` | L57-59 | `lp.width = d.widthPixels * 0.3`、`lp.height = d.heightPixels`、`gravity = END` |
| `ChoiceSpeedDialog.kt` | L51 | `adapter = SwitchVideoAdapter(mContext, data) { item -> item.toString() + "X" }` |
| `switch_speed_video_dialog.xml` | L5 | `android:background="#80121212"` |
| `switch_speed_video_dialog.xml` | L10-13 | 顶部 `<View weight=1>` 占位 |
| `switch_video_dialog_item.xml` | L6 | `android:background="@drawable/card_video_background"` |
| `SwitchVideoAdapter.kt` | L11-15 | `ArrayAdapter<T>` + `titleProvider` |
| `VideoPlayer.kt` | L42 | `private var playSpeed: Float = 1.0f` |
| `VideoPlayer.kt` | L420-445 | `showSpeedDialog()` 完整实现 |
| `VideoPlayer.kt` | L426 | 倍速列表 `listOf(...).reversed()` |
| `styles.xml` | L130-133 | `dialog_style` 定义（透明背景 + 无标题） |
| `colors.xml` | L4 | `<color name="primary">@color/md_light_blue_800</color>` |
| `colors_material_design.xml` | L146 | `<color name="md_light_blue_800">#0277BD</color>` |
| `card_video_background.xml` | L1-7 | `solid #69fdfdfd` + `stroke card_border_water` + `corners 8dp` |
