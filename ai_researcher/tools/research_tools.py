from langchain_core.tools import tool
import arxiv
from textwrap import dedent


@tool(return_direct=True)
def research_digest(query: str) -> str:
    """
    Search arXiv for latest AI research and return formatted citations.
    """

    search = arxiv.Search(
        query=query,
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    summaries = []

    for paper in search.results():

        summary = f"""
        Title: {paper.title}
        Authors: {", ".join(a.name for a in paper.authors)}
        Published: {paper.published.date()}
        Link: {paper.entry_id}

        Summary:
        {paper.summary}
        """

        summaries.append(dedent(summary))

    return "\n\n".join(summaries)