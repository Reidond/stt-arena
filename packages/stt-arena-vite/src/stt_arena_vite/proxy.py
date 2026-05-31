"""Proxy Vite dev asset paths through FastAPI over a Unix socket."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import cast

import httpx
import websockets
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from starlette.websockets import WebSocketDisconnect

from stt_arena_vite.settings import ViteSettings

logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _create_vite_dev_client(settings: ViteSettings) -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(uds=settings.resolved_vite_socket_path)
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=20)
    return httpx.AsyncClient(transport=transport, limits=limits, timeout=30.0)


async def start_vite_dev_proxy(app: FastAPI, settings: ViteSettings) -> None:
    if settings.is_dev:
        app.state.vite_dev_client = _create_vite_dev_client(settings)


async def stop_vite_dev_proxy(app: FastAPI) -> None:
    client = getattr(app.state, "vite_dev_client", None)
    if client is None:
        return
    await client.aclose()
    del app.state.vite_dev_client


def _vite_dev_client(request: Request) -> httpx.AsyncClient:
    client = getattr(request.app.state, "vite_dev_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Vite dev proxy is not ready")
    return cast(httpx.AsyncClient, client)


async def _proxy_to_vite(
    request: Request,
    settings: ViteSettings,
    path: str,
) -> Response:
    query = request.url.query
    target = f"http://vite/{path}"
    if query:
        target = f"{target}?{query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "host"
    }

    try:
        proxied = await _vite_dev_client(request).request(
            request.method,
            target,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        detail = (
            "Vite dev server unavailable at "
            f"{settings.resolved_vite_socket_path}"
        )
        raise HTTPException(
            status_code=502,
            detail=detail,
        ) from exc

    response_headers = {
        key: value
        for key, value in proxied.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
    )


async def _proxy_vite_websocket(
    websocket: WebSocket,
    settings: ViteSettings,
) -> None:
    query = websocket.url.query
    target = "ws://vite/@vite/ws"
    if query:
        target = f"{target}?{query}"

    browser_protocols = {
        protocol.strip()
        for protocol in websocket.headers.get("sec-websocket-protocol", "").split(",")
        if protocol.strip()
    }
    subprotocol = next(
        (
            protocol
            for protocol in ("vite-hmr", "vite-ping")
            if protocol in browser_protocols
        ),
        None,
    )
    await websocket.accept(subprotocol=subprotocol)
    try:
        async with websockets.unix_connect(
            settings.resolved_vite_socket_path,
            uri=target,
            origin=websocket.headers.get("origin"),
            subprotocols=[subprotocol] if subprotocol else None,
            additional_headers={
                "user-agent": websocket.headers.get("user-agent", "stt-arena"),
            },
        ) as vite_ws:
            browser_to_vite = asyncio.create_task(
                _forward_browser_to_vite(websocket, vite_ws)
            )
            vite_to_browser = asyncio.create_task(
                _forward_vite_to_browser(websocket, vite_ws)
            )
            done, pending = await asyncio.wait(
                {browser_to_vite, vite_to_browser},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Vite websocket proxy failed")
        with suppress(RuntimeError):
            await websocket.close(code=1011)


async def _forward_browser_to_vite(
    websocket: WebSocket,
    vite_ws: websockets.ClientConnection,
) -> None:
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                await vite_ws.close()
                return
            if text := message.get("text"):
                await vite_ws.send(text)
            elif data := message.get("bytes"):
                await vite_ws.send(data)
    except WebSocketDisconnect:
        await vite_ws.close()


async def _forward_vite_to_browser(
    websocket: WebSocket,
    vite_ws: websockets.ClientConnection,
) -> None:
    with suppress(RuntimeError, WebSocketDisconnect, websockets.ConnectionClosed):
        async for message in vite_ws:
            if isinstance(message, bytes):
                await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)


def register_vite_dev_proxy(
    app: FastAPI,
    settings_factory: Callable[[], ViteSettings],
) -> None:
    async def proxy_node_modules(path: str, request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"node_modules/{path}")

    async def proxy_react_refresh(request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, "@react-refresh")

    async def proxy_vite_client(path: str, request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@vite/{path}")

    async def proxy_vite_fs(path: str, request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@fs/{path}")

    async def proxy_vite_id(path: str, request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@id/{path}")

    async def proxy_src(path: str, request: Request) -> Response:
        settings = settings_factory()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"src/{path}")

    async def proxy_vite_ws(websocket: WebSocket) -> None:
        settings = settings_factory()
        if not settings.is_dev:
            await websocket.close(code=1008)
            return
        await _proxy_vite_websocket(websocket, settings)

    for handler, route in (
        (proxy_node_modules, "/node_modules/{path:path}"),
        (proxy_react_refresh, "/@react-refresh"),
        (proxy_vite_client, "/@vite/{path:path}"),
        (proxy_vite_fs, "/@fs/{path:path}"),
        (proxy_vite_id, "/@id/{path:path}"),
        (proxy_src, "/src/{path:path}"),
    ):
        app.api_route(route, methods=["GET", "HEAD"], include_in_schema=False)(handler)

    app.websocket("/@vite/ws")(proxy_vite_ws)
