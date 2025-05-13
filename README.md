# Weather Server MCP

A Model Context Protocol (MCP) server that provides weather information via the OpenWeatherMap API. This project demonstrates how to create and use MCP servers to extend AI assistant capabilities with real-time weather data.

## Project Overview

This project implements a local MCP server using FastMCP that allows AI assistants to access current weather conditions and forecasts for any city worldwide. The server connects to the OpenWeatherMap API and provides this data through a standardized MCP interface.

### Key Features

- **Current Weather**: Get real-time weather data for any city
- **Weather Forecasts**: Get forecasts for up to 15 days in the future
- **Temperature Data**: Includes current, minimum, and maximum temperatures
- **Multiple Transport Modes**: Supports both stdio and HTTP streaming modes
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Comprehensive Error Handling**: Robust error handling and logging

## Project Structure

```
weather-server/
├── .dockerignore              # Docker build exclusions
├── .env.example               # Example environment variables
├── .gitignore                 # Git exclusions
├── README.md                  # This file (root documentation)
│
└── weather_mcp/               # Main MCP server implementation
    ├── main.py                # Server entrypoint using FastMCP
    ├── plugins/               # MCP plugins directory
    │   └── weather.py         # Weather tool implementation
    ├── config.yaml.example    # Example configuration file
    ├── .env.example           # Example environment variables
    ├── requirements.txt       # Python dependencies
    ├── Dockerfile             # Docker container definition
    ├── docker-compose.yml     # Docker Compose configuration
    ├── run_server.sh          # Script to run the server
    └── README.md              # Detailed documentation for the MCP server
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenWeatherMap API key (sign up at [OpenWeatherMap](https://home.openweathermap.org/users/sign_up))

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/weather-server.git
   cd weather-server/weather_mcp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the server**:
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml and add your OpenWeatherMap API key
   ```

   Or use environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenWeatherMap API key
   ```

### Running the Server

#### Using the provided script:

```bash
# Make the script executable
chmod +x run_server.sh

# Run in stdio mode (default)
./run_server.sh

# Run in HTTP streaming mode
./run_server.sh -m sse
```

#### Using Docker:

```bash
# Using Docker Compose
docker-compose up -d

# Or build and run the Docker image directly
docker build -t weather-mcp-server .
docker run -d -p 8000:8000 -e OPENWEATHERMAP_API_KEY=your_api_key_here weather-mcp-server
```

## Using with AI Assistants

This MCP server can be integrated with AI assistants that support the Model Context Protocol. Once connected, the assistant can use the weather tool to get weather information.

### Example Tool Usage

```json
{
  "tool": "weather.get_weather",
  "args": {
    "city": "London,uk",
    "days": 0
  }
}
```

### Example Response

```json
{
  "city": "London,uk",
  "date": "2025-05-12",
  "temperature_C": 15.8,
  "min_temperature_C": 12.3,
  "max_temperature_C": 18.2,
  "weather": "scattered clouds"
}
```

## Transport Modes

The server supports two transport modes:

1. **stdio**: Standard input/output mode (default, good for CLI usage)
2. **sse**: HTTP server mode with streaming support (recommended for web clients)

## Docker Support

The project includes Docker support for easy deployment:

- **Dockerfile**: Defines the container image
- **docker-compose.yml**: Simplifies deployment with environment variables
- **.dockerignore**: Optimizes Docker builds

## Detailed Documentation

For more detailed information about the MCP server implementation, API details, and advanced usage, please refer to the [weather_mcp/README.md](weather_mcp/README.md) file.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FastMCP](https://github.com/modelcontextprotocol/fastmcp) - The Python framework for building MCP servers
- [OpenWeatherMap](https://openweathermap.org/) - Weather data provider
