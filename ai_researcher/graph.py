from typing import TypedDict
from langgraph.graph import StateGraph, END

from ai_researcher.agents.research_agent import ResearchAgent
from ai_researcher.agents.report_agent import ReportAgent

# define state data
class AgentState(TypedDict):
    query: str
    research_results: str
    report: str

# define nodes
def research_node(state):
    research_agent = ResearchAgent()
    results = research_agent.run(state["query"])

    return {
        "research_results": results
    }

def report_node(state):
    report_agent = ReportAgent()
    report = report_agent.run(state["research_results"])

    return {
        "report": report
    }

# define graph
class ResearchGraph():
    def __init__(self):
        builder = StateGraph(AgentState)

        builder.add_node("research", research_node)
        builder.add_node("report", report_node)

        builder.set_entry_point("research")

        builder.add_edge("research", "report")
        builder.add_edge("report", END)

        self.graph = builder.compile()

    def run(self, query):
        result = self.graph.invoke({
            "query": query
        })

        return result


if __name__ == "__main__":
    query = "AI"

    research_graph = ResearchGraph()
    result = research_graph.run(query)