"""Unit tests for research and report tools."""
from unittest.mock import MagicMock, patch

from ai_researcher.tools.research_tools import search_ai_research
from ai_researcher.tools.report_tools import convert_html_to_pdf


VALID_HTML = "<!doctype html><html><body><h1>Report</h1></body></html>"


# ---------------------------------------------------------------------------
# search_ai_research (LangChain tool wrapping SerpAPI)
# ---------------------------------------------------------------------------

class TestSearchAiResearch:
    def test_returns_news_results(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "fake-key")

        fake_results = [
            {"title": "AI makes breakthrough", "source": {"name": "TechNews"}, "link": "https://example.com"},
            {"title": "New LLM released", "source": {"name": "AIDaily"}, "link": "https://example.com/2"},
        ]
        mock_client = MagicMock()
        mock_client.search.return_value = {"news_results": fake_results}

        with patch("ai_researcher.tools.research_tools.serpapi.Client", return_value=mock_client):
            result = search_ai_research.invoke({"query": "AI trends"})

        assert result == fake_results

    def test_passes_query_to_serpapi(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "my-key")

        mock_client = MagicMock()
        mock_client.search.return_value = {"news_results": []}

        with patch("ai_researcher.tools.research_tools.serpapi.Client", return_value=mock_client) as MockClient:
            search_ai_research.invoke({"query": "quantum computing"})

        MockClient.assert_called_once_with(api_key="my-key")
        call_args = mock_client.search.call_args[0][0]
        assert call_args["q"] == "quantum computing"
        assert call_args["engine"] == "google_news"

    def test_returns_empty_list_when_no_results(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "fake-key")

        mock_client = MagicMock()
        mock_client.search.return_value = {"news_results": []}

        with patch("ai_researcher.tools.research_tools.serpapi.Client", return_value=mock_client):
            result = search_ai_research.invoke({"query": "obscure topic"})

        assert result == []


# ---------------------------------------------------------------------------
# convert_html_to_pdf (LangChain tool wrapping sync Playwright)
# ---------------------------------------------------------------------------

class TestConvertHtmlToPdf:
    def test_returns_reports_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.tools.report_tools.TMP_DIR", tmp_path)

        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_p = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_pw_cm = MagicMock()
        mock_pw_cm.__enter__ = MagicMock(return_value=mock_p)
        mock_pw_cm.__exit__ = MagicMock(return_value=False)

        with patch("ai_researcher.tools.report_tools.sync_playwright", return_value=mock_pw_cm):
            result = convert_html_to_pdf.invoke({"report_html": VALID_HTML})

        assert result.startswith("/reports/")
        assert result.endswith(".pdf")

    def test_calls_playwright_pdf(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.tools.report_tools.TMP_DIR", tmp_path)

        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_p = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_pw_cm = MagicMock()
        mock_pw_cm.__enter__ = MagicMock(return_value=mock_p)
        mock_pw_cm.__exit__ = MagicMock(return_value=False)

        with patch("ai_researcher.tools.report_tools.sync_playwright", return_value=mock_pw_cm):
            convert_html_to_pdf.invoke({"report_html": VALID_HTML})

        mock_page.set_content.assert_called_once_with(VALID_HTML, wait_until="networkidle")
        mock_page.pdf.assert_called_once()

    def test_pdf_written_to_tmp_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.tools.report_tools.TMP_DIR", tmp_path)

        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_p = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_pw_cm = MagicMock()
        mock_pw_cm.__enter__ = MagicMock(return_value=mock_p)
        mock_pw_cm.__exit__ = MagicMock(return_value=False)

        with patch("ai_researcher.tools.report_tools.sync_playwright", return_value=mock_pw_cm):
            result = convert_html_to_pdf.invoke({"report_html": VALID_HTML})

        filename = result.removeprefix("/reports/")
        pdf_path_arg = str(mock_page.pdf.call_args.kwargs.get("path") or mock_page.pdf.call_args[1].get("path") or mock_page.pdf.call_args[0][0])
        assert filename in pdf_path_arg
