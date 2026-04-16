import os

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ai_researcher.agents.report_agent import ReportAgent
from ai_researcher.agents.research_agent import ResearchAgent


class OrchestratorAgent():
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.report_agent = ReportAgent()
        self.state = {
            "research_results": "",
            "report": "",
        }
        self.tools = [
            self._build_research_tool(),
            self._build_report_tool(),
        ]
        self.tool_map = {tool_item.name: tool_item for tool_item in self.tools}
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_ORCHESTRATOR_MODEL", "gpt-5.4"),
            temperature=0,
        ).bind_tools(
            self.tools,
            parallel_tool_calls=False,
        )

    def _build_research_tool(self):
        @tool
        def run_research_agent(query: str) -> str:
            """
            Delegate research gathering to the research specialist agent.
            Use this when you need current AI research findings for a query.
            """
            print("OrchestratorAgent delegating to ResearchAgent.", flush=True)
            result = self.research_agent.run(query)
            self.state["research_results"] = result
            return result

        return run_research_agent

    def _build_report_tool(self):
        @tool
        def run_report_agent(research_summary: str = "") -> str:
            """
            Delegate report creation to the report specialist agent.
            Use this after you have research findings and need a PDF report.
            """
            print("OrchestratorAgent delegating to ReportAgent.", flush=True)
            summary = research_summary or self.state["research_results"]
            if not summary:
                raise ValueError("Research findings are required before generating a report.")

            result = self.report_agent.run(summary)
            self.state["report"] = result
            return result

        return run_report_agent

    def run(self, query):
        self.state = {
            "research_results": "",
            "report": "",
        }
        messages = [
            SystemMessage(
                content=(
                    "You are an orchestration agent coordinating specialist AI agents. "
                    "Decide which specialist to call and when. "
                    "Use run_research_agent when you need research findings. "
                    "Use run_report_agent when you have enough research to generate the final PDF report. "
                    "If the user asks for a report or PDF report, you must not finish until a report has "
                    "been generated or you can clearly explain why it could not be generated. "
                    "For requests that ask to research and generate a report, call the research specialist "
                    "first and then the report specialist. "
                    "Do not invent research findings or report URLs."
                )
            ),
            HumanMessage(content=f"User request:\n{query}"),
        ]

        for _ in range(6):
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                if self.state["research_results"] and not self.state["report"]:
                    messages.append(
                        SystemMessage(
                            content=(
                                "You already have research findings, but no report has been generated yet. "
                                "If the user asked for a report, call run_report_agent now."
                            )
                        )
                    )
                    continue

                return {
                    "research_results": self.state["research_results"],
                    "report": self.state["report"],
                    "orchestrator_summary": response.content,
                }

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_runner = self.tool_map[tool_name]
                print(f"OrchestratorAgent calling tool: {tool_name}", flush=True)
                tool_result = tool_runner.invoke(tool_args)
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                )

        raise RuntimeError("Orchestrator agent exceeded the maximum number of tool iterations.")
