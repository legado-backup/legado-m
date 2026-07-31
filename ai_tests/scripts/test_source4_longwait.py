#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试源[4]（窝窝精选）文章列表加载 - 长等待版本
该源sortUrl含JS，首次执行需ajax请求安全检测页+解析punycode域名，可能需15-20秒
输出仅保留技术结论
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
SOURCE_NAME = "窝窝精选"
SCREENSHOT_DIR = "ai_tests/reports"
LOGCAT_FILTERS = ["wowo", "Exception", "Error", "FATAL", "ajax", "cache",
                  "AnalyzeUrl", "RssSort", "RssArticle", "AppLog", "AnalyzeRule",
                  "RhinoJavaScriptEngine", "RhinoScriptRuntime", "JSBridge",
                  "WebView", "Cronet", "punycode", "sortUrl"]

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_adb(*args, timeout=15):
    cmd = [ADB_PATH] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def clear_logcat():
    rc, _, _ = run_adb("logcat", "-c")
    print(f"[INFO] logcat cleared: rc={rc}")

def dump_logcat_filtered():
    """抓取logcat，仅输出技术结论"""
    rc, stdout, stderr = run_adb("logcat", "-d", "-t", "800")
    if rc != 0:
        print(f"[ERROR] logcat capture failed: rc={rc}")
        return

    lines = stdout.splitlines()
    filtered = []
    for line in lines:
        for kw in LOGCAT_FILTERS:
            if kw.lower() in line.lower():
                filtered.append(line)
                break

    if not filtered:
        print("[LOGCAT] No matching technical lines found")
        return

    print(f"[LOGCAT] Filtered lines count: {len(filtered)}")
    # 只输出技术信息，脱敏处理
    for line in filtered:
        clean = line
        if len(clean) > 200:
            clean = clean[:200] + "..."
        # 跳过含敏感内容的行
        skip_patterns = ["http://", "https://", ".com/", ".cn/", ".net/",
                         "cookie", "Cookie", "token=", "password", "secret"]
        should_skip = False
        for p in skip_patterns:
            if p in clean:
                should_skip = True
                break
        if should_skip:
            # 提取异常类型即可
            if "Exception" in clean:
                print(f"  [TECH] {clean.split('Exception')[0]}Exception...")
            elif "Error" in clean:
                print(f"  [TECH] {clean.split('Error')[0]}Error...")
            continue
        print(f"  [LOG] {clean}")

def get_current_activity(d):
    """获取当前Activity名"""
    current = d.app_current()
    return current.get('activity', 'unknown'), current.get('package', 'unknown')

def count_articles(d):
    """统计当前页面文章数量，尝试多种resourceId"""
    count_by_title = d(resourceId=f"{RES_PREFIX}tv_title").count
    count_by_name = d(resourceId=f"{RES_PREFIX}tv_name").count
    count_by_text = d(resourceId=f"{RES_PREFIX}tv_text").count
    return max(count_by_title, count_by_name, count_by_text)

def check_ui_state(d, label=""):
    """检查UI状态并输出技术信息"""
    prefix = f"[{label}] " if label else ""
    
    # Activity
    activity, pkg = get_current_activity(d)
    print(f"{prefix}Activity: {activity.split('.')[-1] if activity != 'unknown' else 'unknown'}")
    
    # 关键UI元素
    vp = d(resourceId=f"{RES_PREFIX}view_pager").exists(timeout=1)
    tabs = d(resourceId=f"{RES_PREFIX}tabs_container").exists(timeout=1)
    item_tabs = d(resourceId=f"{RES_PREFIX}item_tab").count
    rv = d(resourceId=f"{RES_PREFIX}recycler_view").exists(timeout=1)
    rv_class = d(className="androidx.recyclerview.widget.RecyclerView").count
    articles = count_articles(d)
    progress = d(className="android.widget.ProgressBar").exists(timeout=0.5)
    
    print(f"{prefix}view_pager={vp} tabs_container={tabs} item_tab_count={item_tabs}")
    print(f"{prefix}recycler_view={rv} RecyclerView_class={rv_class} articles={articles} loading={progress}")
    
    return {
        "activity": activity,
        "view_pager": vp,
        "tabs_container": tabs,
        "item_tab_count": item_tabs,
        "articles": articles,
        "loading": progress,
    }

def main():
    print(f"[INFO] === 测试源[4]文章列表加载（长等待版） ===")
    print(f"[INFO] Package: {PKG}")
    print(f"[INFO] Resource prefix: {RES_PREFIX}")
    
    # Step 1: 连接设备
    print(f"\n[INFO] Connecting to device at {MEMU_ADB_HOST}...")
    d = u2.connect(MEMU_ADB_HOST)
    print(f"[INFO] Device info: {d.info.get('productName', 'unknown')}")
    
    # Step 2: 清除logcat
    clear_logcat()
    
    # Step 3: 确认App在前台
    current_pkg = d.app_current().get("package", "")
    if current_pkg != PKG:
        print(f"[WARN] 前台包: {current_pkg}, 启动目标App...")
        d.app_start(PKG)
        time.sleep(5)
    else:
        print(f"[INFO] App已在前台: {current_pkg}")
    
    # Step 4: 进入订阅页面
    print("\n[INFO] === Step 4: 进入订阅页面 ===")
    rss_tab = d(description="订阅", className="android.widget.FrameLayout")
    if not rss_tab.exists(timeout=5):
        rss_tab = d(description="订阅")
    if rss_tab.exists(timeout=3):
        rss_tab.click()
        print("[INFO] 已点击订阅tab")
        time.sleep(3)
    else:
        # 备用：用text查找
        rss_tab2 = d(text="订阅")
        if rss_tab2.exists(timeout=3):
            rss_tab2.click()
            print("[INFO] 已点击订阅tab(text)")
            time.sleep(3)
        else:
            print("[ERROR] 无法找到订阅入口")
            return
    
    # Step 5: 找到窝窝精选源并点击
    print(f"\n[INFO] === Step 5: 查找并点击源[4] ===")
    source_el = d(text=SOURCE_NAME)
    if not source_el.exists(timeout=3):
        # 先回到顶部
        for _ in range(5):
            d.swipe(500, 500, 500, 1500, duration=200)
            time.sleep(0.3)
        # 向下滚动查找
        for attempt in range(20):
            if d(text=SOURCE_NAME).exists(timeout=1):
                break
            d.swipe(500, 1500, 500, 500, duration=300)
            time.sleep(0.8)
    
    source_el = d(text=SOURCE_NAME)
    if source_el.exists(timeout=2):
        source_el.click()
        print(f"[INFO] 已点击源[4]")
    else:
        print(f"[ERROR] 源[4]未找到")
        dump_logcat_filtered()
        return
    
    # Step 6: 等待源页面加载（最多30秒）
    print(f"\n[INFO] === Step 6: 等待源页面加载 (max 30s) ===")
    page_loaded = False
    for i in range(30):
        # 检查RssSortActivity或RssArticlesActivity
        activity, _ = get_current_activity(d)
        if "RssSort" in activity or "RssArticle" in activity or "Rss" in activity:
            page_loaded = True
            print(f"[INFO] 进入源页面 (等待{i+1}s): {activity.split('.')[-1]}")
            break
        # 也检查UI元素
        vp = d(resourceId=f"{RES_PREFIX}view_pager").exists(timeout=0.5)
        tabs = d(resourceId=f"{RES_PREFIX}tabs_container").exists(timeout=0.5)
        rv = d(resourceId=f"{RES_PREFIX}recycler_view").exists(timeout=0.5)
        if vp or tabs or rv:
            page_loaded = True
            print(f"[INFO] 源页面UI元素已加载 (等待{i+1}s)")
            break
        time.sleep(1)
    
    if not page_loaded:
        print("[WARN] 30s内未检测到源页面Activity，继续等待...")
    
    # 额外等待5秒让页面稳定
    time.sleep(5)
    
    # Step 7: 截图+检查UI状态
    print(f"\n[INFO] === Step 7: 初始UI状态检查 ===")
    try:
        d.screenshot(os.path.join(SCREENSHOT_DIR, "source4_initial.png"))
        print("[INFO] 初始截图已保存")
    except:
        print("[WARN] 截图失败")
    
    state = check_ui_state(d, "INITIAL")
    
    # Step 8: 判断是否有分类标签tabs
    print(f"\n[INFO] === Step 8: 检查分类标签 ===")
    tabs_container = d(resourceId=f"{RES_PREFIX}tabs_container")
    item_tabs = d(resourceId=f"{RES_PREFIX}item_tab")
    tab_count = item_tabs.count if tabs_container.exists(timeout=1) else 0
    
    if tab_count > 0:
        print(f"[INFO] 发现{tab_count}个分类标签(item_tab)")
        # 点击第一个标签
        try:
            item_tabs[0].click()
            print(f"[INFO] 已点击第一个分类标签")
            time.sleep(5)
        except Exception as e:
            print(f"[WARN] 点击分类标签失败: {e}")
    else:
        print(f"[INFO] 无分类标签tabs_container，可能是直接显示文章列表模式")
        # 尝试其他tab识别方式
        # 查找y坐标在100-300范围内的TextView（可能是分类标签）
        text_views = d(className="android.widget.TextView")
        candidate_tabs = []
        for i in range(min(text_views.count, 50)):
            try:
                tab = text_views[i]
                bounds = tab.info.get('bounds', {})
                top = bounds.get('top', 9999)
                if 80 <= top <= 280:
                    left = bounds.get('left', 9999)
                    candidate_tabs.append((i, top, left))
            except:
                continue
        
        if len(candidate_tabs) >= 2:
            candidate_tabs.sort(key=lambda x: (x[1], x[2]))
            print(f"[INFO] 发现{len(candidate_tabs)}个候选分类标签(按位置)")
            try:
                first_idx = candidate_tabs[0][0]
                text_views[first_idx].click()
                print(f"[INFO] 已点击第一个候选标签 idx={first_idx}")
                time.sleep(5)
            except Exception as e:
                print(f"[WARN] 点击候选标签失败: {e}")
        else:
            print(f"[INFO] 候选分类标签不足2个，视为无分类模式")
    
    # Step 9: 等待文章列表加载（最多120秒，每10秒检查一次）
    print(f"\n[INFO] === Step 9: 等待文章列表加载 (max 120s, check every 10s) ===")
    print(f"[INFO] 注意: 源[4]的sortUrl JS首次执行可能需15-20秒(ajax+punycode)")
    
    start_time = time.time()
    last_count = -1
    stable_rounds = 0
    article_count = 0
    check_round = 0
    
    while time.time() - start_time < 120:
        check_round += 1
        time.sleep(10)
        elapsed = int(time.time() - start_time)
        
        article_count = count_articles(d)
        
        if article_count > 0:
            print(f"[INFO] t={elapsed}s round={check_round}: article_count={article_count}")
            if article_count == last_count:
                stable_rounds += 1
                if stable_rounds >= 2:
                    print(f"[INFO] 文章数稳定({stable_rounds}轮不变)，停止等待")
                    break
            else:
                stable_rounds = 0
                last_count = article_count
            
            if article_count >= 3:
                # 再等5秒确认
                time.sleep(5)
                recheck = count_articles(d)
                print(f"[INFO] 确认: recheck_count={recheck}")
                if recheck > 0:
                    article_count = recheck
                    break
        else:
            # 无文章，输出诊断信息
            progress = d(className="android.widget.ProgressBar").exists(timeout=0.5)
            rv_class = d(className="androidx.recyclerview.widget.RecyclerView").count
            
            # 每30秒做一次详细诊断
            if elapsed % 30 == 0 or elapsed == 10:
                state = check_ui_state(d, f"t={elapsed}s")
                try:
                    d.screenshot(os.path.join(SCREENSHOT_DIR, f"source4_t{elapsed}s.png"))
                except:
                    pass
            else:
                print(f"[INFO] t={elapsed}s round={check_round}: no articles, loading={progress}, rv={rv_class}")
    
    final_elapsed = int(time.time() - start_time)
    print(f"\n[INFO] 等待结束: elapsed={final_elapsed}s, final_article_count={article_count}")
    
    # Step 10: 最终诊断
    print(f"\n[INFO] === Step 10: 最终诊断 ===")
    
    # 截图
    try:
        if article_count > 0:
            d.screenshot(os.path.join(SCREENSHOT_DIR, "source4_articles_loaded.png"))
        else:
            d.screenshot(os.path.join(SCREENSHOT_DIR, "source4_no_articles.png"))
        print("[INFO] 最终截图已保存")
    except:
        print("[WARN] 截图失败")
    
    # dump UI hierarchy
    try:
        xml = d.dump_hierarchy()
        xml_path = os.path.join(SCREENSHOT_DIR, "source4_final_ui.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[INFO] UI hierarchy dumped ({len(xml)} bytes)")
        
        # 从XML中提取技术信息
        import re
        # 所有resourceId
        all_ids = set(re.findall(r'resource-id="([^"]*)"', xml))
        # 只保留含项目前缀的
        project_ids = [rid for rid in all_ids if PKG in rid]
        print(f"[INFO] 项目resourceId数量: {len(project_ids)}")
        # 提取id名（不含包名前缀）
        id_names = sorted(set(rid.split("/")[-1] for rid in project_ids))
        print(f"[INFO] 项目ID列表: {id_names}")
    except Exception as e:
        print(f"[WARN] UI dump failed: {e}")
    
    # 检查Activity
    activity, _ = get_current_activity(d)
    print(f"[INFO] 当前Activity: {activity}")
    
    # 如果无文章，做额外检查
    if article_count == 0:
        print("\n[DIAG] 无文章，额外诊断:")
        
        # 检查是否有错误/空提示
        for rid in ["tv_empty", "tv_msg", "tv_error", "tv_tip", "tv_hint"]:
            el = d(resourceId=f"{RES_PREFIX}{rid}")
            if el.exists(timeout=1):
                try:
                    txt = el.get_text()
                    print(f"  [DIAG] {rid}: text_length={len(txt) if txt else 0}")
                except:
                    print(f"  [DIAG] {rid}: exists but text unavailable")
        
        # 检查RecyclerView子项
        rv = d(className="androidx.recyclerview.widget.RecyclerView")
        if rv.exists(timeout=1):
            try:
                child_count = rv.child(className="android.view.ViewGroup").count
                print(f"  [DIAG] RecyclerView子ViewGroup数: {child_count}")
            except:
                print(f"  [DIAG] RecyclerView子项统计失败")
        
        # 检查WebView（可能加载了网页而非列表）
        wv = d(className="android.webkit.WebView")
        if wv.exists(timeout=1):
            print(f"  [DIAG] WebView存在（可能加载了网页）")
        
        # 尝试下拉刷新
        print("\n[INFO] 尝试下拉刷新...")
        d.swipe(400, 600, 400, 200, duration=0.5)
        time.sleep(20)
        
        article_after_refresh = count_articles(d)
        print(f"[INFO] 刷新后文章数: {article_after_refresh}")
        if article_after_refresh > 0:
            article_count = article_after_refresh
        
        # 如果仍然无文章，尝试点击其他分类标签
        if article_count == 0:
            item_tabs = d(resourceId=f"{RES_PREFIX}item_tab")
            tab_count = item_tabs.count
            if tab_count > 1:
                print(f"\n[INFO] 尝试点击其他分类标签 (共{tab_count}个)...")
                for t_idx in range(1, min(tab_count, 4)):
                    try:
                        item_tabs[t_idx].click()
                        print(f"[INFO] 已点击第{t_idx+1}个标签")
                        time.sleep(20)
                        count = count_articles(d)
                        print(f"  文章数: {count}")
                        if count > 0:
                            article_count = count
                            break
                    except Exception as e:
                        print(f"  [WARN] 点击失败: {e}")
    
    # Step 11: 抓取logcat
    print(f"\n[INFO] === Step 11: 抓取logcat ===")
    dump_logcat_filtered()
    
    # 最终汇总
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 源[4]文章列表加载测试（长等待版）")
    print(f"  Package: {PKG}")
    print(f"  等待时间: {final_elapsed}s (max 120s)")
    print(f"  最终文章数: {article_count}")
    print(f"  分类标签数: {tab_count}")
    print(f"  Activity: {activity.split('.')[-1] if activity != 'unknown' else 'unknown'}")
    print(f"  测试结果: {'PASS' if article_count > 0 else 'FAIL'}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
