from langchain_community.chat_models import ChatOllama
from langchain_classic import hub
from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor

from ai_researcher.tools.research_tools import search_ai_research


class ResearchAgent():
    def __init__(self):
        self.llm = ChatOllama(
            model="granite4:3b",
            temperature=0
        )
        self.tools = [search_ai_research]
        self.prompt = hub.pull("hwchase17/react")
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            self.prompt
        )
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=4,
            handle_parsing_errors=True
        )

    def run(self, query):
        response = self.executor.invoke({
            "input": (
                "You are researching the latest informaiton related to the user's query. "
                "Use the available tools to gather evidence, then write a summary of the research found yourself."
                "Do not call tools for summarization or formatting. "
                "After you have enough evidence, stop using tools and return the research found "
                "in a concise summary."
                f"Query:\n{query}"
            )
        })
        return response["output"]


if __name__ == "__main__":
    query = "AI"

    research_agent = ResearchAgent()
    print(research_agent.run(query))
