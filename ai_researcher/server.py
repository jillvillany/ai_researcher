import os
import sys
import json
import requests
from bs4 import BeautifulSoup 
from html import escape
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
load_dotenv()

TMP_DIR = Path(__file__).resolve().parents[1] / "tmp"


def _debug_log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


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


# Create an MCP server
mcp = FastMCP(
    name="AI Researcher",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8050,  # only used for SSE transport (set this to any port)
)


@mcp.tool()
def search_ai_research(query: str) -> str:
    """
    Searches Google News for the latest information and fetches article content.
    Returns a summary of article titles, sources, and text content.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY is not set.")

    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google_news",
            "q": query,
            "api_key": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()
    news_results = results.get("news_results", [])[:5]  # limit to top 5

    articles = []
    for item in news_results:
        title = item.get("title", "")
        link = item.get("link", "")
        source = item.get("source", {}).get("name", "")
        date = item.get("date", "")
        content = ""

        if link:
            try:
                page = requests.get(
                    link,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                soup = BeautifulSoup(page.text, "html.parser")
                # Remove noise
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                # Grab paragraphs
                paragraphs = soup.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs[:20])
            except Exception as e:
                content = f"Could not fetch content: {e}"

        articles.append({
            "title": title,
            "source": source,
            "date": date,
            "link": link,
            "content": content,
        })

    return json.dumps(articles, ensure_ascii=False)


@mcp.tool()
async def convert_html_to_pdf(report_html: str) -> str:
    """
    Generate a PDF from a complete HTML document.
    The report_html argument MUST be a full HTML document starting with <!doctype html>
    or <html>. Do NOT pass plain text or markdown — pass valid HTML only.
    Returns the /reports/<filename> URL of the generated PDF.
    """
    _debug_log("convert_html_to_pdf: normalizing HTML input")
    report_html = _normalize_report_html(report_html)

    TMP_DIR.mkdir(exist_ok=True)

    filename = f"ai_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = TMP_DIR / filename
    html_debug_path = TMP_DIR / f"{output_path.stem}.html"
    html_debug_path.write_text(report_html, encoding="utf-8")
    _debug_log(f"convert_html_to_pdf: wrote debug HTML to {html_debug_path}")

    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF generation failed because Playwright is not installed. "
            "Run `uv sync` and `playwright install`."
        ) from exc

    try:
        async with async_playwright() as p:
            _debug_log("convert_html_to_pdf: launching Chromium")
            browser = await p.chromium.launch()
            page = await browser.new_page()

            _debug_log("convert_html_to_pdf: setting page content")
            await page.set_content(report_html, wait_until="networkidle")

            _debug_log(f"convert_html_to_pdf: writing PDF to {output_path}")
            await page.pdf(path=str(output_path), format="A4", print_background=True)

            await browser.close()
    except Exception as exc:
        # Re-raise with the REAL error message this time
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    return f"/reports/{filename}"


# Run the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
