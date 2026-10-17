from __future__ import annotations


async def test_health_returns_200(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["app"]
    assert body["version"]
    assert body["environment"] in ("development", "production")
    assert body["timestamp"]


async def test_health_ready_reports_mongo_state(client):
    res = await client.get("/api/health/ready")
    body = res.json()
    # 200 when MongoDB is reachable, 503 when it is not — structure always holds.
    assert res.status_code in (200, 503)
    assert body["status"] in ("ready", "degraded")
    assert body["checks"]["mongo"] in ("up", "down")
    if body["checks"]["mongo"] == "up":
        assert res.status_code == 200
        assert body["checks"]["latency_ms"] is not None
    else:
        assert res.status_code == 503


async def test_health_404_for_unknown_route(client):
    res = await client.get("/api/does-not-exist")
    assert res.status_code == 404
