# Weather MCP Server

This project implements a local MCP (Model Context Protocol) server using FastMCP that provides weather information via the OpenWeatherMap API.

## Features

- Get current weather for any city
- Get weather forecasts for up to 15 days in the future
- Includes minimum and maximum temperature data for each forecast
- Configurable default city and API key
- Support for both stdio and HTTP transport modes with streaming support
- Comprehensive error handling and logging

## Project Structure

```
weather_mcp/
├── main.py                 # Main server entrypoint using FastMCP
├── plugins/
│   └── weather.py          # Weather tool (queries OpenWeatherMap API)
├── config.yaml             # Configuration (API key, mode, default city)
├── requirements.txt        # Python dependencies
└── weather.log             # Log file (created at runtime)
```

## Setup

1. **Get an API Key**: Sign up at [OpenWeatherMap](https://home.openweathermap.org/users/sign_up) and get your API key.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   This will install all required dependencies including:
   - FastMCP (≥2.2.6)
   - FastAPI (0.115.12)
   - Starlette (≥0.34.0)
   - Uvicorn (≥0.27.0)
   - Other utility libraries

3. **Configure the Server**:
   
   You can configure the server using either a YAML file or environment variables:

   ### Option 1: Using config.yaml
   
   Edit `config.yaml` and add your OpenWeatherMap API key:
   ```yaml
   apikey: YOUR_OPENWEATHERMAP_API_KEY
   mode: stdio  # or "sse" for HTTP streaming mode
   default_city: Beijing,cn
   ```

   ### Option 2: Using Environment Variables
   
   Copy `.env.example` to `.env` and edit it:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred text editor
   ```
   
   Or set environment variables directly:
   ```bash
   export OPENWEATHERMAP_API_KEY=your_api_key_here
   export MCP_TRANSPORT_MODE=stdio
   export DEFAULT_CITY=London,uk
   ```

## Authorization

When running the server in `sse` or `streamable-http` (default HTTP) transport modes, requests to MCP tools are protected by Bearer Token authentication. This enhances security for network-accessible deployments.

### Setting the Secret Token

The server expects a shared secret token for validating requests. This token must be provided via the `MCP_SHARED_SECRET` environment variable.

You can generate a cryptographically strong, URL-safe token using the provided utility:
```bash
python -m weather_mcp.token_utils
```
This command will output a generated token (e.g., `Generated Token: AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-ABc`) which you can then use to set the environment variable.

Example of setting the variable after generating a token:
```bash
export MCP_SHARED_SECRET="use_the_token_generated_by_the_script_here"
```
If this variable is not set, or if it's set to the default placeholder `your_secret_token`, the server will log a warning. **It is crucial to set a strong, unique secret token for any production or publicly accessible environments.**

### Making Authorized Requests

Clients must include this token in the `Authorization` header as a Bearer token.

Here's an example using `curl` to call the `weather.get_weather` tool:

```bash
curl -X POST http://localhost:3399/mcp \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your-very-secure-and-random-token" \
     -d '{
       "tool": "weather.get_weather",
       "args": {
         "city": "Paris"
       }
     }'
```

Replace `your-very-secure-and-random-token` with the actual token set in `MCP_SHARED_SECRET`.

### Exempted Paths

The following paths are exempt from authentication:

-   `/mcp/health_check`: The health check endpoint.
-   `/mcp/info`: The server information endpoint.
-   FastAPI documentation paths (e.g., `/docs`, `/openapi.json`, `/redoc`) if enabled and accessed.

The `stdio` transport mode does not use this authentication mechanism.

## Running the Server

### Using the provided script:

The project includes a convenient shell script to run the server:

```bash
# Make the script executable if needed
chmod +x run_server.sh

# Run in stdio mode (default)
./run_server.sh

# Run in HTTP streaming mode
./run_server.sh -m sse

# Run in HTTP streaming mode with custom port
./run_server.sh -m sse -p 8080

# Show help
./run_server.sh --help
```

### Using Python directly:

```bash
python main.py
```

### Using FastMCP CLI:

If you have the FastMCP CLI installed globally:

For stdio mode:
```bash
# If fastmcp is installed as a command-line tool
fastmcp run main.py:mcp
```

For HTTP streaming mode:
```bash
# If fastmcp is installed as a command-line tool
fastmcp run main.py:mcp --transport sse --host 127.0.0.1 --port 3399
```

Alternatively, you can set `mode: sse` in `config.yaml` and run with Python directly.

### Using Docker:

The project includes Docker support for easy deployment:

#### Using Docker Compose (recommended):

```bash
# Start the server in HTTP streaming mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

**Health Check:**
The Docker configurations (`Dockerfile` and `docker-compose.yml`) define a health check to monitor the server's status. This health check now utilizes a GET request to the `/mcp/info` endpoint (accessible at `http://localhost:3399/mcp/info` if the container's port 3399 is mapped to the host's port 3399). This endpoint returns a JSON response confirming the service is operational.

#### Using Docker directly:

```bash
# Build the Docker image
docker build -t weather-mcp-server .

# Run in stdio mode (interactive)
docker run -it --rm \
  -e OPENWEATHERMAP_API_KEY=your_api_key_here \
  weather-mcp-server

# Run in HTTP streaming mode
docker run -d --name weather-mcp-server \
  -e OPENWEATHERMAP_API_KEY=your_api_key_here \
  -e MCP_TRANSPORT_MODE=sse \
  -e HTTP_HOST=0.0.0.0 \
  -e SSE_HOST=0.0.0.0 \
  -p 3399:3399 \
  weather-mcp-server
```

## Using the Weather Tool

### API Details

#### Tools

The server provides a single tool: `weather.get_weather`

### Parameters:

- `city` (optional): City name, optionally with country code (e.g., "London,uk"). If not provided, uses the default city from config.
- `days` (optional): Day offset (0=today/current, 1=tomorrow, ..., 15=fifteen days from now). Default is 0 (current weather).

### Example Request:

```json
{
  "tool": "weather.get_weather",
  "args": {
    "city": "Tokyo",
    "days": 1
  }
}
```

### Example Response:

```json
{
  "city": "Tokyo",
  "date": "2025-05-02",
  "temperature_C": 18.5,
  "min_temperature_C": 15.2,
  "max_temperature_C": 22.1,
  "weather": "clear sky"
}
```

#### Note on Resources

This implementation focuses on the core weather tool functionality. Resources have been temporarily disabled due to compatibility issues with the current version of FastMCP.

## Error Handling

The server includes comprehensive error handling for:
- Invalid parameters
- API connection issues
- Missing or invalid API key
- Unexpected API responses

Errors are logged to `weather.log` and returned as error responses to the client.

## Notes on OpenWeatherMap API

- The free tier of OpenWeatherMap includes current weather and 5-day/3-hour forecasts.
- This implementation attempts to use the daily forecast API (`/forecast/daily`) which supports up to 16 days of forecasts but falls back to the 5-day/3-hour forecast API if needed.
- For forecasts beyond 5 days, a paid OpenWeatherMap subscription may be required for the daily forecast API.
- The implementation includes min/max temperature data for all forecasts.
- For paid plans, the One Call API would provide more comprehensive data.

## FastAPI Compatibility

This project has been updated to work with FastAPI 0.115.12. The HTTP streaming implementation has been completely redesigned to use Starlette and uvicorn directly:

- The HTTP streaming mode now uses a direct Starlette application with specific routes for streaming endpoints
- The implementation uses uvicorn to run the Starlette application
- This approach ensures compatibility with FastAPI 0.115.12 and provides a more robust HTTP streaming implementation

### Transport Mode Updates

The server now supports the following transport modes:

1. **stdio**: Standard input/output mode (good for CLI usage)
2. **streamable-http**: HTTP server mode with streaming support (default and recommended for web clients)
3. **sse**: Legacy HTTP streaming mode (for backward compatibility)

### HTTP Streaming Architecture

The HTTP streaming transport mode uses the following components:

1. **Streaming Endpoints**:
   - `/stream`: Primary endpoint for establishing streaming connections (recommended)
   - `/sse`: Legacy endpoint maintained for backward compatibility (deprecated)
   - Clients connect to these endpoints to receive real-time updates
   - Each client receives a unique client ID for message routing

2. **MCP Request Endpoint** (`/mcp`): Handles MCP tool requests
   - Clients send POST requests to this endpoint to execute MCP tools
   - Responses are sent back via the streaming connection

### Using the HTTP Streaming Mode

To connect to the HTTP streaming server:

1. Establish a streaming connection:
   ```javascript
   // Browser example
   const eventSource = new EventSource('http://localhost:3399/stream');
   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data);
     console.log('Received:', data);
   };
   ```

2. Send MCP requests:
   ```javascript
   // Browser example
   const clientId = '...'; // Get this from the streaming connection headers
   fetch('http://localhost:3399/mcp', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'X-Client-ID': clientId
     },
     body: JSON.stringify({
       tool: 'weather.get_weather',
       args: {
         city: 'London,uk'
       },
       request_id: '12345' // Optional, will be generated if not provided
     })
   });
   ```

If you encounter any issues with the HTTP streaming mode, please check that you have installed all the required dependencies:
```bash
pip install -r requirements.txt
```
