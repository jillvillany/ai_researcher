from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from ai_researcher.graph import ResearchGraph

app = Flask(__name__)
research_graph = ResearchGraph()
REPORTS_DIR = Path(__file__).resolve().parents[1] / "tmp"


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

    try:
        result = research_graph.run(query)
    except Exception as exc:
        return jsonify(
            {
                "error": "The research workflow failed.",
                "details": str(exc),
            }
        ), 500

    report = result.get("report", "")
    report_pdf_url = report if isinstance(report, str) and report.startswith("/reports/") else ""

    return jsonify(
        {
            "query": query,
            "research_results": result.get("research_results", ""),
            "report": report,
            "report_pdf_url": report_pdf_url,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
