# 🌤 Weather MCP Server

A Model Context Protocol (MCP) server that provides weather forecast data using the OpenWeatherMap API. This server can be used to fetch current weather and multi-day forecasts for cities worldwide.

This project implements a local Node.js MCP server that connects to OpenWeatherMap API to retrieve weather data for any city (including international cities) for a specified number of days. The implementation includes a custom MCP server that doesn't require external SDK dependencies.

The project also includes a Python-based agent using Google's Agent Development Kit (ADK) that can answer questions about weather and time in specific cities.

## ✨ Features

- 🌍 Fetch current weather data for any city worldwide
- 📅 Get multi-day forecasts (up to 5 days)
- 🌐 Support for international cities with country code specification (e.g., "Paris,fr")
- 🔄 Configurable communication modes:
  - `stdio` mode for command-line interaction
  - `sse` mode for web-based interaction
- 🔌 Easy integration with MCP-compatible clients
- ⚙️ Flexible configuration via environment variables or JSON file
- 🤖 AI-powered agent using Google ADK for natural language weather and time queries

## 🛠 Prerequisites

- Node.js 18 or higher
- Python 3.9 or higher (for Google ADK integration)
- OpenWeatherMap API key ([Get one here](https://openweathermap.org/api))

## 📁 Project Structure

```
weather-server/
├── index.js                # Main entry point
├── config.js               # Configuration loader
├── weather.js              # Weather data handling
├── transport/
│   ├── stdio.js            # Stdio transport implementation
│   └── sse.js              # SSE transport implementation
├── multi_tool_agent/       # Google ADK integration
│   ├── __init__.py         # Python package initialization
│   └── agent.py            # Google ADK agent implementation
├── package.json            # Node.js project dependencies
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
├── .env.example            # Environment variables example
├── config.json.example     # JSON configuration example
└── .gitignore              # Git ignore rules
```

## 📥 Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd weather-server
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Install Python dependencies (for Google ADK):
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your OpenWeatherMap API key:
   - Create a `.env` file in the project root (copy from `.env.example`):
     ```
     OPENWEATHERMAP_API_KEY=your_api_key_here
     ```
   - Or create a `config.json` file (copy from `config.json.example`):
     ```json
     {
       "apiKey": "your_api_key_here",
       "mode": "stdio"
     }
     ```

## ⚙️ Configuration Options

The server can be configured using environment variables or a `config.json` file:

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| API Key | `OPENWEATHERMAP_API_KEY` | (none) | Your OpenWeatherMap API key |
| Mode | `MCP_MODE` | `stdio` | Communication mode (`stdio` or `sse`) |
| Port | `PORT` | `3031` | Port for SSE server (only used in SSE mode) |
| Host | `HOST` | `localhost` | Host for SSE server (only used in SSE mode) |

Configuration priority:
1. Environment variables
2. `config.json` file
3. Default values

### Port Auto-Retry

When running in SSE mode, if the specified port is already in use, the server will automatically try the next 4 consecutive ports. For example, if port 3031 is in use, it will try ports 3032, 3033, 3034, and 3035. If all ports are in use, it will display an error message with suggestions.

The port auto-retry mechanism is implemented in the `transport/sse.js` file. When the server encounters a port that's already in use, it will:

1. Log a message indicating that it's trying the next port
2. Update the port number to the next available port in the retry list
3. Attempt to start the server again with the new port
4. If all ports are in use, it will display a helpful error message with suggestions

### Troubleshooting Port Conflicts

If you encounter port conflicts when running in SSE mode, you can use the included `showPort.sh` script to identify and manage processes using the ports:

```bash
# Make the script executable (if not already)
chmod +x showPort.sh

# Check which processes are using ports 3031-3035
./showPort.sh 3031 3032 3033 3034 3035
```

The script will show you which processes are using these ports and provide commands to terminate them if needed.

## 🚀 Usage

### Starting the Server

```bash
# Using npm (if available)
# Start with stdio mode (default)
npm start

# Start with SSE mode
MCP_MODE=sse npm start

# Using Node.js directly
# Start with stdio mode (default)
node index.js

# Start with SSE mode
MCP_MODE=sse node index.js

# Start with a different port if 3031 is already in use
PORT=3032 MCP_MODE=sse node index.js

# Start with environment variables
OPENWEATHERMAP_API_KEY=your_api_key MCP_MODE=sse node index.js
```

### Using with MCP Clients

The server provides a tool called `get_forecast` that can be used by MCP clients:

```javascript
// Example MCP client usage
const result = await use_mcp_tool({
  server_name: "weather-server",
  tool_name: "get_forecast",
  arguments: {
    city: "Paris,fr",
    days: 3
  }
});
```

### Testing with the Included Test Client

A simple test client is included to demonstrate how to interact with the server:

1. Start the server in one terminal:
   ```bash
   node index.js
   ```

2. Run the test client in another terminal:
   ```bash
   node test-client.js
   ```

The test client will send a request to get a 3-day weather forecast for Paris, France and display the response.

You can also pipe the test client to the server:
```bash
node test-client.js | node index.js
```

### Implementation Details

#### API Usage
The server uses different APIs based on the requested forecast period:
- For single day forecasts (`days=1`), it uses the current weather API:
  ```
  https://api.openweathermap.org/data/2.5/weather?q={city}&APPID={apikey}
  ```
- For multi-day forecasts (`days>1`), it uses the forecast API:
  ```
  https://api.openweathermap.org/data/2.5/forecast?q={city}&cnt={count}&appid={apikey}
  ```
  where `count` is calculated as `days * 8` (8 time slots per day, each representing 3 hours)

#### MCP Server Implementation
This project includes a custom MCP server implementation that:
- Provides a simple interface for registering and executing tools
- Supports both stdio and SSE transport modes
- Handles message parsing and response formatting
- Implements proper error handling and graceful shutdown

## 📚 API Reference

### Google ADK Integration

This project includes a Python-based agent built with Google's Agent Development Kit (ADK) that can answer natural language questions about weather and time in specific cities.

#### Setting Up the Google ADK Agent

1. Make sure you have installed the Google ADK:
   ```bash
   pip install google-adk
   ```

2. The agent is defined in `multi_tool_agent/agent.py` and uses the Gemini 2.0 Flash model.

3. The agent provides two main functions:
   - `get_weather`: Returns weather information for a specified city
   - `get_current_time`: Returns the current time in a specified city

#### Using the Google ADK Agent

You can interact with the Google ADK agent programmatically:

```python
from multi_tool_agent.agent import root_agent

# Get a response from the agent
response = root_agent.generate_content("What's the weather like in New York?")
print(response.text)

# Or use the agent's tools directly
from multi_tool_agent.agent import get_weather, get_current_time

weather_info = get_weather("New York")
time_info = get_current_time("New York")
```

#### Running the ADK Web Interface

To test and interact with your agent through a web interface:

1. Set the SSL certificate file environment variable (required for voice and video tests):
   ```bash
   export SSL_CERT_FILE=$(python -m certifi)
   ```

2. Run the ADK web interface:
   ```bash
   adk web
   ```

3. Open the URL provided (usually http://localhost:8000 or http://127.0.0.1:8000) in your browser.
   This connection stays entirely on your local machine.

4. Select the agent you want to interact with (e.g., `weather_time_agent`).

The web interface provides a convenient way to test your agent's responses to different queries and see how it handles various inputs without writing any code.

### Tool: `get_forecast`

Get weather forecast for a city for a specified number of days.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| city | string | Yes | - | City name with optional country code (e.g., "Paris,fr" or "Tokyo,jp") |
| days | integer | No | 1 | Number of days to forecast (1-5) |

#### Response Format

For current weather (days=1):

```json
{
  "status": "success",
  "data": {
    "location": {
      "name": "Paris",
      "country": "FR",
      "coordinates": {
        "lat": 48.8534,
        "lon": 2.3488
      }
    },
    "current": {
      "date": "2023-05-01T12:00:00.000Z",
      "temp": 18.5,
      "feels_like": 17.8,
      "humidity": 65,
      "pressure": 1012,
      "wind_speed": 3.6,
      "wind_direction": 220,
      "weather": {
        "main": "Clouds",
        "description": "scattered clouds",
        "icon": "03d"
      }
    }
  }
}
```

For multi-day forecast:

```json
{
  "status": "success",
  "data": {
    "location": {
      "name": "Paris",
      "country": "FR",
      "coordinates": {
        "lat": 48.8534,
        "lon": 2.3488
      }
    },
    "forecast": [
      {
        "date": "2023-05-01",
        "summary": {
          "avg_temp": 18.2,
          "avg_humidity": 68,
          "weather": {
            "main": "Clouds",
            "description": "scattered clouds",
            "icon": "03d"
          }
        },
        "hourly": [
          {
            "time": "2023-05-01T00:00:00.000Z",
            "temp": 15.2,
            "feels_like": 14.8,
            "humidity": 75,
            "pressure": 1013,
            "wind_speed": 2.1,
            "wind_direction": 210,
            "weather": {
              "main": "Clear",
              "description": "clear sky",
              "icon": "01n"
            }
          },
          // More hourly forecasts...
        ]
      },
      // More daily forecasts...
    ]
  }
}
```

## ❌ Error Handling

If an error occurs, the server will return a response with status "error" and an error message:

```json
{
  "status": "error",
  "error": "City not found"
}
```

Common errors include:
- Invalid API key
- City not found
- Network issues
- Invalid parameters

The server includes comprehensive error handling:
- Input validation for required parameters
- API error handling with meaningful messages
- Network error handling
- Graceful shutdown on process termination

## 📝 License

ISC

## 🙏 Acknowledgements

- [OpenWeatherMap API](https://openweathermap.org/api) for providing weather data
- [Model Context Protocol](https://modelcontext.org) for the MCP specification
- [Google Agent Development Kit (ADK)](https://github.com/google/agent-development-kit) for AI agent capabilities
