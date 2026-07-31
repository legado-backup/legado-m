#!/usr/bin/env python3
"""逐个验证7个订阅源在Legado App中的列表加载情况
进入源→等待分类标签加载→点击第一个分类→等待文章列表加载→记录结果→返回
"""
import uiautomator2 as u2
import time
import sys
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG_RELEASE = 'io.legado.miss.app.release'
PKG_DEBUG = 'io.legado.miss.app.debug'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'

# 7个源（显示用代号，匹配用前缀）
SOURCES = [
    {'id': 1, 'label': '源[1]', 'prefix': '天籁'},
    {'id': 2, 'label': '源[2]', 'prefix': '撸色'},
    {'id': 3, 'label': '源[3]', 'prefix': '青涩'},
    {'id': 4, 'label': '源[4]', 'prefix': '窝窝'},
    {'id': 5, 'label': '源[5]', 'prefix': '桃花'},
    {'id': 6, 'label': '源[6]', 'prefix': '秘密'},
    {'id': 7, 'label': '源[7]', 'prefix': 'Papa'},
]

d = u2.connect(HOST)


def run_adb(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)
    return r


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
    """关闭可能的弹窗"""
    for txt in ['关闭', '同意', '确定', '否', 'OK', '跳过', '以后再说', '取消']:
        btn = d(text=txt)
        if btn.exists:
            try:
                btn.click()
                time.sleep(0.8)
            except Exception:
                pass


def navigate_to_explore_tab():
    """从主界面进入发现tab（订阅源列表）"""
    # 方法1: 通过底部导航栏的 menu_rss (最可靠)
    rss_tab = d(resourceId=f'{PKG}:id/menu_rss')
    if rss_tab.exists:
        rss_tab.click()
        time.sleep(2)
        return True

    # 方法2: 通过其他常见resourceId
    for rid in ['menu_explore', 'menu_find', 'menu_discovery']:
        tab = d(resourceId=f'{PKG}:id/{rid}')
        if tab.exists:
            tab.click()
            time.sleep(2)
            return True

    # 方法3: 通过文本匹配
    for txt in ['发现', '订阅', 'RSS']:
        tab = d(text=txt)
        if tab.exists:
            tab.click()
            time.sleep(2)
            return True

    # 方法4: 通过BottomNavigationView的子项点击第3个（通常是发现/RSS）
    bnv = d(className='com.google.android.material.bottomnavigation.BottomNavigationView')
    if bnv.exists:
        try:
            children = bnv.child(className='android.view.View')
            if children.count >= 3:
                children[2].click()
                time.sleep(2)
                return True
        except Exception:
            pass

    return False


def find_and_click_source(prefix):
    """在订阅源列表中找到指定源并点击，支持滚动查找"""
    # 先尝试直接匹配 tv_name
    source_el = d(resourceId=f'{PKG}:id/tv_name', textContains=prefix)
    if source_el.exists:
        try:
            source_el.click()
            time.sleep(3)
            return True
        except Exception:
            pass

    # 滚动查找
    for _ in range(10):
        # 检查当前可见的所有源名
        items = d(resourceId=f'{PKG}:id/tv_name')
        if items.exists:
            for i in range(items.count):
                try:
                    txt = items[i].get_text()
                    if prefix in txt:
                        items[i].click()
                        time.sleep(3)
                        return True
                except Exception:
                    continue
        # 向上滚动
        d.swipe(500, 800, 500, 300, 0.3)
        time.sleep(1)

    # 也尝试 text 直接匹配
    source_el2 = d(textContains=prefix)
    if source_el2.exists:
        try:
            source_el2.click()
            time.sleep(3)
            return True
        except Exception:
            pass

    return False


def wait_for_sort_tags(timeout=15):
    """等待分类标签加载，返回分类数量"""
    start = time.time()
    while time.time() - start < timeout:
        # 分类标签通常是TextView在RecyclerView中
        tags = d(className='android.widget.TextView')
        # 过滤掉太短的（可能是其他UI元素）
        count = 0
        if tags.exists:
            for i in range(min(tags.count, 50)):  # 限制遍历数量
                try:
                    txt = tags[i].get_text()
                    if len(txt) >= 2 and len(txt) <= 20:
                        count += 1
                except Exception:
                    continue
        if count >= 2:  # 至少2个分类才算成功
            return count
        time.sleep(2)
    return 0


def click_first_sort_tag():
    """点击第一个分类标签"""
    tags = d(className='android.widget.TextView')
    if tags.exists:
        for i in range(min(tags.count, 20)):
            try:
                txt = tags[i].get_text()
                if len(txt) >= 2 and len(txt) <= 20:
                    tags[i].click()
                    return txt
            except Exception:
                continue
    return None


def wait_for_articles(timeout=30):
    """等待文章列表加载，返回文章数量和是否有图片"""
    start = time.time()
    article_count = 0
    has_image = False

    while time.time() - start < timeout:
        # 检查 tv_title
        titles = d(resourceId=f'{PKG}:id/tv_title')
        if titles.exists and titles.count > 0:
            article_count = titles.count
            # 检查图片
            images = d(resourceId=f'{PKG}:id/iv_image')
            if images.exists and images.count > 0:
                has_image = True
            break
        time.sleep(3)

    # 再等一轮确认（可能还在加载更多）
    if article_count > 0:
        time.sleep(3)
        titles = d(resourceId=f'{PKG}:id/tv_title')
        if titles.exists:
            article_count = max(article_count, titles.count)
        images = d(resourceId=f'{PKG}:id/iv_image')
        if images.exists and images.count > 0:
            has_image = True

    return article_count, has_image


def test_source(src):
    """测试单个源：进入→分类→文章列表→返回"""
    label = src['label']
    prefix = src['prefix']
    result = {
        'id': src['id'],
        'label': label,
        'nav': 'FAIL',
        'sort_count': 0,
        'article_count': 0,
        'has_image': False,
        'error': '',
    }

    # 1. 在订阅源列表找到并点击源
    if not find_and_click_source(prefix):
        result['error'] = 'source not found in list'
        return result

    # 等待进入源页面
    time.sleep(3)
    act = get_current_activity()

    # 检查是否成功进入了源页面（RssSortActivity 或类似）
    if 'MainActivity' in act:
        result['error'] = 'did not enter source page'
        return result

    result['nav'] = 'OK'

    # 2. 等待分类标签加载
    sort_count = wait_for_sort_tags(timeout=15)
    result['sort_count'] = sort_count

    if sort_count == 0:
        result['error'] = 'no sort tags loaded'
        go_back()
        return result

    # 3. 点击第一个分类标签
    first_tag = click_first_sort_tag()
    if not first_tag:
        result['error'] = 'cannot click sort tag'
        go_back()
        return result

    time.sleep(2)

    # 4. 等待文章列表加载
    article_count, has_image = wait_for_articles(timeout=30)
    result['article_count'] = article_count
    result['has_image'] = has_image

    if article_count == 0:
        result['error'] = 'no articles loaded'

    # 5. 返回订阅源列表
    go_back(2)  # 从文章列表→源页面→源列表
    time.sleep(2)

    return result


# ==================== Main ====================
print("=" * 60)
print("7-Source List Loading Verification v2")
print("=" * 60)

# 清空logcat
run_adb('shell logcat -c')

# 尝试启动release包，若崩溃则回退debug包
PKG = PKG_RELEASE  # 默认用release
for try_pkg in [PKG_RELEASE, PKG_DEBUG]:
    run_adb(f'shell am force-stop {try_pkg}')
run_adb(f'shell logcat -c')  # 清空日志
time.sleep(2)

# 启动release包
run_adb(f'shell am start -n {PKG}/io.legado.app.ui.main.MainActivity')
time.sleep(8)

# 检查是否成功进入App
cur_act = get_current_activity()
print(f"Try release: Activity={cur_act}")

# 检查release进程是否存活
proc_check = run_adb(f'shell pidof {PKG}')
if not proc_check.stdout.strip() or 'launcher' in cur_act.lower():
    # release崩溃，回退debug
    print(f"[WARN] Release package crash (SQLite EACCES), falling back to debug package")
    run_adb(f'shell am force-stop {PKG}')
    PKG = PKG_DEBUG
    time.sleep(1)
    run_adb(f'shell am start -n {PKG}/io.legado.app.ui.main.MainActivity')
    time.sleep(10)
    cur_act = get_current_activity()
    print(f"Try debug: Activity={cur_act}")

# 如果仍在Launcher，尝试WelcomeActivity
if 'launcher' in cur_act.lower() or 'Launcher' in cur_act:
    print("[INFO] Still on launcher, trying WelcomeActivity...")
    run_adb(f'shell am start -n {PKG}/io.legado.app.ui.welcome.WelcomeActivity')
    time.sleep(12)
    cur_act = get_current_activity()
    print(f"Activity after WelcomeActivity: {cur_act}")

print(f"Using package: {PKG}")

# 关闭弹窗
close_popups()
time.sleep(1)
close_popups()

# 检查当前Activity
cur_act = get_current_activity()
print(f"Current activity after launch: {cur_act}")

# 进入发现tab（订阅源列表）
if not navigate_to_explore_tab():
    # 如果找不到tab，截图辅助调试
    print("[WARN] Cannot find explore tab, dumping info...")
    print(f"  Activity: {get_current_activity()}")
    # 尝试直接通过BottomNavigationView
    bnv = d(className='com.google.android.material.bottomnavigation.BottomNavigationView')
    print(f"  BNV exists: {bnv.exists}")
    # 尝试列出所有可见文本
    all_text = d(className='android.widget.TextView')
    if all_text.exists:
        for i in range(min(all_text.count, 15)):
            try:
                t = all_text[i].get_text()
                if t:
                    print(f"  TextView[{i}]: {t}")
            except Exception:
                pass
else:
    print("[OK] Navigate to RSS/explore tab success")

time.sleep(2)
close_popups()

results = []

for src in SOURCES:
    print(f"\n--- Testing {src['label']} ---")

    r = test_source(src)
    results.append(r)

    status = 'PASS' if r['article_count'] > 0 else 'FAIL'
    print(f"  Nav={r['nav']} Sorts={r['sort_count']} Articles={r['article_count']} "
          f"Images={'Y' if r['has_image'] else 'N'} Status={status} "
          f"{'Err:' + r['error'] if r['error'] else ''}")

    # 确保回到订阅源列表
    go_back_to_main()
    time.sleep(1)
    navigate_to_explore_tab()
    time.sleep(2)

# ==================== Summary ====================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"{'ID':<4} {'Label':<8} {'Nav':<5} {'Sorts':<7} {'Articles':<10} {'Img':<5} {'Status':<7} {'Error':<20}")
print("-" * 70)

pass_count = 0
fail_list = []

for r in results:
    is_pass = r['article_count'] > 0
    status = 'PASS' if is_pass else 'FAIL'
    if is_pass:
        pass_count += 1
    else:
        fail_list.append(f"源[{r['id']}]")
    print(f"{r['id']:<4} {r['label']:<8} {r['nav']:<5} {r['sort_count']:<7} "
          f"{r['article_count']:<10} {'Y' if r['has_image'] else 'N':<5} "
          f"{status:<7} {r['error']:<20}")

print("-" * 70)
print(f"Result: {pass_count}/{len(results)} passed")
if fail_list:
    print(f"Failed: {', '.join(fail_list)}")
else:
    print("ALL 7 SOURCES PASSED!")
print("=" * 60)
