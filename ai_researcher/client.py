import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()


class MCPOpenAIClient:
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server.

        Args:
            server_script_path: Path to the server script.
        """
        # Server configuration
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_script_path],
        )

        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # Initialize the connection
        await self.session.initialize()

        # List available tools
        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format.

        Returns:
            A list of tools in OpenAI format.
        """
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from OpenAI.
        """
        tools = await self.get_mcp_tools()
        tool_names = {
            tool["function"]["name"]
            for tool in tools
            if tool.get("type") == "function" and tool.get("function")
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI research workflow assistant with access to MCP tools. "
                    "Use the available tools whenever they are needed to complete the user's request. "
                    "For requests that ask for research plus a PDF report, first gather information with "
                    "the research tool, then create the PDF with the report tool. "
                    "You may call tools multiple times if needed. "
                    "Do not ask the user for clarification if the request is broad but actionable. "
                    "Use the user's query directly with the research tool, summarize what you find, "
                    "and continue the workflow. "
                    "If a tool fails, surface that failure clearly instead of answering from prior knowledge."
                ),
            },
            {"role": "user", "content": query},
        ]
        forced_first_tool = None
        forced_next_tool = None
        wants_report = any(phrase in query.lower() for phrase in ["report", "pdf"])
        search_called = False
        report_called = False
        report_url = ""
        lowered_query = query.lower()
        if "search_ai_research" in tool_names and any(
            phrase in lowered_query for phrase in ["latest", "research", "report", "pdf", "ai"]
        ):
            forced_first_tool = {
                "type": "function",
                "function": {"name": "search_ai_research"},
            }

        while True:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=forced_first_tool or forced_next_tool or "auto",
            )
            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump(exclude_none=True))
            forced_first_tool = None
            forced_next_tool = None

            if not assistant_message.tool_calls:
                if wants_report and search_called and not report_called and "convert_html_to_pdf" in tool_names:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "You have already gathered research. Now you must generate a complete HTML "
                                "report and call convert_html_to_pdf with that HTML in the report_html argument. "
                                "Do not finish without creating the PDF report."
                            ),
                        }
                    )
                    forced_next_tool = {
                        "type": "function",
                        "function": {"name": "convert_html_to_pdf"},
                    }
                    continue
                if report_url:
                    return report_url
                return assistant_message.content

            for tool_call in assistant_message.tool_calls:
                print(f"Calling MCP tool: {tool_call.function.name}")
                result = await self.session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )
                tool_text = "\n".join(
                    item.text for item in result.content if hasattr(item, "text")
                )
                tool_failed = getattr(result, "isError", False) or any(
                    marker in tool_text.lower()
                    for marker in [
                        "failed",
                        "error",
                        "not installed",
                        "not set",
                        "traceback",
                    ]
                )

                if tool_failed:
                    raise RuntimeError(
                        f"MCP tool `{tool_call.function.name}` failed: {tool_text or 'Unknown tool error.'}"
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_text,
                    }
                )

                if tool_call.function.name == "search_ai_research":
                    search_called = True
                    if wants_report and not report_called and "convert_html_to_pdf" in tool_names:
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "Using the research results you just received, create a polished HTML report "
                                    "with inline CSS and call convert_html_to_pdf next."
                                ),
                            }
                        )
                        forced_next_tool = {
                            "type": "function",
                            "function": {"name": "convert_html_to_pdf"},
                        }

                if tool_call.function.name == "convert_html_to_pdf":
                    report_called = True
                    if tool_text.strip().startswith("/reports/"):
                        report_url = tool_text.strip()
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    f"The PDF report was created successfully at {report_url}. "
                                    "Do not call more tools unless absolutely necessary."
                                ),
                            }
                        )
                    elif wants_report:
                        raise RuntimeError(
                            "MCP tool `convert_html_to_pdf` did not return a PDF report URL."
                        )

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client."""
    client = MCPOpenAIClient()
    await client.connect_to_server("server.py")

    # Example: Ask about company vacation policy
    query = "Can you research the different orchestration patterns of agentic systmems and write a PDF report on it?"
    print(f"\nQuery: {query}")

    response = await client.process_query(query)
    print(f"\nResponse: {response}")


if __name__ == "__main__":
    asyncio.run(main())
