"""Unit tests for MCP server tools and helpers."""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_researcher.server import _normalize_report_html, search_ai_research, convert_html_to_pdf


# ---------------------------------------------------------------------------
# _normalize_report_html
# ---------------------------------------------------------------------------

class TestNormalizeReportHtml:
    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            _normalize_report_html("")

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError):
            _normalize_report_html("   ")

    def test_valid_html_returned_unchanged(self):
        html = "<!doctype html><html><body><p>Hello</p></body></html>"
        assert _normalize_report_html(html) == html

    def test_html_tag_triggers_passthrough(self):
        html = "<html><body>content</body></html>"
        assert _normalize_report_html(html) == html

    def test_plain_text_wrapped_in_html_document(self):
        result = _normalize_report_html("Just some plain text")
        assert "<!doctype html" in result.lower()
        assert "Just some plain text" in result

    def test_markdown_code_fence_stripped(self):
        fenced = "```html\n<!doctype html><html><body>hi</body></html>\n```"
        result = _normalize_report_html(fenced)
        assert "```" not in result
        assert "<!doctype html" in result.lower()

    def test_plain_text_is_html_escaped(self):
        result = _normalize_report_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ---------------------------------------------------------------------------
# search_ai_research
# ---------------------------------------------------------------------------

SERPAPI_RESPONSE = {
    "news_results": [
        {
            "title": "AI makes breakthrough",
            "link": "https://example.com/article1",
            "source": {"name": "TechNews"},
            "date": "2026-04-17",
        },
        {
            "title": "New LLM released",
            "link": "https://example.com/article2",
            "source": {"name": "AIDaily"},
            "date": "2026-04-16",
        },
    ]
}

ARTICLE_HTML = "<html><body><p>This is the article body text.</p></body></html>"


class TestSearchAiResearch:
    def test_raises_without_serpapi_key(self, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        with pytest.raises(ValueError, match="SERPAPI_KEY"):
            search_ai_research("AI trends")

    def test_returns_json_list_of_articles(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "fake-key")

        mock_serp = MagicMock()
        mock_serp.raise_for_status = MagicMock()
        mock_serp.json.return_value = SERPAPI_RESPONSE

        mock_article = MagicMock()
        mock_article.text = ARTICLE_HTML

        with patch("ai_researcher.server.requests.get", side_effect=[mock_serp, mock_article, mock_article]) as mock_get:
            result = search_ai_research("AI trends")

        articles = json.loads(result)
        assert isinstance(articles, list)
        assert len(articles) == 2
        assert articles[0]["title"] == "AI makes breakthrough"
        assert articles[0]["source"] == "TechNews"

    def test_article_fetch_failure_is_handled_gracefully(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "fake-key")

        mock_serp = MagicMock()
        mock_serp.raise_for_status = MagicMock()
        mock_serp.json.return_value = SERPAPI_RESPONSE

        with patch("ai_researcher.server.requests.get", side_effect=[mock_serp, Exception("timeout"), Exception("timeout")]):
            result = search_ai_research("AI trends")

        articles = json.loads(result)
        assert all("Could not fetch content" in a["content"] for a in articles)

    def test_limits_results_to_five(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "fake-key")

        many_results = {
            "news_results": [
                {"title": f"Article {i}", "link": "", "source": {"name": "S"}, "date": ""}
                for i in range(10)
            ]
        }
        mock_serp = MagicMock()
        mock_serp.raise_for_status = MagicMock()
        mock_serp.json.return_value = many_results

        with patch("ai_researcher.server.requests.get", return_value=mock_serp):
            result = search_ai_research("many results")

        assert len(json.loads(result)) == 5

    def test_passes_query_to_serpapi(self, monkeypatch):
        monkeypatch.setenv("SERPAPI_KEY", "my-key")

        mock_serp = MagicMock()
        mock_serp.raise_for_status = MagicMock()
        mock_serp.json.return_value = {"news_results": []}

        with patch("ai_researcher.server.requests.get", return_value=mock_serp) as mock_get:
            search_ai_research("quantum computing")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["q"] == "quantum computing"
        assert call_kwargs.kwargs["params"]["api_key"] == "my-key"


# ---------------------------------------------------------------------------
# convert_html_to_pdf
# ---------------------------------------------------------------------------

VALID_HTML = "<!doctype html><html><body><h1>Report</h1></body></html>"


class TestConvertHtmlToPdf:
    async def test_returns_reports_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.server.TMP_DIR", tmp_path)

        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_p = MagicMock()
        mock_p.chromium = mock_chromium

        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
            result = await convert_html_to_pdf(VALID_HTML)

        assert result.startswith("/reports/")
        assert result.endswith(".pdf")

    async def test_calls_playwright_pdf(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.server.TMP_DIR", tmp_path)

        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_p = MagicMock()
        mock_p.chromium = mock_chromium

        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
            await convert_html_to_pdf(VALID_HTML)

        mock_page.set_content.assert_called_once()
        mock_page.pdf.assert_called_once()

    async def test_writes_debug_html_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.server.TMP_DIR", tmp_path)

        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_p = MagicMock()
        mock_p.chromium = mock_chromium

        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
            await convert_html_to_pdf(VALID_HTML)

        html_files = list(tmp_path.glob("*.html"))
        assert len(html_files) == 1
        assert VALID_HTML in html_files[0].read_text()

    async def test_raises_on_empty_html(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.server.TMP_DIR", tmp_path)
        with pytest.raises(ValueError, match="empty"):
            await convert_html_to_pdf("")

    async def test_plain_text_is_auto_wrapped(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_researcher.server.TMP_DIR", tmp_path)

        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_p = MagicMock()
        mock_p.chromium = mock_chromium

        mock_playwright_cm = AsyncMock()
        mock_playwright_cm.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("playwright.async_api.async_playwright", return_value=mock_playwright_cm):
            await convert_html_to_pdf("plain text content")

        # set_content should have been called with a full HTML document
        called_html = mock_page.set_content.call_args[0][0]
        assert "<!doctype html" in called_html.lower()
