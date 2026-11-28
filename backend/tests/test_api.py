from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.main import app
from backend.app.db.session import get_session
from backend.app.db.models import Feed, Digest, PipelineRun

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(test_engine)


def override_get_session():
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session
client = TestClient(app)


def test_health_endpoints():
    res1 = client.get("/")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.json()["status"] == "ok"


def test_overview_endpoint():
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert "active_feeds_count" in data
    assert "total_feeds_count" in data
    assert "articles_today_count" in data
    assert "total_digests_count" in data


def test_feeds_crud_and_toggle():
    # 1. Create feed
    feed_payload = {
        "name": "Tempo Nasional Test",
        "url": "https://test.tempo.co/nasional.xml",
        "category": "Nasional",
        "is_active": True,
    }
    create_res = client.post("/api/feeds", json=feed_payload)
    assert create_res.status_code == 201
    created_feed = create_res.json()
    feed_id = created_feed["id"]
    assert created_feed["name"] == "Tempo Nasional Test"
    assert created_feed["is_active"] is True

    # 2. List feeds
    list_res = client.get("/api/feeds")
    assert list_res.status_code == 200
    feeds = list_res.json()
    assert any(f["id"] == feed_id for f in feeds)

    # 3. Toggle feed status
    toggle_res = client.patch(f"/api/feeds/{feed_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # 4. Update feed
    update_res = client.put(f"/api/feeds/{feed_id}", json={"name": "Tempo Updated", "is_active": True})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Tempo Updated"
    assert update_res.json()["is_active"] is True

    # 5. Delete feed
    del_res = client.delete(f"/api/feeds/{feed_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ok"


def test_feed_tester_endpoint():
    # Test probe endpoint (FR-06) with invalid / dummy URL
    probe_res = client.post("/api/feeds/test", json={"url": "https://example.invalid/rss.xml", "limit": 2})
    assert probe_res.status_code == 200
    data = probe_res.json()
    assert "status" in data


def test_digests_crud():
    # Seed a test digest directly into DB
    with Session(test_engine) as session:
        test_d = Digest(
            date="2026-11-25",
            summary_markdown="1️⃣ **Headline Test**\nRingkasan berita.",
            summary_html="1️⃣ <b>Headline Test</b><br/>Ringkasan berita.",
            model_used="test-model",
            total_clusters=1,
            total_sources=1,
            status="draft",
        )
        session.add(test_d)
        session.commit()
        session.refresh(test_d)
        d_id = test_d.id

    # List digests
    list_res = client.get("/api/digests?page=1&limit=5")
    assert list_res.status_code == 200
    page_data = list_res.json()
    assert page_data["total"] >= 1
    assert any(item["id"] == d_id for item in page_data["items"])

    # Get single digest by ID
    get_res = client.get(f"/api/digests/{d_id}")
    assert get_res.status_code == 200
    assert get_res.json()["date"] == "2026-11-25"

    # Get single digest by date string (YYYY-MM-DD)
    get_date_res = client.get("/api/digests/2026-11-25")
    assert get_date_res.status_code == 200
    assert get_date_res.json()["id"] == d_id

    # Edit digest draft (FR-13) by ID
    edit_res = client.put(
        f"/api/digests/{d_id}",
        json={"summary_markdown": "1️⃣ **Updated Headline**\nSuntingan kurator.", "status": "draft"},
    )
    assert edit_res.status_code == 200
    updated_data = edit_res.json()
    assert "Updated Headline" in updated_data["summary_markdown"]
    assert "<b>Updated Headline</b>" in updated_data["summary_html"]

    # Edit digest draft by date string (YYYY-MM-DD)
    edit_date_res = client.put(
        "/api/digests/2026-11-25",
        json={"summary_markdown": "1️⃣ **Updated Again**\nSuntingan kedua."},
    )
    assert edit_date_res.status_code == 200
    assert "Updated Again" in edit_date_res.json()["summary_markdown"]


def test_pipeline_trigger():
    res = client.post("/api/pipeline/run", json={"dry_run": True, "auto_broadcast": False})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    assert "run_id" in data

    # Test trigger with mode="dry_run"
    res_mode = client.post("/api/pipeline/run", json={"mode": "dry_run"})
    assert res_mode.status_code in (200, 409)  # 409 if previous background run is still locking


def test_pipeline_stream_initial_event():
    with client.stream("GET", "/api/pipeline/stream") as stream_res:
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        for line in stream_res.iter_lines():
            if line:
                assert line.startswith("data: ")
                data = line[len("data: "):]
                assert "connected" in data
                break

    # Also test stream with run_id parameter
    with client.stream("GET", "/api/pipeline/stream/test-run-123") as stream_res2:
        assert stream_res2.status_code == 200
        assert "text/event-stream" in stream_res2.headers["content-type"]
        for line in stream_res2.iter_lines():
            if line:
                assert line.startswith("data: ")
                data = line[len("data: "):]
                assert "test-run-123" in data
                break


def test_modular_services_exports():
    """Verify that domain modular services are directly importable and intact."""
    from backend.app.services import rss_service
    from backend.app.services import cluster_service
    from backend.app.services import synthesis_service
    from backend.app.services import telegram_service

    assert hasattr(rss_service, "async_fetch_feed")
    assert hasattr(cluster_service, "cluster_articles")
    assert hasattr(synthesis_service, "synthesize_news")
    assert hasattr(telegram_service, "broadcast_digest_async")


