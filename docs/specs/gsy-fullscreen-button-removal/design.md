# Design：GSY 全屏按钮去重

## Technical Approach

在 GSY 视频播放器的竖屏控制器布局 `video_layout_controller.xml` 中，将 fullscreen ImageView 的 visibility 设为 gone。GSY 基类通过 `findViewById(R.id.fullscreen)` 获取按钮引用的代码不受影响（view 仍存在于布局中，只是不可见），click listener 设置安全（设到 gone view 上不会崩溃，只是永不触发）。

## Architecture Decisions

### ADR-1：选择 visibility=gone 而非删除元素

**Context**：需要移除 GSY 内置全屏按钮，GSY 基类源码不在项目控制范围内。

**Decision**：使用 `android:visibility="gone"` 而非删除 XML 元素。

**Y-Statement**：In the context of GSY 全屏按钮去重，facing GSY 基类通过 findViewById 引用按钮的约束，we decided to 使用 visibility=gone 而非删除元素，accepting view 对象仍占用少量内存的 tradeoff，to achieve 安全移除按钮且不引入 NPE 风险，resolving GSY 基类 findViewById 可能返回 null 的问题，because GSY 是第三方库，删除元素导致的 NPE 难以排查且影响面大。

**Consequences**：
- 正面：最小改动、零风险、GSY 基类代码无需修改
- 负面：click listener 仍设置但永不触发（可接受的开销）

## Data Flow

```
用户进入视频播放器
  → GSY VideoPlayer 初始化
    → init() 调用 findViewById(R.id.fullscreen) 获取引用（view 存在，visibility=gone）
    → VideoPlayerActivity.kt:900 设置 fullscreenButton.setOnClickListener（安全，永不触发）
  → 用户点击屏幕显示控件
    → GSY 底部控制栏显示（fullscreen 按钮不可见，其他按钮正常）
  → 用户点击自定义 btn_fullscreen
    → toggleFullScreen() 执行
    → 进入全屏模式
```

## File Changes

### 1. `app/src/main/res/layout/video_layout_controller.xml`

**修改位置**：L102-108

**修改前**：
```xml
<ImageView
    android:id="@+id/fullscreen"
    android:layout_width="wrap_content"
    android:layout_height="fill_parent"
    android:padding="16dp"
    android:scaleType="center"
    android:src="@drawable/video_enlarge" />
```

**修改后**：
```xml
<ImageView
    android:id="@+id/fullscreen"
    android:layout_width="wrap_content"
    android:layout_height="fill_parent"
    android:padding="16dp"
    android:scaleType="center"
    android:src="@drawable/video_enlarge"
    android:visibility="gone" />
```

### 2. `app/src/main/assets/updateLog.md`

追加 2026/07/12 变更说明。

## 验证计划

1. **编译验证**：`.\gradlew.bat assembleDebug` BUILD SUCCESSFUL
2. **L1 验证**：App 启动无崩溃
3. **L2 验证**：
   - 导航到视频播放器
   - GSY 底部控制栏右下角无全屏按钮
   - 自定义 btn_fullscreen 功能正常
   - 系统返回键退出全屏功能正常
   - 无崩溃日志
