#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段4 导航站拆分

职责：
1. 读取阶段3分类后的JSON（含 is_navigation 标记的源）
2. 对导航类源站提取所有子站链接（去重+过滤无效链接）
3. Playwright 访问每个子站首页，复用阶段3类型识别
4. 对图片站/视频站拆分为独立子源
5. 父源标记 nav_parent=true + enabled=false

边界条件：
- 单个导航站最多拆分20个子源（防止海量外链导致任务爆炸）
- 子站访问失败跳过，不阻断整体流程
- 子源类型置信度<0.4 跳过

输出安全铁律（不可违背）：
- 脚本输出禁止包含业务字段原文（子站URL/名称等）
- 只输出技术指标：idx, parent_idx, sub_idx, type, confidence
- Playwright 异常消息必须脱敏

输入：output/rss/classified_v2.json
输出：
  - output/rss/splitted_v2.json（含拆分子源后的JSON）
  - output/rss/v2_navigation_split_report.json（拆分报告，仅技术指标）
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "splitted_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_navigation_split_report.json"

# Playwright 配置
PAGE_TIMEOUT = 15000
MAX_SUB_PER_PARENT = 20  # 单导航站最多拆分子源数
MIN_CONFIDENCE = 0.4     # 子源最低置信度

# stealth 脚本
STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
}
"""

# 提取导航链接的JS
EXTRACT_SUB_SITES_JS = """
() => {
    const result = [];
    const seen = new Set();
    
    const nav_selectors = [
        '.nav a', '.category a', '.sort a', '.directory a',
        '.friend-link a', '.link-list a', '.site-list a',
        '.content-list a', '.main-sites a', 'nav a',
        '.box a', '.list a', '.item a'
    ];
    
    for (const sel of nav_selectors) {
        document.querySelectorAll(sel).forEach(a => {
            if (!a.href || seen.has(a.href)) return;
            seen.add(a.href);
            
            if (a.href.startsWith('#') || a.href.startsWith('mailto:') || a.href.startsWith('tel:')) return;
            if (a.href.startsWith('javascript:')) return;
            
            const parent_text = a.closest('li, .item, .category, .box')?.innerText || '';
            
            result.push({
                url: a.href,
                text: a.textContent.trim().substring(0, 50),
                context: parent_text.substring(0, 100),
                has_image: !!a.querySelector('img') || !!a.closest('.image, .pic, .gallery, .photo'),
                is_video_hint: /视频|影视|movie|video|play|观看|播放/i.test(a.textContent + ' ' + a.href)
            });
        });
    }
    return result;
}
"""

# DOM 特征分析脚本（复用阶段3）
DOM_FEATURE_JS = """
() => {
    const imgs = document.querySelectorAll('img');
    const videos = document.querySelectorAll('video');
    const a_tags = document.querySelectorAll('a');
    
    return {
        img_count: imgs.length,
        img_gallery: document.querySelectorAll('.gallery, .image-list, .photo-list, ul.photos, .pic-list').length,
        img_in_links: Array.from(imgs).filter(img => 
            img.src && img.width > 100 && img.height > 100
        ).length,
        video_count: videos.length,
        video_links: Array.from(a_tags).filter(a => 
            /play|video|watch|episode|观看|播放/i.test(a.textContent + ' ' + (a.href || ''))
        ).length,
        video_btns: document.querySelectorAll('.play-btn, .video-play, [class*="play"], .player').length,
        external_links: Array.from(a_tags).filter(a => {
            try { return new URL(a.href).host !== location.host; } 
            catch(e) { return false; }
        }).length,
        nav_categories: document.querySelectorAll('.nav, .category, .sort, .directory, .friend-link, .link-list, .site-list').length,
        a_total: a_tags.length,
        article_tags: document.querySelectorAll('article, .article, .post, .news, .blog-item').length,
        text_density: Math.min(document.body.innerText.length / Math.max(document.body.innerHTML.length, 1), 1.0)
    };
}
"""


def sanitize_exception(e: Exception) -> str:
    """脱敏异常消息"""
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def classify_by_dom(features: Dict) -> Tuple[int, float]:
    """DOM 分类，返回 (type, confidence)"""
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
    article_score = (
        min(features['article_tags'] / 5, 1.0) * 0.4 +
        min(features['text_density'] * 10, 1.0) * 0.6
    )

    if img_score > video_score and img_score > article_score and img_score > MIN_CONFIDENCE:
        return (1, round(img_score, 3))
    if video_score > img_score and video_score > article_score and video_score > MIN_CONFIDENCE:
        return (2, round(video_score, 3))
    return (0, 0.0)


def is_navigation_source(source: dict) -> bool:
    """判断是否导航站（基于阶段3的标记）"""
    comment = source.get("sourceComment", "") or ""
    return "[AI_CLASSIFY:nav|" in comment


def create_sub_source(parent_source: dict, sub_url: str, sub_type: int, confidence: float) -> dict:
    """基于父源创建子源"""
    return {
        'sourceUrl': sub_url,
        'sourceName': '',  # 由后续阶段补全
        'sourceComment': f'[AI_EXTRACTED:from_navigation|parent_idx=***|conf={confidence}]',
        'type': sub_type,
        'enabled': True,
        'enabledCookieJar': parent_source.get('enabledCookieJar', True),
        'header': parent_source.get('header', ''),
        'sourceIcon': '',
        'searchUrl': '',
        'sortUrl': '',
        'ruleArticles': '',
        'ruleTitle': '',
        'ruleLink': '',
        'ruleImage': '',
        'ruleNextPage': '',
        'rulePubDate': '',
        'ruleDescription': '',
        'ruleContent': '',
        'articleStyle': 0,
        'enableJs': False,
        'loadWithBaseUrl': False,
        'loginUrl': '',
        'loginUi': '',
        'loginCheckJs': '',
        'lastUpdateTime': 0,
        'customOrder': 0,
        'weight': 0,
    }


def split_navigation_source(source: dict, page, parent_idx: int) -> List[dict]:
    """拆分导航站为子源列表"""
    try:
        sub_sites = page.evaluate(EXTRACT_SUB_SITES_JS)
    except Exception as e:
        print(f"    [WARN] 提取子站链接异常: {sanitize_exception(e)}")
        return []

    if not sub_sites:
        return []

    # 去重+过滤无效链接
    seen_hosts = set()
    valid_sub_sites = []
    for site in sub_sites:
        try:
            host = urlparse(site['url']).netloc
            if host and host not in seen_hosts:
                seen_hosts.add(host)
                valid_sub_sites.append(site)
        except Exception:
            continue

    # 限制单导航站最多拆分子源数
    valid_sub_sites = valid_sub_sites[:MAX_SUB_PER_PARENT]

    return valid_sub_sites


def main():
    print("=" * 80)
    print("RSS v2 阶段4 导航站拆分")
    print("=" * 80)

    # 1. 读取分类后的JSON
    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        print(f"        请先运行阶段3类型识别脚本 classify_source_type_v2.py")
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
        print("[FATAL] playwright 未安装")
        return

    # 3. 拆分导航站
    final_sources: List[dict] = []
    split_records: List[dict] = []
    sub_sources_total = 0
    nav_parent_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        for idx, source in enumerate(sources):
            # 跳过非导航站
            if not is_navigation_source(source):
                final_sources.append(source)
                continue

            nav_parent_count += 1
            source_url = source.get("sourceUrl", "") or ""

            # 访问父源首页
            try:
                page = context.new_page()
                page.add_init_script(STEALTH_JS)
                page.goto(source_url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                # 提取子站链接
                sub_sites = split_navigation_source(source, page, idx)
                page.close()

                if not sub_sites:
                    # 没有子站，保留为普通源
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        "\n[AI_SPLIT:no_sub_sites]"
                    final_sources.append(source)
                    split_records.append({
                        "parent_idx": idx, "sub_count": 0, "status": "no_sub_sites"
                    })
                    continue

                # 标记父源为 nav_parent + 禁用
                source['enabled'] = False
                source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                    f"\n[AI_SPLIT:nav_parent|sub_count={len(sub_sites)}]"

                # Playwright 访问每个子站识别类型
                sub_created = 0
                for sub_idx, sub_site in enumerate(sub_sites):
                    try:
                        sub_page = context.new_page()
                        sub_page.add_init_script(STEALTH_JS)
                        sub_page.goto(sub_site['url'], timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                        sub_page.wait_for_timeout(1000)

                        # DOM 分析
                        features = sub_page.evaluate(DOM_FEATURE_JS)
                        sub_type, conf = classify_by_dom(features)

                        if sub_type in (1, 2) and conf >= MIN_CONFIDENCE:
                            # 创建子源
                            sub_source = create_sub_source(source, sub_site['url'], sub_type, conf)
                            final_sources.append(sub_source)
                            sub_created += 1
                            sub_sources_total += 1

                            split_records.append({
                                "parent_idx": idx, "sub_idx": sub_idx,
                                "type": sub_type, "confidence": conf,
                                "url_len": len(sub_site['url']),
                            })

                        sub_page.close()
                    except Exception as e:
                        # 子站访问失败跳过
                        try:
                            if sub_page:
                                sub_page.close()
                        except Exception:
                            pass
                        continue

                # 父源放到子源之后（避免影响索引）
                final_sources.append(source)

                print(f"  [PROGRESS] parent_idx={idx} 拆分出 {sub_created} 个子源")

            except Exception as e:
                err_msg = sanitize_exception(e)
                print(f"  [FAIL] parent_idx={idx} err={err_msg[:80]}")
                source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                    f"\n[AI_SPLIT:failed|err={err_msg[:50]}]"
                final_sources.append(source)
                split_records.append({
                    "parent_idx": idx, "sub_count": 0, "status": "failed",
                    "error_type": type(e).__name__
                })

        browser.close()

    # 4. 输出拆分后的JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)

    # 5. 输出拆分报告
    report = {
        "stage": "split_navigation_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources_before": total,
        "total_sources_after": len(final_sources),
        "nav_parent_count": nav_parent_count,
        "sub_sources_created": sub_sources_total,
        "records": split_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULT] 导航站拆分完成")
    print(f"  - 输入源数:         {total}")
    print(f"  - 输出源数:         {len(final_sources)} (+{len(final_sources)-total})")
    print(f"  - 导航站父源:       {nav_parent_count}")
    print(f"  - 拆分子源总数:     {sub_sources_total}")
    print(f"\n[OUTPUT]")
    print(f"  - 拆分后JSON:      {OUTPUT_JSON}")
    print(f"  - 拆分报告:         {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
