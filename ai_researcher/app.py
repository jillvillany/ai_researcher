import io
import threading
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from ai_researcher.graph import ResearchGraph

app = Flask(__name__)
research_graph = ResearchGraph()
REPORTS_DIR = Path(__file__).resolve().parents[1] / "tmp"
jobs = {}
jobs_lock = threading.Lock()


class JobLogStream(io.TextIOBase):
    def __init__(self, job_id):
        self.job_id = job_id

    def write(self, text):
        if not text:
            return 0

        with jobs_lock:
            job = jobs.get(self.job_id)
            if job is not None:
                job["logs"] += text

        return len(text)

    def flush(self):
        return None


def run_search_job(job_id, query):
    stream = JobLogStream(job_id)

    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            result = research_graph.run(query)

        report = result.get("report", "")
        report_pdf_url = report if isinstance(report, str) and report.startswith("/reports/") else ""

        with jobs_lock:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = {
                "query": query,
                "research_results": result.get("research_results", ""),
                "report": report,
                "report_pdf_url": report_pdf_url,
            }
    except Exception as exc:
        stream.write(f"\nWorkflow failed: {exc}\n")
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(exc)


@app.route("/")
def home():
    return app.send_static_file("index.html")


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORTS_DIR, filename)


@app.post("/api/search")
def search():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Please enter a search query."}), 400

    job_id = str(uuid.uuid4())

    with jobs_lock:
        jobs[job_id] = {
            "query": query,
            "status": "running",
            "logs": "",
            "result": None,
            "error": "",
        }

    worker = threading.Thread(target=run_search_job, args=(job_id, query), daemon=True)
    worker.start()

    return jsonify(
        {
            "job_id": job_id,
            "status": "running",
        }
    )


@app.get("/api/search/<job_id>")
def search_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)

        if job is None:
            return jsonify({"error": "Job not found."}), 404

        payload = {
            "job_id": job_id,
            "status": job["status"],
            "logs": job["logs"],
            "error": job["error"],
        }

        if job["result"] is not None:
            payload.update(job["result"])

    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
