# Design：修复高亮规则开关切换不即时刷新

## Technical Approach

修复点为 `HighlightRuleActivity.kt` `onEnableToggle` 回调（L58-61）：

```kotlin
// 修复前：原地修改同一实例 → 强跳过按引用比较 → 行被跳过重组
onEnableToggle = { rule, enabled ->
    rule.enabled = enabled
    viewModel.update(rule)
},
// 修复后：copy 创建新实例 → 引用变化 → 行重组（对齐全项目 28 处先例）
onEnableToggle = { rule, enabled ->
    viewModel.update(rule.copy(enabled = enabled))
},
```

完整链路（修复后）：Checkbox 点击 → copy 新实例 → `viewModel.update()` 从 Store load 列表、按 id upsert（新实例替换）、save 持久化 → `postValue` → `composeRules`（mutableStateOf）更新 → `filtered` 重算（rules key 变化）→ `HighlightRuleItem` 收到**不同引用** → 强跳过判定参数已变 → 行重组 → Checkbox 重绘。

## Architecture Decisions

### AD-01: 以 copy（不可变更新）根治重组失效，不做 key 层 workaround
- **Context**: Kotlin 2.3.10 + Compose 强跳过模式（2.0.20+ 默认开启），unstable 类型参数按引用相等比较；项目内 `HighlightRule` 为 var 字段类（unstable），列表项 `HighlightRuleItem` 可被跳过
- **Concern**: 原地修改数据对象后同实例回流列表，Compose 判定"输入未变"跳过重组，UI 显示过期状态
- **Decision**: 回调处 `rule.copy(enabled = enabled)`，以新实例触发重组；不在 items key/contentType 层做 workaround
- **Goal**: 开关即时生效，且与全项目 Compose 列表页既有 copy 模式统一，消除特例
- **Tradeoff**: 每次 toggle 多一次对象拷贝（微秒级，规则量级 ≤ 百条，可忽略）；`HighlightRule` 保持 var（unstable）不变，依赖规范防线防复发
- **Status**: Accepted

### AD-02: 防线建立在规范层而非数据类层
- **Context**: 全量审计确认现存 Compose 列表页仅此一处反模式，其余 28 处均为 copy 模式；改 val 需重写编辑弹窗链路
- **Concern**: 如何"全面杜绝"复发，而不仅是点状修复
- **Decision**: `frontend-ui-standards.md` 补三条：§4 红线（Compose 列表状态禁止原地修改后回流）、§5 门禁清单项（新页面自查）、§6 已知坑（强跳过引用比较陷阱）
- **Goal**: 后续任何 Compose 列表页开发/审查时按门禁拦截该反模式
- **Tradeoff**: 规范约束依赖执行者自觉遵守（有门禁清单 + skill 引用兜底），非编译期强制
- **Status**: Accepted

## Data Flow

```
用户点击 Checkbox
  → onEnableToggle(rule, enabled)          [Activity 回调]
  → rule.copy(enabled = enabled)           [新实例，引用不同]
  → viewModel.update(newRule)
      → HighlightRuleStore.load()          [SharedPreferences 反序列化]
      → upsert by id + save                [持久化]
      → postValue(list)                    [含新实例]
  → Activity.observeData: composeRules = list   [mutableStateOf 触发重组]
  → HighlightRuleScreen.filtered 重算
  → HighlightRuleItem(rule=新实例) → 重组 → Checkbox 重绘 ✅
  → ReadBook.upHighlightRules()            [阅读器即时生效，不变]
```

## File Changes

| 文件 | 变更 | 类型 |
|------|------|------|
| `app/src/main/java/io/legado/app/ui/highlight/HighlightRuleActivity.kt` | L58-61 `onEnableToggle` 原地修改 → copy | 修复 |
| `docs/project-rules/frontend-ui-standards.md` | §4 新增红线 5 / §5 新增清单项 / §6 新增已知坑 | 规范补齐 |
| `app/src/main/assets/updateLog.md` | 追加用户可感知修复条目（编译前） | 交付同步 |
