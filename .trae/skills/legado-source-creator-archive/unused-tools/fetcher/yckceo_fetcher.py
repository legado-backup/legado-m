"""yckceo.com 书源/订阅源合集爬取 + 下载 + 增量更新。

列表页 URL 模式：
  书源: https://www.yckceo.com/yuedu/shuyuans/index.html
  订阅源: https://www.yckceo.com/yuedu/rsss/index.html
  分页: index_{page}.html（第 2 页起）

详情页 URL 模式：
  书源: https://www.yckceo.com/yuedu/shuyuans/content/id/{id}.html
  订阅源: https://www.yckceo.com/yuedu/rsss/content/id/{id}.html

增量更新：对比 Collection 表的 remote_id + date，仅下载新增/更新的合集。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from legado_client.fetcher.http_client import shared_client
from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
from legado_client.storage.database import get_session_factory
from legado_client.storage.models import Collection
from legado_client.storage.repository import bulk_upsert
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.yckceo_fetcher")

_BASE_URL = "https://www.yckceo.com"

# 源类型 → URL 路径片段映射
_TYPE_PATH: dict[str, tuple[str, str]] = {
    "book": ("shuyuans", "yuedu/shuyuans"),
    "rss": ("rsss", "yuedu/rsss"),
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class CollectionItem:
    """列表页解析出的合集条目。"""

    __slots__ = ("remote_id", "title", "user_name", "source_count",
                 "download_count", "date", "detail_url")

    def __init__(
        self,
        remote_id: str,
        title: str,
        user_name: str = "",
        source_count: int = 0,
        download_count: int = 0,
        date: str = "",
        detail_url: str = "",
    ) -> None:
        self.remote_id = remote_id
        self.title = title
        self.user_name = user_name
        self.source_count = source_count
        self.download_count = download_count
        self.date = date
        self.detail_url = detail_url


# ---------------------------------------------------------------------------
# 列表页解析
# ---------------------------------------------------------------------------

async def fetch_list(
    source_type: str = "book",
    max_pages: int = 0,
    incremental: bool = False,
) -> list[CollectionItem]:
    """抓取合集列表页，支持分页和增量更新。

    Args:
        source_type: "book" 或 "rss"
        max_pages: 最大抓取页数，0 表示全部
        incremental: 增量模式，遇到已存在的合集时停止

    Returns:
        合集条目列表
    """
    _, path = _TYPE_PATH[source_type]
    all_items: list[CollectionItem] = []
    page = 1
    known_ids: set[str] = set()

    if incremental:
        known_ids = await _get_known_remote_ids(source_type)

    while True:
        url = _list_url(path, page)
        logger.info("抓取列表页: %s", url)

        try:
            html = await shared_client.get_text(url)
        except Exception as e:
            logger.error("列表页请求失败 %s: %s", url, e)
            break

        items = _parse_list_page(html, source_type)
        if not items:
            logger.info("列表页无更多条目，停止分页")
            break

        all_items.extend(items)
        logger.info("第 %d 页: 解析到 %d 个合集", page, len(items))

        # 增量模式：遇到已知合集时停止
        if incremental:
            should_stop = False
            for item in items:
                if item.remote_id in known_ids:
                    logger.info("增量模式: 遇到已知合集 %s，停止", item.remote_id)
                    should_stop = True
                    break
            if should_stop:
                # 只保留未知合集
                all_items = [it for it in all_items if it.remote_id not in known_ids]
                break

        # 检查是否有下一页
        if not _has_next_page(html):
            break

        page += 1
        if max_pages > 0 and page > max_pages:
            logger.info("已达最大页数 %d，停止", max_pages)
            break

    return all_items


def _list_url(path: str, page: int) -> str:
    """构造列表页 URL。"""
    if page <= 1:
        return f"{_BASE_URL}/{path}/index.html"
    return f"{_BASE_URL}/{path}/index_{page}.html"


def _parse_list_page(html: str, source_type: str) -> list[CollectionItem]:
    """解析列表页 HTML，提取合集条目。多套选择器容错降级。"""
    soup = BeautifulSoup(html, "lxml")
    items: list[CollectionItem] = []

    # 选择器组1: ylist 卡片结构（yckceo 实际布局）
    ylist_divs = soup.select("div.ylist")
    if ylist_divs:
        for div in ylist_divs:
            item = _parse_ylist_div(div, source_type)
            if item:
                items.append(item)
        return items

    # 选择器组2: table 结构
    rows = soup.select("table.table tbody tr")
    if rows:
        for row in rows:
            item = _parse_table_row(row, source_type)
            if item:
                items.append(item)
        return items

    # 选择器组3: div/card 结构
    cards = soup.select("div.collection-card") or soup.select("div.item")
    if cards:
        for card in cards:
            item = _parse_card(card, source_type)
            if item:
                items.append(item)
        return items

    # 选择器组4: 通用链接提取（最低保障）
    links = soup.select("a[href*='/content/id/']")
    for link in links:
        href = link.get("href", "")
        remote_id = _extract_id_from_url(href)
        if remote_id:
            items.append(CollectionItem(
                remote_id=remote_id,
                title=link.get_text(strip=True),
                detail_url=_normalize_url(href),
            ))

    return items


def _parse_ylist_div(div, source_type: str) -> Optional[CollectionItem]:
    """解析 yckceo ylist 卡片结构。"""
    try:
        link_tag = div.select_one("h2 a[href*='/content/id/']")
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        remote_id = _extract_id_from_url(href)
        if not remote_id:
            return None

        title = link_tag.get_text(strip=True)
        user_name = ""
        source_count = 0
        download_count = 0
        date = ""

        # 提取日期（p.m-right）
        date_tag = div.select_one("p.m-right")
        if date_tag:
            date = date_tag.get_text(strip=True)

        # 提取用户名（span.layui-badge-rim 含"用户:"）
        for span in div.select("span.layui-badge-rim"):
            text = span.get_text(strip=True)
            if text.startswith("用户:"):
                user_name = text.replace("用户:", "").strip()
            elif text.startswith("源数量:"):
                source_count = _parse_int(text.replace("源数量:", ""))
            elif text.startswith("下载:"):
                download_count = _parse_int(text.replace("下载:", ""))

        return CollectionItem(
            remote_id=remote_id,
            title=title,
            user_name=user_name,
            source_count=source_count,
            download_count=download_count,
            date=date,
            detail_url=_normalize_url(href),
        )
    except Exception as e:
        logger.debug("解析 ylist 卡片失败: %s", e)
        return None


def _parse_table_row(row, source_type: str) -> Optional[CollectionItem]:
    """解析 table 行。"""
    try:
        link_tag = row.select_one("a[href*='/content/id/']")
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        remote_id = _extract_id_from_url(href)
        if not remote_id:
            return None

        tds = row.select("td")
        title = link_tag.get_text(strip=True)
        user_name = tds[1].get_text(strip=True) if len(tds) > 1 else ""
        source_count = _parse_int(tds[2].get_text(strip=True)) if len(tds) > 2 else 0
        download_count = _parse_int(tds[3].get_text(strip=True)) if len(tds) > 3 else 0
        date = tds[4].get_text(strip=True) if len(tds) > 4 else ""

        return CollectionItem(
            remote_id=remote_id,
            title=title,
            user_name=user_name,
            source_count=source_count,
            download_count=download_count,
            date=date,
            detail_url=_normalize_url(href),
        )
    except Exception as e:
        logger.debug("解析 table 行失败: %s", e)
        return None


def _parse_card(card, source_type: str) -> Optional[CollectionItem]:
    """解析 card 结构。"""
    try:
        link_tag = card.select_one("a[href*='/content/id/']")
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        remote_id = _extract_id_from_url(href)
        if not remote_id:
            return None

        title = link_tag.get_text(strip=True)
        user_tag = card.select_one(".user") or card.select_one(".author")
        user_name = user_tag.get_text(strip=True) if user_tag else ""
        count_tag = card.select_one(".count") or card.select_one(".source-count")
        source_count = _parse_int(count_tag.get_text(strip=True)) if count_tag else 0
        date_tag = card.select_one(".date") or card.select_one("time")
        date = date_tag.get_text(strip=True) if date_tag else ""

        return CollectionItem(
            remote_id=remote_id,
            title=title,
            user_name=user_name,
            source_count=source_count,
            date=date,
            detail_url=_normalize_url(href),
        )
    except Exception as e:
        logger.debug("解析 card 失败: %s", e)
        return None


def _has_next_page(html: str) -> bool:
    """检测列表页是否有下一页。"""
    soup = BeautifulSoup(html, "lxml")
    # 常见分页链接
    next_link = (
        soup.select_one("a.next") or
        soup.select_one("li.next a") or
        soup.select_one("a:-soup-contains('下一页')") or
        soup.select_one("a[rel='next']")
    )
    return next_link is not None


# ---------------------------------------------------------------------------
# 详情页解析 + JSON 下载
# ---------------------------------------------------------------------------

async def fetch_collection_json(
    item: CollectionItem,
    source_type: str = "book",
) -> Optional[str]:
    """从 yckceo 下载源 JSON 内容。

    优先直接构造 JSON URL（/json/id/{id}.json），回退到详情页解析。
    """
    # 优先：直接构造 JSON URL（最可靠）
    path_segment = _TYPE_PATH[source_type][1]  # e.g. "yuedu/shuyuans"
    direct_json_url = f"{_BASE_URL}/{path_segment}/json/id/{item.remote_id}.json"
    try:
        content = await shared_client.get_text(direct_json_url)
        logger.info("直接下载 JSON 成功: %s", direct_json_url)
        return content
    except Exception as e:
        logger.debug("直接 JSON URL 下载失败 %s: %s，回退到详情页解析", direct_json_url, e)

    # 回退：从详情页解析 JSON URL
    if not item.detail_url:
        logger.warning("合集 %s 无详情页 URL", item.remote_id)
        return None

    try:
        html = await shared_client.get_text(item.detail_url)
    except Exception as e:
        logger.error("详情页请求失败 %s: %s", item.detail_url, e)
        return None

    json_url = _extract_json_url(html, source_type)
    if not json_url:
        logger.warning("详情页未找到 JSON 下载链接: %s", item.detail_url)
        return None

    try:
        content = await shared_client.get_text(json_url)
        return content
    except Exception as e:
        logger.error("JSON 下载失败 %s: %s", json_url, e)
        return None


def _extract_json_url(html: str, source_type: str) -> Optional[str]:
    """从详情页 HTML 提取 JSON 下载链接。多套选择器容错。"""
    soup = BeautifulSoup(html, "lxml")

    # 选择器组0: yuedu:// 协议链接（yckceo 实际格式）
    for link in soup.select("a[href*='yuedu://']"):
        href = link.get("href", "")
        # 提取 src 参数中的真实 URL
        match = re.search(r'src=(https?://[^\s&"\'<>]+\.json[^\s&"\'<>]*)', href)
        if match:
            return match.group(1)

    # 选择器组1: 带 download 属性或 JSON 相关文本的链接
    patterns = [
        "a[href$='.json']",
        "a[download]",
        "a:-soup-contains('下载')",
        "a:-soup-contains('JSON')",
        "a:-soup-contains('导入')",
    ]
    for pattern in patterns:
        link = soup.select_one(pattern)
        if link:
            href = link.get("href", "")
            if href:
                return _normalize_url(href)

    # 选择器组2: 在 script 标签或 data 属性中查找 URL
    for script in soup.select("script"):
        text = script.string or ""
        # 匹配常见 JSON URL 模式
        match = re.search(r'(https?://[^\s"\'<>]+\.json[^\s"\'<>]*)', text)
        if match:
            return match.group(1)
        # 匹配 raw.githubusercontent.com
        match = re.search(r'(https?://raw\.githubusercontent\.com/[^\s"\'<>]+)', text)
        if match:
            return match.group(1)

    # 选择器组3: 隐藏 input 中查找 JSON URL
    for inp in soup.select("input#jsonurl"):
        val = inp.get("value", "")
        if val and "http" in val:
            return val

    return None


# ---------------------------------------------------------------------------
# 增量更新
# ---------------------------------------------------------------------------

async def _get_known_remote_ids(source_type: str) -> set[str]:
    """从数据库获取已存在的合集 remote_id 集合。"""
    sf = get_session_factory()
    if sf is None:
        return set()

    from sqlalchemy import select
    async with sf() as session:
        stmt = select(Collection.remote_id).where(
            Collection.source_type == source_type
        )
        result = await session.execute(stmt)
        return {row[0] for row in result.all()}


async def _upsert_collection(item: CollectionItem, source_type: str) -> None:
    """插入或更新合集记录。"""
    sf = get_session_factory()
    if sf is None:
        logger.warning("数据库不可用，跳过合集入库")
        return

    from sqlalchemy import select
    async with sf() as session:
        async with session.begin():
            stmt = select(Collection).where(
                Collection.remote_id == item.remote_id,
                Collection.source_type == source_type,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.title = item.title
                existing.user_name = item.user_name
                existing.source_count = item.source_count
                existing.download_count = item.download_count
                existing.date = item.date
                existing.url = item.detail_url
                existing.last_fetched_at = datetime.now()
            else:
                col = Collection(
                    source_type=source_type,
                    remote_id=item.remote_id,
                    title=item.title,
                    user_name=item.user_name,
                    source_count=item.source_count,
                    download_count=item.download_count,
                    date=item.date,
                    url=item.detail_url,
                    status="pending",
                    last_fetched_at=datetime.now(),
                )
                session.add(col)


async def _mark_collection_status(
    remote_id: str, source_type: str, status: str,
) -> None:
    """更新合集状态。"""
    sf = get_session_factory()
    if sf is None:
        return

    from sqlalchemy import update
    async with sf() as session:
        async with session.begin():
            stmt = (
                update(Collection)
                .where(
                    Collection.remote_id == remote_id,
                    Collection.source_type == source_type,
                )
                .values(status=status)
            )
            await session.execute(stmt)


# ---------------------------------------------------------------------------
# 高层接口
# ---------------------------------------------------------------------------

async def fetch_all(
    source_type: str = "book",
    max_pages: int = 0,
    incremental: bool = True,
    max_collections: int = 0,
) -> dict:
    """抓取并导入所有合集。

    Args:
        source_type: "book" 或 "rss"
        max_pages: 最大列表页数，0 表示全部
        incremental: 增量模式，仅下载新增/更新的合集
        max_collections: 最大合集下载数，0 表示全部

    Returns:
        {"collections": 合集总数, "sources_imported": 导入源数量, "errors": 错误数}
    """
    result = {"collections": 0, "sources_imported": 0, "errors": 0}

    # 1. 抓取列表
    items = await fetch_list(source_type, max_pages, incremental)
    if not items:
        logger.info("无新合集需要下载")
        return result

    if max_collections > 0:
        items = items[:max_collections]

    result["collections"] = len(items)
    logger.info("待下载 %d 个合集", len(items))

    # 2. 逐个下载并导入
    for item in items:
        # 入库合集元数据
        await _upsert_collection(item, source_type)
        await _mark_collection_status(item.remote_id, source_type, "downloading")

        json_str = await fetch_collection_json(item, source_type)
        if not json_str:
            await _mark_collection_status(item.remote_id, source_type, "failed")
            result["errors"] += 1
            continue

        # 解析并入库源
        try:
            parsed = parse_source_json(json_str, source_type)
            if not parsed:
                logger.warning("合集 %s 解析结果为空", item.remote_id)
                await _mark_collection_status(item.remote_id, source_type, "failed")
                result["errors"] += 1
                continue

            deduped = deduplicate_sources(parsed)
            imported = await bulk_upsert(deduped)
            result["sources_imported"] += imported
            await _mark_collection_status(item.remote_id, source_type, "completed")
            logger.info(
                "合集 %s: 解析 %d 个源，去重后 %d，新增 %d",
                item.remote_id, len(parsed), len(deduped), imported,
            )
        except Exception as e:
            logger.error("合集 %s 入库失败: %s", item.remote_id, e)
            await _mark_collection_status(item.remote_id, source_type, "failed")
            result["errors"] += 1

    return result


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _extract_id_from_url(url: str) -> str:
    """从 URL 提取合集 ID。"""
    match = re.search(r"/id/(\d+)", url)
    return match.group(1) if match else ""


def _normalize_url(url: str) -> str:
    """URL 补全为绝对路径。"""
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"{_BASE_URL}{url}"
    return url


def _parse_int(text: str) -> int:
    """从文本中提取整数。"""
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0
