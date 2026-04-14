from langchain_community.chat_models import ChatOllama
from langchain_classic.agents import create_structured_chat_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_classic import hub

from ai_researcher.tools.research_tools import (
    search_ai_research,
    summarize_with_citations,
)


def run_research_agent():

    llm = ChatOllama(
        model="llama3",
        temperature=0
    )

    tools = [
        search_ai_research,
        summarize_with_citations
    ]

    prompt = hub.pull("hwchase17/structured-chat-agent")

    agent = create_structured_chat_agent(
        llm,
        tools,
        prompt
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True
    )

    response = executor.invoke({
        "input": "Find the latest AI research and summarize it with citations."
    })

    return response["output"]


if __name__ == "__main__":
    print(run_research_agent())