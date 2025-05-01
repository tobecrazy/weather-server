#!/usr/bin/env python3
"""
Example client for the Weather MCP Server.
This demonstrates how to connect to and use the weather MCP server.
"""

import json
import sys
import argparse
from fastmcp import FastMCPClient

def main():
    parser = argparse.ArgumentParser(description='Weather MCP Client Example')
    parser.add_argument('--city', type=str, help='City name (e.g., "London,uk")')
    parser.add_argument('--days', type=int, default=0, choices=[0, 1, 2, 3],
                        help='Day offset (0=today, 1=tomorrow, etc.)')
    parser.add_argument('--transport', type=str, default='stdio',
                        choices=['stdio', 'sse'],
                        help='Transport mode (stdio or sse)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Host for SSE mode')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port for SSE mode')
    
    args = parser.parse_args()
    
    # Create client based on transport mode
    if args.transport == 'sse':
        client = FastMCPClient(
            transport="sse",
            host=args.host,
            port=args.port
        )
    else:
        # For stdio mode, we assume the server is running as a subprocess
        # This is just an example - in a real application, you'd need to
        # handle the subprocess management
        print("For stdio mode, you need to connect to a running server.")
        print("Example: pipe this script to the server process.")
        client = FastMCPClient(transport="stdio")
    
    # Prepare the request
    request_args = {}
    if args.city:
        request_args["city"] = args.city
    if args.days is not None:
        request_args["days"] = args.days
    
    try:
        # Call the weather tool
        result = client.call("weather.get_weather", **request_args)
        
        # Pretty print the result
        print("\nWeather Information:")
        print(f"City: {result['city']}")
        print(f"Date: {result['date']}")
        print(f"Temperature: {result['temperature_C']}°C")
        print(f"Weather: {result['weather']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
