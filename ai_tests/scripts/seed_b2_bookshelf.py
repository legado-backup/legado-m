#!/usr/bin/env python3
r"""seed_b2_bookshelf.py — B2 冻结验收书架数据播种（≥6 本合成书 + 合成书源）

目的：compose tasks §4.4-4.8 冻结验收 7 脚本的数据依赖。
首轮 s1-2 FAIL=数据依赖型（书架不足 2 屏滚动位移=0），本脚本一次补齐：
    1. 生成合成书站（8 本书 × 4 章）到 ai_tests/testdata/b2_shelf_srv/
    2. 生成合成书源 JSON 到 ai_tests/testdata/b2_book_source.json（干净锚点数据）
    3. 调 import_book_source.py DB 直插（WAL 安全三件套）
    4. adb reverse tcp:18092 → UI 搜索（searchScope 限定合成源，零外网）
    5. 循环 8 本：搜索结果→详情→放入书架→阅读(1章缓存)→返回
    6. 就绪断言：书架 dump 合成书计数 ≥6（脱敏：仅输出计数）

前置：本地 HTTP 服务已由外部启动（b2_serve，python -m http.server 18092）。
用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/seed_b2_bookshelf.py
退出码：0=就绪 1=播种失败 2=环境不可用

落位口径（总线 2.12 双登记）：
    .gitignore 白名单 !/ai_tests/scripts/seed_b2_bookshelf.py；
    ai_tests/docs/fixed_test_workflow.md 工具表；ai_tests/README.md 族索引。
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_tests.config import ADB_PATH, MEMU_ADB_HOST, PACKAGE  # noqa: E402

PORT = 18092
BASE = f"http://127.0.0.1:{PORT}"
# 合成数据锚点（本地生成，无业务源数据，脱敏口径=可直接输出）
SRC_NAME = "B2冻结合成源"
BOOK_PREFIX = "回归样本读物"
SUFFIXES = "ABCDEFGHIJKLMNOP"
N_BOOKS = 16
N_CHAPTER = 4
CH_PREFIX = "回归样本章节"
CONTENT_ANCHOR = "回归样本正文"
SCOPE = f"{SRC_NAME}::{BASE}"
SEARCH_ACT = f"{PACKAGE}/io.legado.app.ui.book.search.SearchActivity"

BOOKS = [f"{BOOK_PREFIX}{s}" for s in SUFFIXES[:N_BOOKS]]


def run_adb(cmd, timeout=30):
    return subprocess.run(f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}', shell=True,
                          capture_output=True, text=True, timeout=timeout)


# ==================== 1. 合成站点 + 书源 JSON ====================

def build_server_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    q = str(int(time.time()))
    # 搜索页：8 本书一页列出（key 无关，静态返回全部）
    rows = "".join(
        f'<div class="bookbox"><a class="bk" href="{BASE}/book{i}.html?r={q}">{BOOKS[i - 1]}</a>'
        f'<span class="au">样本作者{i}</span></div>'
        for i in range(1, N_BOOKS + 1))
    (root / "search.html").write_text(f"<html><body>{rows}</body></html>", encoding="utf-8")
    # 详情页 × 8（tocUrl 指向各自目录页）
    for i in range(1, N_BOOKS + 1):
        (root / f"book{i}.html").write_text(
            "<html><body>"
            f'<div class="btitle">{BOOKS[i - 1]}</div>'
            f'<div class="bau">样本作者{i}</div>'
            f'<div class="bintro">本地合成回归数据，仅用于自动化验证（书{i}）。</div>'
            f'<a class="btoc" href="{BASE}/toc{i}.html?r={q}">查看目录</a>'
            "</body></html>", encoding="utf-8")
        # 目录页 × 8（4 章，章节页复用 c1-c4）
        chs = "".join(
            f'<div class="ch"><a href="{BASE}/c{j}.html?r={q}">{CH_PREFIX}{j:02d}</a></div>'
            for j in range(1, N_CHAPTER + 1))
        (root / f"toc{i}.html").write_text(f"<html><body>{chs}</body></html>", encoding="utf-8")
    # 正文页 × 4（8 本书复用；每章 30 段保证多页翻页余量——B2 校准：8 段仅 1 页致 R1 翻页断言无余量）
    para = CONTENT_ANCHOR + "：本段为本地合成回归数据，用于验证解析链路。"
    for j in range(1, N_CHAPTER + 1):
        body = "".join(f"<p>{para}（{CH_PREFIX}{j:02d}-第{k}段）</p>" for k in range(1, 31))
        (root / f"c{j}.html").write_text(
            f'<html><body><div class="ct">{body}</div></body></html>', encoding="utf-8")
    return root


def build_source_json(path: Path):
    """合成书源 JSON ×3（同规则不同 id 路径；s2 管理列表需 ≥2 条目）
    规则前缀 class./tag. 为 AnalyzeByJSoup 简写，l3 同口径"""
    sources = []
    for i, sub in enumerate(("", "/s2", "/s3")):
        base = BASE + sub
        sources.append({
            "bookSourceUrl": base,
            "bookSourceName": SRC_NAME if not sub else f"{SRC_NAME}{i + 1}",
            "bookSourceGroup": "回归测试",
            "bookSourceType": 0,
            "enabled": 1,
            "enabledExplore": 0,
            "enabledCookieJar": 0,
            "searchUrl": f"{BASE}/search.html?kw={{{{key}}}}",
            "ruleSearch": json.dumps({
                "bookList": "class.bookbox",
                "name": "class.bk@text",
                "author": "class.au@text",
                "bookUrl": "class.bk@href",
            }, ensure_ascii=False),
            "ruleBookInfo": json.dumps({
                "name": "class.btitle@text",
                "author": "class.bau@text",
                "intro": "class.bintro@text",
                "tocUrl": "class.btoc@href",
            }, ensure_ascii=False),
            "ruleToc": json.dumps({
                "chapterList": "class.ch",
                "chapterName": "tag.a@text",
                "chapterUrl": "tag.a@href",
            }, ensure_ascii=False),
            "ruleContent": json.dumps({
                "content": "class.ct@textNodes",
            }, ensure_ascii=False),
        })
    path.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ==================== 2. u2 辅助（l3_verify_source_baseline 同口径） ====================

def dismiss_popups(d):
    for t in ("关闭", "取消", "以后再说", "我知道了", "知道了"):
        if d(text=t).wait(timeout=1):
            d(text=t).click()
            time.sleep(1)


def find_node(d, text: str):
    xml = d.dump_hierarchy()
    for m in re.finditer(
            r'<node[^>]*text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if m.group(1) == text:
            x1, y1, x2, y2 = map(int, m.groups()[1:])
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def find_nodes_all(d, text: str):
    xml = d.dump_hierarchy()
    out = []
    for m in re.finditer(r'<node[^>]*?/?>', xml):
        node = m.group(0)
        tm = re.search(r'text="([^"]*)"', node)
        if not tm or tm.group(1) != text:
            continue
        cls = re.search(r'class="([^"]*)"', node)
        if cls and "EditText" in cls.group(1):
            continue
        bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
        if bm:
            x1, y1, x2, y2 = map(int, bm.groups())
            out.append({"cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2, "top": y1})
    return out


def tap_text(d, text: str, tries=3, wait=2.5) -> bool:
    for _ in range(tries):
        pos = find_node(d, text)
        if pos:
            d.click(*pos)
            time.sleep(wait)
            return True
        time.sleep(1)
    return False


def wait_text(d, text: str, timeout=20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if find_node(d, text):
            return True
        time.sleep(1.5)
    return False


def back_until(d, activity_suffix: str, max_backs=6) -> bool:
    for _ in range(max_backs):
        cur = d.app_current().get("activity", "")
        if cur.endswith(activity_suffix):
            return True
        d.press("back")
        time.sleep(1.5)
    return d.app_current().get("activity", "").endswith(activity_suffix)


# ==================== 3. UI 播种：循环入架 ====================

def seed_via_search(d) -> int:
    """搜索→逐本：详情→放入书架→阅读(缓存1章)→返回。返回成功入架数。"""
    d.app_stop(PACKAGE)
    time.sleep(1.5)
    d.app_start(PACKAGE)
    time.sleep(6)
    dismiss_popups(d)
    run_adb("logcat -c")
    r = run_adb(f"shell am start -n {SEARCH_ACT} --es key {BOOK_PREFIX} "
                f"--es searchScope '{SCOPE}'", timeout=30)
    if r.returncode != 0:
        print(f"  [FAIL] SearchActivity 启动失败 rc={r.returncode}")
        return 0
    # 等 8 行结果（首本出现即开始；其余逐本等待）
    deadline = time.time() + 40
    while time.time() < deadline:
        if [n for n in find_nodes_all(d, BOOKS[0]) if n["top"] >= 150]:
            break
        time.sleep(1.5)
    else:
        print("  [FAIL] 搜索结果未见合成书锚点（首本）")
        return 0

    added = 0
    for name in BOOKS:
        ok = seed_one_book(d, name)
        print(f"  [{added + 1 if ok else '-'}/{N_BOOKS}] {name}: "
              f"{'OK' if ok else 'FAIL（继续下一本）'}")
        if ok:
            added += 1
    return added


def seed_one_book(d, name: str) -> bool:
    # 结果行定位（top≥150 过滤顶部输入区；视口外小幅滚动兜底）
    row = None
    for _ in range(4):
        rows = [n for n in find_nodes_all(d, name) if n["top"] >= 150]
        if rows:
            row = rows[0]
            break
        d.shell("input swipe 640 900 640 700 250")
        time.sleep(1.2)
    if not row:
        return False
    entered = False
    for _ in range(3):
        rows = [n for n in find_nodes_all(d, name) if n["top"] >= 150]
        if rows:
            d.click(rows[0]["cx"], rows[0]["cy"])
            time.sleep(3)
        if "BookInfo" in d.app_current().get("activity", ""):
            entered = True
            break
    if not entered:
        return False
    # 放入书架（已在架则显示"移出书架"，跳过）
    if find_node(d, "放入书架"):
        tap_text(d, "放入书架", tries=2, wait=2)
    elif not find_node(d, "移出书架"):
        time.sleep(2)  # 详情未就绪再等一次
        if find_node(d, "放入书架"):
            tap_text(d, "放入书架", tries=2, wait=2)
    # 进阅读页一次（首章正文缓存 + 阅读进度，供 s5/cache 依赖）
    if tap_text(d, "阅读", tries=2, wait=6):
        time.sleep(4)   # 首章解析+渲染
        d.press("back")  # 回详情
        time.sleep(2)
    if not back_until(d, "SearchActivity", max_backs=4):
        # 兜底：返回链断裂（落入书架/首页）→ 重开确定性搜索恢复结果列表
        run_adb(f"shell am start -n {SEARCH_ACT} --es key {BOOK_PREFIX} "
                f"--es searchScope '{SCOPE}'", timeout=30)
        time.sleep(3)
    time.sleep(1.5)
    return True


# ==================== 4. 就绪断言 ====================

def assert_shelf(d) -> int:
    """书架 dump 合成书计数（text 或 content-desc 命中）"""
    count = 0
    detail = {}
    xml = d.dump_hierarchy()
    for name in BOOKS:
        n = len(re.findall(rf'(?:text|content-desc)="{name}"', xml))
        detail[name[-1]] = n
        count += 1 if n >= 1 else 0
    print(f"  书架合成书计数: {count}/{N_BOOKS} 分布={detail}")
    return count


def main():
    print("=" * 60)
    print("B2 冻结验收书架播种（合成 8 本, 脱敏口径=合成锚点可输出）")
    print(f"设备: {MEMU_ADB_HOST} | 包: {PACKAGE}")
    print("=" * 60)

    probe = subprocess.run([ADB_PATH, "-s", MEMU_ADB_HOST, "shell", "echo", "ok"],
                           capture_output=True, timeout=15)
    if probe.returncode != 0:
        print("❌ 设备不可连接")
        sys.exit(2)

    root = build_server_dir(Path(__file__).parent.parent / "testdata" / "b2_shelf_srv")
    json_path = build_source_json(
        Path(__file__).parent.parent / "testdata" / "b2_book_source.json")
    print(f"合成站点: {len(list(root.glob('*.html')))} 页 | 书源 JSON: {json_path.name}")

    # 书源 DB 直插（import_book_source.py 同仓复用）
    imp = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "import_book_source.py"),
         str(json_path)], capture_output=True, text=True, timeout=180)
    print(imp.stdout[-1500:] if imp.stdout else "")
    if imp.returncode != 0:
        print(f"❌ 书源导入失败 rc={imp.returncode}")
        sys.exit(1)

    # reverse（服务由外部 http.server 提供，端口映射必须先建立）
    r = run_adb(f"reverse tcp:{PORT} tcp:{PORT}")
    if r.returncode != 0:
        print("❌ adb reverse 失败")
        sys.exit(2)
    print(f"adb reverse tcp:{PORT} OK")

    try:
        import uiautomator2 as u2
        d = u2.connect(MEMU_ADB_HOST)
        added = seed_via_search(d)
        if added < 6:
            print(f"\n[FAIL] 入架成功 {added} 本 < 6，播种失败")
            sys.exit(1)

        # 回书架断言
        back_until(d, "MainActivity")
        time.sleep(2)
        shelf_cnt = assert_shelf(d)
        ok = shelf_cnt >= 6
        print(f"\n[就绪断言] 书架 ≥6 本: {'PASS' if ok else 'FAIL'}（={shelf_cnt}）")
        print("书源计数以 import_book_source.py 插入校验输出为准（≥1）")
        sys.exit(0 if ok else 1)
    finally:
        pass  # reverse 保留（7 脚本运行期间需服务在线；由 b2 收尾统一移除）


if __name__ == "__main__":
    main()
