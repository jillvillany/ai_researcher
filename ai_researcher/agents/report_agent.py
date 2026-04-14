from langchain_community.chat_models import ChatOllama
from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_classic import hub
from ai_researcher.tools.report_tools import generate_pdf_report

class ReportAgent():
    def __init__(self):
        self.llm = ChatOllama(
            model="granite4:3b",
            temperature=0
        )
        self.tools = [generate_pdf_report]
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

    def run(self, report_data):
        response = self.executor.invoke({
            "input": f"Use the research data below to generate a nicely formatted PDF:\n{report_data}"
        })

        return response["output"]