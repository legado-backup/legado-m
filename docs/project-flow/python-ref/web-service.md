# Web 服务 — Python 重构参考

> 迁移自 [modules/web-service.md](../modules/web-service.md) 原「Python 重构参考」章节（2026-08-30 拆分）。本文件为 Web 服务 Python 重构实现的唯一权威源。
> Android 侧 API 实现见 [web-service-api.md](../modules/web-service-api.md)；服务生命周期见 [web-service-lifecycle.md](../modules/web-service-lifecycle.md)。
> 小节结构与原文件保持一致，便于溯源。

### FastAPI 路由实现示例

```python
from fastapi import FastAPI, Query, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Optional, List
import json

app = FastAPI(title="Legado Web API")

# ============================================================
# 数据模型
# ============================================================

class ReturnData(BaseModel):
    """统一响应模型"""
    isSuccess: bool = False
    errorMsg: str = "未知错误，请联系开发者!"
    data: Any = None


class Book(BaseModel):
    bookUrl: str
    tocUrl: str = ""
    origin: str = ""
    originName: str = ""
    name: str = ""
    author: str = ""
    kind: Optional[str] = None
    coverUrl: Optional[str] = None
    intro: Optional[str] = None
    type: int = 0
    group: int = 0
    latestChapterTitle: Optional[str] = None
    latestChapterTime: int = 0
    totalChapterNum: int = 0
    durChapterTitle: Optional[str] = None
    durChapterIndex: int = 0
    durChapterPos: int = 0
    durChapterTime: int = 0
    wordCount: Optional[str] = None
    canUpdate: bool = True
    order: int = 0
    originOrder: int = 0
    variable: Optional[str] = None
    syncTime: int = 0


class BookProgress(BaseModel):
    name: str
    author: str
    durChapterIndex: int
    durChapterPos: int
    durChapterTime: int
    durChapterTitle: Optional[str] = None


class BookSource(BaseModel):
    bookSourceUrl: str
    bookSourceName: str
    bookSourceGroup: Optional[str] = None
    bookSourceType: int = 0
    bookUrlPattern: Optional[str] = None
    customOrder: int = 0
    enabled: bool = True
    enabledExplore: bool = True
    enabledCookieJar: bool = True
    searchUrl: Optional[str] = None
    exploreUrl: Optional[str] = None


class RssSource(BaseModel):
    sourceUrl: str
    sourceName: str
    sourceIcon: str = ""
    sourceGroup: Optional[str] = None
    enabled: bool = True
    sortUrl: Optional[str] = None
    ruleArticles: Optional[str] = None
    ruleNextPage: Optional[str] = None
    ruleTitle: Optional[str] = None
    rulePubDate: Optional[str] = None
    ruleDescription: Optional[str] = None
    ruleImage: Optional[str] = None
    ruleLink: Optional[str] = None
    ruleContent: Optional[str] = None


class ReplaceRule(BaseModel):
    id: Optional[int] = None
    name: str = ""
    group: Optional[str] = None
    pattern: str = ""
    replacement: str = ""
    isRegex: bool = True
    isEnabled: bool = True
    scope: Optional[str] = None
    scopeTitle: bool = False
    scopeContent: bool = True
    timeoutMillisecond: int = 3000
    order: Optional[int] = None


# ============================================================
# 响应辅助函数
# ============================================================

def success(data: Any = None) -> JSONResponse:
    """生成成功响应"""
    rd = ReturnData(isSuccess=True, errorMsg="", data=data)
    return JSONResponse(content=rd.model_dump())


def error(msg: str = "") -> JSONResponse:
    """生成错误响应"""
    rd = ReturnData(isSuccess=False, errorMsg=msg)
    return JSONResponse(content=rd.model_dump())


# ============================================================
# 书籍 API
# ============================================================

@app.get("/getBookshelf", summary="获取书架所有书籍")
async def get_bookshelf():
    return success([])


@app.get("/getChapterList", summary="获取指定书籍的章节列表")
async def get_chapter_list(url: str = Query(..., description="书籍bookUrl")):
    return success([])


@app.get("/refreshToc", summary="强制刷新书籍目录")
async def refresh_toc(url: str = Query(..., description="书籍bookUrl")):
    return success([])


@app.get("/getBookContent", summary="获取正文内容")
async def get_book_content(
    url: str = Query(..., description="书籍bookUrl"),
    index: int = Query(..., description="章节索引序号")
):
    return success("")


@app.get("/getReadConfig", summary="获取Web阅读配置")
async def get_read_config():
    return success({})


@app.post("/saveBook", summary="保存书籍（添加或更新）")
async def save_book(book: Book):
    return success("")


@app.post("/deleteBook", summary="删除书籍")
async def delete_book(data: dict):
    return success("")


@app.post("/saveBookProgress", summary="保存阅读进度")
async def save_book_progress(progress: BookProgress):
    return success("")


@app.post("/saveReadConfig", summary="保存Web阅读配置")
async def save_read_config(config: dict):
    return success("")


@app.post("/addLocalBook", summary="添加本地书籍（文件上传）")
async def add_local_book(
    fileName: str = Form(...),
    fileData: UploadFile = File(...)
):
    return success(True)


# ============================================================
# 书源 API
# ============================================================

@app.get("/getBookSource", summary="获取单个书源")
async def get_book_source(url: str = Query(..., description="书源URL")):
    return success({})


@app.get("/getBookSources", summary="获取所有书源")
async def get_book_sources():
    return success([])


@app.post("/saveBookSource", summary="保存单个书源")
async def save_book_source(source: BookSource):
    return success("")


@app.post("/saveBookSources", summary="批量保存书源")
async def save_book_sources(sources: List[BookSource]):
    return success([])


@app.post("/deleteBookSources", summary="批量删除书源")
async def delete_book_sources(sources: List[BookSource]):
    return success("已执行")


# ============================================================
# RSS API
# ============================================================

@app.get("/getRssSource", summary="获取单个RSS源")
async def get_rss_source(url: str = Query(..., description="RSS源URL")):
    return success({})


@app.get("/getRssSources", summary="获取所有RSS源")
async def get_rss_sources():
    return success([])


@app.post("/saveRssSource", summary="保存单个RSS源")
async def save_rss_source(source: RssSource):
    return success("")


@app.post("/saveRssSources", summary="批量保存RSS源")
async def save_rss_sources(sources: List[RssSource]):
    return success([])


@app.post("/deleteRssSources", summary="批量删除RSS源")
async def delete_rss_sources(sources: List[RssSource]):
    return success("已执行")


# ============================================================
# 替换规则 API
# ============================================================

@app.get("/getReplaceRules", summary="获取所有替换规则")
async def get_replace_rules():
    return success([])


@app.post("/saveReplaceRule", summary="保存替换规则")
async def save_replace_rule(rule: ReplaceRule):
    return success("")


@app.post("/deleteReplaceRule", summary="删除替换规则")
async def delete_replace_rule(data: dict):
    return success("")


@app.post("/testReplaceRule", summary="测试替换规则")
async def test_replace_rule(data: dict):
    return success("")
```

### WebSocket Python 实现示例

#### 搜索 WebSocket

```python
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/searchBook")
async def websocket_search_book(websocket: WebSocket):
    await websocket.accept()

    async def heartbeat():
        """每30秒发送ping保持连接"""
        while True:
            try:
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        message = await websocket.receive_text()

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send_text("数据必须为Json格式")
            await websocket.close(code=1000, reason="Search finish")
            return

        key = data.get("key")
        if not key or not key.strip():
            await websocket.send_text("关键词不能为空")
            await websocket.close(code=1000, reason="Search finish")
            return

        # 执行搜索，逐批返回结果
        async for batch_results in search_books(key):
            await websocket.send_text(json.dumps(batch_results, ensure_ascii=False))

        await websocket.close(code=1000, reason="Search finish")

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
```

#### 书源调试 WebSocket

```python
@app.websocket("/bookSourceDebug")
async def websocket_book_source_debug(websocket: WebSocket):
    await websocket.accept()

    heartbeat_task = asyncio.create_task(heartbeat_30s(websocket))

    try:
        message = await websocket.receive_text()

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send_text("数据必须为Json格式")
            await websocket.close(code=1000, reason="调试结束")
            return

        tag = data.get("tag")
        key = data.get("key")

        if not tag or not key:
            await websocket.send_text("tag和key不能为空")
            await websocket.close(code=1000, reason="调试结束")
            return

        # 执行调试，逐行发送日志
        async for log_line in debug_book_source(tag, key):
            await websocket.send_text(log_line)

        await websocket.close(code=1000, reason="调试结束")

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
```

#### RSS 源调试 WebSocket

```python
@app.websocket("/rssSourceDebug")
async def websocket_rss_source_debug(websocket: WebSocket):
    await websocket.accept()

    heartbeat_task = asyncio.create_task(heartbeat_30s(websocket))

    try:
        message = await websocket.receive_text()

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send_text("数据必须为Json格式")
            await websocket.close(code=1000, reason="调试结束")
            return

        tag = data.get("tag")

        if not tag:
            await websocket.send_text("tag不能为空")
            await websocket.close(code=1000, reason="调试结束")
            return

        # 执行RSS源调试，逐行发送日志
        async for log_line in debug_rss_source(tag):
            await websocket.send_text(log_line)

        await websocket.close(code=1000, reason="调试结束")

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()


async def heartbeat_30s(websocket: WebSocket):
    """心跳保持函数"""
    while True:
        try:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
        except Exception:
            break
```
