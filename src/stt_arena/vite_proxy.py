"""Proxy Vite dev asset paths through FastAPI when using backend integration."""

from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

from stt_arena.config import Settings, get_settings

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

VITE_DEV_ROUTES = (
    "/node_modules/{path:path}",
    "/@vite/{path:path}",
    "/@fs/{path:path}",
    "/@id/{path:path}",
    "/src/{path:path}",
)


async def _proxy_to_vite(request: Request, settings: Settings, path: str) -> Response:
    query = request.url.query
    target = f"{settings.vite_origin}/{path}"
    if query:
        target = f"{target}?{query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "host"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            proxied = await client.request(
                request.method,
                target,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Vite dev server unavailable at {settings.vite_origin}",
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


def register_vite_dev_proxy(app: FastAPI) -> None:
    async def proxy_node_modules(path: str, request: Request) -> Response:
        settings = get_settings()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"node_modules/{path}")

    async def proxy_vite_client(path: str, request: Request) -> Response:
        settings = get_settings()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@vite/{path}")

    async def proxy_vite_fs(path: str, request: Request) -> Response:
        settings = get_settings()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@fs/{path}")

    async def proxy_vite_id(path: str, request: Request) -> Response:
        settings = get_settings()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"@id/{path}")

    async def proxy_src(path: str, request: Request) -> Response:
        settings = get_settings()
        if not settings.is_dev:
            raise HTTPException(status_code=404)
        return await _proxy_to_vite(request, settings, f"src/{path}")

    for handler, route in (
        (proxy_node_modules, "/node_modules/{path:path}"),
        (proxy_vite_client, "/@vite/{path:path}"),
        (proxy_vite_fs, "/@fs/{path:path}"),
        (proxy_vite_id, "/@id/{path:path}"),
        (proxy_src, "/src/{path:path}"),
    ):
        app.api_route(route, methods=["GET", "HEAD"], include_in_schema=False)(handler)
