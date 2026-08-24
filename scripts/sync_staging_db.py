#!/usr/bin/env python3
"""Incremental sync: copy new/updated prod data to staging.

No DELETE — staging is append-only. Uses UPSERT (ON CONFLICT DO UPDATE)
for playground and game, INSERT ON CONFLICT DO NOTHING for round.

Usage:
  PROD_DATABASE_URL=... STAGING_DATABASE_URL=... python scripts/sync_staging_db.py

Requires: asyncpg (pip install asyncpg)
"""

import asyncio
import os
import sys


def _get_urls():
    prod = os.environ.get("PROD_DATABASE_URL", "")
    staging = os.environ.get("STAGING_DATABASE_URL", "")
    if not prod or not staging:
        print("ERROR: Set PROD_DATABASE_URL and STAGING_DATABASE_URL")
        sys.exit(1)
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        prod = prod.replace(prefix, "postgresql://")
        staging = staging.replace(prefix, "postgresql://")
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
        await _sync_table(
            prod_conn,
            staging_conn,
            "playground",
            upsert_cols=["name", "pin_hash", "players", "insights", "updated_at"],
        )
        await _sync_table(
            prod_conn,
            staging_conn,
            "game",
            upsert_cols=[
                "players",
                "settings",
                "current_round",
                "total_rounds",
                "phase",
                "dealer_index",
                "status",
                "updated_at",
                "finished_at",
            ],
        )
        await _sync_table(prod_conn, staging_conn, "round")

        print("\nSync complete.")
    finally:
        await prod_conn.close()
        await staging_conn.close()


async def _sync_table(prod_conn, staging_conn, table, upsert_cols=None):
    """Sync a single table from prod to staging.

    If upsert_cols is provided, uses ON CONFLICT (id) DO UPDATE for those columns.
    Otherwise uses ON CONFLICT DO NOTHING (append-only).
    """
    rows = await prod_conn.fetch(f"SELECT * FROM {table}")  # noqa: S608
    if not rows:
        print(f"  {table}: 0 rows in prod (skipped)")
        return

    columns = list(rows[0].keys())
    col_list = ", ".join(columns)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))

    if upsert_cols:
        update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in upsert_cols)
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "  # noqa: S608
            f"ON CONFLICT (id) DO UPDATE SET {update_clause}"
        )
    else:
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"  # noqa: S608

    inserted = 0
    for row in rows:
        values = [row[col] for col in columns]
        result = await staging_conn.execute(sql, *values)
        if "INSERT" in result:
            inserted += 1

    print(f"  {table}: {len(rows)} prod rows, {inserted} new/updated in staging")


if __name__ == "__main__":
    asyncio.run(sync())
