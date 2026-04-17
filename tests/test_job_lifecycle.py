"""End-to-end job lifecycle tests: POST /api/search → poll until done."""
import time
from unittest.mock import AsyncMock, patch


POLL_TIMEOUT_S = 10
POLL_INTERVAL_S = 0.1


def _poll_until_done(client, job_id):
    """Poll the status endpoint until the job leaves the 'running' state."""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        resp = client.get(f"/api/search/{job_id}")
        data = resp.get_json()
        if data["status"] != "running":
            return data
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"Job {job_id} did not finish within {POLL_TIMEOUT_S}s")


def _make_mock_client(process_query_return):
    """Return a context-manager patch that stubs out MCPOpenAIClient."""
    patcher = patch("ai_researcher.app.MCPOpenAIClient")

    def _start(patcher):
        MockClient = patcher.start()
        instance = MockClient.return_value
        instance.connect_to_server = AsyncMock()
        instance.process_query = AsyncMock(return_value=process_query_return)
        instance.cleanup = AsyncMock()
        return patcher

    return _start(patcher), patcher


class TestJobLifecycleSuccess:
    def test_job_completes_with_pdf_url(self, client):
        """Full happy path: job finishes with a /reports/ URL."""
        fake_url = "/reports/ai_research_report_20260417_120000.pdf"

        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(return_value=fake_url)
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "Latest AI developments"})
            assert resp.status_code == 200
            job_id = resp.get_json()["job_id"]

            result = _poll_until_done(client, job_id)

        assert result["status"] == "completed"
        assert result["report_pdf_url"] == fake_url
        assert result["query"] == "Latest AI developments"
        assert result["report"] == fake_url

    def test_job_completes_with_text_result(self, client):
        """When the LLM returns plain text (no PDF), report_pdf_url is empty."""
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(return_value="Here is a summary of AI news.")
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "AI summary"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "completed"
        assert result["report_pdf_url"] == ""
        assert result["report"] == "Here is a summary of AI news."

    def test_job_logs_are_captured(self, client):
        """Logs written via print() during the job appear in the status response."""
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(return_value="/reports/report.pdf")
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "test logging"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        # The job always logs connection messages via print()
        assert len(result["logs"]) > 0

    def test_multiple_concurrent_jobs_are_independent(self, client):
        """Two simultaneous jobs each get their own job_id and result."""
        url_a = "/reports/report_a.pdf"
        url_b = "/reports/report_b.pdf"

        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            # Alternate return values based on call count
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.cleanup = AsyncMock()
            instance.process_query = AsyncMock(side_effect=[url_a, url_b])

            resp_a = client.post("/api/search", json={"query": "query A"})
            resp_b = client.post("/api/search", json={"query": "query B"})
            job_a = resp_a.get_json()["job_id"]
            job_b = resp_b.get_json()["job_id"]

            assert job_a != job_b

            result_a = _poll_until_done(client, job_a)
            result_b = _poll_until_done(client, job_b)

        assert result_a["status"] == "completed"
        assert result_b["status"] == "completed"
        assert result_a["query"] == "query A"
        assert result_b["query"] == "query B"


class TestJobLifecycleFailure:
    def test_job_fails_when_client_raises(self, client):
        """If MCPOpenAIClient.process_query raises, the job is marked failed."""
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(side_effect=RuntimeError("SerpAPI key missing"))
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "will fail"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "failed"
        assert "SerpAPI key missing" in result["error"]

    def test_failed_job_error_appears_in_logs(self, client):
        """The failure message is appended to the job's log stream."""
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock()
            instance.process_query = AsyncMock(side_effect=RuntimeError("boom"))
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "error test"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert "boom" in result["logs"]

    def test_connect_failure_marks_job_failed(self, client):
        """A failure during connect_to_server propagates to a failed job."""
        with patch("ai_researcher.app.MCPOpenAIClient") as MockClient:
            instance = MockClient.return_value
            instance.connect_to_server = AsyncMock(side_effect=ConnectionError("server not found"))
            instance.process_query = AsyncMock()
            instance.cleanup = AsyncMock()

            resp = client.post("/api/search", json={"query": "connect fail"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "failed"
        assert "server not found" in result["error"]
