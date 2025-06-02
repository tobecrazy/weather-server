import httpx
import json
from typing import Optional, Dict, Any

class MCPClientError(Exception):
    """Custom exception for MCP client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class WeatherMCPClient:
    def __init__(self, base_url: str = "http://localhost:3399/sse"):
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
        """Helper method to make requests to the MCP server."""
        try:
            response = await self._client.request(method, endpoint, params=params, json=data)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            # It seems MCP sometimes returns plain text for errors even with 200 OK for some tools
            # And sometimes returns JSON, sometimes plain text for actual tool output
            try:
                return response.json()
            except json.JSONDecodeError:
                # If JSON decoding fails, return the plain text content
                # This is important for tools that might return non-JSON data
                # or for error messages that are not in JSON format.
                text_response = response.text
                # Attempt to parse known error structures if any, otherwise return raw text
                # For now, we'll assume if it's not JSON, it's either a direct string result or an error string
                if "error" in text_response.lower() and response.status_code >= 400: # Basic check
                    raise MCPClientError(f"Server returned non-JSON error: {text_response}", response.status_code)
                return text_response
        except httpx.HTTPStatusError as e:
            # Attempt to get more detailed error from response
            try:
                error_details = e.response.json()
                error_message = error_details.get("detail", e.response.text)
            except json.JSONDecodeError:
                error_message = e.response.text
            raise MCPClientError(f"HTTP error occurred: {error_message}", status_code=e.response.status_code) from e
        except httpx.RequestError as e:
            # For network errors, timeouts, etc.
            raise MCPClientError(f"Request failed: {str(e)}") from e

    async def close(self):
        """Closes the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> Any:
        """Calls the /health_check tool on the main server."""
        return await self._request("GET", "health_check")

    async def get_404_page(self) -> str:
        """Calls the /get_404_page tool on the main server. Expects HTML content."""
        # This tool is expected to return HTML, so we directly access .text
        try:
            response = await self._client.get("get_404_page")
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise MCPClientError(f"HTTP error occurred while fetching 404 page: {e.response.text}", status_code=e.response.status_code) from e
        except httpx.RequestError as e:
            raise MCPClientError(f"Request failed while fetching 404 page: {str(e)}") from e

    async def get_weather(self, city: Optional[str] = None, days: int = 0) -> Any:
        """Calls the /weather/get_weather tool."""
        params = {}
        if city:
            params["city"] = city
        if days > 0:
            params["days"] = days
        return await self._request("GET", "weather/get_weather", params=params)

    async def get_health_resource(self) -> Any:
        """Fetches the content of the resource at /mcp/info."""
        # Resource URLs are typically relative to the base_url of the server itself, not the /sse endpoint part
        # However, the problem description implies it's a "tool" call via the MCP proxy.
        # Let's assume it's a standard tool call for "/mcp/info"
        # If it were a direct resource fetch, it would be `self.base_url.replace('/sse', '') + "resource/mcp/info"`
        # Given the context, it's more likely a tool that serves this resource.
        # The original problem statement mentions "resource://mcp/info", fastmcp translates this to /mcp/info tool.
        return await self._request("GET", "mcp/info")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

if __name__ == '__main__':
    import asyncio

    async def main():
        # Example usage (requires a running MCP server)
        # Replace with your actual MCP server URL if different
        client = WeatherMCPClient(base_url="http://localhost:3399/sse")
        try:
            print("--- Health Check ---")
            health = await client.health_check()
            print(f"Health check response: {health}\n")

            print("--- Get Weather (Default) ---")
            weather_default = await client.get_weather()
            print(f"Default weather response: {weather_default}\n")

            print("--- Get Weather (London, 3 days) ---")
            weather_london = await client.get_weather(city="London", days=3)
            print(f"Weather for London (3 days): {weather_london}\n")
            
            print("--- Get Weather (Paris, 1 day) ---")
            weather_paris = await client.get_weather(city="Paris", days=1)
            print(f"Weather for Paris (1 day): {weather_paris}\n")

            print("--- Get MCP Info Resource ---")
            mcp_info = await client.get_health_resource()
            print(f"MCP Info response: {mcp_info}\n")
            
            # Note: get_404_page might return a large HTML string
            # print("--- Get 404 Page ---")
            # page_404 = await client.get_404_page()
            # print(f"404 Page content length: {len(page_404)}\n")


        except MCPClientError as e:
            print(f"An error occurred: {e}")
            if e.status_code:
                print(f"Status code: {e.status_code}")
        finally:
            await client.close()

    asyncio.run(main())
