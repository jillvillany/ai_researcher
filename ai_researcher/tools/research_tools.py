import os
import serpapi
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()


@tool
def search_ai_research(query:str) -> str:
    """
    Searches Google News for the latest information.
    Related to the user query.
    """

    client = serpapi.Client(api_key=os.getenv("SERPAPI_KEY"))
    results = client.search({
    "engine": "google_news",
    "q": query
    })
    news_results = results["news_results"]

    return news_results