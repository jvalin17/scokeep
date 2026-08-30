#!/usr/bin/env python3
"""Sync prod data to staging using ID-offset separation.

Prod data occupies IDs < 1,000,000. Staging-created data uses IDs >= 1,000,000.
On each sync: wipe prod-range rows, re-insert prod data, reset sequences.
Staging test data (IDs >= 1M) is preserved across syncs.

Usage:
  PROD_DATABASE_URL=... STAGING_DATABASE_URL=... python scripts/sync_staging_db.py

Requires: asyncpg (pip install asyncpg)
"""

import asyncio
import os
import sys

TABLES = ["playground", "game", "round"]
# Prod IDs stay below this value; staging-created IDs start here.
# At ~1800 rounds/year, prod won't reach 1M for ~555 years.
STAGING_ID_OFFSET = 1_000_000


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

    prod_conn = None
    staging_conn = None

    try:
        print("Connecting to production (read-only)...")
        prod_conn = await asyncpg.connect(prod_url, ssl="require")

        print("Connecting to staging...")
        staging_conn = await asyncpg.connect(staging_url, ssl="require")

        total_errors = 0

        async with staging_conn.transaction():
            # 1a. Delete staging rows that cross-reference prod-range parents
            # (staging games pointing at prod playgrounds would block FK delete)
            result = await staging_conn.execute(
                "DELETE FROM round WHERE game_id IN "
                "(SELECT id FROM game WHERE playground_id < $1 AND id >= $1)",
                STAGING_ID_OFFSET,
            )
            cross_rounds = int(result.split()[-1])
            result = await staging_conn.execute(
                "DELETE FROM game WHERE playground_id < $1 AND id >= $1",
                STAGING_ID_OFFSET,
            )
            cross_games = int(result.split()[-1])
            if cross_rounds or cross_games:
                print(f"  cross-ref: {cross_games} staging games, {cross_rounds} rounds")

            # 1b. Delete prod-range rows (child → parent order)
            for table in reversed(TABLES):
                result = await staging_conn.execute(
                    f"DELETE FROM {table} WHERE id < $1",  # noqa: S608
                    STAGING_ID_OFFSET,
                )
                count = int(result.split()[-1])
                if count:
                    print(f"  {table}: cleared {count} prod-range rows")

            # 2. Insert prod data (parent → child order)
            for table in TABLES:
                rows = await prod_conn.fetch(f"SELECT * FROM {table}")  # noqa: S608
                if not rows:
                    print(f"  {table}: 0 rows in prod (skipped)")
                    continue

                columns = list(rows[0].keys())
                col_list = ", ".join(columns)
                placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
                sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"  # noqa: S608

                errors = 0
                for row in rows:
                    values = [row[col] for col in columns]
                    try:
                        await staging_conn.execute(sql, *values)
                    except Exception as exc:  # noqa: BLE001
                        errors += 1
                        print(f"    WARN: {table} id={row.get('id', '?')}: {exc}")

                total_errors += errors
                status = f"{len(rows)} rows synced"
                if errors:
                    status += f", {errors} errors"
                print(f"  {table}: {status}")

            # 3. Set sequences so new staging IDs start at max(offset, max_id+1)
            for table in TABLES:
                await staging_conn.execute(
                    f"SELECT setval("  # noqa: S608
                    f"pg_get_serial_sequence('{table}', 'id'), "
                    f"GREATEST($1, COALESCE((SELECT MAX(id) FROM {table}), 0) + 1), "
                    f"false)",
                    STAGING_ID_OFFSET,
                )
            print(f"  sequences: reset to >= {STAGING_ID_OFFSET}")

        if total_errors:
            print(f"\nSync finished with {total_errors} errors.")
            sys.exit(1)

        print("\nSync complete.")
    finally:
        if prod_conn:
            await prod_conn.close()
        if staging_conn:
            await staging_conn.close()


if __name__ == "__main__":
    asyncio.run(sync())
