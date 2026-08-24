#!/usr/bin/env python3
"""Sync staging database from production.

Copies all data from prod Neon DB to staging Neon DB.
Tables: playground, game, round (in dependency order).

Usage:
  PROD_DATABASE_URL=... STAGING_DATABASE_URL=... python scripts/sync_staging_db.py

Requires: asyncpg (pip install asyncpg)
"""

import asyncio
import os
import sys

TABLES = ["playground", "game", "round"]


def _get_urls():
    prod = os.environ.get("PROD_DATABASE_URL", "")
    staging = os.environ.get("STAGING_DATABASE_URL", "")
    if not prod or not staging:
        print("ERROR: Set PROD_DATABASE_URL and STAGING_DATABASE_URL")
        sys.exit(1)
    # Strip asyncpg prefix if present
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        prod = prod.replace(prefix, "postgresql://")
        staging = staging.replace(prefix, "postgresql://")
    # Strip query params (sslmode etc — asyncpg handles SSL automatically)
    prod = prod.split("?")[0]
    staging = staging.split("?")[0]
    return prod, staging


async def sync():
    import asyncpg

    prod_url, staging_url = _get_urls()

    print("Connecting to production (read-only)...")
    prod_conn = await asyncpg.connect(prod_url, ssl="require")

    print("Connecting to staging...")
    staging_conn = await asyncpg.connect(staging_url, ssl="require")

    try:
        # Delete in reverse order (child → parent) to respect foreign keys
        for table in reversed(TABLES):
            await staging_conn.execute(f"DELETE FROM {table}")  # noqa: S608
            print(f"  {table}: cleared")

        # Insert in forward order (parent → child)
        for table in TABLES:
            rows = await prod_conn.fetch(f"SELECT * FROM {table}")  # noqa: S608
            count = len(rows)
            if count == 0:
                print(f"  {table}: 0 rows (skipped)")
                continue

            columns = list(rows[0].keys())
            col_list = ", ".join(columns)
            placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))

            for row in rows:
                values = [row[col] for col in columns]
                await staging_conn.execute(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",  # noqa: S608
                    *values,
                )

            print(f"  {table}: {count} rows synced")

        print("\nSync complete.")
    finally:
        await prod_conn.close()
        await staging_conn.close()


if __name__ == "__main__":
    asyncio.run(sync())
