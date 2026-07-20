#!/usr/bin/env python3
r"""v5_4_fix_list_sources.py — 用 Playwright 深度修复 31 个 list 失败源

工作流（每个源）：
1. Playwright 真实访问 sourceUrl（mobile UA + 8s 等待）
2. 检测 CF 盾/登录页 → 标记 enabled=false
3. BS4 解析 DOM，找列表容器+列表项
4. 从首项提取 title/link/image/desc/date 字段规则
5. 本地校验：新规则能否拿到 ≥3 个列表项
6. 最多重试 3 次（不同选择器策略）
7. 输出修复后的源

输出：
- output/rss/v5_4_fixed_sources.json（31 个修复后的源对象列表）
- output/rss/v5_4_fix_report.json（修复统计）

安全规范：禁止输出源名称/URL/cookie，全部用 idx 编号。
"""
import json
import re
import sys
import time
from pathlib import Path
from collections import Counter

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
CLEANED_JSON = ROOT / "output" / "rss" / "optimized_v5_4_cleaned.json"
V53_JSON = ROOT / "output" / "rss" / "optimized_v5_3_final.json"
VERIFY_JSON = ROOT / "output" / "rss" / "v5_3_debug_verify_result.json"
OUT_SOURCES = ROOT / "output" / "rss" / "v5_4_fixed_sources.json"
OUT_REPORT = ROOT / "output" / "rss" / "v5_4_fix_report.json"
DEBUG_DIR = ROOT / "output" / "rss" / "v5_4_fix_debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# list 失败的 verify idx 清单（来自 V5.3 验证报告）
# 包含 21 list_empty + 10 list_parse_failed = 31 个
LIST_FAILED_VERIFY_IDXS = [
    2, 3, 4, 6, 7, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53,
    55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
]

# 浏览器配置
MOBILE_UA = ('Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')
PAGE_TIMEOUT_MS = 30000       # 单页超时 30s
WAIT_AFTER_LOAD_SEC = 8       # DOMContentLoaded 后额外等待

# 候选列表选择器（按优先级排序，覆盖常见 RSS 站点结构）
LIST_SELECTOR_CANDIDATES = [
    # 专用容器
    '.article-list .article-item',
    '.article-list li',
    '.post-list .post',
    '.post-list li',
    '.news-list li',
    '.news-list .item',
    '.list-box .item',
    '.list-content .item',
    '.content-list .item',
    '.content-list li',
    '.entry-list .entry',
    '.entry-list article',
    '.articles article',
    '.articles .article',
    '.posts .post',
    '.posts article',
    '.cards .card',
    '.card-list .card',
    '.item-list .item',
    '.thread-list .thread',
    '.topic-list .topic',
    '.feed .feed-item',
    '.feed-list .feed-item',
    '.stream .stream-item',
    # 通用容器
    '.list .item',
    '.list li',
    '.content .item',
    '.content article',
    '.main .item',
    '.main article',
    '#content .item',
    '#content li',
    '#main .item',
    '#main article',
    # WordPress 常见
    '.post-list',
    '.hentry',
    'article.post',
    'article.article',
    # 通用 article 标签
    'article',
    # 通用 item 类
    '.item',
    '.post',
    '.entry',
    '.card',
    '.article',
    # ul>li 兜底
    'ul > li',
    'li',
]


def load_inputs():
    """加载 cleaned JSON + V5.3 verify 结果，返回 (cleaned_sources, list_failed_positions)

    list_failed_positions: 在 cleaned JSON 中的位置列表
    """
    print(f"[1/3] 加载 cleaned JSON: {CLEANED_JSON.name}")
    with open(CLEANED_JSON, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)
    print(f"     cleaned 源数: {len(cleaned)} | enabled: {sum(1 for s in cleaned if s.get('enabled'))}")

    print(f"[2/3] 加载 V5.3 原始 JSON + verify 结果（用于 idx 映射）")
    with open(V53_JSON, 'r', encoding='utf-8') as f:
        v53_sources = json.load(f)
    with open(VERIFY_JSON, 'r', encoding='utf-8') as f:
        verify = json.load(f)

    # V5.3 enabled 顺序 → 原始 JSON 位置
    v53_enabled_positions = [i for i, s in enumerate(v53_sources) if s.get('enabled')]

    # 收集 list 失败源的 sourceUrl（用 sourceUrl 作为跨 JSON 匹配的 key）
    list_failed_urls = set()
    for r in verify.get('results', []):
        vidx = r.get('idx')
        if vidx in LIST_FAILED_VERIFY_IDXS and r.get('list') == 'fail':
            if vidx < len(v53_enabled_positions):
                orig_pos = v53_enabled_positions[vidx]
                url = v53_sources[orig_pos].get('sourceUrl', '')
                if url:
                    list_failed_urls.add(url)
    print(f"     list 失败源 URL 数（去重）: {len(list_failed_urls)}")

    # 在 cleaned JSON 中找出 list 失败源的位置
    list_failed_positions = []
    for i, src in enumerate(cleaned):
        if src.get('sourceUrl') in list_failed_urls:
            list_failed_positions.append(i)
    print(f"[3/3] cleaned JSON 中 list 失败源位置数: {len(list_failed_positions)}")

    return cleaned, list_failed_positions


def is_cf_shield(soup, page_title=''):
    """检测 CloudFlare 盾"""
    title = (page_title or '').strip().lower()
    if 'just a moment' in title:
        return True
    if soup.find(id='cf-challenge-running'):
        return True
    if soup.find(class_='cf-browser-verification'):
        return True
    # 检测 CF 著名 cookie 名称提示
    if soup.find(string=re.compile(r'cloudflare', re.I)):
        return True
    return False


def is_login_required(soup):
    """检测是否需要登录"""
    # 检测登录表单
    forms = soup.find_all('form')
    for f in forms:
        action = (f.get('action') or '').lower()
        if 'login' in action or 'signin' in action or 'auth' in action:
            return True
    # 检测登录提示
    login_kws = ['请登录', '请先登录', '登录后查看', 'login required', 'sign in to continue']
    text = soup.get_text(separator=' ', strip=True)[:500].lower()
    for kw in login_kws:
        if kw.lower() in text:
            return True
    return False


def find_best_list_selector(soup):
    """在 DOM 中找最佳的列表选择器

    Returns:
        (selector, item_count, first_item_node)
    """
    best = None
    best_count = 0
    best_item = None
    for selector in LIST_SELECTOR_CANDIDATES:
        try:
            items = soup.select(selector)
        except Exception:
            continue
        if not items:
            continue
        # 过滤：每个 item 必须包含 <a href>（保证是列表项而非装饰元素）
        valid_items = [it for it in items if it.find('a', href=True)]
        # 过滤：item 内有非空文本
        valid_items = [it for it in valid_items if it.get_text(strip=True)]
        if len(valid_items) > best_count:
            best_count = len(valid_items)
            best = selector
            best_item = valid_items[0] if valid_items else None
    return best, best_count, best_item


def find_field_rule(item, field_type):
    """在列表项内找字段规则（CSS 选择器 + @attr 格式）

    Returns:
        str: 字段规则字符串（如 'a@href'），找不到返回 ''
    """
    if not item:
        return ''

    if field_type == 'title':
        # 优先级：h1-h6 > .title* > .post-title* > a
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            node = item.find(tag)
            if node and node.get_text(strip=True):
                return f'{tag}@text'
        # 找含 title 的 class
        for cls_pattern in [r'title', r'post-title', r'entry-title', r'article-title']:
            node = item.find(class_=re.compile(cls_pattern, re.I))
            if node and node.get_text(strip=True):
                # 取第一个 class 名作为选择器
                classes = node.get('class', [])
                if classes:
                    return f'.{classes[0]}@text'
                return ''
        # 兜底用 a 文本
        a = item.find('a')
        if a and a.get_text(strip=True):
            return 'a@text'
        return ''

    elif field_type == 'link':
        a = item.find('a', href=True)
        if a:
            return 'a@href'
        return ''

    elif field_type == 'image':
        img = item.find('img')
        if img:
            # 优先 data-src（懒加载），其次 src
            if img.get('data-src'):
                return 'img@data-src'
            if img.get('src'):
                return 'img@src'
            if img.get('data-original'):
                return 'img@data-original'
        return ''

    elif field_type == 'description':
        # 优先级：.desc/.summary/.excerpt > p
        for cls_pattern in [r'desc', r'summary', r'excerpt', r'description', r'intro', r'content']:
            node = item.find(class_=re.compile(cls_pattern, re.I))
            if node and node.get_text(strip=True):
                classes = node.get('class', [])
                if classes:
                    return f'.{classes[0]}@text'
                return ''
        p = item.find('p')
        if p and p.get_text(strip=True):
            return 'p@text'
        return ''

    elif field_type == 'date':
        # 优先级：time 标签 > .date/.time class
        time_node = item.find('time')
        if time_node:
            # 检查 datetime 属性
            if time_node.get('datetime'):
                return 'time@datetime'
            return 'time@text'
        for cls_pattern in [r'date', r'time', r'pub', r'created']:
            node = item.find(class_=re.compile(cls_pattern, re.I))
            if node and node.get_text(strip=True):
                classes = node.get('class', [])
                if classes:
                    return f'.{classes[0]}@text'
                return ''
        return ''

    return ''


def extract_next_page_rule(soup):
    """提取下一页规则"""
    # 优先级：a[rel="next"] > a.next > 含"下一页"文本的链接
    next_node = soup.find('a', attrs={'rel': 'next'})
    if next_node and next_node.get('href'):
        return '@CSS:a[rel="next"]@href'

    next_node = soup.find('a', class_=re.compile(r'next', re.I))
    if next_node and next_node.get('href'):
        classes = next_node.get('class', [])
        if classes:
            return f'@CSS:a.{classes[0]}@href'
        return '@CSS:a.next@href'

    # 找含"下一页"/"Next"/">"文本的链接
    for a in soup.find_all('a', href=True):
        text = (a.get_text() or '').strip()
        if text in ('下一页', '下页', 'Next', 'next', '>', '»'):
            return '@CSS:a:contains(下一页)@href'

    return ''


def extract_search_url(soup, base_url):
    """从搜索表单提取 searchUrl 模板"""
    if not base_url:
        return ''
    forms = soup.find_all('form')
    for form in forms:
        action = form.get('action') or ''
        if not action:
            continue
        # 找文本输入框
        text_input = form.find('input', attrs={'type': re.compile(r'text|search', re.I)})
        if not text_input:
            text_input = form.find('input', attrs={'type': None})
        if not text_input or not text_input.get('name'):
            continue
        input_name = text_input['name']
        # 拼接完整 action URL
        if action.startswith('//'):
            action = 'https:' + action
        elif action.startswith('/'):
            # 从 base_url 提取 origin
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                action = m.group(1) + action
        elif not action.startswith('http'):
            # 相对路径
            m = re.match(r'(https?://[^/]+)', base_url)
            if m:
                action = m.group(1) + '/' + action.lstrip('/')
        sep = '&' if '?' in action else '?'
        return f"{action}{sep}{input_name}={{key}}"
    return ''


def extract_sort_url(soup, base_url):
    """从分类导航提取 sortUrl 模板"""
    if not base_url:
        return ''
    cat_keywords = ['最新', '热门', '分类', '全部', '推荐', '排行', '今日', '昨日']
    items = []
    seen_urls = set()
    m = re.match(r'(https?://[^/]+)', base_url)
    origin = m.group(1) if m else ''

    for a in soup.find_all('a', href=True):
        text = (a.get_text() or '').strip()
        href = a['href']
        if not text or not href or href.startswith('#'):
            continue
        # 标准化 URL
        if href.startswith('//'):
            href = 'https:' + href
        elif href.startswith('/'):
            href = origin + href
        if href in seen_urls:
            continue
        for kw in cat_keywords:
            if kw in text:
                seen_urls.add(href)
                items.append(f"{kw}::{href}")
                break
    if not items and origin:
        items.append(f"最新::{origin}")
    return '\n'.join(items[:5])


def validate_rules_locally(html, rules):
    """本地校验规则：应用 ruleArticles 到 DOM，验证能否拿到 ≥3 个列表项

    Returns:
        (success, item_count, sample_titles)
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        selector = rules.get('ruleArticles', '')
        if not selector:
            return False, 0, []
        items = soup.select(selector)
        valid_items = [it for it in items if it.find('a', href=True) and it.get_text(strip=True)]
        count = len(valid_items)
        # 提取前3个标题样本
        sample_titles = []
        title_rule = rules.get('ruleTitle', '')
        for it in valid_items[:3]:
            title = extract_field_value(it, title_rule)
            if title:
                sample_titles.append(title[:30])
        return count >= 3, count, sample_titles
    except Exception as e:
        return False, 0, [f'exception:{type(e).__name__}']


def extract_field_value(item, rule):
    """根据规则从 item 提取字段值（用于本地校验）"""
    if not rule or not item:
        return ''
    # 解析规则格式：selector@attr 或 @CSS:selector@attr
    if rule.startswith('@CSS:'):
        rule = rule[5:]
    parts = rule.split('@')
    if len(parts) < 2:
        return ''
    selector = parts[0]
    attr = parts[1]
    try:
        if selector.startswith('.'):
            node = item.find(class_=selector[1:])
        elif selector.startswith('#'):
            node = item.find(id=selector[1:])
        else:
            node = item.find(selector)
        if not node:
            return ''
        if attr == 'text':
            return node.get_text(strip=True)
        elif attr == 'href':
            return node.get('href', '')
        elif attr == 'src':
            return node.get('src', '')
        elif attr == 'data-src':
            return node.get('data-src', '')
        elif attr == 'datetime':
            return node.get('datetime', '')
        return node.get(attr, '')
    except Exception:
        return ''


def fix_one_source(playwright_browser, cleaned_pos, src):
    """修复单个源

    Returns:
        dict: 修复结果
        {
            'cleaned_pos': int,
            'verify_idx': int,
            'status': 'fixed'/'disabled_cf'/'disabled_login'/'failed'/'skipped',
            'reason': str,
            'old_rules': {...},
            'new_rules': {...},
            'item_count': int,
            'sample_titles': [str],
        }
    """
    source_url = src.get('sourceUrl', '')
    result = {
        'cleaned_pos': cleaned_pos,
        'status': 'failed',
        'reason': '',
        'old_rules': {
            'ruleArticles': src.get('ruleArticles', ''),
            'ruleTitle': src.get('ruleTitle', ''),
            'ruleLink': src.get('ruleLink', ''),
        },
        'new_rules': {},
        'item_count': 0,
        'sample_titles': [],
    }

    if not source_url:
        result['reason'] = 'empty_source_url'
        return result

    # 提取 base_url（内部用，不输出）
    base_url = source_url
    # 移除 {{page}} 等模板占位符
    base_url = re.sub(r'\{\{.*?\}\}', '', base_url)

    page = None
    try:
        # 简化说明: context 已在 main() 中配置 UA/viewport/locale，new_page() 不接受这些参数
        page = playwright_browser.new_page()
        page.set_default_timeout(PAGE_TIMEOUT_MS)

        # 访问页面
        try:
            resp = page.goto(base_url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT_MS)
        except PlaywrightTimeout:
            result['reason'] = 'page_timeout'
            return result
        except Exception as e:
            result['reason'] = f'page_load_failed:{type(e).__name__}'
            return result

        # 等待动态内容
        time.sleep(WAIT_AFTER_LOAD_SEC)

        # 检查 CF 盾
        page_title = page.title() or ''
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        if is_cf_shield(soup, page_title):
            result['status'] = 'disabled_cf'
            result['reason'] = 'cf_shield_detected'
            return result

        if is_login_required(soup):
            result['status'] = 'disabled_login'
            result['reason'] = 'login_required'
            return result

        # 保存调试 HTML（用于事后分析）
        debug_html_path = DEBUG_DIR / f'src_{cleaned_pos:03d}.html'
        try:
            debug_html_path.write_text(html[:50000], encoding='utf-8', errors='ignore')
        except Exception:
            pass

        # === 多轮重试：找最佳列表选择器 ===
        best_rules = None
        best_count = 0
        best_titles = []

        for attempt in range(3):
            # 每轮尝试不同的选择器策略
            if attempt == 0:
                # 第1轮：完整候选列表
                selector, count, first_item = find_best_list_selector(soup)
            elif attempt == 1:
                # 第2轮：放宽过滤，用更通用的选择器
                selector = None
                # 找含最多 <a> 的同级元素
                parent_candidates = soup.find_all(['ul', 'ol', 'div', 'section'])
                best_parent = None
                best_parent_count = 0
                for p in parent_candidates:
                    children = p.find_all(recursive=False)
                    valid = [c for c in children if c.find('a', href=True) and c.get_text(strip=True)]
                    if len(valid) > best_parent_count:
                        best_parent_count = len(valid)
                        best_parent = p
                if best_parent and best_parent_count >= 3:
                    # 构建 CSS 选择器
                    if best_parent.name in ('ul', 'ol'):
                        selector = f'{best_parent.name} > li'
                    elif best_parent.get('class'):
                        selector = f'.{best_parent.get("class")[0]} > *'
                    else:
                        selector = None
                    if selector:
                        items = soup.select(selector)
                        count = len([i for i in items if i.find('a', href=True) and i.get_text(strip=True)])
                        first_item = items[0] if items else None
                    else:
                        count = 0
                        first_item = None
                else:
                    count = 0
                    first_item = None
            else:
                # 第3轮：直接用 article 标签或 a 标签父级
                articles = soup.find_all('article')
                if len(articles) >= 3:
                    selector = 'article'
                    count = len(articles)
                    first_item = articles[0]
                else:
                    # 最后兜底：找所有含链接+文本的 a 标签
                    all_links = soup.find_all('a', href=True)
                    valid_links = [a for a in all_links if a.get_text(strip=True) and len(a.get_text(strip=True)) > 4]
                    if len(valid_links) >= 3:
                        # 用 a 标签作为列表项
                        selector = 'a'
                        count = len(valid_links)
                        first_item = valid_links[0]
                    else:
                        count = 0
                        first_item = None

            if count < 3 or not first_item:
                continue

            # 提取字段规则
            rules = {
                'ruleArticles': selector,
                'ruleTitle': find_field_rule(first_item, 'title'),
                'ruleLink': find_field_rule(first_item, 'link') or 'a@href',
                'ruleImage': find_field_rule(first_item, 'image'),
                'ruleDescription': find_field_rule(first_item, 'description'),
                'rulePubDate': find_field_rule(first_item, 'date'),
                'ruleNextPage': extract_next_page_rule(soup),
            }

            # 本地校验
            ok, valid_count, titles = validate_rules_locally(html, rules)
            if ok and valid_count > best_count:
                best_rules = rules
                best_count = valid_count
                best_titles = titles

        if best_rules and best_count >= 3:
            result['status'] = 'fixed'
            result['reason'] = f'fixed_with_{best_count}_items'
            result['new_rules'] = best_rules
            result['item_count'] = best_count
            result['sample_titles'] = best_titles
        else:
            result['status'] = 'failed'
            result['reason'] = f'no_valid_selector_found_best_count={best_count}'
            result['item_count'] = best_count

    except Exception as e:
        result['reason'] = f'exception:{type(e).__name__}:{str(e)[:80]}'
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass

    return result


def main():
    print("=" * 70)
    print("v5_4 深度修复 31 个 list 失败源（Playwright + BS4）")
    print("=" * 70)

    cleaned_sources, list_failed_positions = load_inputs()

    print(f"\n--- 开始 Playwright 深度修复 ---")
    print(f"待修复源数: {len(list_failed_positions)}")

    fixed_sources = []
    fix_results = []
    status_counter = Counter()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={'width': 375, 'height': 667},
            locale='zh-CN',
            ignore_https_errors=True,
        )

        total = len(list_failed_positions)
        for i, cleaned_pos in enumerate(list_failed_positions):
            src = cleaned_sources[cleaned_pos]
            print(f"\n[{i+1}/{total}] cleaned_pos={cleaned_pos} 修复中...", flush=True)

            result = fix_one_source(context, cleaned_pos, src)
            fix_results.append(result)
            status_counter[result['status']] += 1

            print(f"  状态: {result['status']} | 原因: {result['reason'][:60]}")
            if result['status'] == 'fixed':
                print(f"  列表项数: {result['item_count']} | 标题样本数: {len(result['sample_titles'])}")

            # 应用修复到源对象
            if result['status'] == 'fixed':
                fixed_src = dict(src)  # 浅拷贝
                new_rules = result['new_rules']
                for field, value in new_rules.items():
                    if value:  # 只更新非空字段
                        fixed_src[field] = value
                fixed_src['enabled'] = True
                # 记录修复元数据到 sourceComment（技术信息，无业务数据）
                old_comment = fixed_src.get('sourceComment', '')
                fix_tag = f"[v5_4_fixed:{result['item_count']}items]"
                if fix_tag not in old_comment:
                    fixed_src['sourceComment'] = f"{old_comment} {fix_tag}".strip()
                fixed_sources.append(fixed_src)
            elif result['status'] in ('disabled_cf', 'disabled_login', 'failed'):
                # 标记 enabled=false（保留源对象以便后续审计）
                disabled_src = dict(src)
                disabled_src['enabled'] = False
                old_comment = disabled_src.get('sourceComment', '')
                reason_tag = f"[v5_4_disabled:{result['status']}]"
                if reason_tag not in old_comment:
                    disabled_src['sourceComment'] = f"{old_comment} {reason_tag}".strip()
                fixed_sources.append(disabled_src)
            else:
                # skipped: 保留原状
                fixed_sources.append(dict(src))

            # 实时保存中间结果（防中断）
            if (i + 1) % 5 == 0 or i == total - 1:
                with open(OUT_SOURCES, 'w', encoding='utf-8') as f:
                    json.dump(fixed_sources, f, ensure_ascii=False, indent=2)
                # 同时保存进度报告
                progress_report = {
                    'total_target': total,
                    'processed': len(fix_results),
                    'status_counts': dict(status_counter),
                    'results': fix_results,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                }
                with open(OUT_REPORT, 'w', encoding='utf-8') as f:
                    json.dump(progress_report, f, ensure_ascii=False, indent=2)

        browser.close()

    # 最终报告
    final_report = {
        'total_target': len(list_failed_positions),
        'total_processed': len(fix_results),
        'status_counts': dict(status_counter),
        'results': fix_results,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("✅ 深度修复完成")
    print("=" * 70)
    print(f"  目标源数: {len(list_failed_positions)}")
    print(f"  状态分布: {dict(status_counter)}")
    print(f"  修复源 JSON: {OUT_SOURCES}")
    print(f"  修复报告: {OUT_REPORT}")


if __name__ == '__main__':
    main()
