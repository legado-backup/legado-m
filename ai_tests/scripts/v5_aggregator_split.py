#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v5_aggregator_split.py — 集成站深度拆分 Phase 2-C

对14个集成站逐个深度分析，将sortUrl中的多分类拆分为独立子源。

输入：
  - V4源JSON: output/rss/optimized_v2_lite_final_v4.json
  - 集成站索引列表（来自 v5_classification.json by_category.aggregator）

输出：
  - output/rss/v5_aggregator_split.json

输出安全铁律（不可违背）：
  - 脚本日志和输出文件禁止出现真实URL/域名/源名称/分类名
  - URL脱敏为 http://[DOMAIN]/path
  - 分类名脱敏为 分类[M]
  - 源名称脱敏为 源[N] - 分类[M]
  - 异常消息必须脱敏
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.stdout.reconfigure(encoding='utf-8')

# ============== 配置 ==============
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "optimized_v2_lite_final_v4.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "v5_aggregator_split.json"

# 14个集成站索引（来自 v5_classification.json by_category.aggregator）
AGGREGATOR_INDICES = [27, 32, 41, 87, 110, 117, 120, 121, 123, 128, 131, 147, 150, 151]

# Playwright 配置
PAGE_TIMEOUT = 30000        # 30s 总超时（任务要求）
GOTO_TIMEOUT = 20000        # 导航超时 20s
NETWORKIDLE_TIMEOUT = 8000  # networkidle 等待 8s（吞掉超时）
SCROLL_WAIT_MS = 1500       # 滚动后等待 1.5s
MAX_SUB_PER_PARENT = 20     # 单父站最多拆分子源数
MIN_CONFIDENCE = 0.6        # 类型识别置信度阈值

# Mobile UA
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/16.0 Mobile/15E148 Safari/604.1")

# ============== JS 注入脚本 ==============
# 去弹框
REMOVE_MODAL_JS = """() => {
    document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal').forEach(e=>e.remove());
}"""

# 深度分析JS：返回所有需要的特征
ANALYZE_PAGE_JS = """() => {
    const result = {};
    const html = document.documentElement.outerHTML;

    // 视频特征
    result.video_tags = document.querySelectorAll('video').length;
    result.video_links = Array.from(document.querySelectorAll('a')).filter(a =>
        /m3u8|\\.mp4|video|播放|观看|play/i.test(a.href + ' ' + a.textContent)
    ).length;
    result.video_js_libs = [];
    if (/video\\.js/i.test(html)) result.video_js_libs.push('video.js');
    if (/jwplayer/i.test(html)) result.video_js_libs.push('jwplayer');
    if (/dplayer/i.test(html)) result.video_js_libs.push('dplayer');
    if (/Hls\\.js|hls\\.js/i.test(html)) result.video_js_libs.push('hls.js');

    // 图片特征
    result.img_count = document.querySelectorAll('img').length;
    result.img_large = Array.from(document.querySelectorAll('img')).filter(img =>
        img.src && img.width > 100 && img.height > 100
    ).length;
    result.img_gallery = document.querySelectorAll('.gallery, .image-list, .photo-list, .pic-list, .album, .thumb-list').length;

    // 文章特征
    result.article_count = document.querySelectorAll('article, .article, .post, .news, .blog-item, .entry').length;
    result.text_density = Math.min(document.body.innerText.length / Math.max(document.body.innerHTML.length, 1), 1.0);

    // body长度（用于判断页面是否真实有内容）
    result.body_html_len = document.body ? document.body.innerHTML.length : 0;
    result.body_text_len = document.body ? document.body.innerText.length : 0;
    result.a_count = document.querySelectorAll('a').length;
    result.div_count = document.querySelectorAll('div').length;

    // 导航页检测：title含"全部分类/所有分类/导航"等
    const title = (document.title || '').toLowerCase();
    result.is_nav_page = /全部|所有|导航|all categories|category list|tags list/i.test(document.title || '');

    // 列表选择器命中（扩充候选，含 entry-card 等影视站常见class）
    const list_sels = [
        '.item', '.post', '.article', '.card', '.video-item', '.image-item',
        '.thumb', '.list-item', '.entry', '.media',
        '.entry-card', '.entry-item', '.video-card', '.movie-item', '.film-item',
        '.news-item', '.list-card', '.stui-vodlist__item', '.stui-pannel',
        '.myui-vodlist__item', '.module-item', '.module-card-item',
        '.vodlist_item', '.vod-list-item', '.thumb-block', '.video-list-item',
        '.post-item', '.article-item', '.news-block', '.col-item', '.cell'
    ];
    result.list_selector_hits = {};
    list_sels.forEach(sel => {
        const c = document.querySelectorAll(sel).length;
        if (c > 0) result.list_selector_hits[sel] = c;
    });

    // 标题选择器命中
    const title_sels = ['h1', 'h2', 'h3', '.title', '.name', '.entry-title', '.video-title', '.movie-title'];
    result.title_selector_hits = {};
    title_sels.forEach(sel => {
        const c = document.querySelectorAll(sel).length;
        if (c > 0) result.title_selector_hits[sel] = c;
    });

    // 图片选择器命中
    const img_sels = ['img', '.thumb img', '.pic img', '.cover img', '.entry-thumb img', '.entry-image img'];
    result.img_selector_hits = {};
    img_sels.forEach(sel => {
        const c = document.querySelectorAll(sel).length;
        if (c > 0) result.img_selector_hits[sel] = c;
    });

    // 链接选择器命中
    const link_sels = ['a', '.title a', '.item a', '.post a', '.thumb a', '.entry-card a', '.entry-title a'];
    result.link_selector_hits = {};
    link_sels.forEach(sel => {
        const c = document.querySelectorAll(sel).length;
        if (c > 0) result.link_selector_hits[sel] = c;
    });

    // 下一页选择器命中
    const next_sels = [
        'a.next', 'a[rel=next]', '.pagination a:last-child', '.page-next', '.next', '.pagebtn',
        '.ct-pagination .next', '.page-numbers.next', '.pagination .next a',
        'a:has(.next)', '.pager .next a', '.pagebar a:last'
    ];
    result.next_selector_hits = {};
    next_sels.forEach(sel => {
        try {
            const c = document.querySelectorAll(sel).length;
            if (c > 0) result.next_selector_hits[sel] = c;
        } catch(e) {} // :has 可能不被支持
    });

    // 搜索表单
    const forms = document.querySelectorAll('form');
    result.search_form_count = forms.length;
    result.search_form_action = '';
    result.search_form_input = '';
    for (const form of forms) {
        const action = form.action || form.getAttribute('action') || '';
        const textInput = form.querySelector('input[type="text"], input[type="search"], input:not([type])');
        if (action && textInput && textInput.name) {
            result.search_form_action = action;
            result.search_form_input = textInput.name;
            break;
        }
    }

    return result;
}"""

# ============== 脱敏函数 ==============
def sanitize_url(url: str) -> str:
    """脱敏URL: 保留路径模式，替换域名"""
    if not url:
        return ''
    if url.startswith('@js'):
        return '@js:[CODE]'
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return url
        path = parsed.path or '/'
        if parsed.query:
            # 保留 query 中的常见模板变量，其他脱敏
            q = parsed.query
            # 移除疑似值，保留参数名
            q_clean = re.sub(r'=\S+', '=[V]', q)
            path += '?' + q_clean
        if parsed.fragment:
            path += '#[ANCHOR]'
        return f"{parsed.scheme}://[DOMAIN]{path}"
    except Exception:
        return '[URL]'


def sanitize_exception(e: Exception) -> str:
    """脱敏异常消息"""
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"'\\]+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    msg = re.sub(r"cookie[s]?", "[CK]", msg, flags=re.IGNORECASE)
    return msg[:200]


# ============== 类型识别 ==============
def classify_type(features: Dict) -> Tuple[int, float, List[str]]:
    """根据特征识别类型，返回 (type, confidence, features_list)

    type: 0=网页/文章, 1=图片, 2=视频
    """
    score_video = 0.0
    score_image = 0.0
    score_article = 0.0
    feats = []

    # 视频评分
    if features.get('video_tags', 0) > 0:
        score_video += 0.6
        feats.append(f"video_tags={features['video_tags']}")
    if features.get('video_links', 0) > 0:
        score_video += 0.4
        feats.append(f"video_links={features['video_links']}")
    if features.get('video_js_libs'):
        score_video += 0.4
        feats.append(f"video_js_libs={features['video_js_libs']}")

    # 内容列表兜底：img>=10 + a>=50 + html_len>5000 + 无强文章特征 → 视频站（影视站常见模式）
    img_count = features.get('img_count', 0)
    a_count = features.get('a_count', 0)
    body_html_len = features.get('body_html_len', 0)
    article_count = features.get('article_count', 0)
    list_hits = features.get('list_selector_hits', {})

    has_list_evidence = (img_count >= 10 and a_count >= 50 and body_html_len > 5000) or bool(list_hits)
    if has_list_evidence and article_count == 0 and score_video == 0:
        score_video = 0.7  # 兜底分（高于0.6阈值）
        feats.append(f"list_evidence(img={img_count},a={a_count},html={body_html_len})")

    # 图片评分
    if img_count > 20:
        score_image += 0.5
        feats.append(f"img_count={img_count}")
    elif img_count > 10:
        score_image += 0.3
        feats.append(f"img_count={img_count}")
    if features.get('img_large', 0) > 5:
        score_image += 0.4
        feats.append(f"img_large={features['img_large']}")
    elif features.get('img_large', 0) > 3:
        score_image += 0.3
        feats.append(f"img_large={features['img_large']}")
    if features.get('img_gallery', 0) > 0:
        score_image += 0.4
        feats.append(f"img_gallery={features['img_gallery']}")

    # 文章评分
    if article_count > 5:
        score_article += 0.5
        feats.append(f"article_count={article_count}")
    if features.get('text_density', 0) > 0.2:
        score_article += 0.4
        feats.append(f"text_density={features['text_density']:.2f}")

    scores = [(2, score_video, "video"), (1, score_image, "image"), (0, score_article, "article")]
    scores.sort(key=lambda x: x[1], reverse=True)
    best_type, best_score, best_name = scores[0]

    if best_score >= MIN_CONFIDENCE:
        return (best_type, round(best_score, 3), feats)
    return (0, 0.0, feats)


# ============== 规则字段提取 ==============
def extract_rules(features: Dict, type_id: int) -> Dict:
    """根据特征提取 Legado 规则字段"""
    rules = {}

    # ruleArticles
    list_hits = features.get('list_selector_hits', {})
    if list_hits:
        best = max(list_hits.items(), key=lambda x: x[1])
        rules['ruleArticles'] = best[0]
    else:
        rules['ruleArticles'] = '.item,.post,.article,.card'

    # ruleTitle
    title_hits = features.get('title_selector_hits', {})
    if title_hits:
        best = max(title_hits.items(), key=lambda x: x[1])
        rules['ruleTitle'] = best[0]
    else:
        rules['ruleTitle'] = 'h1,h2,h3,.title,.name'

    # ruleImage
    img_hits = features.get('img_selector_hits', {})
    if img_hits:
        best = max(img_hits.items(), key=lambda x: x[1])
        sel = best[0]
        if '::attr' not in sel:
            sel = sel + '::attr(src)'
        rules['ruleImage'] = sel
    else:
        rules['ruleImage'] = 'img::attr(src),.thumb img::attr(src)'

    # ruleUrl
    link_hits = features.get('link_selector_hits', {})
    if link_hits:
        best = max(link_hits.items(), key=lambda x: x[1])
        sel = best[0]
        if '::attr' not in sel and sel != 'a':
            sel = sel + ' a::attr(href)' if sel != 'a' else 'a::attr(href)'
        elif sel == 'a':
            sel = 'a::attr(href)'
        rules['ruleUrl'] = sel
    else:
        rules['ruleUrl'] = 'a::attr(href)'

    # ruleNextPage
    next_hits = features.get('next_selector_hits', {})
    if next_hits:
        best = max(next_hits.items(), key=lambda x: x[1])
        sel = best[0]
        if '::attr' not in sel:
            sel = sel + '::attr(href)'
        rules['ruleNextPage'] = sel
    else:
        rules['ruleNextPage'] = 'a.next,a[rel=next],.pagination a:last-child,.page-next'

    # searchUrl（脱敏）
    if features.get('search_form_action') and features.get('search_form_input'):
        action = features['search_form_action']
        input_name = features['search_form_input']
        sep = '&' if '?' in action else '?'
        # 脱敏：保留模板结构，URL部分用[DOMAIN]
        sanitized_action = sanitize_url(action)
        rules['searchUrl'] = f"{sanitized_action}{sep}{input_name}={{{{key}}}}"
    else:
        rules['searchUrl'] = ''

    # ruleContent - 根据类型设置默认模板
    if type_id == 2:  # 视频
        rules['ruleContent'] = '{{$.m3u8||$.mp4}}'
    elif type_id == 1:  # 图片
        rules['ruleContent'] = '{{$.image}}'
    else:  # 文章
        rules['ruleContent'] = '{{$.content}}'

    return rules


# ============== sortUrl 解析 ==============
def parse_sort_url(sort_url: str) -> List[Tuple[str, str]]:
    """解析sortUrl为 [(分类编号, URL), ...] 列表

    分类名脱敏为 分类[M]，不保留原分类名
    """
    if not sort_url:
        return []

    # @js:格式特殊处理：正则提取http(s) URL
    if sort_url.lstrip().startswith('@js'):
        urls = re.findall(r"https?://[^\s\"'\\,)]+", sort_url)
        # 去重保留顺序
        seen = set()
        unique_urls = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)
        return [(f"分类{i+1}", u) for i, u in enumerate(unique_urls[:MAX_SUB_PER_PARENT])]

    # 普通格式: 按\n分割，每行可能含 "分类名::URL"
    categories = []
    lines = sort_url.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '::' in line:
            parts = line.split('::', 1)
            cat_url = parts[1].strip()
        else:
            cat_url = line
        if cat_url and cat_url.startswith('http'):
            categories.append((f"分类{len(categories)+1}", cat_url))
        if len(categories) >= MAX_SUB_PER_PARENT:
            break
    return categories


# ============== 单个集成站处理 ==============
def process_aggregator(source: dict, idx: int, context) -> Tuple[List[dict], List[dict], bool]:
    """处理单个集成站，返回 (subsources, failed, parent_disabled)

    输出全部脱敏，不返回原始URL/分类名
    """
    sort_url = source.get('sortUrl', '') or ''
    categories = parse_sort_url(sort_url)

    if not categories:
        print(f"  [idx={idx}] 无可拆分分类")
        return [], [], False  # 父源保持原状

    print(f"  [idx={idx}] 解析出 {len(categories)} 个分类")

    subsources = []
    failed = []

    for cat_idx, (cat_label, cat_url) in enumerate(categories):
        print(f"    访问 {cat_label} ...", end=' ', flush=True)
        page = None
        try:
            page = context.new_page()
            page.set_default_timeout(PAGE_TIMEOUT)
            page.goto(cat_url, timeout=GOTO_TIMEOUT, wait_until='domcontentloaded')
            # networkidle 等待（吞掉超时）
            try:
                page.wait_for_load_state('networkidle', timeout=NETWORKIDLE_TIMEOUT)
            except PlaywrightTimeout:
                pass
            except Exception:
                pass

            # 注入去弹框JS
            try:
                page.evaluate(REMOVE_MODAL_JS)
            except Exception:
                pass

            # 滚动加载
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(SCROLL_WAIT_MS)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(SCROLL_WAIT_MS)
            except Exception:
                pass

            # 提取特征
            features = page.evaluate(ANALYZE_PAGE_JS)
            page.close()
            page = None

            # 跳过导航页（如 /all/ 全部分类页）
            if features.get('is_nav_page'):
                print(f"[SKIP_NAV] is_nav_page=true")
                failed.append({
                    'parent_source_index': idx,
                    'category_name': cat_label,
                    'error': 'nav_page_skipped',
                })
                continue

            # 类型识别
            type_id, confidence, feats = classify_type(features)
            if confidence < MIN_CONFIDENCE:
                print(f"[SKIP] conf={confidence} img={features.get('img_count',0)} a={features.get('a_count',0)}")
                continue

            # 提取规则
            rules = extract_rules(features, type_id)

            # 构造子源（脱敏）
            subsource = {
                'sourceName': f"源[{idx}] - {cat_label}",
                'sourceUrl': sanitize_url(cat_url),
                'sourceGroup': '集成拆分',
                'sourceComment': f"// 简化说明:从父集成站拆分,父源index={idx},原分类={cat_label}",
                'type': type_id,
                'enabled': True,
                'sortUrl': '',
                'searchUrl': rules['searchUrl'],
                'ruleArticles': rules['ruleArticles'],
                'ruleNextPage': rules['ruleNextPage'],
                'ruleTitle': rules['ruleTitle'],
                'ruleImage': rules['ruleImage'],
                'ruleUrl': rules['ruleUrl'],
                'ruleContent': rules['ruleContent'],
            }

            subsources.append({
                'parent_source_index': idx,
                'category_name': cat_label,  # 已脱敏为 分类[M]
                'subsource': subsource,
                'confidence': confidence,
                'detected_features': feats,
            })
            print(f"[OK] type={type_id} conf={confidence}")

        except Exception as e:
            print(f"[FAIL] {sanitize_exception(e)}")
            failed.append({
                'parent_source_index': idx,
                'category_name': cat_label,
                'error': sanitize_exception(e),
            })
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    # 失败率检查
    total_cats = len(categories)
    failed_count = len(failed)
    if total_cats > 0 and failed_count / total_cats > 0.5:
        print(f"  [idx={idx}] 失败率={failed_count/total_cats:.2f}>0.5, 父源保持enabled")
        return subsources, failed, False  # 父源保持enabled

    return subsources, failed, True  # 父源禁用


# ============== 主流程 ==============
def main():
    print("=" * 80)
    print("集成站深度拆分 Phase 2-C")
    print("=" * 80)

    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        return

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # V4格式是dict，源在 sources 键里
    if isinstance(data, dict) and 'sources' in data:
        sources = data['sources']
        print(f"[INFO] V4版本: {data.get('version', 'N/A')}, total_sources字段: {data.get('total_sources', 'N/A')}")
    else:
        sources = data

    print(f"[INFO] 输入源总数: {len(sources)}")
    print(f"[INFO] 集成站索引({len(AGGREGATOR_INDICES)}): {AGGREGATOR_INDICES}")

    all_subsources: List[dict] = []
    all_failed: List[dict] = []
    parent_disabled_records: List[dict] = []
    parent_partial_records: List[dict] = []
    parent_no_split: List[dict] = []

    started_at = datetime.now()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={'width': 375, 'height': 667},
            locale='zh-CN',
            extra_http_headers={'Accept-Language': 'zh-CN'},
        )

        for idx in AGGREGATOR_INDICES:
            if idx >= len(sources):
                print(f"\n--- 处理父源 idx={idx} --- 越界，跳过")
                parent_no_split.append({'source_index': idx, 'reason': 'out_of_range'})
                continue

            source = sources[idx]
            print(f"\n--- 处理父源 idx={idx} ---")

            subsources, failed, parent_disabled = process_aggregator(source, idx, context)

            all_subsources.extend(subsources)
            all_failed.extend(failed)

            if len(subsources) == 0 and len(failed) == 0:
                # 无可拆分分类
                parent_no_split.append({'source_index': idx, 'reason': 'no_categories'})
            elif parent_disabled:
                parent_disabled_records.append({
                    'source_index': idx,
                    'subsource_count': len(subsources),
                    'failed_count': len(failed),
                })
            else:
                parent_partial_records.append({
                    'source_index': idx,
                    'subsource_count': len(subsources),
                    'failed_count': len(failed),
                    'reason': 'failure_rate_over_50_percent',
                })

        browser.close()

    elapsed = (datetime.now() - started_at).total_seconds()

    # 统计 by_type
    by_type: Dict[int, int] = {}
    for s in all_subsources:
        t = s['subsource']['type']
        by_type[t] = by_type.get(t, 0) + 1

    # 按type排序输出
    by_type_sorted = {f"type{k}": v for k, v in sorted(by_type.items())}

    # 输出
    output = {
        'split_at': started_at.isoformat(),
        'elapsed_seconds': round(elapsed, 1),
        'parent_count': len(AGGREGATOR_INDICES),
        'total_subsources': len(all_subsources),
        'by_type': by_type_sorted,
        'failed_categories': len(all_failed),
        'subsources': all_subsources,
        'parent_disabled': parent_disabled_records,
        'parent_partial': parent_partial_records,
        'parent_no_split': parent_no_split,
        'failed_details': all_failed,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"[DONE] 父站数: {len(AGGREGATOR_INDICES)}")
    print(f"[DONE] 子源数: {len(all_subsources)}")
    print(f"[DONE] 失败数: {len(all_failed)}")
    print(f"[DONE] 各type分布: {by_type_sorted}")
    print(f"[DONE] 完全拆分父站(将禁用): {len(parent_disabled_records)}")
    print(f"[DONE] 部分拆分父站(保持enabled): {len(parent_partial_records)}")
    print(f"[DONE] 无可拆分父站: {len(parent_no_split)}")
    print(f"[DONE] 耗时: {elapsed:.1f}s")
    print(f"[DONE] 输出文件: {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
