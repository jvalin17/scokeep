"""SEO routes: sitemap, robots, Google Search Console verification files."""

import pytest


@pytest.mark.asyncio
async def test_sitemap_includes_home_and_privacy(client):
    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    body = resp.text
    assert "https://scokeep.com/</loc>" in body
    assert "https://scokeep.com/static/privacy.html</loc>" in body


@pytest.mark.asyncio
async def test_robots_points_at_sitemap(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Allow: /" in resp.text
    assert "Sitemap: https://scokeep.com/sitemap.xml" in resp.text


@pytest.mark.asyncio
async def test_google_verification_files_at_root(client):
    for path in (
        "/google58fff8f471367856.html",
        "/google90ca41c797c60c6e.html",
    ):
        resp = await client.get(path)
        assert resp.status_code == 200, path
        assert "google-site-verification:" in resp.text
