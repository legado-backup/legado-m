"""ai_tests/config.py — 全局配置常量

V3 固化层：路径常量、超时、崩溃模式、DB 查询模板
🔒 固化层文件：AI 不应直接修改，必须通过 OpenSpec 流程

持续迭代层（AI 可扩展）：
- CRASH_PATTERNS：基于失败案例扩展
- DB_QUERIES：基于源码 Dao 扩展
"""
from pathlib import Path

# === 项目根目录（自动推断：ai_tests/ 的父目录）===
PROJECT_ROOT = Path(__file__).parent.parent

# === MEmu 模拟器（已探测基线）===
MEMUC_PATH = r"D:\Program Files\Microvirt\MEmu\memuc.exe"
ADB_PATH = r"D:\Program Files\Microvirt\MEmu\adb.exe"
MEMU_INSTANCE_ID = 0
MEMU_ADB_HOST = "127.0.0.1:21503"

# === Legado App ===
# 简化说明：默认 miss flavor + debug 构建，与 build.gradle applicationId="io.legado.miss.app" + applicationIdSuffix=".debug" 对齐 | 已知上限：release 测试需切换为 io.legado.miss.app.release + 改 APK_GLOB_DIR 到 release 路径；legacy flavor 为 io.legado.app.debug（通过 -PcustomAppId=io.legado.app 切换） | 升级路径：基于 APK_GLOB_DIR 自动推断 BUILD_TYPE + flavor（V4）
BUILD_TYPE = "debug"  # debug | release（用户要求用debug包测试，正式包别的AI任务在用）
PACKAGE = f"io.legado.miss.app.{BUILD_TYPE}"
# 主入口 Activity：源码 AndroidManifest.xml 中 .ui.welcome.WelcomeActivity
# 注意：Activity 类名不受 applicationIdSuffix 影响，始终为 io.legado.app.ui.welcome.WelcomeActivity
MAIN_ACTIVITY = "io.legado.app.ui.welcome.WelcomeActivity"

# === APK 自动发现（M2）===
APK_GLOB_DIR = PROJECT_ROOT / "app" / "build" / "outputs" / "apk" / "app" / "debug"

# === 源码根（V3 新增：M8/M9 输入，只读分析）===
SOURCE_ROOT = PROJECT_ROOT / "app" / "src" / "main" / "java" / "io" / "legado" / "app"
ANDROID_MANIFEST = PROJECT_ROOT / "app" / "src" / "main" / "AndroidManifest.xml"

# === V3 源码映射（M8 输出，AI 持续维护）===
SOURCE_MAP_PATH = PROJECT_ROOT / "ai_tests" / "lib" / "source_map.json"

# === 测试用例源 ===
DOCS_TESTS_DIR = PROJECT_ROOT / "docs" / "tests"
AI_TESTS_CASES_DIR = PROJECT_ROOT / "ai_tests" / "cases"

# === 报告输出（M7）===
REPORTS_DIR = PROJECT_ROOT / "ai_tests" / "reports"

# === 超时（秒）===
TIMEOUT_MEMU_START = 60
TIMEOUT_MEMU_STOP = 30
TIMEOUT_ADB_WAIT = 60
TIMEOUT_APK_INSTALL = 120
TIMEOUT_FIRST_FRAME = 30
TIMEOUT_UI_OPERATION = 30
TIMEOUT_UI_IMPLICIT_WAIT = 10

# === 操作延迟（秒）===
OPERATION_DELAY_BEFORE = 0.5
OPERATION_DELAY_AFTER = 0.5
# === click 滚动查找（OpenSpec e2e-ui-executor-hardening R1）===
# click 找不到元素时自动滚动 N 次找，解决 PreferenceScreen 长列表元素在屏幕外不可见问题
# 简化说明：固定向下滚动 | 已知上限：仅向下滚动，元素在上方时找不到 | 升级路径：双向滚动查找（V4）
SCROLL_SEARCH_MAX = 5  # 最大滚动次数（实测"其它设置"页面"调试工具"需滚动 4 次可见）
SCROLL_SEARCH_INTERVAL = 0.3  # 每次滚动后等待界面刷新秒数
# === 崩溃模式（持续迭代层：基于失败案例扩展）===
# 简化说明：正则匹配 logcat 关键字 | 已知上限：仅覆盖文本日志 | 升级路径：接入 LLM 语义分析（V4）
CRASH_PATTERNS = {
    "FATAL": [
        r"FATAL EXCEPTION",
        r"AndroidRuntime.*FATAL",
        r"Process: io.legado.app.*Fatal",
    ],
    "ANR": [
        r"ANR in io.legado.app",
        r"Application Not Responding",
    ],
    "CRASH": [
        r"CRASH: io.legado.app",
        r"force-crashing",
    ],
    "OOM": [
        r"OutOfMemoryError",
        r"Failed to allocate.*allocation",
    ],
    "ClassNotFound": [
        r"ClassNotFoundException",
        r"NoClassDefFoundError",
    ],
    "Other": [
        r"IllegalStateException",
        r"NullPointerException",
        r"RuntimeException",
    ],
}

# === DB 查询模板（持续迭代层：基于源码 Dao 扩展）===
# 简化说明：硬编码 SQL 模板 | 已知上限：仅覆盖已映射模块 | 升级路径：基于源码 Dao 自动生成（V4）
DB_QUERIES = {
    "F-P0-2": "SELECT * FROM book_sources LIMIT 10;",
    "F-P0-3": "SELECT * FROM cover_gallery_groups LIMIT 10;",
    "F-P0-4": "SELECT * FROM books LIMIT 10;",
}

# === 8 类证据类型（M5）===
EVIDENCE_TYPES = [
    "logcat", "ui_xml", "screenshot", "activity_stack",
    "db_state", "prefs_state", "web_api", "meminfo",
]

# === V3 双轨调度配置 ===
# 同 TC-ID 时 Python 优先于 MD
DUAL_TRACK_PYTHON_PRIORITY = True
# Python 失败时降级执行 MD
DUAL_TRACK_FALLBACK_TO_MD = True
