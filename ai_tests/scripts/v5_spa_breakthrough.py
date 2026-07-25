# -*- coding: utf-8 -*-
"""
V5 SPA 站点外链提取突破脚本
对3个SPA导航站（源28/96/153）应用5大技术手段：
  手段1: 滚动触发懒加载
  手段2: Vue/React props 提取
  手段3: 扫描 window 对象所有数据
  手段4: 扫描 script 标签的 JSON 数据
  手段5: 提取所有可见链接（动态渲染后）

输出: v5_spa_breakthrough.json（所有URL脱敏为 http://[DOMAIN]/path）
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# 强制无缓冲输出
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
_orig_print = print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _orig_print(*args, **kwargs)

V5_PATH = Path(r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_final.json")
OUT_PATH = Path(r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_spa_breakthrough.json")

TARGET_INDICES = [28, 96, 153]
MAX_EXTERNAL_PER_PARENT = 50        # 提取外链上限
MAX_SUBSOURCE_PER_PARENT = 15       # 每父站子源上限
PAGE_TIMEOUT_MS = 45000             # 提高到45s
EXTERN_TIMEOUT_MS = 15000           # 提高到15s
CONFIDENCE_THRESHOLD = 0.6          # 降低阈值到0.6（SPA站点识别可能偏低）
POST_GOTO_WAIT_MS = 5000            # goto后额外等待5s让JS执行
SCROLL_WAIT_MS = 3000               # 每次滚动后等待3s

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

# Stealth 反检测脚本：隐藏 headless 特征
JS_STEALTH_INIT = """
() => {
  // 隐藏 webdriver 属性
  try { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); } catch(e) {}
  // 伪装 plugins
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5]
    });
  } catch(e) {}
  // 伪装 languages
  try { Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']}); } catch(e) {}
  // 伪装 platform
  try { Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'}); } catch(e) {}
  // 移除 chrome 检测
  try { window.chrome = window.chrome || {}; } catch(e) {}
  // 伪装 permissions
  try {
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
  } catch(e) {}
  return 'stealth_applied';
}
"""

# 调试信息提取 JS
JS_DEBUG_PAGE_INFO = """
() => {
  const html = document.documentElement.outerHTML || '';
  const title = document.title || '';
  const bodyText = (document.body && document.body.innerText) || '';
  // 检测反爬特征
  const antiBotKeywords = ['captcha', 'verify', 'challenge', 'cloudflare', '安全验证', '人机验证', '访问验证', '阻断', 'block', 'denied', 'forbidden', 'robot', 'antispider'];
  const html_lower = html.toLowerCase();
  const detected = antiBotKeywords.filter(k => html_lower.includes(k));
  return {
    title: title.slice(0, 100),
    title_len: title.length,
    html_len: html.length,
    body_text_len: bodyText.length,
    body_text_preview: bodyText.slice(0, 200).replace(/\\s+/g, ' '),
    a_count: document.querySelectorAll('a[href]').length,
    img_count: document.querySelectorAll('img').length,
    script_count: document.querySelectorAll('script').length,
    iframe_count: document.querySelectorAll('iframe').length,
    form_count: document.querySelectorAll('form').length,
    has_app_root: !!document.querySelector('#app,#root,#__nuxt,#__next,[data-v-app]'),
    antibot_detected: detected,
    final_url: location.href.slice(0, 200),
    ready_state: document.readyState
  };
}
"""

# ========== 脱敏函数 ==========
def sanitize_url(url: str) -> str:
    """将真实URL脱敏为 http://[DOMAIN]/path 格式，保留path模式"""
    if not url:
        return ""
    if url.startswith("@js:"):
        return "@js:[SCRIPT]"
    try:
        p = urlparse(url)
        path = p.path or "/"
        if p.query:
            qs = re.sub(r"=[^&]*", "={val}", p.query)
            path = f"{path}?{qs}"
        if p.fragment:
            path = f"{path}#[ANCHOR]"
        scheme = p.scheme or "http"
        return f"{scheme}://[DOMAIN]{path}"
    except Exception:
        return "http://[DOMAIN]/path"

def mask_url(u: str) -> str:
    if not u or not isinstance(u, str):
        return u
    return re.sub(r'https?://[^/\s"\'\\]+', 'http://[DOMAIN]', u)

def mask_urls_in_data(obj):
    """递归脱敏所有 URL 字符串"""
    if isinstance(obj, str):
        if re.search(r'https?://', obj):
            return re.sub(r'https?://[^/\s"\'\\]+', 'http://[DOMAIN]', obj)
        return obj
    elif isinstance(obj, list):
        return [mask_urls_in_data(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: mask_urls_in_data(v) for k, v in obj.items()}
    return obj

def sanitize_text(t: str, max_len: int = 60) -> str:
    if not t:
        return ""
    t = re.sub(r"https?://[^\s]+", "http://[DOMAIN]/path", t)
    t = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]", t)
    t = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]", t)
    if len(t) > max_len:
        t = t[:max_len] + "..."
    return t

# ========== 5大突破手段 JS ==========

# 手段1: 滚动触发懒加载（滚动3次后提取所有 a[href]）
JS_STRATEGY1_SCROLL_AND_LINKS = """
() => {
  const scrollOnce = () => new Promise(resolve => {
    try { window.scrollTo(0, document.body.scrollHeight); } catch(e) {}
    setTimeout(() => resolve(), 100);
  });
  // 由于page.evaluate是同步的，这里我们直接返回当前快照
  // 真正的滚动循环由Python端控制
  const links = Array.from(document.querySelectorAll('a[href]'))
    .map(a => ({
      href: a.href || '',
      text: (a.textContent || '').trim().slice(0, 30)
    }))
    .filter(a => a.href && a.href.startsWith('http') && !a.href.startsWith('javascript:') && !a.href.startsWith('mailto:'));
  return { links: links, count: links.length };
}
"""

# 手段2: Vue/React props 提取
JS_STRATEGY2_VUE_REACT = """
() => {
  const result = {
    vue_app: null,
    react_root: null,
    nuxt_data: null,
    initial_state: null
  };
  // Vue 3
  try {
    const vueEl = document.querySelector('[data-v-app],#app,#__nuxt,.nuxt-app');
    if (vueEl && vueEl.__vue_app__) {
      const vueApp = vueEl.__vue_app__;
      const root = vueApp._instance && vueApp._instance.proxy;
      result.vue_app = {
        has_router: !!(vueApp.config && vueApp.config.globalProperties && vueApp.config.globalProperties.$router),
        routes_count: 0,
        routes_preview: [],
        current_route: root && root.$route ? root.$route.path : null
      };
      try {
        if (root && root.$router) {
          const routes = root.$router.getRoutes ? root.$router.getRoutes() : [];
          result.vue_app.routes_count = routes.length;
          result.vue_app.routes_preview = routes.slice(0, 10).map(r => r.path);
        }
      } catch(e) { result.vue_app.routes_error = e.message; }
    }
  } catch(e) { result.vue_app = { error: e.message }; }
  // React
  try {
    const reactRoot = document.querySelector('#root,[data-reactroot],#__next');
    if (reactRoot) {
      const fiberKey = Object.keys(reactRoot).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
      const propsKey = Object.keys(reactRoot).find(k => k.startsWith('__reactProps'));
      result.react_root = {
        found: !!fiberKey,
        fiber_key: fiberKey ? 'found' : null,
        props_key: propsKey ? 'found' : null
      };
    }
  } catch(e) { result.react_root = { error: e.message }; }
  // Nuxt
  try {
    if (window.__NUXT__) {
      result.nuxt_data = {
        data_keys: Object.keys(window.__NUXT__.data || {}).slice(0, 10),
        state_keys: Object.keys(window.__NUXT__.state || {}).slice(0, 10)
      };
    }
  } catch(e) { result.nuxt_data = { error: e.message }; }
  // Initial State
  try {
    if (window.__INITIAL_STATE__) {
      result.initial_state = Object.keys(window.__INITIAL_STATE__).slice(0, 10);
    }
    if (window.__APOLLO_STATE__) {
      result.apollo_state = Object.keys(window.__APOLLO_STATE__).slice(0, 10);
    }
    if (window.__PRELOADED_STATE__) {
      result.preloaded_state = Object.keys(window.__PRELOADED_STATE__).slice(0, 10);
    }
  } catch(e) { result.initial_state = { error: e.message }; }
  return result;
}
"""

# 手段3: 扫描 window 对象所有数据属性
JS_STRATEGY3_WINDOW_SCAN = """
() => {
  const ignored = ['document','window','self','location','top','parent','frames','chrome','console','performance','crypto','navigator','history','screen','external','sidebar','length','closed','name','status','frameElement','opener','origin'];
  const data_keys = [];
  try {
    for (const k of Object.keys(window)) {
      if (ignored.includes(k)) continue;
      try {
        const v = window[k];
        if (v && typeof v === 'object' && !Array.isArray(v) && typeof v !== 'function') {
          try {
            const sub_keys = Object.keys(v).slice(0, 5);
            if (sub_keys.length > 0) {
              data_keys.push({key: k, sub_keys: sub_keys});
            }
          } catch(e) {}
        }
      } catch(e) {}
    }
  } catch(e) {}
  return { data_keys: data_keys.slice(0, 50), total: data_keys.length };
}
"""

# 手段4: 扫描 script 标签的 JSON 数据 + 所有 script 文本中的URL + JS重定向目标
JS_STRATEGY4_SCRIPT_JSON = """
() => {
  const result = {
    json_scripts: [],
    inline_url_scripts: [],
    redirect_targets: [],
    all_inline_urls: []
  };
  // 1. 扫描 type=application/json 的 script
  const json_scripts = Array.from(document.querySelectorAll('script[type="application/json"],script[type="application/x-json"],script[id*=__NEXT_DATA__],script[id*=nuxt]'));
  json_scripts.forEach(s => {
    try {
      const text = (s.textContent || '').trim();
      if (text.length < 2) return;
      const data = JSON.parse(text);
      const urls = [];
      const seen = new Set();
      const extract = (obj, depth) => {
        if (depth > 8 || !obj) return;
        if (typeof obj === 'string') {
          if (/^https?:\\/\\//.test(obj) && !seen.has(obj)) {
            seen.add(obj);
            urls.push(obj);
          }
        } else if (Array.isArray(obj)) {
          obj.slice(0, 200).forEach(x => extract(x, depth + 1));
        } else if (typeof obj === 'object') {
          Object.values(obj).slice(0, 200).forEach(x => extract(x, depth + 1));
        }
      };
      extract(data, 0);
      let data_keys = [];
      try { data_keys = Object.keys(data).slice(0, 10); } catch(e) {}
      result.json_scripts.push({
        script_id: s.id || '',
        script_type: s.type || '',
        data_keys: data_keys,
        urls: urls.slice(0, 100),
        urls_count: urls.length
      });
    } catch(e) {
      result.json_scripts.push({
        script_id: s.id || '',
        script_type: s.type || '',
        parse_error: true,
        error_msg: e.message.slice(0, 100)
      });
    }
  });
  // 2. 扫描所有 <script> 文本中的URL（包括重定向目标）
  const all_scripts = Array.from(document.querySelectorAll('script'));
  const all_urls = new Set();
  const redirect_targets = [];
  for (const s of all_scripts) {
    const text = (s.textContent || '');
    if (text.length < 5) continue;
    // 提取JS重定向目标
    const redirect_patterns = [
      /location\\.href\\s*=\\s*['"]([^'"]+)['"]/g,
      /window\\.location\\s*=\\s*['"]([^'"]+)['"]/g,
      /window\\.location\\.href\\s*=\\s*['"]([^'"]+)['"]/g,
      /location\\.replace\\s*\\(\\s*['"]([^'"]+)['"]\\s*\\)/g,
      /location\\.assign\\s*\\(\\s*['"]([^'"]+)['"]\\s*\\)/g,
      /window\\.open\\s*\\(\\s*['"]([^'"]+)['"]/g,
      /document\\.location\\s*=\\s*['"]([^'"]+)['"]/g,
    ];
    for (const p of redirect_patterns) {
      let m;
      while ((m = p.exec(text)) !== null) {
        const target = m[1];
        if (target && target.length > 3) {
          redirect_targets.push(target);
          if (/^https?:\\/\\//.test(target)) all_urls.add(target);
        }
      }
    }
    // 提取所有 http(s):// URL
    const url_matches = text.match(/https?:\\\\?\\/\\\\?\\/[^"'\\s<>)]+/g) || [];
    for (const u of url_matches) {
      // 清理转义字符
      const clean = u.replace(/\\\\\\//g, '/');
      if (clean.length > 10) all_urls.add(clean);
    }
    // 也提取相对路径（/path 形式），后面Python端补全
    const rel_matches = text.match(/['"](\\/[^'"]+\\.html?)['"]/g) || [];
    for (const r of rel_matches) {
      const m = r.match(/['"](\\/[^'"]+\\.html?)['"]/);
      if (m) {
        // 转为绝对URL（运行时补全）
        try {
          const abs = new URL(m[1], location.href).href;
          all_urls.add(abs);
        } catch(e) {}
      }
    }
  }
  result.all_inline_urls = Array.from(all_urls).slice(0, 100);
  result.redirect_targets = Array.from(new Set(redirect_targets)).slice(0, 20);
  return result;
}
"""

# 手段5: 提取所有可见链接（包括动态渲染后）
JS_STRATEGY5_ALL_LINKS = """
() => {
  const links = Array.from(document.querySelectorAll('a[href]'))
    .map(a => {
      try {
        const u = new URL(a.href, location.href);
        return {
          href: u.href,
          text: (a.textContent || '').trim().slice(0, 30),
          host: u.hostname,
          is_external: u.hostname !== location.hostname,
          pathname: u.pathname
        };
      } catch(e) { return null; }
    })
    .filter(a => a && a.href && a.href.startsWith('http') && !a.href.startsWith('javascript:') && !a.href.startsWith('mailto:'));
  // 去重
  const seen = new Set();
  const uniq = [];
  for (const l of links) {
    if (!seen.has(l.href)) {
      seen.add(l.href);
      uniq.push(l);
    }
  }
  return {
    total_links: uniq.length,
    external_links: uniq.filter(l => l.is_external).length,
    internal_links: uniq.filter(l => !l.is_external).length,
    links: uniq.slice(0, 200)
  };
}
"""

# 类型识别 JS（与 navigation_split_v5 一致的DOM特征检测）
JS_DETECT_TYPE = """
() => {
  const html = document.documentElement.outerHTML || '';
  const lower = html.toLowerCase();
  const feats = [];
  const videoTags = document.querySelectorAll('video').length;
  const m3u8Links = (lower.match(/\\.m3u8/g) || []).length;
  const mp4Links = (lower.match(/\\.mp4/g) || []).length;
  const hasVideoJs = lower.includes('video.js') || lower.includes('videojs');
  const hasJwPlayer = lower.includes('jwplayer');
  const hasDPlayer = lower.includes('dplayer') || lower.includes('dp.js');
  const hasHlsJs = lower.includes('hls.js') || lower.includes('hls.min.js');
  const hasFlvJs = lower.includes('flv.js');
  if (videoTags > 0) feats.push('video_tag');
  if (m3u8Links > 0) feats.push('m3u8_link');
  if (mp4Links > 0) feats.push('mp4_link');
  if (hasVideoJs) feats.push('videojs');
  if (hasJwPlayer) feats.push('jwplayer');
  if (hasDPlayer) feats.push('dplayer');
  if (hasHlsJs) feats.push('hls.js');
  if (hasFlvJs) feats.push('flv.js');
  const imgs = document.querySelectorAll('img').length;
  const lazyImgs = document.querySelectorAll('img[data-src], img[data-original], img.lazyload, .lazyload img').length;
  const galleryEls = document.querySelectorAll('.gallery, .photo-album, .album, .swiper-slide, .photo-list').length;
  const imgHeavy = imgs > 15;
  if (imgHeavy) feats.push('img_heavy:' + imgs);
  if (lazyImgs > 0) feats.push('lazyload:' + lazyImgs);
  if (galleryEls > 0) feats.push('gallery:' + galleryEls);
  const articleEls = document.querySelectorAll('.item, .post, .article, article, .news-item, .entry').length;
  if (articleEls > 0) feats.push('article_list:' + articleEls);
  const bodyText = (document.body.innerText || '').length;
  let vtype = 0;
  let conf = 0.5;
  if (videoTags > 0 || m3u8Links > 0 || mp4Links > 0 || hasVideoJs || hasJwPlayer || hasDPlayer || hasHlsJs) {
    vtype = 2;
    conf = 0.85;
    if (m3u8Links > 0) conf = 0.95;
  } else if (imgHeavy && imgs > articleEls * 3) {
    vtype = 1;
    conf = 0.8;
    if (galleryEls > 0 || lazyImgs > 5) conf = 0.9;
  } else if (articleEls > 0) {
    vtype = 0;
    conf = 0.75;
  } else if (bodyText > 500) {
    vtype = 0;
    conf = 0.7;
  } else {
    vtype = 0;
    conf = 0.5;
  }
  return { type: vtype, conf: conf, feats: feats, imgs: imgs, articles: articleEls, body_text_len: bodyText };
}
"""

JS_FIND_SORT_SEARCH = """
() => {
  let sort_url_pattern = '';
  let search_url_pattern = '';
  try {
    const forms = document.querySelectorAll('form[action]');
    for (const f of forms) {
      const inputs = f.querySelectorAll('input[name]');
      for (const i of inputs) {
        if (i.name && (i.name.toLowerCase().includes('q') || i.name.toLowerCase().includes('search') || i.name.toLowerCase().includes('keyword') || i.name.toLowerCase().includes('key'))) {
          search_url_pattern = f.action + '?' + i.name + '={{key}},page={{page}}';
          break;
        }
      }
      if (search_url_pattern) break;
    }
    const cats = document.querySelectorAll('a[href*="category"], a[href*="cate"], a[href*="list"], a[href*="sort"], a[href*="type"], .nav a, .category a');
    const out = [];
    cats.forEach(a => {
      const href = a.href;
      if (href && !href.includes('javascript:')) out.push(href);
    });
    if (out.length > 0) sort_url_pattern = out[0];
  } catch(e) {}
  return { sort_url: sort_url_pattern, search_url: search_url_pattern };
}
"""

# ========== 工具函数 ==========
def is_skip_host(host: str) -> bool:
    """过滤明显的非内容链接（cdn、广告、统计等）"""
    if not host:
        return True
    host = host.lower()
    SKIP_KEYWORDS = [
        "cdn.", "googleapis", "google-analytics", "googletag", "facebook.",
        "twitter.", "instagram.", "youtube.", "gstatic", "schema.org", "w3.org",
        "jquery", "bootstrap", "font-", "cdnjs", "jsdelivr", "unpkg", "npmjs",
        "github.com", "gitlab.com", "gravatar", "wp.com", "wp-content",
        "doubleclick", "adsense", "adserver", "adnxs", "googlesyndication",
        "baidu.com/cdn", "qq.com/static", "aliyun", "aliyuncs", "tencentsdk",
        "msn.com", "bing.com", "yahoo.com", "amazon.com", "ebay.com",
        "wikipedia.org", "mozilla.org", "microsoft.com", "apple.com",
        "linkedin.com", "pinterest.com", "tiktok.com", "telegram.org",
        "discord.com", "discordapp.com", "slack.com",
    ]
    return any(kw in host for kw in SKIP_KEYWORDS)

def is_internal_link(url: str, parent_host: str) -> bool:
    """判断是否为父站内链（同域名）"""
    try:
        u = urlparse(url)
        return (u.hostname or '').lower() == (parent_host or '').lower()
    except Exception:
        return False

def merge_external_links(strat1_links, strat5_links, strat4_urls, parent_url):
    """合并手段1/5的a[href] + 手段4的script JSON中的URL，去重，过滤内链"""
    parent_host = (urlparse(parent_url).hostname or '').lower()
    seen = set()
    merged = []
    # 合并 strat1 + strat5
    for link in (strat1_links or []) + (strat5_links or []):
        href = link.get('href') if isinstance(link, dict) else None
        if not href or not isinstance(href, str):
            continue
        if not href.startswith('http'):
            continue
        if href in seen:
            continue
        if is_internal_link(href, parent_host):
            continue
        host = (urlparse(href).hostname or '').lower()
        if is_skip_host(host):
            continue
        seen.add(href)
        merged.append({
            'href': href,
            'host': host,
            'text': (link.get('text') or '')[:50] if isinstance(link, dict) else '',
            'source': 'a_tag'
        })
    # 合并 strat4 URLs
    for url in (strat4_urls or []):
        if not url or not isinstance(url, str) or not url.startswith('http'):
            continue
        if url in seen:
            continue
        if is_internal_link(url, parent_host):
            continue
        host = (urlparse(url).hostname or '').lower()
        if is_skip_host(host):
            continue
        seen.add(url)
        merged.append({
            'href': url,
            'host': host,
            'text': '',
            'source': 'script_json'
        })
    return merged[:MAX_EXTERNAL_PER_PARENT]

def detect_type_features(page):
    """检测外链页面DOM特征，返回(type, confidence, features, detail)"""
    try:
        r = page.evaluate(JS_DETECT_TYPE)
        return r.get("type", 0), r.get("conf", 0.5), r.get("feats", []), r
    except Exception as e:
        print(f"  [WARN] detect_type error: {type(e).__name__}: {str(e)[:80]}")
        return 0, 0.3, ["detect_error"], {}

def find_sort_search_url(page, base_url):
    """从外链页面提取 sortUrl/searchUrl 模板"""
    sort_pattern = ""
    search_pattern = ""
    try:
        r = page.evaluate(JS_FIND_SORT_SEARCH)
        sort_url = r.get('sort_url', '')
        search_url = r.get('search_url', '')
        if sort_url:
            sort_pattern = sanitize_url(sort_url)
        if search_url:
            try:
                pu = urlparse(search_url)
                scheme = pu.scheme or "http"
                path = pu.path or "/"
                search_pattern = f"{scheme}://[DOMAIN]{path}"
                if pu.query:
                    qs_clean = re.sub(r"\b([a-z0-9_]+)=[^&\s{]*", lambda m: m.group(1) + "={val}", pu.query, flags=re.I)
                    qs_clean = qs_clean.replace("{val}", "{{key}}") if "key" in pu.query else qs_clean
                    search_pattern += "?" + qs_clean
            except Exception:
                search_pattern = "http://[DOMAIN]/search?q={{key}},page={{page}}"
    except Exception as e:
        print(f"  [WARN] find_sort_search error: {type(e).__name__}: {str(e)[:80]}")
    if not search_pattern:
        search_pattern = "http://[DOMAIN]/search?q={{key}},page={{page}}"
    return sort_pattern, search_pattern

def build_subsource(parent_idx: int, sub_idx: int, url: str, vtype: int, conf: float,
                    feats: list, sort_url: str, search_url: str, link_source: str = 'a_tag'):
    """构建子源对象（脱敏后）"""
    rule_articles_default = ".item,.post,.article,article,.news-item,.entry"
    rule_nextpage_default = "a.next,a[rel=next],.pagination a:last-child,.page-next a,.next-page a"
    rule_title_default = ".title,h1,h2,h3,.post-title,.article-title"
    rule_image_default = "img.src,img[data-src],img[data-original],.thumb img,.cover img"
    rule_url_default = "a.href,a@href,.title a@href,.post-title a@href"
    rule_content_default = ".content,.article-content,.post-content,article,.entry-content"

    if vtype == 1:
        rule_articles_default = ".item,.post,.gallery-item,.photo-item,li:has(img),figure"
        rule_image_default = "img.src,img[data-src],img[data-original]"
        rule_content_default = ".content,.article-content,.post-content"
    elif vtype == 2:
        rule_articles_default = ".item,.post,.article,.video-item,.video-list li,.movie-item,.vod_list_item"
        rule_content_default = ".content,.article-content,.video-content,.play-content"

    return {
        "parent_source_index": parent_idx,
        "parent_sourceUrl_pattern": "http://[DOMAIN]/",
        "subsource": {
            "sourceName": f"源[{parent_idx}] - 子站[{sub_idx}]",
            "sourceUrl": sanitize_url(url),
            "sourceGroup": "导航拆分V2",
            "sourceComment": f"// 简化说明:SPA突破拆分,父源index={parent_idx},link_source={link_source}",
            "type": vtype,
            "enabled": True,
            "sortUrl": sort_url,
            "searchUrl": search_url,
            "ruleArticles": rule_articles_default,
            "ruleNextPage": rule_nextpage_default,
            "ruleTitle": rule_title_default,
            "ruleImage": rule_image_default,
            "ruleLink": rule_url_default,
            "ruleUrl": rule_url_default,
            "ruleContent": rule_content_default,
        },
        "confidence": conf,
        "detected_features": feats,
        "link_source": link_source,
    }

# ========== 单源5手段处理 ==========
def goto_with_retry(page, url, max_retries=2):
    """带重试的goto，先networkidle，超时降级domcontentloaded，再超时降级commit"""
    last_err = None
    for attempt in range(max_retries + 1):
        for wait_strategy in ['networkidle', 'domcontentloaded', 'commit']:
            try:
                page.goto(url, wait_until=wait_strategy, timeout=PAGE_TIMEOUT_MS)
                return True, wait_strategy, None
            except PWTimeout:
                last_err = 'PWTimeout:' + wait_strategy
                continue
            except Exception as e:
                last_err = f'{type(e).__name__}:{str(e)[:80]}'
                # 网络层错误直接break到下一次重试
                if 'ERR_TUNNEL' in str(e) or 'ERR_CONNECTION' in str(e) or 'ERR_NAME' in str(e):
                    break
                if 'ERR_HTTP2' in str(e) or 'ERR_PROTOCOL' in str(e):
                    break
                continue
        if attempt < max_retries:
            print(f"  [WARN] goto retry {attempt+1}/{max_retries} (last_err={last_err[:60]})")
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass
    return False, None, last_err


def process_spa_source(page, source_url, source_sort_url=''):
    """对单个SPA源执行5大手段，返回 (strategy_results, raw_strat1_links, raw_strat4_urls, raw_strat5_links)"""
    strategy_results = {
        "strategy1_scroll": {"scrolled": False, "links_count": 0, "links": []},
        "strategy2_vue_react": {"vue_app": None, "react_root": None, "nuxt_data": None, "initial_state": None},
        "strategy3_window_scan": {"data_keys": [], "total": 0},
        "strategy4_script_json": {"json_scripts": [], "inline_url_scripts": []},
        "strategy5_final_links": {"total_links": 0, "external_links": 0, "internal_links": 0, "links": []},
        "debug_page_info": {},
    }
    raw_strat1_links = []
    raw_strat4_urls = []
    raw_strat5_links = []

    # 添加 init_script 注入 stealth（在每个新文档加载前执行）
    try:
        page.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
            window.chrome = window.chrome || {};
        """)
    except Exception:
        pass

    # 访问源URL（重试机制 + 多种wait策略）
    success, wait_strategy, last_err = goto_with_retry(page, source_url, max_retries=2)
    if not success:
        print(f"  [ERROR] goto failed after retries: {last_err}")
        strategy_results['strategy1_scroll']['error'] = f'goto_failed: {last_err}'
        strategy_results['debug_page_info'] = {'goto_error': last_err}
        # 尝试从 sortUrl 提取候选URL作为fallback
        if source_sort_url and '::' in source_sort_url:
            print(f"  [FALLBACK] trying sortUrl candidates...")
            try:
                lines = source_sort_url.split('\n')
                for line in lines[:5]:
                    if '::' in line:
                        url_part = line.split('::', 1)[1].strip()
                        if url_part.startswith('http'):
                            url_part = url_part.replace('{{page}}', '1').replace('{page}', '1')
                            print(f"  [FALLBACK] trying candidate: {mask_url(url_part)}")
                            s2, w2, e2 = goto_with_retry(page, url_part, max_retries=1)
                            if s2:
                                source_url = url_part  # 切换到候选URL
                                success = True
                                break
            except Exception as e:
                print(f"  [FALLBACK] error: {type(e).__name__}: {str(e)[:80]}")
        if not success:
            return strategy_results, raw_strat1_links, raw_strat4_urls, raw_strat5_links

    print(f"  [INFO] goto OK with wait={wait_strategy}")

    # 额外等待 JS 执行
    try:
        page.wait_for_timeout(POST_GOTO_WAIT_MS)
    except Exception:
        pass

    # 注入去弹框JS
    try:
        page.evaluate("document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad,.adsbygoogle').forEach(e=>e.remove())")
    except Exception:
        pass

    # 调试：输出页面信息
    try:
        debug_info = page.evaluate(JS_DEBUG_PAGE_INFO)
        # 脱敏后保存
        debug_info_masked = {
            'title': sanitize_text(debug_info.get('title', ''), 60),
            'title_len': debug_info.get('title_len', 0),
            'html_len': debug_info.get('html_len', 0),
            'body_text_len': debug_info.get('body_text_len', 0),
            'body_text_preview_masked': sanitize_text(debug_info.get('body_text_preview', ''), 100),
            'a_count': debug_info.get('a_count', 0),
            'img_count': debug_info.get('img_count', 0),
            'script_count': debug_info.get('script_count', 0),
            'iframe_count': debug_info.get('iframe_count', 0),
            'form_count': debug_info.get('form_count', 0),
            'has_app_root': debug_info.get('has_app_root', False),
            'antibot_detected': debug_info.get('antibot_detected', []),
            'final_url_masked': mask_url(debug_info.get('final_url', '')),
            'ready_state': debug_info.get('ready_state', ''),
        }
        strategy_results['debug_page_info'] = debug_info_masked
        print(f"  [DEBUG] title_len={debug_info_masked['title_len']} html_len={debug_info_masked['html_len']} body_text_len={debug_info_masked['body_text_len']} a_count={debug_info_masked['a_count']} img={debug_info_masked['img_count']} script={debug_info_masked['script_count']} has_app_root={debug_info_masked['has_app_root']} antibot={debug_info_masked['antibot_detected']}")
        if debug_info_masked['html_len'] < 500:
            print(f"  [WARN] html_len very small ({debug_info_masked['html_len']}), page may be blocked/empty")
    except Exception as e:
        print(f"  [WARN] debug_info error: {type(e).__name__}: {str(e)[:80]}")

    # ========== 手段1：滚动触发3次 + 提取 a[href] ==========
    print(f"  [STRAT1] scrolling 5 times to trigger lazy load...")
    try:
        for i in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(SCROLL_WAIT_MS)
        r1 = page.evaluate(JS_STRATEGY1_SCROLL_AND_LINKS)
        links1 = r1.get('links', []) if r1 else []
        strategy_results['strategy1_scroll'] = {
            "scrolled": True,
            "links_count": len(links1),
            "links_preview_masked": [
                {"href": mask_url(l.get('href', '')), "text": sanitize_text(l.get('text', ''), 30)}
                for l in links1[:20]
            ]
        }
        raw_strat1_links = links1
        print(f"  [STRAT1] OK: links_count={len(links1)}")
    except Exception as e:
        strategy_results['strategy1_scroll'] = {"scrolled": False, "error": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"  [STRAT1] ERROR: {type(e).__name__}: {str(e)[:80]}")

    # ========== 手段2：Vue/React props 提取 ==========
    print(f"  [STRAT2] extracting Vue/React/Nuxt props...")
    try:
        r2 = page.evaluate(JS_STRATEGY2_VUE_REACT)
        strategy_results['strategy2_vue_react'] = mask_urls_in_data(r2) if r2 else {}
        if r2:
            vue = r2.get('vue_app')
            react = r2.get('react_root')
            nuxt = r2.get('nuxt_data')
            init = r2.get('initial_state')
            print(f"  [STRAT2] vue={'yes' if vue else 'no'} react={'yes' if react else 'no'} nuxt={'yes' if nuxt else 'no'} init_state={'yes' if init else 'no'}")
            if vue and isinstance(vue, dict) and vue.get('routes_preview'):
                print(f"  [STRAT2] vue routes_count={vue.get('routes_count', 0)} preview={vue.get('routes_preview')[:3]}")
    except Exception as e:
        strategy_results['strategy2_vue_react'] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"  [STRAT2] ERROR: {type(e).__name__}: {str(e)[:80]}")

    # ========== 手段3：扫描 window 对象所有数据 ==========
    print(f"  [STRAT3] scanning window object data keys...")
    try:
        r3 = page.evaluate(JS_STRATEGY3_WINDOW_SCAN)
        if r3:
            strategy_results['strategy3_window_scan'] = {
                "total": r3.get('total', 0),
                "data_keys": r3.get('data_keys', [])[:30]
            }
            print(f"  [STRAT3] OK: total_keys={r3.get('total', 0)}")
        else:
            strategy_results['strategy3_window_scan'] = {"total": 0, "data_keys": []}
    except Exception as e:
        strategy_results['strategy3_window_scan'] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"  [STRAT3] ERROR: {type(e).__name__}: {str(e)[:80]}")

    # ========== 手段4：扫描 script 标签的 JSON 数据 + 所有script文本URL + JS重定向目标 ==========
    print(f"  [STRAT4] scanning script[type=application/json] tags + inline URLs + redirects...")
    try:
        r4 = page.evaluate(JS_STRATEGY4_SCRIPT_JSON)
        if r4:
            json_scripts = r4.get('json_scripts', [])
            inline_url_scripts = r4.get('inline_url_scripts', [])
            redirect_targets = r4.get('redirect_targets', [])
            all_inline_urls = r4.get('all_inline_urls', [])
            # 收集所有URL（json_scripts的URL + all_inline_urls + redirect_targets中的http URL）
            for s in json_scripts:
                for u in (s.get('urls', []) or []):
                    if u and u.startswith('http'):
                        raw_strat4_urls.append(u)
            for u in all_inline_urls:
                if u and u.startswith('http'):
                    raw_strat4_urls.append(u)
            for t in redirect_targets:
                if t and t.startswith('http'):
                    raw_strat4_urls.append(t)
            # 去重
            raw_strat4_urls = list(dict.fromkeys(raw_strat4_urls))
            # 脱敏后输出
            strategy_results['strategy4_script_json'] = {
                "json_scripts": mask_urls_in_data(json_scripts[:10]),
                "json_scripts_count": len(json_scripts),
                "inline_url_scripts_count": len(inline_url_scripts),
                "redirect_targets_count": len(redirect_targets),
                "redirect_targets_masked": [mask_url(t) for t in redirect_targets[:10]],
                "total_urls_found": len(raw_strat4_urls),
                "urls_preview_masked": [mask_url(u) for u in raw_strat4_urls[:20]]
            }
            print(f"  [STRAT4] OK: json_scripts={len(json_scripts)} inline_with_urls={len(inline_url_scripts)} redirects={len(redirect_targets)} total_urls={len(raw_strat4_urls)}")
        else:
            strategy_results['strategy4_script_json'] = {"json_scripts": [], "inline_url_scripts_count": 0, "redirect_targets_count": 0, "total_urls_found": 0}
    except Exception as e:
        strategy_results['strategy4_script_json'] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"  [STRAT4] ERROR: {type(e).__name__}: {str(e)[:80]}")

    # ========== 手段5：提取所有可见链接（最终） ==========
    print(f"  [STRAT5] extracting all visible links after dynamic render...")
    try:
        r5 = page.evaluate(JS_STRATEGY5_ALL_LINKS)
        if r5:
            links5 = r5.get('links', [])
            raw_strat5_links = links5
            strategy_results['strategy5_final_links'] = {
                "total_links": r5.get('total_links', 0),
                "external_links": r5.get('external_links', 0),
                "internal_links": r5.get('internal_links', 0),
                "links_preview_masked": [
                    {
                        "href": mask_url(l.get('href', '')),
                        "host": l.get('host', ''),
                        "is_external": l.get('is_external', False),
                        "text": sanitize_text(l.get('text', ''), 30)
                    }
                    for l in links5[:30]
                ]
            }
            print(f"  [STRAT5] OK: total={r5.get('total_links',0)} external={r5.get('external_links',0)} internal={r5.get('internal_links',0)}")
        else:
            strategy_results['strategy5_final_links'] = {"total_links": 0, "external_links": 0, "internal_links": 0}
    except Exception as e:
        strategy_results['strategy5_final_links'] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"  [STRAT5] ERROR: {type(e).__name__}: {str(e)[:80]}")

    return strategy_results, raw_strat1_links, raw_strat4_urls, raw_strat5_links

# ========== 主流程 ==========
def main():
    print(f"[INFO] Loading V5 from {V5_PATH}")
    with open(V5_PATH, 'r', encoding='utf-8') as f:
        v5 = json.load(f)
    sources = v5.get('sources', [])
    print(f"[INFO] V5 sources total: {len(sources)}")
    print(f"[INFO] Target indices: {TARGET_INDICES}")

    result = {
        "analyzed_at": datetime.now().isoformat(),
        "total_input": len(TARGET_INDICES),
        "parent_sources": [],
        "total_subsources": 0,
        "by_type": {"type0": 0, "type1": 0, "type2": 0},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        # 父站 mobile context
        parent_ctx = browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent=MOBILE_UA,
            locale='zh-CN',
            extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9'},
            is_mobile=True,
            has_touch=True,
        )
        parent_ctx.set_default_timeout(PAGE_TIMEOUT_MS)
        parent_ctx.set_default_navigation_timeout(PAGE_TIMEOUT_MS)

        # 外链分析 context
        ext_ctx = browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent=MOBILE_UA,
            locale='zh-CN',
            is_mobile=True,
            has_touch=True,
        )
        ext_ctx.set_default_timeout(EXTERN_TIMEOUT_MS)
        ext_ctx.set_default_navigation_timeout(EXTERN_TIMEOUT_MS)

        for source_index in TARGET_INDICES:
            print(f"\n{'='*60}\n[INFO] === Processing SPA source idx={source_index} ===")
            if source_index >= len(sources):
                print(f"[WARN] idx={source_index} out of range, skip")
                result['parent_sources'].append({
                    "source_index": source_index,
                    "sourceUrl_pattern": "",
                    "error": "index_out_of_range",
                    "strategy_results": {},
                    "extracted_external_links": 0,
                    "subsources_created": 0,
                    "subsources": []
                })
                continue

            src = sources[source_index]
            source_url = src.get('sourceUrl', '')
            if not source_url or not source_url.startswith('http'):
                print(f"[WARN] idx={source_index} sourceUrl invalid, skip")
                result['parent_sources'].append({
                    "source_index": source_index,
                    "sourceUrl_pattern": sanitize_url(source_url),
                    "error": "invalid_source_url",
                    "strategy_results": {},
                    "extracted_external_links": 0,
                    "subsources_created": 0,
                    "subsources": []
                })
                continue

            t0 = time.time()
            parent_page = parent_ctx.new_page()
            strategy_results, raw_strat1_links, raw_strat4_urls, raw_strat5_links = process_spa_source(parent_page, source_url, src.get('sortUrl', ''))
            parent_page.close()
            elapsed_strat = time.time() - t0
            print(f"  [INFO] 5 strategies done in {elapsed_strat:.1f}s, strat1_links={len(raw_strat1_links)} strat4_urls={len(raw_strat4_urls)} strat5_links={len(raw_strat5_links)}")

            # 合并所有外链（手段1 + 手段5 的 a[href] + 手段4 的 script JSON URL）
            merged_external = merge_external_links(raw_strat1_links, raw_strat5_links, raw_strat4_urls, source_url)
            print(f"  [INFO] merged external links (after dedup+filter): {len(merged_external)}")

            # 对每个外链做类型识别并创建子源
            subsources = []
            sub_count = 0
            failed = 0
            for li in merged_external:
                if sub_count >= MAX_SUBSOURCE_PER_PARENT:
                    print(f"  [INFO] reached max subsource limit {MAX_SUBSOURCE_PER_PARENT}, stop")
                    break
                ext_url = li.get('href', '')
                if not ext_url:
                    continue
                host = li.get('host', '')
                link_source = li.get('source', 'a_tag')

                ext_page = ext_ctx.new_page()
                try:
                    ext_page.goto(ext_url, wait_until='domcontentloaded', timeout=EXTERN_TIMEOUT_MS)
                except PWTimeout:
                    print(f"  [WARN] ext link timeout host={host} src={link_source}")
                    ext_page.close()
                    failed += 1
                    continue
                except Exception as e:
                    print(f"  [WARN] ext link goto error: {type(e).__name__}: {str(e)[:80]}")
                    ext_page.close()
                    failed += 1
                    continue

                # 简单等待1s让动态内容加载
                try:
                    ext_page.wait_for_timeout(1000)
                except Exception:
                    pass

                vtype, conf, feats, detail = detect_type_features(ext_page)
                sort_url, search_url = find_sort_search_url(ext_page, ext_url)
                ext_page.close()

                if conf < CONFIDENCE_THRESHOLD:
                    print(f"  [SKIP] low conf={conf:.2f} host={host} feats={feats[:2]}")
                    failed += 1
                    continue

                sub_count += 1
                sub = build_subsource(source_index, sub_count, ext_url, vtype, conf, feats, sort_url, search_url, link_source)
                subsources.append(sub)
                result['by_type'][f"type{vtype}"] = result['by_type'].get(f"type{vtype}", 0) + 1
                print(f"  [OK] sub#{sub_count} type={vtype} conf={conf:.2f} src={link_source} feats={feats[:2]}")

            # 记录父站结果
            parent_result = {
                "source_index": source_index,
                "sourceUrl_pattern": sanitize_url(source_url),
                "parent_enabled": src.get('enabled', False),
                "parent_type": src.get('type', 0),
                "strategy_results": strategy_results,
                "merged_external_links_count": len(merged_external),
                "extracted_external_links": len(merged_external),
                "subsources_created": sub_count,
                "failed_external_links": failed,
                "subsources": subsources,
                "elapsed_sec": round(time.time() - t0, 1),
            }
            result['parent_sources'].append(parent_result)
            print(f"  [INFO] parent idx={source_index} done: subsources={sub_count} failed={failed} elapsed={parent_result['elapsed_sec']}s")

        browser.close()

    result['total_subsources'] = sum(len(p.get('subsources', [])) for p in result['parent_sources'])

    # 输出文件
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*60}")
    print(f"[DONE] Output written: {OUT_PATH}")
    print(f"[SUMMARY] parent_sources={len(result['parent_sources'])} total_subsources={result['total_subsources']}")
    print(f"[SUMMARY] by_type={result['by_type']}")
    for p in result['parent_sources']:
        print(f"  idx={p['source_index']}: external={p.get('extracted_external_links',0)} subsources={p.get('subsources_created',0)} failed={p.get('failed_external_links',0)} elapsed={p.get('elapsed_sec',0)}s")


if __name__ == '__main__':
    main()
