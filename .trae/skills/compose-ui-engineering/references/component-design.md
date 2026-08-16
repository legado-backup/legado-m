# Compose 可复用组件设计（Component Contract）

> 提炼自 chrisbanes/skills `compose-component-design`。核心：**组件拥有不变结构，调用者拥有放置（modifier）、内容（slot）、策略选择。**

## 核心原则

可复用 Compose 组件描述布局结构，调用者通过槽位（slot）提供可变视觉内容。组件根接受调用者 `modifier`。

## API 评审流程

1. 确认组件确实可复用（真正单次使用的组件不添加 slot 仪式）。
2. 标记哪些区域由调用者变化：headline / supporting / leading / trailing / actions / body。
3. 把调用者控制的、无约束的 primitive 内容参数和形状 flag **替换为 slot**；保留有意强制语义/设计系统/受限类型/测量快路径的 primitive 参数。
4. slot 落在 Row/Column/Box 内时，加对应 scope receiver（`RowScope.() -> Unit` 等）。
5. 可选区域用 nullable（`null` 默认），组件据此省略容器和间距。
6. 重复的默认内容/标记放 `XxxDefaults` 对象。
7. 与 modifier 规则配合（组件根必须接受 modifier）。

## 1. primitive 内容 → @Composable slot

```kotlin
// ❌ BAD — primitive 参数；只有 trailing 是 slot，其余锁死
@Composable
fun SettingsRow(
    title: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    leadingIcon: ImageVector? = null,
    trailing: (@Composable () -> Unit)? = null,
) { ... }

// ✅ GOOD — 每个视觉区域都是 slot；行只描述结构
@Composable
fun SettingsRow(
    headlineContent: @Composable () -> Unit,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    supportingContent: (@Composable () -> Unit)? = null,
    leadingContent: (@Composable () -> Unit)? = null,
    trailingContent: (@Composable () -> Unit)? = null,
) { ... }
```

调用点保持简短：`SettingsRow(headlineContent = { Text("Account") }, leadingContent = { Icon(...) }, trailingContent = { SettingsRowDefaults.Chevron() })`。

**Slot 命名**：自由表单用 `xxxContent`（`headlineContent`/`trailingContent`，对齐 M3）；语义受限且组件名消歧义的用单数名词（`Scaffold(topBar=, bottomBar=, floatingActionButton=)`）。不要同时用 `content` 和其它 `xxxContent`。

## 2. 落在布局内时加 scope receiver

```kotlin
// ❌ actions 渲染在 Row 内，但调用者拿不到 RowScope.weight()
@Composable
fun MyTopBar(title: @Composable () -> Unit, actions: @Composable () -> Unit = {})

// ✅ 调用者获得 RowScope
@Composable
fun MyTopBar(title: @Composable () -> Unit, actions: @Composable RowScope.() -> Unit = {})
```

receiver 必须匹配 slot 实际落进的父布局：Row→RowScope、Column→ColumnScope、Box→BoxScope。不匹配就别硬加。

## 3. 可选 slot：nullable + null 默认

```kotlin
// ❌ 空 lambda 默认 → 缺席时布局仍分配空间
leadingContent: @Composable () -> Unit = {}

// ✅ null = "无此区域"，组件可跳过容器/间距/内边距
leadingContent: (@Composable () -> Unit)? = null
```

## 4. 默认内容进 XxxDefaults

```kotlin
object SettingsRowDefaults {
    @Composable
    fun Chevron() = Icon(
        imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
        contentDescription = null,
    )
    @Composable
    fun TrailingValue(text: String) = Text(
        text = text,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}
```

可组合的默认内容属于 XxxDefaults，不要内联展开成新参数默认值。

## 不适用场景（不要为这些加 slot）

- **真正单次使用**的组件（复用出现后立即 slot 化）。
- **设计系统原语**要求每个调用者完全一致（`Heading2(text: String)` 故意 primitive 才能强制统一）。
- **组件有意拥有的语义参数**（排版/图标/无障碍文案/产品一致性）。
- **受限类型**（`Switch(checked, onCheckedChange)`——布尔+回调不是"内容"）。
- **性能热路径**（最深 LazyList item 层，slot 是分配的 lambda）。App 代码一般不适用。

## 审查红旗

| 想法 | 现实 |
|------|------|
| "标题永远是 String，slot 是过度设计" | "今天永远是"是陷阱；M3 ListItem.headlineContent 存在正是因为明天要 Text+Badge |
| "lambda 比 string 重" | 常规 UI 不可测量；框架组件全 slot 化 |
| "以后有人要再加 slot" | 加 slot 要改所有调用点，不是"以后"改 |
| "用 sealed Trailing 类型建模变体" | sealed 有界，slot 无界；新变体又要改组件 |
| "leading 永远是 icon，只 slot trailing" | 部分 slot 陷阱；第一次需要头像/旗标就破功 |
| "今天只有一个调用点" | 还没到设计可复用组件的时机，primitive 即可；一旦复制就 slot 化 |

## Legado 适配

- 组件库目录：`app/src/main/java/io/legado/app/ui/widget/components/`（SettingsRow/SettingsCard/SettingsSection 等 32 文件）。
- 新组件必须 camelCase+用途前缀+KDoc 设计来源（AD-xx 或 fork 来源）+ 登记 `ui-standards.md` §3 组件目录；先入 §3.4 真值表再写代码。
- 已有组件与真值表不符即违例（🔴），参照规格修正。
