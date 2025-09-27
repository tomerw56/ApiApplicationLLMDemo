import asyncio
import json
import subprocess
import ollama

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# Path to your MCP server script (adjust)
MCP_SERVER_CMD = ["python", "api_tool_as_mcp.py"]

async def run_demo():
    # Launch MCP server as subprocess (stdio transport)
    server_params = StdioServerParameters(
        command=MCP_SERVER_CMD[0],
        args=MCP_SERVER_CMD[1:],
        env=None
    )
    read, write = await stdio_client(server_params).__aenter__()  # gets (reader, writer, proc)
    session = await ClientSession(read, write).__aenter__()

    # Must initialize the session
    await session.initialize()

    # 1. List available tools
    tools = await session.list_tools()
    print("🛠 Available tools:", tools)

    # 2. Formulate Ollama prompt embedding tools
    tool_defs = [t.to_dict() for t in tools]
    prompt = f"""
You are an API assistant. These are the tools you can use:
{json.dumps(tool_defs, indent=2)}

User: "Create a structure user_profile with fields username(string required), age(int), bio(string)"

Respond with only valid JSON:
{{
  "tool": "set_structure",
  "arguments": {{
    "session_key": "{session.session_id}",  // or your own session key
    "name": "user_profile",
    "fields": [
      {{"name":"username","type":"string","required": true}},
      {{"name":"age","type":"int","required": false}},
      {{"name":"bio","type":"string","required": false}}
    ]
  }}
}}
    """
    # Ask Ollama
    resp = ollama.chat(model="llama3", messages=[{"role":"user","content":prompt}])
    llm_out = resp["message"]["content"]
    print("LLM Output:", llm_out)

    # Extract JSON
    # (reuse your extract_json or block extractor)
    action_call = json.loads(llm_out)  # assume clean

    tool_name = action_call["tool"]
    args = action_call["arguments"]

    # 3. Call that tool
    result = await session.call_tool(tool_name, args)
    print("Tool Result:", result)

    # 4. Optionally, call get_project_data to see state
    result2 = await session.call_tool("get_project_data", {"session_key": args["session_key"]})
    print("Project Data:", result2)

    # Close session and server
    await session.__aexit__(None, None, None)
    await stdio_client(server_params).__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(run_demo())
