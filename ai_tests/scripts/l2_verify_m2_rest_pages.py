# -*- coding: utf-8 -*-
"""l2_verify_m2_rest_pages.py — M2 剩余页真机 L2 验证（按落地顺序增量登记）

已覆盖：
  【config/top-bar-manage】F136① 远端套装下载忙态 + F136② 保存回执分级
    s1 本地套装保存 → 次级回执（「主题已保存到本地」）
    s2 应用中套装保存 → accent 强调回执（含「全局生效」）
    s3 远端套装「应用」→ 卡片按钮转「下载中…」+ 顶部细进度条（构造可测通道）
  【config/navigation-bar-manage】F115 编辑弹框内嵌迷你底栏预览
    s4 预览条渲染 + 布局切换（悬浮/常规/侧栏）即时重绘（像素指纹三态判定，取消即零污染）

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m2_rest_pages.py [--scenario s1|s2|s3|s4|all]
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
    """返回 [(text, top, left, cx, cy)]（含 bounds 的全部文本节点）"""
    out = []
    for m in re.finditer(
            r'<node[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        t = m.group(1)
        x1, y1, x2, y2 = map(int, m.groups()[1:])
        out.append((t, y1, x1, (x1 + x2) // 2, (y1 + y2) // 2))
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
    targets = ["s1", "s2", "s3", "s4"] if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()]

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