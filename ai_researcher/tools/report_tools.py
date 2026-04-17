from datetime import datetime
from pathlib import Path
from html import escape
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright


TMP_DIR = Path(__file__).resolve().parents[2] / "tmp"



def _normalize_report_html(report_html: str) -> str:
    cleaned = (report_html or "").strip()
    cleaned = cleaned.split("```html")[-1]
    cleaned = cleaned.split("```")[0].strip()

    if not cleaned:
        raise ValueError("convert_html_to_pdf received empty report_html.")

    lowered = cleaned.lower()
    if "<html" in lowered or "<!doctype html" in lowered:
        return cleaned

    # If the model returned plain text instead of full HTML, wrap it in a simple document.
    return f"""<!doctype html>
<html lang="en">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Research Report</title>
    <style>
        body {{
        font-family: Arial, sans-serif;
        margin: 40px;
        color: #18261d;
        line-height: 1.6;
        }}
        h1 {{
        margin-bottom: 16px;
        }}
        .content {{
        white-space: pre-wrap;
        }}
    </style>
    </head>
    <body>
    <h1>AI Research Report</h1>
    <div class="content">{escape(cleaned)}</div>
    </body>
</html>"""


# NOTE: Since the is a smaller model - return_direct is needed
# So that this tool usage doesn't loop
@tool(return_direct=True)
def convert_html_to_pdf(report_html: str) -> str:
    """
    Generate a PDF from a complete HTML document.
    The report_html argument MUST be a full HTML document starting with <!doctype html>
    or <html>. Do NOT pass plain text or markdown — pass valid HTML only.
    Returns the /reports/<filename> URL of the generated PDF.
    """
    print("normalizing HTML input")
    report_html = _normalize_report_html(report_html)

    TMP_DIR.mkdir(exist_ok=True)

    filename = f"ai_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = TMP_DIR / filename
    html_debug_path = TMP_DIR / f"{output_path.stem}.html"
    html_debug_path.write_text(report_html, encoding="utf-8")
    print(f"wrote debug HTML to {html_debug_path}")

    try:
        with sync_playwright() as p:
            print("launching Chromium")
            browser = p.chromium.launch()
            page = browser.new_page()

            print("setting page content")
            page.set_content(report_html, wait_until="networkidle")

            print(f"writing PDF to {output_path}")
            page.pdf(path=str(output_path), format="A4", print_background=True)

            browser.close()
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    return f"/reports/{filename}"
