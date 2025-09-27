import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    # Parameters to run the hello server
    params = StdioServerParameters(command="python", args=["hello_mcp_server.py"])

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # List tools
            response = await session.list_tools()
            tools = response.tools
            print("Available tools:", [t.name for t in tools])

            # Call the hello tool
            response = await session.call_tool("hello", {"name": "Tomer"})
            for content in response.content:
                if content.type == 'text':
                    print("Tool result:", content.text)
                else:
                    print("Un known response:", content)
if __name__ == "__main__":
    asyncio.run(main())
