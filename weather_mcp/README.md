# Weather MCP Server

This project implements a local MCP (Model Context Protocol) server using FastMCP that provides weather information via the OpenWeatherMap API.

## Features

- Get current weather for any city
- Get weather forecasts for up to 15 days in the future
- Includes minimum and maximum temperature data for each forecast
- Configurable default city and API key
- Support for both stdio and HTTP transport modes with streaming support
- OAuth 2.0 Bearer Token authentication for HTTP modes
- Comprehensive error handling and logging

## Project Structure

```
weather_mcp/
├── main.py                 # Main server entrypoint using FastMCP
├── auth_proxy.py           # Authentication proxy for the MCP server
├── plugins/
│   └── weather.py          # Weather tool (queries OpenWeatherMap API)
├── utils/
│   ├── auth.py             # Authentication utilities
│   └── generate_token.py   # Token generation utility
├── config.yaml             # Configuration (API key, mode, default city)
├── requirements.txt        # Python dependencies
├── supervisord.conf        # Supervisor configuration for Docker
├── run_server.sh           # Script to run the server
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
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
   
   # Authentication settings (optional)
   auth:
     enabled: true
     secret_key: your_secret_key_here
     token_expiry: 86400  # 24 hours in seconds
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
   
   # Authentication settings (optional)
   export AUTH_ENABLED=true
   export AUTH_SECRET_KEY=your_secret_key_here
   export AUTH_TOKEN_EXPIRY=86400
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

# Run with authentication enabled
./run_server.sh -m sse -a

# Run with authentication and generate a token
./run_server.sh -m sse -a -g

# Run with authentication and a specific secret key
./run_server.sh -m sse -a -s your_secret_key_here

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
The Docker configurations (`Dockerfile` and `docker-compose.yml`) define a health check to monitor the server's status. This health check utilizes a GET request to the `/mcp/info` endpoint through the auth proxy (accessible at `http://localhost:3397/mcp/info` if the container's port 3397 is mapped to the host's port 3397). This endpoint returns a JSON response confirming the service is operational.

**Ports:**
- Port 3397: Auth proxy (exposed to clients)
- Port 3399: MCP server (internal, not directly accessible)

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
  
# Run with authentication enabled
docker run -d --name weather-mcp-server \
  -e OPENWEATHERMAP_API_KEY=your_api_key_here \
  -e MCP_TRANSPORT_MODE=sse \
  -e HTTP_HOST=0.0.0.0 \
  -e SSE_HOST=0.0.0.0 \
  -e AUTH_ENABLED=true \
  -e AUTH_SECRET_KEY=your_secret_key_here \
  -e AUTH_PROXY_HOST=0.0.0.0 \
  -e AUTH_PROXY_PORT=3397 \
  -p 3397:3397 \
  -p 3399:3399 \
  weather-mcp-server
```

Note: When running with Docker, both the MCP server and auth proxy are started automatically using supervisor.

## Authentication

The server supports OAuth 2.0 Bearer Token authentication for HTTP streaming modes (SSE and streamable-http). This provides secure access control for your MCP server.

### Authentication Configuration

Authentication can be configured in several ways:

1. **Using config.yaml**:
   ```yaml
   auth:
     enabled: true                   # Enable or disable authentication
     secret_key: your_secret_key_here # Secret key for signing tokens
     token_expiry: 86400             # Token expiration time in seconds (24 hours)
   ```

2. **Using environment variables**:
   ```bash
   AUTH_ENABLED=true
   AUTH_SECRET_KEY=your_secret_key_here
   AUTH_TOKEN_EXPIRY=86400
   ```

3. **Using command-line options** (with run_server.sh):
   ```bash
   ./run_server.sh -m sse -a -s your_secret_key_here
   ```

### Token Generation

The project includes a token generation utility in `utils/generate_token.py`:

```bash
# Basic usage
python utils/generate_token.py --secret your_secret_key_here

# With user ID
python utils/generate_token.py --secret your_secret_key_here --user "user123"

# With custom expiration (in seconds)
python utils/generate_token.py --secret your_secret_key_here --expiry 3600

# With additional data (as JSON)
python utils/generate_token.py --secret your_secret_key_here --data '{"role":"admin"}'
```

You can also generate a token when starting the server with the `-g` flag:

```bash
./run_server.sh -m sse -a -g
```

### Token Format

The Bearer Token follows a simple format:

```
base64url(payload).base64url(signature)
```

Where:
- `payload` is a JSON object containing token metadata (issue time, expiration, etc.)
- `signature` is an HMAC-SHA256 signature of the payload using the secret key

### Client Authentication

Clients must include the Bearer Token in the Authorization header:

```
Authorization: Bearer your_token_here
```

Example using the provided client:

```bash
python mcp_client/weather_mcp_client.py --token your_token_here
```

Or generate a token on the fly:

```bash
python mcp_client/weather_mcp_client.py --secret your_secret_key_here
```

### Security Considerations

- The secret key should be kept secure and not shared publicly
- For production use, use a strong random key (at least 32 characters)
- Token expiration limits the window of opportunity for token misuse
- Authentication is enforced for all endpoints except the health check endpoint (/mcp/info)

## Authentication Proxy

The server includes an authentication proxy (`auth_proxy.py`) that sits in front of the MCP server and handles authentication. This allows you to expose the MCP server to external clients while ensuring all requests are properly authenticated.

### Authentication Proxy Features

- Handles authentication for all requests to the MCP server
- Forwards authenticated requests to the MCP server
- Exposes a separate port (3397) for client connections
- Uses the same authentication mechanism as the MCP server
- Allows the MCP server to focus on its core functionality

### Running with the Authentication Proxy

You can run the server with the authentication proxy using the provided script:

```bash
# Run with auth proxy enabled
./run_server.sh --proxy

# Run with auth proxy on a custom port
./run_server.sh --proxy --proxy-port 8080

# Run with auth proxy and authentication enabled
./run_server.sh --proxy -a -s your_secret_key_here
```

### Using Docker with Authentication Proxy

When using Docker, the authentication proxy is automatically enabled:

```bash
# Start the server with Docker Compose
docker-compose up -d
```

The Docker setup runs both the MCP server and the authentication proxy, with the proxy exposed on port 3397 and the MCP server running internally on port 3399.

### Client Configuration

When using the authentication proxy, clients should connect to the proxy port (3397 by default) instead of the MCP server port (3399):

```bash
# Using the provided client with the auth proxy
python mcp_client/weather_mcp_client.py --host localhost --port 3397 --token your_token_here
```

Or in a browser:
```javascript
const eventSource = new EventSource('http://localhost:3397/stream');
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

#### Direct Connection (Port 3399)

When connecting directly to the MCP server (without the auth proxy):

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
       'X-Client-ID': clientId,
       'Authorization': 'Bearer your_token_here' // If authentication is enabled
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

#### Through Auth Proxy (Port 3397)

When connecting through the authentication proxy (recommended):

1. Establish a streaming connection:
   ```javascript
   // Browser example
   const eventSource = new EventSource('http://localhost:3397/stream');
   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data);
     console.log('Received:', data);
   };
   ```

2. Send MCP requests:
   ```javascript
   // Browser example
   const clientId = '...'; // Get this from the streaming connection headers
   fetch('http://localhost:3397/mcp', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'X-Client-ID': clientId,
       'Authorization': 'Bearer your_token_here' // Required when using auth proxy
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
