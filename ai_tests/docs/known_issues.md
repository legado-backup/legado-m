# 已知问题与陷阱库

> 由 M16 反馈闭环自动追加，AI 审阅后补充规避方式。
>
> **文件性质**：持续迭代层文件，AI 可直接编辑。M16 `feedback_loop.py` 运行时以追加模式（`"a"`）向本文件末尾追加新陷阱块，初始模板内容会被保留。

## 分类

- **环境类**：模拟器、ADB、uiautomator2、atx-agent 等测试环境基础设施问题
- **兼容类**：APK 版本、Android 版本、设备分辨率等兼容性问题
- **源码类**：Legado 源码本身的 Bug 或行为变更导致的测试失败
- **规则类**：测试规则引擎（CRASH_PATTERNS、source_map.json、case_parser）配置不当或过期
- **提示词类**：AI 提示词模板（ai_prompt_template.j2）调优不足导致 manual 用例过多

## 陷阱库沉淀流程（任务 20.3）

```
M16 feedback_loop.py process(report)
    → _suggest_known_issue() 输出 known_issue_suggestions
    → _append_known_issue() 以追加模式写入本文件
    → AI 审阅末尾新增的陷阱块
    → AI 补充「规避方式」字段（M16 追加的块中 workaround 为"待 AI 审阅补充"）
    → 必要时同步更新 config.CRASH_PATTERNS 或 ai_prompt_template.j2
```

**M16 追加的陷阱块格式**（与本文件现有格式一致）：

```
### [{tc_id}] {title}
- **分类**：{category}
- **场景描述**：{scenario}
- **根因**：{root_cause}
- **规避方式**：{workaround}
- **关联 TC-ID**：{tc_id}
- **verdict**：{verdict}
```

## 陷阱列表

### [已知-001] MEmu 启动慢

- **分类**：环境类
- **场景描述**：首次启动 MEmu 模拟器耗时 >60s，偶发超时导致测试初始化失败
- **根因**：MEmu 冷启动需加载虚拟机镜像，首次启动无缓存；`config.TIMEOUT_MEMU_START = 60` 在低端机上不足
- **规避方式**：调大 `TIMEOUT_MEMU_START`（如改为 90 或 120）；超时后重试一次（run_e2e.py 可加重试逻辑）；建议测试前手动启动 MEmu 预热
- **关联 TC-ID**：未知（影响所有用例的初始化阶段）
- **verdict**：已知

### [已知-002] atx-agent 卡死

- **分类**：环境类
- **场景描述**：uiautomator2 的 atx-agent 偶发卡死，导致 UI 操作（click/wait_element）无响应，用例超时失败
- **根因**：atx-agent 是设备端常驻进程，长时间运行后偶发死锁；与 MEmu 的 ADB 桥接稳定性相关
- **规避方式**：重启 atx-agent（`python -m uiautomator2 stop` 后重新 `init`）；若频繁卡死则重装 atx-agent（`python -m uiautomator2 uninstall` + `init`）；测试用例对 UI 操作设置合理超时（`TIMEOUT_UI_OPERATION = 30`）
- **关联 TC-ID**：未知（影响所有 UI 交互用例）
- **verdict**：已知

### [已知-003] run-at 不可用

- **分类**：环境类
- **场景描述**：执行 `python -m uiautomator2 init` 偶发 `run-at` 命令不可用错误，atx-agent 安装失败
- **根因**：uiautomator2 版本与设备 Android 版本不匹配；MEmu 的 `run-at` 工具链偶发缺失
- **规避方式**：手动 `adb push atx-agent` 到 `/data/local/tmp/` 并赋权；降级使用 adb shell `am instrument` 方式；锁定 uiautomator2 版本（避免自动升级）
- **关联 TC-ID**：未知（影响设备初始化）
- **verdict**：已知

### [已知-004] Web API 8080 未启动

- **分类**：环境类
- **场景描述**：Legado 调试 Web API（端口 8080）未启动，导致 `web_api` 类证据收集失败，M5 证据收集器报错
- **根因**：DebugToolsActivity 中的 Web 服务开关未开启；或 debug 构建未启用 Web API 功能；端口被占用
- **规避方式**：确保 DebugToolsActivity 中 Web 服务已开启（手动进入调试工具页打开开关）；检查 8080 端口占用（`adb shell netstat -tuln | grep 8080`）；测试用例对 `web_api` 证据设置容错降级（缺失时降级为 `logcat` 证据）
- **关联 TC-ID**：未知（影响所有需 web_api 证据的用例）
- **verdict**：已知

### [已知-005] source_map.json 过期

- **分类**：规则类
- **场景描述**：新增 Activity 后未更新 `source_map.json`，导致 M8 影响分析遗漏新 Activity 的关联用例，`recommended_rerun` 不完整
- **根因**：`source_map.json` 是快照式产物，`build_source_map()` 仅在 `--update-source-map` 或文件缺失时重建；新增 Activity 后未触发重建
- **规避方式**：代码变更后运行 `python ai_tests/run_e2e.py --update-source-map` 重建；在 CI 流水线中 `git diff` 检测到 `app/src/main/java/io/legado/app/` 下文件变更时自动触发重建；详见 `ai_tests/docs/source_impact_guide.md`
- **关联 TC-ID**：未知（影响 M8 影响分析准确性）
- **verdict**：已知

### [已知-006] uiautomator2 框架崩溃误判为 App 崩溃

- **分类**：规则类
- **场景描述**：测试运行中 uiautomator2 框架崩溃（`UiAutomationService already registered!`），其 FATAL EXCEPTION 日志被 `CRASH_PATTERNS["FATAL"]` 匹配，M6 规则分析器误判为 App 崩溃，verdict=fail
- **根因**：`CRASH_PATTERNS["FATAL"]` 中 `FATAL EXCEPTION` 正则逐行匹配 logcat，不区分崩溃进程来源；uiautomator2 框架崩溃堆栈包含 `com.android.commands.uiautomator.DumpCommand`，属于测试框架而非被测 App
- **规避方式**：evidence_collector.py 新增 `UIAUTOMATOR2_CRASH_MARKERS` 常量和 `_is_uiautomator2_crash` 方法，在 `extract_anomalies` 匹配到崩溃时检查后续 15 行滑动窗口是否包含 uiautomator2 框架标识（com.android.commands.uiautomator / com.android.uiautomator.core / UiAutomationService），是则排除；详见 `ai_tests/lib/evidence_collector.py`
- **关联 TC-ID**：TC-F-P0-1-01（第七次测试首次出现）
- **verdict**：已修复

### [已知-007] swipe_ext 在 MEmu 上触发 SecurityException 和页面回退

- **分类**：环境类
- **场景描述**：`_scroll_find` 使用 uiautomator2 的 `swipe_ext("up")` 滚动查找元素时，在 MEmu 上触发 `SecurityException: Injecting to another application requires INJECT_EVENTS permission`，或被系统解释为手势导航导致页面回退（ConfigActivity → MainActivity）
- **根因**：`swipe_ext` 通过 uiautomator2 框架注入输入事件，在 MEmu 上可能被拒绝（INJECT_EVENTS 权限不足）或被系统手势导航拦截；同时 MEmu UI 不稳定（`Could not detect idle state`）导致 `waitForExists` 不稳定
- **规避方式**：改用 `self.d.shell(f"input swipe {x1} {y1} {x2} {y2} 300")` ADB input swipe 命令，直接通过 InputManager 注入，不经过 uiautomator2 框架；基于 `window_size()` 动态计算坐标适配不同分辨率；详见 `ai_tests/lib/ui_executor.py` `_scroll_find` 方法
- **关联 TC-ID**：TC-F-P0-1-01（步骤3"调试工具"scroll_find）
- **verdict**：已修复

### [已知-008] 测试用例与 Compose UI 不匹配

- **分类**：源码类
- **场景描述**：测试用例 TC-F-P0-1-01 步骤6"点击 Base64"找不到元素，scroll_find 5 次未找到，步骤失败
- **根因**：测试用例基于旧 RadioButton UI 设计假设编写，但 EncodeToolsScreen 实际使用 Jetpack Compose `ExposedDropdownMenuBox` 选择编码类型；"Base64 编码"是 `OutlinedTextField` 的 value（readOnly，不可点击），不是独立的 RadioButton；且 `currentType=0` 即 Base64 编码为默认选中，无需显式选择
- **规避方式**：测试用例编写前必须核对实际 App 源码 UI 实现（EncodeToolsScreen.kt 等 Compose Screen 文件），不能基于旧 UI 设计假设；对于 Compose `ExposedDropdownMenuBox`/`Spinner` 类组件，若目标选项是默认选中（`currentType=0`），应省略"点击选择"步骤；详见 `docs/tests/F-P0-1-debug-tools.md` TC-F-P0-1-01 步骤说明注释
- **关联 TC-ID**：TC-F-P0-1-01
- **verdict**：已修复

### [已知-009] 验证空炮（模拟器全新安装）

- **分类**：环境类
- **场景描述**：全新安装/重置后的模拟器读不到旧版本写入的脏数据（缓存/prefs/DB），"验证通过"可能是空炮——崩溃复现类验证在干净环境无法复现问题，得出虚假通过结论
- **根因**：全新安装模拟器数据状态干净，与用户真实场景（带脏缓存/旧 prefs/旧 DB）不一致；铁证：config-needs-restart-fix 发现页崩溃在全新安装模拟器无法复现，真机有脏缓存才崩
- **规避方式**：崩溃复现必须先构造用户数据状态（回灌旧版本脏缓存/prefs/DB 后再验证）；复现类问题先确认模拟器数据状态是否贴近用户真实场景，再判定"验证通过"是否有效
- **关联 TC-ID**：未知（影响所有复现类验证）
- **verdict**：已知
