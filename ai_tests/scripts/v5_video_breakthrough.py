# -*- coding: utf-8 -*-
"""
V5 视频源88个深度突破 (Phase 2-A-V2)
对88个 no_video_evidence 源应用6大突破手段
"""
import json, re, sys, time, os, argparse
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DEEPFIX_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deepfix.json'
V5_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_final.json'
OUT_DIR = r'f:\myself\github\WeAgentChat\temp\legado\output\rss'
PROGRESS_JSON = os.path.join(OUT_DIR, 'v5_video_breakthrough.progress.json')

# ========== 脱敏 ==========
def mask_url(u):
    if not u or not isinstance(u, str): return u
    return re.sub(r'https?://[^/\s"\']+', 'http://[DOMAIN]', u)

def mask_urls_in_data(obj):
    """递归脱敏所有 URL 字符串"""
    if isinstance(obj, str):
        if re.search(r'https?://', obj):
            # 只脱敏URL部分，保留其他文本
            return re.sub(r'https?://[^/\s"\'\\]+', 'http://[DOMAIN]', obj)
        return obj
    elif isinstance(obj, list):
        return [mask_urls_in_data(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: mask_urls_in_data(v) for k, v in obj.items()}
    return obj

# ========== JS 探测代码 ==========
JS_STRATEGY1_SCROLL = """
() => {
  const el = document.querySelector('[class*=player],[id*=player],video,.video-wrap,.player,#player,#video,.play-box');
  if (el) { try { el.scrollIntoView(); } catch(e){} return 'scrolled'; }
  return 'no_player_element';
}
"""

JS_STRATEGY2_CLICK_PLAY = """
() => {
  const playBtn = document.querySelector('[class*=play-btn],[class*=play-button],[onclick*=play],.vjs-big-play-button,.play-ico,.btn-play,[class*=btn-play],a.play,#play,.playBtn');
  if (playBtn) { try { playBtn.click(); } catch(e){} return 'clicked'; }
  return 'no_play_button';
}
"""

JS_STRATEGY3_IFRAME = """
() => {
  const iframes = Array.from(document.querySelectorAll('iframe'));
  const iframe_data = iframes.map(f => ({
    src: f.src || '',
    id: f.id || '',
    class: f.className || '',
    has_player_keyword: /player|video|m3u8|mp4|play/i.test(f.src || '')
  }));
  return iframe_data;
}
"""

JS_STRATEGY4_SCRIPT_JSON = """
() => {
  const scripts = Array.from(document.querySelectorAll('script'));
  const video_data = [];
  scripts.forEach(s => {
    const text = s.textContent || '';
    if (text.length < 20) return;
    const m3u8_match = text.match(/["'](https?:\\/\\/[^"']+\\.m3u8[^"']*)["']/);
    const mp4_match = text.match(/["'](https?:\\/\\/[^"']+\\.mp4[^"']*)["']/);
    // json_url 必须以 http 开头（排除测试URL如 www.test.cn）
    let json_url = null;
    const json_match = text.match(/"url"\\s*:\\s*["'](https?:\\/\\/[^"']+)["']/);
    if (json_match) json_url = json_match[1];
    const b64_match = text.match(/["']([A-Za-z0-9+/=]{50,})["']/);
    if (m3u8_match || mp4_match || json_url || b64_match) {
      video_data.push({
        m3u8: m3u8_match ? m3u8_match[1] : null,
        mp4: mp4_match ? mp4_match[1] : null,
        json_url: json_url,
        has_b64: !!b64_match,
        script_size: text.length
      });
    }
  });
  return video_data;
}
"""

JS_STRATEGY5_EVAL = """
() => {
  const scripts = Array.from(document.querySelectorAll('script'));
  const eval_data = [];
  scripts.forEach(s => {
    const text = s.textContent || '';
    if (text.length < 20) return;
    if (/eval\\(|atob\\(|unescape\\(|decodeURIComponent\\(/i.test(text)) {
      eval_data.push({
        has_eval: /eval\\(/i.test(text),
        has_atob: /atob\\(/i.test(text),
        has_unescape: /unescape\\(/i.test(text),
        script_size: text.length,
        preview: text.slice(0, 200)
      });
    }
  });
  return eval_data;
}
"""

JS_DETECT_VIDEO = """
() => {
  const videos = Array.from(document.querySelectorAll('video'));
  const video_srcs = videos.map(v => {
    let src = v.src || v.getAttribute('src') || '';
    if (!src) {
      const s = v.querySelector('source');
      if (s) src = s.src || s.getAttribute('src') || '';
    }
    return src;
  }).filter(Boolean);
  const iframes = Array.from(document.querySelectorAll('iframe'));
  const iframe_player = iframes.filter(f => /player|video|m3u8|mp4|play/i.test(f.src || '')).map(f => f.src);
  const html = document.documentElement.outerHTML;
  const m3u8_in_html = (html.match(/https?:\\/\\/[^"'\\s]+\\.m3u8[^"'\\s]*/g) || []).slice(0, 5);
  const mp4_in_html = (html.match(/https?:\\/\\/[^"'\\s]+\\.mp4[^"'\\s]*/g) || []).slice(0, 5);
  // 检测播放器JS
  const player_js = {
    videojs: /videojs|video-js/i.test(html),
    jwplayer: /jwplayer/i.test(html),
    dplayer: /dplayer|dp\.constructor/i.test(html),
    ckplayer: /ckplayer/i.test(html),
    flowplayer: /flowplayer/i.test(html),
    hls: /hls\\.js|Hls\\.isSupported/i.test(html)
  };
  return {
    video_tag_count: videos.length,
    video_src: video_srcs,
    iframe_count: iframes.length,
    iframe_player: iframe_player,
    m3u8_in_html: m3u8_in_html,
    mp4_in_html: mp4_in_html,
    player_js: player_js
  };
}
"""

# ========== 详情页提取 ==========
DETAIL_PATTERNS = [
    # 详情页/play页模式
    r'href="(\/vod[^"]*play[^"]*\.html)"',
    r'href="(\/vodplay[^"]*\.html)"',
    r'href="(\/v_play[^"]*\.html)"',
    r'href="(\/play[^"]*\.html)"',
    r'href="(\/video[^"]*\.html)"',
    r'href="(\/detail[^"]*\.html)"',
    r'href="(\/vod-detail[^"]*\.html)"',
    r'href="(\/vod-show-id-\d+[^"]*\.html)"',
    r'href="(\/vod-detail-id-\d+[^"]*\.html)"',
    r'href="(\/movie[^"]*\.html)"',
    r'href="(\/index[^"]*\.html)"',
    r'href="(\/[a-z]+\/\d+[^"]*\.html)"',
    r'href="([^"]*vod-id-\d+[^"]*)"',
    r'href="([^"]*article-id-\d+[^"]*)"',
    r'href="([^"]*movie-id-\d+[^"]*)"',
    r'href="(\/[a-z]+\/[a-z]+-\d+[^"]*\.html)"',
    # ?m=vod-detail-id-XXX 类型
    r'href="([^"]*m=vod-detail-id-\d+[^"]*)"',
    r'href="([^"]*m=vod-play-id-\d+[^"]*)"',
    r'href="([^"]*m=vod-play[^"]*)"',
    # ThinkPHP 风格：/index.php/vod/detail/id/123, /vod/show/id/123
    r'href="([^"]*\/vod\/detail\/id\/\d+[^"]*)"',
    r'href="([^"]*\/vod\/show\/id\/\d+[^"]*)"',
    r'href="([^"]*\/vod\/play\/id\/\d+[^"]*)"',
    r'href="([^"]*\/index\.php\/vod\/\w+\/id\/\d+[^"]*)"',
    r'href="([^"]*\/index\.php\/article\/\d+[^"]*)"',
    # 通用详情页：含数字ID的 .html
    r'href="(\/[^"]*\d{4,}[^"]*\.html)"',
    # 带查询参数的详情页 ?id=123 / ?vod=123
    r'href="([^"]*\?id=\d+[^"]*)"',
    r'href="([^"]*\?vod=\d+[^"]*)"',
    r'href="([^"]*\?aid=\d+[^"]*)"',
    r'href="([^"]*\?aid=\d+&[^"]*)"',
]

# 分类页模式（用于从 sortUrl 或主页中提取第一个分类入口）
CATEGORY_PATTERNS = [
    r'href="([^"]*m=vod-type-id-\d+[^"]*)"',
    r'href="([^"]*vodtype\/\d+[^"]*\.html)"',
    r'href="([^"]*vod-type\/\d+[^"]*\.html)"',
    r'href="([^"]*\/list\/\d+[^"]*\.html)"',
    r'href="([^"]*\/category\/\d+[^"]*\.html)"',
    r'href="([^"]*\/type\/\d+[^"]*\.html)"',
    r'href="([^"]*\/show\/\d+[^"]*\.html)"',
    r'href="([^"]*m=vod-type[^"]*)"',
]

def extract_detail_url(list_html, base_url):
    for p in DETAIL_PATTERNS:
        m = re.search(p, list_html, re.IGNORECASE)
        if m:
            return urljoin(base_url, m.group(1))
    # 退而求其次：找任何含数字ID的.html链接（排除列表/分类页）
    candidates = re.findall(r'href="([^"]+\.html)"', list_html)
    skip_kw = ['search', 'sort', 'page', 'about', 'contact', 'help', 'login', 'register',
               'vod-type', 'vodtype', 'vod-show', 'category', '/list/', '/type/', '/show/']
    for c in candidates:
        cl = c.lower()
        if any(k in cl for k in skip_kw): continue
        if re.search(r'\d{3,}', c):
            return urljoin(base_url, c)
    return None

def extract_first_category_from_sorturl(sort_url, base_url):
    """从 sortUrl 字段中提取第一个分类URL
    sortUrl 格式: '分类名1::URL1\n分类名2::URL2\n...'
    或: '@js:...'(JS代码，跳过)
    或: '<js>...</js>'(JS代码，跳过)
    """
    if not sort_url: return None
    if sort_url.startswith('@js:') or sort_url.startswith('<js>'): return None
    # 提取第一个 ::URL
    lines = sort_url.split('\n')
    for line in lines:
        if '::' in line:
            url_part = line.split('::', 1)[1].strip()
            if url_part and not url_part.startswith('@js') and not url_part.startswith('<js'):
                # 替换 {{page}} 占位符为 1
                url_part = url_part.replace('{{page}}', '1').replace('${page}', '1').replace('{page}', '1')
                # 拼接 base_url
                if url_part.startswith('http'):
                    return url_part
                elif url_part.startswith('/'):
                    return urljoin(base_url, url_part)
                else:
                    return urljoin(base_url, '/' + url_part)
    return None

def extract_first_category_from_html(html, base_url):
    """从主页HTML中提取第一个分类URL"""
    for p in CATEGORY_PATTERNS:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            return urljoin(base_url, m.group(1))
    return None

def extract_detail_id(detail_url):
    if not detail_url: return None
    m = re.search(r'/(\d+)(?:\.html|/|$)', detail_url)
    if m: return m.group(1)
    m = re.search(r'[?&]id=(\d+)', detail_url)
    if m: return m.group(1)
    m = re.search(r'-(\d+)\.html', detail_url)
    if m: return m.group(1)
    return None

# ========== 生成 ruleContent ==========
def gen_rule_content(strategy, evidence):
    if strategy == 'strategy1_wait_scroll' or strategy == 'strategy2_click_play':
        return "@js:var v=doc.selectFirst('video');result=v?(v.attr('src')||(v.selectFirst('source')?v.selectFirst('source').attr('src'):'')):''"
    elif strategy == 'strategy3_iframe_nested':
        return "@js:var f=doc.selectFirst('iframe[src*=player]')||doc.selectFirst('iframe');result=f?f.absUrl('src'):''"
    elif strategy == 'strategy4_script_json':
        if evidence.get('m3u8_url'):
            return "@js:String(doc.html()).match(/https?:\\/\\/[^\"']+\\.m3u8[^\"']*/)?.[0]||''"
        elif evidence.get('mp4_url'):
            return "@js:String(doc.html()).match(/https?:\\/\\/[^\"']+\\.mp4[^\"']*/)?.[0]||''"
        else:
            return "@js:String(doc.html()).match(/https?:\\/\\/[^\"']+(m3u8|mp4)[^\"']*/)?.[0]||''"
    elif strategy == 'strategy5_eval_decode':
        return "@js:var m=String(doc.html()).match(/eval\\(([\\s\\S]+?)\\)\\s*;?/);if(m){try{result=eval(m[1])}catch(e){result=''}}else{result=''}"
    elif strategy == 'strategy6_json_api':
        api_url = evidence.get('api_url', '')
        if api_url:
            masked = mask_url(api_url)
            return f"@js:var id=baseUrl.match(/(\\\\d+)/)?.[0]||'';result=java.net.URL('{masked}'.replace('{{id}}',id)).getText()"
        return "@js:result=''"
    return ''

# ========== 单源处理 ==========
def process_source(page, source):
    """对单个源应用6大手段，返回 (success_strategies, evidence, new_fields)"""
    source_url = source.get('sourceUrl', '')
    source_index = source.get('_source_index', -1)
    evidence = {
        'strategy1_result': 'pending',
        'strategy2_result': 'pending',
        'strategy3_result': 'pending',
        'strategy4_result': 'pending',
        'strategy5_result': 'pending',
        'strategy6_result': 'pending',
    }
    success_strategies = []
    new_fields = {}

    if not source_url or not source_url.startswith('http'):
        for k in evidence:
            evidence[k] = 'invalid_source_url'
        return success_strategies, evidence, new_fields

    # Step 1: 访问列表页
    try:
        page.goto(source_url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        list_html = page.content()
    except Exception as e:
        for k in evidence:
            evidence[k] = f'list_load_error: {type(e).__name__}'
        return success_strategies, evidence, new_fields

    # Step 2: 提取详情页
    detail_url = extract_detail_url(list_html, source_url)
    if not detail_url:
        # 主页找不到详情页 -> 尝试从 sortUrl 提取第一个分类入口
        sort_url = source.get('sortUrl', '')
        cat_url = extract_first_category_from_sorturl(sort_url, source_url)
        if not cat_url:
            # sortUrl为空或是JS -> 从主页HTML找分类链接
            cat_url = extract_first_category_from_html(list_html, source_url)
        if cat_url:
            evidence['category_url_tried'] = mask_url(cat_url)
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(2000)
                cat_html = page.content()
                detail_url = extract_detail_url(cat_html, cat_url)
            except Exception as e:
                evidence['category_load_error'] = f'{type(e).__name__}: {str(e)[:100]}'
        if not detail_url:
            # 最后尝试访问详情页路径模式：拼 sourceUrl + /vod-type 或 /vod-search 等
            # 不再尝试，直接失败
            pass
    evidence['detail_url_extracted'] = bool(detail_url)
    if not detail_url:
        for k in evidence:
            if evidence[k] == 'pending':
                evidence[k] = 'no_detail_url_found'
        return success_strategies, evidence, new_fields
    evidence['detail_url_masked'] = mask_url(detail_url)

    # Step 3: 访问详情页
    try:
        page.goto(detail_url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
    except Exception as e:
        for k in evidence:
            if evidence[k] == 'pending':
                evidence[k] = f'detail_load_error: {type(e).__name__}'
        return success_strategies, evidence, new_fields

    detail_id = extract_detail_id(detail_url)
    evidence['detail_id'] = detail_id

    # ========== 手段1：等待15s + 滚动到 player 区域 ==========
    try:
        page.wait_for_timeout(15000)  # 等待15s让视频懒加载
        scroll_result = page.evaluate(JS_STRATEGY1_SCROLL)
        evidence['strategy1_scroll'] = scroll_result
        if scroll_result == 'scrolled':
            page.wait_for_timeout(2000)
        video_info = page.evaluate(JS_DETECT_VIDEO)
        evidence['strategy1_video_info'] = mask_urls_in_data(video_info)
        if video_info.get('video_tag_count', 0) > 0 and video_info.get('video_src'):
            evidence['strategy1_result'] = 'video_found'
            evidence['video_found_at'] = 'strategy1_wait_scroll'
            evidence['video_src'] = mask_urls_in_data(video_info.get('video_src', []))
            success_strategies.append('strategy1_wait_scroll')
            new_fields['ruleContent'] = gen_rule_content('strategy1_wait_scroll', evidence)
            return success_strategies, evidence, new_fields
        if video_info.get('m3u8_in_html'):
            evidence['strategy1_result'] = 'm3u8_in_html'
            evidence['video_found_at'] = 'strategy1_wait_scroll'
            evidence['m3u8_url'] = mask_url(video_info['m3u8_in_html'][0])
            success_strategies.append('strategy1_wait_scroll')
            new_fields['ruleContent'] = gen_rule_content('strategy4_script_json', evidence)
            return success_strategies, evidence, new_fields
        evidence['strategy1_result'] = 'no_video_tag'
    except Exception as e:
        evidence['strategy1_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    # ========== 手段2：点击播放按钮 ==========
    try:
        click_result = page.evaluate(JS_STRATEGY2_CLICK_PLAY)
        evidence['strategy2_click'] = click_result
        if click_result == 'clicked':
            page.wait_for_timeout(5000)
            video_info = page.evaluate(JS_DETECT_VIDEO)
            evidence['strategy2_video_info'] = mask_urls_in_data(video_info)
            if video_info.get('video_tag_count', 0) > 0 and video_info.get('video_src'):
                evidence['strategy2_result'] = 'video_found'
                evidence['video_found_at'] = 'strategy2_click_play'
                evidence['video_src'] = mask_urls_in_data(video_info.get('video_src', []))
                success_strategies.append('strategy2_click_play')
                new_fields['ruleContent'] = gen_rule_content('strategy2_click_play', evidence)
                return success_strategies, evidence, new_fields
            if video_info.get('m3u8_in_html'):
                evidence['strategy2_result'] = 'm3u8_in_html'
                evidence['video_found_at'] = 'strategy2_click_play'
                evidence['m3u8_url'] = mask_url(video_info['m3u8_in_html'][0])
                success_strategies.append('strategy2_click_play')
                new_fields['ruleContent'] = gen_rule_content('strategy4_script_json', evidence)
                return success_strategies, evidence, new_fields
            evidence['strategy2_result'] = 'clicked_but_no_video'
        else:
            evidence['strategy2_result'] = 'no_play_button'
    except Exception as e:
        evidence['strategy2_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    # ========== 手段3：iframe 嵌套 ==========
    try:
        iframe_data = page.evaluate(JS_STRATEGY3_IFRAME)
        evidence['strategy3_iframes'] = mask_urls_in_data(iframe_data)
        player_iframes = [f for f in iframe_data if f.get('has_player_keyword')]
        if player_iframes:
            # 尝试进入第一个 player iframe
            try:
                iframe_src = player_iframes[0].get('src', '')
                if iframe_src:
                    frame = page.frame_locator(f'iframe[src*="{urlparse(iframe_src).path[:30]}"]')
                    # 在iframe内检测视频特征
                    try:
                        iframe_video_info = frame.locator('video').first.count()
                        if iframe_video_info > 0:
                            evidence['strategy3_result'] = 'iframe_video_found'
                            evidence['video_found_at'] = 'strategy3_iframe_nested'
                            evidence['iframe_player_src'] = mask_url(iframe_src)
                            success_strategies.append('strategy3_iframe_nested')
                            new_fields['ruleContent'] = gen_rule_content('strategy3_iframe_nested', evidence)
                            return success_strategies, evidence, new_fields
                    except Exception:
                        pass
                    # iframe 本身就是player
                    evidence['strategy3_result'] = 'iframe_player_found'
                    evidence['video_found_at'] = 'strategy3_iframe_nested'
                    evidence['iframe_player_src'] = mask_url(iframe_src)
                    success_strategies.append('strategy3_iframe_nested')
                    new_fields['ruleContent'] = gen_rule_content('strategy3_iframe_nested', evidence)
                    return success_strategies, evidence, new_fields
                evidence['strategy3_result'] = 'iframe_no_src'
            except Exception as e:
                evidence['strategy3_result'] = f'iframe_enter_error: {type(e).__name__}'
        else:
            evidence['strategy3_result'] = 'no_player_iframe'
    except Exception as e:
        evidence['strategy3_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    # ========== 手段4：script JSON 扫描 ==========
    try:
        script_data = page.evaluate(JS_STRATEGY4_SCRIPT_JSON)
        evidence['strategy4_scripts'] = mask_urls_in_data(script_data)
        m3u8_urls = [s.get('m3u8') for s in script_data if s.get('m3u8')]
        mp4_urls = [s.get('mp4') for s in script_data if s.get('mp4')]
        json_urls = [s.get('json_url') for s in script_data if s.get('json_url')]
        if m3u8_urls:
            evidence['strategy4_result'] = 'm3u8_in_script'
            evidence['video_found_at'] = 'strategy4_script_json'
            evidence['m3u8_url'] = mask_url(m3u8_urls[0])
            success_strategies.append('strategy4_script_json')
            new_fields['ruleContent'] = gen_rule_content('strategy4_script_json', evidence)
            return success_strategies, evidence, new_fields
        if mp4_urls:
            evidence['strategy4_result'] = 'mp4_in_script'
            evidence['video_found_at'] = 'strategy4_script_json'
            evidence['mp4_url'] = mask_url(mp4_urls[0])
            success_strategies.append('strategy4_script_json')
            new_fields['ruleContent'] = gen_rule_content('strategy4_script_json', evidence)
            return success_strategies, evidence, new_fields
        if json_urls:
            evidence['strategy4_result'] = 'json_url_in_script'
            evidence['video_found_at'] = 'strategy4_script_json'
            evidence['json_url'] = mask_url(json_urls[0])
            success_strategies.append('strategy4_script_json')
            new_fields['ruleContent'] = gen_rule_content('strategy4_script_json', evidence)
            return success_strategies, evidence, new_fields
        evidence['strategy4_result'] = 'no_json'
    except Exception as e:
        evidence['strategy4_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    # ========== 手段5：eval 调用检测 ==========
    try:
        eval_data = page.evaluate(JS_STRATEGY5_EVAL)
        evidence['strategy5_eval'] = mask_urls_in_data(eval_data)
        has_eval = any(s.get('has_eval') for s in eval_data)
        has_atob = any(s.get('has_atob') for s in eval_data)
        if has_eval or has_atob:
            # 尝试在控制台执行获取真实URL
            try:
                # 简单尝试：用 atob 解码所有 base64 字符串
                decoded = page.evaluate("""
                () => {
                  const scripts = Array.from(document.querySelectorAll('script'));
                  let found = [];
                  scripts.forEach(s => {
                    const text = s.textContent || '';
                    const b64matches = text.match(/['"]([A-Za-z0-9+/=]{50,})['"]/g) || [];
                    b64matches.forEach(m => {
                      try {
                        const b64 = m.replace(/['"]/g, '');
                        const dec = atob(b64);
                        if (/m3u8|mp4|http/i.test(dec)) {
                          found.push(dec.slice(0, 300));
                        }
                      } catch(e){}
                    });
                  });
                  return found.slice(0, 3);
                }
                """)
                if decoded:
                    evidence['strategy5_decoded'] = mask_urls_in_data(decoded)
                    evidence['strategy5_result'] = 'eval_decoded'
                    evidence['video_found_at'] = 'strategy5_eval_decode'
                    # 找到解码后的URL
                    for d in decoded:
                        m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', d) or re.search(r'https?://[^\s"\']+\.mp4[^\s"\']*', d)
                        if m:
                            evidence['m3u8_url'] = mask_url(m.group(0))
                            break
                    success_strategies.append('strategy5_eval_decode')
                    new_fields['ruleContent'] = gen_rule_content('strategy5_eval_decode', evidence)
                    return success_strategies, evidence, new_fields
                evidence['strategy5_result'] = 'eval_found_but_no_url'
            except Exception as e:
                evidence['strategy5_result'] = f'eval_decode_error: {type(e).__name__}'
        else:
            evidence['strategy5_result'] = 'no_eval'
    except Exception as e:
        evidence['strategy5_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    # ========== 手段6：JSON API 端点 ==========
    try:
        if not detail_id:
            evidence['strategy6_result'] = 'no_detail_id'
        else:
            # 探测常见API路径（缩短超时3s，减少到4个核心API）
            api_paths = [
                f'/api/video?id={detail_id}',
                f'/getPlayUrl?id={detail_id}',
                f'/api.php?xml={detail_id}',
                f'/player/api.php?id={detail_id}',
            ]
            found_api = False
            for path in api_paths:
                api_url = urljoin(source_url, path)
                try:
                    resp = page.request.get(api_url, timeout=3000)
                    if resp.status == 200:
                        body = resp.text()
                        if body:
                            # 检测JSON中的m3u8/mp4
                            m_m3u8 = re.search(r'(https?://[^\s"\'\\]+\.m3u8[^\s"\'\\]*)', body)
                            m_mp4 = re.search(r'(https?://[^\s"\'\\]+\.mp4[^\s"\'\\]*)', body)
                            m_url = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', body)
                            if m_m3u8 or m_mp4 or m_url:
                                evidence['strategy6_result'] = 'api_url_found'
                                evidence['video_found_at'] = 'strategy6_json_api'
                                evidence['api_url'] = mask_url(api_url)
                                if m_m3u8:
                                    evidence['m3u8_url'] = mask_url(m_m3u8.group(1))
                                elif m_mp4:
                                    evidence['mp4_url'] = mask_url(m_mp4.group(1))
                                elif m_url:
                                    evidence['json_url'] = mask_url(m_url.group(1))
                                evidence['api_path'] = path
                                success_strategies.append('strategy6_json_api')
                                new_fields['ruleContent'] = gen_rule_content('strategy6_json_api', evidence)
                                found_api = True
                                break
                except Exception:
                    continue
            if not found_api:
                evidence['strategy6_result'] = 'api_no_match'
    except Exception as e:
        evidence['strategy6_result'] = f'error: {type(e).__name__}: {str(e)[:100]}'

    return success_strategies, evidence, new_fields


# ========== 主流程 ==========
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=88)
    parser.add_argument('--batch', type=int, default=0)  # 批次号
    args = parser.parse_args()

    # 加载数据
    with open(DEEPFIX_JSON, 'r', encoding='utf-8') as f:
        deepfix = json.load(f)
    with open(V5_JSON, 'r', encoding='utf-8') as f:
        v5 = json.load(f)

    nve_list = [f for f in deepfix['failed'] if f.get('result_type') == 'no_video_evidence']
    print(f'[INFO] Total no_video_evidence sources: {len(nve_list)}')

    start = max(0, args.start)
    end = min(args.end, len(nve_list))
    targets = nve_list[start:end]
    print(f'[INFO] Processing batch #{args.batch}: indexes [{start}, {end}), count={len(targets)}')

    # 加载已有进度
    progress = {'batches': {}}
    if os.path.exists(PROGRESS_JSON):
        try:
            with open(PROGRESS_JSON, 'r', encoding='utf-8') as f:
                progress = json.load(f)
        except Exception:
            pass

    batch_results = []
    by_strategy_count = {
        'strategy1_wait_scroll': 0,
        'strategy2_click_play': 0,
        'strategy3_iframe_nested': 0,
        'strategy4_script_json': 0,
        'strategy5_eval_decode': 0,
        'strategy6_json_api': 0,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            viewport={'width': 390, 'height': 844},
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        for i, nve_item in enumerate(targets):
            source_index = nve_item['source_index']
            # 从 V5 取完整字段
            if source_index < len(v5['sources']):
                source = dict(v5['sources'][source_index])
            else:
                source = {}
            source['_source_index'] = source_index

            print(f'\n[Batch {args.batch} | {i+1}/{len(targets)}] source_index={source_index} ...')
            t0 = time.time()
            try:
                success_strategies, evidence, new_fields = process_source(page, source)
            except Exception as e:
                success_strategies = []
                evidence = {'error': f'{type(e).__name__}: {str(e)[:200]}'}
                new_fields = {}

            elapsed = time.time() - t0
            source_url_pattern = mask_url(source.get('sourceUrl', ''))
            item = {
                'source_index': source_index,
                'sourceUrl_pattern': source_url_pattern,
                'success_strategy': success_strategies,
                'new_fields': new_fields,
                'evidence': evidence,
                'elapsed_sec': round(elapsed, 1),
            }
            batch_results.append(item)

            for s in success_strategies:
                by_strategy_count[s] = by_strategy_count.get(s, 0) + 1

            status = 'SUCCESS' if success_strategies else 'FAILED'
            print(f'  -> {status} strategies={success_strategies} elapsed={elapsed:.1f}s')

            # 每源结束后立即持久化进度
            progress['batches'][f'batch_{args.batch}'] = {
                'start': start,
                'end': end,
                'processed': i + 1,
                'total': len(targets),
                'success_count': sum(1 for r in batch_results if r['success_strategy']),
                'failed_count': sum(1 for r in batch_results if not r['success_strategy']),
                'by_strategy': by_strategy_count,
                'last_updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            try:
                with open(PROGRESS_JSON, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        browser.close()

    # 输出本批结果
    batch_out = {
        'batch': args.batch,
        'start': start,
        'end': end,
        'total': len(targets),
        'success_count': sum(1 for r in batch_results if r['success_strategy']),
        'failed_count': sum(1 for r in batch_results if not r['success_strategy']),
        'by_strategy': by_strategy_count,
        'results': batch_results,
    }
    batch_file = os.path.join(OUT_DIR, f'v5_video_breakthrough_batch_{args.batch}.json')
    with open(batch_file, 'w', encoding='utf-8') as f:
        json.dump(batch_out, f, ensure_ascii=False, indent=2)
    print(f'\n[DONE Batch {args.batch}] {batch_file}')
    print(f'  success={batch_out["success_count"]} failed={batch_out["failed_count"]}')
    print(f'  by_strategy={by_strategy_count}')


if __name__ == '__main__':
    main()
