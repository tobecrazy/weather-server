#!/usr/bin/env python3
"""
Test script for the Weather MCP Server resources.
This script tests the server's resources functionality.
"""

import sys
import argparse
import json
import requests

def test_resources_list(host, port):
    """Test listing all resources"""
    url = f"http://{host}:{port}/resources/list"
    print(f"Testing resources list at {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        resources = response.json()
        
        print("\n✅ Success! Available resources:")
        for resource in resources:
            print(f"- {resource}")
        return True, resources
    except Exception as e:
        print(f"\n❌ Error listing resources: {str(e)}")
        return False, None

def test_resource(host, port, resource_name):
    """Test getting a specific resource"""
    url = f"http://{host}:{port}/resources/{resource_name}"
    print(f"Testing resource '{resource_name}' at {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ Success! Resource '{resource_name}':")
        print(json.dumps(data, indent=2))
        return True
    except Exception as e:
        print(f"\n❌ Error getting resource '{resource_name}': {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test the Weather MCP Server resources')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Host for SSE server')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port for SSE server')
    
    args = parser.parse_args()
    
    # Run tests
    success = True
    
    # Test 1: List all resources
    list_success, resources = test_resources_list(args.host, args.port)
    if not list_success:
        success = False
    
    if resources:
        print("\n" + "-" * 40 + "\n")
        
        # Test 2: Get each resource
        for resource in resources:
            if not test_resource(args.host, args.port, resource):
                success = False
            print("\n" + "-" * 40 + "\n")
    
    # Summary
    print("\n" + "=" * 40)
    if success:
        print("✅ All resource tests passed successfully!")
    else:
        print("❌ Some resource tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
