from langchain_community.chat_models import ChatOllama
from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_classic import hub

from ai_researcher.tools.research_tools import search_ai_research, summarize_with_citations


class ResearchAgent():
    def __init__(self):
        self.llm = ChatOllama(
            model="granite4:3b",
            temperature=0
        )
        self.tools = [search_ai_research, summarize_with_citations]
        self.prompt = hub.pull("hwchase17/react")
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            self.prompt
        )
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True
        )

    def run(self, query):
        response = self.executor.invoke({
            "input": f"Find the latest AI research that pertains to th query below and summarize it with citations.\nQuery:\n{query}"
        })

        return response["output"]


if __name__ == "__main__":
    query = "latest NLP research for AI engineers"

    research_agent = ResearchAgent()
    print(research_agent.run(query))