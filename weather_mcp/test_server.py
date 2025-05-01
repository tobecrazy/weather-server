#!/usr/bin/env python3
"""
Test script for the Weather MCP Server.
This script tests the server by making a request and verifying the response.
"""

import sys
import argparse
import json
from fastmcp import FastMCPClient

def test_current_weather(client, city=None):
    """Test getting current weather"""
    print(f"Testing current weather for {city or 'default city'}...")
    try:
        args = {"city": city} if city else {}
        result = client.call("weather.get_weather", **args)
        print("\n✅ Success! Current weather:")
        print(f"City: {result['city']}")
        print(f"Date: {result['date']}")
        print(f"Temperature: {result['temperature_C']}°C")
        print(f"Weather: {result['weather']}")
        return True
    except Exception as e:
        print(f"\n❌ Error getting current weather: {str(e)}")
        return False

def test_forecast(client, city=None, days=1):
    """Test getting weather forecast"""
    print(f"Testing {days}-day forecast for {city or 'default city'}...")
    try:
        args = {"days": days}
        if city:
            args["city"] = city
        result = client.call("weather.get_weather", **args)
        print(f"\n✅ Success! {days}-day forecast:")
        print(f"City: {result['city']}")
        print(f"Date: {result['date']}")
        print(f"Temperature: {result['temperature_C']}°C")
        print(f"Weather: {result['weather']}")
        return True
    except Exception as e:
        print(f"\n❌ Error getting forecast: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test the Weather MCP Server')
    parser.add_argument('--city', type=str, help='City to test with (e.g., "London,uk")')
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
        print(f"Connecting to SSE server at {args.host}:{args.port}...")
        client = FastMCPClient(
            transport="sse",
            host=args.host,
            port=args.port
        )
    else:
        print("Using stdio transport. Make sure the server is running and connected to stdin/stdout.")
        client = FastMCPClient(transport="stdio")
    
    # Run tests
    success = True
    
    # Test 1: Current weather
    if not test_current_weather(client, args.city):
        success = False
    
    print("\n" + "-" * 40 + "\n")
    
    # Test 2: Tomorrow's forecast
    if not test_forecast(client, args.city, 1):
        success = False
    
    print("\n" + "-" * 40 + "\n")
    
    # Test 3: 3-day forecast
    if not test_forecast(client, args.city, 3):
        success = False
    
    # Summary
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
