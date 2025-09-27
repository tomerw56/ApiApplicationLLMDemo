# mcp_server.py
import asyncio
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP, Context
from app import app as fastapi_app  # your FastAPI app

mcp = FastMCP("project-mcp")

@mcp.tool()
async def get_project_data(ctx: Context, session_key: str) -> dict:
    client = fastapi_app.test_client()
    resp = client.get("/get_project_data", params={"session_key": session_key})
    return resp.json()

@mcp.tool()
async def set_structure(ctx: Context, session_key: str, name: str, fields: list[dict]) -> dict:
    client = fastapi_app.test_client()
    payload = {"session_key": session_key, "structure": {"name": name, "fields": fields}}
    resp = client.post("/set_structure", json=payload)
    return resp.json()

@mcp.tool()
async def set_message(ctx: Context, session_key: str, name: str, content: dict) -> dict:
    client = fastapi_app.test_client()
    payload = {"session_key": session_key, "message": {"name": name, "content": content}}
    resp = client.post("/set_message", json=payload)
    return resp.json()


if __name__ == "__main__":
    # don’t wrap with asyncio.run, just call run()
    mcp.run()
