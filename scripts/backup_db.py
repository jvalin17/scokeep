#!/usr/bin/env python3
"""Backup Postgres (Neon) data for Scokeep — app-level safety net before migrations.

Writes a timestamped JSON dump of playground / game / round tables under backups/.

Usage:
  DATABASE_URL=postgresql://... python scripts/backup_db.py
  PROD_DATABASE_URL=postgresql://... python scripts/backup_db.py --label prod

Requires: asyncpg (already a project dependency via SQLAlchemy stack — install asyncpg if needed)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

TABLES = ("playground", "game", "round")


def _normalize_url(url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        url = url.replace(prefix, "postgresql://")
    return url.split("?")[0]


def resolve_database_url(explicit: str | None = None) -> str:
    """Pick DATABASE_URL or PROD_DATABASE_URL from env / CLI."""
    url = (explicit or "").strip() or os.environ.get("DATABASE_URL", "").strip()
    if not url:
        url = os.environ.get("PROD_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("ERROR: Set DATABASE_URL or PROD_DATABASE_URL (or pass --url)")
    if url.startswith("sqlite"):
        raise SystemExit("ERROR: backup_db.py only supports PostgreSQL URLs")
    return _normalize_url(url)


def default_backup_path(label: str, backup_dir: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label) or "db"
    return backup_dir / f"scokeep-{safe_label}-{stamp}.json"


def _serialize_row(row) -> dict:
    data = dict(row)
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


async def fetch_backup(database_url: str) -> dict:
    import asyncpg

    conn = await asyncpg.connect(database_url, ssl="require")
    try:
        payload = {
            "created_at": datetime.now(UTC).isoformat(),
            "tables": {},
        }
        for table in TABLES:
            rows = await conn.fetch(f"SELECT * FROM {table} ORDER BY id")  # noqa: S608
            payload["tables"][table] = [_serialize_row(row) for row in rows]
            payload["tables"][f"{table}_count"] = len(payload["tables"][table])
        return payload
    finally:
        await conn.close()


def write_backup(payload: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return output_path


async def run_backup(
    database_url: str,
    output_path: Path,
) -> Path:
    payload = await fetch_backup(database_url)
    return write_backup(payload, output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backup Scokeep Postgres tables to JSON")
    parser.add_argument("--url", default=None, help="Postgres URL (overrides env)")
    parser.add_argument("--label", default="backup", help="Filename label")
    parser.add_argument(
        "--out",
        default=None,
        help="Output file path (default: backups/scokeep-<label>-<utc>.json)",
    )
    parser.add_argument(
        "--dir",
        default="backups",
        help="Backup directory when --out is not set",
    )
    args = parser.parse_args(argv)

    database_url = resolve_database_url(args.url)
    output_path = Path(args.out) if args.out else default_backup_path(args.label, Path(args.dir))

    print(f"Backing up to {output_path} ...")
    path = asyncio.run(run_backup(database_url, output_path))
    print(f"OK: wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
