#!/usr/bin/env python3
"""
Simple test script to verify authentication with the MCP server.
"""

import argparse
import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Add parent directory to path to import auth module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weather_mcp.utils.auth import generate_token

async def test_auth():
    parser = argparse.ArgumentParser(description="Test MCP Server Authentication")
    parser.add_argument("--url", default="http://localhost:3399", help="MCP server base URL")
    parser.add_argument("--token", help="Bearer token for authentication")
    parser.add_argument("--secret", help="Secret key to generate a token")
    parser.add_argument("--no-auth", action="store_true", help="Test without authentication")
    args = parser.parse_args()
    
    # Handle authentication
    headers = {}
    if args.token:
        # Use provided token
        headers["Authorization"] = f"Bearer {args.token}"
        print(f"Using provided token: {args.token}")
    elif args.secret:
        # Generate a token using the provided secret
        token = generate_token(args.secret)
        headers["Authorization"] = f"Bearer {token}"
        print(f"Generated token: {token}")
    elif not args.no_auth:
        print("No token or secret provided. Use --no-auth to test without authentication.")
        return
    
    # Test endpoints
    base_url = args.url
    endpoints = [
        "/mcp/info",  # Health check endpoint (should work without auth)
        "/sse",       # SSE endpoint (should require auth if enabled)
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\nTesting endpoint: {url}")
            
            # First try without auth
            if not args.no_auth:
                print("  Testing without auth...")
                try:
                    async with session.get(url) as response:
                        print(f"  Response status: {response.status}")
                        if response.status == 200:
                            content_type = response.headers.get('Content-Type', '')
                            if 'json' in content_type:
                                data = await response.json()
                                print(f"  Response {json.dumps(data, indent=2)}")
                            else:
                                text = await response.text()
                                print(f"  Response text: {text[:100]}...")
                        else:
                            text = await response.text()
                            print(f"  Response text: {text}")
                except Exception as e:
                    print(f"  Error: {e}")
            
            # Then try with auth
            if headers:
                print("  Testing with auth...")
                try:
                    async with session.get(url, headers=headers) as response:
                        print(f"  Response status: {response.status}")
                        if response.status == 200:
                            content_type = response.headers.get('Content-Type', '')
                            if 'json' in content_type:
                                data = await response.json()
                                print(f"  Response {json.dumps(data, indent=2)}")
                            else:
                                text = await response.text()
                                print(f"  Response text: {text[:100]}...")
                        else:
                            text = await response.text()
                            print(f"  Response text: {text}")
                except Exception as e:
                    print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
