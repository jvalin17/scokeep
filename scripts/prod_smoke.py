#!/usr/bin/env python3
"""Production smoke checks for scokeep.com (or PROD_SMOKE_BASE_URL).

Read-only checks always run. Optional gameplay smoke creates an ephemeral
room, plays one short round, and asserts sync-round + scoreboard on prod.

Usage:
  python scripts/prod_smoke.py
  PROD_SMOKE_BASE_URL=https://scokeep.com python scripts/prod_smoke.py
  PROD_SMOKE_PLAY=0 python scripts/prod_smoke.py   # skip gameplay
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

DEFAULT_BASE = "https://scokeep.com"
USER_AGENT = "scokeep-prod-smoke/1.0"


class SmokeError(Exception):
    pass


def _request(
    opener: urllib.request.OpenerDirector,
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 45,
) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode()
    url = f"{base.rstrip('/')}{path}"
    if not url.startswith(("http://", "https://")):
        raise SmokeError(f"refusing non-http(s) URL: {url!r}")
    req = urllib.request.Request(  # noqa: S310 — scheme validated above
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html, */*",
        },
        method=method,
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def check_health(opener: urllib.request.OpenerDirector, base: str) -> None:
    status, body = _request(opener, base, "/api/health")
    if status != 200:
        raise SmokeError(f"health HTTP {status}: {body}")
    if not isinstance(body, dict) or body.get("status") != "healthy":
        raise SmokeError(f"health not healthy: {body}")
    if body.get("database") != "connected":
        raise SmokeError(f"database not connected: {body}")
    print("OK  health")


def check_openapi(opener: urllib.request.OpenerDirector, base: str) -> None:
    status, body = _request(opener, base, "/openapi.json")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"openapi HTTP {status}")
    paths = body.get("paths") or {}
    required = [
        "/api/game/{game_id}/sync-round",
        "/api/game/{game_id}/sync-state",
    ]
    missing = [path for path in required if path not in paths]
    if missing:
        raise SmokeError(f"openapi missing routes: {missing} (total={len(paths)})")
    props = (body.get("components", {}).get("schemas", {}).get("GameResponse") or {}).get(
        "properties", {}
    )
    if "source" not in props:
        raise SmokeError(f"GameResponse missing source field: {sorted(props)}")
    print(f"OK  openapi ({len(paths)} routes, sync-round present)")


def validate_sw_cache_name(cache_name: str) -> None:
    """Require content-hashed CACHE_NAME: scokeep-<12 lowercase hex>."""
    if not re.fullmatch(r"scokeep-[0-9a-f]{12}", cache_name):
        raise SmokeError(
            f"unexpected SW cache {cache_name!r} "
            "(want content-hash scokeep-<12 hex>, not legacy scokeep-vNN)"
        )


def check_sw(opener: urllib.request.OpenerDirector, base: str) -> None:
    status, body = _request(opener, base, "/sw.js")
    if status != 200 or not isinstance(body, str):
        raise SmokeError(f"sw.js HTTP {status}")
    match = re.search(r"CACHE_NAME\s*=\s*'([^']+)'", body)
    if not match:
        raise SmokeError("sw.js missing CACHE_NAME")
    cache_name = match.group(1)
    validate_sw_cache_name(cache_name)
    print(f"OK  sw {cache_name}")


def check_seo(opener: urllib.request.OpenerDirector, base: str) -> None:
    status, body = _request(opener, base, "/")
    if status != 200 or not isinstance(body, str):
        raise SmokeError(f"index HTML HTTP {status}")
    if 'rel="canonical" href="https://scokeep.com"' not in body:
        raise SmokeError("canonical link missing or not https://scokeep.com")
    if 'property="og:url" content="https://scokeep.com"' not in body:
        raise SmokeError("og:url missing or not https://scokeep.com")
    print("OK  seo canonical/og:url")

    status, sitemap = _request(opener, base, "/sitemap.xml")
    if status != 200 or not isinstance(sitemap, str):
        raise SmokeError(f"sitemap HTTP {status}")
    if "https://scokeep.com/</loc>" not in sitemap:
        raise SmokeError("sitemap missing homepage")
    if "https://scokeep.com/static/privacy.html</loc>" not in sitemap:
        raise SmokeError("sitemap missing privacy page")
    print("OK  seo sitemap home+privacy")

    for path in (
        "/google58fff8f471367856.html",
        "/google90ca41c797c60c6e.html",
    ):
        status, _ = _request(opener, base, path)
        if status != 200:
            raise SmokeError(f"google verify {path} HTTP {status}")
    print("OK  seo google verification files")


def check_gameplay(opener: urllib.request.OpenerDirector, base: str) -> None:
    """Create ephemeral room, play one round, assert sync-round + scoreboard."""
    run_id = os.environ.get("GITHUB_RUN_ID") or str(int(time.time()))
    room = f"CISmoke{run_id[-6:]}"
    pin = "4321"

    status, created = _request(
        opener,
        base,
        "/api/playground",
        method="POST",
        body={"name": room, "pin": pin, "pin_hint": "ci", "players": ["Alice", "Bob"]},
    )
    if status not in (200, 201) or not isinstance(created, dict):
        raise SmokeError(f"create playground HTTP {status}: {created}")
    playground_id = created["id"]
    print(f"OK  create room {room} id={playground_id}")

    status, _auth = _request(
        opener,
        base,
        "/api/playground/auth",
        method="POST",
        body={"name": room, "pin": pin},
    )
    if status != 200:
        raise SmokeError(f"auth HTTP {status}: {_auth}")
    print("OK  auth")

    status, game = _request(
        opener,
        base,
        "/api/game",
        method="POST",
        body={
            "playground_id": playground_id,
            "players": ["Alice", "Bob"],
            "settings": {
                "game_type": "kachuful",
                "mode": "rookie",
                "appearance": "interactive",
                "num_sets": 1,
                "rounds_per_set": 2,
                "must_lose": True,
                "scoring_formula": "kachuful_standard",
            },
        },
    )
    if status not in (200, 201) or not isinstance(game, dict):
        raise SmokeError(f"create game HTTP {status}: {game}")
    game_id = game["id"]
    if game.get("source") not in (None, "online"):
        # source may be present after IDB-first promote
        pass
    print(f"OK  create game id={game_id} source={game.get('source')}")

    # Server-side bid/score path still exists on prod; sync-round is the IDB path.
    # Exercise sync-round directly (same payload the client sends after scoring).
    sync_body = {
        "round_num": 1,
        "cards_dealt": 2,
        "trump_suit": "spades",
        "bids": {"0": 0, "1": 0},
        "hands_won": {"0": 1, "1": 1},
        "scores": {"0": -10, "1": -10},
        "status": "complete",
    }
    status, synced = _request(
        opener,
        base,
        f"/api/game/{game_id}/sync-round",
        method="POST",
        body=sync_body,
    )
    if status != 200 or not isinstance(synced, dict):
        raise SmokeError(f"sync-round HTTP {status}: {synced}")
    if synced.get("status") != "scored":
        raise SmokeError(f"sync-round status want scored got {synced.get('status')}")
    print("OK  sync-round → scored")

    status, board = _request(opener, base, f"/api/game/{game_id}/scoreboard")
    if status != 200 or not isinstance(board, dict):
        raise SmokeError(f"scoreboard HTTP {status}: {board}")
    rounds = board.get("rounds") or []
    if len(rounds) < 1:
        raise SmokeError(f"scoreboard missing rounds: {board}")
    if rounds[0].get("scores") != {"0": -10, "1": -10}:
        raise SmokeError(f"scoreboard scores mismatch: {rounds[0]}")
    print("OK  scoreboard has synced round")

    # Finish so Resume does not linger on that room
    _request(opener, base, f"/api/game/{game_id}/end", method="POST", body={})
    _request(opener, base, f"/api/game/{game_id}/confirm-final", method="POST", body={})
    print("OK  end + confirm-final")


def main() -> int:
    base = (os.environ.get("PROD_SMOKE_BASE_URL") or DEFAULT_BASE).rstrip("/")
    play = (os.environ.get("PROD_SMOKE_PLAY") or "1") != "0"

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    print(f"Prod smoke against {base}")
    try:
        check_health(opener, base)
        check_openapi(opener, base)
        check_sw(opener, base)
        check_seo(opener, base)
        if play:
            check_gameplay(opener, base)
        else:
            print("SKIP gameplay (PROD_SMOKE_PLAY=0)")
    except SmokeError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — surface unexpected CI errors
        print(f"FAIL  unexpected: {exc}", file=sys.stderr)
        return 1

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
