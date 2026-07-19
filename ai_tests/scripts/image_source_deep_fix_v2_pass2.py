"""
二次深度优化 - 针对22个部分修复(无sortUrl)的源 + 2个失败源
策略:
1. 滚动加载更多内容 (有些分类是延迟加载的)
2. 尝试 /sitemap.xml, /robots.txt, /categories, /tags, /albums, /forum
3. 检测图床/相册类型, 提取相册/标签作为分类
4. 检测BBS类型, 提取板块
"""
import json
import re
import os
import sys
import time
import random
import traceback
from pathlib import Path
from urllib.parse import urlparse, urljoin

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
os.environ.setdefault('PYTHONUNBUFFERED', '1')

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def log(msg):
    print(msg, flush=True)


ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = ROOT / "output" / "rss" / "optimized_v2_lite_final_v3.json"
DEEP_FIX_JSON = ROOT / "output" / "rss" / "image_source_deep_fix_v2.json"
OUTPUT_JSON = ROOT / "output" / "rss" / "image_source_deep_fix_v2.json"  # 直接更新原文件
TMP_JSON = ROOT / "output" / "rss" / "image_source_deep_fix_v2.tmp2.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
PW_TIMEOUT = 18000

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[^\s]*)",
    re.IGNORECASE)


def sanitize(msg):
    if not isinstance(msg, str):
        msg = str(msg)
    msg = URL_RE.sub("[URL]", msg)
    msg = DOMAIN_RE.sub("[DOMAIN]", msg)
    return msg


STEALTH_JS = r"""
() => {
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
    window.chrome = window.chrome || {runtime: {}};
    return true;
}
"""

CLOSE_MODAL_JS = r"""
() => {
    document.querySelectorAll('.modal,.popup,.close,.dialog,.mask,.overlay').forEach(e => {
        try { e.click(); } catch(_){}
        try { e.style.display = 'none'; } catch(_){}
    });
    return true;
}
"""

# 深度提取 sortUrl 的 JS - 滚动后再次扫描
DEEP_SORT_JS = r"""
() => {
    const result = { sortUrl: '', notes: [] };
    const cats = [];
    const seen = new Set();

    // 1. 重新扫描所有 nav a 链接 (扩大候选范围)
    const allLinks = document.querySelectorAll('a[href]');
    for (const a of allLinks) {
        const href = a.getAttribute('href') || '';
        const text = (a.textContent || '').trim();
        if (!href || !text) continue;
        if (href.startsWith('javascript:') || href.startsWith('#') || href.startsWith('tel:') || href.startsWith('mailto:')) continue;
        if (text.length > 30 || text.length < 1) continue;
        const lower = text.toLowerCase();
        if (['首页','主页','home','登录','注册','login','register','signin','signup',
             '关于','about','联系','contact','搜索','search','更多','more',
             'tags','tag','标签','sitemap','rss','atom','feedback','反馈',
             '返回','back','顶部','top','下载','download','app','客户端',
             'prev','next','上一页','下一页','previous','»','«','>','<',
             'gb','big5','english','繁體','简体','分享','share','评论','comment',
             '点赞','like','收藏','favorite','关注','follow','会员','vip',
             '公告','notice','新闻','news','热门','hot','最新','new','推荐','rec'].includes(lower)) continue;
        if (/^\d+$/.test(text)) continue;
        let relPath = href;
        if (href.startsWith('http')) {
            try {
                const u = new URL(href);
                if (u.origin !== location.origin) continue;
                relPath = u.pathname + u.search;
            } catch(e) { continue; }
        }
        // 只保留路径型 (排除纯锚点/纯参数)
        if (!relPath.startsWith('/') && !relPath.startsWith('./')) continue;
        const key = text + '|' + relPath;
        if (seen.has(key)) continue;
        seen.add(key);
        cats.push(text + '::' + relPath);
        if (cats.length >= 30) break;
    }

    result.sortUrl = cats.join('\n');
    if (cats.length > 0) result.notes.push('deep_cats_count=' + cats.length);

    // 2. 检测图床/相册类型 - 提取相册链接
    if (cats.length === 0) {
        const albumLinks = document.querySelectorAll('a[href*="album"], a[href*="gallery"], a[href*="tags/"], a[href*="tag/"], a[href*="category/"], a[href*="cat/"], a[href*="sort/"], a[href*="board/"], a[href*="forum/"]');
        const seen2 = new Set();
        for (const a of albumLinks) {
            const href = a.getAttribute('href') || '';
            const text = (a.textContent || '').trim();
            if (!href || !text || text.length > 30) continue;
            let relPath = href;
            if (href.startsWith('http')) {
                try {
                    const u = new URL(href);
                    if (u.origin !== location.origin) continue;
                    relPath = u.pathname + u.search;
                } catch(e) { continue; }
            }
            const key = text + '|' + relPath;
            if (seen2.has(key)) continue;
            seen2.add(key);
            cats.push(text + '::' + relPath);
            if (cats.length >= 30) break;
        }
        if (cats.length > 0) {
            result.sortUrl = cats.join('\n');
            result.notes.push('album_cats_count=' + cats.length);
        }
    }

    return result;
}
"""


def load_input():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        if 'sources' in data:
            sources = data['sources']
        else:
            sources = data
    else:
        sources = data
    return sources


def load_deep_fix():
    with open(DEEP_FIX_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def pick_targets(deep_data):
    """挑选需要二次分析的源:无sortUrl的 或 失败的"""
    targets = []
    for r in deep_data.get('records', []):
        # 无sortUrl但已 accessible 或 失败
        if not r.get('sort_url_filled') or r.get('error') in ('interrupted', 'goto_err:goto_timeout'):
            targets.append(r)
    return targets


def try_paths_for_categories(page, host):
    """尝试常见分类路径: /sitemap.xml, /categories, /tags, /albums"""
    found = []
    paths_to_try = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap-news.xml',
        '/categories',
        '/category',
        '/tags',
        '/tag',
        '/albums',
        '/album',
        '/forum',
        '/board',
        '/sort',
        '/cat',
        '/sortlist.html',
        '/sort/',
        '/list',
        '/archives',
    ]
    for path in paths_to_try:
        if found:
            break
        try:
            url = host + path
            r = page.request.get(url, timeout=6000, max_redirects=3)
            if not r.ok:
                continue
            text = r.text() or ''
            ct = (r.headers.get('content-type', '') or '').lower()
            # XML sitemap
            if 'xml' in ct or text.lstrip().startswith('<?xml') or '<urlset' in text or '<sitemapindex' in text:
                urls = re.findall(r'<loc>([^<]+)</loc>', text)
                seen = set()
                host_norm = host.rstrip('/').lower()
                for u in urls[:500]:
                    try:
                        pu = urlparse(u)
                        if pu.origin.rstrip('/').lower() != host_norm:
                            continue
                        parts = [p for p in pu.path.split('/') if p]
                        if parts:
                            cat = parts[0]
                            if cat and cat not in seen and len(cat) < 30:
                                seen.add(cat)
                                found.append((cat, '/' + cat))
                                if len(found) >= 15:
                                    break
                    except Exception:
                        continue
                if found:
                    return found, 'sitemap'
            # HTML page - 解析其中的链接
            elif 'html' in ct or '<html' in text.lower()[:500]:
                # 用 page.goto 加载这个 HTML 页面, 然后用 DEEP_SORT_JS 提取
                try:
                    page.goto(url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
                    try:
                        page.evaluate(STEALTH_JS)
                    except Exception:
                        pass
                    try:
                        page.evaluate(CLOSE_MODAL_JS)
                    except Exception:
                        pass
                    try:
                        page.wait_for_load_state('networkidle', timeout=3000)
                    except Exception:
                        pass
                    r2 = page.evaluate(DEEP_SORT_JS)
                    if r2.get('sortUrl'):
                        # 解析 sortUrl 文本
                        for line in r2['sortUrl'].split('\n'):
                            if '::' in line:
                                name, path = line.split('::', 1)
                                found.append((name, path))
                                if len(found) >= 15:
                                    break
                        if found:
                            return found, 'path_' + path
                except Exception:
                    pass
        except Exception:
            continue
    return found, 'none'


def deep_extract_one(page, source_url, prev_record):
    """对单个源进行二次深度分析"""
    accessible = False
    error = None

    try:
        page.goto(source_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        accessible = True
    except PWTimeout:
        error = 'goto_timeout'
    except Exception as e:
        msg = sanitize(str(e)).lower()
        if 'cloudflare' in msg or '403' in msg or '503' in msg:
            error = 'cf_blocked'
        else:
            error = 'goto_err:' + msg[:60]

    if not accessible:
        return None, error

    # 注入 stealth
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass
    # 关闭弹框
    try:
        page.evaluate(CLOSE_MODAL_JS)
    except Exception:
        pass
    # 等待
    try:
        page.wait_for_load_state('networkidle', timeout=3000)
    except Exception:
        pass

    # 滚动加载更多内容 (3次滚动到底)
    try:
        for _ in range(3):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(0.8)
        # 再关弹框
        page.evaluate(CLOSE_MODAL_JS)
    except Exception:
        pass

    # 提取 sortUrl
    new_sort_url = ''
    new_notes = []
    try:
        r = page.evaluate(DEEP_SORT_JS)
        new_sort_url = r.get('sortUrl', '') or ''
        new_notes.extend(r.get('notes', []))
    except Exception as e:
        new_notes.append('deep_eval_err:' + sanitize(str(e))[:60])

    # 如果还没找到, 尝试 /sitemap.xml 等路径
    if not new_sort_url:
        try:
            host = source_url.rstrip('/')
            # 解析 host
            pu = urlparse(source_url)
            host = pu.scheme + '://' + pu.netloc
            cats, source = try_paths_for_categories(page, host)
            if cats:
                new_sort_url = '\n'.join(f'{name}::{path}' for name, path in cats)
                new_notes.append(f'cats_from_{source}={len(cats)}')
        except Exception as e:
            new_notes.append('paths_err:' + sanitize(str(e))[:60])

    return {
        'sort_url_filled': new_sort_url,
        'notes': new_notes
    }, None


def verify_sort_url(page, host, sort_url_str, rule_articles=None):
    if not sort_url_str:
        return False, 0
    first_line = sort_url_str.split('\n')[0]
    if '::' not in first_line:
        return False, 0
    _, path = first_line.split('::', 1)
    path = path.strip()
    if not path:
        return False, 0
    full_url = urljoin(host + '/', path.lstrip('/'))
    try:
        page.goto(full_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        try:
            page.evaluate(STEALTH_JS)
        except Exception:
            pass
        try:
            page.evaluate(CLOSE_MODAL_JS)
        except Exception:
            pass
        try:
            page.wait_for_load_state('networkidle', timeout=3000)
        except Exception:
            pass
        # 滚动加载
        for _ in range(2):
            try:
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(0.5)
            except Exception:
                pass
        count = page.evaluate('() => document.querySelectorAll("img").length')
        list_count = 0
        if rule_articles:
            try:
                ra = json.loads(rule_articles)
                sel = ra.get('articleList', '')
                if sel:
                    css_sel = sel.split('>')[0].strip()
                    if css_sel:
                        list_count = page.evaluate(
                            '(s) => document.querySelectorAll(s).length', css_sel)
            except Exception:
                pass
        final_count = max(int(count or 0), int(list_count or 0))
        return True, final_count
    except Exception:
        return False, 0


def run():
    log('[LOAD] reading input...')
    sources = load_input()
    deep_data = load_deep_fix()
    log(f'[LOAD] deep_fix records: {len(deep_data["records"])}')

    targets = pick_targets(deep_data)
    log(f'[TARGET] need second-pass: {len(targets)}')
    target_idx = {r['idx'] for r in targets}

    # 用 source 列表找到原始 sourceUrl
    src_map = {}
    for i, src in enumerate(sources):
        if i in target_idx:
            src_map[i] = src

    records = deep_data['records']

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage'
        ])
        context = browser.new_context(
            user_agent=UA,
            viewport={'width': 1366, 'height': 900},
            locale='zh-CN',
            ignore_https_errors=True,
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
            }
        )
        page = context.new_page()
        page.set_default_timeout(PW_TIMEOUT)

        try:
            for n, r in enumerate(targets):
                idx = r['idx']
                src = src_map.get(idx)
                if not src:
                    log(f'[{n+1}/{len(targets)}] idx={idx} no source, skip')
                    continue
                source_url = src.get('sourceUrl', '') or ''
                if not source_url:
                    continue
                log(f'[{n+1}/{len(targets)}] idx={idx} deep analyzing...')

                try:
                    result, err = deep_extract_one(page, source_url, r)
                    if result and result.get('sort_url_filled'):
                        # 验证
                        verify_ok = False
                        list_count = 0
                        try:
                            pu = urlparse(source_url)
                            host = pu.scheme + '://' + pu.netloc
                            verify_ok, list_count = verify_sort_url(
                                page, host, result['sort_url_filled'],
                                r.get('rule_articles_filled'))
                        except Exception as e:
                            result['notes'].append('verify_err:' + sanitize(str(e))[:60])

                        # 更新原记录
                        r['sort_url_filled'] = result['sort_url_filled']
                        r['verify_ok'] = verify_ok
                        r['list_items_count'] = list_count
                        r['notes'].extend(result['notes'])
                        r['notes'].append(f'deep_verify_ok={verify_ok},list_count={list_count}')
                        r['error'] = r.get('error', '') or ''
                        log(f'   -> sortUrl_lines={len(result["sort_url_filled"].split(chr(10)))} verify={verify_ok} count={list_count}')
                    elif err:
                        log(f'   -> err={err}')
                        # 不更新原记录(保留之前结果)
                    else:
                        log(f'   -> no sortUrl found')
                except KeyboardInterrupt:
                    log('\n[INTERRUPT] user interrupted, saving...')
                    raise
                except Exception as e:
                    log(f'   -> exception: {sanitize(str(e))[:80]}')

                # 增量保存
                if (n + 1) % 3 == 0:
                    save(records, deep_data)
                    log(f'[SAVE] progress: {n+1}/{len(targets)}')

                time.sleep(0.3 + random.random() * 0.3)

        except KeyboardInterrupt:
            log('\n[INTERRUPT] saving partial...')
        except Exception as e:
            log(f'[FATAL] {sanitize(str(e))}')
            traceback.print_exc()
        finally:
            save(records, deep_data)
            log('[DONE] saved')
            try:
                context.close()
                browser.close()
            except Exception:
                pass

    # 重新统计
    fully_fixed = 0
    partial_fixed = 0
    still_failed = 0
    tmpl_dist = {}
    for r in records:
        s = bool(r.get('sort_url_filled'))
        se = bool(r.get('search_url_filled'))
        ra = bool(r.get('rule_articles_filled'))
        v = bool(r.get('verify_ok'))
        if (s and v) or (s and se and ra):
            fully_fixed += 1
        elif s or se or ra:
            partial_fixed += 1
        else:
            still_failed += 1
        tt = r.get('template_type', 'unknown')
        tmpl_dist[tt] = tmpl_dist.get(tt, 0) + 1

    log('\n========== 最终修复统计 ==========')
    log(f'总数: {len(records)}')
    log(f'完全修复: {fully_fixed}')
    log(f'部分修复: {partial_fixed}')
    log(f'仍然失败: {still_failed}')
    log(f'模板分布: {tmpl_dist}')
    log(f'输出文件: {OUTPUT_JSON}')
    log('==================================')


def save(records, deep_data):
    out = {
        'total': deep_data['total'],
        'fixed': sum(1 for r in records if r.get('sort_url_filled') and r.get('verify_ok')),
        'partial_fixed': sum(1 for r in records if not (r.get('sort_url_filled') and r.get('verify_ok')) and
                              (r.get('sort_url_filled') or r.get('search_url_filled') or r.get('rule_articles_filled'))),
        'still_failed': sum(1 for r in records if not r.get('sort_url_filled') and
                            not r.get('search_url_filled') and not r.get('rule_articles_filled')),
        'records': records
    }
    with open(TMP_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    try:
        with open(TMP_JSON, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            f.write(data)
    except Exception as e:
        log(f'[SAVE_ERR] {sanitize(str(e))}')


if __name__ == '__main__':
    run()
