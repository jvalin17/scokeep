"""Playwright UI test fixtures — real server, real browser, fresh DB.

Uses Playwright's SYNC API to avoid event loop conflicts with pytest-asyncio.
"""

import os
import socket
import subprocess  # noqa: S603
import sys
import time
from pathlib import Path

import httpx
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
SERVER_LOG = Path("ui_test_server.log")


def _pick_free_port() -> int:
    """Bind briefly to port 0 so we never collide with a stale uvicorn on 8050."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    """Start each session with a fresh database."""
    DB_PATH.unlink(missing_ok=True)
    yield
    DB_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def server():
    """Start uvicorn subprocess for the entire UI test session."""
    server_port = _pick_free_port()
    base_url = f"http://127.0.0.1:{server_port}"

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
            "127.0.0.1",
            "--port",
            str(server_port),
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
            response = httpx.get(f"{base_url}/api/health", timeout=2.0)
            if response.status_code == 200:
                break
        except (httpx.HTTPError, OSError):
            time.sleep(0.5)
    else:
        log_file.close()
        log_content = SERVER_LOG.read_text()
        proc.terminate()
        raise RuntimeError(f"Server did not start within 30 seconds\nLog:\n{log_content[-2000:]}")

    yield base_url
    proc.terminate()
    proc.wait(timeout=5)
    log_file.close()
    SERVER_LOG.unlink(missing_ok=True)
