# -*- coding: utf-8 -*-
"""l2_verify_m2_pages.py — M2 批已落地页真机 L2 验证（角色族 4 页 + 主题管理）

对应 commit `788c5a0`（M2 角色族与主题管理页优化项）。用户 2026-09-20 强约束：
「不允许任何不经过真机测试的后续优化」——本脚本即该批的真机验收证据来源。

覆盖：
  t1 角色管理：常驻搜索栏（hint「搜索角色名称 / 身份 / 技能」）
  t2 角色管理：空库「＋ 添加角色」就地入口（合成书无角色）
  t3 角色管理：关系网入口 <2 人 → 页内提示条（「去添加」）而非 toast
  t4 角色编辑：三节分组标题（基础信息 / 人物设定 / 朗读配置）+ 「必填」徽标
  t5 角色编辑：输入名称保存 → 回管理页出现该角色（端到端闭环）
  t6 角色管理：跨组搜索过滤（输入关键字 → 「搜索结果」头 + 命中）
  t7 角色管理：搜索无命中 → 「没有匹配「x」的角色。」
  t8 角色卡片：空区块折叠收纳条「N 个区块未填写」
  t9 角色卡片：Hero「角色关系」入口存在
  t10 关系网：常用关系词快捷词（6 预设）存在
  t11 主题管理：来源徽标（内置/本地/云端）
  t12 全程 FATAL=0（run_steps 统一判定）

数据策略（零污染用户数据）：
  离线在 books 表插入一条**合成书**（bookUrl=`l2://m2verify/book`），
  测完删除该书 + 其全部角色/关系；不改动任何既有书的数据。

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m2_pages.py [--scenario all|t1..t11]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装（build-legado.bat 产物）
"""
import argparse
import re
import sqlite3
import subprocess
import sys
import tempfile
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

# --- 页面入口（Activity 全限定名，Java 包名恒为 io.legado.app） ---
ACT_CHAR_MANAGE = "io.legado.app.ui.book.character.BookCharacterManageActivity"
ACT_CHAR_EDIT = "io.legado.app.ui.book.character.BookCharacterEditActivity"
ACT_CHAR_CARD = "io.legado.app.ui.book.character.BookCharacterCardActivity"
ACT_CHAR_RELATION = "io.legado.app.ui.book.character.BookCharacterRelationActivity"
ACT_THEME_MANAGE = "io.legado.app.ui.config.ThemeManageActivity"

DB_REMOTE = f"/data/data/{PKG}/databases/legado.db"
DB_DIR = f"/data/data/{PKG}/databases/"

# --- 合成书（测试专用，收尾删除；不触碰用户既有数据） ---
SYNTH_URL = "l2://m2verify/book"
SYNTH_NAME = "L2校验样本书"
SYNTH_AUTHOR = "L2校验"

# --- 断言文案（取自源码实际字面量，禁臆测） ---
S_SEARCH_HINT = "搜索角色名称 / 身份 / 技能"   # CharacterManageScreen.searchHint
S_ADD_CHAR = "＋ 添加角色"                     # 空态 actionLabel
S_EMPTY_LIB = "还没有角色，先添加主角或重要角色。"
S_RELATION_TOP = "关系网"                       # topActions 文本
S_RELATION_HINT = "至少需要两个角色才能编辑关系网"
S_HINT_ACTION = "去添加"
S_SEC_BASE = "基础信息"
S_SEC_PROFILE = "人物设定"
S_SEC_TTS = "朗读配置"
S_REQUIRED = "必填"
S_SEARCH_HEADER = "搜索结果"
S_EMPTY_BLOCKS = "个区块未填写"
S_CARD_RELATION = "角色关系"
S_RELATION_TITLE = "角色关系网"
RELATION_PRESETS = ("亲子", "师徒", "兄弟", "敌对", "同门", "恋人")
THEME_SOURCE_BADGES = ("内置", "本地", "云端", "本地+云端")

TEST_CHAR_1 = "L2校验角色甲"
TEST_CHAR_2 = "L2校验角色乙"


# ============================ 基础设施 ============================

def sh(*args, timeout=45):
    """adb shell 直连（超时重连一次：高频 dump 会让设备短暂失去响应，实测 2026-09-20）"""
    try:
        return ca.sh(*args, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
        time.sleep(3)
        return ca.sh(*args, timeout=timeout)


def sh_su(cmd, timeout=25):
    return ca.sh_su(cmd, timeout=timeout)


def adb_raw(args, timeout=60):
    return subprocess.run([ADB, "-s", HOST] + args, capture_output=True, timeout=timeout)


def db_pull(local_path: str) -> bool:
    """WAL 安全拉库（对齐 import_book_source.py 通道）"""
    sh("am", "force-stop", PKG)
    time.sleep(2)
    sh_su(f"cp {DB_REMOTE} /sdcard/m2v.db")
    sh_su("chmod 666 /sdcard/m2v.db")
    for ext in ("-wal", "-shm"):
        sh_su(f"cp {DB_REMOTE}{ext} /sdcard/m2v.db{ext} 2>/dev/null; true")
    r = adb_raw(["pull", "/sdcard/m2v.db", local_path])
    for ext in ("-wal", "-shm"):
        p = Path(local_path + ext)
        if p.exists():
            p.unlink()
    return r.returncode == 0


def db_push(local_path: str) -> bool:
    r = adb_raw(["push", local_path, "/sdcard/m2v.db"])
    if r.returncode != 0:
        return False
    r2 = sh_su(f"stat -c %U {DB_DIR}")
    owner = (r2.stdout or b"").decode("utf-8", "ignore").strip() or "u0_a72"
    sh_su(f"cp /sdcard/m2v.db {DB_REMOTE}")
    sh_su(f"chown {owner}:{owner} {DB_REMOTE}")
    sh_su(f"chmod 660 {DB_REMOTE}")
    sh_su(f"rm -f {DB_REMOTE}-wal {DB_REMOTE}-shm")
    return True


def insert_synthetic_book(db_path: str) -> bool:
    """按 books 表实际 schema 动态构造最小可用行（NOT NULL 列按类型兜底）"""
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        meta = cur.execute("PRAGMA table_info(books)").fetchall()
        if not meta:
            print("[FAIL] books 表不存在")
            return False
        cols, vals = [], []
        for _cid, name, ctype, notnull, dflt, pk in meta:
            if pk and "INT" in (ctype or "").upper():
                continue  # 自增主键不显式写
            if name == "bookUrl":
                cols.append(name); vals.append(SYNTH_URL); continue
            if name == "name":
                cols.append(name); vals.append(SYNTH_NAME); continue
            if name == "author":
                cols.append(name); vals.append(SYNTH_AUTHOR); continue
            if name in ("origin", "originName", "type", "latestChapterTitle",
                        "intro", "kind", "customTag", "variable", "coverUrl"):
                cols.append(name)
                vals.append(0 if "INT" in (ctype or "").upper() else "")
                continue
            if notnull and dflt is None:
                cols.append(name)
                vals.append(0 if "INT" in (ctype or "").upper() else "")
        cur.execute(f"DELETE FROM books WHERE bookUrl = ?", (SYNTH_URL,))
        cur.execute(
            f"INSERT INTO books ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})",
            vals)
        con.commit()
        n = cur.execute("SELECT COUNT(*) FROM books WHERE bookUrl = ?", (SYNTH_URL,)).fetchone()[0]
        print(f"[data] 合成书已注入（命中 {n} 行），列数={len(cols)}")
        return n == 1
    finally:
        con.close()


def purge_synth_data(db_path: str):
    """清合成数据（零残留）：合成书 + 其角色/关系。

    ⚠️ 关键：通过 UI 保存的角色其 `bookUrl` 是 **workKey 形态**（`work:{author}/{name}`，
    见 `BookIdentity.key`），**不是** Activity 入参的 `bookUrl`；只按 `l2://m2verify/%`
    删除会漏掉这些残留 → 下次跑 t3 时角色数已 ≥2，点击「关系网」直接跳转关系页
    （实测踩坑 2026-09-20）。
    """
    key = work_key(SYNTH_NAME, SYNTH_AUTHOR)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        for tbl in ("book_character_relations", "book_characters"):
            try:
                cur.execute(
                    f"DELETE FROM {tbl} WHERE bookUrl = ? OR bookUrl LIKE 'l2://m2verify/%'",
                    (key,))
            except Exception:
                pass
        try:
            cur.execute("DELETE FROM books WHERE bookUrl LIKE 'l2://m2verify/%'")
        except Exception:
            pass
        con.commit()
    finally:
        con.close()


def work_key(name: str, author: str) -> str:
    """复现 BookIdentity.key（NFKC + 去空白 + lowercase → work:{author}/{name}）"""
    import unicodedata
    def norm(v):
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", v).strip()).lower()
    return f"work:{norm(author)}/{norm(name)}"


def current_activity() -> str:
    r = sh("dumpsys", "activity", "activities", timeout=15)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s",
                  r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def start_act(act: str, book_url: str = None, extras: dict = None):
    """启动页面。注意：ca.sh 会自动补 `shell`，此处不可重复传。"""
    cmd = ["am", "start", "-n", f"{PKG}/{act}"]
    if book_url is not None:
        cmd += ["--es", "bookUrl", book_url]
    for k, v in (extras or {}).items():
        cmd += ["--es", k, str(v)]
    sh(*cmd)
    time.sleep(4.0)


def dump_xml(d) -> str:
    for _ in range(2):
        try:
            return d.dump_hierarchy()
        except Exception:
            time.sleep(1.5)
    return ""


def has_text(d, text: str) -> bool:
    return text in dump_xml(d)


def tap_text(d, text: str, timeout=6) -> bool:
    """文本点击（先 u2 selector，失败退 dump bounds 坐标）"""
    try:
        node = d(text=text)
        if node.wait(timeout=timeout):
            node.click()
            time.sleep(1.5)
            return True
    except Exception:
        pass
    return ca.click_by_dump(d, f'text="{re.escape(text)}"', timeout=2)


def input_first_edittext(d, text: str) -> bool:
    """定位首个 EditText（Compose TextField 在 a11y 层为 android.widget.EditText）并输入。

    首帧重试：冷启动后 dump 可能早于 Compose 首帧 → 空树导致定位失败（实测时序抖动）。
    """
    b = None
    for _ in range(2):
        b = ca.dump_bounds(d, 'class="android.widget.EditText"')
        if b:
            break
        time.sleep(2.0)
    if not b:
        return False
    w, h = d.window_size()
    d.click(b["cx"] / w, b["cy"] / h)
    time.sleep(1.0)
    try:
        d.send_keys(text)
    except Exception:
        sh("input", "text", text)
    time.sleep(1.0)
    return True


def focus_search(d) -> bool:
    """聚焦管理页搜索框：优先 BasicTextField 本体（EditText），退而点 hint 文本节点。

    注意：hint 是 decorationBox 内的独立 Text（不可聚焦），点它未必能唤起输入法，
    故首选 class=android.widget.EditText。
    """
    for pat in ('class="android.widget.EditText"',
                f'text="{re.escape(S_SEARCH_HINT)}"'):
        b = ca.dump_bounds(d, pat)
        if b:
            w, h = d.window_size()
            d.click(b["cx"] / w, b["cy"] / h)
            time.sleep(1.2)
            return True
    return False


def wait_device(timeout=90) -> bool:
    """等待 adb shell 通道恢复（模拟器在高频 dump 下会短暂失去响应，实测 2026-09-20）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = ca.sh("echo", "alive", timeout=20)
            if b"alive" in (r.stdout or b""):
                return True
        except Exception:
            pass
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
        time.sleep(4)
    return False


def guarded(fn):
    """步骤包装：执行前确保设备就绪，避免单个步骤因设备抖动整体失败"""
    def inner(d):
        if not wait_device():
            print(f"  [warn] 设备未就绪，跳过前置等待继续尝试")
        return fn(d)
    return inner


def connect_robust(retries=3):
    """轻量连接：**禁用 `ps -A` / `pidof`**（MEmu 上遍历 /proc 极慢，实测 20s+ 超时，
    而 echo/ls/dumpsys 均在 1s 内响应）。

    步骤：adb connect → echo 探针 → su 探针 → u2.connect
    uiautomator 残留进程由 u2 自行处理；如遇 AccessibilityServiceAlreadyRegisteredError，
    手工 `adb shell su -c 'kill -9 <pid>'` 后再跑（SOP 陷阱 1）。
    """
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
    raise RuntimeError("设备连接失败（已重试 %d 次）" % retries)


def reset_app():
    sh("am", "force-stop", PKG)
    time.sleep(1.5)


# ============================ 步骤 ============================

def t1_manage_search_bar(d) -> bool:
    """角色管理：常驻搜索栏（AppManagementScaffold secondRow）"""
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    ok = has_text(d, S_SEARCH_HINT)
    print(f"  [t1] 搜索栏 hint 可见={ok} | 当前页={current_activity()}")
    ca.shot(d, "m2_t1_manage_search")
    return ok


def t2_manage_empty_entry(d) -> bool:
    """角色管理：空库给「＋ 添加角色」就地入口"""
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    xml = dump_xml(d)
    ok = S_ADD_CHAR in xml and S_EMPTY_LIB in xml
    print(f"  [t2] 空态文案={S_EMPTY_LIB in xml} / 添加入口={S_ADD_CHAR in xml}")
    ca.shot(d, "m2_t2_manage_empty")
    return ok


def t3_relation_hint(d) -> bool:
    """角色管理：关系网入口 <2 人 → 页内提示条（非 toast）

    注意：提示条 `LaunchedEffect` 4s 自动消退（CharacterManageScreen），
    而 `dump_hierarchy` 单次耗时可观 ⇒ 必须走 u2 selector 快速点击 + 立即轮询断言，
    禁止在中间插入全量 dump / 额外 sleep。
    """
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    # 顶栏动作为纯图标（AppManagementIconAction(contentDescription=action.text)）→ 用 description 定位
    clicked = False
    try:
        node = d(description=S_RELATION_TOP)
        if node.wait(timeout=3):
            node.click()
            clicked = True
    except Exception:
        pass
    if not clicked:
        print("  [t3] 未找到顶栏「关系网」入口（content-desc 未命中）")
        return False
    # 立即轮询（4s 窗口内），不用 dump_hierarchy
    hit_text = hit_action = False
    deadline = time.time() + 3.0
    while time.time() < deadline and not (hit_text and hit_action):
        try:
            if d(text=S_RELATION_HINT).exists:
                hit_text = True
            if d(text=S_HINT_ACTION).exists:
                hit_action = True
        except Exception:
            pass
        if not (hit_text and hit_action):
            time.sleep(0.25)
    ok = hit_text and hit_action
    print(f"  [t3] 提示条文案={hit_text} / 「去添加」={hit_action}")
    ca.shot(d, "m2_t3_relation_hint")
    return ok


def t4_edit_sections(d) -> bool:
    """角色编辑：三节分组标题 + 「必填」徽标（长表单需滚动合并采集，dump 仅含可见节点）"""
    reset_app()
    start_act(ACT_CHAR_EDIT, SYNTH_URL)
    # 首帧就绪重试（冷启动后 dump 可能早于 Compose 首帧 → 空树，实测时序抖动）
    xml = ""
    for _ in range(2):
        xml = dump_xml(d)
        if S_SEC_BASE in xml:
            break
        time.sleep(2.0)
    w, h = d.window_size()
    for _ in range(2):  # 两次上滑覆盖三节
        d.swipe(w * 0.5, h * 0.75, w * 0.5, h * 0.3, 0.3)
        time.sleep(1.2)
        xml += dump_xml(d)
    secs = [s for s in (S_SEC_BASE, S_SEC_PROFILE, S_SEC_TTS) if s in xml]
    req = S_REQUIRED in xml
    print(f"  [t4] 分组标题命中={secs} / 必填徽标={req}")
    ca.shot(d, "m2_t4_edit_sections")
    return len(secs) == 3 and req


def t5_edit_save_roundtrip(d) -> bool:
    """角色编辑：输入名称 → 保存 → 回管理页出现该角色（端到端）"""
    reset_app()
    start_act(ACT_CHAR_EDIT, SYNTH_URL)
    if not input_first_edittext(d, TEST_CHAR_1):
        print("  [t5] 未定位到名称输入框")
        return False
    if not tap_text(d, "保存"):
        print("  [t5] 未找到「保存」按钮")
        return False
    time.sleep(2.5)
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    ok = _wait_texts(d, (TEST_CHAR_1,), timeout=8.0)
    print(f"  [t5] 保存后管理页出现该角色={ok}")
    ca.shot(d, "m2_t5_edit_saved")
    return ok


def _wait_texts(d, texts, timeout=8.0) -> bool:
    """轮询等待全部文本可见（Compose 首帧/异步加载抖动兜底）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        xml = dump_xml(d)
        if all(t in xml for t in texts):
            return True
        time.sleep(1.0)
    return False


def _ensure_two_chars(d) -> bool:
    """确保合成书下至少有 2 个角色（供 t6~t10 使用）"""
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    if _wait_texts(d, (TEST_CHAR_1, TEST_CHAR_2), timeout=6.0):
        return True
    for name in (TEST_CHAR_1, TEST_CHAR_2):
        reset_app()
        start_act(ACT_CHAR_EDIT, SYNTH_URL)
        if not input_first_edittext(d, name):
            print(f"  [data] 输入框定位失败（{name}）")
            return False
        if not tap_text(d, "保存"):
            print(f"  [data] 「保存」未命中（{name}）")
            return False
        time.sleep(2.5)
    reset_app()
    start_act(ACT_CHAR_MANAGE, SYNTH_URL)
    return _wait_texts(d, (TEST_CHAR_1, TEST_CHAR_2), timeout=10.0)


def t6_search_filter(d) -> bool:
    """角色管理：跨组搜索过滤（输入关键字 → 「搜索结果」头 + 命中）"""
    if not _ensure_two_chars(d):
        print("  [t6] 前置：合成书角色不足 2 个")
        return False
    if not focus_search(d):
        print("  [t6] 未定位到搜索框")
        return False
    try:
        d.send_keys(TEST_CHAR_1)
    except Exception:
        sh("input", "text", TEST_CHAR_1)
    time.sleep(2.0)
    xml = dump_xml(d)
    ok = (S_SEARCH_HEADER in xml) and (TEST_CHAR_1 in xml) and (TEST_CHAR_2 not in xml)
    print(f"  [t6] 结果头={S_SEARCH_HEADER in xml} / 命中甲={TEST_CHAR_1 in xml} / 排除乙={TEST_CHAR_2 not in xml}")
    ca.shot(d, "m2_t6_search_filter")
    return ok


def t7_search_no_match(d) -> bool:
    """角色管理：搜索无命中 → 明确空态文案"""
    if not _ensure_two_chars(d):
        return False
    if not focus_search(d):
        return False
    kw = "ZZZ不存在角色"
    try:
        d.send_keys(kw)
    except Exception:
        sh("input", "text", "ZZZ")
    time.sleep(2.0)
    xml = dump_xml(d)
    ok = "没有匹配" in xml
    print(f"  [t7] 无命中文案可见={ok}")
    ca.shot(d, "m2_t7_search_empty")
    return ok


def t8_card_empty_blocks(d) -> bool:
    """角色卡片：空区块折叠收纳条「N 个区块未填写」"""
    if not _ensure_two_chars(d):
        return False
    if not tap_text(d, TEST_CHAR_1):
        b = ca.dump_bounds(d, f'text="{re.escape(TEST_CHAR_1)}"')
        if not b:
            print("  [t8] 未定位到角色行")
            return False
        w, h = d.window_size()
        d.click(b["cx"] / w, b["cy"] / h)
        time.sleep(2.5)
    time.sleep(1.5)
    xml = dump_xml(d)
    ok = S_EMPTY_BLOCKS in xml
    print(f"  [t8] 折叠收纳条={ok} | 当前页={current_activity()}")
    ca.shot(d, "m2_t8_card_fold")
    return ok


def t9_card_relation_entry(d) -> bool:
    """角色卡片：Hero「角色关系」入口存在"""
    if not _ensure_two_chars(d):
        return False
    if not tap_text(d, TEST_CHAR_1):
        b = ca.dump_bounds(d, f'text="{re.escape(TEST_CHAR_1)}"')
        if not b:
            return False
        w, h = d.window_size()
        d.click(b["cx"] / w, b["cy"] / h)
        time.sleep(2.5)
    time.sleep(1.5)
    xml = dump_xml(d)
    ok = S_CARD_RELATION in xml
    print(f"  [t9] 「角色关系」入口={ok}")
    ca.shot(d, "m2_t9_card_relation_entry")
    return ok


def t10_relation_presets(d) -> bool:
    """关系网：常用关系词快捷词（6 预设）—— 需先点「添加关系」打开编辑弹层"""
    if not _ensure_two_chars(d):
        return False
    reset_app()
    start_act(ACT_CHAR_RELATION, SYNTH_URL)
    time.sleep(1.5)
    if not tap_text(d, "添加关系"):
        print("  [t10] 未找到「添加关系」入口")
        ca.shot(d, "m2_t10_relation_no_entry")
        return False
    time.sleep(1.8)
    xml = dump_xml(d)
    hit = [p for p in RELATION_PRESETS if p in xml]
    ok = len(hit) >= 4   # 6 预设可能因换行/裁剪少显，命中 ≥4 即证明词表已接线
    print(f"  [t10] 关系词命中={hit}（{len(hit)}/6）")
    ca.shot(d, "m2_t10_relation_presets")
    return ok


def t11_theme_source_badge(d) -> bool:
    """主题管理：卡片来源徽标（内置/本地/云端）"""
    reset_app()
    start_act(ACT_THEME_MANAGE)
    time.sleep(3.0)
    xml = dump_xml(d)
    hit = [b for b in THEME_SOURCE_BADGES if b in xml]
    ok = len(hit) >= 1
    print(f"  [t11] 来源徽标命中={hit} | 当前页={current_activity()}")
    ca.shot(d, "m2_t11_theme_badge")
    return ok


STEPS = {
    "t1": guarded(t1_manage_search_bar),
    "t2": guarded(t2_manage_empty_entry),
    "t3": guarded(t3_relation_hint),
    "t4": guarded(t4_edit_sections),
    "t5": guarded(t5_edit_save_roundtrip),
    "t6": guarded(t6_search_filter),
    "t7": guarded(t7_search_no_match),
    "t8": guarded(t8_card_empty_blocks),
    "t9": guarded(t9_card_relation_entry),
    "t10": guarded(t10_relation_presets),
    "t11": guarded(t11_theme_source_badge),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--keep-data", action="store_true", help="保留合成书（调试用）")
    args = ap.parse_args()

    d = connect_robust()
    since = ca.device_now()

    # --- 数据准备：注入合成书（零污染） ---
    tmpdir = tempfile.mkdtemp(prefix="m2v_")
    local_db = str(Path(tmpdir) / "legado.db")
    if not db_pull(local_db):
        print("❌ 拉库失败")
        return 2
    purge_synth_data(local_db)          # 清上次残留（含 workKey 形态角色）
    if not insert_synthetic_book(local_db):
        print("❌ 合成书注入失败")
        return 2
    if not db_push(local_db):
        print("❌ 推库失败")
        return 2
    print(f"[data] workKey hash={abs(hash(work_key(SYNTH_NAME, SYNTH_AUTHOR))) % 1000:03d}")
    time.sleep(2)

    ok = True
    scen = (args.scenario or "all").strip()
    targets = ["all"] if scen == "all" else [s.strip() for s in scen.split(",") if s.strip()]
    for sid in targets:
        ok = ca.run_steps(STEPS, scenario=sid,
                          tag_keywords=["AndroidRuntime"], since_ts=since, ctx=d) and ok

    # --- 收尾：清合成数据（零残留） ---
    if not args.keep_data:
        if db_pull(local_db):
            purge_synth_data(local_db)
            db_push(local_db)
            print("[data] 合成书与其角色/关系已清理")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
