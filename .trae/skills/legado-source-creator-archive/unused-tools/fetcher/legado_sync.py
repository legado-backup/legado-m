"""Legado 真机源数据拉取。

通过 Legado Web 接口从真机拉取书源/订阅源。
LegadoWebClient 完整实现在阶段三，此处先定义接口和基本实现。

接口文档（Legado 内置 Web 服务）：
- GET /getBookSources → 返回 BookSource JSON 数组（ReturnData 包装）
- GET /getRssSources → 返回 RssSource JSON 数组（ReturnData 包装）
- POST /saveBookSources → 批量保存书源
- POST /saveRssSources → 批量保存订阅源
"""
from __future__ import annotations

import json
from typing import Optional

import httpx

from legado_client.storage.repository import bulk_upsert
from legado_client.utils.config import config
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.legado_sync")

# 源类型 → API 路径
_API_PATH: dict[str, str] = {
    "book": "/getBookSources",
    "rss": "/getRssSources",
}


def _extract_source_list(raw_json: str, source_type: str) -> list[dict]:
    """从设备返回的 JSON 中提取原始源 dict 列表。

    设备返回格式可能为：
    - ReturnData 包装: {"isSuccess": true, "data": [...]}
    - 裸数组: [...]
    - 单个对象: {...}
    """
    data = json.loads(raw_json)
    if isinstance(data, dict):
        # ReturnData 包装格式
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return []

    # 过滤非 dict 和空对象，注入 source_type
    result = []
    for item in items:
        if not isinstance(item, dict) or not item:
            continue
        item["source_type"] = source_type
        result.append(item)
    return result


async def pull_from_device(
    source_type: str = "book",
    host: Optional[str] = None,
    port: Optional[int] = None,
    auth_token: Optional[str] = None,
) -> dict:
    """从 Legado 真机拉取源数据。

    Args:
        source_type: "book" 或 "rss"
        host: 设备 IP，默认使用 config.device_host
        port: 设备端口，默认使用 config.device_port
        auth_token: 认证令牌，默认使用 config.device_auth_token

    Returns:
        {"total": 总数, "imported": 新增数, "errors": 错误数}
    """
    device_host = host or config.device_host
    device_port = port or config.device_port
    token = auth_token or config.device_auth_token

    if not device_host:
        return {"total": 0, "imported": 0, "errors": 1,
                "message": "未配置设备 IP，请设置 LEGADO_DEVICE_HOST 或传入 host 参数"}

    api_path = _API_PATH[source_type]
    url = f"http://{device_host}:{device_port}{api_path}"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    logger.info("从设备拉取 %s 源: %s", source_type, url)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0, read=300.0, write=30.0, pool=30.0),
        ) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content = resp.text
    except httpx.ConnectError as e:
        logger.error("设备连接失败 %s: %s", url, e)
        return {"total": 0, "imported": 0, "errors": 1,
                "message": f"设备连接失败: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error("设备返回错误 %s: HTTP %d", url, e.response.status_code)
        return {"total": 0, "imported": 0, "errors": 1,
                "message": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error("设备拉取异常 %s: %s", url, e)
        return {"total": 0, "imported": 0, "errors": 1,
                "message": str(e)}

    # 解析：提取原始 dict 列表（不做字段映射，留给 bulk_upsert 的 _map_source_data）
    try:
        source_list = _extract_source_list(content, source_type)
    except Exception as e:
        logger.error("设备返回数据解析失败: %s", e)
        return {"total": 0, "imported": 0, "errors": 1,
                "message": f"JSON 解析失败: {e}"}

    if not source_list:
        logger.info("设备无 %s 源数据", source_type)
        return {"total": 0, "imported": 0, "errors": 0}

    try:
        imported = await bulk_upsert(source_list)
    except Exception as e:
        logger.error("设备源入库失败: %s", e)
        return {"total": len(source_list), "imported": 0, "errors": 1,
                "message": f"入库失败: {e}"}

    logger.info("设备 %s 源: 解析 %d，新增 %d",
                source_type, len(source_list), imported)
    return {"total": len(source_list), "imported": imported, "errors": 0}


async def push_to_device(
    source_type: str = "book",
    source_ids: Optional[list[int]] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    auth_token: Optional[str] = None,
) -> dict:
    """推送源数据到 Legado 真机（预留接口，阶段三实现）。

    Args:
        source_type: "book" 或 "rss"
        source_ids: 要推送的源 ID 列表，None 表示全部
        host: 设备 IP
        port: 设备端口
        auth_token: 认证令牌

    Returns:
        {"pushed": 推送数量, "errors": 错误数}
    """
    # 简化说明：推送功能在阶段三 LegadoWebClient 中实现 | 已知上限：仅有接口框架 | 升级路径：阶段三补全
    logger.warning("push_to_device 尚未实现，将在阶段三补全")
    return {"pushed": 0, "errors": 1, "message": "功能尚未实现"}
