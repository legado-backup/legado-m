# -*- coding: utf-8 -*-
"""
v5_hard_source_fix.py
对67个难点源（V4）深度处理：
- CF盾源：尝试 google_cache / JS注入 / 直接等待 三种破盾策略
- 登录源：检测登录入口和字段，构建 loginUrl/loginUi/loginJs
- 弹框源：注入通用去弹框 JS，写入 sourceComment
- enabled=false 源：访问成功且页面正常则恢复 enabled=true
输出已脱敏的 v5_hard_source_fix.json
"""
import json
import time
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Error as PWError

# ============ 配置 ============
V4_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v4.json"
CLASSIFICATION_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_classification.json"
OUTPUT_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_hard_source_fix.json"
PROGRESS_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_hard_source_fix.progress.txt"
SUMMARY_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_hard_source_fix.summary.txt"

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIEWPORT = {"width": 375, "height": 667}
TIMEOUT_MS = 30000

# 通用去弹框 JS（覆盖常见 modal/popup/overlay/mask/dialog 等）
REMOVE_POPUP_JS = r"""
(() => {
  let removed = 0;
  document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.ad-popup,.vip-modal,.login-modal,.notice,.alert,[class*=popup],[class*=modal]').forEach(function(e){
    try {
      const cs = getComputedStyle(e);
      if (cs.position === 'fixed' || (parseInt(cs.zIndex || '0', 10) > 999)) {
        e.remove();
        removed++;
      }
    } catch(err) {}
  });
  try { window.alert = function(){}; } catch(e) {}
  try { window.confirm = function(){return true;}; } catch(e) {}
  try { window.prompt = function(){return '';}; } catch(e) {}
  return removed;
})()
"""

# CF 检测 JS：判断页面是否仍在 CF 拦截页
CF_DETECT_JS = r"""
(() => {
  const title = (document.title || '').toLowerCase();
  const bodyText = (document.body ? document.body.innerText : '').slice(0, 500).toLowerCase();
  const isCf = title.indexOf('just a moment') >= 0
            || title.indexOf('cloudflare') >= 0
            || bodyText.indexOf('just a moment') >= 0
            || bodyText.indexOf('checking your browser') >= 0
            || bodyText.indexOf('cf-browser-verification') >= 0;
  return { is_cf: isCf, title: document.title || '' };
})()
"""

# 登录入口检测 JS
LOGIN_LINK_DETECT_JS = r"""
(() => {
  const links = Array.from(document.querySelectorAll('a[href]'));
  const hits = [];
  for (const a of links) {
    const href = a.href || '';
    const text = (a.textContent || '').trim().slice(0, 30);
    if (/login|signin|sign-in|log-in|登录|登入|登錄/i.test(href + ' ' + text)) {
      hits.push({ href: href, text: text });
    }
    if (hits.length >= 8) break;
  }
  return hits;
})()
"""

# 登录表单字段检测 JS
LOGIN_FORM_DETECT_JS = r"""
(() => {
  const forms = Array.from(document.querySelectorAll('form'));
  const result = { forms_found: forms.length, fields: [], submit_btn: '' };
  for (const form of forms) {
    const inputs = form.querySelectorAll('input');
    for (const inp of inputs) {
      const name = inp.name || inp.id || '';
      const type = inp.type || 'text';
      const ph = inp.placeholder || '';
      if (type === 'hidden' || type === 'submit' || type === 'button') continue;
      result.fields.push({ name: name, type: type, placeholder: ph });
      if (result.fields.length >= 8) break;
    }
    const btn = form.querySelector('button[type=submit],input[type=submit],button:not([type])');
    if (btn) result.submit_btn = btn.name || btn.id || 'form button[type=submit]';
    if (result.fields.length > 0) break;
  }
  return result;
})()
"""

# 页面正常性检测 JS
PAGE_NORMAL_DETECT_JS = r"""
(() => {
  const title = document.title || '';
  const bodyLen = document.body ? document.body.innerText.length : 0;
  const linkCount = document.querySelectorAll('a').length;
  const has404 = /404|not found|找不到|无法访问|connection refused|err_/.test((title + ' ' + (document.body ? document.body.innerText.slice(0, 300) : '')).toLowerCase());
  return { title: title.slice(0, 60), body_len: bodyLen, link_count: linkCount, has_404: has404 };
})()
"""

# ============ 工具函数 ============
def mask_url(url):
    """脱敏 URL：域名→[DOMAIN]，路径模式保留"""
    if not url:
        return ""
    m = re.sub(r'://[^/]+', '://[DOMAIN]', url)
    m = re.sub(r'#.*', '#[ANCHOR]', m)
    return m

def get_domain(url):
    if not url:
        return ""
    url = url.split('#')[0]
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1) if m else ""

def to_google_cache(url):
    """构造 google_cache URL"""
    if not url:
        return ""
    return f"https://webcache.googleusercontent.com/search?q=cache:{url}"

# ============ 破盾策略 ============
def try_cf_break(page, source_url):
    """
    对 CF 盾源依次尝试策略 A(google_cache) / B(JS注入) / C(直接等待)
    返回 {success: bool, strategy: str, evidence: dict, new_url: str}
    """
    result = {'success': False, 'strategy': '', 'evidence': {}, 'new_url': ''}

    # 策略 C - 直接等待（先访问原 URL）
    try:
        resp = page.goto(source_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        result['evidence']['status_code'] = resp.status if resp else None
        # 等 10 秒让 CF challenge 自动完成
        page.wait_for_timeout(10000)
        try:
            cf_state = page.evaluate(CF_DETECT_JS)
            result['evidence']['cf_state_after_wait'] = cf_state
            if not cf_state['is_cf']:
                result['success'] = True
                result['strategy'] = 'wait'
                return result
        except Exception:
            pass
    except Exception:
        pass

    # 策略 A - google_cache
    try:
        cache_url = to_google_cache(source_url)
        resp = page.goto(cache_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        if resp and resp.status < 400:
            page.wait_for_timeout(3000)
            try:
                cf_state = page.evaluate(CF_DETECT_JS)
                result['evidence']['cf_state_after_cache'] = cf_state
                if not cf_state['is_cf']:
                    # 进一步确认页面非空
                    normal = page.evaluate(PAGE_NORMAL_DETECT_JS)
                    result['evidence']['page_normal_after_cache'] = normal
                    if normal.get('body_len', 0) > 200:
                        result['success'] = True
                        result['strategy'] = 'google_cache'
                        result['new_url'] = cache_url
                        return result
            except Exception:
                pass
    except Exception:
        pass

    # 策略 B - JS注入（绕过 cf，设置 referer 和 UA）
    try:
        page.set_extra_http_headers({
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        resp = page.goto(source_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        if resp:
            result['evidence']['status_code_inject'] = resp.status
        page.wait_for_timeout(8000)
        try:
            cf_state = page.evaluate(CF_DETECT_JS)
            result['evidence']['cf_state_after_inject'] = cf_state
            if not cf_state['is_cf']:
                result['success'] = True
                result['strategy'] = 'js_inject'
                return result
        except Exception:
            pass
    except Exception:
        pass

    result['strategy'] = 'all_failed'
    return result

# ============ 登录检测 ============
def detect_login(page, source_url, existing_login_url):
    """
    检测登录入口和字段，构建 loginUi/loginJs
    返回 {login_url, login_ui, login_js, evidence}
    """
    result = {
        'login_url': existing_login_url or '',
        'login_ui': '',
        'login_js': '',
        'evidence': {'login_links': [], 'login_form': None, 'login_form_found': False}
    }

    # 已有 loginUrl，直接使用
    target_login_url = existing_login_url or ''

    # 步骤1：检测登录入口（仅在无 loginUrl 时）
    if not target_login_url:
        try:
            links = page.evaluate(LOGIN_LINK_DETECT_JS)
            if links:
                result['evidence']['login_links'] = [{'href': mask_url(l['href']), 'text': l['text']} for l in links[:3]]
                # 选第一个作为登录URL
                if links[0].get('href'):
                    target_login_url = links[0]['href']
        except Exception:
            pass

    if not target_login_url:
        return result

    # 步骤2：访问登录页检测字段
    try:
        resp = page.goto(target_login_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        if not resp or resp.status >= 400:
            return result
        page.wait_for_timeout(2000)
        try:
            page.evaluate(REMOVE_POPUP_JS)
        except Exception:
            pass
        form_info = page.evaluate(LOGIN_FORM_DETECT_JS)
        result['evidence']['login_form'] = form_info
        if form_info and form_info.get('fields'):
            result['evidence']['login_form_found'] = True
            # 步骤3：构建 loginUi / loginJs
            fields = form_info['fields']
            submit = form_info.get('submit_btn', '')
            username_field = None
            password_field = None
            for f in fields:
                name_l = (f.get('name', '') + f.get('placeholder', '')).lower()
                if f.get('type') == 'password':
                    password_field = f
                elif any(k in name_l for k in ['user', 'account', 'name', 'email', 'login', 'mail', '账号', '账号', '用户']):
                    username_field = f
            # fallback：第一个 text 类型作为用户名
            if not username_field:
                for f in fields:
                    if f.get('type') in ('text', 'email', None, ''):
                        username_field = f
                        break
            if username_field and password_field:
                u_sel = f"input[name={username_field.get('name', 'username')}]"
                p_sel = f"input[name={password_field.get('name', 'password')}]"
                # 如果没有 name，用 type 选择器
                if not username_field.get('name'):
                    u_sel = f"input[type={username_field.get('type', 'text')}]"
                if not password_field.get('name'):
                    p_sel = "input[type=password]"
                submit_sel = "button[type=submit]" if not submit else f"button#{submit},button[name={submit}]"
                result['login_ui'] = json.dumps({
                    'username': u_sel,
                    'password': p_sel,
                    'submit': submit_sel
                }, ensure_ascii=False)
                result['login_js'] = (
                    "// 简化说明:自动登录脚本\n"
                    f"var u=document.querySelector('{u_sel}');\n"
                    f"var p=document.querySelector('{p_sel}');\n"
                    "if(u&&p){u.value='[USER]';p.value='[PASS]';"
                    "var f=document.querySelector('form');if(f){f.submit();}}"
                )
    except Exception as e:
        result['evidence']['login_form_error'] = type(e).__name__

    return result

# ============ 主流程 ============
def main():
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
        f.write(f"[START] {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")

    # 加载 V4
    with open(V4_PATH, 'r', encoding='utf-8') as f:
        v4_raw = json.load(f)
    v4_data = v4_raw['sources'] if isinstance(v4_raw, dict) and 'sources' in v4_raw else v4_raw

    # 加载分类
    with open(CLASSIFICATION_PATH, 'r', encoding='utf-8') as f:
        classification = json.load(f)
    hard_list = classification.get('by_category', {}).get('hard', [])
    total = len(hard_list)

    # 支持环境变量限制数量（冒烟测试用）
    limit_env = os.environ.get('V5_HARD_LIMIT', '')
    if limit_env and limit_env.isdigit():
        total = min(total, int(limit_env))
        hard_list = hard_list[:total]

    print(f"[START] total={total}, v4_len={len(v4_data)}")
    with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[INFO] total={total}, v4_len={len(v4_data)}\n")

    fixes_result = {
        'analyzed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_input': total,
        'by_difficulty': {
            'cf_shield_success': 0,
            'cf_shield_failed': 0,
            'login_configured': 0,
            'login_failed': 0,
            'popup_removed': 0,
            'popup_unremovable': 0,
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

        for i, item in enumerate(hard_list):
            idx = item['source_index']
            dtype = item.get('type', '')
            enabled = item.get('enabled', True)

            # 写进度（脱敏：只记录 idx 和 type）
            with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
                f.write(f"[{i+1}/{total}] idx={idx} type={dtype} enabled={enabled}\n")

            # 边界检查
            if idx >= len(v4_data):
                fixes_result['failed'].append({
                    'source_index': idx,
                    'difficulty_type': dtype,
                    'reason': 'index_out_of_range'
                })
                continue

            source = v4_data[idx]
            source_url = source.get('sourceUrl', '') or ''
            existing_login_url = source.get('loginUrl', '') or ''

            if not source_url:
                fixes_result['failed'].append({
                    'source_index': idx,
                    'difficulty_type': dtype,
                    'reason': 'no_sourceUrl'
                })
                continue

            # 类型判断
            is_cf = 'cf' in dtype
            is_login = 'login' in dtype
            is_disabled = (enabled is False) or ('disabled' in dtype)

            new_fields = {}
            evidence = {
                'page_title': '',
                'login_form_found': False,
                'popup_removed_count': 0
            }
            strategy_applied = []
            success = True
            fail_reason = ''

            # 第1步：访问 sourceUrl（mobile_context, 30s）
            try:
                resp = page.goto(source_url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
                if resp:
                    evidence['status_code'] = resp.status
                # 等 networkidle（短超时，失败不致命）
                try:
                    page.wait_for_load_state('networkidle', timeout=8000)
                except Exception:
                    pass
                # 注入去弹框
                try:
                    popup_count = page.evaluate(REMOVE_POPUP_JS)
                    evidence['popup_removed_count'] = int(popup_count or 0)
                    if evidence['popup_removed_count'] > 0:
                        strategy_applied.append('popup_remove')
                except Exception:
                    pass
            except PWTimeoutError:
                fail_reason = 'timeout'
                success = False
            except PWError as e:
                fail_reason = 'pw_error:' + type(e).__name__
                success = False
            except Exception as e:
                fail_reason = 'err:' + type(e).__name__
                success = False

            # 第2步：CF 破盾
            cf_broken = False
            cf_strategy = ''
            new_source_url = ''
            if is_cf and success:
                try:
                    cf_result = try_cf_break(page, source_url)
                    evidence['cf_break'] = {
                        'success': cf_result['success'],
                        'strategy': cf_result['strategy']
                    }
                    if cf_result['success']:
                        cf_broken = True
                        cf_strategy = cf_result['strategy']
                        strategy_applied.append(cf_strategy)
                        if cf_result.get('new_url'):
                            new_source_url = cf_result['new_url']
                    else:
                        strategy_applied.append('cf_failed')
                except Exception as e:
                    evidence['cf_break'] = {'error': type(e).__name__}
                    strategy_applied.append('cf_error')

            # 第3步：登录检测
            login_configured = False
            if is_login and success:
                try:
                    login_result = detect_login(page, source_url, existing_login_url)
                    evidence['login_form_found'] = login_result['evidence']['login_form_found']
                    if login_result['login_ui'] and login_result['login_js']:
                        new_fields['loginUi'] = login_result['login_ui']
                        new_fields['loginJs'] = login_result['login_js']
                        if login_result['login_url'] and not existing_login_url:
                            new_fields['loginUrl'] = login_result['login_url']
                        login_configured = True
                        strategy_applied.append('login_detect')
                except Exception as e:
                    evidence['login_form_error'] = type(e).__name__
                    strategy_applied.append('login_error')

            # 第4步：去弹框 JS 写入 sourceComment（所有源都注入）
            if success:
                # 构造 sourceComment（追加 @js: 前置去弹框处理）
                existing_comment = source.get('sourceComment', '') or ''
                popup_js_inline = (
                    "@js:(()=>{"
                    "document.querySelectorAll('.modal,.popup,.overlay,.mask,.dialog,.ad-modal,.ad-popup,.vip-modal,.login-modal,.notice,.alert,[class*=popup],[class*=modal]').forEach(e=>{try{const c=getComputedStyle(e);if(c.position==='fixed'||parseInt(c.zIndex||'0',10)>999){e.remove();}}catch(_){}});"
                    "window.alert=function(){};window.confirm=function(){return true;};window.prompt=function(){return '';};"
                    "})()"
                )
                if popup_js_inline not in existing_comment:
                    if existing_comment:
                        new_fields['sourceComment'] = existing_comment + '\n' + popup_js_inline
                    else:
                        new_fields['sourceComment'] = popup_js_inline
                    strategy_applied.append('popup_comment')

            # 第5步：检测页面是否正常
            page_title = ''
            page_normal = False
            if success:
                try:
                    normal_info = page.evaluate(PAGE_NORMAL_DETECT_JS)
                    page_title = normal_info.get('title', '')[:60]
                    evidence['page_title'] = page_title
                    if (normal_info.get('body_len', 0) > 200
                            and not normal_info.get('has_404')
                            and not page_title.lower().startswith('just a moment')):
                        page_normal = True
                except Exception:
                    pass

            # 第6步：enabled 恢复
            if is_disabled and success and page_normal:
                new_fields['enabled'] = True
                strategy_applied.append('enable_recover')

            # 第7步：sourceUrl 替换（仅当 CF 破盾策略 A 成功）
            if cf_broken and cf_strategy == 'google_cache' and new_source_url:
                new_fields['sourceUrl'] = new_source_url

            # 第8步：写入 sourceComment 时脱敏
            # 统计更新
            if is_cf:
                if cf_broken:
                    fixes_result['by_difficulty']['cf_shield_success'] += 1
                else:
                    fixes_result['by_difficulty']['cf_shield_failed'] += 1
            if is_login:
                if login_configured:
                    fixes_result['by_difficulty']['login_configured'] += 1
                else:
                    fixes_result['by_difficulty']['login_failed'] += 1
            if evidence.get('popup_removed_count', 0) > 0:
                fixes_result['by_difficulty']['popup_removed'] += 1
            elif success and 'popup_comment' in strategy_applied:
                fixes_result['by_difficulty']['popup_removed'] += 1
            if not success:
                fixes_result['by_difficulty']['popup_unremovable'] += 1
            if new_fields.get('enabled') is True:
                fixes_result['by_difficulty']['enabled_recovered'] += 1

            # 构造输出（脱敏：sourceUrl_pattern 而非 sourceUrl）
            new_fields_masked = dict(new_fields)
            if 'sourceUrl' in new_fields_masked:
                new_fields_masked['sourceUrl'] = mask_url(new_fields_masked['sourceUrl'])
            if 'loginUrl' in new_fields_masked:
                new_fields_masked['loginUrl'] = mask_url(new_fields_masked['loginUrl'])
            # loginUi/loginJs/sourceComment 不含敏感信息（占位 [USER]/[PASS]）

            if not success:
                fixes_result['failed'].append({
                    'source_index': idx,
                    'difficulty_type': dtype,
                    'reason': fail_reason,
                    'suggestion': '网络访问失败，建议人工检查源URL可达性'
                })
            else:
                fixes_result['fixes'].append({
                    'source_index': idx,
                    'sourceUrl_pattern': mask_url(source_url),
                    'difficulty_type': dtype,
                    'strategy_applied': strategy_applied,
                    'success': success,
                    'new_fields': new_fields_masked,
                    'evidence': evidence
                })

            # 每 5 个源写一次中间结果
            if (i + 1) % 5 == 0:
                with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                    json.dump(fixes_result, f, ensure_ascii=False, indent=2)
                print(f"[PROGRESS] {i+1}/{total}")
                with open(PROGRESS_PATH, 'a', encoding='utf-8') as f:
                    f.write(f"[PROGRESS] {i+1}/{total} success={len(fixes_result['fixes'])} failed={len(fixes_result['failed'])}\n")

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

    # 写技术摘要（不含URL/源名）
    summary = {
        'analyzed_at': fixes_result['analyzed_at'],
        'total_input': fixes_result['total_input'],
        'by_difficulty': fixes_result['by_difficulty'],
        'fixes_count': len(fixes_result['fixes']),
        'failed_count': len(fixes_result['failed']),
        'failed_reasons': {}
    }
    for f_item in fixes_result['failed']:
        r = f_item.get('reason', 'unknown')
        summary['failed_reasons'][r] = summary['failed_reasons'].get(r, 0) + 1

    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[DONE] success={summary['fixes_count']} failed={summary['failed_count']}")
    print(f"[STATS] {summary['by_difficulty']}")
    print(f"[FAIL_REASONS] {summary['failed_reasons']}")

if __name__ == '__main__':
    main()
