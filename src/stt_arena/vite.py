from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from stt_arena.assets_util import MANIFEST_PATH
from stt_arena.config import Settings

ENTRY_KEY = "src/main.ts"


@dataclass(frozen=True, slots=True)
class HtmlTag:
    tag: str
    attrs: dict[str, str]


def vite_tags(settings: Settings) -> list[HtmlTag]:
    if settings.is_dev:
        origin = settings.vite_origin
        return [
            HtmlTag("script", {"type": "module", "src": f"{origin}/@vite/client"}),
            HtmlTag("script", {"type": "module", "src": f"{origin}/src/main.ts"}),
        ]

    manifest = _load_manifest()
    entry = manifest.get(ENTRY_KEY)
    if entry is None:
        msg = (
            f"Vite manifest missing entry {ENTRY_KEY!r}. "
            "Run `uv run build` before starting in production mode."
        )
        raise RuntimeError(msg)

    tags: list[HtmlTag] = []
    for css_file in entry.get("css", []):
        tags.append(
            HtmlTag("link", {"rel": "stylesheet", "href": f"/static/dist/{css_file}"})
        )
    tags.append(
        HtmlTag(
            "script",
            {"type": "module", "src": f"/static/dist/{entry['file']}"},
        )
    )
    return tags


@lru_cache
def _load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        msg = (
            f"Vite manifest not found at {MANIFEST_PATH}. "
            "Run `uv run build` first."
        )
        raise RuntimeError(msg)
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
