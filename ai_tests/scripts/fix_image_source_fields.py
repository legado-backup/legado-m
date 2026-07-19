"""
图片源(type=1)字段补全脚本
- 读取 optimized_v2_lite_final.json，筛出 type=1 且 sortUrl 为空的源
- 用 Playwright 访问首页，提取 sortUrl/searchUrl/ruleArticles/ruleImage/ruleNextPage
- 输出安全：源[idx]替代真实名称，URL用[URL]替代，异常脱敏
- 增量保存：每10个源保存一次
"""
import json
import re
import os
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse, urljoin

# 强制无缓冲输出
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
os.environ.setdefault('PYTHONUNBUFFERED', '1')

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def log(msg):
    """带 flush 的日志"""
    print(msg, flush=True)

# ===== 配置 =====
ROOT = Path(r"f:\myself\github\WeAgentChat\temp\legado")
INPUT_JSON = ROOT / "output" / "rss" / "optimized_v2_lite_final.json"
DIAG_JSON = ROOT / "output" / "rss" / "db_field_diagnose.json"
OUTPUT_JSON = ROOT / "output" / "rss" / "image_source_field_fix.json"
TMP_JSON = ROOT / "output" / "rss" / "image_source_field_fix.tmp.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PW_TIMEOUT = 12000
SAVE_EVERY = 10

# ===== 脱敏 =====
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[^\s]*)", re.IGNORECASE)


def sanitize(msg: str) -> str:
    if not isinstance(msg, str):
        msg = str(msg)
    msg = URL_RE.sub("[URL]", msg)
    msg = DOMAIN_RE.sub("[DOMAIN]", msg)
    return msg


# ===== JS 提取脚本 =====
# 注入到页面，提取 sortUrl/searchUrl/ruleArticles/ruleImage/ruleNextPage
EXTRACT_JS = r"""
() => {
    const result = {
        sortUrl: '',
        searchUrl: '',
        ruleArticles: '',
        ruleImage: '',
        ruleNextPage: '',
        host: location.origin,
        pathname: location.pathname,
        notes: []
    };

    // 1. 提取 sortUrl: 从导航/分类列表 a 标签提取
    //    归类为 "分类名::相对路径" 格式，多分类用 \n 分隔
    try {
        const cats = [];
        const seen = new Set();
        // 常见分类容器选择器
        const navSelectors = [
            'nav a', '.nav a', '.navbar a', '.menu a', '.navigation a',
            '.header a', '.category a', '.categories a', '.cat-list a',
            '.sidebar a', '.tags a', '.filter a', '.nav-menu a',
            'ul.menu a', 'ul.nav a', '.main-nav a'
        ];
        for (const sel of navSelectors) {
            const links = document.querySelectorAll(sel);
            if (links.length === 0) continue;
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                const text = (a.textContent || '').trim();
                if (!href || !text) continue;
                if (href.startsWith('javascript:') || href.startsWith('#')) continue;
                if (text.length > 20 || text.length < 1) continue;
                // 排除主页/登录/注册等
                const lower = text.toLowerCase();
                if (['首页', '主页', 'home', '登录', '注册', 'login', 'register',
                     '关于', 'about', '联系', 'contact', '搜索', 'search'].includes(lower)) continue;
                const key = text + '|' + href;
                if (seen.has(key)) continue;
                seen.add(key);
                // 只保留相对路径或同源路径
                let relPath = href;
                if (href.startsWith('http')) {
                    try {
                        const u = new URL(href);
                        if (u.origin !== location.origin) continue;
                        relPath = u.pathname + u.search;
                    } catch (e) { continue; }
                }
                cats.push(text + '::' + relPath);
                if (cats.length >= 30) break;
            }
            if (cats.length >= 10) break;
        }
        result.sortUrl = cats.join('\n');
        if (cats.length > 0) result.notes.push('cats_count=' + cats.length);
    } catch (e) {
        result.notes.push('sortUrl_err:' + e.message);
    }

    // 2. 提取 searchUrl: 从搜索表单提取
    try {
        const forms = document.querySelectorAll('form');
        let found = false;
        for (const form of forms) {
            const action = form.getAttribute('action') || location.pathname;
            const method = (form.getAttribute('method') || 'get').toLowerCase();
            // 找 keyword 输入框
            const inputs = form.querySelectorAll('input');
            let keywordName = null;
            for (const inp of inputs) {
                const n = (inp.getAttribute('name') || '').toLowerCase();
                const t = (inp.getAttribute('type') || '').toLowerCase();
                const ph = (inp.getAttribute('placeholder') || '').toLowerCase();
                if (['search', 'keyword', 'q', 'wd', 'key', 's', 'query', 'kw', 'name'].includes(n) ||
                    ph.includes('搜索') || ph.includes('search') || ph.includes('关键字') ||
                    ph.includes('关键词') || t === 'search') {
                    keywordName = inp.getAttribute('name');
                    break;
                }
            }
            if (!keywordName) continue;
            let fullAction = action;
            if (action.startsWith('http')) {
                try {
                    const u = new URL(action);
                    fullAction = u.pathname + u.search;
                } catch (e) { fullAction = action; }
            } else if (action.startsWith('/')) {
                fullAction = action;
            } else {
                fullAction = location.pathname.replace(/[^/]*$/, '') + action;
            }
            if (method === 'get') {
                result.searchUrl = fullAction + (fullAction.includes('?') ? '&' : '?') +
                    keywordName + '={{key}}&page={{page}}';
            } else {
                result.searchUrl = fullAction + ',{"method\":\"POST\",\"body\":\"' +
                    keywordName + '={{key}}&page={{page}}\"}';
            }
            found = true;
            break;
        }
        // 兜底：构造通用搜索 URL
        if (!found) {
            // 探测常见搜索路径（不发起请求，仅推断）
            const guessPaths = ['/search', '/search.php', '/index.php', '/s'];
            result.searchUrl = '/search?q={{key}}&page={{page}}';
            result.notes.push('searchUrl_fallback_guess');
        }
    } catch (e) {
        result.notes.push('searchUrl_err:' + e.message);
    }

    // 3. 提取 ruleArticles: 图片列表 DOM 选择器
    try {
        const candidates = [
            '.gallery img', 'ul.photos img', '.pic-list img', '.image-list img',
            'article img', '.post img', '.list img', '.grid img',
            '.thumbnail img', '.thumb img', '.card img', '.item img',
            '.photo img', '.image img', '.picture img', '.img-list img',
            '.waterfall img', '.masonry img', '.posts img', '.content-list img',
            '.gallery-item img', '.photo-item img', '.image-item img',
            '.list-item img', '.card-item img', '.post-item img',
            'ul.list img', 'ul.gallery img', '.row img', '.container img'
        ];
        let best = '';
        let bestCount = 0;
        for (const sel of candidates) {
            try {
                const els = document.querySelectorAll(sel);
                if (els.length > bestCount) {
                    bestCount = els.length;
                    // 提取父容器作为列表选择器
                    const parent = els[0]?.parentElement;
                    if (parent) {
                        let pSel = '';
                        if (parent.className) {
                            const cls = parent.className.split(/\s+/)[0];
                            if (cls) pSel = '.' + cls;
                        }
                        if (!pSel && parent.tagName) {
                            pSel = parent.tagName.toLowerCase();
                        }
                        // 再上一层作为 articleList
                        const grandparent = parent.parentElement;
                        let listSel = '';
                        if (grandparent) {
                            if (grandparent.className) {
                                const gcls = grandparent.className.split(/\s+/)[0];
                                if (gcls) listSel = '.' + gcls;
                            }
                            if (!listSel && grandparent.id) {
                                listSel = '#' + grandparent.id;
                            }
                            if (!listSel) listSel = grandparent.tagName.toLowerCase();
                        }
                        // 用 img 父元素作为 articleList 项
                        const imgSel = (pSel || parent.tagName.toLowerCase());
                        // 尝试父容器直接定位
                        const parentEls = listSel ? document.querySelectorAll(listSel + ' > *') : [];
                        if (parentEls.length >= 3) {
                            best = JSON.stringify({
                                articleList: listSel + ' > ' + imgSel,
                                image: 'img@src',
                                title: 'a@text||img@alt',
                                url: 'a@href'
                            });
                        } else {
                            // 直接用 img 选择器作为 articleList
                            best = JSON.stringify({
                                articleList: sel.replace(' img', ''),
                                image: 'img@src',
                                title: 'a@text||img@alt',
                                url: 'a@href'
                            });
                        }
                    }
                }
            } catch (e) {}
        }
        result.ruleArticles = best;
        if (bestCount > 0) result.notes.push('imgs_count=' + bestCount);
    } catch (e) {
        result.notes.push('ruleArticles_err:' + e.message);
    }

    // 4. 提取 ruleImage: 单图元素选择器（基于最大图片所在容器）
    try {
        const imgSelectors = [
            '.content img', 'article img', '.photo-item img', '.article img',
            '.post-content img', '.entry-content img', '.main img',
            '.viewer img', '.image-viewer img', '.photo-content img',
            '.detail img', '.picture img', '.single img'
        ];
        let best = '';
        for (const sel of imgSelectors) {
            const els = document.querySelectorAll(sel);
            if (els.length > 0) {
                best = sel;
                break;
            }
        }
        // 兜底：取最大图片的父容器 class
        if (!best) {
            const imgs = document.querySelectorAll('img');
            let maxArea = 0;
            let maxImg = null;
            for (const img of imgs) {
                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;
                const area = w * h;
                if (area > maxArea) {
                    maxArea = area;
                    maxImg = img;
                }
            }
            if (maxImg) {
                let p = maxImg.parentElement;
                while (p && p !== document.body) {
                    if (p.className) {
                        const cls = p.className.split(/\s+/)[0];
                        if (cls && cls.length < 30) {
                            best = '.' + cls + ' img';
                            break;
                        }
                    }
                    p = p.parentElement;
                }
            }
        }
        result.ruleImage = best;
    } catch (e) {
        result.notes.push('ruleImage_err:' + e.message);
    }

    // 5. 提取 ruleNextPage: 下一页链接选择器
    try {
        const nextCandidates = [
            'a.next', 'a.next-page', 'a[rel=next]', 'a[rel="next"]',
            '.pagination a:last-child', '.page a:last-child', '.pager a:last-child',
            '.page-next a', '.next a', 'a.page-next', 'a[title=下一页]',
            'a[title="下一页"]', 'a:has-text("下一页")'
        ];
        let best = '';
        // 先按 class/title 找
        const aTags = document.querySelectorAll('a');
        for (const a of aTags) {
            const cls = (a.getAttribute('class') || '').toLowerCase();
            const rel = (a.getAttribute('rel') || '').toLowerCase();
            const txt = (a.textContent || '').trim();
            const title = (a.getAttribute('title') || '').trim();
            if (cls.includes('next') || rel === 'next' ||
                txt === '下一页' || txt === 'Next' || txt === 'next' || txt === '»' || txt === '>' ||
                title === '下一页' || title === 'Next') {
                // 反推选择器
                if (a.className) {
                    const firstCls = a.className.split(/\s+/)[0];
                    if (firstCls) { best = '.' + firstCls + '@href'; break; }
                }
                if (a.id) { best = '#' + a.id + '@href'; break; }
                if (rel === 'next') { best = 'a[rel=next]@href'; break; }
            }
        }
        // 兜底
        if (!best) {
            // 分页容器最后一个 a
            const pagSels = ['.pagination', '.page', '.pager', '.page-list', '.page-nav'];
            for (const ps of pagSels) {
                const pag = document.querySelector(ps);
                if (pag) {
                    const links = pag.querySelectorAll('a');
                    if (links.length >= 2) {
                        best = ps + ' a:last-child@href';
                        break;
                    }
                }
            }
        }
        result.ruleNextPage = best;
    } catch (e) {
        result.notes.push('ruleNextPage_err:' + e.message);
    }

    return result;
}
"""

CLOSE_MODAL_JS = r"""
() => {
    // 关闭弹框
    document.querySelectorAll('.modal, .popup, .close, .modal-close, .popup-close, [data-dismiss], .mask, .overlay').forEach(e => {
        try { e.click(); } catch(err) {}
        try { e.style.display = 'none'; } catch(err2) {}
    });
    return true;
}
"""


def load_input():
    """读取输入JSON,返回源列表(每条含type字段)"""
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 数据可能是 list 或 dict
    if isinstance(data, dict):
        # 可能有 source field
        if 'sources' in data:
            sources = data['sources']
        else:
            sources = data
    else:
        sources = data
    return sources


def pick_image_sources(sources):
    """筛出 type=1 且 sortUrl 为空的源,返回 [(idx, source), ...]"""
    result = []
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        t = src.get('type', 0)
        # 兼容字符串
        try:
            t = int(t)
        except (ValueError, TypeError):
            t = 0
        if t != 1:
            continue
        sort_url = src.get('sortUrl', '') or ''
        if sort_url.strip():
            continue
        result.append((i, src))
    return result


def try_wayback(page, source_url):
    """对 CF 防护源尝试 Wayback Machine"""
    try:
        wayback = 'https://web.archive.org/web/2024/' + source_url
        page.goto(wayback, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        return True
    except Exception:
        return False


def extract_one(page, source_url):
    """对单个源用 Playwright 提取字段,返回 dict 或 None"""
    accessible = False
    error = None
    try:
        page.goto(source_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        accessible = True
    except PWTimeout:
        # 超时,尝试 Wayback
        if try_wayback(page, source_url):
            accessible = True
            error = 'orig_timeout_wayback_ok'
        else:
            error = 'goto_timeout'
    except Exception as e:
        # 检测是否 CF
        msg = sanitize(str(e))
        if 'cloudflare' in msg.lower() or 'cf' in msg.lower() or '403' in msg or '503' in msg:
            if try_wayback(page, source_url):
                accessible = True
                error = 'cf_blocked_wayback_ok'
            else:
                error = 'cf_blocked'
        else:
            error = 'goto_err:' + msg[:80]

    if not accessible:
        return {'accessible': False, 'error': error}

    # 关闭弹框
    try:
        page.evaluate(CLOSE_MODAL_JS)
    except Exception:
        pass

    # 等待 DOM 稳定
    try:
        page.wait_for_load_state('networkidle', timeout=3000)
    except Exception:
        pass

    # 执行提取
    try:
        result = page.evaluate(EXTRACT_JS)
        result['accessible'] = True
        result['error'] = error or ''
        return result
    except Exception as e:
        return {'accessible': True, 'error': 'eval_err:' + sanitize(str(e))[:80]}


def verify_sort_url(page, host, sort_url_str):
    """验证 sortUrl 拼接后的完整URL能否访问,列表项>0"""
    if not sort_url_str:
        return False, 0
    # 取第一个分类
    first_line = sort_url_str.split('\n')[0]
    if '::' not in first_line:
        return False, 0
    _, path = first_line.split('::', 1)
    full_url = urljoin(host + '/', path.lstrip('/'))
    try:
        page.goto(full_url, timeout=PW_TIMEOUT, wait_until='domcontentloaded')
        # 计数 img 标签
        count = page.evaluate('() => document.querySelectorAll("img").length')
        return True, int(count or 0)
    except Exception as e:
        return False, 0


def save_json(records, total, fixed, failed):
    """保存结果(增量+最终)"""
    out = {
        'total': total,
        'fixed': fixed,
        'still_failed': failed,
        'records': records
    }
    with open(TMP_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # 最终保存
    if os.path.exists(TMP_JSON):
        with open(TMP_JSON, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            f.write(data)


def run():
    print('[LOAD] reading input json...')
    sources = load_input()
    print(f'[LOAD] total sources: {len(sources)}')
    image_srcs = pick_image_sources(sources)
    print(f'[FILTER] type=1 & sortUrl empty: {len(image_srcs)}')

    # 已处理的 idx 集合(用于断点续传)
    done_idx = set()
    records = []
    if TMP_JSON.exists():
        try:
            with open(TMP_JSON, 'r', encoding='utf-8') as f:
                prev = json.load(f)
            records = prev.get('records', [])
            done_idx = {r.get('idx') for r in records}
            print(f'[RESUME] already done: {len(done_idx)}')
        except Exception as e:
            print(f'[RESUME] failed: {sanitize(str(e))}')

    fixed_count = sum(1 for r in records if r.get('sort_url_filled'))
    failed_count = sum(1 for r in records if not r.get('sort_url_filled') and
                       not r.get('search_url_filled') and not r.get('rule_articles_filled'))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=UA,
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
            ignore_https_errors=True
        )
        # 启用 JS
        page = context.new_page()
        page.set_default_timeout(PW_TIMEOUT)

        try:
            for n, (idx, src) in enumerate(image_srcs):
                if idx in done_idx:
                    continue
                # 输出安全:不打印 sourceUrl
                print(f'\n[{n+1}/{len(image_srcs)}] idx={idx} processing...')

                source_url = src.get('sourceUrl', '') or ''
                record = {
                    'idx': idx,
                    'source_url_accessible': False,
                    'sort_url_filled': '',
                    'search_url_filled': '',
                    'rule_articles_filled': '',
                    'rule_image_filled': '',
                    'rule_next_page_filled': '',
                    'method': 'playwright_dom',
                    'error': '',
                    'notes': []
                }

                if not source_url:
                    record['error'] = 'no_source_url'
                    records.append(record)
                    failed_count += 1
                    continue

                try:
                    r = extract_one(page, source_url)
                    record['source_url_accessible'] = bool(r.get('accessible'))

                    if r.get('accessible'):
                        sort_url = r.get('sortUrl', '') or ''
                        search_url = r.get('searchUrl', '') or ''
                        rule_articles = r.get('ruleArticles', '') or ''
                        rule_image = r.get('ruleImage', '') or ''
                        rule_next = r.get('ruleNextPage', '') or ''

                        # 验证 sortUrl
                        verify_ok = False
                        list_count = 0
                        if sort_url:
                            try:
                                host = r.get('host', '') or source_url.rstrip('/')
                                verify_ok, list_count = verify_sort_url(page, host, sort_url)
                            except Exception as e:
                                record['notes'].append('verify_err:' + sanitize(str(e))[:60])

                        record['sort_url_filled'] = sort_url
                        record['search_url_filled'] = search_url
                        record['rule_articles_filled'] = rule_articles
                        record['rule_image_filled'] = rule_image
                        record['rule_next_page_filled'] = rule_next
                        record['notes'].extend(r.get('notes', []))
                        record['notes'].append(f'verify_ok={verify_ok},list_count={list_count}')

                        # 修复计数
                        any_filled = bool(sort_url or search_url or rule_articles)
                        if any_filled:
                            fixed_count += 1
                        else:
                            failed_count += 1
                        if r.get('error'):
                            record['error'] = r['error']
                    else:
                        record['error'] = r.get('error', 'unknown')
                        failed_count += 1
                except KeyboardInterrupt:
                    print('\n[INTERRUPT] user interrupted, saving...')
                    record['error'] = 'interrupted'
                    records.append(record)
                    raise
                except Exception as e:
                    record['error'] = 'main_err:' + sanitize(str(e))[:80]
                    failed_count += 1

                records.append(record)

                # 增量保存
                if (n + 1) % SAVE_EVERY == 0:
                    save_json(records, len(image_srcs), fixed_count, failed_count)
                    print(f'[SAVE] progress: {len(records)}/{len(image_srcs)}')

        except KeyboardInterrupt:
            print('\n[INTERRUPT] saving partial results...')
        except Exception as e:
            print(f'[FATAL] {sanitize(str(e))}')
            traceback.print_exc()
        finally:
            save_json(records, len(image_srcs), fixed_count, failed_count)
            print(f'[DONE] saved {len(records)} records')
            try:
                context.close()
                browser.close()
            except Exception:
                pass

    # 最终统计
    fully_fixed = 0
    partial_fixed = 0
    still_failed = 0
    for r in records:
        s = bool(r.get('sort_url_filled'))
        se = bool(r.get('search_url_filled'))
        ra = bool(r.get('rule_articles_filled'))
        if s and se and ra:
            fully_fixed += 1
        elif s or se or ra:
            partial_fixed += 1
        else:
            still_failed += 1

    print('\n========== 修复统计 ==========')
    print(f'总数: {len(records)}')
    print(f'完全修复(3字段都填): {fully_fixed}')
    print(f'部分修复(1-2字段填): {partial_fixed}')
    print(f'仍然失败: {still_failed}')
    print(f'输出文件: {OUTPUT_JSON}')
    print('==============================')


if __name__ == '__main__':
    run()
