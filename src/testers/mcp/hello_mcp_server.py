import asyncio
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("hello-server")

@mcp.tool("hello")
async def hello_tool(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport='stdio')
