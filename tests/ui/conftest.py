"""Playwright UI test fixtures — real server, real browser, fresh DB.

Uses Playwright's SYNC API to avoid event loop conflicts with pytest-asyncio.
"""

import os
import subprocess  # noqa: S603
import sys
import time
import urllib.error
import urllib.request  # noqa: S310
from pathlib import Path

import pytest

collect_ignore_glob: list[str] = []


# Override the root conftest's event_loop and setup_database fixtures
# to prevent them from interfering with Playwright's sync tests
@pytest.fixture(scope="session")
def event_loop():
    """Override root event_loop — UI tests don't need one."""
    return None


@pytest.fixture(autouse=True)
def setup_database():
    """Override root setup_database — UI tests use their own DB via subprocess."""
    yield


DB_PATH = Path("ui_test.db")
SERVER_PORT = 8050
BASE_URL = f"http://localhost:{SERVER_PORT}"
SERVER_LOG = Path("ui_test_server.log")


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    """Start each session with a fresh database."""
    DB_PATH.unlink(missing_ok=True)
    yield
    DB_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def server():
    """Start uvicorn subprocess for the entire UI test session."""
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///./{DB_PATH}",
        "RATE_LIMIT_ENABLED": "false",
        "ADMIN_KEY": "test-admin-key",
    }
    # Write server output to a log file instead of PIPE to avoid
    # subprocess deadlock when the pipe buffer fills up (~64KB).
    log_file = SERVER_LOG.open("w")
    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",  # noqa: S104
            "--port",
            str(SERVER_PORT),
        ],
        env=env,
        stdout=log_file,
        stderr=log_file,
    )

    # Wait for server to be ready (up to 30s)
    for _ in range(60):
        if proc.poll() is not None:
            log_file.close()
            log_content = SERVER_LOG.read_text()
            raise RuntimeError(
                f"Server process exited with code {proc.returncode}\nLog:\n{log_content[-2000:]}"
            )
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2)  # noqa: S310
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            time.sleep(0.5)
    else:
        log_file.close()
        log_content = SERVER_LOG.read_text()
        proc.terminate()
        raise RuntimeError(f"Server did not start within 30 seconds\nLog:\n{log_content[-2000:]}")

    yield BASE_URL
    proc.terminate()
    proc.wait(timeout=5)
    log_file.close()
    SERVER_LOG.unlink(missing_ok=True)
