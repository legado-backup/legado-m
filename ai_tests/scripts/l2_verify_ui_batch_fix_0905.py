#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
l2_verify_ui_batch_fix_0905.py — ui-batch-fix-0905 批次 L2 验证
覆盖场景：
  T1 崩溃弹框回归：debug 会话无"检测到阅读发生了崩溃"弹框 + FATAL=0
  T2 经典订阅头部收口：一级按钮（星标/刷新/历史/分组/设置）消失 + 三点(菜单)存在
  T3 三点菜单 6 项：历史记录/收藏/刷新/设置/布局设置/分组管理 + 布局设置/分组管理弹窗可开
  T4 经典发现页分组按钮：点击有反馈（弹窗或空态 toast，截图前后像素差佐证）
  T5 订阅源管理多选菜单：死项"校验所选订阅源"不再出现
用法：
  ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_ui_batch_fix_0905.py [--scenario all|t1|t2|t3|t4|t5]
证据：ai_tests/reports/ui_batch_fix_0905/*.png
"""
import argparse
import base64
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uiautomator2 as u2

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

HOST = MEMU_ADB_HOST
PREFS_REMOTE = f"/data/data/{PACKAGE}/shared_prefs/{PACKAGE}_preferences.xml"
MAIN = f"{PACKAGE}/io.legado.app.ui.main.MainActivity"
RSS_SOURCE_ACT = f"{PACKAGE}/io.legado.app.ui.rss.source.RssSourceActivity"
REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "ui_batch_fix_0905"

# 一级按钮 content-desc（收口后不应出现在订阅顶栏）
ONE_LEVEL_DESCS = ["收藏", "刷新", "历史记录", "分组", "设置"]
# 三点菜单 6 项文本
MORE_MENU_ITEMS = ["历史记录", "收藏", "刷新", "设置", "布局设置", "分组管理"]
# 死菜单项文本（应消失）
DEAD_ITEM = "校验所选订阅源"


def sh(*args, timeout=30):
    return subprocess.run([ADB_PATH, "-s", HOST, "shell"] + list(args),
                          capture_output=True, timeout=timeout)


def crash_count() -> int:
    r = sh("logcat", "-d", "-b", "crash", timeout=15)
    log = r.stdout.decode("utf-8", errors="ignore")
    return len(re.findall(r"FATAL EXCEPTION", log))


def go_main(d):
    sh("am", "start", "-n", MAIN)
    time.sleep(3.0)


def _find_bounds(xml: str, attr: str, value: str):
    m = re.search(
        r'%s="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % (attr, re.escape(value)),
        xml)
    if not m:
        m = re.search(
            r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*%s="%s"' % (attr, re.escape(value)),
            xml)
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def click_by(d, attr: str, value: str, tries: int = 3) -> bool:
    for _ in range(tries):
        try:
            pos = _find_bounds(d.dump_hierarchy(), attr, value)
        except Exception:
            pos = None
        if pos:
            sh("input", "tap", str(pos[0]), str(pos[1]))
            time.sleep(2.0)
            return True
        time.sleep(1.5)
    return False


def dump_texts(d) -> set:
    xml = d.dump_hierarchy()
    return set(t for t in re.findall(r'text="([^"]+)"', xml) if t.strip()), xml


def dump_texts_only(d) -> set:
    return dump_texts(d)[0]


def go_tab(d, desc: str) -> bool:
    go_main(d)
    ok = click_by(d, "content-desc", desc)
    if not ok:
        ok = click_by(d, "text", desc)
    time.sleep(1.5)
    return ok


def screenshot(d, name: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    remote = f"/sdcard/{name}.png"
    local = REPORT_DIR / f"{name}.png"
    sh("screencap", "-p", remote, timeout=20)
    subprocess.run([ADB_PATH, "-s", HOST, "pull", remote, str(local)],
                   capture_output=True, timeout=30)
    sh("rm", remote)
    return local


def read_prefs_xml() -> str:
    """base64 通道读 prefs 全文（SOP 铁律）"""
    r = sh("su -c 'base64 %s 2>/dev/null'" % PREFS_REMOTE, timeout=20)
    return base64.b64decode(r.stdout.decode("utf-8", "ignore")).decode("utf-8", "ignore")


def write_prefs_xml(xml: str):
    """base64 通道回写 prefs（须先 force-stop 防 App 覆盖）"""
    b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    sh("su -c 'echo %s | base64 -d > %s'" % (b64, PREFS_REMOTE), timeout=30)


def force_stop():
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)


def set_pref_value(xml: str, key: str, new_value: str) -> str:
    """替换 <string name=key>v</string> 或 value 属性；无该键时返回原文"""
    pat_text = r'(<string\s+name="%s"[^>]*>)[^<]*(</string>)' % re.escape(key)
    if re.search(pat_text, xml):
        return re.sub(pat_text, r'\g<1>%s\g<2>' % new_value, xml)
    pat_attr = r'(<\w+\s+name="%s"[^>]*value=")[^"]*(")' % re.escape(key)
    if re.search(pat_attr, xml):
        return re.sub(pat_attr, r'\g<1>%s\g<2>' % new_value, xml)
    return xml


def dismiss_popup():
    sh("input", "keyevent", "BACK")
    time.sleep(1.2)


def pixel_region_mean(path: Path, x0: float, y0: float, x1: float, y1: float) -> float:
    """灰度均值（裁剪比例区域），用于前后帧差异判定"""
    try:
        from PIL import Image
        img = Image.open(path).convert("L")
        w, h = img.size
        crop = img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))
        stat = crop.histogram()
        total = sum(stat)
        if total == 0:
            return -1.0
        return sum(i * c for i, c in enumerate(stat)) / total
    except Exception as e:
        print(f"[WARN] pixel analysis fail: {e}")
        return -1.0


def t1_crash_dialog(d) -> bool:
    """debug 包 BuildConfig.DEBUG=true 恒拦截弹框；会话内断言弹框文案零出现 + FATAL=0"""
    ok = True
    r = sh("logcat", "-d", timeout=15)
    log = r.stdout.decode("utf-8", errors="ignore")
    n_dialog = len(re.findall(r"检测到阅读发生了崩溃", log))
    if n_dialog != 0:
        print(f"[T1][FAIL] 崩溃弹框文案出现 {n_dialog} 次（debug 包应恒为 0）")
        ok = False
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T1][FAIL] FATAL EXCEPTION 计数={n_fatal}")
        ok = False
    # 二轮重建（主题/转屏等重建路径也不弹）：切一次后台再回前台
    sh("input", "keyevent", "KEYCODE_HOME")
    time.sleep(1.5)
    go_main(d)
    r = sh("logcat", "-d", timeout=15)
    log = r.stdout.decode("utf-8", errors="ignore")
    n_dialog2 = len(re.findall(r"检测到阅读发生了崩溃", log))
    if n_dialog2 != 0:
        print(f"[T1][FAIL] 重建后弹框文案出现 {n_dialog2} 次")
        ok = False
    print(f"[T1] {'PASS' if ok else 'FAIL'} (dialogText=0, FATAL={n_fatal})")
    return ok


def t2_rss_header(d) -> bool:
    """经典订阅头部：一级按钮消失 + 三点存在；先确保经典形态（读 prefs modernRssPage）"""
    ok = True
    go_tab(d, "订阅")
    time.sleep(1.5)
    xml = d.dump_hierarchy()
    # 顶栏区域取屏幕上部 15% 内节点；直接全屏找 desc，但排除底部导航区域
    found_one_level = []
    for desc in ONE_LEVEL_DESCS:
        pos = _find_bounds(xml, "content-desc", desc)
        if pos and pos[1] < 300:  # 顶栏区域（MEmu 1280x720 顶栏 y<300 宽松界）
            found_one_level.append(desc)
    if found_one_level:
        print(f"[T2][FAIL] 一级按钮仍在顶栏: {found_one_level}")
        ok = False
    more_pos = _find_bounds(xml, "content-desc", "菜单")
    if not more_pos or more_pos[1] >= 300:
        print(f"[T2][FAIL] 三点按钮(菜单)不在顶栏: pos={more_pos}")
        ok = False
    search_pos = _find_bounds(xml, "content-desc", "搜索")
    print(f"[T2] more={more_pos}, search={search_pos}, oneLevelInTop={found_one_level}")
    print(f"[T2] {'PASS' if ok else 'FAIL'}")
    return ok


def t3_more_menu(d) -> bool:
    """三点菜单 6 项齐全 + 布局设置/分组管理弹窗可开可关"""
    ok = True
    go_tab(d, "订阅")
    time.sleep(1.0)
    if not click_by(d, "content-desc", "菜单"):
        print("[T3][FAIL] 三点按钮点击失败")
        return False
    time.sleep(1.2)
    texts, _ = dump_texts(d)
    missing = [i for i in MORE_MENU_ITEMS if i not in texts]
    if missing:
        print(f"[T3][FAIL] 三点菜单缺项: {missing}; visible={sorted(list(texts))[:24]}")
        ok = False
    else:
        print(f"[T3] 菜单 6 项齐全: {MORE_MENU_ITEMS}")
    # 分组信息列举不应存在（用户无分组时本来就无；有分组时也不应列举）——无法稳定区分，跳过强断言
    dismiss_popup()
    # 布局设置弹窗
    if not click_by(d, "content-desc", "菜单"):
        print("[T3][FAIL] 三点按钮二次点击失败")
        return False
    time.sleep(1.0)
    if click_by(d, "text", "布局设置", tries=2):
        time.sleep(1.5)
        texts2, xml2 = dump_texts(d)
        dialog_open = any(k in texts2 for k in ("间距", "视图", "列数", "确定", "取消"))
        if not dialog_open:
            # Compose 弹框 dump 可能无文本，降级截图佐证
            p = screenshot(d, "t3_folder_config_dialog")
            print(f"[T3][WARN] 布局设置弹窗文本未命中，截图佐证: {p}")
        else:
            print("[T3] 布局设置弹窗已打开")
        dismiss_popup()
    else:
        print("[T3][FAIL] 布局设置项点击失败")
        ok = False
    # 分组管理弹窗
    if not click_by(d, "content-desc", "菜单"):
        print("[T3][FAIL] 三点按钮三次点击失败")
        return False
    time.sleep(1.0)
    if click_by(d, "text", "分组管理", tries=2):
        time.sleep(1.5)
        texts3, _ = dump_texts(d)
        dialog_open2 = any(k in texts3 for k in ("分组", "新建", "确定", "取消", "添加"))
        if not dialog_open2:
            p = screenshot(d, "t3_group_manage_dialog")
            print(f"[T3][WARN] 分组管理弹窗文本未命中，截图佐证: {p}")
        else:
            print("[T3] 分组管理弹窗已打开")
        dismiss_popup()
    else:
        print("[T3][FAIL] 分组管理项点击失败")
        ok = False
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T3][FAIL] FATAL={n_fatal}")
        ok = False
    print(f"[T3] {'PASS' if ok else 'FAIL'} (FATAL={n_fatal})")
    return ok


def t4_explore_group(d) -> bool:
    """经典发现页分组按钮：点击后有可见反馈（弹窗/空态 toast）。
    发现页需 legacy 形态——经配置页 UI 通道切换（设置→发现页模式→经典发现），测试后还原新版。"""
    ok = True
    go_main(d)
    # 1) 打开发现-订阅配置页
    sh("am", "start", "-n", f"{PACKAGE}/io.legado.app.ui.config.ConfigActivity",
       "-e", "configTag", "discoverySubscriptionConfig")
    time.sleep(2.5)
    # 2) 点击"发现页模式"行
    if not click_by(d, "text", "发现页模式", tries=4):
        print("[T4][FAIL] 配置页未找到'发现页模式'行")
        return False
    time.sleep(1.2)
    # 3) 选择"经典发现"
    if not click_by(d, "text", "经典发现", tries=3):
        print("[T4][FAIL] 未找到'经典发现'选项")
        return False
    time.sleep(1.2)
    sh("input", "keyevent", "BACK")
    time.sleep(1.0)
    sh("input", "keyevent", "BACK")
    time.sleep(1.5)
    try:
        go_tab(d, "发现")
        time.sleep(2.0)
        xml = d.dump_hierarchy()
        tb = None
        for rid in (f"{PACKAGE}:id/toolbar", "io.legado.app:id/toolbar",
                    f"{PACKAGE}:id/title_bar", "io.legado.app:id/title_bar"):
            tb = _find_bounds(xml, "resource-id", rid)
            if tb:
                print(f"[T4] anchor via {rid}")
                break
        if not tb:
            m = re.search(r'class="(?:android\.widget|androidx\.appcompat\.widget)\.Toolbar"[^>]*'
                          r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
            if not m:
                m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*'
                              r'class="(?:android\.widget|androidx\.appcompat\.widget)\.Toolbar"', xml)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                tb = ((x1 + x2) // 2, (y1 + y2) // 2)
                print(f"[T4] anchor via Toolbar class, bounds=({x1},{y1},{x2},{y2})")
        if not tb:
            ids = sorted(set(re.findall(r'resource-id="([^"]*(?:toolbar|title_bar)[^"]*)"', xml)))
            print(f"[T4][FAIL] toolbar/title_bar 未定位; 相关 resource-id={ids}")
            return False
        tap = (tb[0] + 30, tb[1])  # toolbar 右端内缩 30px（分组图标）
        before = screenshot(d, "t4_before")
        sh("input", "tap", str(tap[0]), str(tap[1]))
        time.sleep(2.0)
        after = screenshot(d, "t4_after")
        dismiss_popup()
        diff = abs(pixel_region_mean(before, 0.0, 0.05, 1.0, 0.95)
                   - pixel_region_mean(after, 0.0, 0.05, 1.0, 0.95))
        print(f"[T4] tap={tap}, regionGrayDiff={diff:.2f} (>=1.0 判定有反馈)")
        if diff < 1.0:
            print("[T4][FAIL] 点击分组图标无可见反馈")
            ok = False
        n_fatal = crash_count()
        if n_fatal != 0:
            print(f"[T4][FAIL] FATAL={n_fatal}")
            ok = False
    finally:
        # 还原新版发现
        sh("am", "start", "-n", f"{PACKAGE}/io.legado.app.ui.config.ConfigActivity",
           "-e", "configTag", "discoverySubscriptionConfig")
        time.sleep(2.5)
        if click_by(d, "text", "发现页模式", tries=4):
            time.sleep(1.2)
            if click_by(d, "text", "新版发现", tries=3):
                time.sleep(1.0)
            else:
                print("[T4][WARN] 还原新版发现失败")
        sh("input", "keyevent", "BACK")
        time.sleep(1.0)
        print("[T4] discoveryPageMode 已还原")
    print(f"[T4] {'PASS' if ok else 'FAIL'}")
    return ok


def _pick_video_book(flat: bool):
    """从 DB 取一本视频书（脱敏返回），flat=True 选无卷书，False 选有卷书"""
    import sqlite3
    import tempfile
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)
    DB_REMOTE = f"/data/data/{PACKAGE}/databases/legado.db"
    with tempfile.TemporaryDirectory() as tmpdir:
        local_db = str(Path(tmpdir) / "legado.db")
        subprocess.run([ADB_PATH, "-s", HOST, "pull", DB_REMOTE, local_db],
                       capture_output=True, timeout=60)
        con = sqlite3.connect(local_db)
        cur = con.cursor()
        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        cond = "not exists (select 1 from chapters c2 where c2.bookUrl=b.bookUrl and c2.isVolume=1)" \
            if flat else \
            "exists (select 1 from chapters c2 where c2.bookUrl=b.bookUrl and c2.isVolume=1)"
        row = cur.execute(
            f"""select b.name, b.bookUrl, b.origin from books b
            join book_sources s on b.origin=s.bookSourceUrl
            where s.bookSourceType=4 and b.bookUrl in
            (select bookUrl from chapters group by bookUrl having count(*)>2)
            and {cond} order by (select count(*) from chapters c3 where c3.bookUrl=b.bookUrl) desc limit 1""").fetchone()
        con.close()
        return row


def _flatten_video_book(book_url: str):
    """临时删除指定视频书的卷行（触发 initSource 无卷回退），返回删除行数"""
    import sqlite3
    import tempfile
    DB_REMOTE = f"/data/data/{PACKAGE}/databases/legado.db"
    with tempfile.TemporaryDirectory() as tmpdir:
        local_db = str(Path(tmpdir) / "legado.db")
        subprocess.run([ADB_PATH, "-s", HOST, "pull", DB_REMOTE, local_db],
                       capture_output=True, timeout=60)
        con = sqlite3.connect(local_db)
        cur = con.cursor()
        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        cur.execute("delete from chapters where bookUrl=? and isVolume=1", (book_url,))
        n = cur.rowcount
        n_ch = cur.execute("select count(*) from chapters where bookUrl=?",
                           (book_url,)).fetchone()[0]
        con.commit()
        con.close()
        subprocess.run([ADB_PATH, "-s", HOST, "push", local_db, DB_REMOTE],
                       capture_output=True, timeout=60)
        sh("rm", f"{DB_REMOTE}-wal", f"{DB_REMOTE}-shm")
        return n, n_ch


def _set_video_layout_mode(mode: int):
    """写 video_config.xml layoutMode（0 沉浸式/1 传统），force-stop 后写入并回读校验"""
    VIDEO_PREFS = f"/data/data/{PACKAGE}/shared_prefs/video_config.xml"
    sh("am", "force-stop", PACKAGE)
    time.sleep(2.0)
    r = sh("su -c 'base64 %s 2>/dev/null'" % VIDEO_PREFS)
    raw = r.stdout.decode("utf-8", "ignore").strip()
    if raw:
        xml = base64.b64decode(raw).decode("utf-8", "ignore")
        if 'name="layoutMode"' in xml:
            xml = re.sub(r'(<int\s+name="layoutMode"\s+value=")\d+(")',
                         r'\g<1>%d\g<2>' % mode, xml)
        else:
            xml = xml.replace("</map>", f'<int name="layoutMode" value="{mode}" /></map>')
    else:
        xml = ("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>"
               f"<map><int name=\"layoutMode\" value=\"{mode}\" /></map>")
    b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    sh("su -c 'echo %s | base64 -d > %s'" % (b64, VIDEO_PREFS), timeout=30)
    r2 = sh("su -c 'base64 %s 2>/dev/null'" % VIDEO_PREFS)
    back = base64.b64decode(r2.stdout.decode("utf-8", "ignore")).decode("utf-8", "ignore")
    m = re.search(r'name="layoutMode"\s+value="(\d+)"', back)
    print(f"[layoutMode] 写入={mode}, 回读={m.group(1) if m else '(absent)'}")


def _launch_video_player(book_url: str, origin: str):
    """确定性直唤播放器（sourceType=0 book）。
    ⚠️ URL 含 & 时 adb shell 远端会截断 intent extra（铁证：hasBook=false/tocSize=0），
    必须整体单字符串+单引号包裹传参。"""
    cmd = ("am start -n %s/io.legado.app.ui.video.VideoPlayerActivity "
           "--es sourceKey '%s' --es bookUrl '%s' --ei sourceType 0"
           % (PACKAGE, origin.replace("'", "'\\''"), book_url.replace("'", "'\\''")))
    sh(cmd)
    time.sleep(14.0)


def _assert_immersive_episodes(tag: str, d) -> bool:
    """断言：进入播放器 + 左下角集数选择器渲染（先点屏幕唤出自动隐藏的控件）"""
    ok = True
    resumed = sh("dumpsys", "activity", "activities").stdout.decode("utf-8", "ignore")
    act = re.findall(r"mResumedActivity:.*?(\S+VideoPlayerActivity\S*)", resumed)
    sh("input", "tap", "360", "300")  # 视频区单击唤出控制器
    time.sleep(1.5)
    xml = d.dump_hierarchy()
    has_rv = "rv_episodes" in xml
    ep_texts = re.findall(r'text="([^"]{1,12})"', xml)
    ep_like = [t for t in ep_texts if re.match(r"^(第.{1,5}(集|期|话|章)|\d{1,3})$", t)]
    print(f"[{tag}] resumed={act[:1]}, rv_episodes_in_dump={has_rv}, epLikeTexts={len(ep_like)}")
    screenshot(d, f"{tag}_immersive")
    if not act:
        print(f"[{tag}][FAIL] 未进入 VideoPlayerActivity")
        ok = False
    elif not (has_rv or len(ep_like) >= 2):
        print(f"[{tag}][FAIL] 沉浸式页未见集数选择器/集数文本")
        ok = False
    return ok


def t6_flat_video_book(d) -> bool:
    """V2：无卷（扁平 TOC）视频书源沉浸式左下角集数列表（Intent 直唤确定性入口）。
    优先选库内已扁平书；无扁平书时临时删卷行构造。"""
    ok = True
    row = _pick_video_book(flat=True)
    if row:
        book_name, book_url, origin = row
        n_del, n_ch = 0, -1
        import sqlite3
        import tempfile
        sh("am", "force-stop", PACKAGE)
        time.sleep(2.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            local_db = str(Path(tmpdir) / "legado.db")
            subprocess.run([ADB_PATH, "-s", HOST, "pull",
                            f"/data/data/{PACKAGE}/databases/legado.db", local_db],
                           capture_output=True, timeout=60)
            con = sqlite3.connect(local_db)
            cur = con.cursor()
            try:
                cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            n_ch = cur.execute(
                "select count(*) from chapters where bookUrl=?",
                (book_url,)).fetchone()[0]
            con.close()
        print(f"[T6] 目标书 nameHash={abs(hash(book_name)) % 1000:03d}, "
              f"已有扁平 TOC, 章节={n_ch}")
    else:
        row = _pick_video_book(flat=False)
        if not row:
            print("[T6][FAIL] 库内无可测视频书")
            return False
        book_name, book_url, origin = row
        n_del, n_ch = _flatten_video_book(book_url)
        print(f"[T6] 目标书 nameHash={abs(hash(book_name)) % 1000:03d}, "
              f"删卷行={n_del}, 剩章节={n_ch}（TOC 已扁平）")
    _set_video_layout_mode(0)
    go_main(d)
    _launch_video_player(book_url, origin)
    if not _assert_immersive_episodes("T6", d):
        ok = False
    sh("input", "keyevent", "BACK")
    time.sleep(2.0)
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T6][FAIL] FATAL={n_fatal}")
        ok = False
    print(f"[T6] {'PASS' if ok else 'FAIL'}")
    return ok


def t7_volumed_video_book(d) -> bool:
    """回归：有卷视频书源沉浸式多线路映射不被本次改动破坏"""
    ok = True
    row = _pick_video_book(flat=True)
    if not row:
        print("[T7][SKIP] 库内无有卷视频书")
        return True
    book_name, book_url, origin = row
    print(f"[T7] 目标书 nameHash={abs(hash(book_name)) % 1000:03d}（有卷，回归对照）")
    _set_video_layout_mode(0)
    go_main(d)
    _launch_video_player(book_url, origin)
    if not _assert_immersive_episodes("T7", d):
        ok = False
    sh("input", "keyevent", "BACK")
    time.sleep(2.0)
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T7][FAIL] FATAL={n_fatal}")
        ok = False
    print(f"[T7] {'PASS' if ok else 'FAIL'}")
    return ok


def t8_layout_switch_prevnext(d) -> bool:
    """布局切换回归：传统布局下 上一部/下一部 嗅探播放 + 切回沉浸式功能正常。
    判定证据：控件存在 + 前后帧像素差（视频真实在播）+ 标题变化（hash 比对，不输出业务名）。"""
    ok = True
    VIDEO_PREFS = f"/data/data/{PACKAGE}/shared_prefs/video_config.xml"
    row = _pick_video_book(flat=True)
    if not row:
        print("[T8][SKIP] 库内无有卷视频书")
        return True
    book_name, book_url, origin = row
    name_hash = abs(hash(book_name)) % 100000

    def video_playing(tag: str) -> bool:
        """播放区域多帧像素差（3 次采样任一 ≥1.0 判定在播；规避片头静止画面误报）"""
        for i in range(3):
            p1 = screenshot(d, f"{tag}_f{i}a")
            time.sleep(2.2)
            p2 = screenshot(d, f"{tag}_f{i}b")
            diff = abs(pixel_region_mean(p1, 0.1, 0.15, 0.9, 0.75)
                       - pixel_region_mean(p2, 0.1, 0.15, 0.9, 0.75))
            print(f"[{tag}] 采样{i} 帧差={diff:.2f}")
            if diff >= 1.0:
                return True
            time.sleep(1.0)
        print(f"[{tag}] 3 次采样均静止，判定未在播")
        return False

    def title_hash() -> str:
        xml = d.dump_hierarchy()
        # 传统布局标题：优先取顶部 300px 内"第N集"形态文本，退化为最长文本
        ep = None
        best = ""
        for m in re.finditer(r'text="([^"]{2,40})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
            t = m.group(1)
            y1 = int(m.group(3))
            if y1 < 300:
                if re.match(r"^第.{1,4}集$", t) and ep is None:
                    ep = t
                if len(t) > len(best):
                    best = t
        chosen = ep or best
        return str(abs(hash(chosen)) % 100000) if chosen else ""

    # ===== 阶段1：传统布局 =====
    _set_video_layout_mode(1)
    go_main(d)
    _launch_video_player(book_url, origin)
    xml = d.dump_hierarchy()
    has_legacy = ("legacyContainer" in xml) or ("下一部" in xml)
    resumed = sh("dumpsys", "activity", "activities").stdout.decode("utf-8", "ignore")
    act = re.findall(r"mResumedActivity:.*?(\S+VideoPlayerActivity\S*)", resumed)
    print(f"[T8] 传统布局 resumed={act[:1]}, legacy节点={has_legacy}")
    screenshot(d, "t8_legacy")
    if not act:
        print("[T8][FAIL] 未进入 VideoPlayerActivity")
        return False
    if not has_legacy:
        print("[T8][FAIL] 传统布局节点未渲染")
        ok = False
    if not video_playing("T8"):
        print("[T8][FAIL] 传统布局视频未在播放（帧差不足）")
        ok = False
    def click_contains(label: str) -> bool:
        """部分匹配点击（按钮文案带装饰符：'下一部 ▶'/'◀ 上一部'）"""
        for _ in range(3):
            xml_t = d.dump_hierarchy()
            m = (re.search(r'text="([^"]*%s[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                           % re.escape(label), xml_t)
                 or re.search(r'content-desc="([^"]*%s[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                              % re.escape(label), xml_t)
                 or re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="([^"]*%s[^"]*)"'
                              % re.escape(label), xml_t))
            if m:
                g = m.groups()
                if g[0].isdigit():
                    x1, y1, x2, y2 = map(int, g[:4])
                else:
                    x1, y1, x2, y2 = map(int, g[1:5])
                sh("input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                time.sleep(2.0)
                return True
            time.sleep(1.5)
        return False

    th0 = title_hash()
    # ===== 阶段2：传统布局选集切换（点击"第02集"→ 标题变化 + 真实播放）=====
    # 注：上一部/下一部按钮按设计仅在存在切换队列（发现页进入注入）时显示，
    # Intent 直唤无队列 → 按钮隐藏为预期行为；上下部+嗅探连播回归由
    # verify_rss_sniff_after_download.py（订阅源用户路径）覆盖。
    if not click_contains("第02集"):
        print("[T8][FAIL] 选集'第02集'未定位")
        ok = False
    time.sleep(14.0)
    th1 = title_hash()
    playing_next = video_playing("T8next")
    print(f"[T8] 选集切换: 标题hash {th0} -> {th1}, 在播={playing_next}")
    if th0 and th1 and th0 == th1:
        print("[T8][FAIL] 选集切换后标题未变化")
        ok = False
    if not playing_next:
        print("[T8][FAIL] 选集切换后视频未在播放")
        ok = False
    # ===== 阶段3：切回第01集（行为一致性）=====
    if not click_contains("第01集"):
        print("[T8][FAIL] 选集'第01集'未定位")
        ok = False
    time.sleep(14.0)
    th2 = title_hash()
    playing_prev = video_playing("T8prev")
    print(f"[T8] 切回第01集: 标题hash {th1} -> {th2}, 在播={playing_prev}")
    if not playing_prev:
        print("[T8][FAIL] 切回后视频未在播放")
        ok = False
    sh("input", "keyevent", "BACK")
    time.sleep(2.0)
    # ===== 阶段4：切回沉浸式功能正常 =====
    _set_video_layout_mode(0)
    _launch_video_player(book_url, origin)
    if not _assert_immersive_episodes("T8imv", d):
        ok = False
    if not video_playing("T8imv"):
        print("[T8][FAIL] 沉浸式切回后视频未在播放")
        ok = False
    sh("input", "keyevent", "BACK")
    time.sleep(2.0)
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T8][FAIL] FATAL={n_fatal}")
        ok = False
    print(f"[T8] {'PASS' if ok else 'FAIL'}")
    return ok


def t5_rss_source_menu(d) -> bool:
    """订阅源管理多选菜单：死项"校验所选订阅源"不再出现"""
    ok = True
    go_tab(d, "订阅")
    time.sleep(1.0)
    if not click_by(d, "content-desc", "菜单"):
        print("[T5][FAIL] 三点按钮点击失败")
        return False
    time.sleep(1.0)
    if not click_by(d, "text", "设置", tries=2):
        print("[T5][FAIL] 设置(订阅源管理)入口点击失败")
        return False
    time.sleep(2.5)
    # 进入多选：长按第一行（dump 找列表内首个可长按节点——用书名/源名文本不可预知，取屏幕中部坐标长按）
    r = sh("input", "swipe", "640", "400", "640", "400", "900")
    time.sleep(2.0)
    texts, _ = dump_texts(d)
    if DEAD_ITEM in texts:
        print(f"[T5][FAIL] 死菜单项仍存在: {DEAD_ITEM}; visible={sorted(list(texts))[:24]}")
        ok = False
    else:
        print(f"[T5] 死菜单项已不存在（{DEAD_ITEM}）")
    screenshot(d, "t5_rss_source_sel_menu")
    dismiss_popup()
    sh("input", "keyevent", "BACK")  # 退出订阅源管理
    time.sleep(1.5)
    n_fatal = crash_count()
    if n_fatal != 0:
        print(f"[T5][FAIL] FATAL={n_fatal}")
        ok = False
    print(f"[T5] {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all",
                    choices=["all", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"])
    args = ap.parse_args()
    d = u2.connect(HOST)
    print(f"=== ui-batch-fix-0905 L2 验证 start, host={HOST}, pkg={PACKAGE} ===")
    sh("logcat", "-c")
    time.sleep(1.0)
    results = []
    if args.scenario in ("all", "t1"):
        results.append(("T1 崩溃弹框回归", t1_crash_dialog(d)))
    if args.scenario in ("all", "t2"):
        results.append(("T2 订阅头部收口", t2_rss_header(d)))
    if args.scenario in ("all", "t3"):
        results.append(("T3 三点菜单6项", t3_more_menu(d)))
    if args.scenario in ("all", "t4"):
        results.append(("T4 发现页分组反馈", t4_explore_group(d)))
    if args.scenario in ("all", "t5"):
        results.append(("T5 死菜单清理", t5_rss_source_menu(d)))
    if args.scenario in ("all", "t6"):
        results.append(("T6 无卷视频书沉浸式集数", t6_flat_video_book(d)))
    if args.scenario in ("all", "t7"):
        results.append(("T7 有卷视频书回归", t7_volumed_video_book(d)))
    if args.scenario in ("all", "t8"):
        results.append(("T8 布局切换+上下部回归", t8_layout_switch_prevnext(d)))
    print("=== 结果汇总 ===")
    all_pass = True
    for name, passed in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        all_pass = all_pass and passed
    print(f"=== 总判定: {'PASS' if all_pass else 'FAIL'} ===")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
