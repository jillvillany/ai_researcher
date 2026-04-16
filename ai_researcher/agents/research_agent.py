import os

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from ai_researcher.tools.research_tools import search_ai_research


class ResearchAgent():
    def __init__(self):
        self.tool_map = {
            search_ai_research.name: search_ai_research,
        }
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_RESEARCH_MODEL", "gpt-5.4-mini"),
            temperature=0,
        ).bind_tools(
            [search_ai_research],
            parallel_tool_calls=False,
        )

    def run(self, query):
        messages = [
            SystemMessage(
                content=(
                    "You are researching the latest AI information related to the user's query. "
                    "Use tools only to gather evidence. After you have enough evidence, write the "
                    "summary yourself. Do not use tools for summarization or formatting."
                    "Provide sources and links for all your findings."
                    "Do not make up any findings or links."
                    "You only need to conduct one search as this is a high level summary but be sure to look at multiple sources."
                )
            ),
            HumanMessage(content=f"Research query:\n{query}"),
        ]

        for _ in range(4):
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response.content

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool = self.tool_map[tool_name]
                tool_args = tool_call.get("args", {})
                print(f"ResearchAgent calling tool: {tool_name}", flush=True)
                tool_result = tool.invoke(tool_args)
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                )

        raise RuntimeError("Research agent exceeded the maximum number of tool iterations.")


if __name__ == "__main__":
    query = "AI"

    research_agent = ResearchAgent()
    print(research_agent.run(query))
