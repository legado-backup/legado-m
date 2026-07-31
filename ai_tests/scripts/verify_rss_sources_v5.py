# -*- coding: utf-8 -*-
"""
验证7个订阅源(v5)的文章列表加载和搜索功能
仅输出技术结论，禁止输出业务数据
"""

import uiautomator2 as u2
import time
import sys

PKG = "io.legado.miss.app.debug"
ID_PREFIX = f"{PKG}:id/"

# 源编号映射，输出时用代号
SOURCE_NAMES = [
    "源[1]", "源[2]", "源[3]", "源[4]", "源[5]", "源[6]", "源[7]"
]
SOURCE_REAL = [
    "天籁精选", "撸色精品", "青涩精选", "窝窝精选",
    "桃花视频", "秘密线路", "Papa线路"
]

MAX_WAIT = 60
CHECK_INTERVAL = 10
SEARCH_KEYWORD = "HD"


def connect_device():
    """连接设备"""
    d = u2.connect()
    d.implicitly_wait(3)
    return d


def ensure_app_running(d):
    """确保App运行在前台"""
    current = d.app_current()
    if current.get("package") != PKG:
        d.app_start(PKG)
        time.sleep(5)
    print(f"[INFO] App前台确认: package={current.get('package')}", flush=True)


def go_to_rss_source_list(d):
    """进入订阅源列表页面"""
    # 先回到主界面（多次back确保干净状态）
    for _ in range(3):
        d.press("back")
        time.sleep(0.3)

    # 确保在App内
    current = d.app_current()
    if current.get("package") != PKG:
        d.app_start(PKG)
        time.sleep(3)

    # 点击底部"订阅"tab - 使用resourceId定位
    rss_tab = d(resourceId=f"{ID_PREFIX}menu_rss")
    if rss_tab.exists(timeout=5):
        rss_tab.click()
        time.sleep(3)
        print("[INFO] 已点击底部订阅tab(menu_rss)", flush=True)
        return True

    # 备选：content-desc
    rss_tab2 = d(description="订阅")
    if rss_tab2.exists(timeout=3):
        rss_tab2.click()
        time.sleep(3)
        print("[INFO] 已通过content-desc点击订阅tab", flush=True)
        return True

    print("[WARN] 未能导航到订阅源列表，尝试直接启动Activity", flush=True)
    d.app_start(f"{PKG}/io.legado.app.ui.rss.RssActivity")
    time.sleep(3)
    return True


def find_and_click_source(d, source_name, retry=3):
    """在列表中找到源并点击进入"""
    for attempt in range(retry):
        el = d(text=source_name)
        if el.exists(timeout=3):
            el.click()
            time.sleep(2)
            return True

        # 尝试滚动查找 - 用try/except防止无scrollable元素报错
        try:
            scrollable = d(scrollable=True)
            if scrollable.exists(timeout=1):
                scrollable.scroll.to(text=source_name)
                time.sleep(1)
                el = d(text=source_name)
                if el.exists(timeout=2):
                    el.click()
                    time.sleep(2)
                    return True
        except Exception as e:
            print(f"[WARN] 滚动查找异常: {e}", flush=True)

        # 尝试fling向下滚动
        try:
            for _ in range(3):
                d(scrollable=True).fling.forward()
                time.sleep(0.5)
                el = d(text=source_name)
                if el.exists(timeout=1):
                    el.click()
                    time.sleep(2)
                    return True
        except Exception:
            pass

        print(f"[WARN] 源[{SOURCE_NAMES[SOURCE_REAL.index(source_name)]}] 第{attempt+1}次未找到", flush=True)

    return False


def wait_for_content(d, max_wait=MAX_WAIT, check_interval=CHECK_INTERVAL):
    """等待内容加载，返回(是否成功, 文章数量)"""
    elapsed = 0
    while elapsed < max_wait:
        # 检查 tv_title 或 tv_text
        titles = d(resourceId=f"{ID_PREFIX}tv_title")
        texts = d(resourceId=f"{ID_PREFIX}tv_text")
        title_count = titles.count if titles.exists(timeout=1) else 0
        text_count = texts.count if texts.exists(timeout=1) else 0
        article_count = max(title_count, text_count)

        if article_count > 0:
            # 尝试点击第一个分类tab
            try:
                tabs = d(resourceId=f"{ID_PREFIX}mTabLayout")
                if tabs.exists(timeout=2):
                    tab_items = tabs.child(className="android.widget.LinearLayout")
                    if tab_items.count > 0:
                        tab_items[0].click()
                        time.sleep(5)
                        # 重新计数
                        titles2 = d(resourceId=f"{ID_PREFIX}tv_title")
                        texts2 = d(resourceId=f"{ID_PREFIX}tv_text")
                        title_count2 = titles2.count if titles2.exists(timeout=2) else 0
                        text_count2 = texts2.count if texts2.exists(timeout=2) else 0
                        article_count = max(title_count2, text_count2)
            except Exception as e:
                print(f"[WARN] Tab点击异常: {e}", flush=True)

            return True, article_count

        time.sleep(check_interval)
        elapsed += check_interval

    return False, 0


def test_list_loading(d, source_name, source_code):
    """测试源的文章列表加载"""
    print(f"[INFO] === 测试列表加载: {source_code} ===", flush=True)

    if not find_and_click_source(d, source_name):
        print(f"[FAIL] {source_code} 列表加载: 未找到源入口", flush=True)
        return False, 0

    success, count = wait_for_content(d)

    # 返回
    d.press("back")
    time.sleep(2)

    if success:
        print(f"[PASS] {source_code} 列表加载: 成功, 文章数={count}", flush=True)
    else:
        print(f"[FAIL] {source_code} 列表加载: 超时, 文章数=0", flush=True)

    return success, count


def test_search(d, source_name, source_code):
    """测试源内搜索功能"""
    print(f"[INFO] === 测试源内搜索: {source_code} ===", flush=True)

    if not find_and_click_source(d, source_name):
        print(f"[FAIL] {source_code} 搜索: 未找到源入口", flush=True)
        return False, 0

    # 等待源页面加载
    time.sleep(10)

    # 点击搜索按钮
    search_btn = d(resourceId=f"{ID_PREFIX}menu_search")
    if not search_btn.exists(timeout=5):
        # 尝试overflow menu
        more_btn = d(description="更多选项")
        if more_btn.exists(timeout=2):
            more_btn.click()
            time.sleep(1)
            search_item = d(text="搜索")
            if search_item.exists(timeout=2):
                search_item.click()
                time.sleep(1)
        else:
            print(f"[FAIL] {source_code} 搜索: 未找到搜索按钮", flush=True)
            d.press("back")
            time.sleep(2)
            return False, 0
    else:
        search_btn.click()
        time.sleep(1)

    # 输入搜索关键词
    search_input = d(resourceId=f"{ID_PREFIX}search_src_text")
    if not search_input.exists(timeout=3):
        # 备选搜索框
        search_input = d(className="android.widget.EditText")
        if not search_input.exists(timeout=2):
            print(f"[FAIL] {source_code} 搜索: 未找到搜索输入框", flush=True)
            d.press("back")
            time.sleep(1)
            d.press("back")
            time.sleep(2)
            return False, 0

    search_input.set_text(SEARCH_KEYWORD)
    time.sleep(1)

    # 提交搜索
    d.press("enter")
    time.sleep(3)

    # 等待搜索结果
    success, count = wait_for_content(d, max_wait=MAX_WAIT)

    # 返回搜索界面再返回源列表
    d.press("back")
    time.sleep(1)
    d.press("back")
    time.sleep(2)

    if success:
        print(f"[PASS] {source_code} 搜索: 成功, 结果数={count}", flush=True)
    else:
        print(f"[FAIL] {source_code} 搜索: 超时, 结果数=0", flush=True)

    return success, count


def main():
    print("=" * 60, flush=True)
    print("订阅源(v5)列表加载+搜索功能验证", flush=True)
    print("=" * 60, flush=True)

    # 1. 连接设备
    print("[INFO] 连接设备...", flush=True)
    try:
        d = connect_device()
    except Exception as e:
        print(f"[ERROR] 设备连接失败: {e}", flush=True)
        sys.exit(1)

    # 2. 确保App运行
    print("[INFO] 确保App运行...", flush=True)
    ensure_app_running(d)

    # 3. 进入订阅源列表
    print("[INFO] 进入订阅源列表...", flush=True)
    go_to_rss_source_list(d)
    time.sleep(2)

    # 4. 测试列表加载
    print("\n" + "=" * 60, flush=True)
    print("第一部分：列表加载测试", flush=True)
    print("=" * 60, flush=True)

    list_results = {}
    for i, (real_name, code_name) in enumerate(zip(SOURCE_REAL, SOURCE_NAMES)):
        success, count = test_list_loading(d, real_name, code_name)
        list_results[code_name] = (success, count)
        # 每次测试后回到列表
        time.sleep(1)

    # 重新进入订阅源列表（确保状态干净）
    go_to_rss_source_list(d)
    time.sleep(2)

    # 5. 测试搜索功能
    print("\n" + "=" * 60, flush=True)
    print("第二部分：源内搜索测试", flush=True)
    print("=" * 60, flush=True)

    search_results = {}
    for i, (real_name, code_name) in enumerate(zip(SOURCE_REAL, SOURCE_NAMES)):
        success, count = test_search(d, real_name, code_name)
        search_results[code_name] = (success, count)
        time.sleep(1)

    # 6. 输出技术结论
    print("\n" + "=" * 60, flush=True)
    print("技术结论摘要", flush=True)
    print("=" * 60, flush=True)

    # 列表加载结论
    list_success = sum(1 for v in list_results.values() if v[0])
    list_fail = sum(1 for v in list_results.values() if not v[0])
    list_counts = [v[1] for v in list_results.values() if v[0]]
    list_min = min(list_counts) if list_counts else 0
    list_max = max(list_counts) if list_counts else 0

    print(f"\n[列表加载] 成功: {list_success}/7, 失败: {list_fail}/7", flush=True)
    if list_counts:
        print(f"[列表加载] 文章数范围: {list_min} ~ {list_max}", flush=True)
    for code, (ok, cnt) in list_results.items():
        status = "成功" if ok else "失败"
        print(f"  {code}: {status}, 文章数={cnt}", flush=True)

    # 搜索结论
    search_success = sum(1 for v in search_results.values() if v[0])
    search_fail = sum(1 for v in search_results.values() if not v[0])
    search_counts = [v[1] for v in search_results.values() if v[0]]
    search_min = min(search_counts) if search_counts else 0
    search_max = max(search_counts) if search_counts else 0

    print(f"\n[源内搜索] 成功: {search_success}/7, 失败: {search_fail}/7", flush=True)
    if search_counts:
        print(f"[源内搜索] 结果数范围: {search_min} ~ {search_max}", flush=True)
    for code, (ok, cnt) in search_results.items():
        status = "成功" if ok else "失败"
        print(f"  {code}: {status}, 结果数={cnt}", flush=True)

    # 失败源汇总
    failed_list = [code for code, (ok, _) in list_results.items() if not ok]
    failed_search = [code for code, (ok, _) in search_results.items() if not ok]
    if failed_list:
        print(f"\n[列表加载失败源]: {', '.join(failed_list)}", flush=True)
    if failed_search:
        print(f"[搜索失败源]: {', '.join(failed_search)}", flush=True)

    print("\n测试完成.", flush=True)


if __name__ == "__main__":
    main()
