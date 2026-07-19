"""
Navigation source deep splitter.

Reads classified_v2.json, finds AI_CLASSIFY:nav sources, deeply analyzes each
navigation site with Playwright to extract sub-site links, identifies image/video
sub-sites via DOM feature analysis, and creates independent subscription sources.

Output safety: console logs only print technical metrics (idx, counts, confidence,
identified_by). No sourceName/sourceUrl/sourceComment content is printed. URLs in
error messages are sanitized to [URL]/[DOMAIN].
"""
import json
import os
import re
import sys
import time
import traceback
from urllib.parse import urlparse, urljoin

# Output safety: ensure utf-8 on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ====== Config ======
INPUT_PATH = 'output/rss/classified_v2.json'
OUTPUT_PATH = 'output/rss/subagent_navigation_split.json'
PROGRESS_LOG = 'output/rss/_nav_split_progress.log'
INTERMEDIATE_PATH = 'output/rss/_nav_split_intermediate.json'

MAX_SUB_SITES_PER_PARENT = 15  # task says max 20, use 15 for balance
SUB_SITE_TIMEOUT_MS = 12000
PARENT_TIMEOUT_MS = 18000
CONFIDENCE_THRESHOLD = 0.4
POST_LOAD_WAIT_MS = 1500

# Skip these domains (social/app stores/search engines)
SKIP_DOMAIN_KEYWORDS = [
    'facebook.', 'twitter.', 'x.com', 'instagram.', 'telegram.', 't.me',
    'youtube.', 'youtu.be', 'google.', 'baidu.', 'bing.', 'apple.com',
    'github.', 'gitlab.', 'weibo.', 'qq.com', 'wangwang', 'whatsapp',
    'pinterest.', 'linkedin.', 'tiktok.', 'douyin.', 'vk.com', 'reddit.',
    'amazon.', 'ebay.', 'paypal.', 'stripe.', 'jsdelivr.', 'cloudflare.',
    'github.io', 'wikipedia.', 'wiki', 'gov.', 'edu.', 'mozilla.',
]


def sanitize_error(msg: str) -> str:
    """Sanitize error messages: replace URLs/domains with placeholders."""
    if not msg:
        return ''
    # Replace URLs
    msg = re.sub(r'https?://[^\s\'"<>,]+', '[URL]', msg)
    # Replace domain patterns (xxx.yyy.tld)
    msg = re.sub(r'\b[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z]{2,})+\b', '[DOMAIN]', msg, flags=re.IGNORECASE)
    # Replace IPs
    msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', msg)
    return msg


def log_progress(msg: str):
    """Log to both console (safe) and progress file."""
    safe = sanitize_error(msg)
    print(f'[{time.strftime("%H:%M:%S")}] {safe}', flush=True)
    try:
        with open(PROGRESS_LOG, 'a', encoding='utf-8') as f:
            f.write(f'[{time.strftime("%H:%M:%S")}] {safe}\n')
    except Exception:
        pass


def is_skip_domain(host: str) -> bool:
    host_lower = host.lower()
    for kw in SKIP_DOMAIN_KEYWORDS:
        if kw in host_lower:
            return True
    return False


def extract_path_pattern(path: str) -> str:
    """Convert path to pattern: replace long numeric/hex segments with {id}."""
    if not path or path == '/':
        return '/'
    segments = path.split('/')
    new_segments = []
    for seg in segments:
        if not seg:
            new_segments.append('')
            continue
        # numeric id
        if re.match(r'^\d{3,}$', seg):
            new_segments.append('{id}')
        # hex hash
        elif re.match(r'^[a-f0-9]{10,}$', seg, re.IGNORECASE):
            new_segments.append('{id}')
        # ends with .html/.htm/.php/.asp/.jsp
        elif re.search(r'\.(html?|php|asp|jsp|shtml)$', seg, re.IGNORECASE):
            # keep filename but it's a detail page
            if re.match(r'^\d+', seg):
                new_segments.append('{id}.html')
            else:
                new_segments.append(seg)
        else:
            new_segments.append(seg)
    result = '/'.join(new_segments)
    # Truncate long patterns
    if len(result) > 60:
        result = result[:60] + '...'
    return result or '/'


# JavaScript for extracting external links from a navigation page
JS_EXTRACT_LINKS = """
() => {
  const parentHost = window.location.hostname;
  const links = document.querySelectorAll('a[href]');
  const seen = new Set();
  const results = [];
  for (const a of links) {
    const href = a.href || '';
    if (!href || !href.startsWith('http')) continue;
    let url;
    try { url = new URL(href); } catch(e) { continue; }
    if (url.hostname === parentHost) continue;
    if (seen.has(url.hostname)) continue;
    seen.add(url.hostname);
    const text = (a.textContent || '').trim().substring(0, 60);
    // location in nav/header/footer
    let location = 'body';
    let p = a;
    for (let i = 0; i < 5 && p; i++) {
      const tag = p.tagName ? p.tagName.toLowerCase() : '';
      if (tag === 'nav') { location = 'nav'; break; }
      if (tag === 'header') { location = 'header'; break; }
      if (tag === 'footer') { location = 'footer'; break; }
      p = p.parentElement;
    }
    results.push({
      href: href,
      host: url.hostname,
      path: url.pathname,
      text: text,
      location: location
    });
  }
  return results;
}
"""

# JavaScript for analyzing a sub-site's DOM
JS_ANALYZE_DOM = """
() => {
  const imgs = document.querySelectorAll('img');
  const videos = document.querySelectorAll('video');
  const iframes = document.querySelectorAll('iframe');
  const allLinks = Array.from(document.querySelectorAll('a[href]'));
  
  // Collect CSS classes
  const allClasses = new Set();
  document.querySelectorAll('*').forEach(el => {
    if (el.classList) {
      el.classList.forEach(c => {
        if (c) allClasses.add(c.toLowerCase());
      });
    }
  });
  const classList = Array.from(allClasses);
  
  // Image-related classes
  const imgClasses = classList.filter(c =>
    /gallery|album|photo|picture|image|pic-|pics|grid-item|thumb|wallpaper|cosplay/.test(c)
  );
  
  // Video-related classes
  const videoClasses = classList.filter(c =>
    /video|player|movie|play-|episode|drama|anime|vod|film|stream|broadcast/.test(c)
  );
  
  // Link URL patterns
  const linkHrefs = allLinks.map(a => a.href).filter(Boolean);
  const imgUrls = linkHrefs.filter(u => /\\/(pic|image|photo|gallery|album|tu|tupian|cos)\\b/i.test(u));
  const videoUrls = linkHrefs.filter(u => /\\/(video|movie|play|vod|drama|anime|film|episode|kan|kanv)\\b/i.test(u));
  
  // Meta info
  const title = (document.title || '').toLowerCase();
  const metaDesc = (document.querySelector('meta[name="description"]') || {}).content || '';
  const keywords = (document.querySelector('meta[name="keywords"]') || {}).content || '';
  const metaText = (title + ' ' + metaDesc + ' ' + keywords).toLowerCase();
  
  // Image keyword in meta
  const imgMetaHit = /picture|photo|image|gallery|wallpaper|cosplay|\\bpic\\b|tupian|tupianku/.test(metaText);
  // Video keyword in meta
  const videoMetaHit = /video|movie|film|drama|anime|episode|play online|stream|vod|dianying|dianshi|dongman/.test(metaText);
  
  // Count visible images (with size)
  let visibleImgCount = 0;
  imgs.forEach(img => {
    const rect = img.getBoundingClientRect();
    if (rect.width > 50 && rect.height > 50) visibleImgCount++;
  });
  
  return {
    img_count: imgs.length,
    visible_img_count: visibleImgCount,
    video_count: videos.length,
    iframe_count: iframes.length,
    link_count: allLinks.length,
    img_classes: imgClasses.slice(0, 8),
    video_classes: videoClasses.slice(0, 8),
    img_url_count: imgUrls.length,
    video_url_count: videoUrls.length,
    img_meta_hit: imgMetaHit,
    video_meta_hit: videoMetaHit,
    title_len: (document.title || '').length,
    body_text_len: (document.body && document.body.innerText) ? document.body.innerText.length : 0
  };
}
"""


def calc_confidence(metrics: dict):
    """Calculate image/video confidence scores and reasons."""
    img_score = 0.0
    img_reasons = []
    video_score = 0.0
    video_reasons = []

    # Image indicators
    if metrics.get('visible_img_count', 0) > 30:
        img_score += 0.4
        img_reasons.append('visible_img_high')
    elif metrics.get('visible_img_count', 0) > 10:
        img_score += 0.25
        img_reasons.append('visible_img_mid')

    if metrics.get('img_classes'):
        img_score += 0.3
        img_reasons.append('img_gallery_class:' + metrics['img_classes'][0])

    if metrics.get('img_url_count', 0) > 5:
        img_score += 0.3
        img_reasons.append('img_url_pattern')
    elif metrics.get('img_url_count', 0) > 0:
        img_score += 0.1
        img_reasons.append('img_url_few')

    if metrics.get('img_meta_hit'):
        img_score += 0.15
        img_reasons.append('img_meta_keyword')

    # Video indicators
    if metrics.get('video_count', 0) > 0:
        video_score += 0.45
        video_reasons.append('video_tag')

    if metrics.get('video_classes'):
        video_score += 0.3
        video_reasons.append('video_class:' + metrics['video_classes'][0])

    if metrics.get('video_url_count', 0) > 5:
        video_score += 0.3
        video_reasons.append('video_url_pattern')
    elif metrics.get('video_url_count', 0) > 0:
        video_score += 0.15
        video_reasons.append('video_url_few')

    if metrics.get('video_meta_hit'):
        video_score += 0.15
        video_reasons.append('video_meta_keyword')

    # Iframe could indicate embedded video player
    if metrics.get('iframe_count', 0) > 0 and video_score > 0:
        video_score += 0.05
        video_reasons.append('iframe_embed')

    img_score = min(img_score, 0.95)
    video_score = min(video_score, 0.95)

    return img_score, img_reasons, video_score, video_reasons


def create_sub_source(sub_url: str, sub_type: int, confidence: float,
                      identified_by: list, parent_idx: int) -> dict:
    """Create a minimal sub-source object for next-stage field completion."""
    parsed = urlparse(sub_url)
    domain = parsed.hostname or ''
    return {
        'sourceUrl': sub_url,
        'sourceName': domain,
        'sourceComment': f'AI_EXTRACTED_FROM_NAV:parent_idx={parent_idx},confidence={confidence:.2f},by={",".join(identified_by[:3])}',
        'type': sub_type,
        'enabled': True,
        'sourceIcon': '',
        'searchUrl': '',
        'sortUrl': '',
        'articleStyle': 0,
        'customOrder': 0,
        'enableJs': False,
        'enabledCookieJar': False,
        'header': '',
        'lastHost': domain,
        'lastUpdateTime': 0,
        'loadWithBaseUrl': '',
        'loginCheckJs': '',
        'loginUrl': '',
        'parseConcurrency': 0,
        'preload': False,
        'ruleArticles': '',
        'ruleContent': '',
        'ruleImage': '',
        'ruleLink': '',
        'ruleNextPage': '',
        'rulePubDate': '',
        'ruleTitle': '',
        'showWebLog': False,
        'singleUrl': False,
        'sourceGroup': '',
        'weight': 0,
    }


def visit_page(page, url: str, timeout_ms: int):
    """Visit URL with timeout, return (success, error_msg)."""
    try:
        resp = page.goto(url, timeout=timeout_ms, wait_until='domcontentloaded')
        if POST_LOAD_WAIT_MS > 0:
            page.wait_for_timeout(POST_LOAD_WAIT_MS)
        # Check HTTP status
        if resp and resp.status >= 400:
            return False, f'http_{resp.status}'
        return True, ''
    except PlaywrightTimeout:
        return False, 'timeout'
    except Exception as e:
        return False, sanitize_error(str(e))[:200]


def extract_sub_sites_from_parent(page, parent_url: str):
    """Extract sub-site links from a navigation page."""
    try:
        raw_links = page.evaluate(JS_EXTRACT_LINKS)
    except Exception as e:
        return [], sanitize_error(str(e))[:200]

    # Filter and deduplicate by host
    seen_hosts = set()
    # Also track parent's host to skip
    parent_host = urlparse(parent_url).hostname or ''
    if parent_host:
        seen_hosts.add(parent_host)

    candidates = []
    for link in raw_links:
        host = link.get('host', '')
        if not host:
            continue
        if is_skip_domain(host):
            continue
        if host in seen_hosts:
            continue
        seen_hosts.add(host)
        # Build candidate (don't keep text - could be sensitive)
        href = link.get('href', '')
        # Normalize: strip query/fragment for homepage visit
        parsed = urlparse(href)
        home_url = f'{parsed.scheme}://{parsed.netloc}/'
        candidates.append({
            'home_url': home_url,
            'host': host,
            'path': parsed.path or '/',
            'location': link.get('location', 'body'),
        })

    # Prioritize: nav/header links first, then by shorter path
    candidates.sort(key=lambda c: (
        0 if c['location'] in ('nav', 'header') else 1,
        len(c['path']),
    ))

    return candidates[:MAX_SUB_SITES_PER_PARENT], ''


def analyze_sub_site(page, sub_url: str):
    """Analyze a sub-site's DOM, return (metrics, error)."""
    success, err = visit_page(page, sub_url, SUB_SITE_TIMEOUT_MS)
    if not success:
        return None, err
    try:
        metrics = page.evaluate(JS_ANALYZE_DOM)
        return metrics, ''
    except Exception as e:
        return None, sanitize_error(str(e))[:200]


def process_parent(browser, parent_idx: int, parent_source: dict) -> dict:
    """Process one navigation parent site, return result dict."""
    parent_url = parent_source.get('sourceUrl', '')
    result = {
        'parent_idx': parent_idx,
        'parent_url_accessible': False,
        'sub_sites_found': 0,
        'sub_sites_valid': 0,
        'sub_sources_created': [],
        'parent_error': '',
    }

    if not parent_url or not parent_url.startswith('http'):
        result['parent_error'] = 'invalid_parent_url'
        return result

    # Create a fresh context for each parent to avoid state leakage
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 800},
        locale='zh-CN',
    )
    # Block heavy resources for speed (but keep images for img_count analysis)
    context.route('**/*', lambda route: (
        route.abort() if route.request.resource_type in ('media', 'font')
        else route.continue_()
    ))
    page = context.new_page()

    try:
        # Step 1: visit parent
        success, err = visit_page(page, parent_url, PARENT_TIMEOUT_MS)
        if not success:
            result['parent_error'] = err or 'parent_inaccessible'
            log_progress(f'  parent_idx={parent_idx} parent_visit_failed err={err}')
            return result
        result['parent_url_accessible'] = True

        # Step 2: extract sub-sites
        sub_sites, extract_err = extract_sub_sites_from_parent(page, parent_url)
        result['sub_sites_found'] = len(sub_sites)
        if extract_err:
            log_progress(f'  parent_idx={parent_idx} extract_warn err={extract_err}')
        if not sub_sites:
            log_progress(f'  parent_idx={parent_idx} no_sub_sites_found')
            return result

        log_progress(f'  parent_idx={parent_idx} sub_sites_found={len(sub_sites)}')

        # Step 3: analyze each sub-site
        valid_count = 0
        for sub_idx, sub in enumerate(sub_sites):
            home_url = sub['home_url']
            host = sub['host']

            metrics, err = analyze_sub_site(page, home_url)
            if metrics is None:
                log_progress(f'    sub_idx={sub_idx} analyze_failed err={err}')
                continue

            valid_count += 1

            # Step 4: confidence & type identification
            img_score, img_reasons, video_score, video_reasons = calc_confidence(metrics)

            chosen_type = 0
            chosen_conf = 0.0
            chosen_reasons = []
            if img_score >= video_score and img_score >= CONFIDENCE_THRESHOLD:
                chosen_type = 1  # image
                chosen_conf = img_score
                chosen_reasons = img_reasons
            elif video_score > img_score and video_score >= CONFIDENCE_THRESHOLD:
                chosen_type = 2  # video
                chosen_conf = video_score
                chosen_reasons = video_reasons

            if chosen_type == 0:
                # Below threshold or no clear type - skip
                log_progress(f'    sub_idx={sub_idx} skipped img_score={img_score:.2f} video_score={video_score:.2f}')
                continue

            # Step 5: create sub-source
            sub_source = create_sub_source(home_url, chosen_type, chosen_conf,
                                           chosen_reasons, parent_idx)
            path_pattern = extract_path_pattern(sub['path'])

            result['sub_sources_created'].append({
                'sub_idx': sub_idx,
                'sub_url_pattern': f'[DOMAIN]{path_pattern}',
                'sub_type': chosen_type,
                'confidence': round(chosen_conf, 2),
                'identified_by': chosen_reasons[:5],
                'sub_source': sub_source,
            })
            log_progress(f'    sub_idx={sub_idx} type={chosen_type} conf={chosen_conf:.2f} by={chosen_reasons[:3]}')

        result['sub_sites_valid'] = valid_count
        log_progress(f'  parent_idx={parent_idx} done valid={valid_count} created={len(result["sub_sources_created"])}')

    finally:
        try:
            page.close()
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass

    return result


def write_final_output(nav_sources, results, image_count, video_count, interrupted=False):
    """Write final output and intermediate state. Used both on success and interruption."""
    final_output = {
        'agent': 'navigation_source_splitter',
        'total_navigation_sources': len(nav_sources),
        'total_sub_sources_extracted': image_count + video_count,
        'image_sub_sources': image_count,
        'video_sub_sources': video_count,
        'interrupted': interrupted,
        'results': results,
        'sub_sources': [
            sub['sub_source'] for r in results for sub in r.get('sub_sources_created', [])
        ],
    }
    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_progress(f'final_output_save_err: {sanitize_error(str(e))[:100]}')
        return False


def main():
    log_progress('=== Navigation Source Splitter START ===')

    # Load input
    if not os.path.exists(INPUT_PATH):
        log_progress(f'FATAL: input not found: {INPUT_PATH}')
        return 1
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    log_progress(f'loaded sources: {len(sources)}')

    # Filter nav sources
    nav_sources = []
    for i, s in enumerate(sources):
        comment = s.get('sourceComment', '')
        if 'AI_CLASSIFY:nav' in comment:
            nav_sources.append((i, s))
    log_progress(f'nav_sources_found: {len(nav_sources)}')

    if not nav_sources:
        log_progress('FATAL: no nav sources found')
        return 1

    # Resume support: load intermediate results
    done_parents = {}
    if os.path.exists(INTERMEDIATE_PATH):
        try:
            with open(INTERMEDIATE_PATH, 'r', encoding='utf-8') as f:
                inter = json.load(f)
            done_parents = {r['parent_idx']: r for r in inter.get('results', [])}
            log_progress(f'resumed from intermediate: {len(done_parents)} parents already done')
        except Exception as e:
            log_progress(f'intermediate_load_err: {sanitize_error(str(e))[:100]}')

    # Mark parent sources: nav_parent=true, enabled=false
    for idx, s in nav_sources:
        s['nav_parent'] = True
        s['enabled'] = False
        # Append marker to sourceComment (keep existing comment)
        existing = s.get('sourceComment', '')
        if 'NAV_PARENT_DISABLED' not in existing:
            s['sourceComment'] = existing + '|NAV_PARENT_DISABLED'

    results = list(done_parents.values())
    image_count = 0
    video_count = 0
    for r in results:
        for sub in r.get('sub_sources_created', []):
            if sub['sub_type'] == 1:
                image_count += 1
            elif sub['sub_type'] == 2:
                video_count += 1

    interrupted = False

    # Launch browser
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins',
                ]
            )
        except Exception as e:
            err_msg = sanitize_error(str(e))
            log_progress(f'FATAL: browser_launch_failed err={err_msg}')
            if 'Executable doesn\'t exist' in str(e) or 'browser_type.launch' in str(e):
                log_progress('HINT: run `playwright install chromium` first')
            return 1

        try:
            total = len(nav_sources)
            for i, (parent_idx, parent_source) in enumerate(nav_sources):
                if parent_idx in done_parents:
                    log_progress(f'[{i+1}/{total}] parent_idx={parent_idx} SKIP (already done)')
                    continue

                log_progress(f'[{i+1}/{total}] parent_idx={parent_idx} START')

                try:
                    result = process_parent(browser, parent_idx, parent_source)
                except KeyboardInterrupt:
                    log_progress(f'  parent_idx={parent_idx} INTERRUPTED, saving state...')
                    interrupted = True
                    break
                except Exception as e:
                    err_msg = sanitize_error(str(e))
                    log_progress(f'  parent_idx={parent_idx} UNEXPECTED_ERR: {err_msg}')
                    result = {
                        'parent_idx': parent_idx,
                        'parent_url_accessible': False,
                        'sub_sites_found': 0,
                        'sub_sites_valid': 0,
                        'sub_sources_created': [],
                        'parent_error': f'unexpected_err: {err_msg[:100]}',
                    }

                results.append(result)
                # Update counts
                for sub in result.get('sub_sources_created', []):
                    if sub['sub_type'] == 1:
                        image_count += 1
                    elif sub['sub_type'] == 2:
                        video_count += 1

                # Save intermediate after each parent
                try:
                    inter_out = {
                        'agent': 'navigation_source_splitter',
                        'total_navigation_sources': total,
                        'total_sub_sources_extracted': image_count + video_count,
                        'image_sub_sources': image_count,
                        'video_sub_sources': video_count,
                        'results': results,
                        'sub_sources': [
                            sub['sub_source'] for r in results for sub in r.get('sub_sources_created', [])
                        ],
                    }
                    with open(INTERMEDIATE_PATH, 'w', encoding='utf-8') as f:
                        json.dump(inter_out, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    log_progress(f'  intermediate_save_err: {sanitize_error(str(e))[:100]}')

        except KeyboardInterrupt:
            log_progress('OUTER KeyboardInterrupt caught, saving state...')
            interrupted = True
        finally:
            try:
                browser.close()
            except Exception:
                pass

    # Final output (always write, even if interrupted)
    write_final_output(nav_sources, results, image_count, video_count, interrupted)

    log_progress(f'=== {"INTERRUPTED" if interrupted else "DONE"} ===')
    log_progress(f'total_navigation_sources: {len(nav_sources)}')
    log_progress(f'total_sub_sources_extracted: {image_count + video_count}')
    log_progress(f'image_sub_sources: {image_count}')
    log_progress(f'video_sub_sources: {video_count}')
    log_progress(f'output: {OUTPUT_PATH}')

    # Clean up intermediate file only on success
    if not interrupted:
        try:
            if os.path.exists(INTERMEDIATE_PATH):
                os.remove(INTERMEDIATE_PATH)
        except Exception:
            pass

    return 0 if not interrupted else 2


if __name__ == '__main__':
    sys.exit(main())
