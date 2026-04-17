import os
import json
import requests
from bs4 import BeautifulSoup
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()


@tool()
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