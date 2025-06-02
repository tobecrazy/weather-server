import asyncio
import sys
import os

# Adjust path to import from parent directory if necessary
# This is common when running a script directly from a subdirectory of a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from mcp_client.weather_mcp_client import WeatherMCPClient, MCPClientError
except ImportError:
    print("Failed to import WeatherMCPClient. Ensure the client module is in the mcp_client directory and sys.path is correct.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)


async def main():
    # Default base URL for the MCP server
    # You can override this with an environment variable if needed
    mcp_base_url = os.getenv("MCP_SERVER_URL", "http://localhost:3399/sse")
    
    print(f"Attempting to connect to MCP server at: {mcp_base_url}")
    # It's good practice to ensure the URL ends with a slash for base_url in httpx
    if not mcp_base_url.endswith('/'):
        mcp_base_url += '/'
        
    client = WeatherMCPClient(base_url=mcp_base_url)

    try:
        print("\n--- Testing health_check() ---")
        try:
            health_status = await client.health_check()
            print("Health check successful.")
            print(f"Response: {health_status}")
        except MCPClientError as e:
            print(f"Error during health_check: {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")

        print("\n--- Testing get_404_page() ---")
        try:
            html_content = await client.get_404_page()
            print("get_404_page successful.")
            print(f"Response (first 100 chars): {html_content[:100]}...")
            # print(f"Full HTML content length: {len(html_content)}") # Uncomment to see full length
        except MCPClientError as e:
            print(f"Error during get_404_page: {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")

        print("\n--- Testing get_weather() (default) ---")
        try:
            weather_default = await client.get_weather()
            print("get_weather (default) successful.")
            print(f"Response: {weather_default}")
        except MCPClientError as e:
            print(f"Error during get_weather (default): {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")

        print("\n--- Testing get_weather(city=\"London,uk\", days=1) ---")
        try:
            weather_london = await client.get_weather(city="London,uk", days=1)
            print("get_weather (London,uk, 1 day) successful.")
            print(f"Response: {weather_london}")
        except MCPClientError as e:
            print(f"Error during get_weather (London,uk, 1 day): {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")
        
        print("\n--- Testing get_weather(city=\"NonExistentCity\", days=1) ---")
        try:
            weather_non_existent = await client.get_weather(city="NonExistentCityHopefully", days=1)
            print("get_weather (NonExistentCityHopefully, 1 day) - this might succeed or fail depending on server handling.")
            print(f"Response: {weather_non_existent}")
        except MCPClientError as e:
            print(f"Error during get_weather (NonExistentCityHopefully, 1 day): {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")

        print("\n--- Testing get_health_resource() ---")
        try:
            health_resource = await client.get_health_resource()
            print("get_health_resource successful.")
            print(f"Response: {health_resource}")
        except MCPClientError as e:
            print(f"Error during get_health_resource: {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")

    except MCPClientError as e:
        print(f"\nA critical MCPClientError occurred: {e}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n--- Closing client connection ---")
        await client.close()
        print("Client connection closed.")

if __name__ == "__main__":
    print("Starting WeatherMCPClient test script...")
    asyncio.run(main())
    print("\nTest script finished.")
