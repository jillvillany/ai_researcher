"""Tests for Flask API endpoints."""
import uuid
from unittest.mock import AsyncMock, patch
from ai_researcher.app import jobs, jobs_lock


class TestHomeRoute:
    def test_home_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_home_returns_html(self, client):
        resp = client.get("/")
        assert b"Research Report Generator" in resp.data


class TestReportsRoute:
    def test_serves_existing_pdf(self, client, sample_pdf):
        resp = client.get(f"/reports/{sample_pdf.name}")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"

    def test_returns_404_for_missing_file(self, client):
        resp = client.get("/reports/does_not_exist.pdf")
        assert resp.status_code == 404


class TestSearchPost:
    def test_missing_body_returns_400(self, client):
        resp = client.post("/api/search", content_type="application/json", data="{}")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_empty_query_returns_400(self, client):
        resp = client.post("/api/search", json={"query": "   "})
        assert resp.status_code == 400

    def test_non_json_body_returns_400(self, client):
        resp = client.post("/api/search", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_valid_query_creates_job(self, client):
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(return_value="/reports/report.pdf")
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "AI news"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert "job_id" in data
            assert data["status"] == "running"

    def test_valid_query_registers_job_in_store(self, client):
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(return_value="/reports/report.pdf")
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "AI news"})
            job_id = resp.get_json()["job_id"]

            with jobs_lock:
                assert job_id in jobs
                assert jobs[job_id]["query"] == "AI news"


class TestSearchStatus:
    def test_unknown_job_returns_404(self, client):
        resp = client.get(f"/api/search/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_running_job_returns_status(self, client):
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {"status": "running", "logs": "starting...", "error": "", "result": None}

        resp = client.get(f"/api/search/{job_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "running"
        assert data["logs"] == "starting..."

    def test_completed_job_includes_result(self, client):
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "status": "completed",
                "logs": "done",
                "error": "",
                "result": {
                    "query": "AI news",
                    "report": "/reports/report.pdf",
                    "report_pdf_url": "/reports/report.pdf",
                },
            }

        resp = client.get(f"/api/search/{job_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "completed"
        assert data["report_pdf_url"] == "/reports/report.pdf"

    def test_failed_job_includes_error(self, client):
        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                "status": "failed",
                "logs": "oops",
                "error": "SerpAPI key missing",
                "result": None,
            }

        resp = client.get(f"/api/search/{job_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "failed"
        assert data["error"] == "SerpAPI key missing"
