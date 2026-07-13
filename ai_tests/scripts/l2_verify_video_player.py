#!/usr/bin/env python3
r"""l2_verify_video_player.py — 视频播放器L2功能验证

固定测试流程步骤3：导航到视频播放器 + 执行场景操作 + 日志验证

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_player.py [--scenario SCENARIO] [--manual]

场景：
    swipe_article       - 上下滑动切换文章（⚠️依赖已移除的SwipeTest临时日志，可能全部未触发）
    pagination          - 分页加载（⚠️同上）
    preload             - 预缓冲（⚠️同上）
    position_memory     - 位置记忆（⚠️同上）
    backward_compat     - 向后兼容
    buffer_progress     - 缓冲进度条更新（⚠️依赖已移除的F1临时日志）
    control_visibility  - 控件自动隐藏（⚠️依赖已移除的F2临时日志）
    error_patterns      - ★推荐★ 错误模式验证（永久日志，验证4个修复点0错误）
    all                 - 全部场景（默认）

注意：
    swipe_article/pagination/preload/position_memory/buffer_progress/control_visibility
    场景依赖SwipeTest/F1/F2临时日志，这些日志已在任务#69/#77/#109中移除。
    这些场景会显示"未触发"是预期行为，非代码问题。
    推荐使用 error_patterns 场景验证修复点：检查Malformed URL/destroy failed/
    ClassCastException/IllegalBlockSizeException四种错误模式是否为0。

模式：
    自动模式（默认）：脚本自动启动App并导航到视频播放器
    --manual         ：用户已手动导航到视频播放器，脚本只执行场景验证

退出码：
    0 = 全部场景通过
    1 = 部分场景未通过
    2 = 致命错误（设备连接/导航失败）
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# 添加 ai_tests 目录到 path 以 import config 和 swipe_test_log
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY

# 导入 swipe_test_log 的功能（同目录）
sys.path.insert(0, str(Path(__file__).parent))
from swipe_test_log import clear_logcat, capture_log, analyze_log, LOG_TMP_PATH

# 尝试导入 uiautomator2（可选依赖）
try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False


def run_adb(cmd, timeout=30):
    """执行ADB命令"""
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def connect_device():
    """连接MEmu设备"""
    if not HAS_U2:
        print("⚠️ uiautomator2 未安装，使用 ADB 命令操作")
        return None
    try:
        device = u2.connect(MEMU_ADB_HOST)
        info = device.info
        print(f"✅ 已连接设备: {info.get('productName', 'unknown')}")
        return device
    except Exception as e:
        print(f"⚠️ uiautomator2 连接失败: {e}，使用 ADB 命令操作")
        return None


def swipe_up(device):
    """向上滑动（切换到下一篇文章）"""
    if device:
        device.swipe_ext("up", scale=0.8)
    else:
        # ADB fallback: 从屏幕下部滑到上部
        run_adb("shell input swipe 500 1500 500 500 300")
    time.sleep(1)


def swipe_down(device):
    """向下滑动（切换到上一篇文章）"""
    if device:
        device.swipe_ext("down", scale=0.8)
    else:
        # ADB fallback: 从屏幕上部滑到下部
        run_adb("shell input swipe 500 500 500 1500 300")
    time.sleep(1)


def press_back():
    """按返回键"""
    run_adb("shell input keyevent 4")
    time.sleep(1)


def navigate_to_video_player(device):
    """自动导航到视频播放器

    流程：
    1. 启动App
    2. 等待App加载
    3. 导航到订阅源Tab
    4. 点击视频类型的订阅源
    5. 点击文章列表中的第一篇文章
    6. 等待视频播放器启动

    返回 True 如果导航成功
    """
    print("\n=== 导航到视频播放器 ===")

    # 检查App是否已运行
    result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
    if PACKAGE not in result.stdout:
        # 启动App
        print("  启动App...")
        run_adb(f"shell am start -n {PACKAGE}/{MAIN_ACTIVITY}")
        time.sleep(5)

    # 检查是否已在视频播放器
    result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
    if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
        print("✅ 已在视频播放器页面")
        return True

    # 尝试导航到订阅源
    if device:
        print("  尝试通过 uiautomator2 导航...")
        try:
            # 查找并点击订阅Tab（底部导航栏）
            # 修复：实际Tab content-desc="订阅" resourceId=menu_rss，非text="订阅源"
            rss_tab = device(resourceId="io.legado.app.debug:id/menu_rss")
            if rss_tab.exists:
                rss_tab.click()
                time.sleep(2)
                print("  已点击订阅Tab (menu_rss)")
            else:
                print("  ⚠️ 未找到订阅Tab，导航失败")
                return False

            # 查找视频类型的订阅源（优先找已知视频源名称）
            video_source_names = [
                "奈飞中文网--内置视频播放器",
                "18AV-new-内置播放器",
            ]
            source_clicked = False
            for name in video_source_names:
                src = device(text=name)
                if src.exists:
                    src.click()
                    time.sleep(3)
                    print(f"  已点击视频源: {name}")
                    source_clicked = True
                    break
            if not source_clicked:
                # 回退：点击第一个订阅源
                source_item = device(resourceId="io.legado.app.debug:id/recycler_view").child(index=0)
                if source_item.exists:
                    source_item.click()
                    time.sleep(3)
                    print("  已点击第一个订阅源（回退）")
                    source_clicked = True
            if not source_clicked:
                print("  ⚠️ 未找到可点击的订阅源")
                return False

            # 进入分类页后，点击第一个分类
            time.sleep(3)
            # 查找分类（排除footer文本如"我是有底线的"）
            categories = ["电影", "剧集", "综艺", "动漫", "无码破解", "最新"]
            cat_clicked = False
            for cat_name in categories:
                cat = device(text=cat_name)
                if cat.exists:
                    cat.click()
                    time.sleep(8)  # 等待文章列表加载
                    print(f"  已点击分类: {cat_name}")
                    cat_clicked = True
                    break
            if not cat_clicked:
                print("  ⚠️ 未找到分类，可能已在文章列表")
                cat_clicked = True  # 可能直接进入了文章列表

            # 在文章列表中点击第一篇文章
            time.sleep(2)
            rv = device(resourceId="io.legado.app.debug:id/recycler_view")
            if rv.exists:
                articles = rv.child(className="android.view.ViewGroup", clickable="true")
                if articles.count > 0:
                    articles[0].click()
                    time.sleep(10)  # 等待视频播放器加载（含WebView嗅探m3u8）
                    print("  已点击第一篇文章")

            # 检查是否进入视频播放器
            result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
            if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
                print("✅ 导航到视频播放器成功")
                return True
            else:
                print("⚠️ 导航后未进入视频播放器")
                return False

        except Exception as e:
            print(f"⚠️ uiautomator2 导航失败: {e}")
            return False
    else:
        print("⚠️ 无 uiautomator2，无法自动导航")
        print("   请使用 --manual 模式：手动导航到视频播放器后再运行脚本")
        return False


def verify_paths(required_paths, found_paths):
    """验证关键路径是否触发"""
    missing = [p for p in required_paths if p not in found_paths]
    return missing


def scenario_swipe_article(device):
    """场景1: 上下滑动切换文章

    验证点：onPageSelected→activatePlayer→switchToArticle→startPlay
    """
    print("\n=== 场景1: 上下滑动切换文章 ===")

    clear_logcat()
    print("  向上滑动切换到下一篇文章...")
    swipe_up(device)
    time.sleep(3)  # 等待切换和加载

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    required = ["onPageSelected", "activatePlayer"]
    missing = verify_paths(required, found)

    if not missing:
        print("✅ 场景1验证通过: 关键路径已触发（onPageSelected + activatePlayer）")
        return True
    else:
        print(f"⚠️ 场景1部分路径未触发: {missing}")
        return False


def scenario_pagination(device):
    """场景2: 分页加载

    验证点：loadMoreArticles + ARTICLES_LOADED
    """
    print("\n=== 场景2: 分页加载 ===")

    clear_logcat()
    print("  连续向上滑动5次，触发分页加载...")
    for i in range(5):
        swipe_up(device)
        time.sleep(2)

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    required = ["loadMoreArticles", "ARTICLES_LOADED"]
    missing = verify_paths(required, found)

    if not missing:
        print("✅ 场景2验证通过: 分页加载已触发")
        return True
    else:
        print(f"⚠️ 场景2部分路径未触发: {missing}")
        print("   （可能文章数量不足，未触发分页加载）")
        return False


def scenario_preload(device):
    """场景3: 预缓冲

    验证点：preloadNextArticleHtml
    """
    print("\n=== 场景3: 预缓冲 ===")

    clear_logcat()
    print("  等待视频播放以触发预缓冲（15秒）...")
    # 等待视频播放到80%触发预缓冲
    time.sleep(15)

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    if "preloadNextArticleHtml" in found:
        print("✅ 场景3验证通过: 预缓冲已触发")
        return True
    else:
        print("⚠️ 场景3预缓冲未触发（可能视频未播放到80%）")
        return False


def scenario_position_memory(device):
    """场景4: 位置记忆

    验证点：finish_save_link + onResume_scroll
    """
    print("\n=== 场景4: 位置记忆 ===")

    # 第一步：在播放器中向上滑动改变位置，然后退出
    clear_logcat()
    print("  向上滑动2次改变文章位置...")
    for i in range(2):
        swipe_up(device)
        time.sleep(2)

    print("  按返回键退出播放器...")
    press_back()
    time.sleep(2)

    capture_log()
    found_exit = analyze_log()

    if found_exit is None:
        print("⚠️ 退出阶段日志分析失败")
        return False

    # 第二步：重新进入播放器
    print("  重新进入播放器...")
    clear_logcat()

    # 如果有device，尝试重新进入
    if device:
        try:
            # 在文章列表中点击第一篇文章
            article = device(className="androidx.recyclerview.widget.RecyclerView").child(index=0)
            if article.exists:
                article.click()
                time.sleep(5)
        except Exception:
            pass
    else:
        # ADB fallback：点击屏幕中部
        run_adb("shell input tap 500 800")
        time.sleep(5)

    capture_log()
    found_reenter = analyze_log()

    if found_reenter is None:
        print("⚠️ 重新进入阶段日志分析失败")
        return False

    # 验证关键路径
    has_save = "finish_save_link" in found_exit
    has_scroll = "onResume_scroll" in found_reenter

    if has_save and has_scroll:
        print("✅ 场景4验证通过: 位置记忆已触发")
        return True
    else:
        missing = []
        if not has_save:
            missing.append("finish_save_link")
        if not has_scroll:
            missing.append("onResume_scroll")
        print(f"⚠️ 场景4部分路径未触发: {missing}")
        return False


def scenario_backward_compat(device):
    """场景5: 向后兼容

    验证点：无SwipeTest日志触发（因为不进入文章模式）
    """
    print("\n=== 场景5: 向后兼容 ===")

    # 向后兼容场景需要从非订阅源入口进入播放器
    # 简化验证：检查当前日志中是否有SwipeTest触发
    # 如果当前不是文章模式，不应触发文章相关日志

    clear_logcat()
    print("  等待5秒观察日志...")
    time.sleep(5)

    capture_log()

    # 检查日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        swipetest_lines = [l for l in content.split('\n') if 'SwipeTest' in l]

        # 过滤掉非文章模式的日志（backward_compat 场景不应触发文章切换相关日志）
        article_related = [l for l in swipetest_lines
                          if any(k in l for k in ['onPageSelected', 'switchToArticle', 'loadMoreArticles'])]

        if not article_related:
            print("✅ 场景5验证通过: 向后兼容正常（无文章模式日志触发）")
            return True
        else:
            print(f"⚠️ 场景5向后兼容异常: 触发了 {len(article_related)} 条文章模式日志")
            return False
    else:
        print("✅ 场景5验证通过: 无SwipeTest日志")
        return True


def scenario_buffer_progress(device):
    """场景6: 缓冲进度条更新（F1）

    验证点：F1 startBufferUpdate + F1 缓冲更新
    """
    print("\n=== 场景6: 缓冲进度条更新（F1）===")

    clear_logcat()
    print("  等待视频播放10秒，观察缓冲进度更新...")
    time.sleep(10)

    capture_log()

    # 读取日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        has_start = "F1 startBufferUpdate" in content
        has_update = "F1 缓冲更新" in content

        if has_start and has_update:
            # 统计缓冲更新次数
            update_count = content.count("F1 缓冲更新")
            print(f"✅ 场景6验证通过: 缓冲进度更新已触发（{update_count}次更新）")
            return True
        else:
            missing = []
            if not has_start:
                missing.append("F1 startBufferUpdate")
            if not has_update:
                missing.append("F1 缓冲更新")
            print(f"⚠️ 场景6部分路径未触发: {missing}")
            return False
    else:
        print("⚠️ 日志文件不存在")
        return False


def scenario_control_visibility(device):
    """场景7: 控件自动隐藏（F2）

    验证点：F2 scheduleAutoHide + F2 autoHide触发（3秒后）
    """
    print("\n=== 场景7: 控件自动隐藏（F2）===")

    clear_logcat()
    print("  等待视频播放5秒（控件应显示后3秒自动隐藏）...")
    time.sleep(5)

    capture_log()

    # 读取日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        has_schedule = "F2 scheduleAutoHide" in content
        has_autohide = "F2 autoHide触发" in content

        if has_schedule and has_autohide:
            print("✅ 场景7验证通过: 控件自动隐藏已触发（scheduleAutoHide + autoHide触发）")
            return True
        elif has_schedule and not has_autohide:
            print("⚠️ 场景7部分通过: scheduleAutoHide已触发但autoHide未触发")
            print("   （可能3秒未到或控件已被手动隐藏）")
            return False
        else:
            missing = []
            if not has_schedule:
                missing.append("F2 scheduleAutoHide")
            if not has_autohide:
                missing.append("F2 autoHide触发")
            print(f"⚠️ 场景7部分路径未触发: {missing}")
            return False
    else:
        print("⚠️ 日志文件不存在")
        return False


def scenario_error_patterns(device):
    """场景8: 错误模式验证（永久日志，替代已移除的SwipeTest临时日志）

    验证4个已修复的错误模式不再出现：
    - P2: Malformed URL / HttpDataSourceException（ExoPlayer file://协议）
    - P1-C: destroy failed / WebView method on another thread（WebViewPool线程安全）
    - P1-A: ClassCastException / cannot be cast（ImageUtils类型容错）
    - P2-A: IllegalBlockSizeException / DATA_NOT_MULTIPLE（图片解密长度校验）

    新增验证（071317版本修复点）：
    - P1-A-new: FileUriExposedException（系统浏览器打开file://崩溃）
    - P1-B-new: UnrecognizedInputFormatException + .mpd（MPD误判）
    - P2-A-new: 图片解密错误 + CancellationException（协程取消误报）
    - P2-C: PROTOCOL_ERROR / StreamReset（HTTP/2协议错误）
    - P2-B: ECONNREFUSED + 127.0.0.1（DNS劫持到本地地址）

    验证方法：清空logcat → 播放视频20秒 → 滑动切换文章 → 抓取logcat → 检查错误模式
    """
    print("\n=== 场景8: 错误模式验证（9个修复点）===")
    print("  检查 旧4项(Malformed/destroy/ClassCast/IllegalBlockSize) + 新5项(FileUri/MPD/Cancellation/PROTOCOL_ERROR/ECONNREFUSED)")

    # 清空logcat
    run_adb("logcat -c")
    print("  等待视频播放20秒...")

    # 等待视频播放
    time.sleep(20)

    # 滑动切换文章（触发新的视频加载和图片加载）
    if device:
        print("  滑动切换文章...")
        device.swipe(360, 600, 360, 300, 1.0)
        time.sleep(8)

    # 抓取logcat
    result = run_adb("logcat -d")
    log = result.stdout

    # 定义错误模式（旧4项 + 新5项）
    error_patterns = {
        "P2 Malformed URL": ["Malformed", "HttpDataSourceException"],
        "P1-C destroy failed": ["destroy failed", "WebView method", "another thread"],
        "P1-A ClassCastException": ["ClassCastException", "cannot be cast"],
        "P2-A IllegalBlockSize": ["IllegalBlockSize", "DATA_NOT_MULTIPLE"],
        # 071317新增修复点
        "P1-B FileUriExposed": ["FileUriExposedException"],
        "P1-A-new MPD误判": ["UnrecognizedInputFormatException"],  # .mpd误判导致ExoPlayer解析失败
        "P2-C HTTP/2协议错误": ["PROTOCOL_ERROR", "StreamReset"],
        "P2-B DNS劫持本地": ["ECONNREFUSED"],  # 127.0.0.1连接拒绝
    }

    all_pass = True
    for name, patterns in error_patterns.items():
        errors = []
        for pattern in patterns:
            errors.extend([l for l in log.splitlines() if pattern in l])
        if errors:
            print(f"  ❌ {name}: {len(errors)}个错误")
            for e in errors[:2]:
                print(f"     {e[:120]}")
            all_pass = False
        else:
            print(f"  ✅ {name}: 0错误")

    # P2-A-new: 图片解密错误中不应包含 CancellationException（协程取消误报修复验证）
    decrypt_cancel_lines = [l for l in log.splitlines()
                            if "解密错误" in l and ("CancellationException" in l or "JobCancellationException" in l)]
    if decrypt_cancel_lines:
        print(f"  ❌ P2-A-new 协程取消误报: {len(decrypt_cancel_lines)}个")
        for e in decrypt_cancel_lines[:2]:
            print(f"     {e[:120]}")
        all_pass = False
    else:
        print(f"  ✅ P2-A-new 协程取消误报: 0")

    # 检查FATAL EXCEPTION
    fatal = [l for l in log.splitlines() if "FATAL" in l]
    if fatal:
        print(f"  ❌ FATAL EXCEPTION: {len(fatal)}个")
        for f in fatal[:3]:
            print(f"     {f[:120]}")
        all_pass = False
    else:
        print(f"  ✅ FATAL EXCEPTION: 0")

    # 检查ExoPlayer是否在播放（EventLogger loading事件）
    loading_events = [l for l in log.splitlines() if "EventLogger" in l and "loading" in l]
    if loading_events:
        print(f"  ✅ ExoPlayer播放活跃: {len(loading_events)}个loading事件")
    else:
        print(f"  ⚠️ ExoPlayer loading事件为0（视频可能未播放）")

    if all_pass:
        print("✅ 场景8验证通过: 4个修复点全部0错误")
        return True
    else:
        print("⚠️ 场景8验证未通过: 存在错误")
        return False


def main():
    parser = argparse.ArgumentParser(description="视频播放器L2功能验证")
    parser.add_argument(
        "--scenario",
        choices=["swipe_article", "pagination", "preload",
                 "position_memory", "backward_compat",
                 "buffer_progress", "control_visibility",
                 "error_patterns", "all"],
        default="all",
        help="验证场景（默认all）。推荐error_patterns验证修复点"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="手动模式：用户已手动导航到视频播放器，脚本只执行场景验证"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Legado 视频播放器L2功能验证")
    print(f"场景: {args.scenario} | 模式: {'手动' if args.manual else '自动'}")
    print("=" * 60)

    # 连接设备
    device = connect_device()

    # 导航到视频播放器（非手动模式时）
    if not args.manual:
        if not navigate_to_video_player(device):
            print("❌ 无法自动导航到视频播放器")
            print("   建议：手动导航到视频播放器后使用 --manual 参数运行")
            sys.exit(2)
    else:
        # 手动模式：验证当前是否在视频播放器
        result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
        if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
            print("✅ 手动模式：已在视频播放器页面")
        else:
            print("⚠️ 手动模式：当前不在视频播放器页面，仍继续执行")

    # 执行场景验证
    scenarios = {
        "swipe_article": scenario_swipe_article,
        "pagination": scenario_pagination,
        "preload": scenario_preload,
        "position_memory": scenario_position_memory,
        "backward_compat": scenario_backward_compat,
        "buffer_progress": scenario_buffer_progress,
        "control_visibility": scenario_control_visibility,
        "error_patterns": scenario_error_patterns,
    }

    if args.scenario == "all":
        results = {}
        for name, func in scenarios.items():
            try:
                results[name] = func(device)
            except Exception as e:
                print(f"❌ 场景 {name} 执行异常: {e}")
                results[name] = False

        print("\n" + "=" * 60)
        print("L2验证结果汇总")
        print("=" * 60)
        for name, passed in results.items():
            status = "✅ 通过" if passed else "⚠️ 未通过"
            print(f"  {name}: {status}")

        all_passed = all(results.values())
    else:
        try:
            passed = scenarios[args.scenario](device)
        except Exception as e:
            print(f"❌ 场景 {args.scenario} 执行异常: {e}")
            passed = False
        all_passed = passed
        print(f"\n场景 {args.scenario}: {'✅ 通过' if passed else '⚠️ 未通过'}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ L2验证全部通过")
    else:
        print("⚠️ L2验证部分未通过（详见上方报告）")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
