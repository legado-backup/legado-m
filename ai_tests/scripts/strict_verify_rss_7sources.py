#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
严格验证7个订阅源的分类和搜索功能
- 必须截图确认每个步骤的实际UI状态
- 必须dump UI hierarchy确认页面结构
- 分类标签检查：TabLayout中是否有多个标签
- 搜索测试：必须在源内搜索，不是全局搜索
- 仅输出技术结论，禁止输出业务数据
"""

import uiautomator2 as u2
import time
import sys
import os
import subprocess
import re
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ==================== 配置 ====================
PKG = 'io.legado.miss.app.debug'
ID = f'{PKG}:id/'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
SEARCH_KEYWORD = 'HD'

# 截图和dump输出目录
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'output', 'screenshots', 'rss_strict'
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 7个源（代号映射）
SOURCES = [
    {'id': 1, 'code': '源[1]', 'prefix': '天籁'},
    {'id': 2, 'code': '源[2]', 'prefix': '撸色'},
    {'id': 3, 'code': '源[3]', 'prefix': '青涩'},
    {'id': 4, 'code': '源[4]', 'prefix': '窝窝'},
    {'id': 5, 'code': '源[5]', 'prefix': '桃花'},
    {'id': 6, 'code': '源[6]', 'prefix': '秘密'},
    {'id': 7, 'code': '源[7]', 'prefix': 'Papa'},
]


# ==================== 工具函数 ====================
def run_adb(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} {cmd}'
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)
        return r
    except subprocess.TimeoutExpired:
        return None


def screenshot(name):
    """截图保存到输出目录"""
    path = os.path.join(OUTPUT_DIR, f'{name}.png')
    try:
        d.screenshot(path)
        print(f'  [SCREENSHOT] {path}', flush=True)
    except Exception as e:
        print(f'  [SCREENSHOT-FAIL] {name}: {e}', flush=True)
    return path


def dump_hierarchy(name):
    """dump UI hierarchy到本地XML文件（安全过滤版）"""
    remote = '/data/local/tmp/ui_dump.xml'
    local = os.path.join(OUTPUT_DIR, f'{name}.xml')
    try:
        run_adb('shell uiautomator dump /data/local/tmp/ui_dump.xml', timeout=15)
        run_adb(f'pull {remote} {local}', timeout=15)
        print(f'  [DUMP] {local}', flush=True)
        return local
    except Exception as e:
        print(f'  [DUMP-FAIL] {name}: {e}', flush=True)
        return None


def parse_dump_safe(xml_path, max_text_len=0):
    """解析UI dump，提取技术字段（resource-id, class, bounds, clickable）
    max_text_len: 0=完全过滤text, >0=允许最长N字符的text（用于调试分类标签）
    返回: list of dict
    """
    if not xml_path or not os.path.exists(xml_path):
        return []
    result = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for elem in root.iter('node'):
            rid = elem.get('resource-id', '')
            cls = elem.get('class', '')
            bounds = elem.get('bounds', '')
            clickable = elem.get('clickable', 'false')
            scrollable = elem.get('scrollable', 'false')
            text_val = elem.get('text', '')
            content_desc = elem.get('content-desc', '')

            short_cls = cls.split('.')[-1] if cls else ''
            short_rid = rid.split(':id/')[-1] if ':id/' in rid else rid

            entry = {
                'rid_short': short_rid,
                'cls_short': short_cls,
                'clickable': clickable,
                'scrollable': scrollable,
                'bounds': bounds,
            }

            # 只在调试模式下保留短text（用于确认分类标签）
            if max_text_len > 0 and text_val and len(text_val) <= max_text_len:
                entry['text'] = text_val

            result.append(entry)
    except Exception as e:
        print(f'  [PARSE-FAIL] {e}', flush=True)
    return result


def get_current_activity():
    cur = d.app_current()
    return cur.get('activity', '?')


def go_back(times=1):
    for _ in range(times):
        d.press('back')
        time.sleep(1.5)


def go_back_to_main():
    for _ in range(8):
        act = get_current_activity()
        if 'MainActivity' in act:
            return True
        d.press('back')
        time.sleep(1.5)
    return False


def close_popups():
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过', '以后再说', '取消']:
        btn = d(text=txt)
        if btn.exists(timeout=0.5):
            try:
                btn.click()
                time.sleep(0.5)
            except Exception:
                pass


def find_tab_labels(dump_data):
    """从dump数据中查找TabLayout相关的标签
    重点找：item_tab, mTabLayout, TabLayout等组件
    返回: (标签数量, 标签列表)
    """
    tab_labels = []
    tab_rids = ['item_tab', 'mTabLayout', 'tab_item', 'tabs', 'tabtext']
    tab_cls = ['TabLayout', 'TabItem', 'HorizontalScrollView']

    for entry in dump_data:
        rid = entry.get('rid_short', '')
        cls = entry.get('cls_short', '')
        # 查找TabLayout中的标签
        if any(t in rid.lower() for t in tab_rids):
            if entry.get('text'):
                tab_labels.append(entry['text'])
        # 查找TabLayout class
        if 'TabLayout' in cls or 'TabItem' in cls:
            if entry.get('text'):
                tab_labels.append(entry['text'])

    # 如果上面没找到，尝试找TabLayout容器内的所有TextView
    # （这需要更复杂的XML解析，先返回已有结果）
    return len(tab_labels), tab_labels


def count_tabs_from_ui():
    """直接通过u2查找TabLayout中的标签数量"""
    tab_count = 0

    # 方法1: item_tab resourceId
    item_tabs = d(resourceId=f'{ID}item_tab')
    if item_tabs.exists(timeout=2):
        tab_count = item_tabs.count
        print(f'  [TABS] item_tab count: {tab_count}', flush=True)
        return tab_count

    # 方法2: mTabLayout的子元素
    tab_layout = d(resourceId=f'{ID}mTabLayout')
    if tab_layout.exists(timeout=2):
        try:
            children = tab_layout.child(className='android.widget.LinearLayout')
            if children.exists(timeout=1):
                tab_count = children.count
                print(f'  [TABS] mTabLayout LinearLayout children: {tab_count}', flush=True)
                return tab_count
        except Exception:
            pass
        try:
            children2 = tab_layout.child(className='android.widget.TextView')
            if children2.exists(timeout=1):
                tab_count = children2.count
                print(f'  [TABS] mTabLayout TextView children: {tab_count}', flush=True)
                return tab_count
        except Exception:
            pass

    # 方法3: 查找SlidingTabLayout或TabLayout class
    tab_cls = d(className='com.google.android.material.tabs.TabLayout')
    if tab_cls.exists(timeout=2):
        try:
            tab_views = tab_cls.child(className='android.widget.LinearLayout')
            if tab_views.exists(timeout=1):
                tab_count = tab_views.count
                print(f'  [TABS] Material TabLayout children: {tab_count}', flush=True)
                return tab_count
        except Exception:
            pass

    # 方法4: 查找特定区域的TextView（TabLayout区域的标签）
    # TabLayout一般在屏幕上半部分，检查该区域的TextView
    all_tv = d(className='android.widget.TextView')
    if all_tv.exists(timeout=2):
        count = all_tv.count
        # 过滤：只看屏幕上半部分（y<500）且文本长度2-15的
        upper_labels = []
        for i in range(min(count, 80)):
            try:
                info = all_tv[i].info
                bounds = info.get('bounds', {})
                top = bounds.get('top', 999)
                txt = info.get('text', '')
                rid = info.get('resourceName', '').split(':id/')[-1] if info.get('resourceName') else ''
                # Tab区域一般在y<600
                if top < 600 and txt and 2 <= len(txt) <= 15:
                    # 排除标题栏（通常是长标题或固定文本）
                    if rid not in ['tv_title', 'tv_name', 'toolbar_title', 'title']:
                        upper_labels.append({'text': txt, 'rid': rid, 'top': top})
            except Exception:
                continue
        if upper_labels:
            # 去重相近位置的标签（同一行只计一次）
            seen_tops = set()
            unique_labels = []
            for lb in sorted(upper_labels, key=lambda x: x['top']):
                rounded_top = round(lb['top'] / 10) * 10
                if rounded_top not in seen_tops:
                    seen_tops.add(rounded_top)
                    unique_labels.append(lb)
            if len(unique_labels) >= 2:
                # 这些可能是标签，但需要排除标题
                tab_count = len(unique_labels)
                print(f'  [TABS] Upper-region labels: {tab_count}', flush=True)
                for lb in unique_labels:
                    print(f'    label: rid={lb["rid"]}, top={lb["top"]}', flush=True)

    print(f'  [TABS] Final tab count: {tab_count}', flush=True)
    return tab_count


def count_articles():
    """统计当前页面的文章数量"""
    titles = d(resourceId=f'{ID}tv_title')
    count = 0
    if titles.exists(timeout=2):
        count = titles.count

    # 备选检查
    if count == 0:
        texts = d(resourceId=f'{ID}tv_text')
        if texts.exists(timeout=2):
            count = texts.count

    return count


# ==================== 连接设备 ====================
print('=' * 70, flush=True)
print('严格验证7个订阅源 - 分类标签 + 搜索功能', flush=True)
print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
print('=' * 70, flush=True)

d = u2.connect(HOST)
d.implicitly_wait(3)

# ==================== 启动App ====================
print('\n[Phase 0] 启动App...', flush=True)
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)

close_popups()
time.sleep(1)
close_popups()

cur_act = get_current_activity()
print(f'  Activity: {cur_act}', flush=True)

if 'MainActivity' not in cur_act:
    # 可能还在Welcome或其他页
    time.sleep(5)
    close_popups()
    cur_act = get_current_activity()
    print(f'  Activity (retry): {cur_act}', flush=True)

# ==================== 导航到订阅源列表 ====================
print('\n[Phase 1] 导航到订阅源列表...', flush=True)

# 先确保在MainActivity
go_back_to_main()
time.sleep(1)

# 点击底部订阅tab
rss_tab = d(resourceId=f'{ID}menu_rss')
if rss_tab.exists(timeout=5):
    rss_tab.click()
    time.sleep(3)
    print('  点击menu_rss成功', flush=True)
else:
    # 备选：文本匹配
    for txt in ['订阅', '发现', 'RSS']:
        tab = d(text=txt)
        if tab.exists(timeout=2):
            tab.click()
            time.sleep(3)
            print(f'  通过文本"{txt}"点击成功', flush=True)
            break

screenshot('0_rss_source_list')
dump_hierarchy('0_rss_source_list')

# ==================== 逐个测试每个源 ====================
results = {}

for src in SOURCES:
    sid = src['id']
    code = src['code']
    prefix = src['prefix']
    result = {
        'id': sid,
        'code': code,
        'nav_ok': False,
        'activity': '',
        'tab_count': 0,
        'tab_labels': [],
        'article_count_initial': 0,
        'article_count_after_wait': 0,
        'search_nav_ok': False,
        'search_activity': '',
        'search_result_count': 0,
        'errors': [],
    }

    print(f'\n{"="*70}', flush=True)
    print(f'[TEST] {code} (id={sid})', flush=True)
    print(f'{"="*70}', flush=True)

    # 确保回到订阅源列表
    go_back_to_main()
    time.sleep(1)
    rss_tab = d(resourceId=f'{ID}menu_rss')
    if rss_tab.exists(timeout=3):
        rss_tab.click()
        time.sleep(2)

    # ===== Step 1: 找到源并点击进入 =====
    print(f'\n  [Step 1] 导航到源[{sid}]...', flush=True)

    # 先尝试精确匹配tv_name
    found = False
    source_el = d(resourceId=f'{ID}tv_name', textContains=prefix)
    if source_el.exists(timeout=3):
        try:
            source_el.click()
            found = True
        except Exception:
            pass

    # 滚动查找
    if not found:
        for scroll_attempt in range(8):
            items = d(resourceId=f'{ID}tv_name')
            if items.exists(timeout=2):
                for i in range(items.count):
                    try:
                        txt = items[i].get_text()
                        if prefix in txt:
                            items[i].click()
                            found = True
                            break
                    except Exception:
                        continue
            if found:
                break
            d.swipe(500, 800, 500, 300, 0.3)
            time.sleep(1)

    if not found:
        # 尝试text直接匹配
        el2 = d(textContains=prefix)
        if el2.exists(timeout=2):
            try:
                el2.click()
                found = True
            except Exception:
                pass

    if not found:
        print(f'  [FAIL] 未找到源[{sid}]', flush=True)
        result['errors'].append('source not found')
        results[code] = result
        continue

    # 等待进入源页面
    time.sleep(5)
    act = get_current_activity()
    result['activity'] = act.split('.')[-1] if act else '?'
    result['nav_ok'] = True
    print(f'  Activity: {result["activity"]}', flush=True)

    # ===== Step 2: 截图1 - 进入源后的初始页面 =====
    print(f'\n  [Step 2] 截图初始页面...', flush=True)
    screenshot(f's{sid}_1_initial')
    dump_hierarchy(f's{sid}_1_initial')

    # ===== Step 3: 等待15秒让JS执行+网络请求完成 =====
    print(f'\n  [Step 3] 等待15秒(JS+网络)...', flush=True)
    time.sleep(15)

    # ===== Step 4: 截图2 - 等待后的页面 =====
    print(f'\n  [Step 4] 截图等待后页面...', flush=True)
    screenshot(f's{sid}_2_after_wait')
    dump_file = dump_hierarchy(f's{sid}_2_after_wait')

    # ===== Step 5: 检查分类标签 =====
    print(f'\n  [Step 5] 检查分类标签...', flush=True)

    # 从dump数据中查找TabLayout标签（允许短text用于确认分类）
    if dump_file:
        dump_data = parse_dump_safe(dump_file, max_text_len=20)
        tab_num, tab_labels = find_tab_labels(dump_data)
        result['tab_labels'] = tab_labels
        # 输出关键结构信息（只输出rid和cls，不输出text内容）
        for entry in dump_data:
            rid = entry.get('rid_short', '')
            cls = entry.get('cls_short', '')
            if any(kw in rid.lower() for kw in ['tab', 'sort', 'item_', 'viewpager', 'pager']):
                print(f'    结构: rid={rid}, cls={cls}', flush=True)
            if any(kw in cls.lower() for kw in ['tablayout', 'tabitem', 'viewpager', 'recycler']):
                print(f'    结构: rid={rid}, cls={cls}', flush=True)

    # 通过u2直接检查
    tab_count = count_tabs_from_ui()
    result['tab_count'] = tab_count

    # 额外检查: ViewPager是否存在
    vp = d(resourceId=f'{ID}view_pager')
    if vp.exists(timeout=2):
        print(f'  ViewPager存在', flush=True)
    else:
        vp2 = d(className='androidx.viewpager.widget.ViewPager')
        if vp2.exists(timeout=2):
            print(f'  ViewPager(v2)存在', flush=True)

    # ===== Step 6: 检查文章列表 =====
    print(f'\n  [Step 6] 检查文章列表...', flush=True)
    article_count = count_articles()
    result['article_count_after_wait'] = article_count
    print(f'  文章数: {article_count}', flush=True)

    # 如果有分类标签，点击第一个标签后再检查
    if tab_count > 0:
        print(f'  尝试点击第一个分类标签...', flush=True)
        item_tab = d(resourceId=f'{ID}item_tab')
        if item_tab.exists(timeout=2):
            try:
                item_tab[0].click()
                time.sleep(5)
                article_after_tab = count_articles()
                print(f'  点击标签后文章数: {article_after_tab}', flush=True)
                if article_after_tab > article_count:
                    result['article_count_after_wait'] = article_after_tab
            except Exception as e:
                print(f'  点击标签失败: {e}', flush=True)

    # ===== Step 7: 记录当前Activity =====
    act = get_current_activity()
    result['activity'] = act.split('.')[-1] if act else '?'
    print(f'  当前Activity: {result["activity"]}', flush=True)

    # ===== Step 8: 搜索测试 =====
    print(f'\n  [Step 8] 搜索测试...', flush=True)

    # 点击搜索按钮
    search_btn = d(resourceId=f'{ID}menu_search')
    if not search_btn.exists(timeout=3):
        # 尝试overflow menu
        more_btn = d(description='更多选项')
        if more_btn.exists(timeout=2):
            more_btn.click()
            time.sleep(1)
            search_item = d(text='搜索')
            if search_item.exists(timeout=2):
                search_item.click()
                time.sleep(1)
                result['search_nav_ok'] = True
        else:
            print(f'  [SEARCH-FAIL] 未找到搜索按钮', flush=True)
            result['errors'].append('no search button')
    else:
        search_btn.click()
        time.sleep(3)
        result['search_nav_ok'] = True

    if result['search_nav_ok']:
        # 截图3：搜索界面
        search_act = get_current_activity()
        result['search_activity'] = search_act.split('.')[-1] if search_act else '?'
        print(f'  搜索Activity: {result["search_activity"]}', flush=True)
        screenshot(f's{sid}_3_search_ui')
        dump_hierarchy(f's{sid}_3_search_ui')

        # 在搜索框输入关键词
        search_input = d(resourceId=f'{ID}search_src_text')
        if not search_input.exists(timeout=3):
            search_input = d(className='android.widget.EditText')

        if search_input.exists(timeout=3):
            search_input.set_text(SEARCH_KEYWORD)
            time.sleep(1)
            # 提交搜索
            d.press('enter')
            time.sleep(3)

            # 截图4：搜索结果（等待30秒）
            print(f'  等待30秒搜索结果...', flush=True)
            time.sleep(30)

            screenshot(f's{sid}_4_search_result')
            dump_hierarchy(f's{sid}_4_search_result')

            # 检查搜索结果
            search_count = count_articles()
            result['search_result_count'] = search_count
            print(f'  搜索结果数: {search_count}', flush=True)

            # 检查搜索结果Activity
            search_act2 = get_current_activity()
            print(f'  搜索结果Activity: {search_act2.split(".")[-1] if search_act2 else "?"}', flush=True)

            # 额外检查: RecyclerView
            rv = d(className='androidx.recyclerview.widget.RecyclerView')
            if rv.exists(timeout=2):
                try:
                    rv_count = rv.child().count
                    print(f'  RecyclerView子项数: {rv_count}', flush=True)
                except Exception:
                    pass

            # 如果没结果，再等10秒重试
            if search_count == 0:
                print(f'  无结果，再等10秒...', flush=True)
                time.sleep(10)
                search_count2 = count_articles()
                if search_count2 > 0:
                    result['search_result_count'] = search_count2
                    print(f'  延迟搜索结果数: {search_count2}', flush=True)
        else:
            print(f'  [SEARCH-FAIL] 未找到搜索输入框', flush=True)
            result['errors'].append('no search input')

    # 返回到主界面
    go_back_to_main()
    time.sleep(1)

    results[code] = result


# ==================== 汇总报告 ====================
print(f'\n{"="*70}', flush=True)
print('严格验证结果汇总', flush=True)
print(f'{"="*70}', flush=True)

print(f'\n{"代号":<8} {"导航":<5} {"Activity":<22} {"分类数":<7} {"文章数":<7} {"搜索导航":<7} {"搜索Activity":<22} {"搜索结果":<8} {"错误":<20}', flush=True)
print('-' * 110, flush=True)

for code, r in results.items():
    nav = 'OK' if r['nav_ok'] else 'FAIL'
    tabs = str(r['tab_count'])
    articles = str(r['article_count_after_wait'])
    search_nav = 'OK' if r['search_nav_ok'] else 'FAIL'
    search_count = str(r['search_result_count'])
    errors = '; '.join(r['errors']) if r['errors'] else ''

    print(f'{code:<8} {nav:<5} {r["activity"]:<22} {tabs:<7} {articles:<7} '
          f'{search_nav:<7} {r["search_activity"]:<22} {search_count:<8} {errors:<20}', flush=True)

print('-' * 110, flush=True)

# 分类统计
tab_ok = sum(1 for r in results.values() if r['tab_count'] > 0)
tab_fail_list = [r['code'] for r in results.values() if r['tab_count'] == 0 and r['nav_ok']]

# 搜索统计
search_ok = sum(1 for r in results.values() if r['search_result_count'] > 0)
search_fail_list = [r['code'] for r in results.values() if r['search_result_count'] == 0 and r['search_nav_ok']]

# 文章统计
article_ok = sum(1 for r in results.values() if r['article_count_after_wait'] > 0)
article_fail_list = [r['code'] for r in results.values() if r['article_count_after_wait'] == 0 and r['nav_ok']]

print(f'\n[分类标签] 成功: {tab_ok}/7', flush=True)
if tab_fail_list:
    print(f'[分类标签] 失败源: {", ".join(tab_fail_list)}', flush=True)

print(f'[文章列表] 成功: {article_ok}/7', flush=True)
if article_fail_list:
    print(f'[文章列表] 失败源: {", ".join(article_fail_list)}', flush=True)

print(f'[源内搜索] 成功: {search_ok}/7', flush=True)
if search_fail_list:
    print(f'[源内搜索] 失败源: {", ".join(search_fail_list)}', flush=True)

# 最终判定
all_ok = (tab_ok == 7 and article_ok == 7 and search_ok == 7)
print(f'\n最终判定: {"ALL PASS" if all_ok else "NEED FIX"}', flush=True)

print(f'\n截图和UI dump保存在: {OUTPUT_DIR}', flush=True)
print('=' * 70, flush=True)
