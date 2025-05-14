#!/bin/bash
# Script to run the Weather MCP Server in different modes

# Function to display usage information
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -m, --mode MODE     Set the transport mode (stdio, sse, or streamable-http, default: streamable-http)"
    echo "  -h, --host HOST     Set the host for HTTP mode (default: 127.0.0.1)"
    echo "  -p, --port PORT     Set the port for HTTP mode (default: 8000)"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  Run in streamable-http mode (default)"
    echo "  $0 -m sse  Run in HTTP mode with default host and port"
    echo "  $0 -m sse -p 8080   Run in HTTP mode on port 8080"
}

# Default values
MODE="streamable-http"
HOST="127.0.0.1"
PORT="8000"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -m|--mode)
            MODE="$2"
            shift
            shift
            ;;
        -h|--host)
            HOST="$2"
            shift
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if the required files exist
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Make sure you're running this script from the weather_mcp directory."
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    echo "Error: config.yaml not found. Please create it based on the example in the README."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import fastmcp, yaml, requests" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the server based on the selected mode
echo "Starting Weather MCP Server in ${MODE} mode..."

if [ "$MODE" = "sse" ] || [ "$MODE" = "streamable-http" ]; then
    echo "Server will be available at http://${HOST}:${PORT}"
    # Use the FastMCP CLI if available, otherwise fall back to direct execution
    if command -v fastmcp &> /dev/null; then
        # Set transport mode
        TRANSPORT_MODE="sse"
        fastmcp run main.py:mcp --transport "$TRANSPORT_MODE" --host "$HOST" --port "$PORT"
    else
        # Set environment variables and run directly
        export MCP_TRANSPORT_MODE="$MODE"
        export HTTP_HOST="$HOST"
        export HTTP_PORT="$PORT"
        # Also set legacy variables for backward compatibility
        export SSE_HOST="$HOST"
        export SSE_PORT="$PORT"
        python3 main.py
    fi
else
    python3 main.py
fi
