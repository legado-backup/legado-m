#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订阅源视频类型重新识别脚本（宽松标准版）

背景：阶段3 type=2 只识别出3个视频源，标准过严。
本脚本用更宽松的标准重新识别 type=0 中的视频源。

识别标准（满足任一即认为是视频源）：
  a. sourceUrl/sortUrl/searchUrl 含视频关键词（/vod/、/vodplay/、/vodtype/、/movie/、/play/、/video/、m3u8、mp4、player、/影视、/视频、/动漫、/anime）
  b. ruleContent 含视频字段（<video、m3u8、mp4、player_aaaa、vodplay、hls.js、video-element、iframe）
  c. sourceComment 含视频描述（视频站、苹果CMS、MACCMS、影视、vod、player）
  d. sourceGroup = "视频"
  e. ruleArticles/ruleImage 含视频暗示（vod、video、play、movie、vodImg、vod-detail）
  f. sortUrl 含视频分类关键词（动作片、喜剧片、国产剧、综艺、动漫、番剧、电视剧、电影等）
  g. loginUrl 含视频路径（vodplay、/play/、/vod/）

输出安全铁律（不可违背）：
  - 脚本输出禁止包含业务字段原文（sourceName/sourceUrl/sourceComment 内容）
  - 只输出技术指标：idx, type, identified_by, confidence
  - 异常消息必须脱敏（替换 URL/域名为 [URL]/[DOMAIN]）

输入：output/rss/classified_v2.json（222源）
输出：output/rss/subagent_video_reidentify.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "subagent_video_reidentify.json"


# ========== 视频识别关键词库 ==========

# URL路径中的视频关键词（强信号）
URL_VIDEO_PATTERNS = [
    r'/vod(?:play|type|search|-|-type|-search)?/',  # /vod/, /vodplay/, /vodtype/, /vod-search/
    r'/vodplay/', r'/vodtype/', r'/vod-search/', r'/vod-search',
    r'vod-type-id', r'vod-type', r'vodtype',
    r'/movie/', r'/movies/', r'/play/', r'/video/', r'/videos/',
    r'/watch', r'/anime/', r'/dongman/', r'/donghua/',
    r'/v\.html', r'/v/', r'/v_play', r'/vplay',
    r'\.m3u8', r'\.mp4', r'player_aaaa',
    r'/vod-detail', r'/vodimg', r'/vodimg/',
    r'vodsearch', r'vod-search',
]

# sortUrl中的视频分类关键词（强信号）
SORTURL_VIDEO_CATEGORIES = [
    '动作片', '喜剧片', '爱情片', '科幻片', '恐怖片', '剧情片', '战争片', '记录片', '纪录片',
    '动画片', '动漫', '番剧', '番组',
    '国产剧', '台湾剧', '韩国剧', '韩剧', '欧美剧', '香港剧', '港剧', '泰国剧', '泰剧',
    '日本剧', '日剧', '海外剧', '港台剧', '日韩剧', '欧美剧',
    '综艺', '娱乐',
    '短剧', '微剧',
    '体育', '足球', '篮球',
    '电影', '电视剧', '剧集',
    '影视', '视频',
    # 英文分类
    'movie', 'movies', 'tv', 'tvshow', 'tv-play', 'drama', 'anime',
]

# ruleContent 中的视频字段（强信号）
RULE_CONTENT_VIDEO_PATTERNS = [
    r'<video', r'</video>', r'<source', r'video-element', r'video-source',
    r'videoSrc', r'videoUrl', r'video_src', r'video_url',
    r'\.m3u8', r'\.mp4', r'\.flv', r'\.webm',
    r'player_aaaa', r'player_', r'MacPlayer', r'macplayer',
    r'playerConfig', r'playerConfigJson',
    r'hls\.js', r'Hls\.js', r'flv\.js', r'flvjs',
    r'vodplay', r'vod-play', r'vod_play',
    r'iframe\s+src', r'<iframe',
    r'VideoPlayer', r'videoPlayer',
    r'playVideo', r'play_video',
    r'videojs', r'video-js',
    r'DPPlayer', r'dplayer', r'DPlayer',
    r'jwplayer', r'JWPlayer',
    r'sniffer', r'视频嗅探',
]

# ruleArticles / ruleImage / ruleLink 中的视频暗示字段
RULE_FIELDS_VIDEO_HINTS = [
    'vod', 'vodst', 'vodImg', 'vod-detail', 'vodimg',
    'video', 'videoList', 'video-list', 'video_list',
    'play', 'playList', 'play-list', 'play_list',
    'movie', 'movieList', 'movie-list',
    'xing_vb', 'xing_vb4',  # 常见视频站列表class
    'stui-vodlist', 'stui-pannel',  # 常见模板
    'module-vodlist', 'module-items',
    'myui-vodlist', 'myui-vod',
    'vodList', 'vod_list', 'vodlist',
    'videolist', 'video_list',
]

# sourceComment 中的视频描述关键词（中等信号）
COMMENT_VIDEO_KEYWORDS = [
    '视频站', '视频源', '视频网站', '视频APP', '视频app',
    '苹果CMS', 'MACCMS', 'macms', 'mac-cms', 'MacCMS',
    '影视站', '影视源', '影视网站',
    'vod', 'VOD',
    'player', 'Player',
    'm3u8', 'mp4',
    '视频嗅探', '嗅探',
    '播放器', '在线播放',
    '电影站', '电影源',
    '电视剧', '综艺', '动漫',
    'HLS', 'hls',
    '爬虫',  # 视频源常用
]

# 强信号关键词（命中即高置信度0.9）
STRONG_SIGNAL_PATTERNS = [
    r'player_aaaa', r'\.m3u8', r'\.mp4', r'\.flv',
    r'<video', r'</video>',
    r'hls\.js', r'Hls\.js',
    r'vodtype', r'vod-type', r'vodplay', r'vod-search',
    r'/vod/', r'/vodplay/', r'/vodtype/',
]


# ========== 脱敏工具 ==========

def sanitize_text(text: str, max_len: int = 100) -> str:
    """文本脱敏：替换URL/域名/token，并截断"""
    if not text or not isinstance(text, str):
        return ""
    # 替换完整URL
    text = re.sub(r'https?://[^\s"\'<>]+', '[URL]', text)
    # 替换裸域名
    text = re.sub(r'\b[a-z0-9\-]+\.(?:com|net|org|cc|tv|me|info|xyz|top|site|online|live|club|io|cn|jp|kr|us|uk|de|fr|ru|in|au|ca)\b[^\s]*',
                  '[DOMAIN]', text, flags=re.IGNORECASE)
    # 替换token/cookie/password等
    text = re.sub(r'(token|cookie|password|key|secret|auth|sign)=[^&\s"\'<>]+',
                  r'\1=***', text, flags=re.IGNORECASE)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def sanitize_exception(e: Exception) -> str:
    """脱敏异常消息"""
    return sanitize_text(str(e), 150)


# ========== 识别函数 ==========

def match_patterns(text: str, patterns: List[str]) -> List[str]:
    """对文本批量匹配正则，返回命中的pattern列表"""
    if not text:
        return []
    hits = []
    for p in patterns:
        try:
            if re.search(p, text, re.IGNORECASE):
                hits.append(p)
        except re.error:
            # 非正则的纯字符串匹配
            if p.lower() in text.lower():
                hits.append(p)
    return hits


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    """对文本做关键词匹配（大小写不敏感，子串匹配）"""
    if not text:
        return []
    text_lower = text.lower()
    hits = []
    for kw in keywords:
        if kw.lower() in text_lower:
            hits.append(kw)
    return hits


def identify_video_source(source: dict) -> Tuple[List[str], float, Dict[str, Any]]:
    """
    识别单个源是否为视频源

    返回: (identified_by_list, confidence, evidence_detail)
    identified_by_list: 命中的识别标准列表
    confidence: 0.0-1.0
    evidence_detail: 详细证据（脱敏后）
    """
    identified_by = []
    evidence = {
        "url_hits": [],
        "sorturl_hits": [],
        "searchurl_hits": [],
        "rulecontent_hits": [],
        "comment_hits": [],
        "rulefields_hits": [],
        "sourcegroup_hit": False,
        "loginurl_hits": [],
        "strong_signal_hits": [],
    }
    strong_hits_count = 0

    # 提取字段（不输出原文）
    source_url = source.get("sourceUrl", "") or ""
    sort_url = source.get("sortUrl", "") or ""
    search_url = source.get("searchUrl", "") or ""
    rule_content = source.get("ruleContent", "") or ""
    rule_articles = source.get("ruleArticles", "") or ""
    rule_image = source.get("ruleImage", "") or ""
    rule_link = source.get("ruleLink", "") or ""
    rule_title = source.get("ruleTitle", "") or ""
    source_comment = source.get("sourceComment", "") or ""
    source_group = source.get("sourceGroup", "") or ""
    login_url = source.get("loginUrl", "") or ""

    # === 标准 a: URL关键词 ===
    url_text = source_url
    url_hits = match_patterns(url_text, URL_VIDEO_PATTERNS)
    if url_hits:
        identified_by.append("url_keyword")
        evidence["url_hits"] = [f"pattern:{p[:40]}" for p in url_hits[:3]]

    sorturl_pattern_hits = match_patterns(sort_url, URL_VIDEO_PATTERNS)
    sorturl_category_hits = match_keywords(sort_url, SORTURL_VIDEO_CATEGORIES)
    if sorturl_pattern_hits or sorturl_category_hits:
        identified_by.append("sortUrl_keyword")
        evidence["sorturl_hits"] = (
            [f"pattern:{p[:30]}" for p in sorturl_pattern_hits[:2]] +
            [f"category:{c}" for c in sorturl_category_hits[:3]]
        )

    searchurl_hits = match_patterns(search_url, URL_VIDEO_PATTERNS)
    if searchurl_hits:
        identified_by.append("searchUrl_keyword")
        evidence["searchurl_hits"] = [f"pattern:{p[:30]}" for p in searchurl_hits[:2]]

    loginurl_hits = match_patterns(login_url, URL_VIDEO_PATTERNS)
    if loginurl_hits:
        identified_by.append("loginUrl_keyword")
        evidence["loginurl_hits"] = [f"pattern:{p[:30]}" for p in loginurl_hits[:2]]

    # === 标准 b: ruleContent视频字段 ===
    rc_hits = match_patterns(rule_content, RULE_CONTENT_VIDEO_PATTERNS)
    if rc_hits:
        identified_by.append("ruleContent_video_field")
        evidence["rulecontent_hits"] = [f"pattern:{p[:30]}" for p in rc_hits[:3]]

    # === 标准 c: sourceComment视频描述 ===
    comment_hits = match_keywords(source_comment, COMMENT_VIDEO_KEYWORDS)
    if comment_hits:
        identified_by.append("comment_video_desc")
        evidence["comment_hits"] = [f"kw:{k}" for k in comment_hits[:3]]

    # === 标准 d: sourceGroup ===
    if source_group and any(kw in source_group for kw in ["视频", "video", "Video", "VIDEO", "影视"]):
        identified_by.append("sourceGroup_video")
        evidence["sourcegroup_hit"] = True

    # === 标准 e: ruleArticles/ruleImage/ruleLink含视频暗示 ===
    rule_fields_text = f"{rule_articles}||{rule_image}||{rule_link}||{rule_title}"
    fields_hits = match_keywords(rule_fields_text, RULE_FIELDS_VIDEO_HINTS)
    if fields_hits:
        identified_by.append("ruleFields_video_hint")
        evidence["rulefields_hits"] = [f"hint:{h}" for h in fields_hits[:3]]

    # === 强信号检测：命中即高置信度 ===
    all_text = f"{source_url} {sort_url} {search_url} {rule_content} {source_comment} {login_url}"
    strong_hits = match_patterns(all_text, STRONG_SIGNAL_PATTERNS)
    evidence["strong_signal_hits"] = [f"strong:{p[:30]}" for p in strong_hits[:3]]
    strong_hits_count = len(strong_hits)

    # === 计算置信度 ===
    if not identified_by:
        return ([], 0.0, evidence)

    # 基础分: 每个标准贡献分数
    score_map = {
        "url_keyword": 0.4,
        "sortUrl_keyword": 0.4,
        "searchUrl_keyword": 0.3,
        "loginUrl_keyword": 0.3,
        "ruleContent_video_field": 0.5,
        "comment_video_desc": 0.3,
        "sourceGroup_video": 0.6,
        "ruleFields_video_hint": 0.25,
    }
    base_score = sum(score_map.get(k, 0.2) for k in identified_by)
    # 强信号加权
    base_score += min(strong_hits_count * 0.15, 0.3)
    # 多标准叠加奖励
    if len(identified_by) >= 3:
        base_score += 0.1
    if len(identified_by) >= 5:
        base_score += 0.1

    confidence = min(base_score, 1.0)

    # 强信号直接拉高置信度
    if strong_hits_count >= 2:
        confidence = max(confidence, 0.9)
    elif strong_hits_count >= 1:
        confidence = max(confidence, 0.75)

    # sourceGroup=视频 是非常强的信号
    if "sourceGroup_video" in identified_by:
        confidence = max(confidence, 0.85)

    # ruleContent中含视频模板是强信号
    if "ruleContent_video_field" in identified_by and strong_hits_count >= 1:
        confidence = max(confidence, 0.9)

    # 仅comment_keyword，无其他证据 → 可能视频源
    if identified_by == ["comment_video_desc"]:
        confidence = min(confidence, 0.55)

    # 仅ruleFields_video_hint，无其他证据 → 可能视频源
    if identified_by == ["ruleFields_video_hint"]:
        confidence = min(confidence, 0.5)

    return (identified_by, round(confidence, 3), evidence)


# ========== ruleContent 设计 ==========

V1_SNIFFER_JS = """<js>
(function(){
    var scripts = document.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent || '';
        var match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.m3u8[^\\s"'<>]*/);
        if (match) return match[0];
        match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.mp4[^\\s"'<>]*/);
        if (match) return match[0];
    }
    return '';
})();
</js>"""

V2_MACCMS_JS = """@js:var pm=result.match(/player_aaaa=({[\\s\\S]*?})<\\/script>/);
if(!pm){result}else{var p=JSON.parse(pm[1]);decodeURIComponent(p.url)}"""

V3_IFRAME_JS = """<js>
(function(){
    var f = document.querySelector('iframe[src]');
    return f ? f.src : '';
})();
</js>"""

V4_VIDEO_TAG_JS = """<js>
(function(){
    var v = document.querySelector('video[src], video source[src]');
    if (v) return v.src || v.getAttribute('src') || '';
    return '';
})();
</js>"""


def has_existing_video_template(rule_content: str) -> bool:
    """检测ruleContent是否已含完整视频模板（V1/V2/V3等）"""
    if not rule_content:
        return False
    indicators = [
        'video-element', 'hls.js', 'Hls.js', 'video-source', 'video-container',
        'player_aaaa', 'VideoPlayer', 'playerConfig',
        '<!DOCTYPE html>', '<video', '<source',
        'm3u8', '.mp4',
    ]
    rc_lower = rule_content.lower()
    return any(ind.lower() in rc_lower for ind in indicators)


def design_rule_content(source: dict, identified_by: List[str], evidence: Dict) -> Tuple[str, str, str]:
    """
    设计ruleContent

    返回: (rule_content, strategy, notes)
    - 若已有视频模板，保留原模板
    - 否则根据识别证据选择V1/V2/V3/V4/sniffer
    """
    rule_content = source.get("ruleContent", "") or ""
    source_comment = source.get("sourceComment", "") or ""
    sort_url = source.get("sortUrl", "") or ""

    # 1) 已有完整视频模板：保留
    if has_existing_video_template(rule_content):
        # 判断具体策略
        if 'player_aaaa' in rule_content:
            strategy = "V2"
        elif 'hls.js' in rule_content or 'Hls.js' in rule_content:
            strategy = "V1"
        elif '<video' in rule_content or '<source' in rule_content:
            strategy = "V1"
        elif 'iframe' in rule_content.lower():
            strategy = "V3"
        else:
            strategy = "existing_template"
        return (rule_content, strategy, "保留原有视频模板")

    # 2) 苹果CMS/MACCMS信号 → V2模板
    cms_signals = ['苹果CMS', 'MACCMS', 'macms', 'MacCMS', 'mac-cms', '苹果cms']
    is_cms = any(s.lower() in source_comment.lower() for s in cms_signals)
    has_vodplay = any('vodplay' in s for s in evidence.get("url_hits", []) +
                      evidence.get("sorturl_hits", []) +
                      evidence.get("searchurl_hits", []) +
                      evidence.get("loginurl_hits", []))
    has_vodtype = any('vodtype' in s.lower() or 'vod-type' in s.lower() for s in evidence.get("sorturl_hits", []) +
                      evidence.get("url_hits", []))
    if is_cms or has_vodplay or has_vodtype:
        return (V2_MACCMS_JS, "V2", "苹果CMS/VOD模板,使用player_aaaa解析")

    # 3) ruleContent含video/m3u8/mp4字段 → V1模板
    rc_hits = evidence.get("rulecontent_hits", [])
    if rc_hits and any('m3u8' in h or 'mp4' in h or '<video' in h or 'hls' in h.lower()
                       for h in rc_hits):
        return (V1_SNIFFER_JS, "V1", "ruleContent含视频字段,使用script嗅探m3u8/mp4")

    # 4) iframe信号 → V3模板
    rc_text = source.get("ruleContent", "") or ""
    if '<iframe' in rc_text.lower() or 'iframe' in rc_text.lower()[:500]:
        return (V3_IFRAME_JS, "V3", "ruleContent含iframe,使用iframe src提取")

    # 5) 默认：嗅探器策略（让VideoPlayerActivity自动嗅探）
    return ("", "sniffer", "无明显视频字段,使用嗅探器策略(留空ruleContent)")


# ========== 主流程 ==========

def main():
    if not INPUT_JSON.exists():
        print(f"[ERROR] 输入文件不存在: {INPUT_JSON}")
        sys.exit(1)

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    type0_indices = [i for i, item in enumerate(data) if item.get("type") == 0]
    print(f"[INFO] 总源数: {total}")
    print(f"[INFO] type=0 源数: {len(type0_indices)}")

    results = []
    identified_count = 0
    possible_count = 0  # 置信度0.5-0.7的可能视频源

    # 识别标准命中统计
    criteria_stats = {
        "url_keyword": 0,
        "sortUrl_keyword": 0,
        "searchUrl_keyword": 0,
        "loginUrl_keyword": 0,
        "ruleContent_video_field": 0,
        "comment_video_desc": 0,
        "sourceGroup_video": 0,
        "ruleFields_video_hint": 0,
    }

    # 强信号命中统计
    strong_signal_stats = {
        "player_aaaa": 0,
        "m3u8": 0,
        "mp4": 0,
        "vodtype": 0,
        "vodplay": 0,
        "video_tag": 0,
        "hls_js": 0,
    }

    for idx in type0_indices:
        source = data[idx]
        try:
            identified_by, confidence, evidence = identify_video_source(source)
        except Exception as e:
            print(f"  [WARN] idx={idx} 识别异常: {sanitize_exception(e)}")
            continue

        if not identified_by:
            continue

        # 更新命中统计
        for k in identified_by:
            if k in criteria_stats:
                criteria_stats[k] += 1

        # 更新强信号统计
        strong_hits = evidence.get("strong_signal_hits", [])
        for s in strong_hits:
            s_lower = s.lower()
            if 'player_aaaa' in s_lower:
                strong_signal_stats["player_aaaa"] += 1
            if 'm3u8' in s_lower:
                strong_signal_stats["m3u8"] += 1
            if 'mp4' in s_lower:
                strong_signal_stats["mp4"] += 1
            if 'vodtype' in s_lower or 'vod-type' in s_lower:
                strong_signal_stats["vodtype"] += 1
            if 'vodplay' in s_lower:
                strong_signal_stats["vodplay"] += 1
            if '<video' in s_lower or '</video' in s_lower:
                strong_signal_stats["video_tag"] += 1
            if 'hls' in s_lower:
                strong_signal_stats["hls_js"] += 1

        # 设计ruleContent
        rule_content_designed, strategy, design_notes = design_rule_content(source, identified_by, evidence)

        # 分类: 高置信度 vs 可能
        if confidence >= 0.7:
            identified_count += 1
        else:
            possible_count += 1

        result = {
            "idx": idx,
            "original_type": 0,
            "new_type": 2,
            "identified_by": identified_by,
            "identified_by_count": len(identified_by),
            "confidence": confidence,
            "is_possible": confidence < 0.7,
            "rule_content_strategy": strategy,
            "rule_content_designed": rule_content_designed if strategy != "existing_template" else "[保留原模板]",
            "enable_js": True,
            "evidence_summary": {
                "url_hits_count": len(evidence.get("url_hits", [])),
                "sorturl_hits_count": len(evidence.get("sorturl_hits", [])),
                "searchurl_hits_count": len(evidence.get("searchurl_hits", [])),
                "rulecontent_hits_count": len(evidence.get("rulecontent_hits", [])),
                "comment_hits_count": len(evidence.get("comment_hits", [])),
                "rulefields_hits_count": len(evidence.get("rulefields_hits", [])),
                "strong_signal_count": len(evidence.get("strong_signal_hits", [])),
                "sourcegroup_hit": evidence.get("sourcegroup_hit", False),
            },
            "analysis_notes": f"{design_notes}; 命中{len(identified_by)}条标准,置信度{confidence}",
        }
        results.append(result)

    # 按置信度排序
    results.sort(key=lambda x: x["confidence"], reverse=True)

    # 构建输出
    output = {
        "agent": "video_source_reidentifier",
        "version": "2.0_loose",
        "input_file": str(INPUT_JSON.name),
        "total_analyzed": len(type0_indices),
        "total_sources_in_input": total,
        "video_source_count": identified_count,
        "possible_video_count": possible_count,
        "total_identified": identified_count + possible_count,
        "criteria_stats": criteria_stats,
        "strong_signal_stats": strong_signal_stats,
        "results": results,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OUTPUT] 已保存到 {OUTPUT_JSON}")
    print(f"\n========== 识别摘要 ==========")
    print(f"总分析 type=0 源: {len(type0_indices)}")
    print(f"高置信度视频源(conf>=0.7): {identified_count}")
    print(f"可能视频源(conf 0.5-0.7): {possible_count}")
    print(f"总识别视频源: {identified_count + possible_count}")
    print(f"\n========== 识别标准命中统计 ==========")
    for k, v in criteria_stats.items():
        print(f"  {k}: {v}次")
    print(f"\n========== 强信号命中统计 ==========")
    for k, v in strong_signal_stats.items():
        print(f"  {k}: {v}次")
    print(f"\n========== Top 10 高置信度源 ==========")
    for r in results[:10]:
        print(f"  idx={r['idx']:3d} conf={r['confidence']:.2f} strategy={r['rule_content_strategy']:12s} "
              f"criteria={r['identified_by_count']} strong={r['evidence_summary']['strong_signal_count']}")


if __name__ == "__main__":
    main()
