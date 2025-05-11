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
fastmcp run main.py:mcp --transport sse --host 127.0.0.1 --port 8000
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
  -p 8000:8000 \
  weather-mcp-server
```

## Using the Weather Tool

### Example Clients

The project includes example client scripts that demonstrate how to use the weather MCP server:

#### Standard Client (stdio mode)

```bash
# Make the script executable if needed
chmod +x example_client.py

# Get current weather for London
./example_client.py --city London,uk

# Get tomorrow's weather for Tokyo
./example_client.py --city Tokyo --days 1
```

#### SSE Client

```bash
# Make the script executable if needed
chmod +x example_client_streamable.py

# Connect using the SSE transport
./example_client_streamable.py --transport sse --host 127.0.0.1 --port 8000 --city Paris

# Get tomorrow's weather for Tokyo
./example_client_streamable.py --transport sse --host 127.0.0.1 --port 8000 --city Tokyo --days 1
```

### Testing the Server

The project includes a test script that verifies the server is working correctly:

```bash
# Make the script executable if needed
chmod +x test_server.py

# Test with default settings (stdio mode)
./test_server.py

# Test with a specific city
./test_server.py --city Tokyo

# Test against an SSE server
./test_server.py --transport sse --host 127.0.0.1 --port 8000
```

The test script runs three tests:
1. Getting current weather
2. Getting tomorrow's forecast
3. Getting a forecast for a future day (up to 15 days ahead)

If all tests pass, the script exits with code 0. If any test fails, it exits with code 1.

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

1. **stdio**: Standard input/output mode (default, good for CLI usage)
2. **sse**: HTTP server mode with streaming support (recommended for web clients)
3. **streamable-http**: Deprecated alias for sse mode (for backward compatibility)

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
   const eventSource = new EventSource('http://localhost:8000/stream');
   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data);
     console.log('Received:', data);
   };
   ```

2. Send MCP requests:
   ```javascript
   // Browser example
   const clientId = '...'; // Get this from the streaming connection headers
   fetch('http://localhost:8000/mcp', {
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
