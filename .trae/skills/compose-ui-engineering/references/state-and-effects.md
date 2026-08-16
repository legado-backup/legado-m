# Compose 状态与副作用（State & Effects）

> 提炼自 chrisbanes/skills `compose-state-and-effects`，适配 Legado 项目。核心：**每个 state 一个最低必要 owner，每个 effect 有正当生命周期与 key。**

## 状态归属决策

### 本地 state

| 情境 | 方案 |
|------|------|
| 单个 composable 读写简单 UI 状态 | `var x by remember { mutableStateOf(0) }` |
| 集合变更 | `remember { mutableStateListOf() }` / `mutableStateMapOf()`（`.add()` 可触发重组） |
| 进程/Activity 重建后应保留 | `rememberSaveable` 或自定义 Saver（只存可序列化值，不存 LazyListState/FocusRequester/协程作用域） |

两个条件缺一不可：`remember{}` 保证存活重组，`mutableStateOf()` 保证写入触发重组。`remember { mutableStateOf(mutableListOf()) }` 后 `.add()` **不会**重组。

### 提升（hoisting）

兄弟或父级需要读某 state → 提升到最低公共祖先。只提升到真正需要读写的层级，不要"以防万一"全部提升。

### Plain state holder

多个关联 `remember` 由同一组回调协调、有具名操作（`clear()`/`submit()`/`jumpToTop()`）、派生 flag 散落时，抽一个 `@Stable class XxxState` + `@Composable fun rememberXxxState()`。**一个 boolean / 一个文本框 / 简单显隐不要抽**——仪式感不是职责分离。

```kotlin
@Stable
class ProductSearchState(
    query: String,
    private val listState: LazyListState,
) {
    var query by mutableStateOf(query)
        private set
    var filtersOpen by mutableStateOf(false)
        private set
    val canClear: Boolean get() = query.isNotEmpty()

    fun updateQuery(value: String) { query = value }
    fun clear() { query = "" }
    suspend fun jumpToTop() = listState.animateScrollToItem(0)
}
```

注意：需要帧时钟的挂起 UI 操作（scroll/drawer 动画）必须在组合作用域协程（`rememberCoroutineScope`/`LaunchedEffect`）执行，**不要移到 viewModelScope**。

### 屏幕边界拆分（state-holder vs plain UI）

屏幕取 ViewModel/组件收集状态时，拆两层：

```kotlin
@Composable
fun ProfileScreen(component: ProfileComponent, modifier: Modifier = Modifier) {
    val state by component.state.collectAsStateWithLifecycle()
    ProfileScreen(
        state = state,
        onNameChange = component::onNameChange,
        onSaveClick = component::save,
        onBackClick = component::back,
        modifier = modifier,
    )
}

@Composable
fun ProfileScreen(
    state: ProfileUiState,
    onNameChange: (String) -> Unit,
    onSaveClick: () -> Unit,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // 纯布局
}
```

| 关注点 | state-holder composable | plain UI composable |
|--------|------------------------|---------------------|
| 收集业务状态/一次性 effect | 是 | 否 |
| 持有 DI 对象 | 是 | 否 |
| 接受不可变 UI state + 事件回调 | 转发 | 是 |
| 拥有布局/modifier/semantics/test tag | 否/最少 | 是 |
| 拥有 Compose 运行时对象（LazyListState 等） | 否 | 是 |

**Legado 适配**：本项目用 Fragment 做壳（XML 壳 + ComposeView 桥接）+ ViewModel。业务状态在 ViewModel+Room Flow，`collectAsStateWithLifecycle()` 收集后传给 plain UI composable。异步用 `Coroutine.async{}.onSuccess{}.onError{}` 链。

不要给每个小组件都拆两层。屏幕或内聚区域边界才拆，且前提是"去掉应用依赖后 UI 仍值得 preview/test"。

## Effect 选择表

| 需求 | API | 示例场景 |
|------|-----|----------|
| 每次成功重组后发布 state | `SideEffect` | 把 Compose 值同步给非 Compose 代码 |
| 注册/注销 | `DisposableEffect(keys...)` | 生命周期观察者、资源，必须 onDispose 清理 |
| 挂起/一次性/keyed 工作 | `LaunchedEffect(keys...)` | Flow 收集、延迟、预加载 |
| 事件回调里启动挂起 | `rememberCoroutineScope()` | 点击 → snackbar/滚动 |
| 快照读→Flow | `snapshotFlow{}`（LaunchedEffect 内） | firstVisibleItemIndex → analytics |

## Key 规则

- key = effect 跟随的生命周期对象：`userId`、`screenId`、`lifecycleOwner`、`focusRequester`。
- 不用宽泛对象（`state`、`viewModel`）当 key——只用一个属性时用该属性。
- 不用变化的 lambda 当 key（除非真想每次重启）。
- 禁止 `LaunchedEffect(Unit)` 掩盖变化的输入。

## 陈旧捕获（stale capture）

长生命周期 effect 不应重启但需要最新回调/值时用 `rememberUpdatedState`：

```kotlin
val latestOnTimeout by rememberUpdatedState(onTimeout)
LaunchedEffect(Unit) {
    delay(1_000)
    latestOnTimeout()  // 总是最新
}
```

**陷阱**：`rememberUpdatedState` 的 delegate 在 `remember {}` 块内**急切读取**会快照初始值永不刷新。应改为把变化值当 `remember` 的 key，或包一层 lambda 延迟读取。

**不要**用 rememberUpdatedState 逃避选 key——值变了应重启的工作就把它当 key。

## Flow 收集

- **event/side-effect flow**（snackbar/导航/analytics/焦点命令）：`LaunchedEffect(events) { events.collect { ... } }`。
- **UI 渲染 state**：在 state holder 附近 `collectAsStateWithLifecycle()`，传 plain 值给 UI。
- `snapshotFlow { ... }.map{...}` 没有终结 `collect` 等于没做。
- Android 优先生命周期感知收集。

## 用户事件

点击/手势启动挂起工作 → `rememberCoroutineScope().launch { ... }`。**禁止 event flag 反模式**：`shouldShowSnackbar = true` 再触发 LaunchedEffect 是错的，点击本身就是事件。

## 注册与清理

`DisposableEffect(owner, observer) { register(); onDispose { unregister() } }`——每一条注册路径都有匹配的 onDispose。

## 常见错误（RED 检查点）

| 错误 | 修正 |
|------|------|
| 网络请求在组合体 | 移到 ViewModel；UI 拥有的 keyed 工作才 LaunchedEffect |
| analytics/埋点写在组合体 | SideEffect（每重组发布）或 LaunchedEffect(key)（按 key 一次） |
| LaunchedEffect(Unit) 捕获变化 id | key 用 id，或 rememberUpdatedState |
| rememberUpdatedState 在 remember{} 内急切读 | 当 remember key |
| LaunchedEffect(state){...} 重启过频 | 用具体属性当 key |
| 点击置 flag 触发 effect | rememberCoroutineScope 直接调 |
| 组合体内读 focus 做副作用 | LaunchedEffect(focused) / snapshotFlow |
| onSizeChanged 写 state 且兄弟在组合读它 | 兄弟必须在 measure 阶段消费，不组合读 |

## 审查红旗

- "这个只运行一次"——组合体里的代码。
- 带变化参数却 `LaunchedEffect(Unit)`。
- effect 内 Flow 链无终结 collect。
- key 为了压 lint 而非建模生命周期。
- rememberUpdatedState 在 remember{} 急切读。
