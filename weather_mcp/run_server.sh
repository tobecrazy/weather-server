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
    echo "  -a, --auth          Enable authentication (default: disabled)"
    echo "  -s, --secret KEY    Set the authentication secret key"
    echo "  -g, --gen-token     Generate a token after starting the server"
    echo "  --proxy             Enable auth proxy (default: disabled)"
    echo "  --proxy-host HOST   Set the host for auth proxy (default: 127.0.0.1)"
    echo "  --proxy-port PORT   Set the port for auth proxy (default: 3397)"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  Run in streamable-http mode (default)"
    echo "  $0 -m sse           Run in HTTP mode with default host and port"
    echo "  $0 -m sse -p 8080   Run in HTTP mode on port 8080"
    echo "  $0 --proxy          Run with auth proxy enabled"
}

# Default values
MODE="streamable-http"
HOST="127.0.0.1"
PORT="3399"
AUTH_ENABLED="false"
AUTH_SECRET_KEY=""
GENERATE_TOKEN="false"
PROXY_ENABLED="false"
PROXY_HOST="127.0.0.1"
PROXY_PORT="3397"

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
        -a|--auth)
            AUTH_ENABLED="true"
            shift
            ;;
        -s|--secret)
            AUTH_SECRET_KEY="$2"
            shift
            shift
            ;;
        -g|--gen-token)
            GENERATE_TOKEN="true"
            shift
            ;;
        --proxy)
            PROXY_ENABLED="true"
            shift
            ;;
        --proxy-host)
            PROXY_HOST="$2"
            shift
            shift
            ;;
        --proxy-port)
            PROXY_PORT="$2"
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

# Generate a random secret key if authentication is enabled but no key is provided
if [ "$AUTH_ENABLED" = "true" ] && [ -z "$AUTH_SECRET_KEY" ]; then
    # Generate a random 32-character hex string
    AUTH_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    echo "Generated random secret key: $AUTH_SECRET_KEY"
fi

# Define a function to map transport modes to supported FastMCP transport modes
get_fastmcp_transport() {
    local mode="$1"
    case "$mode" in
        "sse")
            echo "sse"
            ;;
        "streamable-http")
            # streamable-http is an alias for streamable-http
            echo "streamable-http"
            ;;
        "stdio")
            echo "stdio"
            ;;
        *)
            # Default to stdio for unknown modes
            echo "stdio"
            ;;
    esac
}

# Run the server based on the selected mode
echo "Starting Weather MCP Server in ${MODE} mode..."

# Function to start the auth proxy
start_auth_proxy() {
    echo "Starting Auth Proxy at http://${PROXY_HOST}:${PROXY_PORT}"
    python3 auth_proxy.py --host "$PROXY_HOST" --port "$PROXY_PORT" &
    PROXY_PID=$!
    echo "Auth Proxy started with PID: $PROXY_PID"
    # Give the proxy a moment to start
    sleep 2
}

# Function to start the MCP server
start_mcp_server() {
    if [ "$MODE" = "sse" ] || [ "$MODE" = "streamable-http" ]; then
        echo "MCP Server will be available at http://${HOST}:${PORT}"
        # Use the FastMCP CLI if available, otherwise fall back to direct execution
        if command -v fastmcp &> /dev/null; then
            # Map the requested mode to a supported FastMCP transport mode
            TRANSPORT_MODE=$(get_fastmcp_transport "$MODE")
            
            # Log the transport mode being used
            if [ "$TRANSPORT_MODE" != "$MODE" ]; then
                echo "Using '$TRANSPORT_MODE' transport for '$MODE' mode"
            fi
            
            # If running behind auth proxy, set the environment variable
            if [ "$PROXY_ENABLED" = "true" ]; then
                export BEHIND_AUTH_PROXY="true"
            fi
            
            fastmcp run main.py:mcp --transport "$TRANSPORT_MODE" --host "$HOST" --port "$PORT" &
            MCP_PID=$!
        else
            # Set environment variables and run directly
            export MCP_TRANSPORT_MODE="$MODE"
            export HTTP_HOST="$HOST"
            export HTTP_PORT="$PORT"
            # Also set legacy variables for backward compatibility
            export SSE_HOST="$HOST"
            export SSE_PORT="$PORT"
            
            # If running behind auth proxy, set the environment variable
            if [ "$PROXY_ENABLED" = "true" ]; then
                export BEHIND_AUTH_PROXY="true"
                echo "Running MCP server behind auth proxy, disabling built-in authentication"
            fi
            
            # Set authentication environment variables if enabled
            if [ "$AUTH_ENABLED" = "true" ]; then
                export AUTH_ENABLED="true"
                export AUTH_SECRET_KEY="$AUTH_SECRET_KEY"
            fi
            
            python3 main.py &
            MCP_PID=$!
        fi
    else
        # If running behind auth proxy, set the environment variable
        if [ "$PROXY_ENABLED" = "true" ]; then
            export BEHIND_AUTH_PROXY="true"
            echo "Running MCP server behind auth proxy, disabling built-in authentication"
        fi
        
        # Set authentication environment variables if enabled
        if [ "$AUTH_ENABLED" = "true" ]; then
            export AUTH_ENABLED="true"
            export AUTH_SECRET_KEY="$AUTH_SECRET_KEY"
        fi
        
        python3 main.py &
        MCP_PID=$!
    fi
    echo "MCP Server started with PID: $MCP_PID"
}

# Start the services
if [ "$PROXY_ENABLED" = "true" ]; then
    # Start both services
    start_mcp_server
    start_auth_proxy
    echo "Services started. Access the Weather MCP Server through the Auth Proxy at http://${PROXY_HOST}:${PROXY_PORT}"
else
    # Start only the MCP server
    start_mcp_server
    echo "MCP Server started. Access directly at http://${HOST}:${PORT}"
fi

# Generate a token if requested
if [ "$GENERATE_TOKEN" = "true" ] && [ "$AUTH_ENABLED" = "true" ]; then
    echo "Generating authentication token..."
    sleep 1  # Give the server a moment to start
    python3 utils/generate_token.py --secret "$AUTH_SECRET_KEY"
fi

# Wait for Ctrl+C to terminate
echo "Press Ctrl+C to terminate all services"
wait
