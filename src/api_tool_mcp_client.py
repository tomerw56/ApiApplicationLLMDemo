import asyncio
import json
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional

import ollama

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


CONFIG_FILE_NAME="api_tool_mcp_config.json"
CONFIG_NAME="API_TOOL"

class OllamaMCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    def load_server_config(self,name: str, path:str=CONFIG_FILE_NAME):
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


        server_params = self.load_server_config(name=CONFIG_NAME)
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
        await client.ask_ollama(user_prompt = "Create a structure user_profile with fields "
                                              "username(string required), age(int), bio(string)")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

# # Path to your MCP server script (adjust)
# MCP_SERVER_CMD = ["python", "api_tool_as_mcp_server.py"]
#
#
#
# async def run_demo():
#     # Launch MCP server as subprocess (stdio transport)
#     server_params = StdioServerParameters(
#         command=MCP_SERVER_CMD[0],
#         args=MCP_SERVER_CMD[1:],
#         env=None
#     )
#     read, write = await stdio_client(server_params).__aenter__()  # gets (reader, writer, proc)
#     session = await ClientSession(read, write).__aenter__()
#
#     # Must initialize the session
#     await session.initialize()
#
#     # 1. List available tools
#     tools = await session.list_tools()
#     print("🛠 Available tools:", tools)
#
#     # 2. Formulate Ollama prompt embedding tools
#     tool_defs = [t.to_dict() for t in tools]
#     prompt = f"""
# You are an API assistant. These are the tools you can use:
# {json.dumps(tool_defs, indent=2)}
#
# User: "Create a structure user_profile with fields username(string required), age(int), bio(string)"
#
# Respond with only valid JSON:
# {{
#   "tool": "set_structure",
#   "arguments": {{
#     "session_key": "{session.session_id}",  // or your own session key
#     "name": "user_profile",
#     "fields": [
#       {{"name":"username","type":"string","required": true}},
#       {{"name":"age","type":"int","required": false}},
#       {{"name":"bio","type":"string","required": false}}
#     ]
#   }}
# }}
#     """
#     # Ask Ollama
#     resp = ollama.chat(model="llama3", messages=[{"role":"user","content":prompt}])
#     llm_out = resp["message"]["content"]
#     print("LLM Output:", llm_out)
#
#     # Extract JSON
#     # (reuse your extract_json or block extractor)
#     action_call = json.loads(llm_out)  # assume clean
#
#     tool_name = action_call["tool"]
#     args = action_call["arguments"]
#
#     # 3. Call that tool
#     result = await session.call_tool(tool_name, args)
#     print("Tool Result:", result)
#
#     # 4. Optionally, call get_project_data to see state
#     result2 = await session.call_tool("get_project_data", {"session_key": args["session_key"]})
#     print("Project Data:", result2)
#
#     # Close session and server
#     await session.__aexit__(None, None, None)
#     await stdio_client(server_params).__aexit__(None, None, None)
#
#
# if __name__ == "__main__":
#     asyncio.run(run_demo())
