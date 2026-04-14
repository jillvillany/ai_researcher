from langchain_openai import ChatOpenAI
from ai_researcher.tools.research_tools import (
    search_ai_research,
    summarize_with_citations,
)


# register tools
tools = [
    search_ai_research,
    summarize_with_citations
]

tool_map = {
    tool.name: tool
    for tool in tools
}



def run_research_agent():

    tools = [
        search_ai_research,
        summarize_with_citations
    ]

    llm = ChatOpenAI(
    model="gpt-4o",
        temperature=0
    ).bind_tools(tools)

    response = llm.invoke("Find the latest AI research and summarize it with citations.")

    return response


if __name__ == "__main__":
    print(run_research_agent())