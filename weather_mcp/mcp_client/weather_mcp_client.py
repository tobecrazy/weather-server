from fastmcp import Client

async def main():
 
    # Connect via SSE
    async with Client("http://localhost:3399/sse") as client:
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(f"Result: {result.text}")
        