#!/usr/bin/env python3
"""deep_optimize_with_playwright.py — 用Playwright真实浏览器深度优化失败源

对 v2 验证 scenario_1_list_load 失败的 10 个源：
1. 用 Playwright 真实浏览器访问（突破反爬）
2. 等待页面完全加载（含JS渲染）
3. 用 JavaScript 提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）
4. 校验字段有效性，只替换无效字段
5. 输出纯技术指标（禁止业务字段原文）

输出：idx + 访问状态 + 字段长度 + is_valid + 替换记录
不输出：URL/源名称/域名/cookie内容
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.stdout.reconfigure(encoding='utf-8')

FAILED_IDX = [1, 21, 24, 30, 36, 39, 46, 55, 58, 60]

INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'
OUTPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final_v3.json'


def extract_base_url(source_url):
    """从 sourceUrl 提取 base_url（脚本内部用，不输出）"""
    if not source_url or not source_url.startswith('http'):
        return ''
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    m = re.match(r'(https?://[^/]+)', base)
    return m.group(1) + '/' if m else ''


# JavaScript 提取4字段的代码（在浏览器上下文执行）
EXTRACT_JS = """
(() => {
    const result = {sourceIcon: '', searchUrl: '', sortUrl: '', ruleNextPage: ''};
    
    // 1. sourceIcon: favicon
    const iconLink = document.querySelector('link[rel*="icon"]') || document.querySelector('link[rel="shortcut icon"]');
    if (iconLink && iconLink.href) {
        result.sourceIcon = iconLink.href;
    }
    
    // 2. searchUrl: 找搜索表单
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
        const action = form.action || form.getAttribute('action');
        const textInput = form.querySelector('input[type="text"], input[type="search"], input:not([type])');
        if (action && textInput && textInput.name) {
            let fullAction = action;
            if (action.startsWith('/')) {
                fullAction = location.origin + action;
            }
            const sep = fullAction.includes('?') ? '&' : '?';
            result.searchUrl = fullAction + sep + textInput.name + '={{key}}';
            break;
        }
    }
    
    // 3. sortUrl: 找分类链接（含"最新"/"热门"/"分类"等关键词的<a>）
    const catKeywords = ['最新', '热门', '分类', '全部', '推荐', '排行'];
    const catLinks = [];
    document.querySelectorAll('a').forEach(a => {
        const text = (a.textContent || '').trim();
        const href = a.href;
        if (!href) return;
        for (const kw of catKeywords) {
            if (text.includes(kw) && !catLinks.includes(href)) {
                catLinks.push(href);
                break;
            }
        }
    });
    if (catLinks.length > 0) {
        const items = catLinks.slice(0, 5).map(link => '分类::' + link);
        result.sortUrl = items.join('\\n');
    }
    
    // 4. ruleNextPage: 找分页
    const nextSelectors = [
        'a.next', 'a.next.page-link', 'a[rel="next"]',
        'a:contains("下一页")', 'a:contains("Next")', '.pagination a:last-child'
    ];
    // 直接用 querySelector
    const nextByClass = document.querySelector('a.next, a.next-page, a.page-link.next');
    if (nextByClass && nextByClass.href) {
        result.ruleNextPage = '@CSS:a.next@href';
    } else {
        const nextByRel = document.querySelector('a[rel="next"]');
        if (nextByRel && nextByRel.href) {
            result.ruleNextPage = '@CSS:a[rel="next"]@href';
        } else {
            // 找含"下一页"文字的链接
            const allLinks = document.querySelectorAll('a');
            for (const a of allLinks) {
                const text = (a.textContent || '').trim();
                if (text === '下一页' || text === 'Next' || text === '>') {
                    if (a.href) {
                        result.ruleNextPage = '@CSS:a:contains(下一页)@href';
                        break;
                    }
                }
            }
        }
    }
    
    return result;
})();
"""


def is_valid_field(field, value):
    """校验字段值是否合法"""
    if not value or not isinstance(value, str):
        return False
    if value.strip() in ('None', 'null', 'undefined', 'NaN', 'page'):
        return False
    if field == 'ruleNextPage':
        if value.startswith(('@CSS:', '@XPath:', '@js:', '<js>')):
            return True
        if '@href' in value:
            return True
        if re.match(r'^[.#a-zA-Z][\w\-:. ()#\[\]>]+@?.*', value):
            return True
        return False
    if field in ('sourceIcon', 'searchUrl', 'sortUrl'):
        if not value.startswith(('http', '/', '@js:', '<js>')):
            return False
        return True
    return True


def main():
    print('=' * 70)
    print('Playwright 深度优化失败源（脱敏输出）')
    print('=' * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    
    print(f'\n总源数: {len(sources)}')
    print(f'待深度优化的失败源 idx: {FAILED_IDX}')
    
    detail_results = []
    optimized_count = 0
    no_change_count = 0
    
    with sync_playwright() as p:
        # 启动 chromium（headless）
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',  # 隐藏 webdriver 标识
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        # 注入 stealth 脚本（隐藏 webdriver）
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        page = context.new_page()
        
        for idx in FAILED_IDX:
            s = sources[idx]
            source_url = s.get('sourceUrl', '')
            base_url = extract_base_url(source_url)
            
            print(f'\n  [idx={idx}]')
            print(f'    base_url_len={len(base_url)} is_http_prefix={base_url.startswith("http")}')
            
            if not base_url:
                print(f'    跳过: sourceUrl非http开头')
                detail_results.append({
                    'idx': idx, 'strategy': 'skip_invalid_url',
                    'status': 0, 'html_len': 0, 'fields_extracted': {},
                    'optimization': 'no_change', 'reason': 'sourceUrl not http prefix'
                })
                no_change_count += 1
                continue
            
            # Playwright 访问
            try:
                resp = page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
                status = resp.status if resp else 0
                
                # 等待页面渲染
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except PlaywrightTimeout:
                    pass  # networkidle 超时不算失败
                
                # 检查是否被反爬拦截（如 CF challenge）
                page_title = page.title() or ''
                is_cf_challenge = 'just a moment' in page_title.lower() or 'cf-challenge' in (page.content() or '').lower()
                
                content = page.content() or ''
                html_len = len(content)
                
                print(f'    访问结果: status={status} html_len={html_len} is_cf={is_cf_challenge}')
                
                if status != 200 or html_len < 1000 or is_cf_challenge:
                    print(f'    优化策略: 无法有效访问（status={status} len={html_len} cf={is_cf_challenge}）')
                    detail_results.append({
                        'idx': idx, 'strategy': 'playwright',
                        'status': status, 'html_len': html_len,
                        'is_cf_challenge': is_cf_challenge,
                        'fields_extracted': {},
                        'optimization': 'no_change',
                        'reason': f'status={status} or len={html_len} or cf={is_cf_challenge}'
                    })
                    no_change_count += 1
                    continue
                
                # 提取4字段
                extracted = page.evaluate(EXTRACT_JS)
                
                # 校验提取的字段
                valid_fields = {}
                for field, value in extracted.items():
                    if value:
                        is_valid = is_valid_field(field, value)
                        print(f'    提取 {field}: len={len(value)} is_valid={is_valid}')
                        if is_valid:
                            valid_fields[field] = value
                
                # 对比当前值，只在新值有效且当前值无效/为空时替换
                changes = []
                for field, new_value in valid_fields.items():
                    current_value = s.get(field, '')
                    current_valid = is_valid_field(field, current_value)
                    if not current_valid:
                        s[field] = new_value
                        changes.append({
                            'field': field,
                            'before_len': len(current_value) if current_value else 0,
                            'after_len': len(new_value),
                            'before_valid': current_valid,
                            'after_valid': True,
                        })
                        print(f'    替换 {field}: before_len={len(current_value) if current_value else 0} after_len={len(new_value)}')
                
                if changes:
                    optimized_count += 1
                    detail_results.append({
                        'idx': idx, 'strategy': 'playwright',
                        'status': status, 'html_len': html_len,
                        'fields_extracted': {f: len(v) if v else 0 for f, v in extracted.items()},
                        'optimization': 'fields_updated',
                        'changes': changes,
                    })
                else:
                    no_change_count += 1
                    print(f'    无字段需要替换')
                    detail_results.append({
                        'idx': idx, 'strategy': 'playwright',
                        'status': status, 'html_len': html_len,
                        'fields_extracted': {f: len(v) if v else 0 for f, v in extracted.items()},
                        'optimization': 'no_change', 'reason': 'no invalid fields to replace'
                    })
                    
            except PlaywrightTimeout as e:
                print(f'    Playwright超时: exception:PlaywrightTimeout')
                detail_results.append({
                    'idx': idx, 'strategy': 'playwright',
                    'status': 0, 'html_len': 0,
                    'fields_extracted': {},
                    'optimization': 'no_change', 'reason': f'playwright_timeout'
                })
                no_change_count += 1
            except Exception as e:
                # 异常消息可能含URL，脱敏：只保留异常类型+错误关键词，去掉URL
                err_msg = str(e)
                # 用正则去掉URL
                err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                # 进一步去掉可能的域名
                err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg_safe)
                # 截断
                err_msg_safe = err_msg_safe[:200]
                print(f'    Playwright异常: exception:{type(e).__name__} msg={err_msg_safe}')
                detail_results.append({
                    'idx': idx, 'strategy': 'playwright',
                    'status': 0, 'html_len': 0,
                    'fields_extracted': {},
                    'optimization': 'no_change', 'reason': f'exception:{type(e).__name__}: {err_msg_safe}'
                })
                no_change_count += 1
        
        browser.close()
    
    # 保存优化后的JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    
    print('\n' + '=' * 70)
    print('Playwright 深度优化汇总')
    print('=' * 70)
    print(f'  总失败源数: {len(FAILED_IDX)}')
    print(f'  成功优化字段: {optimized_count} 个源')
    print(f'  无变化: {no_change_count} 个源')
    
    # 字段替换统计
    from collections import Counter
    field_changes = Counter()
    for r in detail_results:
        if r['optimization'] == 'fields_updated':
            for c in r.get('changes', []):
                field_changes[c['field']] += 1
    
    print(f'\n--- 字段替换统计 ---')
    for field, count in field_changes.most_common():
        print(f'  {field}: {count} 次替换')
    
    # 保存详细报告
    report_path = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/deep_optimization_playwright_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_failed': len(FAILED_IDX),
            'optimized_count': optimized_count,
            'no_change_count': no_change_count,
            'field_changes': dict(field_changes),
            'detail': detail_results,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n优化后JSON: {OUTPUT_PATH}')
    print(f'详细报告: {report_path}')


if __name__ == '__main__':
    main()
