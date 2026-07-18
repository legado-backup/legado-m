#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段3 类型识别与分类

职责：
1. Playwright 访问每个源首页（预处理后可访问的源）
2. DOM 特征分析（img/video/nav/article 4维度权重打分）
3. 辅助识别：sourceUrl 模板关键词
4. 综合决策：type(0/1/2) + is_navigation(bool) + confidence(0.0-1.0)
5. 跳过 needs_manual 源（占位符未恢复的源）

输出安全铁律（不可违背）：
- 脚本输出禁止包含业务字段原文（sourceName/sourceUrl/sourceComment 内容）
- 只输出技术指标：idx, type, is_navigation, confidence, error_type
- Playwright 异常消息必须脱敏（替换 URL/域名为 [URL]/[DOMAIN]）

输入：output/rss/preprocessed_v2.json（222源）
输出：
  - output/rss/classified_v2.json（含 type 字段的JSON）
  - output/rss/v2_type_classification_report.json（类型识别报告，仅技术指标）
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "preprocessed_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_type_classification_report.json"

# Playwright 配置
PAGE_TIMEOUT = 12000  # 单页超时12秒（减少）
MAX_RETRY = 1         # 失败重试次数（减少）
NAV_WAIT_UNTIL = "domcontentloaded"  # 等待DOM加载即可
NAVIGATE_TIMEOUT = 15000  # 整个 goto+render 超时

# stealth 脚本（避免被反爬识别）
STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
}
"""

# DOM 特征分析脚本
DOM_FEATURE_JS = """
() => {
    const imgs = document.querySelectorAll('img');
    const videos = document.querySelectorAll('video');
    const a_tags = document.querySelectorAll('a');
    
    const img_count = imgs.length;
    const img_gallery = document.querySelectorAll('.gallery, .image-list, .photo-list, ul.photos, .pic-list').length;
    const img_in_links = Array.from(imgs).filter(img => 
        img.src && img.width > 100 && img.height > 100
    ).length;
    
    const video_count = videos.length;
    const video_links = Array.from(a_tags).filter(a => 
        /play|video|watch|episode|观看|播放/i.test(a.textContent + ' ' + (a.href || ''))
    ).length;
    const video_btns = document.querySelectorAll('.play-btn, .video-play, [class*="play"], .player').length;
    
    const external_links = Array.from(a_tags).filter(a => {
        try { return new URL(a.href).host !== location.host; } 
        catch(e) { return false; }
    }).length;
    const nav_categories = document.querySelectorAll('.nav, .category, .sort, .directory, .friend-link, .link-list, .site-list').length;
    
    const article_tags = document.querySelectorAll('article, .article, .post, .news, .blog-item').length;
    const text_density = document.body.innerText.length / Math.max(document.body.innerHTML.length, 1);
    
    return {
        img_count, img_gallery, img_in_links,
        video_count, video_links, video_btns,
        external_links, nav_categories, a_total: a_tags.length,
        article_tags, text_density: Math.min(text_density, 1.0)
    };
}
"""

# sourceUrl 模板关键词辅助识别
TYPE_HINT_PATTERNS = {
    'video': [r'/video/', r'/v/', r'/movie/', r'/play', r'/watch', r'视频', r'影视', r'电影'],
    'image': [r'/image/', r'/pic/', r'/photo/', r'/gallery/', r'/tu/', r'图片', r'图库', r'壁纸'],
    'navigation': [r'/nav/', r'/link/', r'导航', r'网址', r'发布页'],
}


def sanitize_exception(e: Exception) -> str:
    """脱敏异常消息：替换URL/域名为代号"""
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def classify_by_url(source_url: str) -> Optional[str]:
    """通过URL辅助识别类型"""
    text = source_url.lower()
    for type_key, patterns in TYPE_HINT_PATTERNS.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return type_key
    return None


def classify_by_dom(features: Dict) -> Tuple[int, bool, float]:
    """通过DOM特征分析识别类型

    返回: (type, is_navigation, confidence)
    type: 0=网页, 1=图片, 2=视频
    is_navigation: 是否导航站
    confidence: 0.0-1.0 置信度
    """
    # 权重打分
    img_score = (
        min(features['img_count'] / 20, 1.0) * 0.4 +
        min(features['img_gallery'], 1.0) * 0.3 +
        min(features['img_in_links'] / 10, 1.0) * 0.3
    )
    video_score = (
        min(features['video_count'], 1.0) * 0.4 +
        min(features['video_links'] / 5, 1.0) * 0.4 +
        min(features['video_btns'] / 3, 1.0) * 0.2
    )
    nav_score = (
        min(features['external_links'] / 20, 1.0) * 0.5 +
        min(features['nav_categories'], 1.0) * 0.3 +
        min(features['a_total'] / 50, 1.0) * 0.2
    )
    article_score = (
        min(features['article_tags'] / 5, 1.0) * 0.4 +
        min(features['text_density'] * 10, 1.0) * 0.6
    )

    scores = {
        'image': img_score, 'video': video_score,
        'navigation': nav_score, 'article': article_score
    }
    best = max(scores, key=scores.get)
    confidence = scores[best]

    if best == 'navigation' and confidence > 0.5:
        return (0, True, round(confidence, 3))
    elif best == 'image' and confidence > 0.4:
        return (1, False, round(confidence, 3))
    elif best == 'video' and confidence > 0.4:
        return (2, False, round(confidence, 3))
    else:
        return (0, False, round(confidence, 3))


def classify_source(source: dict, page) -> Tuple[int, bool, float, str]:
    """分类单个源

    返回: (type, is_navigation, confidence, method)
    method: 'dom' / 'url_hint' / 'default'
    """
    # 优先 DOM 分析
    try:
        features = page.evaluate(DOM_FEATURE_JS)
        if features:
            type_val, is_nav, conf = classify_by_dom(features)
            if conf >= 0.4:
                return (type_val, is_nav, conf, 'dom')
    except Exception as e:
        print(f"    [WARN] DOM分析异常: {sanitize_exception(e)}")

    # 兜底：URL辅助识别
    source_url = source.get("sourceUrl", "") or ""
    url_hint = classify_by_url(source_url)
    if url_hint == 'image':
        return (1, False, 0.5, 'url_hint')
    elif url_hint == 'video':
        return (2, False, 0.5, 'url_hint')
    elif url_hint == 'navigation':
        return (0, True, 0.5, 'url_hint')

    # 默认网页源
    return (0, False, 0.0, 'default')


def extract_base_url(source_url: str) -> str:
    """从模板URL提取base_url"""
    base = re.sub(r"\{\{.*?\}\}", "", source_url)
    base = base.rstrip("/?")
    if base.startswith(("http://", "https://")):
        return base
    return source_url


def is_accessible(source: dict) -> bool:
    """判断源是否可访问（非needs_manual）"""
    comment = source.get("sourceComment", "") or ""
    if "[AI_PREPROCESS:needs_manual" in comment:
        return False
    source_url = source.get("sourceUrl", "") or ""
    if not source_url.startswith(("http://", "https://")):
        return False
    return True


def main():
    print("=" * 80)
    print("RSS v2 阶段3 类型识别与分类")
    print("=" * 80)

    # 1. 读取预处理后的JSON
    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        print(f"        请先运行阶段2预处理脚本 preprocess_sources_v2.py")
        return

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {sanitize_exception(e)}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    # 2. 启动 Playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[FATAL] playwright 未安装，请运行: pip install playwright && playwright install chromium")
        return

    # 3. 类型识别
    classified_sources: List[dict] = []
    report_records: List[dict] = []

    # 断点续传：如果已有部分结果，加载并跳过已处理的源
    processed_idxs = set()
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                classified_sources = json.load(f)
            processed_idxs = {r.get('idx') for r in classified_sources if 'idx' in r}
            # 注：原JSON没有idx字段，所以这条路径实际上不会复用，只是占位
            # 真正的续传逻辑通过report_records的idx判断
            print(f"[INFO] 发现已有输出文件，但JSON不含idx字段，重新开始处理")
            classified_sources = []
        except Exception:
            pass

    # 加载已有的报告记录（用于断点续传）
    if OUTPUT_REPORT.exists():
        try:
            with open(OUTPUT_REPORT, "r", encoding="utf-8") as f:
                old_report = json.load(f)
            old_records = old_report.get("records", [])
            old_idxs = {r['idx'] for r in old_records if 'idx' in r}
            print(f"[INFO] 已有报告记录 {len(old_idxs)} 条，将跳过这些源")
        except Exception:
            old_idxs = set()
            old_records = []
    else:
        old_idxs = set()
        old_records = []

    type_stats = {
        'type_0_web': 0,
        'type_1_image': 0,
        'type_2_video': 0,
        'navigation': 0,
        'needs_manual': 0,
        'access_failed': 0,
    }

    method_stats = {
        'dom': 0,
        'url_hint': 0,
        'default': 0,
        'skipped': 0,
        'failed': 0,
    }

    # 重新计算已处理源的统计
    for rec in old_records:
        if rec.get('method') == 'skipped':
            method_stats['skipped'] += 1
            type_stats['needs_manual'] += 1
        elif rec.get('method') == 'failed':
            method_stats['failed'] += 1
            type_stats['access_failed'] += 1
        elif rec.get('is_navigation'):
            type_stats['navigation'] += 1
        elif rec.get('type') == 0:
            type_stats['type_0_web'] += 1
        elif rec.get('type') == 1:
            type_stats['type_1_image'] += 1
        elif rec.get('type') == 2:
            type_stats['type_2_video'] += 1

    # 加载已处理的源（按idx保留）
    classified_sources_dict = {}

    # 如果有已处理的记录，从原sources重建dict（包括sourceComment标签）
    if old_records:
        old_records_by_idx = {r['idx']: r for r in old_records if 'idx' in r}
        for idx, source in enumerate(sources):
            if idx in old_records_by_idx:
                rec = old_records_by_idx[idx]
                src_copy = dict(source)  # 浅拷贝
                src_copy['type'] = rec.get('type', 0)
                method = rec.get('method', 'unknown')
                is_nav = rec.get('is_navigation', False)
                conf = rec.get('confidence', 0.0)
                # 重建 sourceComment 标签
                if method == 'skipped':
                    tag = 'skipped'
                    extra = f"[AI_CLASSIFY:{tag}|reason=needs_manual]"
                elif is_nav:
                    tag = 'nav'
                    extra = f"[AI_CLASSIFY:{tag}|conf={conf}|method={method}]"
                elif method == 'failed':
                    tag = 'access_failed'
                    extra = f"[AI_CLASSIFY:{tag}|stage7_retry]"
                else:
                    tag = f"type{rec.get('type', 0)}"
                    extra = f"[AI_CLASSIFY:{tag}|conf={conf}|method={method}]"
                # 追加到原 sourceComment（避免重复追加）
                orig_comment = src_copy.get('sourceComment', '') or ''
                if 'AI_CLASSIFY:' not in orig_comment:
                    src_copy['sourceComment'] = orig_comment + '\n' + extra if orig_comment else extra
                classified_sources_dict[idx] = src_copy
        print(f"[INFO] 已从原 sources 重建 {len(classified_sources_dict)} 个源到 dict")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )

            for idx, source in enumerate(sources):
                # 断点续传：跳过已处理的源
                if idx in old_idxs:
                    continue

                # 跳过needs_manual源
                if not is_accessible(source):
                    source['type'] = 0
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        "\n[AI_CLASSIFY:skipped|reason=needs_manual]"
                    classified_sources_dict[idx] = source
                    report_records.append({
                        "idx": idx, "type": 0, "is_navigation": False,
                        "confidence": 0.0, "method": "skipped",
                    })
                    type_stats['needs_manual'] += 1
                    method_stats['skipped'] += 1
                    continue

                # 提取base_url（如果是模板源）
                source_url = source.get("sourceUrl", "") or ""
                access_url = extract_base_url(source_url) if "{{" in source_url else source_url

                # Playwright 访问（带重试）
                page = None
                success = False
                type_val, is_nav, conf, method = 0, False, 0.0, 'default'

                for attempt in range(MAX_RETRY + 1):
                    try:
                        page = context.new_page()
                        page.add_init_script(STEALTH_JS)
                        # 关键：限制所有操作超时为5秒，避免evaluate卡死
                        page.set_default_timeout(5000)
                        page.goto(access_url, timeout=PAGE_TIMEOUT, wait_until=NAV_WAIT_UNTIL)
                        # 不等待 networkidle，避免某些站点的长连接导致卡死
                        # 直接尝试 DOM 分析，失败立即跳过
                        try:
                            type_val, is_nav, conf, method = classify_source(source, page)
                            success = True
                        except Exception as eval_e:
                            # evaluate 失败，用URL辅助识别
                            url_hint = classify_by_url(access_url)
                            if url_hint == 'image':
                                type_val, is_nav, conf, method = 1, False, 0.5, 'url_hint_fallback'
                            elif url_hint == 'video':
                                type_val, is_nav, conf, method = 2, False, 0.5, 'url_hint_fallback'
                            elif url_hint == 'navigation':
                                type_val, is_nav, conf, method = 0, True, 0.5, 'url_hint_fallback'
                            else:
                                type_val, is_nav, conf, method = 0, False, 0.0, 'default_fallback'
                            success = True  # 标记为成功（已用兜底识别）
                        break
                    except Exception as e:
                        if attempt == MAX_RETRY:
                            # 最后一次失败，记录但不中断
                            err_msg = sanitize_exception(e)
                            print(f"  [FAIL] idx={idx} attempt={attempt+1} err={err_msg[:80]}")
                        else:
                            # 重试
                            if page:
                                try:
                                    page.close()
                                except Exception:
                                    pass
                            continue
                    finally:
                        if page:
                            try:
                                page.close()
                            except Exception:
                                pass

                # 设置type字段
                if success:
                    source['type'] = type_val
                    tag = "nav" if is_nav else f"type{type_val}"
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        f"\n[AI_CLASSIFY:{tag}|conf={conf}|method={method}]"

                    method_stats[method] = method_stats.get(method, 0) + 1

                    if is_nav:
                        type_stats['navigation'] += 1
                    elif type_val == 0:
                        type_stats['type_0_web'] += 1
                    elif type_val == 1:
                        type_stats['type_1_image'] += 1
                    elif type_val == 2:
                        type_stats['type_2_video'] += 1
                else:
                    # 访问失败，标记为needs_retry（阶段7深度重试）
                    source['type'] = 0
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        "\n[AI_CLASSIFY:access_failed|stage7_retry]"
                    type_stats['access_failed'] += 1
                    method_stats['failed'] += 1

                classified_sources_dict[idx] = source
                report_records.append({
                    "idx": idx, "type": type_val, "is_navigation": is_nav,
                    "confidence": conf, "method": method if success else "failed",
                })

                # 进度打印（每20个源打印一次）
                if (idx + 1) % 20 == 0 or idx == total - 1:
                    print(f"  [PROGRESS] {idx+1}/{total} ({(idx+1)*100//total}%)")
                    # 增量保存（每20个源保存一次，防止中断丢失数据）
                    try:
                        # 合并已处理的源
                        merged_sources = list(classified_sources_dict.values())
                        # 加上跳过的needs_manual源（在report_records里有但不在dict里时也要保留）
                        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
                        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                            json.dump(merged_sources, f, ensure_ascii=False, indent=2)
                        # 同时保存报告
                        report = {
                            "stage": "classify_type_v2",
                            "input_file": str(INPUT_JSON.name),
                            "output_file": str(OUTPUT_JSON.name),
                            "total_sources": total,
                            "processed_count": len(classified_sources_dict),
                            "type_stats": type_stats,
                            "method_stats": method_stats,
                            "records": report_records,
                        }
                        with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
                            json.dump(report, f, ensure_ascii=False, indent=2)
                    except Exception as save_e:
                        print(f"  [WARN] 增量保存失败: {save_e}")

            try:
                browser.close()
            except Exception:
                pass

    except KeyboardInterrupt:
        print("\n[WARN] 用户中断（Ctrl+C），保存已处理的结果...")
        # 中断时保存已处理结果
        try:
            merged_sources = list(classified_sources_dict.values())
            OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(merged_sources, f, ensure_ascii=False, indent=2)
            report = {
                "stage": "classify_type_v2_interrupted",
                "input_file": str(INPUT_JSON.name),
                "output_file": str(OUTPUT_JSON.name),
                "total_sources": total,
                "processed_count": len(classified_sources_dict),
                "type_stats": type_stats,
                "method_stats": method_stats,
                "records": report_records,
            }
            with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 已保存 {len(classified_sources_dict)} 个已处理源")
        except Exception as save_e:
            print(f"[ERROR] 中断保存失败: {save_e}")
        return

    # 4. 输出分类后的JSON（合并 classified_sources_dict 中的所有源，按 idx 排序）
    final_sources = [classified_sources_dict[idx] for idx in sorted(classified_sources_dict.keys())]
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)

    # 5. 输出类型识别报告
    report = {
        "stage": "classify_type_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "processed_count": len(final_sources),
        "type_stats": type_stats,
        "method_stats": method_stats,
        "records": report_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 6. 打印汇总
    print(f"\n[RESULT] 类型识别完成")
    print(f"  - 总源数:           {total}")
    print(f"  - 已处理源数:       {len(final_sources)}")
    print(f"  - 网页源(type=0):   {type_stats['type_0_web']}")
    print(f"  - 图片源(type=1):   {type_stats['type_1_image']}")
    print(f"  - 视频源(type=2):   {type_stats['type_2_video']}")
    print(f"  - 导航站:           {type_stats['navigation']}")
    print(f"  - 待人工(needs_manual): {type_stats['needs_manual']}")
    print(f"  - 访问失败(stage7重试): {type_stats['access_failed']}")
    print(f"\n[METHOD]")
    print(f"  - DOM分析成功:      {method_stats['dom']}")
    print(f"  - URL辅助识别:      {method_stats['url_hint']}")
    print(f"  - 默认网页:         {method_stats['default']}")
    print(f"  - 跳过(needs_manual): {method_stats['skipped']}")
    print(f"  - 失败(stage7重试): {method_stats['failed']}")
    print(f"\n[OUTPUT]")
    print(f"  - 分类后JSON:       {OUTPUT_JSON}")
    print(f"  - 类型识别报告:     {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
