#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点E子站批量技术分析（脱敏输出）
逐站访问.cfd子站，提取CMS类型/4字段/列表页/播放页链路
"""
import sys
import json
import re
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright

MS_DOMAINS = {
    "microsoft.com", "microsoftonline.com", "live.com", "office.com",
    "office365.com", "sway.cloud.microsoft", "sway.office.com",
    "azureedge.net", "msftauth.net", "sharepoint.com", "docs.com",
    "skype.com", "bing.com", "msn.com", "windows.net", "xbox.com",
    "github.com", "linkedin.com", "twitter.com", "facebook.com",
    "youtube.com", "youtu.be", "vimeo.com", "soundcloud.com",
    "sketchfab.com", "pickit.com", "google.com", "googleapis.com",
    "gstatic.com", "cloudflare.com", "jsdelivr.net", "unpkg.com",
    "w3.org", "schema.org", "msft.net", "azure.com",
}


def is_ms_domain(domain):
    domain = domain.lower()
    for ms in MS_DOMAINS:
        if domain == ms or domain.endswith("." + ms):
            return True
    return False


def sanitize_url(url):
    if not url:
        return "[空]"
    try:
        parsed = urlparse(url)
        return f"[域名:.{parsed.netloc.split('.')[-1]}]{parsed.path[:40]}"
    except Exception:
        return "[解析失败]"


def detect_cms(html, url):
    """识别CMS类型"""
    url_lower = url.lower()
    html_lower = html.lower()
    # MacCMS特征
    if '/vod/' in html_lower or '/vodsearch/' in url_lower or 'maccms' in html_lower or 'vodplay' in html_lower:
        return 'MacCMS'
    if '/index.php/vod/' in html_lower:
        return 'MacCMS'
    # WordPress特征
    if 'wp-content' in html_lower or 'wp-json' in html_lower or 'wordpress' in html_lower:
        return 'WordPress'
    # Typecho
    if 'typecho' in html_lower or '/usr/uploads/' in html_lower:
        return 'Typecho'
    # 通用视频站特征
    if 'player_data' in html_lower or 'vod_play' in html_lower:
        return 'MacCMS-like'
    return 'Unknown'


def analyze_site(page, url, site_idx):
    """分析单个子站（含安全检测等待）"""
    result = {"idx": site_idx, "url_suffix": "." + urlparse(url).netloc.split(".")[-1]}
    
    try:
        # 访问首页
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        # 检测"浏览器安全检测"页面，等待跳转
        title = page.title()
        if "安全检测" in title or "检测" in title:
            print(f"  [检测到安全检测页面，等待15秒...]")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(10000)
            title = page.title()
        
        # 再次检测，如果还是安全检测，再等一次
        if "安全检测" in title or "检测" in title:
            print(f"  [仍在安全检测，再等10秒...]")
            page.wait_for_timeout(10000)
            try:
                title = page.title()
            except Exception:
                pass
        
        result["title"] = title[:50] if title else "[空]"
        html = page.content()
        result["html_len"] = len(html)
        result["cms"] = detect_cms(html, page.url)
        result["final_url_suffix"] = "." + urlparse(page.url).netloc.split(".")[-1] if urlparse(page.url).netloc else ""
        
        # 提取4字段（IIFE）
        fields = page.evaluate("""() => {
            const r = {};
            const icon = document.querySelector('link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
            r.icon = icon ? icon.href : (window.location.origin + '/favicon.ico');
            const form = document.querySelector('form[action*="search"], form[id*="search"], form[class*="search"], #searchform, .search-form');
            r.searchForm = form ? {
                action: form.action,
                inputs: Array.from(form.querySelectorAll('input,select')).map(i => ({name:i.name, type:i.type}))
            } : null;
            const allLinks = Array.from(document.querySelectorAll('a[href]'));
            r.catLinks = allLinks.filter(a => /\\/vod\\//i.test(a.href) || /\\/category\\//i.test(a.href) || /\\/type\\//i.test(a.href) || /\\/list\\//i.test(a.href)).slice(0,10).map(a => ({href:a.href, text:a.textContent.trim().substring(0,20)}));
            const pg = document.querySelector('.pagination, .page-nav, .nav-links, ul.page-numbers, .myui-page');
            r.pagination = pg ? pg.className : null;
            const listSelectors = ['.stui-vodlist__box', '.myui-vodlist__box', '.vodlist_item', '.stui-vodlist__item', '.module-item', '.video-block', 'ul.vodlist li', '.col-pb', '.item', '.module-items .module-item'];
            r.listItems = 0;
            r.listSelector = '';
            for (const sel of listSelectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    r.listItems = els.length;
                    r.listSelector = sel;
                    break;
                }
            }
            if (r.listItems === 0) {
                const divs = Array.from(document.querySelectorAll('div')).filter(d => {
                    return d.querySelector('a[href]') && d.querySelector('img') && d.children.length < 5;
                });
                if (divs.length > 3) {
                    r.listItems = divs.length;
                    r.listSelector = '[通用:div>a+img]';
                }
            }
            const nav = document.querySelector('nav, .nav, .navbar, .menu, #menu, .header .nav');
            r.navItems = nav ? Array.from(nav.querySelectorAll('a[href]')).slice(0,8).map(a => ({href:a.href, text:a.textContent.trim().substring(0,15)})) : [];
            r.hasApiSearch = allLinks.some(a => a.href.includes('ac=list') || a.href.includes('ac=detail'));
            r.hasVodPlay = allLinks.some(a => a.href.includes('/vodplay/') || a.href.includes('/vod/play'));
            r.hasVodDetail = allLinks.some(a => a.href.includes('/voddetail/') || a.href.includes('/vod/detail') || a.href.includes('/vodinfo/'));
            r.bodyTextLen = (document.body.innerText || '').length;
            return r;
        }""")
        result.update(fields)
        
        # 如果有列表项，提取首个链接路径
        if result.get("listSelector") and result.get("listItems", 0) > 0 and "[通用" not in result["listSelector"]:
            try:
                first_item = page.query_selector(result["listSelector"] + ' a[href]')
                if first_item:
                    link_href = first_item.get_attribute('href')
                    result["first_link_path"] = urlparse(link_href).path[:50] if link_href else "[空]"
                    if '/vodplay/' in (link_href or '') or '/play/' in (link_href or ''):
                        result["link_type"] = "播放页"
                    elif '/voddetail/' in (link_href or '') or '/detail/' in (link_href or '') or '/info/' in (link_href or ''):
                        result["link_type"] = "详情页"
                    else:
                        result["link_type"] = "未知"
            except Exception:
                result["link_type"] = "提取失败"
        
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:100]}"
    
    return result


def main():
    print("=== 站点E子站批量技术分析（脱敏）===")
    
    # 读取子站URL
    with open("output/siteE_subsites.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 筛选.cfd域名（真正的子站）
    subsites = []
    for url in data["subsites"]:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if is_ms_domain(domain):
                continue
            if domain.endswith(".cfd") or domain.endswith(".xyz") or domain.endswith(".buzz"):
                if url not in subsites:
                    subsites.append(url)
        except Exception:
            continue
    
    print(f"筛选出 {len(subsites)} 个子站（.cfd/.xyz/.buzz域名）")
    print()
    
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # Stealth模式：隐藏headless标识
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
        """)
        page = context.new_page()
        
        for i, url in enumerate(subsites):
            print(f"--- 分析子站[{i+1}] ---")
            result = analyze_site(page, url, i+1)
            results.append({"url": url, "analysis": result})
            
            # 输出脱敏报告
            a = result
            print(f"  域名后缀: {a.get('url_suffix','')}")
            print(f"  最终域名后缀: {a.get('final_url_suffix','')}")
            print(f"  标题: {a.get('title','')[:40]}")
            print(f"  CMS类型: {a.get('cms','')}")
            print(f"  HTML长度: {a.get('html_len',0)}")
            print(f"  列表选择器: {a.get('listSelector','')}")
            print(f"  列表项数: {a.get('listItems',0)}")
            print(f"  有API搜索: {a.get('hasApiSearch',False)}")
            print(f"  有vodPlay链接: {a.get('hasVodPlay',False)}")
            print(f"  有vodDetail链接: {a.get('hasVodDetail',False)}")
            print(f"  首个链接路径: {a.get('first_link_path','')}")
            print(f"  链接类型: {a.get('link_type','')}")
            print(f"  搜索表单: {'有' if a.get('searchForm') else '无'}")
            if a.get('searchForm'):
                inputs = a['searchForm'].get('inputs',[])
                print(f"    action路径: {urlparse(a['searchForm'].get('action','')).path[:30]}")
                print(f"    输入框: {inputs}")
            print(f"  分页类: {a.get('pagination','')}")
            print(f"  导航项数: {len(a.get('navItems',[]))}")
            if a.get('error'):
                print(f"  [ERROR] {a['error']}")
            print()
    
        browser.close()
    
    # 保存完整结果
    with open("output/siteE_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"=== 分析完成，结果已保存: output/siteE_analysis.json ({len(results)}个子站) ===")


if __name__ == "__main__":
    main()
