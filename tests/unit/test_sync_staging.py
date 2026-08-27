"""Unit tests for the staging DB sync script (scripts/sync_staging_db.py).

Strategy: mock asyncpg.connect so no real DB connection is needed.
We capture every SQL statement executed on the staging connection and
verify ordering, content, and transactional behaviour.

Schema FK chain: playground → game → round
Delete order (child-first): round, game, playground
Insert order (parent-first): playground, game, round
"""

import asyncio
import contextlib
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

STAGING_ID_OFFSET = 1_000_000
TABLES = ["playground", "game", "round"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(table: str, row_id: int, **extra) -> MagicMock:
    """Return a fake asyncpg Record-like object for *table* with the given id."""
    row = MagicMock()
    base: dict = {"id": row_id}
    base.update(extra)

    row.keys.return_value = list(base.keys())
    row.__getitem__ = lambda self, k: base[k]
    row.get = lambda k, default=None: base.get(k, default)
    return row


def _make_staging_conn(execute_side_effects: list | None = None):
    """Build a mock staging asyncpg connection with a working transaction context."""
    conn = AsyncMock()

    # Track every execute call for assertions
    conn.execute_calls: list[tuple] = []

    if execute_side_effects:
        conn.execute.side_effect = execute_side_effects
    else:
        # Default: DELETE returns "DELETE 0", setval returns nothing
        async def default_execute(sql, *args):
            if sql.strip().upper().startswith("DELETE"):
                return "DELETE 0"
            return None

        conn.execute.side_effect = default_execute

    # transaction() must be a plain callable returning an async CM (not a coroutine).
    txn_cm = AsyncMock()
    txn_cm.__aenter__ = AsyncMock(return_value=None)
    txn_cm.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=txn_cm)

    return conn


def _make_prod_conn(rows_by_table: dict[str, list]) -> AsyncMock:
    """Build a mock prod asyncpg connection whose fetch() returns pre-set rows."""
    conn = AsyncMock()

    async def fetch(sql, *args):
        for table in TABLES:
            if table in sql:
                return rows_by_table.get(table, [])
        return []

    conn.fetch.side_effect = fetch
    return conn


def _run(coro):
    """Run a coroutine synchronously (avoids pytest-asyncio dependency for pure mocks)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Import the real sync function under test
# ---------------------------------------------------------------------------


def _import_sync():
    import importlib
    import sys

    # Ensure a fresh import so patches on asyncpg apply cleanly
    project_root = str(pathlib.Path(__file__).parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import scripts.sync_staging_db as m

    importlib.reload(m)
    return m.sync


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def prod_rows():
    """One prod-range row per table (id < 1M)."""
    return {
        "playground": [_make_row("playground", 1, name="Prod PG", pin_hash="x", share_code="abc")],
        "game": [_make_row("game", 1, playground_id=1)],
        "round": [_make_row("round", 1, game_id=1)],
    }


@pytest.fixture()
def staging_execute_log():
    """Mutable list that records every (sql, args) call to staging conn.execute."""
    return []


@pytest.fixture()
def staging_conn(staging_execute_log):
    conn = AsyncMock()

    async def recording_execute(sql, *args):
        staging_execute_log.append((sql.strip(), args))
        if sql.strip().upper().startswith("DELETE"):
            return "DELETE 1"
        return None

    conn.execute.side_effect = recording_execute

    # transaction() must be a plain (non-async) callable that returns an async CM.
    # AsyncMock would make it awaitable (a coroutine), breaking `async with`.
    txn_cm = AsyncMock()
    txn_cm.__aenter__ = AsyncMock(return_value=None)
    txn_cm.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=txn_cm)
    return conn


# ---------------------------------------------------------------------------
# Test 1 — prod rows are inserted into staging
# ---------------------------------------------------------------------------


class TestProdDataInsertedInStaging:
    """After sync, every prod row must appear as an INSERT on the staging conn."""

    def test_prod_data_inserted_in_staging(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        insert_sqls = [sql for sql, _ in staging_execute_log if sql.upper().startswith("INSERT")]

        # One INSERT per table (playground, game, round)
        assert len(insert_sqls) == 3, (
            f"Expected 3 INSERT statements, got {len(insert_sqls)}: {insert_sqls}"
        )
        tables_inserted = {sql.split()[2].lower() for sql in insert_sqls}
        assert tables_inserted == {"playground", "game", "round"}

    def test_inserted_values_include_prod_id(self, prod_rows, staging_conn, staging_execute_log):
        """The values passed to INSERT must include the prod row's id (1)."""
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        insert_calls = [
            (sql, args) for sql, args in staging_execute_log if sql.upper().startswith("INSERT")
        ]

        for _sql, args in insert_calls:
            assert 1 in args, f"Prod row id=1 missing from INSERT args: {args}"


# ---------------------------------------------------------------------------
# Test 2 — staging test data (id >= 1M) is never deleted
# ---------------------------------------------------------------------------


class TestStagingTestDataPreserved:
    """DELETE statements must only target rows WHERE id < 1_000_000."""

    def test_delete_condition_uses_offset(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        delete_calls = [
            (sql, args) for sql, args in staging_execute_log if sql.upper().startswith("DELETE")
        ]

        assert delete_calls, "Expected DELETE statements but found none"
        for sql, args in delete_calls:
            assert "id < $1" in sql, f"DELETE missing 'id < $1': {sql}"
            assert STAGING_ID_OFFSET in args, (
                f"DELETE not using STAGING_ID_OFFSET ({STAGING_ID_OFFSET}): {args}"
            )

    def test_no_unconditional_delete(self, prod_rows, staging_conn, staging_execute_log):
        """No DELETE without a WHERE clause (would wipe all staging data)."""
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        for sql, _ in staging_execute_log:
            if sql.upper().startswith("DELETE"):
                assert "WHERE" in sql.upper(), f"Unconditional DELETE found: {sql}"


# ---------------------------------------------------------------------------
# Test 3 — old prod-range data replaced, not duplicated
# ---------------------------------------------------------------------------


class TestProdRangeWipedBeforeInsert:
    """Each table must be DELETEd before its prod rows are INSERTed."""

    def _execution_order(self, log):
        ops = []
        for sql, _ in log:
            upper = sql.upper()
            if upper.startswith("DELETE"):
                # extract table name: DELETE FROM <table> WHERE ...
                parts = upper.split()
                # parts[0]=DELETE parts[1]=FROM parts[2]=<TABLE>
                if len(parts) >= 3:
                    ops.append(("DELETE", parts[2].lower()))
            elif upper.startswith("INSERT"):
                parts = upper.split()
                # INSERT INTO <table> ...
                if len(parts) >= 3:
                    ops.append(("INSERT", parts[2].lower()))
        return ops

    def test_delete_before_insert_for_each_table(
        self, prod_rows, staging_conn, staging_execute_log
    ):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        ops = self._execution_order(staging_execute_log)

        for table in TABLES:
            try:
                first_delete = next(
                    i for i, (op, t) in enumerate(ops) if op == "DELETE" and t == table
                )
                first_insert = next(
                    i for i, (op, t) in enumerate(ops) if op == "INSERT" and t == table
                )
            except StopIteration:
                pytest.fail(f"Missing DELETE or INSERT for table '{table}' in ops: {ops}")

            assert first_delete < first_insert, (
                f"Table '{table}': DELETE (pos {first_delete}) must come before "
                f"INSERT (pos {first_insert})"
            )

    def test_all_three_tables_deleted(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        deleted_tables_loose = set()
        for sql, _ in staging_execute_log:
            upper = sql.upper()
            if upper.startswith("DELETE"):
                for t in TABLES:
                    if t in sql.lower():
                        deleted_tables_loose.add(t)

        assert deleted_tables_loose == {"playground", "game", "round"}, (
            f"Not all tables deleted. Found: {deleted_tables_loose}"
        )


# ---------------------------------------------------------------------------
# Test 4 — FK order respected
# ---------------------------------------------------------------------------


class TestFKOrderRespected:
    """Delete must go round → game → playground; insert playground → game → round."""

    def _table_positions(self, log, op_prefix):
        """Return {table: first_log_index} for statements matching op_prefix.

        Matches precisely: DELETE FROM <table> or INSERT INTO <table> so that
        table names appearing inside setval/pg_get_serial_sequence strings are
        not confused with actual DML on that table.
        """
        positions = {}
        op_upper = op_prefix.upper().rstrip()
        # Map op to the keyword that precedes the table name
        preposition = "FROM" if op_upper == "DELETE" else "INTO"
        for i, (sql, _) in enumerate(log):
            upper = sql.upper()
            if not upper.startswith(op_upper):
                continue
            # Extract table name: the token after preposition keyword
            tokens = upper.split()
            try:
                prep_idx = tokens.index(preposition)
                table_token = tokens[prep_idx + 1].lower().rstrip("(")
            except (ValueError, IndexError):
                continue
            if table_token in TABLES and table_token not in positions:
                positions[table_token] = i
        return positions

    def test_delete_order_round_game_playground(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        pos = self._table_positions(staging_execute_log, "DELETE")
        assert pos["round"] < pos["game"], (
            f"round DELETE ({pos.get('round')}) before game ({pos.get('game')})"
        )
        assert pos["game"] < pos["playground"], (
            f"game DELETE ({pos.get('game')}) before playground ({pos.get('playground')})"
        )

    def test_insert_order_playground_game_round(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        pos = self._table_positions(staging_execute_log, "INSERT")
        assert pos["playground"] < pos["game"], (
            f"playground INSERT ({pos.get('playground')}) before game ({pos.get('game')})"
        )
        assert pos["game"] < pos["round"], (
            f"game INSERT ({pos.get('game')}) before round ({pos.get('round')})"
        )


# ---------------------------------------------------------------------------
# Test 5 — sequences reset to >= 1M
# ---------------------------------------------------------------------------


class TestSequencesResetAboveOffset:
    """setval must be called for each table with STAGING_ID_OFFSET as the floor."""

    def test_setval_called_for_all_tables(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        setval_calls = [(sql, args) for sql, args in staging_execute_log if "setval" in sql.lower()]

        assert len(setval_calls) == 3, (
            f"Expected 3 setval calls (one per table), got {len(setval_calls)}"
        )

    def test_setval_uses_offset_as_floor(self, prod_rows, staging_conn, staging_execute_log):
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        setval_calls = [(sql, args) for sql, args in staging_execute_log if "setval" in sql.lower()]

        for _sql, args in setval_calls:
            assert STAGING_ID_OFFSET in args, (
                f"setval must use STAGING_ID_OFFSET ({STAGING_ID_OFFSET}) as arg, got: {args}"
            )

    def test_setval_uses_greatest_to_respect_existing_ids(
        self, prod_rows, staging_conn, staging_execute_log
    ):
        """The SQL must use GREATEST so an existing max_id above 1M is respected."""
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        setval_calls = [sql for sql, _ in staging_execute_log if "setval" in sql.lower()]
        for sql in setval_calls:
            assert "greatest" in sql.lower(), (
                f"setval SQL must use GREATEST to guard against id collision: {sql}"
            )

    def test_setval_called_after_inserts(self, prod_rows, staging_conn, staging_execute_log):
        """Sequences must be reset AFTER all rows are inserted (so MAX(id) is correct)."""
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        last_insert_pos = max(
            (
                i
                for i, (sql, _) in enumerate(staging_execute_log)
                if sql.upper().startswith("INSERT")
            ),
            default=-1,
        )
        first_setval_pos = next(
            (i for i, (sql, _) in enumerate(staging_execute_log) if "setval" in sql.lower()),
            None,
        )
        assert first_setval_pos is not None, "No setval call found"
        assert first_setval_pos > last_insert_pos, (
            f"setval (pos {first_setval_pos}) must come after last INSERT (pos {last_insert_pos})"
        )


# ---------------------------------------------------------------------------
# Test 6 — transaction rollback on error
# ---------------------------------------------------------------------------


class TestTransactionRollbackOnError:
    """If any staging execute raises, the transaction context manager receives the
    exception and no partial state is committed."""

    def test_transaction_context_manager_entered(self, prod_rows, staging_conn):
        """sync() must always use staging_conn.transaction() as a context manager."""
        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        staging_conn.transaction.assert_called_once()
        staging_conn.transaction.return_value.__aenter__.assert_awaited_once()

    def test_exception_propagates_through_transaction(self, prod_rows):
        """When staging execute fails on INSERT, the exception exits the transaction
        context manager (triggering asyncpg's implicit rollback)."""
        boom_conn = AsyncMock()
        call_count = 0

        async def failing_execute(sql, *args):
            nonlocal call_count
            call_count += 1
            upper = sql.strip().upper()
            if upper.startswith("DELETE"):
                return "DELETE 0"
            if upper.startswith("INSERT"):
                raise RuntimeError("simulated DB failure")
            return None

        boom_conn.execute.side_effect = failing_execute

        txn_cm = AsyncMock()
        txn_cm.__aenter__ = AsyncMock(return_value=None)
        # Simulate asyncpg NOT suppressing the exception
        txn_cm.__aexit__ = AsyncMock(return_value=False)
        boom_conn.transaction = MagicMock(return_value=txn_cm)

        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, boom_conn]),
        ):
            sync = _import_sync()
            # Script catches per-row errors, logs warnings, then exits non-zero
            with pytest.raises(SystemExit):
                _run(sync())

        # __aexit__ must have been called (transaction context was properly closed)
        boom_conn.transaction.return_value.__aexit__.assert_awaited_once()

    def test_connections_closed_after_error(self, prod_rows):
        """prod and staging connections are always closed, even when sync raises."""
        error_conn = AsyncMock()

        async def raise_on_execute(sql, *args):
            raise RuntimeError("catastrophic failure")

        error_conn.execute.side_effect = raise_on_execute

        txn_cm = AsyncMock()
        txn_cm.__aenter__ = AsyncMock(return_value=None)
        txn_cm.__aexit__ = AsyncMock(return_value=False)
        error_conn.transaction = MagicMock(return_value=txn_cm)

        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, error_conn]),
        ):
            sync = _import_sync()
            with contextlib.suppress(Exception):
                _run(sync())

        prod_conn.close.assert_awaited_once()
        error_conn.close.assert_awaited_once()

    def test_all_deletes_happen_inside_transaction(
        self, prod_rows, staging_conn, staging_execute_log
    ):
        """All DELETEs must occur after __aenter__ and before __aexit__."""
        prod_conn = _make_prod_conn(prod_rows)
        enter_event = []
        exit_event = []

        async def patched_aenter(*_args, **_kwargs):
            enter_event.append(len(staging_execute_log))
            return None  # matches what __aenter__ normally returns

        async def patched_aexit(*_args, **_kwargs):
            exit_event.append(len(staging_execute_log))
            return False

        staging_conn.transaction.return_value.__aenter__ = AsyncMock(side_effect=patched_aenter)
        staging_conn.transaction.return_value.__aexit__ = AsyncMock(side_effect=patched_aexit)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        assert enter_event, "Transaction __aenter__ was never called"
        assert exit_event, "Transaction __aexit__ was never called"

        txn_start = enter_event[0]
        txn_end = exit_event[0]

        delete_positions = [
            i for i, (sql, _) in enumerate(staging_execute_log) if sql.upper().startswith("DELETE")
        ]
        for pos in delete_positions:
            assert txn_start <= pos < txn_end, (
                f"DELETE at log pos {pos} is outside transaction window [{txn_start}, {txn_end})"
            )


# ---------------------------------------------------------------------------
# Test 7 — sync exits non-zero when row errors occur
# ---------------------------------------------------------------------------


class TestSyncExitsOnErrors:
    """If any INSERT fails, sync() must raise so the process exits non-zero."""

    def test_sync_raises_on_row_errors(self, prod_rows):
        """When per-row INSERTs fail, sync must raise SystemExit(1)."""
        boom_conn = AsyncMock()

        async def failing_execute(sql, *args):
            upper = sql.strip().upper()
            if upper.startswith("DELETE"):
                return "DELETE 0"
            if upper.startswith("INSERT"):
                raise RuntimeError("simulated row failure")
            return None

        boom_conn.execute.side_effect = failing_execute

        txn_cm = AsyncMock()
        txn_cm.__aenter__ = AsyncMock(return_value=None)
        txn_cm.__aexit__ = AsyncMock(return_value=False)
        boom_conn.transaction = MagicMock(return_value=txn_cm)

        prod_conn = _make_prod_conn(prod_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, boom_conn]),
            pytest.raises(SystemExit) as exc_info,
        ):
            sync = _import_sync()
            _run(sync())

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Test 8 — empty prod table still deletes staging and resets sequences
# ---------------------------------------------------------------------------


class TestEmptyProdTable:
    """When a prod table has 0 rows, DELETE and setval must still run."""

    def test_empty_prod_still_deletes_and_resets(self, staging_conn, staging_execute_log):
        empty_rows = {"playground": [], "game": [], "round": []}
        prod_conn = _make_prod_conn(empty_rows)

        with (
            patch.dict(
                "os.environ",
                {
                    "PROD_DATABASE_URL": "postgresql://prod/db",
                    "STAGING_DATABASE_URL": "postgresql://staging/db",
                },
            ),
            patch("asyncpg.connect", side_effect=[prod_conn, staging_conn]),
        ):
            sync = _import_sync()
            _run(sync())

        delete_calls = [s for s, _ in staging_execute_log if s.upper().startswith("DELETE")]
        assert len(delete_calls) == 3, (
            f"Expected 3 DELETEs even for empty prod, got {len(delete_calls)}"
        )

        setval_calls = [s for s, _ in staging_execute_log if "setval" in s.lower()]
        assert len(setval_calls) == 3, (
            f"Expected 3 setval calls even for empty prod, got {len(setval_calls)}"
        )

        insert_calls = [s for s, _ in staging_execute_log if s.upper().startswith("INSERT")]
        assert len(insert_calls) == 0, f"Expected 0 INSERTs for empty prod, got {len(insert_calls)}"


# ---------------------------------------------------------------------------
# Test 9 — missing env vars calls sys.exit(1)
# ---------------------------------------------------------------------------


class TestMissingEnvVars:
    """_get_urls() must exit with code 1 when env vars are missing."""

    def test_missing_prod_url_exits(self):
        with (
            patch.dict("os.environ", {"STAGING_DATABASE_URL": "x"}, clear=True),
            pytest.raises(SystemExit) as exc_info,
        ):
            sync = _import_sync()
            _run(sync())
        assert exc_info.value.code == 1

    def test_missing_staging_url_exits(self):
        with (
            patch.dict("os.environ", {"PROD_DATABASE_URL": "x"}, clear=True),
            pytest.raises(SystemExit) as exc_info,
        ):
            sync = _import_sync()
            _run(sync())
        assert exc_info.value.code == 1
