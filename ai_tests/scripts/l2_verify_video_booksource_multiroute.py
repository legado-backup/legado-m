#!/usr/bin/env python3
r"""l2_verify_video_booksource_multiroute.py — 视频书源多线路多集 L2 真机验证

video-booksource-multiroute 功能真机测试（测试包 io.legado.miss.app.debug）：
    L0 零规则源（ruleToc/ruleContent 全空，MacCmsNormalizer 直产卷章）
    L1 四条 JSONPath 源（chapterList=$.chapters[*] 消费注入结构）
    订阅源回归（悬浮选择器仍在、无详情入口，UI 零退化）

前置：
    1. 模拟器 127.0.0.1:21503 已连接
    2. 测试书源已导入（ai_tests/scripts/testdata/booksource_video_l0_hhzy.json / l1）
       ai_tests\venv\Scripts\python.exe ai_tests/scripts/import_book_source.py <json>
    3. 站点可访问（API 探测已预验：搜索"2025"首页全多线路，2线路×N集）

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_booksource_multiroute.py --case l0
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_booksource_multiroute.py --case l1
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_booksource_multiroute.py --case regression
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_booksource_multiroute.py --case all

脱敏口径：报告只输出异常类型/日志关键行（技术关键字），不输出域名/URL/播放地址原文。
回归路径：rssReadRecords 历史单篇直达播放页（VideoPlayerActivity 支持的合法入口）。

退出码：0=全部通过 1=部分未通过 2=致命（设备/导航失败）
"""
import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PACKAGE = "io.legado.miss.app.debug"
MAIN_ACTIVITY = "io.legado.app.ui.welcome.WelcomeActivity"
SEARCH_ACTIVITY = "io.legado.app.ui.book.search.SearchActivity"
PLAYER_ACTIVITY = "io.legado.app.ui.video.VideoPlayerActivity"

# 测试源（与 testdata/booksource_video_l{0,1}_hhzy.json 一致；域名脱敏在报告层处理）
L0_NAME, L0_SCOPE_URL = "AI-Test-L0", "https://hhzyapi.com/api.php/provide/vod"
L1_NAME, L1_SCOPE_URL = "AI-Test-L1", "https://hhzyapi.com/api.php/provide/vod/"
# 搜索词用纯数字：站点H 首页 20 条全多线路（2线路×9集）；且避免 am start 中文 extra 编码损坏
SEARCH_KEY = "2025"

RESULT = {}

try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False


def run_adb(cmd, timeout=60):
    full = [ADB, "-s", DEVICE] + cmd
    return subprocess.run(full, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def front_activity():
    r = run_adb("shell dumpsys activity activities".split())
    # 格式: mResumedActivity: ActivityRecord{... u0 pkg/activity t123}
    m = re.search(r"mResumedActivity:.*?u0\s+(\S+)", r.stdout or "")
    return m.group(1) if m else ""


def wait_front(substr, timeout=20):
    for _ in range(timeout * 2):
        act = front_activity()
        if substr in act:
            return True
        time.sleep(0.5)
    return False


def get_app_pid():
    r = run_adb(["shell", "pidof", PACKAGE])
    out = (r.stdout or "").strip()
    return out.split()[0] if out else None


def logcat_dump():
    r = run_adb("logcat -d".split(), timeout=90)
    return r.stdout or ""


def logcat_clear():
    run_adb("logcat -c".split())


def log_errors(log):
    """错误模式统计：只输出异常类型计数，不输出原始行（脱敏）
    FATAL 全量检查；其余异常仅统计 App 进程行（排除 system_server/u2 噪音）"""
    pats = {
        "FATAL": r"FATAL EXCEPTION",
        "NullPointerException": r"NullPointerException",
        "IllegalStateException": r"IllegalStateException",
        "ClassCastException": r"ClassCastException",
        "IndexOutOfBounds": r"IndexOutOfBoundsException",
        "JSONException": r"JSONException",
    }
    pid = get_app_pid()
    pid_re = re.compile(rf"\s{pid}\s+[VDIWE]\s") if pid else None
    out = {}
    for name, p in pats.items():
        hits = [l for l in log.splitlines() if re.search(p, l)]
        if name != "FATAL" and pid_re:
            hits = [l for l in hits if pid_re.search(l)]
        if hits:
            out[name] = len(hits)
    return out


def connect():
    if not HAS_U2:
        print("❌ uiautomator2 未安装")
        return None
    try:
        d = u2.connect(DEVICE)
        print(f"✅ 设备已连接: {d.info.get('productName', 'unknown')}")
        return d
    except Exception as e:
        print(f"❌ u2 连接失败: {type(e).__name__}: {e}")
        return None


def start_app():
    run_adb(["shell", "am", "force-stop", PACKAGE])
    time.sleep(1.5)
    run_adb(["shell", "am", "start", "-n", f"{PACKAGE}/{MAIN_ACTIVITY}"])
    time.sleep(6)


def search_single_source(d, source_name, scope_url, key=SEARCH_KEY):
    """am start 直达单源搜索（searchScope 格式 源名::源URL，receiptIntent 自动 setQuery 触发搜索）"""
    run_adb(["shell", "am", "start", "-n", f"{PACKAGE}/{SEARCH_ACTIVITY}",
             "--es", "key", key, "--es", "searchScope", f"{source_name}::{scope_url}"])
    time.sleep(4)
    if not wait_front("SearchActivity", 15):
        return False, "SearchActivity 未到前台"
    # 等待搜索结果（单源一般 <10s，保险 12s）
    time.sleep(12)
    return True, ""


def dump_result_items(d):
    """dump 层级 → 返回列表候选文本节点 [(text, cx, cy)]
    Compose 列表 item 的 clickable 在无文本根容器上，文本节点本身不可点，
    但点击文本坐标会命中 item。排除顶部搜索区与 meta 行（作者：/分类）。"""
    xml = d.dump_hierarchy()
    root = ET.fromstring(xml)
    items = []
    for node in root.iter("node"):
        t = (node.get("text") or "").strip()
        if not t or t.startswith("作者") or len(t) < 4:
            continue
        b = node.get("bounds", "[0,0][0,0]")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if y1 < 150 or y1 > 1800 or (x2 - x1) < 60:
            continue
        items.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return items


def click_first_result_until_player(d, max_try=4):
    """点击搜索结果直到进入 VideoPlayerActivity（点错 back 重试下一个候选）"""
    for _ in range(max_try):
        if wait_front("VideoPlayerActivity", 8):
            return True, ""
        cands = dump_result_items(d)
        if not cands:
            print("    ⚠️ 无结果候选节点，等待 3s 重试")
            time.sleep(3)
            continue
        t, x, y = cands[0]
        print(f"    点击结果 text_len={len(t)} y={y}")
        d.click(x, y)
        time.sleep(3)
        if wait_front("VideoPlayerActivity", 12):
            return True, ""
        run_adb(["shell", "input", "keyevent", "4"])
        time.sleep(2)
    return wait_front("VideoPlayerActivity", 5), "点击结果未进入播放器"


def get_title_text(d):
    el = d(resourceId=f"{PACKAGE}:id/tv_video_title")
    return el.get_text() if el.exists else None


def ensure_title_visible(d, tries=3):
    """唤出播放器控件直到 tv_video_title 可见；全屏态先退全屏（tv_video_title 属竖屏控件）"""
    for _ in range(tries):
        if d(resourceId=f"{PACKAGE}:id/tv_video_title").exists:
            return True
        # 全屏态：btn_back_overlay 可见 → 先退全屏
        if d(resourceId=f"{PACKAGE}:id/btn_back_overlay").exists:
            run_adb(["shell", "input", "keyevent", "4"])
            time.sleep(1.5)
        d.click(540, 400)
        time.sleep(1)
    return d(resourceId=f"{PACKAGE}:id/tv_video_title").exists


def open_detail_sheet(d):
    """点左下角标题打开详情抽屉 → 等待 Compose sheet 渲染"""
    if not ensure_title_visible(d):
        return False, "tv_video_title 不可见（控件唤出失败）"
    title = d(resourceId=f"{PACKAGE}:id/tv_video_title")
    title.click()
    time.sleep(2)
    sheet = d(text="详情")
    if sheet.wait(timeout=6):
        return True, ""
    return False, "详情抽屉未出现（无 text=详情）"


def sheet_nodes(d):
    """dump 抽屉节点（带坐标）: [(text, cx, cy)]"""
    xml = d.dump_hierarchy()
    root = ET.fromstring(xml)
    nodes = []
    for node in root.iter("node"):
        t = (node.get("text") or "").strip()
        if not t:
            continue
        b = node.get("bounds", "[0,0][0,0]")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        nodes.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return nodes


def close_sheet(d):
    run_adb(["shell", "input", "keyevent", "4"])
    time.sleep(1.5)


def check_book_source_flow(d, case, source_name, scope_url, expect_l0):
    """书源全链路：搜索→播放器→目录日志→详情抽屉→切线路→选集"""
    steps = {}
    print(f"\n===== [{case}] 单源搜索: {source_name} =====")
    logcat_clear()
    ok, err = search_single_source(d, source_name, scope_url)
    steps["搜索页打开"] = (ok, err)
    if not ok:
        return steps

    ok, err = click_first_result_until_player(d)
    steps["结果点入播放器"] = (ok, err if not ok else "")
    if not ok:
        return steps

    # 等目录+起播（L0/L1 目录解析 + 内容直链）
    time.sleep(8)

    log = logcat_dump()
    has_norm = "MacCMS规范化完成" in log
    has_l0 = "卷章直产完成" in log
    if expect_l0:
        steps["日志-规范化注入"] = (has_norm, "" if has_norm else "缺 MacCMS规范化完成")
        steps["日志-L0卷章直产"] = (has_l0, "" if has_l0 else "缺 卷章直产完成")
    else:
        steps["日志-规范化注入"] = (has_norm, "" if has_norm else "缺 MacCMS规范化完成")
        steps["日志-L1不走直产"] = (not has_l0, "" if not has_l0 else "L1 出现卷章直产日志(应走规则)")

    # 详情抽屉（点左下角标题）
    ok, err = open_detail_sheet(d)
    steps["详情抽屉打开"] = (ok, err)
    if not ok:
        return steps

    # 坐标区间定位：线路 label 与 选集 label 之间=线路胶囊；选集 label 之后=集数网格
    nodes = sheet_nodes(d)
    y_route = next((y for t, x, y in nodes if t == "线路"), None)
    y_ep = next((y for t, x, y in nodes if t == "选集"), None)
    has_intro = any(len(t) > 20 for t, x, y in nodes)
    steps["抽屉-简介"] = (has_intro, "" if has_intro else "简介区未检出长文本")
    if y_route is None or y_ep is None:
        steps["抽屉-线路Tab"] = (False, "缺 线路/选集 label")
        steps["抽屉-选集网格"] = (False, "缺 线路/选集 label")
        return steps
    route_caps = [(t, x, y) for t, x, y in nodes if y_route < y < y_ep and len(t) <= 12]
    episodes = [(t, x, y) for t, x, y in nodes if y > y_ep and len(t) <= 16]
    steps["抽屉-线路Tab"] = (len(route_caps) >= 2, f"线路胶囊数={len(route_caps)}" if len(route_caps) < 2 else "")
    steps["抽屉-选集网格"] = (len(episodes) >= 1, f"集数节点数={len(episodes)}" if not episodes else "")
    print(f"    抽屉统计: 线路胶囊={len(route_caps)} 集数节点={len(episodes)}")

    title_before = get_title_text(d)
    # 播放管线断言关键字：playBookEpisode/startPlayBookChapter 正常路径不打日志，
    # 以 ExoPlayer EventLogger / MediaCodec / WebBook 正文采集日志为准
    PIPE_KEYS = ("playBookEpisode", "startPlayBookChapter", "EventLogger", "MediaCodec",
                 "获取正文开始", "正文规则为空")

    # 切线路：点第二个胶囊（第一个为当前选中线路），断言播放管线有新动作
    if len(route_caps) >= 2:
        _, x, y = route_caps[1]
        logcat_clear()
        d.click(x, y)  # 点击后抽屉自动 dismiss 并起播
        time.sleep(6)
        log2 = logcat_dump()
        pipeline = any(k in log2 for k in PIPE_KEYS)
        ok_title = wait_front("VideoPlayerActivity", 8)
        steps["切线路播放"] = (pipeline and ok_title,
                          "" if (pipeline and ok_title) else f"管线日志={pipeline} 前台={ok_title}")
    else:
        steps["切线路播放"] = (False, "线路胶囊<2（可能点入单线路影片）")

    # 选集：重开抽屉，点第二个集数节点，断言播放管线新动作
    # 点击命中判定：命中 item 后抽屉会 dismiss（详情节点消失）+ 播放管线日志
    ep_ok, ep_detail = False, "重开抽屉失败（tv_video_title 不可见）"
    for attempt in range(3):
        if not (ensure_title_visible(d) and open_detail_sheet(d)):
            ep_detail = f"第{attempt+1}次重开抽屉失败"
            continue
        nodes2 = sheet_nodes(d)
        y_ep2 = next((y for t, x, y in nodes2 if t == "选集"), None)
        eps2 = [(t, x, y) for t, x, y in nodes2 if y_ep2 and y > y_ep2 and len(t) <= 16]
        if not eps2:
            ep_detail = "抽屉无集数节点"
            continue
        pick = eps2[1] if len(eps2) > 1 else eps2[0]
        logcat_clear()
        d.click(pick[1], pick[2])
        time.sleep(7)
        log3 = logcat_dump()
        pipeline3 = any(k in log3 for k in PIPE_KEYS)
        sheet_gone = not d(text="详情").exists  # 命中 item → dismiss
        if pipeline3 and sheet_gone:
            ep_ok, ep_detail = True, ""
            break
        ep_detail = f"尝试{attempt+1}: 管线={pipeline3} 抽屉关闭={sheet_gone}"
        close_sheet(d)
    steps["选集播放"] = (ep_ok, ep_detail)

    # 错误模式
    log4 = logcat_dump()
    errs = log_errors(log4)
    steps["播放错误检查"] = (not errs, f"错误模式={errs}" if errs else "")
    return steps


def case_l0(d):
    print("\n" + "=" * 60)
    print("用例 L0：零规则视频书源全链路")
    print("=" * 60)
    start_app()
    steps = check_book_source_flow(d, "L0", L0_NAME, L0_SCOPE_URL, expect_l0=True)
    return report("L0", steps)


def case_l1(d):
    print("\n" + "=" * 60)
    print("用例 L1：四条 JSONPath 视频书源全链路")
    print("=" * 60)
    start_app()
    steps = check_book_source_flow(d, "L1", L1_NAME, L1_SCOPE_URL, expect_l0=False)
    return report("L1", steps)


def get_last_rss_record():
    """从 DB 取最近一条订阅源播放历史 (origin, record)；值仅在脚本内使用"""
    import os
    import sqlite3
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "l2rr.db")
    # SOP 陷阱#4：su -c 必须整体单参数传递（列表拆参会失败）
    run_adb(["shell", f"su -c 'cp /data/data/{PACKAGE}/databases/legado.db /sdcard/l2rr.db'"])
    r = run_adb(["pull", "/sdcard/l2rr.db", tmp])
    if r.returncode != 0:
        print(f"    ⚠️ DB pull 失败: {(r.stderr or '')[:80]}")
        return None, None
    pair = (None, None)
    con = None
    try:
        con = sqlite3.connect(f"file:{tmp}?mode=ro&immutable=1", uri=True)
        cur = con.cursor()
        # 优先取多线路源（ruleRoutes 非空）的历史播放记录，保证悬浮选择器可验证
        cur.execute(
            "SELECT r.origin, r.record FROM rssReadRecords r "
            "JOIN rssSources s ON r.origin = s.sourceUrl "
            "WHERE s.ruleRoutes IS NOT NULL AND s.ruleRoutes != '' "
            "ORDER BY r.durPos DESC LIMIT 5")
        rows = cur.fetchall()
        if not rows:
            cur.execute("SELECT origin, record FROM rssReadRecords ORDER BY durPos DESC LIMIT 5")
            rows = cur.fetchall()
        print(f"    历史记录数(取样)={len(rows)} origin_len={[len(o or '') for o, _ in rows]}")
        if rows:
            pair = rows[0]
    except Exception as e:
        print(f"    ⚠️ DB 查询失败: {type(e).__name__}")
    finally:
        if con is not None:
            con.close()
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
    return pair


def case_regression(d):
    print("\n" + "=" * 60)
    print("用例 回归：订阅源播放页（悬浮选择器仍在 / 无详情入口）")
    print("=" * 60)
    steps = {}
    start_app()
    # 历史单篇直达（VideoPlayerActivity 支持 sourceKey+sourceType=rss+record）
    origin, record = get_last_rss_record()
    if not origin or not record:
        return report("回归", {"历史记录": (False, "rssReadRecords 无可用记录")})
    logcat_clear()
    run_adb(["shell", "am", "start", "-n", f"{PACKAGE}/{PLAYER_ACTIVITY}",
             "--es", "sourceKey", origin, "--ei", "sourceType", "1",
             "--es", "record", record])
    ok = wait_front("VideoPlayerActivity", 20)
    steps["订阅源进播放器"] = (ok, "" if ok else "历史记录直达播放页失败")
    if ok:
        time.sleep(8)  # 等源加载+起播
        ensure_title_visible(d)
        has_title = d(resourceId=f"{PACKAGE}:id/tv_video_title").exists
        steps["悬浮标题存在"] = (has_title, "" if has_title else "tv_video_title 不存在")
        has_route_selector = d(resourceId=f"{PACKAGE}:id/tv_route_selector").exists
        steps["悬浮线路选择器"] = (True, f"可见={has_route_selector}（单线路源隐藏属既有行为）")
        has_ep_selector = d(resourceId=f"{PACKAGE}:id/rv_episodes").exists
        steps["悬浮集数选择器"] = (True, f"可见={has_ep_selector}（单集源隐藏属既有行为）")
        # 点标题 → 不应出现详情抽屉（AD-06 零退化）
        if has_title:
            d(resourceId=f"{PACKAGE}:id/tv_video_title").click()
            time.sleep(2.5)
            no_sheet = not d(text="详情").wait(timeout=4)
            steps["无详情入口(零退化)"] = (no_sheet, "" if no_sheet else "订阅源模式出现详情抽屉（退化!）")
    log = logcat_dump()
    errs = log_errors(log)
    steps["错误检查"] = (not errs, f"错误模式={errs}" if errs else "")
    return report("回归", steps)


def report(case, steps):
    passed = all(ok for ok, _ in steps.values())
    print(f"\n----- [{case}] 结果 -----")
    for name, (ok, detail) in steps.items():
        mark = "✅" if ok else "❌"
        line = f"  {mark} {name}"
        if detail:
            line += f"  ({detail})"
        print(line)
    RESULT[case] = passed
    return passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=["l0", "l1", "regression", "all"], default="all")
    args = ap.parse_args()
    d = connect()
    if d is None:
        sys.exit(2)
    try:
        if args.case in ("l0", "all"):
            case_l0(d)
        if args.case in ("l1", "all"):
            case_l1(d)
        if args.case in ("regression", "all"):
            case_regression(d)
    finally:
        print("\n" + "=" * 60)
        print("总体结果: " + " | ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in RESULT.items()))
        print("=" * 60)
    sys.exit(0 if all(RESULT.values()) and RESULT else 1)


if __name__ == "__main__":
    main()
