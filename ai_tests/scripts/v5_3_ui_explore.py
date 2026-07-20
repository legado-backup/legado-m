#!/usr/bin/env python3
"""v5_3_ui_explore.py — 探索App内调试功能UI结构（一次性探索脚本）

输出：
- output/rss/v5_3_explore_*.png 截图
- output/rss/v5_3_explore_*.xml UI dump
- 控制台输出关键技术字段（不输出源名称/域名/URL）

注意：脚本禁止打印 sourceName/sourceUrl/sortUrl 等业务字段。
"""
import subprocess
import sys
import time
import os
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'
OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def adb(*args, timeout=30):
    cmd = [ADB, '-s', HOST] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, text=False)


def adb_shell(cmd_str, timeout=30):
    """adb shell 命令（用列表方式传参避免路径转换）"""
    return adb('shell', cmd_str, timeout=timeout)


def clear_log():
    adb('logcat', '-c')


def dump_log(timeout=10):
    r = adb('logcat', '-d', '-v', 'threadtime', timeout=timeout)
    return r.stdout.decode('utf-8', errors='ignore')


def dump_ui(name):
    """dump UI 到本地文件，返回 xml 文本"""
    remote = '/sdcard/ui_dump.xml'
    adb_shell(f'uiautomator dump {remote}', timeout=15)
    local = OUT_DIR / name
    adb('pull', remote, str(local), timeout=15)
    if local.exists():
        return local.read_text(encoding='utf-8', errors='ignore')
    return ''


def screenshot(name):
    remote = '/sdcard/scr.png'
    adb_shell(f'screencap -p {remote}', timeout=10)
    local = OUT_DIR / name
    adb('pull', remote, str(local), timeout=15)
    return str(local)


def tap(x, y):
    adb_shell(f'input tap {x} {y}', timeout=10)


def swipe(x1, y1, x2, y2, ms=300):
    adb_shell(f'input swipe {x1} {y1} {x2} {y2} {ms}', timeout=10)


def back():
    adb_shell('input keyevent 4', timeout=10)


def parse_ui_nodes(xml_text):
    """从UI XML提取所有可点击/有文本的节点"""
    nodes = []
    # 简化解析：用正则提取 node 元素
    for m in re.finditer(r'<node\b[^>]*?/>|<node\b[^>]*?>(.*?)</node>', xml_text, re.DOTALL):
        tag = m.group(0)
        # 提取属性
        attrs = {}
        for am in re.finditer(r'(\w+)="([^"]*)"', tag):
            attrs[am.group(1)] = am.group(2)
        if attrs:
            nodes.append(attrs)
    return nodes


def find_node_by_text(nodes, text_pattern):
    """根据 text 或 content-desc 找节点"""
    results = []
    for n in nodes:
        text = n.get('text', '') or ''
        desc = n.get('content-desc', '') or ''
        if re.search(text_pattern, text) or re.search(text_pattern, desc):
            results.append(n)
    return results


def find_clickable_nodes(nodes):
    return [n for n in nodes if n.get('clickable') == 'true']


def get_bounds_center(bounds_str):
    """bounds="[x1,y1][x2,y2]" → (cx, cy)"""
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str or '')
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def main():
    print('=' * 70)
    print('探索 App 内 RSS 源调试功能 UI 结构')
    print('=' * 70)

    # 清理日志，启动App
    clear_log()
    print('\n[1] 启动 App...')
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)
    adb_shell(f'am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
    time.sleep(8)

    xml = dump_ui('v5_3_explore_01_home.xml')
    screenshot('v5_3_explore_01_home.png')
    nodes = parse_ui_nodes(xml)
    print(f'  当前UI节点数: {len(nodes)}')
    # 找订阅源入口
    rss_entries = find_node_by_text(nodes, r'订阅|RSS|订阅源')
    print(f'  "订阅源"入口节点: {len(rss_entries)}')
    for n in rss_entries[:3]:
        b = get_bounds_center(n.get('bounds', ''))
        print(f'    - text={n.get("text","")!r} desc={n.get("content-desc","")!r} center={b}')

    # 找底部Tab标签
    print('\n  当前页面可点击节点（前15个）:')
    clickable = find_clickable_nodes(nodes)
    for n in clickable[:15]:
        b = get_bounds_center(n.get('bounds', ''))
        t = n.get('text', '') or n.get('content-desc', '')
        print(f'    - text={t!r} center={b}')

    # 找"我的"或"订阅" tab
    my_tab = find_node_by_text(nodes, r'^我的$|^我$')
    if my_tab:
        b = get_bounds_center(my_tab[0].get('bounds', ''))
        if b:
            print(f'\n[2] 点击"我的"tab @ {b}')
            tap(*b)
            time.sleep(3)
            xml = dump_ui('v5_3_explore_02_my.xml')
            screenshot('v5_3_explore_02_my.png')
            nodes = parse_ui_nodes(xml)
            print(f'  节点数: {len(nodes)}')
            rss_entries = find_node_by_text(nodes, r'订阅源|RSS源管理|订阅')
            print(f'  "订阅源"入口: {len(rss_entries)}')
            for n in rss_entries[:3]:
                b = get_bounds_center(n.get('bounds', ''))
                print(f'    - text={n.get("text","")!r} desc={n.get("content-desc","")!r} center={b}')

    # 直接用 am start 进入 RssSourceActivity（更可靠）
    print('\n[3] 尝试直接 am start 订阅源管理界面...')
    # 候选Activity名
    candidates = [
        'io.legado.app.ui.rss.RssMainActivity',
        'io.legado.app.ui.rss.source.RssSourceActivity',
        'io.legado.app.ui.rss.RssActivity',
        'io.legado.app.ui.rss.source.RssSourceListActivity',
    ]
    for act in candidates:
        r = adb_shell(f'am start -n {PKG}/{act}', timeout=10)
        out = r.stdout.decode('utf-8', errors='ignore')
        err = r.stderr.decode('utf-8', errors='ignore')
        if 'Error' not in out and 'Error' not in err:
            print(f'  ✅ 启动成功: {act}')
            time.sleep(4)
            xml = dump_ui('v5_3_explore_03_rss_list.xml')
            screenshot('v5_3_explore_03_rss_list.png')
            nodes = parse_ui_nodes(xml)
            print(f'  节点数: {len(nodes)}')
            # 找列表项
            list_items = [n for n in nodes if n.get('clickable') == 'true']
            print(f'  可点击节点: {len(list_items)}')
            for n in list_items[:8]:
                b = get_bounds_center(n.get('bounds', ''))
                t = (n.get('text', '') or '')[:30]
                print(f'    - text={t!r} center={b}')
            break
        else:
            print(f'  ❌ 失败: {act} → {out.strip()[:80]}')

    # 如果还没到，回到主页尝试通过菜单进入
    print('\n[4] 探索当前页面文字内容（找订阅源入口）...')
    xml = dump_ui('v5_3_explore_04_current.xml')
    screenshot('v5_3_explore_04_current.png')
    nodes = parse_ui_nodes(xml)
    all_texts = sorted(set(n.get('text', '') for n in nodes if n.get('text', '').strip()))
    print(f'  当前页面所有文本节点（前30个，已脱敏）:')
    for t in all_texts[:30]:
        # 脱敏：禁止打印完整源名称/URL/域名，只打印UI技术文本（菜单项/按钮文字）
        if re.match(r'^https?://', t) or '.' in t and len(t) > 20:
            print(f'    - [URL/域名已脱敏]')
        else:
            print(f'    - {t!r}')

    # 保存日志
    log = dump_log()
    log_path = OUT_DIR / 'v5_3_explore.log'
    log_path.write_text(log, encoding='utf-8', errors='ignore')
    print(f'\n  日志已保存: {log_path}')

    print('\n[5] 完成 UI 探索，请人工分析 dump 文件确定调试按钮位置')


if __name__ == '__main__':
    main()
