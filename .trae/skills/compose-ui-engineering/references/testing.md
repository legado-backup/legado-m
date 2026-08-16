# Compose UI 测试与真机验证（UI Testing & Real-Device Verification）

> 核心：**测最小 UI 契约**。plain state composable + 回调捕获，不构造整个 ViewModel/组件图。真机功能点覆盖是 Legado 实施门禁（FR-11）。

## 本地 UI 测试（单元层）

测最小契约：plain state composable + 回调捕获，不构造 ViewModel/仓库/导航。

| 断言目标 | 做法 |
|----------|------|
| 文字存在/按钮使能 | semantics：`onNodeWithText("...")` / `assertIsEnabled()` |
| 点击回调接线 | 捕获变量断言（`onClick` 调用后 flag 置真） |
| 布局/间距/颜色/图片 | screenshot test（固定数据、冻结时钟、fake 图片加载器） |
| hover/press/focus 态 | 注入 `MutableInteractionSource` 并 `emit`，不用鼠标/触摸模拟 |
| 语义 vs test tag | 语义断言优先；test tag 只用于无稳定文字节点 |

```kotlin
// 测 plain UI（不含 VM）
@Composable
fun Greeting(state: GreetingUiState, onDismiss: () -> Unit, modifier: Modifier = Modifier) {
    Text(state.title, modifier = modifier.testTag("title"))
    Button(onClick = onDismiss) { Text("关闭") }
}

@Test
fun click_dismiss_callback() {
    var dismissed = false
    composeTestRule.setContent {
        Greeting(GreetingUiState("标题"), onDismiss = { dismissed = true })
    }
    composeTestRule.onNodeWithText("关闭").performClick()
    assertTrue(dismissed)
}
```

### 项目适配（本地测试现状）

- `./gradlew test`（JVM 单元测试）。注意：gradle **勿 `--offline`、需 `--no-parallel`**；全量单测 175 tests / 5 failures（AnalyzeRuleTest JVM 环境既有失败，非 UI 回归）。
- 纯 Compose UI 目前主要靠**真机功能点覆盖**（下述），本地 UI 测试按需补。

## 真机功能点覆盖（FR-11 门禁 · 强制）

> 每个 Compose 化页面交付前，必须真机验证功能点，SOP 见 `ai_tests/docs/fixed_test_workflow.md`。

### 环境硬约束

- **必须用** `ai_tests\venv\Scripts\python.exe`（**禁止公共 Python**）。
- MEmu 模拟器（需管理员权限启动，`memuc.exe` 报 requires elevation 时用提升 shell）；测试包 `io.legado.miss.app.debug`（真机测试固定用测试包，见 docs/project-rules/package-naming.md）。
- **禁止同一模拟器实例同时操作多个包**（Activity 抢占）。
- **禁止在 `temp/` 创建临时测试脚本**。

### 固定脚本入口（优先复用，勿重复造轮子）

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/quick_build_install.py` | 编译+安装+L1 |
| `ai_tests/scripts/import_rss_source.py` | 导入订阅源 |
| `ai_tests/scripts/l2_verify_video_player.py` | 视频播放器 L2 |
| `ai_tests/scripts/swipe_test_log.py` | 滑动测试日志 |
| `python ai_tests/run_e2e.py --tc all` | 全量用例 |

### 真机断言技巧（AOAdapt）

- uiautomator2 元素 `.bounds()` 是**方法**不是属性。
- switch 需点**中心坐标**。
- 验证布局闪变/骨架屏：肉眼+截图对比（如 V-4 书架 loading）。

## 审查红旗

- 测试构造整个 ViewModel/组件图（耦合重、脆）。
- 用鼠标/触摸模拟代替 InteractionSource 注入。
- 交付前跳过真机功能点覆盖（FR-11）。
- 用公共 Python 跑 ai_tests（会破坏 venv 约定）。
