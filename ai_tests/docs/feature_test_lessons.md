# 功能测试经验沉淀：rss-concurrency-and-checksource-optimization

> **创建时间**：2026-07-15
> **关联任务**：rss-concurrency-and-checksource-optimization 真机测试
> **测试脚本**：ai_tests/scripts/verify_all_features.py
> **测试结果**：6 PASS / 0 SKIP / 0 FAIL

## 1. 测试Bug修复经验

### 1.1 Python `or`运算符陷阱（UiObject总是truthy）

**问题**：`d(textContains="默认") or d(textContains="导入")` 总是返回第一个UiObject，因为UiObject总是truthy（无论exists与否）。

**修复**：改为 `if not exists:` 链式判断
```python
import_item = d(textContains="默认")
if not import_item.exists:
    import_item = d(textContains="导入")
```

**教训**：uiautomator2的UiObject是惰性对象，`.exists` 才能判断是否存在，不能用Python `or` 做选择。

### 1.2 模拟器英文环境需用英文关键词搜索UI

**问题**：测试脚本搜索中文"解析并发"，但MEmu模拟器使用英文环境，UI显示"RSS parse concurrency"。

**修复**：搜索关键词列表加入英文
```python
found = scroll_and_find(d, "01_other_config",
    ["RSS parse concurrency", "Image load concurrency", "解析并发", "图片并发"],
    max_scrolls=15)
```

**教训**：strings.xml中values/是英文默认值，values-zh/是中文。模拟器/真机语言环境决定显示哪种。测试脚本必须同时支持中英文关键词。

### 1.3 domainCheckMode RadioGroup需勾选"域名"CheckBox才显示

**问题**：点击"校验设置"后dump XML，未找到domainCheckMode相关UI文本。

**根因**：`dialog_check_source_config.xml`的`domain_check_mode_group` RadioGroup默认`android:visibility="gone"`，必须先勾选"域名"CheckBox（resource-id=`check_domain`）才会变为VISIBLE。

**修复**：测试脚本中点击"校验设置"后，先勾选"域名"CheckBox，再dump XML验证RadioGroup显示。

**教训**：UI元素的visibility可能是动态控制的，测试前需理解UI交互逻辑（CheckSourceConfig.kt L46-47控制visibility）。

### 1.4 书源菜单无"导入默认规则"项（只有订阅源有）

**问题**：测试脚本尝试在书源管理菜单找"导入默认规则"项导入默认书源，但菜单中没有此项。

**根因**：
- BookSourceActivity.kt使用`R.menu.book_source`，该菜单文件没有"导入默认规则"项
- 对比：RssSourceActivity.kt有`menu_import_default -> viewModel.importDefault()`
- DefaultData.kt只有`importDefaultRssSources()`，没有`importDefaultBookSources()`

**教训**：书源和订阅源的功能不对等，测试前需确认功能差异。

### 1.5 MEmu设备无sqlite3，需pull DB到本地查询

**问题**：通过`run-as io.legado.app.debug sqlite3`或`su -c sqlite3`查询数据库都失败，提示`sqlite3: not found`。

**修复**：用ADB pull DB到本地，用Python sqlite3查询
```python
# 用 su -c cp 复制到 /sdcard/（绕过权限）
for src, dst in [(db_remote, db_sdcard), (wal_remote, wal_sdcard), (shm_remote, shm_sdcard)]:
    run_adb(["shell", f"su -c 'cp {src} {dst}' 2>/dev/null"], timeout=15)
# 用 adb pull 拉取
sp.run([ADB, "-s", DEVICE_SERIAL, "pull", sdcard_path, local_path], ...)
# 用Python sqlite3查询
conn = sqlite3.connect(str(db_local))
cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # 合并WAL
```

**教训**：MEmu模拟器的`/system/bin`目录下没有sqlite3二进制。必须pull DB到本地用Python查询，且要处理WAL/SHM文件。

### 1.6 UI resource-id命名规则

**问题**：脚本用`recyclerView`（驼峰），实际UI resource-id是`recycler_view`（下划线）。

**修复**：`d(resourceId=f"{PKG}:id/recycler_view")`

**教训**：legado app使用下划线命名（`recycler_view`、`cb_selected_all`），不是驼峰命名。测试前用dump_hierarchy确认实际resource-id。

### 1.7 DB表名规则（Room实体驼峰命名）

**问题**：SQL查询`rss_sources`报`no such table`。

**根因**：Room实体使用驼峰命名`@Entity(tableName = "rssSources")`，不是下划线。

**修复**：`SELECT COUNT(*) FROM rssSources`

**教训**：Room实体的tableName属性决定DB表名，需查实体类确认（RssSource.kt L: `@Entity(tableName = "rssSources")`）。

### 1.8 菜单导航方式（底部操作栏vs右上角三点）

**问题**：选择模式下点击右上角三点菜单无效。

**根因**：选择模式后应点底部`select_action_bar`内的`iv_menu_more`，而非右上角三点菜单。

**修复**：
```python
menu_btn = d(resourceId=f"{PKG}:id/select_action_bar").child(resourceId=f"{PKG}:id/iv_menu_more")
if not menu_btn.exists:
    all_menu_more = d(resourceId=f"{PKG}:id/iv_menu_more")
    if all_menu_more.count > 1:
        menu_btn = all_menu_more[all_menu_more.count - 1]
```

**教训**：选择模式下菜单入口不同，需先进入选择模式（长按）再点底部操作栏菜单。

### 1.9 checkSource()对话框流程

**问题**：点击"校验所选"后未真正启动校验。

**根因**：checkSource()会弹出搜索关键词输入对话框，需点"确定"才启动CheckSource.start()。

**修复**：
```python
check_item.click()
time.sleep(2)
ok_btn = d(text="确定")
if not ok_btn.exists:
    ok_btn = d(text="OK")
if not ok_btn.exists:
    ok_btn = d(resourceId="android:id/button1")
if ok_btn.exists:
    ok_btn.click()
```

**教训**：校验功能有确认对话框中间步骤，测试脚本需处理对话框交互。

### 1.10 get_logcat()返回None导致异常

**问题**：`analyze_logcat_for_service()`中`get_logcat()`返回None，传入`write_text(log)`时异常`data must be str, not NoneType`。

**根因**：logcat获取失败（超时或编码问题）返回None。

**修复**：
```python
def get_logcat(filter_tag=None, timeout=15):
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return result.stdout.decode("utf-8", errors="ignore") or ""
    except Exception as e:
        return ""

log = get_logcat() or ""
```

**教训**：subprocess调用可能失败，所有外部调用都需要try-catch + None保护。用bytes模式读取再decode避免GBK编码问题。

## 2. 测试方法论

### 2.1 分层测试方案（UI+Service+数据+日志）

| 层级 | 验证方式 | 工具 |
|------|---------|------|
| UI层 | dump_hierarchy + 截图 | uiautomator2 |
| Service层 | logcat过滤Service名 | adb logcat -d |
| 数据层 | pull DB + sqlite3查询 | adb pull + Python sqlite3 |
| 日志层 | AndroidRuntime:E崩溃检测 | adb logcat -s AndroidRuntime:E |

**关键**：不能只验证UI显示，必须交叉验证Service启动+数据回填+无崩溃。

### 2.2 logcat日志过滤策略

**原则**：只搜技术关键词（Service名/类名/函数名），不搜业务数据（遵守output-safety.md）。

```python
service_keywords = [
    "CheckSourceService",      # Service名
    "CheckRssSourceService",   # Service名
    "SourceWeightCalculator",  # 类名
    "calculateBookWeight",     # 函数名
    "weight",                  # 变量名（非业务数据）
]
```

### 2.3 pull DB查询weight（WAL模式处理）

```python
# 1. su -c cp 复制DB+WAL+SHM到/sdcard/
# 2. adb pull拉取到本地
# 3. PRAGMA wal_checkpoint(TRUNCATE)合并WAL
# 4. 查询weight字段
cursor.execute("SELECT COUNT(*) FROM book_sources WHERE weight > 0")
```

**关键**：必须同时复制WAL和SHM文件，否则查询结果不完整。

### 2.4 问题发现→记录→修复闭环流程（AD-05）

**流程**：
1. 测试中发现问题立即追加到issues-found.md
2. 记录格式：问题描述+根因分析+修复方案+验证结果+状态
3. 修复后回填状态为"已修复"
4. 防止压缩上下文后丢失：issues-found.md作为任务状态的补充权威源

**反模式**：禁止"先继续测试后面再补"（怕忘记）。

## 3. 测试环境配置

| 配置项 | 值 |
|--------|-----|
| ADB路径 | D:/Program Files/Microvirt/MEmu/adb.exe |
| 设备序列号 | 127.0.0.1:21503 |
| 包名 | io.legado.app.debug |
| Python环境 | ai_tests/venv/Scripts/python.exe |
| DB pull目录 | ai_tests/reports/feature_test/db_pull/ |
| 测试报告目录 | ai_tests/reports/feature_test/ |

## 4. 编译与测试命令

### 编译命令
```bash
export JAVA_HOME='C:\Program Files\AdoptOpenJDK\jdk-17.0.0.20-hotspot'
export ANDROID_HOME='F:\myself\github\WeAgentChat\temp\legado\temp\android-sdk'
export GRADLE_USER_HOME='F:\gh'
./gradlew.bat assembleAppDebug --no-daemon --no-build-cache -Dorg.gradle.vfs.watch=false 2>&1 | tail -40
```

### 测试运行命令
```bash
ai_tests/venv/Scripts/python.exe ai_tests/scripts/verify_all_features.py 2>&1 | tee ai_tests/reports/feature_test/test_run_v4f.log
```

### DB手动pull+查询命令
```bash
adb -s 127.0.0.1:21503 shell "su -c 'cp /data/data/io.legado.app.debug/databases/legado.db /sdcard/legado.db'"
adb -s 127.0.0.1:21503 pull /sdcard/legado.db ai_tests/reports/feature_test/db_pull/legado.db
```
