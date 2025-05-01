# Weather MCP Server

This project implements a local MCP (Model Context Protocol) server using FastMCP that provides weather information via the OpenWeatherMap API.

## Features

- Get current weather for any city
- Get weather forecasts for up to 3 days in the future
- Configurable default city and API key
- Support for both stdio and SSE transport modes
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

3. **Configure the Server**:
   
   You can configure the server using either a YAML file or environment variables:

   ### Option 1: Using config.yaml
   
   Edit `config.yaml` and add your OpenWeatherMap API key:
   ```yaml
   apikey: YOUR_OPENWEATHERMAP_API_KEY
   mode: stdio  # or "sse" for HTTP mode
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

# Run in SSE mode
./run_server.sh -m sse

# Run in SSE mode with custom port
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

For SSE (HTTP) mode:
```bash
# If fastmcp is installed as a command-line tool
fastmcp run main.py:mcp --transport sse --host 127.0.0.1 --port 8000
```

Alternatively, you can set `mode: sse` in `config.yaml` and run with Python directly.

### Using Docker:

The project includes Docker support for easy deployment:

#### Using Docker Compose (recommended):

```bash
# Start the server in SSE mode
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

# Run in SSE mode
docker run -d --name weather-mcp-server \
  -e OPENWEATHERMAP_API_KEY=your_api_key_here \
  -e MCP_TRANSPORT_MODE=sse \
  -e SSE_HOST=0.0.0.0 \
  -p 8000:8000 \
  weather-mcp-server
```

## Using the Weather Tool

### Example Client

The project includes an example client script that demonstrates how to use the weather MCP server:

```bash
# Make the script executable if needed
chmod +x example_client.py

# Get current weather for London
./example_client.py --city London,uk

# Get tomorrow's weather for Tokyo
./example_client.py --city Tokyo --days 1

# Connect to an SSE server
./example_client.py --transport sse --host 127.0.0.1 --port 8000 --city Paris
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
3. Getting a 3-day forecast

If all tests pass, the script exits with code 0. If any test fails, it exits with code 1.

### API Details

#### Tools

The server provides a single tool: `weather.get_weather`

### Parameters:

- `city` (optional): City name, optionally with country code (e.g., "London,uk"). If not provided, uses the default city from config.
- `days` (optional): Day offset (0=today/current, 1=tomorrow, 2=day after tomorrow, 3=three days from now). Default is 0 (current weather).

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
- This implementation attempts to use the daily forecast API (`/forecast/daily`) but falls back to the 5-day/3-hour forecast API if needed.
- For paid plans, the One Call API would provide more comprehensive data.
