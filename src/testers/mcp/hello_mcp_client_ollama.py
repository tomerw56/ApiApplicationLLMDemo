import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional

import ollama
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

class OllamaMCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    def load_server_config(self,name: str, path="mcp_config.json"):
        config = json.loads(Path(path).read_text())
        server_cfg = config["servers"][name]

        if server_cfg["type"] == "stdio":
            return StdioServerParameters(
                command=server_cfg["command"],
                args=server_cfg.get("args", [])
            )
        else:
            raise ValueError(f"Unsupported server type: {server_cfg['type']}")

    async def connect_to_server(self):
        """Connect to an MCP server"""

        #server_params = StdioServerParameters(command="python", args=["hello_mcp_server.py"])
        server_params = self.load_server_config("hello")
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    @staticmethod
    def extract_json(text: str):
        """Extract JSON from text (first { to last })."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start > end:
            raise ValueError("No JSON object found")
        return json.loads(text[start:end+1])

    async def ask_ollama(self, user_prompt: str) -> str:
        """Process a query using Claude and available tools"""

        response = await self.session.list_tools()
        tools = response.tools
        tools_schema = [t.__dict__ for t in tools]
        print("Available tools:", [t.name for t in tools])

        system_prompt = f"""
            You are an assistant that controls API tools.

            You have access to these tools:
            {json.dumps(tools_schema, indent=2)}

            Instruction: {user_prompt}

            Respond ONLY with valid JSON in this format:
            {{
              "tool": "tool_name",
              "arguments": {{
                "name": "value"
              }}
            }}
            """
        ollama_response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": system_prompt}],
        )
        ollama_response_content= ollama_response.message.content
        try:
            tool_call = self.extract_json(ollama_response_content)
        except Exception as e:
            print("⚠️ Failed to parse JSON from LLM:", e)
            return "Error: Failed to parse JSON from LLM"

        tool = tool_call["tool"]
        args = tool_call["arguments"]

        # Call the tool
        response = await self.session.call_tool(tool, args)
        for content in response.content:
            if content.type == "text":
                print("✅ Tool result:", content.text)
                return f"OK: {content.text}"
            else:
                print("Unknown response:", content)
                return "Error: Unknown response"
        return "Error: Default activation"

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():

    client = OllamaMCPClient()
    try:
        await client.connect_to_server()
        await client.ask_ollama(user_prompt = "Generate a random name and call the hello method")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
