# -*- coding: utf-8 -*-
"""测试源[3]文章列表加载情况 - V5
使用正确的 resourceId (view_pager, tabs_container, title_bar)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uiautomator2 as u2
import subprocess
import time
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE

PKG = PACKAGE  # io.legado.miss.app.debug
RES_PREFIX = f"{PKG}:id/"
SOURCE_NAME = "青涩精选"

def run_adb(*args, timeout=15):
    cmd = [ADB_PATH] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def clear_logcat():
    rc, stdout, stderr = run_adb("logcat", "-c")
    if rc == 0:
        print("[INFO] logcat cleared")
    else:
        print(f"[WARN] logcat clear failed: rc={rc}")

def dump_logcat_filtered():
    rc, stdout, stderr = run_adb("logcat", "-d", "-t", "500")
    if rc != 0:
        print(f"[ERROR] logcat capture failed: rc={rc}")
        return

    lines = stdout.splitlines()
    keywords = ["Exception", "Error", "FATAL", "AnalyzeUrl", "rssArticle", "RssArticle",
                "RssSortViewModel", "RssArticlesViewModel", "AppLog", "AnalyzeRule",
                "RssArticle", "getRssArticles"]
    filtered = []
    for line in lines:
        for kw in keywords:
            if kw in line:
                filtered.append(line)
                break

    if not filtered:
        print("[LOGCAT] No matching technical lines found")
        return

    print(f"[LOGCAT] Filtered lines count: {len(filtered)}")
    for line in filtered:
        clean = line
        if len(clean) > 200:
            clean = clean[:200] + "..."
        skip_patterns = ["http://", "https://", ".com/", ".cn/", "cookie", "Cookie", "token="]
        should_skip = False
        for p in skip_patterns:
            if p in clean:
                should_skip = True
                break
        if should_skip:
            if "Exception" in clean:
                print(f"  [TECH] {clean.split('Exception')[0]}Exception...")
            elif "Error" in clean:
                print(f"  [TECH] {clean.split('Error')[0]}Error...")
            continue
        print(f"  [LOG] {clean}")

def main():
    print(f"[INFO] Connecting to device at {MEMU_ADB_HOST}...")
    d = u2.connect(MEMU_ADB_HOST)
    print(f"[INFO] Device info: {d.info.get('productName', 'unknown')}")

    # Step 1: Clear logcat
    clear_logcat()

    # Step 2: Launch app
    print(f"[INFO] Launching {PKG}...")
    d.app_start(PKG)
    time.sleep(4)

    # Step 3: Navigate to subscription page
    print("[INFO] Clicking 订阅 tab...")
    rss_tab = d(description="订阅", className="android.widget.FrameLayout")
    if rss_tab.exists(timeout=3):
        rss_tab.click()
        print("[INFO] Clicked 订阅 tab")
        time.sleep(3)

    # Step 4: Find and click source[3]
    print(f"[INFO] Searching for source[3]...")
    source_el = d(text=SOURCE_NAME)
    if not source_el.exists(timeout=5):
        for attempt in range(15):
            d.swipe(500, 1200, 500, 400, duration=0.3)
            time.sleep(1)
            source_el = d(text=SOURCE_NAME)
            if source_el.exists(timeout=2):
                break

    if source_el.exists(timeout=2):
        source_el.click()
        print(f"[INFO] Clicked source[3]")
    else:
        print(f"[ERROR] Source[3] not found")
        dump_logcat_filtered()
        return

    # Step 5: Wait for RssSortActivity to load
    print("[INFO] Waiting for RssSortActivity...")
    time.sleep(5)

    current = d.app_current()
    print(f"[INFO] Activity: {current.get('activity', 'unknown')}")

    if "RssSort" not in current.get('activity', ''):
        print("[ERROR] Not in RssSortActivity!")
        dump_logcat_filtered()
        return

    # Step 6: Verify key UI elements exist
    print("[INFO] Checking key UI elements...")
    vp = d(resourceId=f"{RES_PREFIX}view_pager")
    tabs = d(resourceId=f"{RES_PREFIX}tabs_container")
    title_bar = d(resourceId=f"{RES_PREFIX}title_bar")
    print(f"  view_pager exists: {vp.exists(timeout=2)}")
    print(f"  tabs_container exists: {tabs.exists(timeout=2)}")
    print(f"  title_bar exists: {title_bar.exists(timeout=2)}")

    # Step 7: Find category tabs and click the first one
    print("[INFO] Finding category tabs (y 100-300)...")
    text_views = d(className="android.widget.TextView")
    category_tabs = []
    for i in range(text_views.count):
        try:
            tab = text_views[i]
            bounds = tab.info.get('bounds', {})
            top = bounds.get('top', 9999)
            if 100 <= top <= 300:
                left = bounds.get('left', 9999)
                category_tabs.append((i, top, left))
        except:
            continue

    # Sort by (top, left) to get tabs in visual order
    category_tabs.sort(key=lambda x: (x[1], x[2]))
    print(f"[INFO] Found {len(category_tabs)} category tabs")

    if not category_tabs:
        print("[ERROR] No category tabs found!")
        dump_logcat_filtered()
        return

    # Click first tab
    first_tab_idx = category_tabs[0][0]
    print(f"[INFO] Clicking first category tab idx={first_tab_idx}")
    try:
        text_views[first_tab_idx].click()
        print("[INFO] Clicked first category tab")
    except Exception as e:
        print(f"[ERROR] Failed: {e}")

    # Step 8: Wait for articles - but also dump the XML for diagnosis
    print("[INFO] Waiting for article list (max 90s)...")
    time.sleep(5)

    # Take a screenshot for diagnosis
    try:
        d.screenshot("ai_tests/reports/source3_debug_screenshot.png")
        print("[INFO] Screenshot saved")
    except:
        print("[WARN] Screenshot failed")

    # Dump UI hierarchy for diagnosis
    try:
        xml = d.dump_hierarchy()
        with open("ai_tests/reports/source3_debug_ui.xml", "w", encoding="utf-8") as f:
            f.write(xml)
        print("[INFO] UI hierarchy dumped")
    except Exception as e:
        print(f"[WARN] UI dump failed: {e}")

    # Check for articles with correct resourceId
    start_time = time.time()
    last_count = -1
    stable_count = 0

    while time.time() - start_time < 90:
        # Try multiple possible article item resourceIds
        article_count = 0
        for rid in ["tv_title", "tv_name", "tv_text"]:
            views = d(resourceId=f"{RES_PREFIX}{rid}")
            c = views.count
            if c > 0:
                article_count = max(article_count, c)
                if c > 0 and rid != "tv_title":
                    print(f"[INFO] Found articles via {rid}: count={c}")

        elapsed = int(time.time() - start_time)

        if article_count > 0:
            print(f"[INFO] t={elapsed}s: article count = {article_count}")
            if article_count == last_count:
                stable_count += 1
                if stable_count >= 2:
                    break
            else:
                stable_count = 0
                last_count = article_count
            if article_count >= 3:
                time.sleep(5)
                break
        else:
            # Check for loading/error indicators
            progress = d(className="android.widget.ProgressBar")
            if progress.exists(timeout=0.5):
                print(f"[INFO] t={elapsed}s: ProgressBar visible (loading...)")

            # Check for RecyclerView
            rv = d(className="androidx.recyclerview.widget.RecyclerView")
            if rv.exists(timeout=0.5):
                print(f"[INFO] t={elapsed}s: RecyclerView found")

            if elapsed % 20 == 0 and elapsed > 0:
                print(f"[INFO] t={elapsed}s: no articles yet...")
                # Re-dump UI to see changes
                try:
                    xml = d.dump_hierarchy()
                    # Quick scan for tv_title in XML
                    if "tv_title" in xml:
                        print(f"  [DIAG] tv_title found in UI XML!")
                    if "RecyclerView" in xml:
                        print(f"  [DIAG] RecyclerView found in UI XML!")
                    if "tv_empty" in xml or "tv_msg" in xml:
                        print(f"  [DIAG] Empty/msg view found in UI XML!")
                except:
                    pass

        time.sleep(5)

    final_count = d(resourceId=f"{RES_PREFIX}tv_title").count
    print(f"\n[RESULT] Article count: {final_count}")

    # If no articles, try other tabs
    if final_count == 0:
        print("[WARN] No articles, trying other tabs...")
        for tab_idx, top, left in category_tabs[1:5]:
            try:
                text_views[tab_idx].click()
                print(f"[INFO] Clicked tab idx={tab_idx}")
                time.sleep(20)
                count = d(resourceId=f"{RES_PREFIX}tv_title").count
                print(f"  article count after tab: {count}")
                if count > 0:
                    final_count = count
                    break
            except:
                continue

    # Try pull-to-refresh
    if final_count == 0:
        print("[INFO] Trying pull-to-refresh...")
        # Swipe down in the content area
        d.swipe(400, 600, 400, 300, duration=0.5)
        time.sleep(15)
        final_count = d(resourceId=f"{RES_PREFIX}tv_title").count
        print(f"[INFO] After refresh: article count = {final_count}")

    # Final diagnostics
    if final_count == 0:
        print("\n[DIAG] Final diagnostics:")
        # Check content area
        tvs = d(className="android.widget.TextView")
        content_count = 0
        for i in range(tvs.count):
            try:
                bounds = tvs[i].info.get('bounds', {})
                if bounds.get('top', 0) > 250:
                    content_count += 1
            except:
                pass
        print(f"  Content area TextView count (y>250): {content_count}")

        # Check all views
        rv = d(className="androidx.recyclerview.widget.RecyclerView")
        print(f"  RecyclerView exists: {rv.exists(timeout=1)}")

        vp = d(resourceId=f"{RES_PREFIX}view_pager")
        print(f"  ViewPager exists: {vp.exists(timeout=1)}")

    # Step 9: Capture logcat
    print(f"\n[INFO] Capturing logcat...")
    dump_logcat_filtered()

    # Summary
    print(f"\n{'='*50}")
    print(f"[SUMMARY]")
    print(f"  Source[3] article list test:")
    print(f"  - Article count: {final_count}")
    print(f"  - Test status: {'PASS' if final_count > 0 else 'FAIL'}")
    print(f"  - Activity: RssSortActivity")
    print(f"  - Category tabs: {len(category_tabs)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
