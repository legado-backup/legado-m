# -*- coding: utf-8 -*-
"""l2_verify_m2_rest_pages.py — M2 剩余页真机 L2 验证（按落地顺序增量登记）

已覆盖：
  【config/top-bar-manage】F136① 远端套装下载忙态 + F136② 保存回执分级
    s1 本地套装保存 → 次级回执（「主题已保存到本地」）
    s2 应用中套装保存 → accent 强调回执（含「全局生效」）
    s3 远端套装「应用」→ 卡片按钮转「下载中…」+ 顶部细进度条（构造可测通道）
  【config/navigation-bar-manage】F115 编辑弹框内嵌迷你底栏预览
    s4 预览条渲染 + 布局切换（悬浮/常规/侧栏）即时重绘（像素指纹三态判定，取消即零污染）
  【main/discovery-suite-manage】F21 行内高频前置 + F20 倍率即时预览 + 蓝图声称已修项
    s5 常驻「设为当前」+ ⋮ 收敛 + 副标题类型摘要 + 倍率行样例（播种合成套件，测后还原 prefs 快照）
  【main/rss】F29 两级标签视觉分层 + F28 源卡未读标记
    s6 经典订阅+标签样式+常规顶栏（prefs 播种）→ 一级胶囊零回归 / 二级描边弱底分层（同栏像素对比）
       + 「全部 · N 源」源数胶囊 + 未读圆点（沙箱库播种 3 行未读，测后按前缀删除并复核归零）
  【about/read-record】F161 达成态 + F162 摘要行/续读直达 + 分隔符修复
    s7 目标分钟播种 10 →「已达成」徽标 + 达成文案；9999 → 徽标消失回退默认文案
       + 热力图摘要行按设备日聚合真值逐字核对 + 最近在读「续读 ›」+ 旧分隔符零残留

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m2_rest_pages.py [--scenario s1|s2|s3|s4|s5|all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装（build-legado.bat / quick_build_install.py 产物）

数据策略（零污染，全部限定测试包沙箱）：
  · s1/s2 通过 UI 新建顶栏套装（沿用页面默认名「自定义顶栏」），收尾经 UI「⋮ → 删除本地」
    删除**本轮创建的那一个**（按创建前后本地包名集合差集识别），不触碰任何既有套装；
  · s3 需可测通道：临时写入 WebDAV 配置（指向本机监听端口，只接受不响应 → 下载挂起）
    + 播种 remote_cache/day.json（合成远端套装），测后**整份还原 prefs 快照**并删除播种缓存。

安全：不输出源名称/域名/URL；WebDAV 地址仅为本机回环端口，不触碰任何外部服务。
"""
import argparse
import json
import re
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import uiautomator2 as u2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca  # noqa: E402

# ============================ 常量 ============================

ACT_TOPBAR = "io.legado.app.ui.config.TopBarManageActivity"

PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
PREFS_TMP = "/data/local/tmp/m2rest_prefs.xml"
EXT = f"/sdcard/Android/data/{PKG}/files"
PKG_TYPE_DIR = f"{EXT}/topBarPackages"
REMOTE_CACHE_DAY = f"{PKG_TYPE_DIR}/remote_cache/day.json"

# --- 文案锚点（取自 values-zh/strings.xml 实际值，禁臆测） ---
S_TITLE = "顶栏管理"                       # top_bar_manage
S_SUMMARY = "管理主页面顶栏"                # top_bar_manage_summary
S_ADD = "添加主题"                         # theme_add
S_MANUAL = "手动配置"                      # theme_manual_config
S_EDIT_TITLE = "编辑顶栏"                  # top_bar_edit
S_OK = "确认"                              # ok
S_APPLY = "应用"                           # theme_apply
S_APPLIED = "已应用"                       # theme_applied_state
S_EDIT = "编辑"                            # edit
S_MORE = "更多"                            # more
S_SAVED_LOCAL = "主题已保存到本地"          # theme_saved_local
S_APPLIED_RECEIPT = "全局生效"              # top_bar_saved_applied（F136② accent 强调分支）
S_DOWNLOADING = "下载中"                    # top_bar_downloading（F136① 忙态）
S_DELETE_LOCAL = "删除本地"                 # theme_delete_local
S_DELETE = "删除"                          # delete

# --- 合成远端套装（仅播种在测试包缓存目录，测后删除） ---
SEED_NAME = "L2校验远端套装"
SEED_DIR = "l2_verify_remote"

# --- navigation-bar-manage（F115 编辑弹框内嵌迷你预览） ---
ACT_NAVBAR = "io.legado.app.ui.config.NavigationBarManageActivity"
NB_TYPE_DIR = f"{EXT}/navigationBarPackages"
S_NB_MANAGE = "底栏管理"          # navigation_bar_manage
S_NB_ADD = "添加主题"             # theme_add（底栏页复用同一入口文案）
S_NB_MANUAL = "手动配置"          # theme_manual_config
S_NB_EDIT = "底栏主题"            # navigation_bar_edit（弹框标题）
S_NB_PREVIEW = "底栏预览"         # navigation_bar_preview（预览条 contentDescription）
S_NB_LAYOUT = "底栏样式"          # bottom_bar_layout_mode
S_NB_FLOATING = "悬浮底栏"        # bottom_bar_layout_floating
S_NB_STANDARD = "常规底栏"        # bottom_bar_layout_standard
S_NB_SIDEBAR = "侧边栏"           # bottom_bar_layout_sidebar
S_CANCEL = "取消"                 # cancel
# 预览条内探针：相对节点高度取底栏中线（节点内容高 72dp，底栏 52dp 底对齐 → 中线 ≈ 0.64）
BAR_Y_RATIO = 0.64
COLOR_THRESH = 6                  # 「底栏色」vs「底衬页面色」最小通道差（实测校准用，脚本会打印实值）

# --- main/discovery-suite-manage（F21 行内前置 + F20 倍率即时预览 + 修复1/2/4） ---
ACT_DISCOVERY = "io.legado.app.ui.main.explore.DiscoverySuiteManageActivity"
S_DS_SET_CURRENT = "设为当前"     # discovery_suite_set_current（常驻动作 contentDescription）
S_DS_RENAME = "重命名套件"        # discovery_suite_rename（⋮ 内）
S_DS_ALIAS = "设置别名"          # discovery_suite_alias（⋮ 内）
S_DS_DELETE = "删除套件"          # discovery_suite_delete
S_DS_OPACITY = "透明度倍率"
S_DS_MINUS = "-0.25"
S_DS_PLUS = "+0.25"
S_DS_MORE = "更多菜单"            # more_menu（⋮ 的 contentDescription）
S_DS_CREATE = "新建套件"          # discovery_suite_create（顶栏纯图标动作 → 用 contentDescription）
S_DS_ADD_WIDGET = "添加控件"      # discovery_suite_add_widget
S_DS_SAVE = "保存"                # EditorBottomBar 保存钮
S_DS_ERR_EMPTY = "请先选择要展示的 Tag 或书源目标"  # discovery_suite_widget_targets_empty（修复2 内联）
S_DS_CURRENT_TAG = "当前套件"
S_DS_EMPTY_PAGE = "还没有套件"
CONFIRM_TEXTS = ("确认", "确定", "删除")
TEST_SUITES = ("L2校验套件甲", "L2校验套件乙")

# --- 灵敏度参数 ---
DAV_PORT = 8931
DAV_URL = f"http://10.0.2.2:{DAV_PORT}/dav/"   # MEmu NAT 下宿主回环
DAV_URL_FALLBACK = "http://192.0.2.1:8080/dav/"  # TEST-NET-1 黑洞（无监听时的兜底挂起源）

CREATED_PKG_NAMES = []   # 本轮经 UI 创建的测试套装名（收尾删除）


# ============================ 基础设施 ============================

def sh(*args, timeout=45):
    try:
        return ca.sh(*args, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
        time.sleep(3)
        return ca.sh(*args, timeout=timeout)


def sh_su(cmd, timeout=30):
    return ca.sh_su(cmd, timeout=timeout)


def connect_robust(retries=3):
    """轻量连接：MEmu 上 `ps -A`/`pidof` 极慢（>60s）已被禁用（实测 2026-09-20）。"""
    subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
    time.sleep(1.5)
    for i in range(retries):
        try:
            r = ca.sh("echo", "device_ok", timeout=20)
            if b"device_ok" not in (r.stdout or b""):
                raise RuntimeError("echo 探针无响应")
            su = ca.sh("su -c 'id -u'", timeout=25)
            if not (su.stdout or b"").strip().endswith(b"0"):
                raise RuntimeError("su 不可用")
            return u2.connect(HOST)
        except Exception as e:
            print(f"[warn] connect 失败({i + 1}/{retries}): {type(e).__name__} {e}")
            subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
            time.sleep(5)
    raise RuntimeError("设备连接失败")


def reset_app():
    sh("am", "force-stop", PKG)
    time.sleep(1.5)


def current_activity() -> str:
    r = sh("dumpsys", "activity", "activities", timeout=20)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s",
                  r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def start_act(act: str):
    """启动页面。注意：ca.sh 自动补 `shell`，此处不可再传。"""
    sh("am", "start", "-n", f"{PKG}/{act}")
    time.sleep(3.0)


def dump_xml(d) -> str:
    for _ in range(2):
        try:
            return d.dump_hierarchy()
        except Exception:
            time.sleep(1.5)
    return ""


def wait_texts(d, texts, timeout=8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        xml = dump_xml(d)
        if all(t in xml for t in texts):
            return True
        time.sleep(1.0)
    return False


def poll_text(d, text, timeout=4.0, contains=False) -> bool:
    """快速轮询文本可见（selector 通道，避免全量 dump 拖过自动消退窗口）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if contains:
                if d(textContains=text).exists:
                    return True
            elif d(text=text).exists:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def tap_text(d, text, timeout=6) -> bool:
    for _ in range(2):
        try:
            node = d(text=text)
            if node.wait(timeout=timeout):
                node.click()
                time.sleep(1.2)
                return True
        except Exception:
            pass
        time.sleep(0.8)
    return ca.click_by_dump(d, f'text="{re.escape(text)}"', timeout=2)


def text_nodes(xml: str):
    """返回 [(label, top, left, cx, cy)]（含 bounds 的全部可读节点）

    label 口径：`text` 非空优先，否则取 `content-desc`（**纯图标动作**如 ⋮/顶栏图标
    只有 content-desc，旧版仅取 text 会静默漏掉 ⇒ 本轮「未定位到 ⋮」假失败的真因，2026-09-20）。
    """
    out = []
    for m in re.finditer(r'<node[^>]*>', xml):
        tag = m.group(0)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        t = re.search(r'\btext="([^"]*)"', tag)
        cd = re.search(r'\bcontent-desc="([^"]*)"', tag)
        label = (t.group(1) if t and t.group(1) else (cd.group(1) if cd else ""))
        if not label:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        out.append((label, y1, x1, (x1 + x2) // 2, (y1 + y2) // 2))
    return out


def click_xy(d, cx, cy):
    w, h = d.window_size()
    d.click(cx / w, cy / h)
    time.sleep(1.2)


def click_in_card(d, card_title: str, label: str, timeout=6) -> bool:
    """卡片作用域内点击：取卡片标题下方、最近的一个 label 文本节点（同卡内按钮）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        xml = dump_xml(d)
        nodes = text_nodes(xml)
        titles = [n for n in nodes if n[0] == card_title]
        if titles:
            title_top = max(t[1] for t in titles)
            # 同卡按钮：位于标题下方且最近的 label（下一张卡标题会更大，取最小者即可）
            cands = [n for n in nodes if n[0] == label and n[1] > title_top]
            if cands:
                _, _, _, cx, cy = min(cands, key=lambda n: n[1])
                click_xy(d, cx, cy)
                return True
        time.sleep(0.8)
    return False


def click_last_text(d, text: str, timeout=6) -> bool:
    """点击最下方该文案节点（用于确认弹框：标题与按钮同文案时取按钮）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        nodes = [n for n in text_nodes(dump_xml(d)) if n[0] == text]
        if nodes:
            _, _, _, cx, cy = max(nodes, key=lambda n: n[1])
            click_xy(d, cx, cy)
            return True
        time.sleep(0.8)
    return False


# ---------------------- 本地套装清单（FS 通道，识别本轮新建） ----------------------

def local_pkg_names(kind: str = "day") -> set:
    """读设备本地顶栏套装目录 → 套装名集合（每包目录内 top_bar.json 的 name 字段）

    ⚠️ SOP 陷阱：`sh -c` **不可**用列表形式传（adb 会按空格重拼参数，`-c` 的值被拆散 →
    命令静默变成 `sh -c cat` 无参输出）。必须把整串命令作为**单个**参数，并自带引号
    （目录名可能含空格，如「自定义顶栏 2」）。
    """
    r = sh(f"ls -1 '{PKG_TYPE_DIR}/{kind}' 2>/dev/null")
    dirs = [x.strip() for x in r.stdout.decode("utf-8", "ignore").splitlines() if x.strip()]
    names = set()
    for dn in dirs:
        rr = sh(f"cat '{PKG_TYPE_DIR}/{kind}/{dn}/top_bar.json' 2>/dev/null")
        m = re.search(r'"name"\s*:\s*"([^"]*)"', rr.stdout.decode("utf-8", "ignore"))
        if m:
            names.add(m.group(1))
    return names


# ---------------------- prefs 快照 / 还原 ----------------------

def prefs_snapshot(local_path: str) -> bool:
    reset_app()
    r = subprocess.run([ADB, "-s", HOST, "exec-out", "cat", PREFS],
                       capture_output=True, timeout=40)
    if b"</map>" not in (r.stdout or b""):
        return False
    Path(local_path).write_bytes(r.stdout)
    return True


def prefs_write(xml: str) -> bool:
    """整份写回 prefs（写前须 force-stop，防内存态覆盖）"""
    reset_app()
    tmp_local = Path(tempfile.mkdtemp(prefix="m2rest_")) / "prefs.xml"
    tmp_local.write_text(xml, encoding="utf-8")
    subprocess.run([ADB, "-s", HOST, "push", str(tmp_local), PREFS_TMP],
                   capture_output=True, timeout=60)
    sh_su(f"cat {PREFS_TMP} > {PREFS}")
    verify = sh_su(f'grep -c "</map>" {PREFS}')
    return b"1" in (verify.stdout or b"")


def prefs_patch(xml: str, values: dict) -> str:
    """插入/覆盖若干 <string name=...> 键值"""
    for k, v in values.items():
        pat = re.compile(r'<string name="' + re.escape(k) + r'">[^<]*</string>')
        item = f'<string name="{k}">{v}</string>'
        xml = pat.sub(item, xml) if pat.search(xml) else xml.replace("</map>", item + "</map>")
    return xml


def prefs_patch_typed(xml: str, values: dict) -> str:
    """插入/覆盖若干 prefs 键，**按真实元素类型**写入。

    铁律：prefs 的 `<string>` / `<int>` / `<boolean>` 元素类型必须与读取方
    （`getPrefString/Int/Boolean` → SharedPreferences 同名 getter）一致，否则抛
    ClassCastException（实测：把 int 写成 `<string>` 会让 AppConfig 读崩）。
    values 值形如 {"key": ("bool"|"int"|"str", "value")}。
    """
    for key, (kind, value) in values.items():
        xml = re.sub(
            rf'<(?:string|int|boolean|long|float) name="{re.escape(key)}"[^>]*(?:/>|>[^<]*</\w+>)',
            "", xml)
        if kind == "bool":
            item = f'<boolean name="{key}" value="{value}" />'
        elif kind == "int":
            item = f'<int name="{key}" value="{value}" />'
        else:
            item = f'<string name="{key}">{value}</string>'
        xml = xml.replace("</map>", item + "</map>")
    return xml


# ---------------------- 挂起式 TCP 监听（构造下载 in-flight 通道） ----------------------

class _HangHandler(socketserver.BaseRequestHandler):
    """只接受连接、不响应任何字节 → 客户端停在读/连接等待（制造可观测的 in-flight 窗口）"""

    def handle(self):
        try:
            self.request.settimeout(60)
            time.sleep(50)
        except Exception:
            pass


class HangServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_hang_server(port: int) -> HangServer:
    srv = HangServer(("0.0.0.0", port), _HangHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------------------- 远端缓存播种 / 清理 ----------------------

def seed_remote_cache() -> bool:
    payload = [{
        "name": SEED_NAME,
        "dirName": SEED_DIR,
        "isNightMode": False,
        "updatedAt": int(time.time() * 1000),
    }]
    tmp = Path(tempfile.mkdtemp(prefix="m2seed_")) / "day.json"
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    sh_su(f"mkdir -p {PKG_TYPE_DIR}/remote_cache")
    subprocess.run([ADB, "-s", HOST, "push", str(tmp), "/sdcard/m2seed_day.json"],
                   capture_output=True, timeout=60)
    sh_su(f"cp /sdcard/m2seed_day.json {REMOTE_CACHE_DAY}")
    sh_su("rm -f /sdcard/m2seed_day.json")
    r = sh_su(f"cat {REMOTE_CACHE_DAY} | wc -c")
    return (r.stdout or b"").strip().isdigit() and int((r.stdout or b"0").strip()) > 10


def purge_remote_cache():
    sh_su(f"rm -f {REMOTE_CACHE_DAY}")


# ============================ 步骤 ============================

def open_topbar(d) -> bool:
    reset_app()
    start_act(ACT_TOPBAR)
    ok = wait_texts(d, [S_TITLE], timeout=10)
    return ok


def _open_add_dialog_and_save(d) -> bool:
    """「添加主题 → 手动配置 → 确认」：走到保存动作即返回（回执断言由调用方紧接轮询）"""
    if not tap_text(d, S_ADD):
        print("  [create] 未找到「添加主题」")
        return False
    if not tap_text(d, S_MANUAL):
        print("  [create] 未找到「手动配置」")
        return False
    if not wait_texts(d, [S_EDIT_TITLE, S_OK], timeout=8):
        print("  [create] 编辑弹框未出现")
        return False
    return tap_text(d, S_OK)


def _register_new_pkg(before: set) -> str:
    """按本地包名集合差集识别本轮新建套装（零歧义）"""
    after = local_pkg_names()
    new = after - before
    if not new:
        print("  [create] 本地未新增套装（名称差集为空）")
        return ""
    name = sorted(new)[0]
    if name not in CREATED_PKG_NAMES:
        CREATED_PKG_NAMES.append(name)
    print(f"  [create] 新套装已创建，名称长度={len(name)}")
    return name


def _create_pkg(d) -> str:
    """UI 新建一个顶栏套装，返回新套装名（失败返回 ""）"""
    before = local_pkg_names()
    if not _open_add_dialog_and_save(d):
        return ""
    time.sleep(2.0)
    return _register_new_pkg(before)


def _delete_pkg(d, name: str) -> bool:
    """UI 删除指定套装（⋮ → 删除本地 → 确认），复位当前应用套装"""
    if not open_topbar(d):
        return False
    if not click_in_card(d, name, S_MORE):
        print("  [clean] 未定位到卡片 ⋮")
        return False
    time.sleep(1.0)
    if not tap_text(d, S_DELETE_LOCAL):
        print("  [clean] 未找到「删除本地」")
        return False
    time.sleep(1.2)
    if not click_last_text(d, S_DELETE):
        print("  [clean] 确认删除未命中")
        return False
    time.sleep(2.5)
    gone = name not in local_pkg_names()
    print(f"  [clean] 套装已从本地删除={gone}")
    return gone


def s1_local_save_receipt(d) -> bool:
    """F136②：本地（非应用）套装保存 → 次级回执「主题已保存到本地」"""
    if not open_topbar(d):
        print("  [s1] 未进入顶栏管理页")
        return False
    before = local_pkg_names()
    if not _open_add_dialog_and_save(d):
        return False
    # 回执 3.6s 自动消退 → 保存后必须紧接轮询，再走 FS 识别（FS 多次 adb 往返耗时）
    hit = poll_text(d, S_SAVED_LOCAL, timeout=4.0)
    applied = poll_text(d, S_APPLIED_RECEIPT, timeout=0.4, contains=True)
    ca.shot(d, "m2rest_s1_local_receipt")
    name = _register_new_pkg(before)
    print(f"  [s1] 次级回执={hit} / 误报强调回执={applied} / 新套装已登记={bool(name)} | 当前页={current_activity()}")
    return hit and not applied and bool(name)


def s2_applied_save_receipt(d) -> bool:
    """F136②：应用中套装保存 → accent 强调回执（含「全局生效」）"""
    if not open_topbar(d):
        print("  [s2] 未进入顶栏管理页")
        return False
    name = CREATED_PKG_NAMES[0] if CREATED_PKG_NAMES else _create_pkg(d)
    if not name:
        return False
    if not wait_texts(d, [name], timeout=8):
        print("  [s2] 卡片未渲染")
        return False
    # 1) 设为当前应用套装（卡片按钮由「应用」→「已应用」）
    if not click_in_card(d, name, S_APPLY):
        print("  [s2] 未点击「应用」")
        return False
    time.sleep(3.0)
    applied_state = poll_text(d, S_APPLIED, timeout=6.0)
    print(f"  [s2] 套装已应用={applied_state}")
    if not applied_state:
        return False
    # 2) 编辑当前应用套装并保存 → 强调回执
    if not click_in_card(d, name, S_EDIT):
        print("  [s2] 未点击「编辑」")
        return False
    if not wait_texts(d, [S_EDIT_TITLE, S_OK], timeout=8):
        print("  [s2] 编辑弹框未出现")
        return False
    tap_text(d, S_OK)
    hit = poll_text(d, S_APPLIED_RECEIPT, timeout=4.0, contains=True)
    print(f"  [s2] 强调回执（含「全局生效」）={hit}")
    ca.shot(d, "m2rest_s2_applied_receipt")
    return hit


def s3_remote_download_busy(d, dav_url: str = None) -> bool:
    """F136①：远端套装「应用」→ 卡片按钮转「下载中…」+ 顶部细进度条

    构造通道：WebDAV 指向只接受不响应的本地监听（下载挂起）+ 播种 remote_cache，
    清单加载超时(4s)后回退缓存 → 卡片以 REMOTE 源渲染。测后整份还原 prefs 快照。
    """
    url = dav_url or DAV_URL
    srv = None
    snap = Path(tempfile.mkdtemp(prefix="m2prefs_")) / "prefs.xml"
    if not prefs_snapshot(str(snap)):
        print("  [s3] prefs 快照失败（前置）")
        return False
    try:
        if url == DAV_URL:
            try:
                srv = start_hang_server(DAV_PORT)
            except Exception as e:
                print(f"  [s3] 监听端口不可用({type(e).__name__})，改用黑洞地址")
                url = DAV_URL_FALLBACK
        xml = snap.read_text(encoding="utf-8")
        xml = prefs_patch(xml, {
            "cloudStorageType": "WEBDAV",
            "web_dav_url": url,
            "web_dav_account": "l2",
            "web_dav_password": "l2",
        })
        if not prefs_write(xml):
            print("  [s3] prefs 写入失败")
            return False
        if not seed_remote_cache():
            print("  [s3] 远端缓存播种失败")
            return False

        open_topbar(d)
        ready = poll_text(d, SEED_NAME, timeout=14.0)
        print(f"  [s3] 远端卡片可见={ready} | 当前页={current_activity()}")
        if not ready:
            ca.shot(d, "m2rest_s3_no_remote_card")
            return False
        ca.shot(d, "m2rest_s3_remote_card")

        if not click_in_card(d, SEED_NAME, S_APPLY):
            print("  [s3] 未点击远端卡片「应用」")
            return False
        busy = poll_text(d, S_DOWNLOADING, timeout=5.0, contains=True)
        print(f"  [s3] 下载忙态「{S_DOWNLOADING}…」可见={busy}")
        ca.shot(d, "m2rest_s3_downloading")
        return busy
    finally:
        if srv is not None:
            try:
                srv.shutdown()
            except Exception:
                pass
        purge_remote_cache()
        xml_back = snap.read_text(encoding="utf-8")
        ok_restore = prefs_write(xml_back)
        print(f"  [s3] prefs 已还原={ok_restore} / 播种缓存已删")
        reset_app()
        open_topbar(d)
        clean = not poll_text(d, SEED_NAME, timeout=6.0)
        print(f"  [s3] 还原后远端卡片不再出现={clean}")


def sc_purge_created(d) -> bool:
    """收尾：删除本轮创建的全部测试套装（零残留）"""
    ok = True
    for name in list(CREATED_PKG_NAMES):
        ok = _delete_pkg(d, name) and ok
    if not CREATED_PKG_NAMES:
        print("  [sc] 本轮无新建套装")
    print(f"  [sc] 清理完成={ok} / 剩余测试套装={len(CREATED_PKG_NAMES)}")
    return ok


def nav_pkg_names(kind: str = "day") -> set:
    """底栏套装名集合（目录内 navigation.json 的 name 字段；仅用于零污染校验）"""
    r = sh(f"ls -1 '{NB_TYPE_DIR}/{kind}' 2>/dev/null")
    dirs = [x.strip() for x in r.stdout.decode("utf-8", "ignore").splitlines() if x.strip()]
    names = set()
    for dn in dirs:
        rr = sh(f"cat '{NB_TYPE_DIR}/{kind}/{dn}/navigation.json' 2>/dev/null")
        m = re.search(r'"name"\s*:\s*"([^"]*)"', rr.stdout.decode("utf-8", "ignore"))
        if m:
            names.add(m.group(1))
    return names


# ---------------------- 像素探针（预览条是否随配置重绘的客观判定） ----------------------

def _mean_rgb(img, cx, cy, rad=2):
    xs = range(max(0, cx - rad), min(img.width, cx + rad + 1))
    ys = range(max(0, cy - rad), min(img.height, cy + rad + 1))
    px = [img.getpixel((x, y)) for x in xs for y in ys]
    if not px:
        return (0, 0, 0)
    return tuple(sum(p[i] for p in px) // len(px) for i in range(3))


def _dist(a, b) -> int:
    return max(abs(a[i] - b[i]) for i in range(3))


def preview_signature(shot_path: str, bounds: dict):
    """返回预览条的布局指纹：(底栏中线左缘 6px 处是否底栏色, 顶部左缘 30px 处是否底栏色)

    三种布局的可判别签名（相对节点自身边界，与屏幕尺寸/密度无关）：
      悬浮：底栏内缩 8dp → (中线左缘 6px=底衬, 顶部=底衬)
      常规：底栏贴左 → (中线左缘 6px=底栏, 顶部=底衬)
      侧栏：竖条贴左且全高 → (中线左缘 6px=底栏, 顶部=底栏)
    """
    from PIL import Image
    img = Image.open(shot_path).convert("RGB")
    # 底衬参考点取「顶部水平居中」：三种布局下该点都是底衬（侧栏条只占左侧 50dp）
    # ⚠️ 不可取左上角——侧栏布局下左上角落在竖条内，会把参考色取成底栏色（实测踩坑 2026-09-20）
    cx = (bounds["left"] + bounds["right"]) // 2
    plate = _mean_rgb(img, cx, bounds["top"] + 6)
    h = bounds["bottom"] - bounds["top"]
    bar_y = bounds["top"] + int(h * BAR_Y_RATIO)
    mid_left = _mean_rgb(img, bounds["left"] + 6, bar_y)
    top_left = _mean_rgb(img, bounds["left"] + 30, bounds["top"] + 12)
    sig = (_dist(mid_left, plate) > COLOR_THRESH, _dist(top_left, plate) > COLOR_THRESH)
    print(f"    [probe] plate={plate} mid_left={mid_left}(d={_dist(mid_left, plate)}) "
          f"top_left={top_left}(d={_dist(top_left, plate)}) → sig={sig}")
    return sig


def preview_bounds(d):
    """定位预览条（contentDescription 语义节点）"""
    try:
        node = d(description=S_NB_PREVIEW)
        if node.exists:
            return node.info["bounds"]
    except Exception:
        pass
    return None


def _open_navbar_edit_dialog(d) -> bool:
    """底栏页 → 添加主题 → 手动配置 → 编辑弹框（不落盘，取消即零污染）"""
    reset_app()
    start_act(ACT_NAVBAR)
    if not wait_texts(d, [S_NB_MANAGE], timeout=10):
        print(f"  [s4] 未进入底栏管理页（栈顶={current_activity()}）")
        return False
    if not tap_text(d, S_NB_ADD):
        print("  [s4] 未找到「添加主题」")
        return False
    if not tap_text(d, S_NB_MANUAL):
        print("  [s4] 未找到「手动配置」")
        return False
    ok = wait_texts(d, [S_NB_EDIT, S_NB_PREVIEW], timeout=8)
    if not ok:
        xml = dump_xml(d)
        has_edit = S_NB_EDIT in xml
        has_name = S_CANCEL in xml
        has_preview_desc = S_NB_PREVIEW in xml
        print(f"  [s4][diag] 弹框标题={has_edit} / 取消键={has_name} / 预览描述={has_preview_desc} "
              f"/ preview_bounds={bool(preview_bounds(d))} / 栈顶={current_activity()}")
    return ok


def s4_navbar_edit_preview(d) -> bool:
    """F115：编辑弹框内嵌迷你底栏预览 + 布局切换即时重绘（像素指纹三态判定）"""
    import tempfile as _tf
    before = nav_pkg_names()
    if not _open_navbar_edit_dialog(d):
        return False
    shot_dir = Path(_tf.mkdtemp(prefix="m2shot_"))
    ok_gate = True
    observed = {}

    def capture(tag: str):
        b = preview_bounds(d)
        if not b:
            print(f"  [s4] {tag}: 预览条不可定位（content-desc 未命中）")
            return None
        p = str(shot_dir / f"{tag}.png")
        d.screenshot(p)
        return preview_signature(p, b)

    # 1) 显式切「悬浮底栏」再采基线（设备侧 AppConfig.bottomBarLayoutMode 未必是悬浮，实测为常规）
    if tap_text(d, S_NB_LAYOUT):
        time.sleep(1.0)
        tap_text(d, S_NB_FLOATING)
        time.sleep(2.0)
    observed["floating"] = capture("floating")
    ca.shot(d, "m2rest_s4_preview_floating")

    # 2) 切「常规底栏」
    if tap_text(d, S_NB_LAYOUT):
        time.sleep(1.0)
        tap_text(d, S_NB_STANDARD)
        time.sleep(2.0)
        observed["standard"] = capture("standard")
        ca.shot(d, "m2rest_s4_preview_standard")
    else:
        print("  [s4] 未找到「底栏样式」行")
        ok_gate = False

    # 3) 切「侧边栏」
    if tap_text(d, S_NB_LAYOUT):
        time.sleep(1.0)
        tap_text(d, S_NB_SIDEBAR)
        time.sleep(2.0)
        observed["sidebar"] = capture("sidebar")
        ca.shot(d, "m2rest_s4_preview_sidebar")

    ok_gate = ok_gate and all(observed.get(k) is not None for k in ("floating", "standard", "sidebar"))
    if not ok_gate:
        print(f"  [s4] 指纹采集不全：{observed}")
        return False

    floating_ok = observed["floating"] == (False, False)
    standard_ok = observed["standard"] == (True, False)
    sidebar_ok = observed["sidebar"] == (True, True)
    print(f"  [s4] 指纹判定 悬浮={floating_ok} 常规={standard_ok} 侧栏={sidebar_ok}")

    # 4) 取消 → 零污染校验（未落盘、未新建套装）
    tap_text(d, S_CANCEL)
    time.sleep(1.5)
    closed = preview_bounds(d) is None
    after = nav_pkg_names()
    no_new = (after - before) == set()
    print(f"  [s4] 弹框已关闭={closed} / 未新建套装={no_new}")
    return floating_ok and standard_ok and sidebar_ok and closed and no_new


def _tap_desc(d, desc, timeout=6) -> bool:
    """纯图标动作（contentDescription）点击"""
    try:
        node = d(description=desc)
        if node.wait(timeout=timeout):
            node.click()
            time.sleep(1.2)
            return True
    except Exception:
        pass
    return ca.click_by_dump(d, f'content-desc="{re.escape(desc)}"', timeout=2)


def _input_first_edittext(d, text: str) -> bool:
    """定位首个 EditText（Compose TextField 在 a11y 层为 android.widget.EditText）并输入"""
    b = None
    for _ in range(2):
        b = ca.dump_bounds(d, 'class="android.widget.EditText"')
        if b:
            break
        time.sleep(2.0)
    if not b:
        return False
    click_xy(d, b["cx"], b["cy"])
    time.sleep(0.8)
    try:
        d.send_keys(text)
    except Exception:
        sh("input", "text", text)
    time.sleep(1.0)
    return True


def _tap_confirm(d, timeout=6) -> bool:
    """确认键（不同弹框文案不一：确认/确定/删除）→ 取最下方命中项"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        nodes = [n for n in text_nodes(dump_xml(d)) if n[0] in CONFIRM_TEXTS]
        if nodes:
            _, _, _, cx, cy = max(nodes, key=lambda n: n[1])
            click_xy(d, cx, cy)
            return True
        time.sleep(0.6)
    return False


def _row_title_containing(d, keyword: str, timeout=6.0) -> str:
    """列表中包含关键字的行标题实文本（弹框可能预填名称导致前后缀差异 → 不假设全等）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        cands = [n[0] for n in text_nodes(dump_xml(d))
                 if keyword in n[0] and len(n[0]) <= len(keyword) + 8]
        if cands:
            return min(cands, key=len)
        time.sleep(0.8)
    return ""


def _create_suite(d, name: str) -> str:
    """顶栏「新建套件」→ 名称输入 → 确认；返回列表中的实际行标题（失败返回 ""）"""
    if not _tap_desc(d, S_DS_CREATE):
        print("  [s5] 未找到「新建套件」顶栏动作")
        return ""
    time.sleep(1.5)
    if not _input_first_edittext(d, name):
        print("  [s5] 未定位到套件名称输入框")
        return ""
    if not _tap_confirm(d):
        print("  [s5] 名称弹框确认未命中")
        return ""
    time.sleep(2.0)
    # 创建成功后页面直接进入该套件详情态 ⇒ 返回列表再定位行（实测确认，2026-09-20）
    sh("input", "keyevent", "KEYCODE_BACK")
    time.sleep(1.8)
    return _row_title_containing(d, name, timeout=8.0)


def _multiset_diff(after: list, before: list) -> list:
    """标签多重集差（弹出菜单内容 = 打开后标签 - 打开前标签，规避「列表里的同名节点」干扰）"""
    pool = list(before)
    out = []
    for x in after:
        if x in pool:
            pool.remove(x)
        else:
            out.append(x)
    return out


def _dismiss_popup(d):
    """点顶栏空白区关掉弹出菜单（避免 BACK 触发页面回退）"""
    w, h = d.window_size()
    click_xy(d, w // 2, int(h * 0.08))
    time.sleep(1.0)


def _delete_suite(d, name: str) -> bool:
    """列表行 ⋮ → 删除（R.string.delete=「删除」）→ 确认"""
    if not click_in_card(d, name, S_DS_MORE):
        print(f"  [s5][clean] 未定位到 {name} 的 ⋮")
        return False
    time.sleep(1.0)
    if not tap_text(d, S_DELETE):
        print("  [s5][clean] 未找到「删除」")
        return False
    time.sleep(1.2)
    if not _tap_confirm(d):
        print("  [s5][clean] 删除确认未命中")
        return False
    time.sleep(2.0)
    return not poll_text(d, name, timeout=4.0)


def _purge_test_suites(d) -> None:
    """清理本脚本历史运行留下的测试套件（命名前缀 L2 为测试专用，避免误删用户数据）"""
    for _ in range(8):
        xml = dump_xml(d)
        cands = [n[0] for n in text_nodes(xml)
                 if n[0].startswith(("L2Suite", "L2校验套件"))]
        if not cands:
            return
        if not _delete_suite(d, sorted(cands, key=len)[0]):
            return


def s5_discovery_suite_row_and_opacity(d) -> bool:
    """发现套件管理（真实 UI 流程，零污染）：

    ①F21 非当前套件行常驻「设为当前」；⋮ 内不再重复该项（仅剩重命名/别名/删除）
    ②F20 倍率行 mini 面板样例 + 步进原位可见
    ③修复2 控件保存校验：无目标时**就地内联**报错（原为 toast）
    收尾：删除本轮创建的两个套件并复检测试残留归零

    前置：设备**无用户套件**（脚本会先清理自身历史残留；用户数据不受影响）
    """
    reset_app()
    start_act(ACT_DISCOVERY)
    time.sleep(2.5)
    if not ca.dump_bounds(d, f'content-desc="{re.escape(S_DS_CREATE)}"'):
        print(f"  [s5] 未进入套件管理列表态（栈顶={current_activity()}）")
        return False
    _purge_test_suites(d)
    created = []
    for name in TEST_SUITES:
        title = _create_suite(d, name)
        if not title:
            print(f"  [s5] 新建套件失败（第 {len(created) + 1} 个）")
            break
        created.append(title)
    if len(created) != 2:
        print(f"  [s5] 前置不足（已建 {len(created)} 个），跳过断言")
        for t in created:
            _delete_suite(d, t)
        return False

    xml = dump_xml(d)
    current_tag_count = xml.count(S_DS_CURRENT_TAG)
    residents = 0
    try:
        residents = d(description=S_DS_SET_CURRENT).count
    except Exception:
        pass
    print(f"  [s5] 「{S_DS_CURRENT_TAG}」出现 {current_tag_count} 次（应=1）/ "
          f"常驻「{S_DS_SET_CURRENT}」数={residents}（应=1）")
    ca.shot(d, "m2rest_s5_rows")

    # 定位常驻动作所在行（= 非当前套件行）→ 校验其 ⋮ 收敛
    act_bounds = ca.dump_bounds(d, f'content-desc="{re.escape(S_DS_SET_CURRENT)}"')
    row_title = ""
    if act_bounds:
        cands = [n for n in text_nodes(xml) if n[0] in created]
        if cands:
            row_title = min(cands, key=lambda n: abs(n[4] - act_bounds["cy"]))[0]
    menu_labels, menu_set_current = [], True
    if row_title:
        before_labels = [n[0] for n in text_nodes(dump_xml(d))]
        if click_in_card(d, row_title, S_DS_MORE):
            time.sleep(1.2)
            after_labels = [n[0] for n in text_nodes(dump_xml(d))]
            menu_labels = _multiset_diff(after_labels, before_labels)
            menu_set_current = S_DS_SET_CURRENT in menu_labels
            ca.shot(d, "m2rest_s5_more_menu")
            _dismiss_popup(d)
    expected_menu = {"编辑", S_DS_RENAME, S_DS_ALIAS, S_DELETE}
    print(f"  [s5] 非当前行 ⋮ 弹出项={sorted(set(menu_labels))}（期望={sorted(expected_menu)}）"
          f" / 含「{S_DS_SET_CURRENT}」={menu_set_current}")

    # 详情页（点非当前套件行进入）→ F20 倍率行
    detail_ok = False
    step_ok = False
    if row_title:
        tap_text(d, row_title)
        time.sleep(2.5)
        detail_xml = dump_xml(d)
        detail_ok = S_DS_OPACITY in detail_xml
        ca.shot(d, "m2rest_s5_detail_opacity")
        if tap_text(d, S_DS_PLUS):
            time.sleep(1.5)
            step_ok = "1.25x" in dump_xml(d)
    print(f"  [s5] 详情倍率行可见={detail_ok} / +0.25 后文案 1.25x={step_ok}")

    # 修复2：控件编辑器内不选目标直接保存 → 内联报错
    inline_ok = False
    if _tap_desc(d, S_DS_ADD_WIDGET):
        time.sleep(2.5)
        if tap_text(d, S_DS_SAVE):
            time.sleep(1.5)
            inline_ok = poll_text(d, S_DS_ERR_EMPTY, timeout=4.0)
            ca.shot(d, "m2rest_s5_inline_validate")
    print(f"  [s5] 控件保存内联校验可见={inline_ok}")

    # 收尾：逐级返回列表（编辑器→详情→列表），必要时重进页面 → 删除两个套件 → 复检残留归零
    for _ in range(2):
        sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.2)
    if not ca.dump_bounds(d, f'content-desc="{re.escape(S_DS_CREATE)}"'):
        start_act(ACT_DISCOVERY)
        time.sleep(2.5)
    purge_ok = True
    for t in created:
        purge_ok = _delete_suite(d, t) and purge_ok
    residue = [n[0] for n in text_nodes(dump_xml(d))
               if n[0].startswith(("L2Suite", "L2校验套件"))]
    print(f"  [s5] 清理={purge_ok} / 残留测试套件={len(residue)}")

    return (current_tag_count == 1 and residents == 1
            and set(menu_labels) == expected_menu and not menu_set_current
            and detail_ok and step_ok and inline_ok
            and purge_ok and not residue)


# ============================ main/rss（F29 两级标签分层 + F28 源卡未读标记） ============================

ACT_MAIN = "io.legado.app.ui.main.MainActivity"
S_TAB_RSS = "订阅"                    # R.string.rss（底栏导航标签）
S_FILTER = "筛选"                     # R.string.screen（顶栏筛选箭头 contentDescription）
S_UNREAD_DOT = "有未读文章"           # rss_source_unread（未读圆点 contentDescription）
S_GROUP_ALL = "全部"                  # R.string.all_groups（一级胶囊）
S_GROUP_WEB = "网页"                  # R.string.type_web（一级同栏底衬参照）
S_RSS_COUNT_PREFIX = "全部 · "        # rss_tag_all_count（F29 二级「全部」胶囊的源数前缀）
DB_REL = "databases/legado.db"
UNREAD_SEED_PREFIX = "l2seed/"


def _remote_md5(path: str) -> str:
    r = sh(f"run-as {PKG} md5sum {path}", timeout=60)
    m = re.search(rb"([0-9a-f]{32})", r.stdout or b"")
    return m.group(1).decode() if m else ""


def _local_md5(path: Path) -> str:
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _db_pull(workdir: Path) -> Path:
    """拉取测试包数据库（含 -wal/-shm 以保持一致性），本地 checkpoint 合并后返回主库路径

    `exec-out` 通道（二进制安全）+ 主库 md5 比对：截断/串包一律可被识别。
    """
    reset_app()
    main = workdir / "legado.db"
    for suffix in ("", "-wal", "-shm"):
        dst = workdir / f"legado.db{suffix}"
        with open(dst, "wb") as fh:
            r = subprocess.run(
                [ADB, "-s", HOST, "exec-out", f"run-as {PKG} cat {DB_REL}{suffix}"],
                stdout=fh, stderr=subprocess.DEVNULL, timeout=120)
        if r.returncode != 0 or dst.stat().st_size == 0:
            dst.unlink(missing_ok=True)
    if not main.exists() or main.stat().st_size < 4096:
        return None
    remote = _remote_md5(DB_REL)
    if remote and remote != _local_md5(main):
        print("  [db] ⚠️ 拉取主库 md5 不一致（-wal 未合并的合法差异或截断），按本地副本继续")
    con = sqlite3.connect(str(main))
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.commit()
    finally:
        con.close()
    return main


def _db_push(local_path: Path) -> bool:
    """整份写回数据库：`adb push` → /data/local/tmp → `run-as cp`（**app uid 属主 + 目录默认
    SELinux 标签**），写后删设备侧 WAL/SHM 并做 **md5 双向校验**。

    🔴 铁律：**不可用 `adb shell` + stdin 灌入**写二进制 —— 实测 300000B 仅落地 246B
    （2026-09-20 沙箱库被重建为空库的真因）；`exec-out`/`push` 才是二进制安全通道。
    """
    reset_app()
    tmp = "/data/local/tmp/l2_db_push.db"
    r = subprocess.run([ADB, "-s", HOST, "push", str(local_path), tmp],
                       capture_output=True, timeout=180)
    if r.returncode != 0:
        print("  [db] push 到 /data/local/tmp 失败")
        return False
    sh(f"run-as {PKG} cp {tmp} {DB_REL}", timeout=90)
    sh(f"run-as {PKG} rm -f {DB_REL}-wal", timeout=30)
    sh(f"run-as {PKG} rm -f {DB_REL}-shm", timeout=30)
    sh(f"rm -f {tmp}", timeout=30)
    remote_md5 = _remote_md5(DB_REL)
    local_md5 = _local_md5(local_path)
    ok = bool(remote_md5) and remote_md5 == local_md5
    print(f"  [db] 写回校验 md5_match={ok}（size={local_path.stat().st_size}）")
    return ok


def _snapshot_db(workdir: Path, dest: Path) -> bool:
    """写库前的整份快照（收尾必须回滚，见 s6 finally）"""
    import shutil
    db = _db_pull(workdir)
    if db is None:
        return False
    shutil.copy2(db, dest)
    return True


def _db_seed_unread(workdir: Path, rows: int = 3) -> bool:
    """播种未读文章（挑第一个启用源），返回是否成功；日志只打印源指纹，不落源名称/URL"""
    db = _db_pull(workdir)
    if db is None:
        print("  [s6] 数据库拉取失败（播种中止）")
        return False
    con = sqlite3.connect(str(db))
    try:
        cur = con.cursor()
        row = cur.execute(
            "select sourceUrl from rssSources where enabled = 1 order by customOrder limit 1"
        ).fetchone()
        if not row:
            print("  [s6] 无启用源，无法播种")
            return False
        origin = row[0]
        cur.executemany(
            "insert or replace into rssArticles"
            "(origin, sort, title, `order`, link, pubDate, description, content, image,"
            " `group`, read, variable, type, durPos)"
            " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(origin, "l2sort", "L2校验文章", 10 ** 13 - i, f"{UNREAD_SEED_PREFIX}{i}",
              "", "", "", "", "默认分组", 0, "", 0, 0) for i in range(rows)])
        con.commit()
    finally:
        con.close()
    ok = _db_push(db)
    print(f"  [s6] 未读播种 rows={rows} / 写回={ok} / 源指纹={hash(origin) % 10000}")
    return ok


def _db_purge_seeded(workdir: Path) -> int:
    """清理播种行（按 link 前缀），返回删除行数（-1=通道失败）；不触碰既有数据"""
    db = _db_pull(workdir)
    if db is None:
        return -1
    con = sqlite3.connect(str(db))
    try:
        cur = con.cursor()
        cur.execute("delete from rssArticles where link like ?", (f"{UNREAD_SEED_PREFIX}%",))
        removed = cur.rowcount
        con.commit()
    finally:
        con.close()
    _db_push(db)
    return removed


def _open_rss_tab(d, tries=3) -> bool:
    """底栏切到订阅 tab：`menu_rss` 节点坐标点击为主通道，文案/描述兜底；
    **判据唯一**=底栏选中态落在 `menu_rss`（不依赖任何业务文案）。"""
    for _ in range(tries):
        if _selected_tab(dump_xml(d)) == "menu_rss":
            time.sleep(2.0)
            return True
        if not ca.click_by_dump(d, 'resource-id="[^"]*menu_rss[^"]*"', timeout=4):
            if not _tap_desc(d, S_TAB_RSS, timeout=3):
                tap_text(d, S_TAB_RSS, timeout=3)
        time.sleep(2.5)
    return _selected_tab(dump_xml(d)) == "menu_rss"


def _selected_tab(xml: str) -> str:
    """底栏当前选中 tab 的菜单 id 后缀（只读 id/selected 属性，不涉及任何业务文案）"""
    for tag in re.findall(r"<node[^>]*>", xml):
        if 'selected="true"' in tag:
            m = re.search(r'resource-id="[^"]*/(menu_\w+)"', tag)
            if m:
                return m.group(1)
    return ""


def _desc_count(d, desc: str) -> int:
    try:
        return d(description=desc).count
    except Exception:
        return 0


def _two_level_probe(d, workdir: Path) -> dict:
    """两级同栏像素对比：chip 中心色 vs 同栏未选中 chip 中心色（后者=透明底 → 顶栏底色参照）"""
    from PIL import Image
    xml = dump_xml(d)
    nodes = text_nodes(xml)
    w, _h = d.window_size()
    shot = str(workdir / "probe.png")
    d.screenshot(shot)
    img = Image.open(shot).convert("RGB")

    def pick(label, prefix=False):
        if prefix:
            return next((n for n in nodes if n[0].startswith(label)), None)
        return next((n for n in nodes if n[0] == label), None)

    def ref_of(sel):
        _, _, left, cx, cy = sel
        # 排除：自身、左侧节点、同栏右侧动作区（筛选按钮自带底色，不能当底衬参照）
        cands = [n for n in nodes
                 if abs(n[4] - cy) <= 24 and n[2] > left + 8
                 and abs(n[3] - cx) >= 8 and n[3] < w - 48]
        return min(cands, key=lambda n: n[2]) if cands else None

    out = {}
    for key, sel in (("primary", pick(S_GROUP_ALL)),
                     ("secondary", pick(S_RSS_COUNT_PREFIX, True))):
        ref = ref_of(sel) if sel else None
        if ref is None:
            out[key] = None
            print(f"    [probe] {key}: 未定位到选中/参照 chip")
            continue
        sel_rgb = _mean_rgb(img, sel[3], sel[4])
        ref_rgb = _mean_rgb(img, ref[3], ref[4])
        out[key] = _dist(sel_rgb, ref_rgb)
        print(f"    [probe] {key}: sel={sel_rgb} ref={ref_rgb} delta={_dist(sel_rgb, ref_rgb)}")
    return out


def s6_rss_tag_hierarchy_and_unread(d) -> bool:
    """订阅页（main/rss）：F29 两级标签视觉分层 + F28 源卡未读标记

    构造通道：prefs 播种「经典订阅 + 标签样式 + 常规顶栏」——仅常规顶栏下一级分组胶囊与
  二级源标签同屏，才存在「两级」判定对象；F28 用测试包沙箱数据库播种 3 条未读文章
  （link 唯一前缀，测后删除并复核归零）。零污染：prefs 快照还原 **+ 数据库整份快照回滚**。

  🔴 沙箱库写回铁律（2026-09-20 踩坑，代价=整库被重建为空库）：**禁止用 `adb shell` + stdin
  灌二进制**（实测 300000B 只落地 246B）；必须 `adb push` → `/data/local/tmp` → `run-as cp`，
  并在写后做 **md5 双向校验**；写库前必须先快照、收尾整份回滚。
  """
    workdir = Path(tempfile.mkdtemp(prefix="m2rss_"))
    snap = workdir / "prefs.xml"
    db_snap = workdir / "legado_snapshot.db"
    if not prefs_snapshot(str(snap)):
        print("  [s6] prefs 快照失败（前置）")
        return False
    if not _snapshot_db(workdir, db_snap):
        print("  [s6] 数据库快照失败（前置）")
        return False
    ok = False
    try:
        xml = prefs_patch_typed(snap.read_text(encoding="utf-8"), {
            "modernRssPage": ("bool", "false"),
            "sourceGroupStyle": ("int", "1"),
            "sourceGroupMode": ("int", "0"),
            "defaultTopBarStyle": ("str", "regular"),
        })
        if not prefs_write(xml):
            print("  [s6] prefs 写入失败")
            return False
        if not _db_seed_unread(workdir):
            print("  [s6] 未读播种失败")
            return False

        reset_app()
        start_act(ACT_MAIN)
        time.sleep(3.0)
        if not _open_rss_tab(d):
            print(f"  [s6] 未进入订阅 tab（栈顶={current_activity()}）")
            return False
        landed = False
        for _ in range(6):
            xml_now = dump_xml(d)
            if _selected_tab(xml_now) == "menu_rss" and S_GROUP_ALL in xml_now:
                landed = True
                break
            time.sleep(2.0)
        print(f"  [s6] 订阅页经典标签样式落地={landed} / 选中tab={_selected_tab(dump_xml(d))} "
              f"/ 类型胶囊(按类型样式才有)={S_GROUP_WEB in dump_xml(d)}")
        ca.shot(d, "m2rest_s6_classic_grid")
        if not landed:
            return False

        # F28：未读圆点（唯一播种源 ⇒ 恰好 1 个；零基线校验见收尾）
        dots = _desc_count(d, S_UNREAD_DOT)
        print(f"  [s6] 未读圆点数量={dots}（期望 1）")
        ca.shot(d, "m2rest_s6_unread_dot")

        # F29①：展开二级源标签，核对「全部 · N 源」源数前缀
        expanded = _tap_desc(d, S_FILTER)
        time.sleep(1.5)
        count_chip = next((n for n in text_nodes(dump_xml(d))
                           if n[0].startswith(S_RSS_COUNT_PREFIX)), None)
        print(f"  [s6] 筛选展开={expanded} / 二级源数胶囊={bool(count_chip)}")
        ca.shot(d, "m2rest_s6_two_level_tags")

        # F29②：两级选中态同栏像素对比（弱底 vs 实心；同栏未选中 chip 作底衬参照，规避主题差异）
        probe = _two_level_probe(d, workdir) if count_chip else {}
        prim = probe.get("primary")
        sec = probe.get("secondary")
        # 判定口径：①一级仍为实心选中底（零回归） ②两级选中填充强度可区分（一眼分层）
        hierarchy_ok = (prim is not None and sec is not None
                        and prim >= 4 and min(prim, sec) >= 2 and abs(prim - sec) >= 4)
        print(f"  [s6] 两级填充差判定={hierarchy_ok}（primary={prim} secondary={sec}）")

        # F28 收尾：清理播种 → 复核未读圆点归零（同一进程内 DB 失效触达）
        removed = _db_purge_seeded(workdir)
        reset_app()
        start_act(ACT_MAIN)
        time.sleep(3.0)
        reopened = _open_rss_tab(d)
        time.sleep(2.0)
        dots_after = _desc_count(d, S_UNREAD_DOT)
        print(f"  [s6] 播种行已删={removed} / 清理后未读圆点={dots_after}（期望 0）/ 重开页={reopened}")

        ok = bool(landed and dots == 1 and count_chip and hierarchy_ok
                  and removed >= 3 and dots_after == 0)
    finally:
        try:
            # 最强零污染口径：整份回滚到写库前快照（播种期间任何异常都不外溢）
            rolled = _db_push(db_snap)
            print(f"  [s6] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s6] 兜底回滚异常: {type(e).__name__}")
        ok_restore = prefs_write(snap.read_text(encoding="utf-8"))
        print(f"  [s6] prefs 已还原={ok_restore}")
        reset_app()
    return ok


# ============================ about/read-record（F161 达成态 + F162 摘要行/续读直达 + 分隔符修复） ============================

ACT_READ_RECORD_STATS = "io.legado.app.ui.about.ReadRecordStatsActivity"
S_RR_CONTINUE = "续读 ›"              # read_record_continue_reading
S_RR_ACHIEVED = "已达成"              # read_record_goal_achieved
S_RR_ACHIEVED_HINT = "今日目标已达成"  # read_record_goal_achieved_hint
S_RR_GOAL_PROGRESS = "今日目标"       # read_record_goal_target_progress（未达成态文案）
S_RR_STREAK = "最长连续"
S_RR_MAXDAY = "单日最高"
RR_OLD_SEPARATOR = "路"               # 修复前误用字符（页面不得再出现）
GOAL_ACHIEVED_MINUTES = 10            # < 今日已读（约 16 分钟）⇒ 达成态
GOAL_UNACHIEVED_MINUTES = 9999        # 远超今日已读 ⇒ 未达成态


def _patch_goal_minutes(xml: str, minutes: int) -> str:
    """改写 readRecordGoalConfig 的 dailyGoalMinutes（prefs 内 JSON 以 &quot; 转义）"""
    rx = re.compile(r'(dailyGoalMinutes(?:&quot;|")\s*:\s*)(\d+)')
    if rx.search(xml):
        return rx.sub(lambda m: m.group(1) + str(minutes), xml, count=1)
    item = f'<string name="readRecordGoalConfig">{{&quot;dailyGoalMinutes&quot;:{minutes}}}</string>'
    return xml.replace("</map>", item + "</map>")


def _daily_truth(workdir: Path):
    """从设备库读日聚合真值 → (最长连续天数, 单日最高毫秒)；失败返回 (None, None)"""
    db = _db_pull(workdir)
    if db is None:
        return (None, None)
    con = sqlite3.connect(str(db))
    try:
        rows = list(con.execute("select date, readTime from readRecordDaily"))
    finally:
        con.close()
    import datetime as _dt
    act = sorted({_dt.date.fromisoformat(d) for d, t in rows if t and t > 0})
    best = run = 0
    for i, day in enumerate(act):
        run = run + 1 if i > 0 and (day - act[i - 1]).days == 1 else 1
        best = max(best, run)
    mx = max([t for _, t in rows], default=0)
    return (best, mx)


def _format_during_py(ms: int) -> str:
    """复刻 formatDuring 口径（values-zh：%d天/%d小时/%d分钟/%d秒；秒仅在同一日内展示）"""
    days = ms // 86400000
    hours = (ms % 86400000) // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    out = ""
    if days > 0:
        out += f"{days}天"
    if hours > 0:
        out += f"{hours}小时"
    if minutes > 0:
        out += f"{minutes}分钟"
    if seconds > 0 and days == 0 and hours == 0:
        out += f"{seconds}秒"
    return out or "0秒"


def _collect_scroll_texts(d, max_scroll=5) -> set:
    """收集纵向滚动过程中的全部可见文本（NestedScrollView 只 dump 可见区）"""
    seen = set()
    w, h = d.window_size()
    for i in range(max_scroll):
        for label, *_ in text_nodes(dump_xml(d)):
            seen.add(label)
        d.swipe(w * 0.5, h * 0.75, w * 0.5, h * 0.35)
        time.sleep(1.0)
    for label, *_ in text_nodes(dump_xml(d)):
        seen.add(label)
    return seen


def s7_read_record_optimizations(d) -> bool:
    """阅读记录页（about/read-record）：F161 达成态徽标 + F162 热力图摘要/续读直达 + 分隔符修复

    构造通道：prefs 播种目标分钟（10 → 达成；9999 → 未达成），判定后整份还原。
    零污染：不改数据库，仅读日聚合真值作为摘要行期望值。
    """
    workdir = Path(tempfile.mkdtemp(prefix="m2rr_"))
    snap = workdir / "prefs.xml"
    if not prefs_snapshot(str(snap)):
        print("  [s7] prefs 快照失败（前置）")
        return False
    base = snap.read_text(encoding="utf-8")
    ok = False
    try:
        streak, max_ms = _daily_truth(workdir)
        expected_summary = None
        if streak is not None:
            expected_summary = f"{S_RR_STREAK} {streak} 天 · {S_RR_MAXDAY} {_format_during_py(max_ms)}"
        print(f"  [s7] 日聚合真值：最长连续={streak} 天 / 单日最高={_format_during_py(max_ms or 0)}"
              f" / 期望摘要={bool(expected_summary)}")

        # ① 达成态
        if not prefs_write(_patch_goal_minutes(base, GOAL_ACHIEVED_MINUTES)):
            print("  [s7] 达成态 prefs 写入失败")
            return False
        reset_app()
        start_act(ACT_READ_RECORD_STATS)
        time.sleep(4.0)
        texts = _collect_scroll_texts(d)
        ca.shot(d, "m2rest_s7_achieved")
        achieved_badge = S_RR_ACHIEVED in texts
        achieved_hint = any(S_RR_ACHIEVED_HINT in t for t in texts)
        summary_ok = expected_summary is not None and expected_summary in texts
        continue_ok = S_RR_CONTINUE in texts
        # 修复断言：旧错误分隔符只在「空格包围」形态下成立（书籍名自身含该字不误伤）
        meta_rows = [t for t in texts if "上次打开" in t]
        joined_rows = [t for t in meta_rows if " · " in t]
        mojibake_free = not any(f" {RR_OLD_SEPARATOR} " in t for t in texts)
        print(f"  [s7] 达成徽标={achieved_badge} / 达成文案={achieved_hint} / "
              f"热力图摘要命中={summary_ok} / 续读直达={continue_ok}")
        print(f"  [s7] 最近在读 meta 行={len(meta_rows)}（含「 · 」分隔={len(joined_rows)}）"
              f" / 旧分隔符残留={not mojibake_free}")

        # ② 未达成态（同一页面换目标，断言达成态消失且回退默认文案）
        if not prefs_write(_patch_goal_minutes(base, GOAL_UNACHIEVED_MINUTES)):
            print("  [s7] 未达成态 prefs 写入失败")
            return False
        reset_app()
        start_act(ACT_READ_RECORD_STATS)
        time.sleep(4.0)
        texts2 = _collect_scroll_texts(d)
        ca.shot(d, "m2rest_s7_unachieved")
        badge_gone = S_RR_ACHIEVED not in texts2
        progress_back = any(S_RR_GOAL_PROGRESS in t for t in texts2)
        print(f"  [s7] 未达成态：徽标消失={badge_gone} / 默认进度文案回归={progress_back}")

        ok = (achieved_badge and achieved_hint and summary_ok and continue_ok
              and mojibake_free and badge_gone and progress_back)
    finally:
        ok_restore = prefs_write(base)
        print(f"  [s7] prefs 已还原={ok_restore}")
        reset_app()
    return ok


def guarded(fn):
    def inner(d):
        try:
            return fn(d)
        except Exception as e:
            print(f"  [EXC] {type(e).__name__}: {e}")
            return False

    inner.__name__ = getattr(fn, "__name__", "step")
    return inner


STEPS = {
    "s1": guarded(s1_local_save_receipt),
    "s2": guarded(s2_applied_save_receipt),
    "s3": guarded(s3_remote_download_busy),
    "s4": guarded(s4_navbar_edit_preview),
    "s5": guarded(s5_discovery_suite_row_and_opacity),
    "s6": guarded(s6_rss_tag_hierarchy_and_unread),
    "s7": guarded(s7_read_record_optimizations),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--keep-data", action="store_true", help="保留本轮创建的测试套装（调试用）")
    ap.add_argument("--dav-url", default=None, help="覆盖 s3 的 WebDAV 地址（调试用）")
    ap.add_argument("--purge-names", default=None,
                    help="按名清理残留顶栏套装（逗号分隔；仅用于本脚本历史失败运行的沙箱残留）")
    args = ap.parse_args()

    d = connect_robust()
    since = ca.device_now()

    # 显式点名清理（仅测试包沙箱；默认不执行，避免误删用户自建套装）
    if args.purge_names:
        names = [x.strip() for x in args.purge_names.split(",") if x.strip()]
        ok_purge = True
        for n in names:
            ok_purge = _delete_pkg(d, n) and ok_purge
        print(f"[purge] 清理={ok_purge}（{len(names)} 个）")
        if (args.scenario or "").strip() == "purge":
            return 0 if ok_purge else 1

    scen = (args.scenario or "all").strip()
    targets = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"] if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()]

    ok = True
    for sid in targets:
        if sid == "s3":
            ok = ok and bool(STEPS["s3"](d))
            print(f"s3: {'PASS' if ok else 'FAIL'}")
            continue
        ok = ca.run_steps({sid: STEPS[sid]}, scenario=sid, tag_keywords=[], since_ts=since, ctx=d) and ok

    # 收尾：删除本轮创建的测试套装（零残留）
    if not args.keep_data and CREATED_PKG_NAMES:
        sc_ok = sc_purge_created(d)
        ok = ok and sc_ok

    errs = ca.logcat_errors(["AndroidRuntime"], since_ts=since)
    fatal_ok = all(v == 0 for k, v in errs.items() if k in ("FATAL EXCEPTION", "AndroidRuntime"))
    print(f"[logcat] {errs} fatal_ok={fatal_ok}")
    ok = ok and fatal_ok
    print(f"== L2 总结: {'ALL PASS' if ok else 'HAS FAIL'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())