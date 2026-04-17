import pytest
from pathlib import Path
from ai_researcher.app import app as flask_app, jobs, jobs_lock

REPORTS_DIR = Path(__file__).resolve().parents[1] / "tmp"


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_jobs():
    with jobs_lock:
        jobs.clear()
    yield
    with jobs_lock:
        jobs.clear()


@pytest.fixture
def sample_pdf(tmp_path):
    """Write a minimal fake PDF into the real REPORTS_DIR and clean up after."""
    REPORTS_DIR.mkdir(exist_ok=True)
    pdf_file = REPORTS_DIR / "test_report.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")
    yield pdf_file
    pdf_file.unlink(missing_ok=True)
