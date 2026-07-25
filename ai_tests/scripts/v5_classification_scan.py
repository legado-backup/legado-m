# -*- coding: utf-8 -*-
"""
V4订阅源分类扫描脚本
输入: optimized_v2_lite_final_v4.json (229源)
输出: v5_classification.json (脱敏分类结果)

输出安全规范:
- 不输出sourceName/sourceComment原文
- sourceUrl路径模式化: http(s)://[DOMAIN]/path
- 只输出技术字段: source_index/missing字段名/type/reason
"""
import json
import re
from datetime import datetime
from urllib.parse import urlparse

INPUT_FILE = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v2_lite_final_v4.json'
OUTPUT_FILE = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_classification.json'


def sanitize_url(url):
    """路径模式化URL: http(s)://[DOMAIN]/path
    增强版:
    - 处理含@js:等内嵌URL的字段,扫描所有http(s)://协议并替换域名
    - 处理"业务名@js:..."格式: 去除业务名前缀
    - 处理URL中文锚点: 替换为#[ANCHOR]
    """
    if not url or not isinstance(url, str):
        return ''
    # 多行字段: 逐行处理
    if '\n' in url:
        lines = [sanitize_url(line) for line in url.split('\n') if line.strip()]
        return '\n'.join(lines)
    # 处理"业务名@js:..."格式: sourceUrl字段允许"显示名@js:代码"
    # 去除业务名前缀,只保留@js:之后的技术结构
    if '@js:' in url:
        idx_js = url.find('@js:')
        url = '@js:' + url[idx_js + 4:]
    # 扫描所有 http(s)://xxx 并替换其中的domain为[DOMAIN]
    def replace_domain(m):
        proto = m.group(1)
        return f'{proto}[DOMAIN]'
    sanitized = re.sub(r'(https?://)[^/\s,\'"\)]+', replace_domain, url)
    # 替换中文锚点 #中文 -> #[ANCHOR]
    sanitized = re.sub(r'#[^\s?&/\'"]+', '#[ANCHOR]', sanitized)
    # 替换可能残留的中文文本(排除常见技术词汇)
    sanitized = re.sub(r'[\u4e00-\u9fa5]+', '[CN]', sanitized)
    # 截断防止过长(含JS代码场景)
    if len(sanitized) > 100:
        sanitized = sanitized[:100] + '...'
    return sanitized


def get_domain(url):
    if not url or not isinstance(url, str):
        return ''
    m = re.match(r'https?://([^/\s,]+)', url)
    return m.group(1).lower() if m else ''


def is_empty(v):
    """判断字段是否为空"""
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ''
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def to_str(v):
    """安全转字符串: dict/list转JSON, None转空串"""
    if v is None:
        return ''
    if isinstance(v, str):
        return v
    if isinstance(v, (list, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def classify_navigation(src, source_url, sort_url, source_comment):
    """导航站识别"""
    reasons = []
    url_lower = source_url.lower()
    # sourceUrl关键词
    nav_keywords = ['nav', 'dao', 'hao', '123', 'daohang', 'navigation', 'portal', 'index']
    matched_kw = [kw for kw in nav_keywords if kw in url_lower]
    if matched_kw:
        reasons.append(f'url含导航关键词:{matched_kw}')
    # sortUrl为空或与sourceUrl相同
    if is_empty(sort_url):
        reasons.append('sortUrl为空')
    elif source_url and sort_url.strip() == source_url.strip():
        reasons.append('sortUrl与sourceUrl相同')
    # sourceComment含"导航"
    if source_comment and isinstance(source_comment, str) and '导航' in source_comment:
        reasons.append('comment含导航字样')
    # 至少满足2个特征才认为是导航站(避免误判)
    if len(reasons) >= 2:
        return reasons
    # 单独满足"comment含导航"+任一其他
    if any('comment' in r for r in reasons) and len(reasons) >= 1:
        return reasons
    return []


def classify_aggregator(sort_url, source_url):
    """集成站识别: sortUrl含多个分类且不同分类指向不同子域"""
    if is_empty(sort_url):
        return []
    # 解析sortUrl: 格式 "分类1::url1\n分类2::url2"
    lines = [l.strip() for l in sort_url.split('\n') if l.strip()]
    if len(lines) < 2:
        return []
    urls_in_sort = []
    for line in lines:
        if '::' in line:
            _, u = line.split('::', 1)
            urls_in_sort.append(u.strip())
        else:
            urls_in_sort.append(line)
    if len(urls_in_sort) < 2:
        return []
    # 比较host
    domains = set()
    for u in urls_in_sort:
        d = get_domain(u)
        if d:
            domains.add(d)
    # 不同分类指向不同子域
    if len(domains) >= 2:
        return [f'sortUrl含{len(lines)}分类,{len(domains)}个不同子域']
    # 同一域名但不同子目录路径(二级聚合)
    paths = set()
    base_domain = next(iter(domains), '')
    for u in urls_in_sort:
        if base_domain:
            m = re.match(r'https?://[^/]+(/[^/,]*)', u)
            if m:
                top_path = m.group(1).split('/')[1] if '/' in m.group(1) else m.group(1)
                paths.add(top_path)
    if len(paths) >= 3:
        return [f'sortUrl含{len(lines)}分类,同域但{len(paths)}个不同顶层目录']
    return []


def classify_video(src, rule_content, source_group):
    """视频源识别"""
    reasons = []
    # type=2
    if src.get('type') == 2:
        reasons.append('type=2')
    # ruleContent含@js: + m3u8/mp4/getPlayUrl
    if rule_content and isinstance(rule_content, str):
        if '@js:' in rule_content or '<js>' in rule_content:
            video_kw = ['m3u8', 'mp4', 'getPlayUrl', 'videoSources', 'video-element', 'Hls.js', 'hls.js']
            matched = [kw for kw in video_kw if kw.lower() in rule_content.lower()]
            if matched:
                reasons.append(f'ruleContent含视频字段:{matched[:3]}')
        # 含video标签或HLS播放器模板
        if '<video' in rule_content.lower() or 'hls.js' in rule_content.lower():
            if '视频播放模板' not in str(reasons):
                reasons.append('ruleContent含video/HLS播放模板')
    # sourceGroup含"视频"
    if source_group and isinstance(source_group, str):
        if '视频' in source_group or '影视' in source_group:
            reasons.append('sourceGroup含视频/影视')
    # 去重
    return reasons


def classify_image(src, rule_articles, rule_content):
    """图片源识别"""
    reasons = []
    if src.get('type') == 1:
        reasons.append('type=1')
    # ruleArticles含图片列表选择器
    if rule_articles and isinstance(rule_articles, str):
        img_selectors = ['img', 'image', '.pic', '.thumb', '.cover', 'src=', 'data-src', 'data-original']
        matched = [s for s in img_selectors if s in rule_articles.lower()]
        if matched and src.get('type') == 1:
            reasons.append(f'ruleArticles含图片选择器:{matched[:2]}')
    # ruleContent含图片选择器
    if rule_content and isinstance(rule_content, str):
        if '<img' in rule_content.lower() and src.get('type') == 1:
            reasons.append('ruleContent含img标签')
    return reasons


def classify_missing(src, search_url, sort_url, rule_next, rule_articles):
    """缺字段源识别"""
    missing = []
    if is_empty(search_url):
        missing.append('searchUrl')
    if is_empty(sort_url):
        missing.append('sortUrl')
    if is_empty(rule_next):
        missing.append('ruleNextPage')
    if is_empty(rule_articles):
        missing.append('ruleArticles')
    # enabled=false单独标记,不算"缺字段"但归入此类
    if src.get('enabled') is False:
        missing.append('enabled=false')
    return missing


def classify_hard(src, source_url, sort_url, source_comment, login_check_js, login_url):
    """难点源识别: CF/登录/弹框"""
    reasons = []
    type_tags = []
    # CF关键词
    cf_keywords = ['cloudflare', 'cf_', '5秒盾', 'just a moment', 'ddos protection', 'checking your browser']
    text_to_check = (source_url or '') + ' ' + (source_comment or '')
    if isinstance(login_check_js, str):
        text_to_check += ' ' + login_check_js
    text_lower = text_to_check.lower()
    matched_cf = [kw for kw in cf_keywords if kw in text_lower]
    if matched_cf:
        reasons.append(f'含CF关键词:{matched_cf[:2]}')
        type_tags.append('cf')
    # 登录关键词
    login_keywords = ['login', 'register', '登录', '注册']
    login_text = (sort_url or '') + ' ' + (source_comment or '') + ' ' + (login_url or '')
    login_text_lower = login_text.lower()
    matched_login = [kw for kw in login_keywords if kw.lower() in login_text_lower]
    if matched_login:
        reasons.append(f'含登录关键词:{matched_login[:2]}')
        type_tags.append('login')
    # loginCheckJs非空(需要登录验证)
    if isinstance(login_check_js, str) and login_check_js.strip():
        if 'loginCheckJs' not in str(reasons):
            reasons.append('loginCheckJs非空(需登录验证)')
            if 'login' not in type_tags:
                type_tags.append('login')
    # loginUrl非空
    if isinstance(login_url, str) and login_url.strip():
        if 'loginUrl非空' not in str(reasons):
            reasons.append('loginUrl非空')
            if 'login' not in type_tags:
                type_tags.append('login')
    # enabled=false 但有sourceUrl(可能需破盾)
    if src.get('enabled') is False and source_url:
        if 'enabled=false' not in str(reasons):
            reasons.append('enabled=false但有sourceUrl(待破盾检测)')
            type_tags.append('disabled')
    if not type_tags:
        return [], []
    return type_tags, reasons


def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sources = data.get('sources', [])
    total = len(sources)

    result = {
        'scan_at': datetime.now().isoformat(),
        'total': total,
        'by_category': {
            'navigation': [],
            'aggregator': [],
            'video': [],
            'image': [],
            'missing_fields': [],
            'hard': []
        },
        'stats': {
            'navigation_count': 0,
            'aggregator_count': 0,
            'video_count': 0,
            'image_count': 0,
            'missing_fields_count': 0,
            'hard_count': 0,
            'overlap_count': 0
        }
    }

    # 记录每个源归属的分类数(用于overlap统计)
    source_categories = {}

    for idx, src in enumerate(sources):
        source_url = to_str(src.get('sourceUrl', ''))
        sort_url = to_str(src.get('sortUrl', ''))
        source_comment = to_str(src.get('sourceComment', ''))
        rule_content = to_str(src.get('ruleContent', ''))
        rule_articles = to_str(src.get('ruleArticles', ''))
        rule_next = to_str(src.get('ruleNextPage', ''))
        search_url = to_str(src.get('searchUrl', ''))
        source_group = to_str(src.get('sourceGroup', ''))
        login_check_js = to_str(src.get('loginCheckJs', ''))
        login_url = to_str(src.get('loginUrl', ''))

        cats_for_source = []

        # 1. 导航站
        nav_reasons = classify_navigation(src, source_url, sort_url, source_comment)
        if nav_reasons:
            result['by_category']['navigation'].append({
                'source_index': idx,
                'sourceUrl_pattern': sanitize_url(source_url)[:80],
                'reason': '; '.join(nav_reasons)
            })
            cats_for_source.append('navigation')

        # 2. 集成站
        agg_reasons = classify_aggregator(sort_url, source_url)
        if agg_reasons:
            result['by_category']['aggregator'].append({
                'source_index': idx,
                'sourceUrl_pattern': sanitize_url(source_url)[:80],
                'sortUrl_categories': sort_url.count('\n') + 1 if sort_url else 0,
                'reason': '; '.join(agg_reasons)
            })
            cats_for_source.append('aggregator')

        # 3. 视频源
        vid_reasons = classify_video(src, rule_content, source_group)
        if vid_reasons:
            result['by_category']['video'].append({
                'source_index': idx,
                'type': src.get('type'),
                'sourceUrl_pattern': sanitize_url(source_url)[:80],
                'reason': '; '.join(vid_reasons)
            })
            cats_for_source.append('video')

        # 4. 图片源
        img_reasons = classify_image(src, rule_articles, rule_content)
        if img_reasons:
            result['by_category']['image'].append({
                'source_index': idx,
                'type': src.get('type'),
                'sourceUrl_pattern': sanitize_url(source_url)[:80],
                'reason': '; '.join(img_reasons)
            })
            cats_for_source.append('image')

        # 5. 缺字段源
        missing = classify_missing(src, search_url, sort_url, rule_next, rule_articles)
        if missing:
            result['by_category']['missing_fields'].append({
                'source_index': idx,
                'enabled': src.get('enabled'),
                'missing': missing,
                'sourceUrl_pattern': sanitize_url(source_url)[:80]
            })
            cats_for_source.append('missing_fields')

        # 6. 难点源
        hard_types, hard_reasons = classify_hard(src, source_url, sort_url, source_comment, login_check_js, login_url)
        if hard_types:
            result['by_category']['hard'].append({
                'source_index': idx,
                'type': '/'.join(hard_types),
                'enabled': src.get('enabled'),
                'sourceUrl_pattern': sanitize_url(source_url)[:80],
                'reason': '; '.join(hard_reasons)
            })
            cats_for_source.append('hard')

        if len(cats_for_source) > 1:
            source_categories[idx] = cats_for_source

    # 统计
    result['stats']['navigation_count'] = len(result['by_category']['navigation'])
    result['stats']['aggregator_count'] = len(result['by_category']['aggregator'])
    result['stats']['video_count'] = len(result['by_category']['video'])
    result['stats']['image_count'] = len(result['by_category']['image'])
    result['stats']['missing_fields_count'] = len(result['by_category']['missing_fields'])
    result['stats']['hard_count'] = len(result['by_category']['hard'])
    result['stats']['overlap_count'] = len(source_categories)

    # 添加overlap详情
    result['overlap_details'] = [
        {'source_index': idx, 'categories': cats}
        for idx, cats in source_categories.items()
    ]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 控制台输出统计(只输出技术数字,不输出业务字段)
    print(f'=== V4订阅源分类扫描完成 ===')
    print(f'总源数: {total}')
    print(f'导航站: {result["stats"]["navigation_count"]}')
    print(f'集成站: {result["stats"]["aggregator_count"]}')
    print(f'视频源: {result["stats"]["video_count"]}')
    print(f'图片源: {result["stats"]["image_count"]}')
    print(f'缺字段: {result["stats"]["missing_fields_count"]}')
    print(f'难点源: {result["stats"]["hard_count"]}')
    print(f'多分类重叠: {result["stats"]["overlap_count"]}')
    print(f'输出文件: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
