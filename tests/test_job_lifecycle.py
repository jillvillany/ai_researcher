"""End-to-end job lifecycle tests: POST /api/search → poll until done."""
import time
from unittest.mock import patch


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


class TestJobLifecycleSuccess:
    def test_job_completes_with_pdf_url(self, client):
        """Full happy path: job finishes with a /reports/ URL."""
        fake_url = "/reports/ai_research_report_20260417_120000.pdf"
        fake_result = {"report": fake_url, "research_results": "some findings"}

        with patch("ai_researcher.app.research_graph.run", return_value=fake_result):
            resp = client.post("/api/search", json={"query": "Latest AI developments"})
            assert resp.status_code == 200
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "completed"
        assert result["report_pdf_url"] == fake_url
        assert result["query"] == "Latest AI developments"
        assert result["report"] == fake_url
        assert result["research_results"] == "some findings"

    def test_job_completes_with_no_pdf(self, client):
        """When report is not a /reports/ URL, report_pdf_url is empty."""
        fake_result = {"report": "Could not generate PDF.", "research_results": "some findings"}

        with patch("ai_researcher.app.research_graph.run", return_value=fake_result):
            resp = client.post("/api/search", json={"query": "AI summary"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "completed"
        assert result["report_pdf_url"] == ""
        assert result["report"] == "Could not generate PDF."

    def test_job_logs_are_captured(self, client):
        """Logs written via print() during the job appear in the status response."""
        fake_result = {"report": "/reports/r.pdf", "research_results": ""}

        with patch("ai_researcher.app.research_graph.run", return_value=fake_result):
            resp = client.post("/api/search", json={"query": "test logging"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        # app.py always prints "Starting research workflow..." and "Research workflow completed."
        assert "Starting research workflow" in result["logs"]
        assert "Research workflow completed" in result["logs"]

    def test_multiple_concurrent_jobs_are_independent(self, client):
        """Two simultaneous jobs each get their own job_id and result."""
        result_a = {"report": "/reports/report_a.pdf", "research_results": "findings A"}
        result_b = {"report": "/reports/report_b.pdf", "research_results": "findings B"}

        with patch("ai_researcher.app.research_graph.run", side_effect=[result_a, result_b]):
            resp_a = client.post("/api/search", json={"query": "query A"})
            resp_b = client.post("/api/search", json={"query": "query B"})
            job_a = resp_a.get_json()["job_id"]
            job_b = resp_b.get_json()["job_id"]

            assert job_a != job_b

            final_a = _poll_until_done(client, job_a)
            final_b = _poll_until_done(client, job_b)

        assert final_a["status"] == "completed"
        assert final_b["status"] == "completed"
        assert final_a["query"] == "query A"
        assert final_b["query"] == "query B"


class TestJobLifecycleFailure:
    def test_job_fails_when_graph_raises(self, client):
        """If research_graph.run raises, the job is marked failed."""
        with patch("ai_researcher.app.research_graph.run", side_effect=RuntimeError("SERPAPI_KEY not set")):
            resp = client.post("/api/search", json={"query": "will fail"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "failed"
        assert "SERPAPI_KEY not set" in result["error"]

    def test_failed_job_error_appears_in_logs(self, client):
        """The failure message is appended to the job's log stream."""
        with patch("ai_researcher.app.research_graph.run", side_effect=RuntimeError("boom")):
            resp = client.post("/api/search", json={"query": "error test"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert "boom" in result["logs"]

    def test_orchestrator_iteration_limit_marks_job_failed(self, client):
        """RuntimeError from the orchestrator iteration cap is captured as a failed job."""
        with patch(
            "ai_researcher.app.research_graph.run",
            side_effect=RuntimeError("Orchestrator agent exceeded the maximum number of tool iterations."),
        ):
            resp = client.post("/api/search", json={"query": "loop test"})
            job_id = resp.get_json()["job_id"]
            result = _poll_until_done(client, job_id)

        assert result["status"] == "failed"
        assert "exceeded" in result["error"]
