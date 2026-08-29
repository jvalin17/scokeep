"""Test that insights recompute isolates failures per playground.

Root cause: shared DB session means one playground's failure aborts the
PostgreSQL transaction, cascading InFailedSQLTransactionError to all
subsequent playgrounds.

Fix: fresh session per playground in _recompute_all_insights().
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import _recompute_all_insights


def _run(coro):
    return asyncio.run(coro)


def _make_session_factory(pg_ids):
    """Build a mock async_session_factory that returns sessions with pg_ids."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(pid,) for pid in pg_ids]
    mock_session.execute = AsyncMock(return_value=mock_result)

    call_count = {"n": 0}

    def factory():
        call_count["n"] += 1
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    return factory, call_count


class TestInsightsSessionIsolation:
    """Each playground gets its own DB session so failures don't cascade."""

    def test_second_playground_succeeds_after_first_fails(self):
        """If compute_insights raises for pg_id=1, pg_id=2 still runs."""
        call_log = []

        async def mock_compute(db, pg_id):
            if pg_id == 1:
                call_log.append(("fail", pg_id))
                raise RuntimeError("simulated insights failure")
            call_log.append(("ok", pg_id))

        factory, session_count = _make_session_factory([1, 2])

        with (
            patch("app.database.async_session_factory", side_effect=factory),
            patch("app.services.insights.compute_insights", side_effect=mock_compute),
        ):
            _run(_recompute_all_insights())

        assert ("fail", 1) in call_log
        assert ("ok", 2) in call_log
        # 3 sessions: 1 for ID fetch + 1 per playground
        assert session_count["n"] == 3

    def test_all_playgrounds_attempted_even_with_failures(self):
        """Even if multiple playgrounds fail, all are attempted."""
        attempted = []

        async def mock_compute(db, pg_id):
            attempted.append(pg_id)
            if pg_id in (1, 3):
                raise RuntimeError(f"fail for {pg_id}")

        factory, _ = _make_session_factory([1, 2, 3, 4])

        with (
            patch("app.database.async_session_factory", side_effect=factory),
            patch("app.services.insights.compute_insights", side_effect=mock_compute),
        ):
            _run(_recompute_all_insights())

        assert attempted == [1, 2, 3, 4]
