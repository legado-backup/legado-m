"""源 JSON 解析：字段映射、URL 标准化、domain_key 提取、去重。

将 Legado 的 BookSource/RssSource JSON 统一解析为标准化字典，
便于后续入库和查询。
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# BookSource 字段映射：数据库列名 → JSON key（str）或 lambda 提取器
# ---------------------------------------------------------------------------
BOOK_SOURCE_MAPPING: dict[str, str | Callable[[dict], Optional[str]]] = {
    "source_url": "bookSourceUrl",
    "source_name": "bookSourceName",
    "source_icon": lambda _: None,  # BookSource 无 bookSourceIcon 字段
    "source_group": "bookSourceGroup",
    "book_source_type": "bookSourceType",  # 0文本/1音频/2图片/3文件/4视频
    "book_url_pattern": "bookUrlPattern",
    "search_url": "searchUrl",
    "explore_url": "exploreUrl",
    "explore_screen": "exploreScreen",
    "enabled_explore": "enabledExplore",  # 默认true
    "enabled": "enabled",  # 默认true
    "login_url": "loginUrl",
    "login_check_js": "loginCheckJs",  # 注意不是loginCheckUrl
    "login_ui": "loginUi",  # JSON字符串
    "cover_decode_js": "coverDecodeJs",
    "event_listener": "eventListener",  # Boolean
    "custom_button": "customButton",  # Boolean
    "respond_time": "respondTime",
    "weight": "weight",
    "rule_search": lambda obj: _serialize_rule(obj, "ruleSearch"),
    "rule_book_info": lambda obj: _serialize_rule(obj, "ruleBookInfo"),
    "rule_toc": lambda obj: _serialize_rule(obj, "ruleToc"),
    "rule_content": lambda obj: _serialize_rule(obj, "ruleContent"),
    "rule_explore": lambda obj: _serialize_rule(obj, "ruleExplore"),
}

# ---------------------------------------------------------------------------
# RssSource 字段映射
# ---------------------------------------------------------------------------
RSS_SOURCE_MAPPING: dict[str, str | Callable[[dict], Optional[str]]] = {
    "source_url": "sourceUrl",
    "source_name": "sourceName",
    "source_icon": "sourceIcon",
    "source_group": "sourceGroup",
    "rss_type": "type",  # 0网页/1图片/2视频（注意字段名是type）
    "enabled_explore": lambda _: None,  # RssSource无此字段
    "login_url": "loginUrl",
    "login_check_js": "loginCheckJs",
    "login_ui": "loginUi",
    "search_url": "searchUrl",
    "explore_url": lambda _: None,  # 订阅源无发现URL
    "event_listener": lambda _: None,  # BookSource特有
    "custom_button": lambda _: None,  # BookSource特有
    "respond_time": lambda _: None,
    "weight": lambda _: None,
    "book_source_type": lambda _: None,
    "rule_articles": "ruleArticles",  # String，非嵌套对象
    "rule_content": "ruleContent",  # String
    "rule_title": "ruleTitle",
    "rule_image": "ruleImage",
    "rule_link": "ruleLink",
    "rule_next_page": "ruleNextPage",
    "rule_pub_date": "rulePubDate",
    "rule_description": "ruleDescription",
}


def _serialize_rule(obj: dict, key: str) -> Optional[str]:
    """将嵌套规则对象序列化为 JSON 字符串，已经是字符串则原样返回。"""
    val = obj.get(key)
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """URL 标准化：去协议、去 www 前缀、去端口、去尾斜杠。

    Examples:
        >>> normalize_url("https://www.example.com:8080/path/")
        'example.com/path'
    """
    if not url:
        return ""
    url = url.strip()
    # 去协议
    url = re.sub(r"^https?://", "", url)
    # 去 www 前缀
    url = re.sub(r"^www\.", "", url)
    # 去端口
    url = re.sub(r":(\d+)(?=/|$)", "", url)
    # 去尾斜杠
    url = url.rstrip("/")
    return url


def extract_domain_key(url: str) -> str:
    """从 URL 提取域名作为 domain_key。

    Examples:
        >>> extract_domain_key("https://www.example.com:8080/path/")
        'example.com'
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        domain = parsed.hostname or ""
    except Exception:
        domain = ""
    if not domain:
        # 回退：手动提取第一段
        domain = re.sub(r"^https?://", "", url.strip())
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split("/")[0].split(":")[0]
    # 去 www 前缀
    domain = re.sub(r"^www\.", "", domain)
    return domain.lower()


def parse_source_json(raw_json: str, source_type: Optional[str] = None) -> list[dict]:
    """解析 BookSource/RssSource JSON，返回标准化字典列表。

    支持数组或单个对象格式的 JSON。自动检测源类型（若未指定）。

    Args:
        raw_json: 源 JSON 字符串
        source_type: "book" 或 "rss"，为 None 时自动检测

    Returns:
        标准化字典列表，每个字典包含 source_type 和 domain_key 字段
    """
    data = json.loads(raw_json)
    if isinstance(data, dict):
        # Legado 真机 Web 服务返回 {"data": [...]} 包装格式，需提取内层数组
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return []

    results: list[dict] = []
    for obj in items:
        if not isinstance(obj, dict) or not obj:
            continue
        st = source_type or _detect_type(obj)
        mapping = BOOK_SOURCE_MAPPING if st == "book" else RSS_SOURCE_MAPPING
        row = _map_fields(obj, mapping, st)
        results.append(row)
    return results


def _detect_type(obj: dict) -> str:
    """自动检测源类型。"""
    if "bookSourceUrl" in obj or "ruleSearch" in obj:
        return "book"
    if "sourceUrl" in obj or "ruleArticles" in obj:
        return "rss"
    # 含 bookSource 前缀字段则认为是书源
    for key in obj:
        if key.startswith("bookSource"):
            return "book"
    return "rss"


def _map_fields(obj: dict, mapping: dict[str, str | Callable], source_type: str) -> dict:
    """按映射表提取字段，补充 source_type 和 domain_key。"""
    row: dict = {}
    for db_col, json_key in mapping.items():
        if callable(json_key):
            row[db_col] = json_key(obj)
        else:
            row[db_col] = obj.get(json_key)
    # 补充元数据字段
    row["source_type"] = source_type
    source_url = row.get("source_url") or ""
    row["domain_key"] = extract_domain_key(source_url)
    # 保留原始 JSON 用于备份/恢复
    row["source_json"] = json.dumps(obj, ensure_ascii=False)
    return row


def deduplicate_sources(sources: list[dict]) -> list[dict]:
    """按 domain_key + source_name 组合去重，保留最新版本。

    当 domain_key + source_name 相同时，保留列表中靠后的（更新的）条目。

    Args:
        sources: 标准化字典列表

    Returns:
        去重后的列表
    """
    seen: dict[tuple, dict] = {}
    for src in sources:
        key = (src.get("domain_key", ""), src.get("source_name", ""))
        seen[key] = src  # 后覆盖前，保留最新
    return list(seen.values())
