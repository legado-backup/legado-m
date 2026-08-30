# 错误沉淀机制

> 建立"错误→沉淀→子规范→主规范引用"闭环机制，防止反复犯同类错误。

## 触发场景

- 用户严厉批评的错误
- 浪费用户时间的错误
- 同类错误第2次出现
- 用户明确要求"沉淀到子规范"的错误

## 沉淀流程

```
错误发生 → 分析根因 → 提炼规则 → 写入子规范 → AGENTS.md 引用
```

### Step 1: 错误发生

识别错误类型：
- 代码 Bug（如 MaterialButton 主题不兼容）
- 设计偏差（如 lastHost 只在校验层回填）
- 流程缺失（如测试不勾选 CheckBox 走错路径）
- 规范缺失（如数据库升级未沉淀）

### Step 2: 分析根因

精确到文件+行号：
- 哪个文件？
- 哪个方法？
- 哪行代码？
- 为什么出错？

### Step 3: 提炼规则

将具体错误抽象为通用规则：
- 错误：MaterialButton 需要 Material 主题
- 规则：使用 Material 组件前必须确认项目主题是 Theme.MaterialComponents 后代

### Step 4: 写入子规范

根据错误类型选择子规范：
- 数据库相关 → `database-migration-safety.md`
- 测试相关 → `real-device-test-reuse.md`
- 全局思考 → `global-thinking-checklist.md`
- 通用规则 → 本文件（spec-sedimentation-mechanism.md）

### Step 5: AGENTS.md 引用

在 AGENTS.md 的「子规范加载表」（按任务类型必须加载）中添加引用。

## 沉淀格式

每条沉淀规则必须包含5个要素：

```markdown
### [规则名]

- **场景描述**：什么情况下会犯这个错误
- **强制要求**：必须做什么
- **反面案例**：本次犯的错误（引用 Issue-N）
- **正面做法**：正确的做法
- **何时加载**：触发条件
```

## 本次沉淀的规则清单

### S1: MaterialButton 需要 Material 主题（Issue-2）

- **场景描述**：使用 MaterialButton/MaterialCardView 等 Material 组件
- **强制要求**：使用前必须确认项目主题是 Theme.MaterialComponents 后代，否则改用 AppCompatButton/Button
- **反面案例**：dialog_highlight_rule_edit.xml 用 MaterialButton + Widget.Material3.Button.TextButton 样式，但项目主题是 Theme.AppCompat.DayNight.NoActionBar，导致 4 次 FATAL EXCEPTION
- **正面做法**：4 个布局的 MaterialButton 改为 Button/AppCompatButton，用 ?attr/borderlessButtonStyle 保持视觉一致
- **何时加载**：使用 Material 组件的任务

### S2: 校验必须真正触发功能路径（Issue-7）

- **场景描述**：校验类功能的测试和实现
- **强制要求**：校验必须真正触发 AnalyzeUrl 真实请求路径，不能走 Socket 快速失败路径；权重计算基于关键元素获取程度而非二元判断
- **反面案例**：测试报告说"90ms 优化成功"，但实际是 Socket 快速失败路径，根本没触发 AnalyzeUrl 真实请求模式
- **正面做法**：测试时必须勾选"域名"CheckBox + 选择"解析规则真实请求"模式；权重计算改为基于关键元素获取程度（搜索结果数/详情字段完整度/目录章节数/正文字数）
- **何时加载**：校验类功能实现和测试

### S3: 字段回填必须覆盖使用/调试/校验三层（Issue-8）

- **场景描述**：新增字段的回填点设计
- **强制要求**：新增字段必须在真实使用层（WebBook/Rss）+ 调试层（Debug）+ 校验层（CheckSource）三层都回填
- **反面案例**：lastHost 字段只在校验层回填（3处），缺失真实使用层和调试层，导致字段"有等于没有"
- **正面做法**：三层回填 + 用"变化才写 DB"策略避免性能问题
- **何时加载**：新增字段的任务

### S4: Activity 布局禁止两个 TitleBar 并存（Issue-4）

- **场景描述**：Activity 布局设计
- **强制要求**：一个 Activity 布局只能有一个 TitleBar，否则 onAttachedToWindow 自动调 setSupportActionBar 会导致 ActionBar 状态混乱
- **反面案例**：activity_video_player.xml L16-19/L36-39 存在两个 TitleBar，导致返回按钮不生效
- **正面做法**：只保留一个 TitleBar，用 setNavigationOnClickListener { finish() } 绕过 BaseActivity final 方法拦截
- **何时加载**：Activity 布局设计/修改

### S5: 复杂需求设计方案必须经过3次验证（Issue-14）

- **场景描述**：复杂需求的设计方案审查
- **强制要求**：涉及3+文件改动 / 涉及数据库 / 涉及多场景交互 / 涉及回填点的需求，设计方案必须经过3次验证才能提交检查点1
- **反面案例**：校验逻辑设计偏差、lastHost 设计偏差、单源线程数配置遗漏 UI 入口，都是因为只做一次方案就提交
- **正面做法**：
  1. 第一次验证：方案设计完成后自问"每个修复方案是否可执行？是否有遗漏？"
  2. 第二次验证：对照用户原始反馈逐条核对覆盖情况
  3. 第三次验证：用子代理交叉审查设计文档
- **何时加载**：复杂需求设计阶段

## 沉淀触发条件

遇到以下情况必须触发沉淀流程：

1. 用户说"你又犯了这个错误"——同类错误第2次出现
2. 用户说"这个问题之前也遇到过"——历史教训未沉淀
3. 用户说"你应该沉淀到子规范"——明确要求沉淀
4. 用户严厉批评的错误——浪费用户时间
5. 测试发现设计文档未覆盖的问题——设计偏差

## 反模式

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| 错误只在对话中反思 | 新对话无法加载教训 | 写入子规范+AGENTS.md 引用 |
| project_memory 记录但不结构化 | 无法按场景加载 | 结构化为子规范+触发条件 |
| 沉淀后不在 AGENTS.md 引用 | AI 不知道有这个规范 | AGENTS.md 引用+触发条件 |
| 同类错误第2次出现未沉淀 | 第3次还会犯 | 第2次出现立即沉淀 |

## 何时必须加载本规范

- 错误发生后的沉淀流程
- 复杂需求设计阶段（3次验证）
- 新对话开始时检查是否有未沉淀的错误
