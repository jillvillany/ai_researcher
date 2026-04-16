class ResearchGraph():
    def __init__(self):
        from ai_researcher.agents.orchestrator_agent import OrchestratorAgent

        self.orchestrator = OrchestratorAgent()

    def run(self, query):
        return self.orchestrator.run(query)


if __name__ == "__main__":
    query = "AI"

    research_graph = ResearchGraph()
    result = research_graph.run(query)
