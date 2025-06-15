import os
import sys
import argparse
import aiohttp
from fastmcp import Client
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path to import auth module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from weather_mcp.utils.auth import generate_token

async def main():
    parser = argparse.ArgumentParser(description="Weather MCP Client")
    parser.add_argument("--url", default="http://localhost:3397/sse", help="MCP server URL")
    parser.add_argument("--city", default=None, help="City for weather query")
    parser.add_argument("--days", type=int, default=0, help="Days offset (0=today, 1=tomorrow, etc.)")
    parser.add_argument("--token", help="Bearer token for authentication")
    parser.add_argument("--secret", help="Secret key to generate a token")
    args = parser.parse_args()
    
    # Handle authentication
    headers = {}
    if args.token:
        # Use provided token
        headers["Authorization"] = f"Bearer {args.token}"
    elif args.secret:
        # Generate a token using the provided secret
        token = generate_token(args.secret)
        headers["Authorization"] = f"Bearer {token}"
        print(f"Generated token: {token}")
    
    # Connect to the server
    print(f"Connecting to {args.url}")
    
    # Create a custom session with headers
    session = aiohttp.ClientSession(headers=headers)
    
    # Connect using the custom session
    try:
        # Try with session parameter first (newer versions of fastmcp)
        client = Client(args.url, session=session)
    except TypeError:
        # Fall back to older versions of fastmcp
        client = Client(args.url)
        client._session = session
    
    async with client:
        try:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {tools}")
            
            # Call the weather tool
            weather_args = {}
            if args.city:
                weather_args["city"] = args.city
            if args.days is not None:
                weather_args["days"] = args.days
                
            result = await client.call_tool("weather.get_weather", weather_args)
            print(f"Weather result: {result.text}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Ensure the session is closed
            if not session.closed:
                await session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
