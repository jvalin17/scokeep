"""Content-hashed service worker — CACHE_NAME tracks app-shell files automatically."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

CACHE_NAME_PATTERN = re.compile(r"const CACHE_NAME = '[^']*'")
APP_SHELL_PATTERN = re.compile(r"const APP_SHELL = \[(.*?)\];", re.DOTALL)
SHELL_PATH_PATTERN = re.compile(r"'([^']+)'")


def parse_app_shell_paths(sw_source: str) -> list[str]:
    """Extract URL paths from the APP_SHELL array in sw.js."""
    match = APP_SHELL_PATTERN.search(sw_source)
    if not match:
        raise ValueError("APP_SHELL array not found in service worker source")
    return SHELL_PATH_PATTERN.findall(match.group(1))


def resolve_shell_file(static_dir: Path, url_path: str) -> Path:
    """Map an APP_SHELL URL path to a file under static_dir."""
    if url_path == "/":
        return static_dir / "index.html"
    if url_path.startswith("/static/"):
        return static_dir / url_path.removeprefix("/static/")
    raise ValueError(f"Unexpected app-shell path: {url_path}")


def compute_shell_cache_name(static_dir: Path, sw_source: str) -> str:
    """Hash normalized SW source + every APP_SHELL file → scokeep-<12 hex>."""
    digest = hashlib.sha256()
    normalized = CACHE_NAME_PATTERN.sub("const CACHE_NAME = ''", sw_source, count=1)
    digest.update(normalized.encode("utf-8"))
    for url_path in parse_app_shell_paths(sw_source):
        digest.update(url_path.encode("utf-8"))
        file_path = resolve_shell_file(static_dir, url_path)
        if file_path.is_file():
            digest.update(file_path.read_bytes())
        else:
            digest.update(b"MISSING")
    return f"scokeep-{digest.hexdigest()[:12]}"


def render_service_worker(static_dir: Path) -> str:
    """Read static/sw.js and inject a content-hash CACHE_NAME."""
    source = (static_dir / "sw.js").read_text(encoding="utf-8")
    if not CACHE_NAME_PATTERN.search(source):
        raise ValueError("CACHE_NAME declaration not found in static/sw.js")
    cache_name = compute_shell_cache_name(static_dir, source)
    return CACHE_NAME_PATTERN.sub(f"const CACHE_NAME = '{cache_name}'", source, count=1)
