import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.database import create_tables, engine
from app.routes import game, playground, score
from app.routes import round as round_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

STATIC_DIR = Path(__file__).parent / "static"


async def _recompute_all_insights():
    """Recompute insights for all playgrounds on startup."""
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.playground import Playground
    from app.services.insights import compute_insights

    logger = logging.getLogger("scokeep.startup")
    async with async_session_factory() as db:
        result = await db.execute(select(Playground.id))
        pg_ids = [row[0] for row in result.all()]
        for pg_id in pg_ids:
            try:
                await compute_insights(db, pg_id)
            except Exception:
                logger.warning("Failed to recompute insights for playground %s", pg_id)
        logger.info("Recomputed insights for %d playgrounds", len(pg_ids))


def _log_task_error(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        logging.getLogger("scokeep.startup").error(
            "Insights recompute failed: %s", task.exception(),
        )


@asynccontextmanager
async def lifespan(application: FastAPI):
    await create_tables()
    task = asyncio.create_task(_recompute_all_insights())
    task.add_done_callback(_log_task_error)
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Scokeep", version="0.1.0", lifespan=lifespan)
app.state.limiter = playground.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import Response  # noqa: E402

from app.config import settings  # noqa: E402


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if settings.debug and request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.include_router(playground.router)
app.include_router(game.router)
app.include_router(round_routes.router)
app.include_router(score.router)


@app.get("/")
async def index():
    response = FileResponse(STATIC_DIR / "index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(STATIC_DIR / "favicon.ico")


@app.get("/apple-touch-icon.png")
async def apple_touch_icon():
    return FileResponse(STATIC_DIR / "apple-touch-icon.png")


@app.get("/google90ca41c797c60c6e.html")
async def google_verification():
    return FileResponse(STATIC_DIR / "google90ca41c797c60c6e.html")


@app.get("/sitemap.xml")
async def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://scokeep.onrender.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    from starlette.responses import Response as StarletteResponse
    return StarletteResponse(content=xml, media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /
Sitemap: https://scokeep.onrender.com/sitemap.xml"""
    from starlette.responses import Response as StarletteResponse
    return StarletteResponse(content=content, media_type="text/plain")


@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon_precomposed():
    return FileResponse(STATIC_DIR / "apple-touch-icon.png")


@app.get("/api/health")
async def health():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        logging.getLogger("scokeep.health").error("DB health check failed: %s", exc)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable"},
        )
