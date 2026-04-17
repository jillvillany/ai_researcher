import anyio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from pathlib import Path

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
        self.openai_client = AsyncOpenAI()
        self.model = model
        self._stdio_cm = None
        self._session_cm = None

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server.

        Args:
            server_script_path: Path to the server script.
        """
        # Resolve the python executable: prefer the venv, fall back to current
        # NOTE: needed when running from the vscode debugger
        venv_python = Path(server_script_path).resolve().parent.parent / ".venv" / "bin" / "python"
        python_exec = str(venv_python) if venv_python.exists() else sys.executable
        
        # Server configuration
        server_params = StdioServerParameters(
            command=python_exec,
            args=[server_script_path],
        )

        self._stdio_cm = stdio_client(server_params)
        stdio, write = await self._stdio_cm.__aenter__()

        self._session_cm = ClientSession(stdio, write)
        self.session = await self._session_cm.__aenter__()

        await self.session.initialize()

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
                    "For every user request, you MUST always follow these two steps in order:\n"
                    "1. Call search_ai_research with the user's topic to gather information.\n"
                    "2. Call convert_html_to_pdf with a well-structured HTML report of your findings.\n"
                    "Never skip step 2 — always generate a PDF, regardless of how the user phrases their query. "
                    "You may call search_ai_research multiple times if needed for broader coverage. "
                    "Do not ask the user for clarification. "
                    "Do not use prior knowledge, use the latest information as of today's date."
                    "If a tool fails, surface that failure clearly instead of answering from prior knowledge. "
                    "IMPORTANT: When calling convert_html_to_pdf, the report_html argument must be a "
                    "complete, valid HTML document (starting with <!doctype html>). Use proper HTML tags "
                    "for structure (h1, h2, p, ul, li, etc.) and inline CSS for styling. "
                    "Never pass plain text or markdown — always pass rendered HTML."
                ),
            },
            {"role": "user", "content": query},
        ]

        report_url = ""  # track PDF url independently of LLM response - this way doesn't error if llm returns message at end about report path

        while True:
            response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump(exclude_none=True))

            if not assistant_message.tool_calls:
                # Return the PDF url if we got one, otherwise the LLM text
                return report_url if report_url else assistant_message.content

            for tool_call in assistant_message.tool_calls:
                print(f"Calling MCP tool: {tool_call.function.name}")
                result = await self.session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )
                tool_text = "\n".join(
                    item.text for item in result.content if hasattr(item, "text")
                ).strip()

                # Capture PDF url directly from tool output, don't trust the LLM to relay it
                if tool_call.function.name == "convert_html_to_pdf":
                    if tool_text.startswith("/reports/"):
                        report_url = tool_text

                # error check
                tool_failed = getattr(result, "isError", False)
                if tool_failed:
                    raise RuntimeError(
                        f"MCP tool `{tool_call.function.name}` failed: {tool_text or 'Unknown tool error.'}"
                    )

                # ALWAYS append tool result — must come last, after everything else
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_text,
                })


    async def cleanup(self):
        if self._session_cm:
            await self._session_cm.__aexit__(None, None, None)
        if self._stdio_cm:
            await self._stdio_cm.__aexit__(None, None, None)


async def main():
    client = MCPOpenAIClient()
    
    try:
        await client.connect_to_server("ai_researcher/server.py")
        
        query = "Can you research the different orchestration patterns of agentic systems and write a PDF report on it?"
        print(f"\nQuery: {query}")
        
        response = await client.process_query(query)
        print(f"\nResponse: {response}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    anyio.run(main, backend="asyncio") # force asyncio backend to match MCP's expectation
