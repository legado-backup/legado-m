#!/usr/bin/env python3
r"""batch_optimize_sources.py — 批量优化订阅源（v4 + Playwright）

工作流：
    1. 读取 exported_from_emulator.json（65个源）
    2. 对每个源用 Playwright 真实访问站点首页
    3. 用 JavaScript IIFE 提取缺失字段值（sourceIcon/searchUrl/sortUrl/ruleNextPage/ruleDescription/ruleImage）
    4. 补全源 JSON（只补缺失字段，不覆盖已有值）
    5. 保存为 optimized_batch.json + 输出统计报告

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/batch_optimize_sources.py

输入：output/rss/exported_from_emulator.json
输出：output/rss/optimized_batch.json + output/rss/optimization_report.json
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / '.trae/skills/legado-source-creator/scripts'))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 导入 v4 校验器
from legado_client.validator import validate_source


# ==================== 工具函数 ====================

def extract_base_url(source_url: str) -> str:
    """从 sourceUrl 模板提取真实首页 URL。

    例：https://xxx.com/{{page==1?'':'page/'+page+'/'}} → https://xxx.com/
    """
    if not source_url:
        return ''
    # 去掉 {{}} 模板部分
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    return base.rstrip('/') + '/'


def build_search_url(form_info: dict) -> str:
    """从表单信息构建 searchUrl"""
    if not form_info or not form_info.get('action'):
        return ''
    action = form_info['action'].rstrip('?').rstrip('&')
    inputs = form_info.get('inputs', [])
    text_input = next((i for i in inputs if i.get('type') in ('text', 'search')), None)
    if text_input and text_input.get('name'):
        sep = '&' if '?' in action else '?'
        return f"{action}{sep}{text_input['name']}={{{{key}}}}"
    return ''


def build_sort_url(category_links: list, hot_links: list, base_url: str) -> str:
    """从分类链接+排序参数构建 sortUrl"""
    items = []
    if hot_links:
        items.append(f"热门::{hot_links[0]}")
    if category_links:
        # 优先 /categories/ 全分类页
        all_cat = next((l for l in category_links if '/categories/' in l.get('href', '')), None)
        if all_cat:
            items.append(f"全部分类::{all_cat['href']}")
        # 也加几个 tag 分类（限制3个，避免敏感词）
        tag_links = [l for l in category_links if '/tag/' in l.get('href', '') or '/tags/' in l.get('href', '')]
        for tl in tag_links[:3]:
            text = tl.get('text', '').strip()
            if text and len(text) <= 20:
                items.append(f"{text}::{tl['href']}")
    items.append(f"最新::{base_url}")
    return '\n'.join(items)


def extract_next_page_selector(pagination_html: str) -> str:
    """从分页HTML提取下一页CSS选择器"""
    if not pagination_html:
        return ''
    if 'next page-link' in pagination_html:
        return '@CSS:a.next.page-link@href'
    if 'class="next"' in pagination_html or 'class=\'next\'' in pagination_html:
        return '@CSS:a.next@href'
    if 'rel="next"' in pagination_html or 'rel=\'next\'' in pagination_html:
        return '@CSS:a[rel="next"]@href'
    if 'page-link' in pagination_html:
        return '@CSS:a.page-link:last-child@href'
    return ''


# ==================== JavaScript 提取模板 ====================

EXTRACT_JS = """
(function() {
  const result = {};
  // 1. sourceIcon: favicon
  const iconLink = document.querySelector('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
  result.icon = iconLink ? iconLink.href : null;
  if (!result.icon) {
    const metaImg = document.querySelector('meta[itemprop="image"], meta[property="og:image"]');
    result.icon = metaImg ? metaImg.content : null;
  }
  if (!result.icon) {
    result.icon = window.location.origin + '/favicon.ico';
  }
  // 2. searchForm
  const searchForm = document.querySelector('form[action*="search"], form[id*="search"], form[class*="search"], #searchform, .search-form');
  result.searchForm = searchForm ? {
    action: searchForm.action || window.location.origin + '/',
    method: searchForm.method || 'get',
    inputs: Array.from(searchForm.querySelectorAll('input,select')).map(function(i) {
      return {name: i.name, type: i.type, placeholder: i.placeholder};
    })
  } : null;
  // 3. categoryLinks
  const allLinks = Array.from(document.querySelectorAll('a[href]'));
  result.categoryLinks = allLinks.filter(function(a) {
    return /\\/category\\//i.test(a.href) || /\\/tags?\\//i.test(a.href);
  }).slice(0, 15).map(function(a) {
    return {href: a.href, text: a.textContent.trim().substring(0, 30)};
  });
  // 4. hotLinks (排序参数)
  result.hotLinks = allLinks.filter(function(a) {
    return /filter=popular|filter=hot|sort=|order=/i.test(a.href);
  }).slice(0, 5).map(function(a) { return a.href; });
  // 5. pagination
  const pagination = document.querySelector('.pagination, .page-nav, .nav-links, .wp-pagenavi, nav[role="navigation"], ul.page-numbers');
  result.paginationHTML = pagination ? pagination.outerHTML.substring(0, 2000) : null;
  // 6. ruleDescription: 查找播放数/观看数元素
  const viewsEl = document.querySelector('.views, .views-number, .views_count, .video-views, .post-views, [class*="views"]');
  result.ruleDescriptionSelector = viewsEl ? viewsEl.className.split(' ')[0] : null;
  // 7. ruleImage
  const firstImg = document.querySelector('img[data-src], img.lazyload, img.video-img, .thumb img, .post-thumbnail img');
  if (firstImg) {
    const cls = firstImg.className.split(' ')[0];
    const dataSrc = firstImg.getAttribute('data-src') !== null ? '@data-src' : '@src';
    result.ruleImageSelector = cls ? '@CSS:img.' + cls + dataSrc : '@CSS:img' + dataSrc;
  } else {
    result.ruleImageSelector = null;
  }
  // 8. sourceComment: 提取页面主题信息
  const generatorMeta = document.querySelector('meta[name="generator"]');
  result.cmsInfo = generatorMeta ? generatorMeta.content : null;
  return JSON.stringify(result, null, 2);
})();
"""


# ==================== 主流程 ====================

def optimize_single_source(page, source: dict) -> tuple:
    """优化单个源，返回 (optimized_source, extract_info, error)"""
    source_url = source.get('sourceUrl', '')
    base_url = extract_base_url(source_url)
    if not base_url or not base_url.startswith('http'):
        return source, None, f'invalid sourceUrl: len={len(source_url)}'

    try:
        page.goto(base_url, timeout=30000, wait_until='domcontentloaded')
    except PlaywrightTimeout:
        return source, None, 'navigate timeout'
    except Exception as e:
        return source, None, f'navigate error: {type(e).__name__}'

    # 检测是否被 CF 拦截
    try:
        title = page.title()
        if 'Just a moment' in title or 'Cloudflare' in title:
            return source, None, 'CF challenge blocked'
    except Exception:
        pass

    # 执行 JavaScript 提取
    try:
        result_json = page.evaluate(EXTRACT_JS)
        extracted = json.loads(result_json) if isinstance(result_json, str) else result_json
    except Exception as e:
        return source, None, f'eval error: {type(e).__name__}'

    # 补全缺失字段
    optimized = dict(source)  # 拷贝
    fields_filled = []

    # sourceIcon
    if not source.get('sourceIcon') and extracted.get('icon'):
        optimized['sourceIcon'] = extracted['icon']
        fields_filled.append('sourceIcon')

    # searchUrl
    if not source.get('searchUrl'):
        search_url = build_search_url(extracted.get('searchForm'))
        if search_url:
            optimized['searchUrl'] = search_url
            fields_filled.append('searchUrl')

    # sortUrl
    if not source.get('sortUrl'):
        sort_url = build_sort_url(
            extracted.get('categoryLinks', []),
            extracted.get('hotLinks', []),
            base_url
        )
        if sort_url:
            optimized['sortUrl'] = sort_url
            fields_filled.append('sortUrl')

    # ruleNextPage
    if not source.get('ruleNextPage'):
        next_selector = extract_next_page_selector(extracted.get('paginationHTML', ''))
        if next_selector:
            optimized['ruleNextPage'] = next_selector
            fields_filled.append('ruleNextPage')

    # ruleDescription
    if not source.get('ruleDescription') and extracted.get('ruleDescriptionSelector'):
        optimized['ruleDescription'] = f"@CSS:.{extracted['ruleDescriptionSelector']}@text"
        fields_filled.append('ruleDescription')

    # ruleImage
    if not source.get('ruleImage') and extracted.get('ruleImageSelector'):
        optimized['ruleImage'] = extracted['ruleImageSelector']
        fields_filled.append('ruleImage')

    # sourceComment（不覆盖已有）
    if not source.get('sourceComment'):
        cms = extracted.get('cmsInfo') or ''
        comment = f"批量优化 - CMS:{cms}" if cms else "批量优化 - Playwright分析"
        optimized['sourceComment'] = comment
        fields_filled.append('sourceComment')

    return optimized, extracted, None


def main():
    input_file = PROJECT_ROOT / 'output/rss/exported_from_emulator.json'
    output_file = PROJECT_ROOT / 'output/rss/optimized_batch.json'
    report_file = PROJECT_ROOT / 'output/rss/optimization_report.json'

    print("=" * 60)
    print("批量优化订阅源 - v4 + Playwright")
    print("=" * 60)

    # 读取源
    with open(input_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f"加载源: {len(sources)} 个")

    # 启动 Playwright
    optimized_sources = []
    report = {
        'total': len(sources),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': [],
        'fields_filled_stats': {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()

        for i, src in enumerate(sources):
            source_name = src.get('sourceName', f'source_{i}')
            source_url = src.get('sourceUrl', '')
            # 脱敏输出（只显示长度，不显示完整URL）
            print(f"\n[{i+1}/{len(sources)}] name_len={len(source_name)} url_len={len(source_url)}")

            # 先校验是否需要优化
            r_before = validate_source(src, source_type='rss', strict_recommended=True)
            if r_before['passed']:
                print(f"  SKIP - already passed")
                optimized_sources.append(src)
                report['skipped'] += 1
                report['details'].append({
                    'idx': i, 'name_len': len(source_name),
                    'status': 'skipped', 'fields_filled': []
                })
                continue

            # 优化
            optimized, extracted, error = optimize_single_source(page, src)

            if error:
                print(f"  FAIL - {error}")
                optimized_sources.append(src)  # 保留原值
                report['failed'] += 1
                report['details'].append({
                    'idx': i, 'name_len': len(source_name),
                    'status': 'failed', 'error': error
                })
                continue

            # 重新校验
            r_after = validate_source(optimized, source_type='rss', strict_recommended=True)
            fields_filled = []
            for field in ['sourceIcon', 'searchUrl', 'sortUrl', 'ruleNextPage',
                          'ruleDescription', 'ruleImage', 'sourceComment']:
                if not src.get(field) and optimized.get(field):
                    fields_filled.append(field)
                    report['fields_filled_stats'][field] = report['fields_filled_stats'].get(field, 0) + 1

            print(f"  OK - filled {len(fields_filled)} fields: {fields_filled}")
            if r_after['passed']:
                print(f"  PASSED validation")
            else:
                still_missing = r_after.get('all_missing', [])
                print(f"  still missing: {still_missing}")

            optimized_sources.append(optimized)
            report['success'] += 1
            report['details'].append({
                'idx': i, 'name_len': len(source_name),
                'status': 'success', 'fields_filled': fields_filled,
                'passed_after': r_after['passed'],
                'still_missing': r_after.get('all_missing', []),
            })

            # 短暂延迟避免被反爬
            time.sleep(0.5)

        browser.close()

    # 写入优化后的JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(optimized_sources, f, ensure_ascii=False, indent=2)
    print(f"\n优化后JSON已保存: {output_file}")

    # 写入报告
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"优化报告已保存: {report_file}")

    # 输出统计
    print("\n" + "=" * 60)
    print("批量优化统计")
    print("=" * 60)
    print(f"总计: {report['total']}")
    print(f"成功: {report['success']}")
    print(f"失败: {report['failed']}")
    print(f"跳过: {report['skipped']}")
    print(f"\n字段补全统计:")
    for k, v in sorted(report['fields_filled_stats'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} sources")


if __name__ == '__main__':
    main()
