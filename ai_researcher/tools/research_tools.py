from textwrap import dedent

import arxiv
from langchain.tools import tool


@tool
def search_ai_research(query:str) -> str:
    """
    Searches arXiv for the latest AI research papers.
    Returns top 3 newest results as a readable text digest.
    """

    search = arxiv.Search(
        query=query,
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = []

    for paper in search.results():
        results.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "published": str(paper.published.date()),
            "summary": paper.summary,
            "link": paper.entry_id
        })

    if not results:
        return "No papers were found for that query."

    paper_summaries = []
    for paper in results:
        paper_summary = f"""
        Title: {paper['title']}
        Authors: {", ".join(paper['authors'])}
        Published: {paper['published']}
        Link: {paper['link']}
        Abstract: {paper['summary']}
        """
        paper_summaries.append(dedent(paper_summary).strip())

    return "\n\n".join(paper_summaries)