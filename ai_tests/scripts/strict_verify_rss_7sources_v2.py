#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
严格验证7个订阅源 - 修复版 v2
修复要点：
1. 使用无包名前缀的resourceId查找（uiautomator dump包名可能不准）
2. 检测并处理VideoPlayer自动播放（按back回到文章列表）
3. 精确检测RssSortActivity的自定义TextView标签（非TabLayout）
4. 搜索使用SearchView（menu_search），检查searchUrl是否存在
5. 截图+dump确认每一步
"""

import uiautomator2 as u2
import time
import sys
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ==================== 配置 ====================
PKG_DEBUG = 'io.legado.miss.app.debug'
PKG_RELEASE = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
SEARCH_KEYWORD = 'HD'

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'output', 'screenshots', 'rss_strict_v2'
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


def rid(name):
    """生成两种包名前缀的resourceId列表，用于兼容查找"""
    return [
        f'{PKG_DEBUG}:id/{name}',
        f'{PKG_RELEASE}:id/{name}',
    ]


def find_element(d, resource_id_name, **kwargs):
    """查找元素，自动尝试两种包名前缀"""
    for prefix in rid(resource_id_name):
        el = d(resourceId=prefix, **kwargs)
        if el.exists(timeout=2):
            return el
    return None


def find_element_any(d, resource_id_name, **kwargs):
    """查找所有匹配的元素（返回最大count的那个）"""
    best = None
    best_count = 0
    for prefix in rid(resource_id_name):
        el = d(resourceId=prefix, **kwargs)
        if el.exists(timeout=2):
            cnt = el.count
            if cnt > best_count:
                best = el
                best_count = cnt
    return best


def screenshot(name):
    path = os.path.join(OUTPUT_DIR, f'{name}.png')
    try:
        d.screenshot(path)
        print(f'  [SCREENSHOT] {name}.png', flush=True)
    except Exception as e:
        print(f'  [SCREENSHOT-FAIL] {name}: {e}', flush=True)
    return path


def dump_hierarchy(name):
    remote = '/data/local/tmp/ui_dump_v2.xml'
    local = os.path.join(OUTPUT_DIR, f'{name}.xml')
    try:
        run_adb(f'shell uiautomator dump {remote}', timeout=15)
        run_adb(f'pull {remote} "{local}"', timeout=15)
        print(f'  [DUMP] {name}.xml', flush=True)
        return local
    except Exception as e:
        print(f'  [DUMP-FAIL] {name}: {e}', flush=True)
        return None


def parse_dump_full(xml_path):
    """解析UI dump，返回完整节点列表（包含text用于分析分类标签）"""
    if not xml_path or not os.path.exists(xml_path):
        return []
    result = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for elem in root.iter('node'):
            result.append({
                'rid': elem.get('resource-id', ''),
                'cls': elem.get('class', ''),
                'text': elem.get('text', ''),
                'content_desc': elem.get('content-desc', ''),
                'bounds': elem.get('bounds', ''),
                'clickable': elem.get('clickable', 'false'),
                'scrollable': elem.get('scrollable', 'false'),
                'package': elem.get('package', ''),
            })
    except Exception as e:
        print(f'  [PARSE-FAIL] {e}', flush=True)
    return result


def get_current_activity():
    cur = d.app_current()
    return cur.get('activity', '?')


def is_video_player_page():
    """检查当前是否在VideoPlayer页面"""
    act = get_current_activity()
    if 'VideoPlayer' in act:
        return True
    # 也检查UI元素
    for prefix in rid('playerView'):
        if d(resourceId=prefix).exists(timeout=1):
            return True
    for prefix in rid('surface_container'):
        if d(resourceId=prefix).exists(timeout=1):
            return True
    # 检查是否有视频播放控件
    if d(className='io.github.anilugoswarp.android.player.ExoPlayerView').exists(timeout=1):
        return True
    return False


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


def count_articles():
    """统计当前页面的文章数量"""
    count = 0
    for prefix in rid('tv_title'):
        titles = d(resourceId=prefix)
        if titles.exists(timeout=2):
            c = titles.count
            if c > count:
                count = c
    if count == 0:
        for prefix in rid('tv_text'):
            texts = d(resourceId=prefix)
            if texts.exists(timeout=2):
                c = texts.count
                if c > count:
                    count = c
    return count


def detect_tabs_from_dump(dump_data):
    """从UI dump数据中检测分类标签
    RssSortActivity的标签是自定义TextView，在tabsContainer（LinearLayout）中
    每行是HorizontalScrollView > LinearLayout > [TextView, TextView, ...]
    """
    tabs = []
    in_tabs_area = False
    
    # 查找tabsContainer
    tabs_container_found = False
    for node in dump_data:
        node_rid = node.get('rid', '')
        if 'tabsContainer' in node_rid:
            tabs_container_found = True
            break
    
    if not tabs_container_found:
        # 没有tabsContainer，可能只有1个分类（tabs被隐藏）
        return 0, []
    
    # 从tabsContainer中提取标签
    # tabsContainer的子元素是HorizontalScrollView，每个包含一行标签
    # 标签是TextView，有clickable=true
    for node in dump_data:
        node_rid = node.get('rid', '')
        cls = node.get('cls', '')
        text = node.get('text', '')
        bounds = node.get('bounds', '')

        # 查找可点击的TextView（标签按钮）
        # 标签在tabsContainer下方区域，通常是y坐标在120-300之间
        if 'TextView' in cls and text and len(text) >= 2 and len(text) <= 20:
            # 解析bounds获取y坐标
            try:
                import re
                m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if m:
                    y1 = int(m.group(2))
                    # 标签区域在toolbar下方（y>120）且在文章列表上方（y<500）
                    if 120 < y1 < 500:
                        # 排除toolbar标题和文章标题
                        short_rid = node_rid.split(':id/')[-1] if ':id/' in node_rid else ''
                        if short_rid not in ['tv_title', 'tv_name', 'toolbar_title', 'title', '']:
                            tabs.append({'text': text, 'rid': short_rid, 'y': y1})
                        elif short_rid == '':
                            # 无rid的TextView在标签区域，可能是分类标签
                            tabs.append({'text': text, 'rid': 'unknown', 'y': y1})
            except Exception:
                pass
    
    return len(tabs), tabs


def detect_tabs_from_ui():
    """通过u2直接检测分类标签
    RssSortActivity的标签是自定义TextView，在tabsContainer LinearLayout中
    """
    tab_count = 0
    
    # 方法1: 检查tabsContainer是否存在
    for prefix in rid('tabsContainer'):
        tc = d(resourceId=prefix)
        if tc.exists(timeout=2):
            print(f'  [TABS] tabsContainer存在', flush=True)
            # 查找tabsContainer中的可点击TextView
            try:
                # tabsContainer > HorizontalScrollView > LinearLayout > [TextView...]
                hsv = tc.child(className='android.widget.HorizontalScrollView')
                if hsv.exists(timeout=1):
                    row = hsv.child(className='android.widget.LinearLayout')
                    if row.exists(timeout=1):
                        tab_tvs = row.child(className='android.widget.TextView')
                        if tab_tvs.exists(timeout=1):
                            tab_count = tab_tvs.count
                            print(f'  [TABS] tabsContainer内TextView数: {tab_count}', flush=True)
                            return tab_count
            except Exception as e:
                print(f'  [TABS] tabsContainer遍历异常: {e}', flush=True)
    
    # 方法2: 查找屏幕上方区域的可点击短文本TextView
    # 这些可能是自定义标签
    all_tv = d(className='android.widget.TextView')
    if all_tv.exists(timeout=2):
        count = all_tv.count
        upper_labels = []
        for i in range(min(count, 100)):
            try:
                info = all_tv[i].info
                bounds = info.get('bounds', {})
                top = bounds.get('top', 999)
                txt = info.get('text', '')
                node_rid = info.get('resourceName', '').split(':id/')[-1] if info.get('resourceName') else ''
                clickable = info.get('clickable', False)

                # 标签区域：toolbar下方(y>120)，内容区域上方(y<500)
                if 120 < top < 500 and txt and 2 <= len(txt) <= 15 and clickable:
                    upper_labels.append({'text': txt, 'rid': node_rid, 'top': top, 'clickable': True})
            except Exception:
                continue
        
        if upper_labels:
            tab_count = len(upper_labels)
            print(f'  [TABS] 上方可点击TextView: {tab_count}', flush=True)
            for lb in upper_labels:
                print(f'    标签: rid={lb["rid"]}, top={lb["top"]}, len={len(lb["text"])}', flush=True)
            return tab_count
    
    # 方法3: 检查ViewPager的页面数（通过adapter count无法直接获取，但可以左右滑动测试）
    print(f'  [TABS] 未找到标签', flush=True)
    return 0


def check_search_available():
    """检查搜索功能是否可用（searchUrl是否存在）
    在RssSortActivity中，menu_search只在searchUrl非空时可见
    """
    # 检查menu_search是否可见
    for prefix in rid('menu_search'):
        search_btn = d(resourceId=prefix)
        if search_btn.exists(timeout=2):
            return True, 'menu_search可见'
    
    # 检查SearchView（可能是展开的搜索栏）
    for prefix in rid('search_src_text'):
        search_input = d(resourceId=prefix)
        if search_input.exists(timeout=2):
            return True, 'SearchView展开'
    
    # 检查overflow menu
    more_btn = d(description='更多选项')
    if more_btn.exists(timeout=1):
        return None, 'overflow_menu存在（需展开检查）'
    
    return False, '无搜索按钮'


# ==================== 连接设备 ====================
print('=' * 70, flush=True)
print('严格验证7个订阅源 v2 - 分类标签 + 搜索', flush=True)
print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
print('=' * 70, flush=True)

d = u2.connect(HOST)
d.implicitly_wait(3)

# ==================== 启动App ====================
print('\n[Phase 0] 启动App...', flush=True)
# 先关闭两个包
run_adb(f'shell am force-stop {PKG_DEBUG}')
run_adb(f'shell am force-stop {PKG_RELEASE}')
time.sleep(2)

# 启动debug包
run_adb(f'shell am start -n {PKG_DEBUG}/io.legado.app.ui.welcome.WelcomeActivity')
time.sleep(12)

close_popups()
time.sleep(1)
close_popups()

cur_act = get_current_activity()
print(f'  Activity: {cur_act}', flush=True)

# 确认debug包是前台
cur_pkg = d.app_current().get('package', '?')
print(f'  前台包: {cur_pkg}', flush=True)

# ==================== 导航到订阅源列表 ====================
print('\n[Phase 1] 导航到订阅源列表...', flush=True)
go_back_to_main()
time.sleep(1)

# 点击底部订阅tab
rss_tab = find_element(d, 'menu_rss')
if rss_tab:
    rss_tab.click()
    time.sleep(3)
    print('  点击menu_rss成功', flush=True)
else:
    for txt in ['订阅', '发现', 'RSS']:
        tab = d(text=txt)
        if tab.exists(timeout=2):
            tab.click()
            time.sleep(3)
            print(f'  通过文本点击成功', flush=True)
            break

screenshot('0_rss_source_list')

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
        'is_video_player': False,
        'tab_count': 0,
        'tab_source': '',
        'article_count': 0,
        'search_available': False,
        'search_detail': '',
        'search_result_count': 0,
        'errors': [],
    }

    print(f'\n{"="*70}', flush=True)
    print(f'[TEST] {code} (id={sid})', flush=True)
    print(f'{"="*70}', flush=True)

    # 确保回到订阅源列表
    go_back_to_main()
    time.sleep(1)
    rss_tab = find_element(d, 'menu_rss')
    if rss_tab:
        rss_tab.click()
        time.sleep(2)

    # ===== Step 1: 找到源并点击进入 =====
    print(f'\n  [Step 1] 导航到源[{sid}]...', flush=True)

    found = False
    # 尝试tv_name匹配
    for pkg_prefix in [PKG_DEBUG, PKG_RELEASE]:
        source_el = d(resourceId=f'{pkg_prefix}:id/tv_name', textContains=prefix)
        if source_el.exists(timeout=2):
            try:
                source_el.click()
                found = True
                break
            except Exception:
                pass

    # 滚动查找
    if not found:
        for _ in range(8):
            for pkg_prefix in [PKG_DEBUG, PKG_RELEASE]:
                items = d(resourceId=f'{pkg_prefix}:id/tv_name')
                if items.exists(timeout=1):
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
    time.sleep(3)
    act = get_current_activity()
    result['activity'] = act.split('.')[-1] if act else '?'
    result['nav_ok'] = True
    print(f'  Activity: {result["activity"]}', flush=True)

    # ===== Step 2: 检查是否自动进入了VideoPlayer =====
    print(f'\n  [Step 2] 检查页面类型...', flush=True)
    time.sleep(5)  # 等待页面加载

    is_vp = is_video_player_page()
    result['is_video_player'] = is_vp

    if is_vp:
        print(f'  [WARN] 检测到VideoPlayer，按back返回文章列表', flush=True)
        screenshot(f's{sid}_0_videoplayer')
        go_back()
        time.sleep(3)
        act = get_current_activity()
        print(f'  Back后Activity: {act.split(".")[-1] if act else "?"}', flush=True)

    # ===== Step 3: 截图初始页面 =====
    print(f'\n  [Step 3] 截图初始页面...', flush=True)
    screenshot(f's{sid}_1_initial')

    # ===== Step 4: 等待JS执行+网络请求 =====
    print(f'\n  [Step 4] 等待15秒(JS+网络)...', flush=True)
    time.sleep(15)

    # ===== Step 5: 截图等待后页面 + dump =====
    print(f'\n  [Step 5] 截图+dump等待后页面...', flush=True)
    screenshot(f's{sid}_2_after_wait')
    dump_file = dump_hierarchy(f's{sid}_2_after_wait')

    # ===== Step 6: 检查分类标签 =====
    print(f'\n  [Step 6] 检查分类标签...', flush=True)

    # 从dump数据检测
    if dump_file:
        dump_data = parse_dump_full(dump_file)
        dump_tab_count, dump_tabs = detect_tabs_from_dump(dump_data)
        print(f'  [DUMP-TABS] dump检测到 {dump_tab_count} 个标签', flush=True)
        
        # 输出关键结构
        for node in dump_data:
            node_rid = node.get('rid', '')
            cls = node.get('cls', '')
            text = node.get('text', '')
            short_rid = node_rid.split(':id/')[-1] if ':id/' in node_rid else node_rid
            short_cls = cls.split('.')[-1] if cls else ''
            
            # 输出tabsContainer相关的结构
            if any(kw in short_rid.lower() for kw in ['tab', 'sort', 'viewpager', 'pager', 'container']):
                # 过滤text输出，只显示技术结构
                text_info = f' text_len={len(text)}' if text else ''
                print(f'    结构: rid={short_rid}, cls={short_cls}{text_info}', flush=True)
            
            # 输出标签区域的TextView
            if short_cls == 'TextView' and text:
                try:
                    import re
                    m = re.match(r'\[(\d+),(\d+)\]', node.get('bounds', ''))
                    if m:
                        y = int(m.group(2))
                        if 120 < y < 500 and 2 <= len(text) <= 15:
                            clickable = node.get('clickable', 'false')
                            print(f'    上方TextView: rid={short_rid}, y={y}, clickable={clickable}, text_len={len(text)}', flush=True)
                except Exception:
                    pass
        
        result['tab_count'] = dump_tab_count
        result['tab_source'] = 'dump'

    # 通过u2直接检测
    ui_tab_count = detect_tabs_from_ui()
    if ui_tab_count > result['tab_count']:
        result['tab_count'] = ui_tab_count
        result['tab_source'] = 'ui'

    # 如果都没有标签，检查是否只有1个分类
    if result['tab_count'] == 0:
        # 检查viewPager的页面数
        for pkg_prefix in [PKG_DEBUG, PKG_RELEASE]:
            vp = d(resourceId=f'{pkg_prefix}:id/viewPager')
            if vp.exists(timeout=2):
                print(f'  ViewPager存在但无可见标签 → 可能只有1个分类（tabsContainer隐藏）', flush=True)
                break

    # ===== Step 7: 检查文章列表 =====
    print(f'\n  [Step 7] 检查文章列表...', flush=True)
    article_count = count_articles()
    result['article_count'] = article_count
    print(f'  文章数: {article_count}', flush=True)

    # ===== Step 8: 搜索测试 =====
    print(f'\n  [Step 8] 搜索测试...', flush=True)

    # 检查搜索是否可用
    search_ok, search_detail = check_search_available()
    result['search_detail'] = search_detail

    if search_ok is True:
        result['search_available'] = True
        print(f'  搜索可用: {search_detail}', flush=True)

        # 点击搜索按钮
        search_btn = None
        for prefix in rid('menu_search'):
            sb = d(resourceId=prefix)
            if sb.exists(timeout=2):
                search_btn = sb
                break

        if search_btn:
            search_btn.click()
            time.sleep(2)
        else:
            # 搜索可能在overflow中
            more_btn = d(description='更多选项')
            if more_btn.exists(timeout=2):
                more_btn.click()
                time.sleep(1)
                search_item = d(text='搜索')
                if search_item.exists(timeout=2):
                    search_item.click()
                    time.sleep(1)

        screenshot(f's{sid}_3_search_ui')

        # 在搜索框输入关键词
        search_input = None
        for prefix in rid('search_src_text'):
            si = d(resourceId=prefix)
            if si.exists(timeout=3):
                search_input = si
                break

        if not search_input:
            search_input = d(className='android.widget.EditText')

        if search_input and search_input.exists(timeout=3):
            search_input.set_text(SEARCH_KEYWORD)
            time.sleep(1)
            d.press('enter')
            time.sleep(3)

            print(f'  等待30秒搜索结果...', flush=True)
            time.sleep(30)

            screenshot(f's{sid}_4_search_result')
            dump_hierarchy(f's{sid}_4_search_result')

            search_count = count_articles()
            result['search_result_count'] = search_count
            print(f'  搜索结果数: {search_count}', flush=True)

            # 检查搜索后Activity
            search_act = get_current_activity()
            print(f'  搜索后Activity: {search_act.split(".")[-1] if search_act else "?"}', flush=True)

            # 如果搜索结果数等于文章数，说明搜索可能没有真正生效
            if search_count == article_count and article_count > 0:
                print(f'  [WARN] 搜索结果数=文章数={search_count}，搜索可能未生效', flush=True)
                result['errors'].append('search_not_effective')
        else:
            print(f'  [SEARCH-FAIL] 未找到搜索输入框', flush=True)
            result['errors'].append('no search input')

    elif search_ok is False:
        print(f'  搜索不可用: {search_detail}', flush=True)
        result['errors'].append(f'no_search: {search_detail}')
    else:
        # None = 需要展开overflow检查
        print(f'  需展开overflow检查: {search_detail}', flush=True)
        more_btn = d(description='更多选项')
        if more_btn.exists(timeout=2):
            more_btn.click()
            time.sleep(1)
            screenshot(f's{sid}_3_overflow')
            # 检查是否有搜索选项
            search_item = d(text='搜索')
            if search_item.exists(timeout=2):
                result['search_available'] = True
                print(f'  overflow中有搜索选项', flush=True)
            else:
                # 列出所有菜单项
                menu_items = d(className='android.widget.TextView')
                if menu_items.exists(timeout=2):
                    for i in range(min(menu_items.count, 10)):
                        try:
                            txt = menu_items[i].get_text()
                            if txt and len(txt) <= 15:
                                print(f'    菜单项: len={len(txt)}', flush=True)
                        except Exception:
                            continue
            d.press('back')
            time.sleep(1)

    # 返回主界面
    go_back_to_main()
    time.sleep(1)

    results[code] = result


# ==================== 汇总报告 ====================
print(f'\n{"="*70}', flush=True)
print('严格验证结果汇总 v2', flush=True)
print(f'{"="*70}', flush=True)

header = f'{"代号":<8} {"导航":<5} {"VP":<4} {"Activity":<22} {"分类数":<7} {"文章数":<7} {"搜索可用":<7} {"搜索结果":<8} {"错误":<25}'
print(f'\n{header}', flush=True)
print('-' * 110, flush=True)

for code, r in results.items():
    nav = 'OK' if r['nav_ok'] else 'FAIL'
    vp = 'Y' if r['is_video_player'] else 'N'
    tabs = str(r['tab_count'])
    articles = str(r['article_count'])
    search_avail = 'Y' if r['search_available'] else 'N'
    search_count = str(r['search_result_count'])
    errors = '; '.join(r['errors']) if r['errors'] else ''

    print(f'{code:<8} {nav:<5} {vp:<4} {r["activity"]:<22} {tabs:<7} {articles:<7} '
          f'{search_avail:<7} {search_count:<8} {errors:<25}', flush=True)

print('-' * 110, flush=True)

# 分类统计
tab_ok = sum(1 for r in results.values() if r['tab_count'] > 0)
tab_fail_list = [r['code'] for r in results.values() if r['tab_count'] == 0 and r['nav_ok']]

# 文章统计
article_ok = sum(1 for r in results.values() if r['article_count'] > 0)
article_fail_list = [r['code'] for r in results.values() if r['article_count'] == 0 and r['nav_ok']]

# 搜索统计
search_available_count = sum(1 for r in results.values() if r['search_available'])
search_ok = sum(1 for r in results.values() if r['search_result_count'] > 0)
search_not_effective = [r['code'] for r in results.values() if 'search_not_effective' in r['errors']]
search_no_btn = [r['code'] for r in results.values() if not r['search_available'] and r['nav_ok']]

# 视频自动播放统计
vp_count = sum(1 for r in results.values() if r['is_video_player'])

print(f'\n[分类标签] 有标签: {tab_ok}/7, 无标签: {7-tab_ok}/7', flush=True)
if tab_fail_list:
    print(f'[分类标签] 无标签源: {", ".join(tab_fail_list)}', flush=True)

print(f'[文章列表] 有文章: {article_ok}/7', flush=True)
if article_fail_list:
    print(f'[文章列表] 无文章源: {", ".join(article_fail_list)}', flush=True)

print(f'[搜索可用] 搜索按钮可见: {search_available_count}/7', flush=True)
print(f'[搜索结果] 有结果: {search_ok}/7', flush=True)
if search_not_effective:
    print(f'[搜索结果] 结果=文章数(可能未生效): {", ".join(search_not_effective)}', flush=True)
if search_no_btn:
    print(f'[搜索结果] 无搜索按钮: {", ".join(search_no_btn)}', flush=True)

print(f'[视频自动播放] 进入源后自动播放: {vp_count}/7', flush=True)

# 最终判定
all_ok = (tab_ok == 7 and article_ok == 7 and search_ok == 7)
print(f'\n最终判定: {"ALL PASS" if all_ok else "NEED FIX"}', flush=True)

print(f'\n截图和UI dump保存在: {OUTPUT_DIR}', flush=True)
print('=' * 70, flush=True)
