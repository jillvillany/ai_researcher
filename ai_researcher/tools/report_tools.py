from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from playwright.sync_api import sync_playwright


TMP_DIR = Path(__file__).resolve().parents[2] / "tmp"


@tool(return_direct=True)
def convert_html_to_pdf(report_html: str) -> str:
    """
    Generate a formatted PDF report from research summary text.
    Returns the file path of the generated PDF.
    """

    # report_html = report_html.split("```html")[-1]
    # report_html = report_html.split("```")[0]

    TMP_DIR.mkdir(exist_ok=True)

    filename = f"ai_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = TMP_DIR / filename

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.set_content(report_html, wait_until="networkidle")

        page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True
        )

        browser.close()

    return f"/reports/{filename}"
