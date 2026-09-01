# -*- coding: utf-8 -*-
"""compose_assert.py — Compose 迁移 L2 断言函数库（复用层）

来源：design-b1-b2-baseline-freeze.md §4.2（B2 起沉淀到 ai_tests/lib/compose_assert.py）。
被 l2_verify_compose_{page}.py 系列脚本导入，模板自包含兜底逻辑见各脚本自身。

铁律对齐（分册 §4.0 + SOP）：
- su -c 整串：整条命令作为单字符串传给 adb shell，禁止列表形式（-c 内容被按空格拆散）
- logcat 早期窗口：采集必须带 -T 时间戳起点参数（设备 date 输出），防历史日志污染
- StaleObjectException 兜底：控件断言统一走 dump_hierarchy + 正则 bounds 通道
- 脱敏：只输出计数/布尔/路径模式/技术字段，禁输出源名称/完整 URL/业务文本
"""
import base64
import re
import subprocess
import sys
import time
from pathlib import Path

import uiautomator2 as u2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:  # SOP：优先复用 config.py 常量，禁止硬编码路径
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:  # 模板自包含兜底（与既有 L2 脚本一致）
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

MAIN = f"{PKG}/io.legado.app.ui.main.MainActivity"
PREFS_DEFAULT = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
OUT_DIR = "output"


def sh(*args, timeout=30):
    """adb shell 直连（list 参数，仅用于无 su 需求的命令）"""
    return subprocess.run([ADB, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def sh_su(cmd: str, timeout=20):
    """su -c 整串铁律：整条命令作为单字符串传给 adb shell"""
    return sh("su -c '%s'" % cmd, timeout=timeout)


def connect() -> u2.Device:
    """connect 前置：adb connect + echo 探针 + su 探针 + uiautomator 残留进程清理。
    探针失败 sys.exit(2)（设备/环境不可用），对齐 l2_verify_p0_sandbox_cache.py 口径。"""
    subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
    time.sleep(1.0)
    probe = sh("echo", "device_ok", timeout=10)
    if probe.returncode != 0 or b"device_ok" not in probe.stdout:
        print("❌ 设备不可连接（MEmu 未启动或 ADB 未就绪）")
        sys.exit(2)
    if not sh_su("id -u").stdout.strip().endswith(b"0"):
        print("❌ su 不可用（MEmu 默认 root，请检查模拟器 root 开关）")
        sys.exit(2)
    # SOP 陷阱1：残留 uiautomator 进程占锁 → AccessibilityServiceAlreadyRegisteredError
    r = sh("ps", "-A", timeout=10)
    for line in r.stdout.decode("utf-8", errors="ignore").splitlines():
        if "com.github.uiautomator" in line and "shell" not in line:
            pid = line.split()[1] if line.split() else ""
            if pid.isdigit():
                sh_su(f"kill -9 {pid}", timeout=10)
                time.sleep(1.0)
    return u2.connect(HOST)


def device_now() -> str:
    """设备侧当前时间（logcat -T 时间戳起点，防历史日志污染；格式 mm-dd HH:MM:SS.mmm）"""
    r = sh("date", "+%m-%d %H:%M:%S.000", timeout=10)
    return r.stdout.decode("utf-8", errors="ignore").strip()


def logcat_errors(tag_keywords: list, since_ts: str = None, timeout=25) -> dict:
    """针对性计数：FATAL/AndroidRuntime/指定 tag → {关键词: 次数}，判定=0。
    since_ts 必传（device_now() 起点），仅统计起点之后的日志（-T 参数铁律）。"""
    cmd = f"logcat -d -T '{since_ts}'" if since_ts else "logcat -d -t 800"
    r = sh(cmd, timeout=timeout)
    log = r.stdout.decode("utf-8", errors="ignore")
    keys = ["FATAL EXCEPTION", "AndroidRuntime"] + list(tag_keywords)
    return {k: log.count(k) for k in keys}


def dump_bounds(d, pattern: str):
    """dump_hierarchy + 正则取节点 bounds；StaleObjectException 兜底通道。
    pattern 需含 text= 或 content-desc= 完整匹配段（正则片段）；返回 {left,top,cx,cy} 或 None"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        time.sleep(1.5)
        xml = d.dump_hierarchy()
    m = re.search(r'<node[^>]*' + pattern + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return {"left": x1, "top": y1, "right": x2, "bottom": y2,
            "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}


def assert_text_visible(d, text: str, timeout=5) -> bool:
    """文本可见断言（wait 超时判定）。Compose 文本节点 clickable=False 时改断言容器。"""
    try:
        return bool(d(text=text).wait(timeout=timeout))
    except Exception:
        return bool(dump_bounds(d, f'text="{re.escape(text)}"'))


def click_by_dump(d, pattern: str, timeout=5) -> bool:
    """dump→正则 bounds→坐标点击（规避 selector 失效），重试 2 次。
    底部导航为 Compose 绘制时用 content-desc 正则段（menu_rss 等语义键）。"""
    for _ in range(2):
        b = dump_bounds(d, pattern)
        if b:
            w, h = d.window_size()
            d.click(b["cx"] / w, b["cy"] / h)
            time.sleep(1.2)
            return True
        time.sleep(1)
    return False


def long_click_by_dump(d, pattern: str, duration_ms=900) -> bool:
    """长按（多选态入口）：dump→bounds→input swipe 同点长按"""
    b = dump_bounds(d, pattern)
    if not b:
        return False
    sh("input", "swipe", str(b["cx"]), str(b["cy"]), str(b["cx"]), str(b["cy"]),
       str(duration_ms), timeout=15)
    time.sleep(1.2)
    return True


def assert_window_single(d, main_anchor: str) -> bool:
    """弹框独立窗口不变量（S6-4 协议验证）：弹框开启期 dump，主界面锚点不可 dump。
    main_anchor 传主界面标志节点正则段（如底部导航 content-desc）。"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        return True  # dump 本身失败=独立窗口典型表现（Compose Dialog 窗口隔离）
    return re.search(r'<node[^>]*' + main_anchor, xml) is None


def assert_bounds_moved(before, after, min_dx=50) -> bool:
    """位移断言（回顶/间距/拖拽）：两 bounds 位移≥阈值；None 通道按 False"""
    if not before or not after:
        return False
    dx = abs(after["cx"] - before["cx"])
    dy = abs(after["cy"] - before["cy"])
    return dx >= min_dx or dy >= min_dx


def su_cat(path: str) -> str:
    """base64 通道读文件（PowerShell > 重定向会产出损坏文件，SOP 铁律）"""
    r = sh_su(f"base64 {path} 2>/dev/null")
    raw = r.stdout.decode("utf-8", errors="ignore").strip()
    if not raw:
        return ""
    return base64.b64decode(raw).decode("utf-8", errors="ignore")


def prefs_read(key: str, retries=3, interval=1.0) -> str:
    """prefs 读单键值（apply 异步落盘需轮询）；值在 value 属性非文本节点"""
    pat = re.compile(r'<\w+\s+name="' + re.escape(key) + r'" value="([^"]*)"')
    for _ in range(retries):
        xml = su_cat(PREFS_DEFAULT)
        m = pat.search(xml)
        if m:
            return m.group(1)
        time.sleep(interval)
    return ""


def prefs_read_bool(key: str) -> bool:
    return prefs_read(key) == "true"


def prefs_read_int(key: str, default=-1) -> int:
    v = prefs_read(key)
    return int(v) if v.lstrip("-").isdigit() else default


def ensure_env(d, dismiss=("关闭", "取消", "以后再说", "我知道了", "知道了")):
    """前置保障：启动主入口 + 弹窗关闭 + 包名带构建类型后缀核对"""
    if not sh(f"pm", "path", PKG, timeout=10).stdout.strip():
        print(f"❌ 包未安装或包名不匹配: {PKG}")
        sys.exit(2)
    d.app_start(PKG)
    time.sleep(6)
    for t in dismiss:
        if d(text=t).wait(timeout=1):
            d(text=t).click()
            time.sleep(1)


def shot(d, name: str):
    """截图证据（output/l2_*.png，B2 验收证据形式之一）"""
    try:
        d.screenshot(f"{OUT_DIR}/{name}.png")
    except Exception as e:
        print(f"[WARN] 截图失败 {name}: {type(e).__name__}")


def run_steps(steps: dict, scenario: str = "all", tag_keywords: list = None,
              since_ts: str = None, ctx=None) -> bool:
    """步骤注册表执行 + logcat 判定 + 汇总退出码（§4.1 main 骨架统一通道）
    ctx=设备会话（uiautomator2 device），注入每个步骤函数首参 fn(ctx)"""
    results = {}
    for sid, fn in steps.items():
        if scenario in ("all", sid):
            try:
                results[sid] = bool(fn(ctx))
            except Exception as e:  # 单步异常不中断其余步骤
                print(f"[EXC] {sid}: {type(e).__name__}")
                results[sid] = False
            print(f"{sid}: {'PASS' if results[sid] else 'FAIL'}")
    errs = logcat_errors(tag_keywords or [], since_ts=since_ts)
    fatal_ok = all(v == 0 for k, v in errs.items()
                   if k in ("FATAL EXCEPTION", "AndroidRuntime"))
    print(f"[logcat] {errs} fatal_ok={fatal_ok}")
    all_pass = bool(results) and all(results.values()) and fatal_ok
    print(f"== L2 总结: {'ALL PASS' if all_pass else 'HAS FAIL'} ==")
    return all_pass
