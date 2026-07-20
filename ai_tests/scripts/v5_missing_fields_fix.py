# -*- coding: utf-8 -*-
"""
v5_missing_fields_fix.py
对135个缺字段源深度补全：
- Playwright mobile_context 访问 sourceUrl
- 注入去弹框 JS
- DOM 结构检测（列表/标题/下一页/图片/搜索表单）
- 根据缺失字段补全（searchUrl/sortUrl/ruleNextPage/ruleArticles/enabled）
- 输出已脱敏的 v5_missing_fields_fix.json
"""
import json
import time
import re
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Error as PWError

# ============ 配置 ============
V4_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v4.json"
CLASSIFICATION_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_classification.json"
OUTPUT_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_missing_fields_fix.json"
PROGRESS_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_missing_fields_fix.progress.txt"
SUMMARY_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_missing_fields_fix.summary.txt"

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
VIEWPORT = {"width": 375, "height": 667}
TIMEOUT_MS = 30000

REMOVE_POPUP_JS = """
document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal').forEach(e=>e.remove())
"""

DOM_DETECT_JS = r"""
(() => {
  const result = {
    list_hits: [],
    title_hits: [],
    nextpage_hits: [],
    image_hits: [],
    search_form_found: false,
    search_form_action: '',
    search_input_name: '',
    pagination_found: false,
    infinite_scroll_hint: false
  };
  const listSelectors = ['.entry-card','.post','.article','.item','.card','.video-item','.image-item','.list-item','.box','.thumbnail','.entry','.lazy','.thumb'];
  for (const sel of listSelectors) {
    try { const els = document.querySelectorAll(sel); if (els.length > 0) result.list_hits.push({selector: sel, count: els.length}); } catch(e){}
  }
  const titleSelectors = ['h1','h2','h3','h4','.title','.name','.post-title','.entry-title'];
  for (const sel of titleSelectors) {
    try { const els = document.querySelectorAll(sel); if (els.length > 0) result.title_hits.push({selector: sel, count: els.length}); } catch(e){}
  }
  const nextSelectors = ['a.next','a[rel=next]','.pagination a:last-child','.page-next','.next a','.pager a:last-child','.nextpage','a:contains("下一页")','a:contains("Next")'];
  for (const sel of nextSelectors) {
    try {
      if (sel.indexOf(':contains') >= 0) continue;
      const els = document.querySelectorAll(sel);
      if (els.length > 0) result.nextpage_hits.push({selector: sel, count: els.length});
    } catch(e){}
  }
  // 文本匹配下一页
  try {
    const links = document.querySelectorAll('a');
    for (const a of links) {
      const txt = (a.textContent || '').trim();
      if (txt === '下一页' || txt === '下页' || txt === 'Next' || txt === 'next' || txt === '»' || txt === '>') {
        result.nextpage_hits.push({selector: 'a:text(' + txt + ')', count: 1, href: a.getAttribute('href') || ''});
        break;
      }
    }
  } catch(e){}
  // 分页容器
  try {
    const pag = document.querySelectorAll('.pagination,.pager,.page-nav,.page-navi,.pagenavi');
    if (pag.length > 0) result.pagination_found = true;
  } catch(e){}
  // 图片选择器
  try {
    const imgs = document.querySelectorAll('img');
    if (imgs.length > 0) result.image_hits.push({selector: 'img::attr(src)', count: imgs.length});
    const lazyImgs = document.querySelectorAll('.lazyload,.lazy');
    if (lazyImgs.length > 0) result.image_hits.push({selector: '.lazyload::attr(data-src)', count: lazyImgs.length});
    const thumbImgs = document.querySelectorAll('.thumb img');
    if (thumbImgs.length > 0) result.image_hits.push({selector: '.thumb img::attr(src)', count: thumbImgs.length});
  } catch(e){}
  // 搜索表单
  try {
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
      const action = form.getAttribute('action') || '';
      const inputs = form.querySelectorAll('input[name]');
      for (const input of inputs) {
        const name = (input.getAttribute('name') || '').toLowerCase();
        if (['q','s','search','keyword','wd','key','kw'].includes(name)) {
          result.search_form_found = true;
          result.search_form_action = action;
          result.search_input_name = name;
          break;
        }
      }
      if (result.search_form_found) break;
    }
  } catch(e){}
  // 无限滚动提示（含加载更多按钮或 sentinel 元素）
  try {
    const loadMore = document.querySelectorAll('.load-more,.loadmore,.js-load-more,#load_more,.infinite-scroll');
    if (loadMore.length > 0) result.infinite_scroll_hint = true;
  } catch(e){}
  return result;
})()
"""

# ============ 工具函数 ============
def mask_url(url):
    """脱敏 URL：域名→[DOMAIN]，锚点→[ANCHOR]，查询参数保留模式"""
    if not url:
        return ""
    m = re.sub(r'://[^/]+', '://[DOMAIN]', url)
    m = re.sub(r'#.*', '#[ANCHOR]', m)
    return m

def get_domain(url):
    """从 URL 提取域名（含端口），去除锚点"""
    if not url:
        return ""
    # 先去除锚点
    url = url.split('#')[0]
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1) if m else ""

def build_search_url(domain, action, input_name):
    """基于搜索表单构造 searchUrl"""
    key_ph = "{{key}}"
    page_ph = "{{page}}"
    if action and action.startswith('http'):
        base = action
    elif action and action.startswith('/'):
        base = f"http://{domain}{action}"
    else:
        base = f"http://{domain}/search"
    sep = '&' if '?' in base else '?'
    return f"{base}{sep}{input_name}={key_ph},page={page_ph}"

def detect_source(page, source_url):
    """访问源URL并检测DOM，返回 dict"""
    result = {'page_ok': False, 'dom_hit': None, 'error': None, 'status': None}
    try:
        resp = page.goto(source_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        if resp:
            result['status'] = resp.status
        # 等待 networkidle（短超时，失败不致命）
        try:
            page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        # 注入去弹框
        try:
            page.evaluate(REMOVE_POPUP_JS)
        except Exception:
            pass
        # 滚动2次加载内容
        try:
            page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            page.wait_for_timeout(800)
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(800)
        except Exception:
            pass
        # DOM 检测
        dom_hit = page.evaluate(DOM_DETECT_JS)
        result['page_ok'] = True
        result['dom_hit'] = dom_hit
    except PWTimeoutError:
        result['error'] = 'timeout'
    except PWError as e:
        msg = str(e)[:80]
        result['error'] = 'pw_error:' + type(e).__name__
    except Exception as e:
        result['error'] = 'err:' + type(e).__name__
    return result

def try_search_endpoints(page, domain):
    """对缺 searchUrl 的源，尝试访问常见搜索路径检测"""
    candidates = [
        f"http://{domain}/search?q=test",
        f"http://{domain}/?s=test",
        f"http://{domain}/search.php?q=test",
        f"http://{domain}/index.php?search=test",
    ]
    for url in candidates:
        try:
            resp = page.goto(url, wait_until='domcontentloaded', timeout=15000)
            if resp and resp.status < 400:
                # 检测页面是否有结果列表
                try:
                    page.evaluate(REMOVE_POPUP_JS)
                except Exception:
                    pass
                try:
                    dom = page.evaluate(DOM_DETECT_JS)
                    if dom and (dom.get('list_hits') or dom.get('title_hits')):
                        return {'ok': True, 'endpoint': url, 'has_results': True}
                except Exception:
                    pass
        except Exception:
            continue
    return {'ok': False}

def try_sort_endpoints(page, domain):
    """对缺 sortUrl 的源，尝试访问 /sitemap 或 /categories 提取分类URL"""
    candidates = [
        f"http://{domain}/sitemap",
        f"http://{domain}/sitemap.xml",
        f"http://{domain}/categories",
        f"http://{domain}/category",
        f"http://{domain}/categories.html",
    ]
    for url in candidates:
        try:
            resp = page.goto(url, wait_until='domcontentloaded', timeout=15000)
            if resp and resp.status < 400:
                # 提取分类链接
                try:
                    cats = page.evaluate(r"""
                    (() => {
                      const links = document.querySelectorAll('a[href*="category"],a[href*="cat"],a[href*="/sort"],a[href*="/list"]');
                      const result = [];
                      for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        const txt = (a.textContent || '').trim();
                        if (href && txt && txt.length < 20) {
                          result.push({href: href, text: txt});
                        }
                        if (result.length >= 20) break;
                      }
                      return result;
                    })()
                    """)
                    if cats and len(cats) > 0:
                        return {'ok': True, 'endpoint': url, 'categories': cats}
                except Exception:
                    pass
        except Exception:
            continue
    return {'ok': False}

def fix_source(source, missing_fields, detect_result, page):
    """根据缺失字段和检测结果补全"""
    fixes = {}
    evidence = {
        'dom_hit': [],
        'search_form_found': False,
        'nextpage_hit': False,
        'pagination_found': False,
        'infinite_scroll_hint': False,
        'search_endpoint_tested': False,
        'sort_endpoint_tested': False
    }
    confidence = 0.5
    
    source_url = source.get('sourceUrl', '') or ''
    domain = get_domain(source_url)
    dom_hit = detect_result.get('dom_hit') or {}
    
    # 记录 DOM 命中（仅 selector 名，不含内容）
    for hit in dom_hit.get('list_hits', [])[:3]:
        evidence['dom_hit'].append(hit['selector'])
    for hit in dom_hit.get('title_hits', [])[:2]:
        evidence['dom_hit'].append(hit['selector'])
    
    evidence['pagination_found'] = bool(dom_hit.get('pagination_found'))
    evidence['infinite_scroll_hint'] = bool(dom_hit.get('infinite_scroll_hint'))
    
    # 缺 sortUrl
    if 'sortUrl' in missing_fields:
        sort_result = {'ok': False}
        if page and domain:
            try:
                sort_result = try_sort_endpoints(page, domain)
                evidence['sort_endpoint_tested'] = True
            except Exception:
                sort_result = {'ok': False}
        if sort_result.get('ok') and sort_result.get('categories'):
            # 构造 sortUrl：用源URL作为基础
            cats = sort_result['categories'][:10]
            sort_url_parts = []
            for c in cats:
                href = c.get('href', '')
                if href.startswith('/'):
                    href = f"http://{domain}{href}"
                elif not href.startswith('http'):
                    href = f"http://{domain}/{href}"
                txt = c.get('text', '').strip()
                if href and txt:
                    sort_url_parts.append(f"{txt}::{href}")
            if sort_url_parts:
                fixes['sortUrl'] = '\n'.join(sort_url_parts)
                confidence = max(confidence, 0.8)
            else:
                fixes['sortUrl'] = source_url
                confidence = min(confidence, 0.4)
        else:
            # fallback: 用 sourceUrl 本身
            fixes['sortUrl'] = source_url
            confidence = min(confidence, 0.4)
    
    # 缺 searchUrl
    if 'searchUrl' in missing_fields:
        search_form = dom_hit.get('search_form_found', False)
        if search_form:
            action = dom_hit.get('search_form_action', '')
            input_name = dom_hit.get('search_input_name', 'q') or 'q'
            fixes['searchUrl'] = build_search_url(domain, action, input_name)
            evidence['search_form_found'] = True
            confidence = max(confidence, 0.85)
        else:
            # 尝试访问常见搜索路径
            search_result = {'ok': False}
            if page and domain:
                try:
                    search_result = try_search_endpoints(page, domain)
                    evidence['search_endpoint_tested'] = True
                except Exception:
                    search_result = {'ok': False}
            if search_result.get('ok'):
                # 基于命中的 endpoint 构造
                endpoint = search_result['endpoint']
                # 将 test 替换为占位符
                url_clean = endpoint.replace('q=test', 'q={{key}}').replace('s=test', 's={{key}}').replace('search=test', 'search={{key}}').replace('?test', '?{{key}}')
                if 'page' not in url_clean:
                    url_clean = url_clean + ',page={{page}}'
                fixes['searchUrl'] = url_clean
                confidence = max(confidence, 0.7)
            else:
                # fallback 默认模板
                fixes['searchUrl'] = f"http://{domain}/search?q={{{{key}}}}"
                confidence = min(confidence, 0.3)
    
    # 缺 ruleNextPage
    if 'ruleNextPage' in missing_fields:
        next_hits = dom_hit.get('nextpage_hits', [])
        if next_hits:
            first = next_hits[0]
            sel = first['selector']
            # 处理文本匹配的 a
            if sel.startswith('a:text('):
                fixes['ruleNextPage'] = 'a@href||text==' + sel[7:-1]
            else:
                fixes['ruleNextPage'] = sel + '@href'
            evidence['nextpage_hit'] = True
            confidence = max(confidence, 0.85)
        elif evidence['infinite_scroll_hint']:
            fixes['ruleNextPage'] = 'js:window.scrollTo(0,document.body.scrollHeight)'
            confidence = max(confidence, 0.6)
        else:
            # 无命中的留空
            fixes['ruleNextPage'] = ''
            confidence = min(confidence, 0.4)
    
    # 缺 ruleArticles
    if 'ruleArticles' in missing_fields:
        list_hits = dom_hit.get('list_hits', [])
        if list_hits:
            fixes['ruleArticles'] = list_hits[0]['selector']
            confidence = max(confidence, 0.9)
        else:
            # fallback
            fixes['ruleArticles'] = '.post,.article,.item'
            confidence = min(confidence, 0.5)
    
    # enabled=false 的源
    if 'enabled=false' in missing_fields:
        if detect_result.get('page_ok') and dom_hit and (dom_hit.get('list_hits') or dom_hit.get('title_hits')):
            fixes['enabled'] = True
            confidence = max(confidence, 0.7)
        else:
            fixes['enabled'] = False
            confidence = min(confidence, 0.3)
    
    return fixes, evidence, confidence

# ============ 主流程 ============
def main():
    # 清空进度文件
    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
        f.write(f"[START] {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    
    # 读取 V4
    with open(V4_PATH, 'r', encoding='utf-8') as f:
        v4_raw = json.load(f)
    # V4 顶层是 dict，源数组在 ['sources'] 下
    if isinstance(v4_raw, dict) and 'sources' in v4_raw:
        v4_data = v4_raw['sources']
    else:
        v4_data = v4_raw
    
    # 读取分类
    with open(CLASSIFICATION_PATH, 'r', encoding='utf-8') as f:
        classification = json.load(f)
    
    missing_list = classification.get('by_category', {}).get('missing_fields', [])
    total = len(missing_list)
    
    # 支持环境变量限制数量（冒烟测试用）
    limit_env = os.environ.get('V5_LIMIT', '')
    if limit_env and limit_env.isdigit():
        total = min(total, int(limit_env))
        missing_list = missing_list[:total]
    
    print(f"[START] total={total}, v4_len={len(v4_data)}")
    with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[INFO] total={total}, v4_len={len(v4_data)}\n")
    
    fixes_result = {
        'analyzed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_input': total,
        'success_count': 0,
        'failed_count': 0,
        'by_missing_field': {
            'sortUrl_fixed': 0,
            'searchUrl_fixed': 0,
            'ruleNextPage_fixed': 0,
            'ruleArticles_fixed': 0,
            'enabled_recovered': 0
        },
        'fixes': [],
        'failed': []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            user_agent=MOBILE_UA,
            locale='zh-CN',
            extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9'}
        )
        context.set_default_timeout(TIMEOUT_MS)
        page = context.new_page()
        
        for i, item in enumerate(missing_list):
            idx = item['source_index']
            missing = item['missing']
            
            # 写进度（脱敏：只记录 idx 和 missing，不记录 URL）
            with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
                f.write(f"[{i+1}/{total}] idx={idx} missing={missing}\n")
            
            # 边界检查
            if idx >= len(v4_data):
                fixes_result['failed'].append({
                    'source_index': idx,
                    'reason': 'index_out_of_range'
                })
                fixes_result['failed_count'] += 1
                continue
            
            source = v4_data[idx]
            source_url = source.get('sourceUrl', '') or ''
            
            if not source_url:
                fixes_result['failed'].append({
                    'source_index': idx,
                    'reason': 'no_sourceUrl'
                })
                fixes_result['failed_count'] += 1
                continue
            
            # 第一次访问
            detect_result = detect_source(page, source_url)
            # 失败则重试1次
            if not detect_result['page_ok']:
                with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
                    f.write(f"  retry1 idx={idx} reason={detect_result.get('error')}\n")
                detect_result = detect_source(page, source_url)
            
            if not detect_result['page_ok']:
                fixes_result['failed'].append({
                    'source_index': idx,
                    'reason': detect_result.get('error', 'unknown')
                })
                fixes_result['failed_count'] += 1
                # 写中间结果（每25个为一批）
                if (i + 1) % 25 == 0:
                    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                        json.dump(fixes_result, f, ensure_ascii=False, indent=2)
                continue
            
            # 补全
            try:
                new_fields, evidence, confidence = fix_source(source, missing, detect_result, page)
            except Exception as e:
                fixes_result['failed'].append({
                    'source_index': idx,
                    'reason': 'fix_error:' + type(e).__name__
                })
                fixes_result['failed_count'] += 1
                continue
            
            # 统计
            for k, v in new_fields.items():
                if k == 'sortUrl' and v:
                    fixes_result['by_missing_field']['sortUrl_fixed'] += 1
                elif k == 'searchUrl' and v:
                    fixes_result['by_missing_field']['searchUrl_fixed'] += 1
                elif k == 'ruleNextPage':
                    fixes_result['by_missing_field']['ruleNextPage_fixed'] += 1
                elif k == 'ruleArticles' and v:
                    fixes_result['by_missing_field']['ruleArticles_fixed'] += 1
                elif k == 'enabled' and v is True:
                    fixes_result['by_missing_field']['enabled_recovered'] += 1
            
            fixes_result['fixes'].append({
                'source_index': idx,
                'sourceUrl_pattern': mask_url(source_url),
                'missing_fields': missing,
                'new_fields': new_fields,
                'confidence': round(confidence, 2),
                'evidence': {
                    'dom_hit': evidence['dom_hit'],
                    'search_form_found': evidence['search_form_found'],
                    'nextpage_hit': evidence['nextpage_hit'],
                    'pagination_found': evidence['pagination_found'],
                    'infinite_scroll_hint': evidence['infinite_scroll_hint'],
                    'search_endpoint_tested': evidence['search_endpoint_tested'],
                    'sort_endpoint_tested': evidence['sort_endpoint_tested']
                }
            })
            fixes_result['success_count'] += 1
            
            # 每25个写一次中间结果
            if (i + 1) % 25 == 0:
                with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                    json.dump(fixes_result, f, ensure_ascii=False, indent=2)
                print(f"[PROGRESS] {i+1}/{total} success={fixes_result['success_count']} failed={fixes_result['failed_count']}")
        
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass
    
    # 写最终输出
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(fixes_result, f, ensure_ascii=False, indent=2)
    
    # 写技术摘要（不含URL）
    summary = {
        'analyzed_at': fixes_result['analyzed_at'],
        'total_input': fixes_result['total_input'],
        'success_count': fixes_result['success_count'],
        'failed_count': fixes_result['failed_count'],
        'by_missing_field': fixes_result['by_missing_field'],
        'failed_reasons': {},
        'confidence_distribution': {'high_ge_0.8': 0, 'mid_0.5_0.8': 0, 'low_lt_0.5': 0}
    }
    # 失败原因统计
    for f_item in fixes_result['failed']:
        r = f_item.get('reason', 'unknown')
        summary['failed_reasons'][r] = summary['failed_reasons'].get(r, 0) + 1
    # 置信度分布
    for fx in fixes_result['fixes']:
        c = fx.get('confidence', 0)
        if c >= 0.8:
            summary['confidence_distribution']['high_ge_0.8'] += 1
        elif c >= 0.5:
            summary['confidence_distribution']['mid_0.5_0.8'] += 1
        else:
            summary['confidence_distribution']['low_lt_0.5'] += 1
    
    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"[DONE] success={fixes_result['success_count']} failed={fixes_result['failed_count']}")
    print(f"[STATS] {fixes_result['by_missing_field']}")
    print(f"[CONF] {summary['confidence_distribution']}")
    print(f"[FAIL_REASONS] {summary['failed_reasons']}")

if __name__ == '__main__':
    main()
