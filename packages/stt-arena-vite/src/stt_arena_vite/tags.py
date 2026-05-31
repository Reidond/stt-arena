from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from stt_arena_vite.settings import ViteSettings

ENTRY_KEY = "src/main.tsx"


@dataclass(frozen=True, slots=True)
class HtmlTag:
    tag: str
    attrs: dict[str, str]


def vite_tags(settings: ViteSettings, *, manifest_path: Path) -> list[HtmlTag]:
    if settings.is_dev:
        return [
            HtmlTag("script", {"type": "module", "src": "/@vite/client"}),
            HtmlTag("script", {"type": "module", "src": "/src/main.tsx"}),
        ]

    manifest = _load_manifest(manifest_path)
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
def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        msg = f"Vite manifest not found at {manifest_path}. Run `uv run build` first."
        raise RuntimeError(msg)
    return json.loads(manifest_path.read_text(encoding="utf-8"))
