
import arxiv
from langchain.tools import tool
from textwrap import dedent


@tool
def search_ai_research(query:str) -> str:
    """
    Searches arXiv for the latest AI research papers.
    Returns top 3 newest results.
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

    return results


@tool
def summarize_with_citations(papers:list[dict]) -> str:
    """
    Summarizes research papers and formats output
    with article title, author, and publication date.
    """

    summaries = []

    for paper in papers:

        summary = f"""
        Title: {paper['title']}
        Authors: {", ".join(paper['authors'])}
        Published: {paper['published']}
        Link: {paper['link']}

        Summary:
        {paper['summary']}
        """

        summaries.append(dedent(summary))

    return "\n\n".join(summaries)