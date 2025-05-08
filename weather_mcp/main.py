# Standard library imports
import os
import logging
import json
import asyncio
import uuid

# Third-party imports
import yaml
import uvicorn
from fastmcp import FastMCP
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, JSONResponse, HTMLResponse
from starlette.background import BackgroundTask

# Load environment variables from .env file if it exists
load_dotenv()

# Initialize logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    filename='weather.log',
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('weather_mcp')

# Load configuration - first try environment variables, then config.yaml
apikey = os.getenv('OPENWEATHERMAP_API_KEY')
default_city = os.getenv('DEFAULT_CITY')
mode = os.getenv('MCP_TRANSPORT_MODE')

# If environment variables are not set, try config.yaml
if not all([apikey, default_city, mode]):
    logger.info("Some configuration not found in environment variables, checking config.yaml")
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Only override if not already set from environment
        if not apikey:
            apikey = config.get('apikey')
        if not default_city:
            default_city = config.get('default_city')
        if not mode:
            mode = config.get('mode')
    except FileNotFoundError:
        logger.warning(f"Configuration file not found: {config_path}")
    except Exception as e:
        logger.warning(f"Error reading config file: {str(e)}")

# Set defaults for any missing configuration
if not apikey or apikey == 'YOUR_OPENWEATHERMAP_API_KEY' or apikey == 'your_api_key_here':
    logger.warning("API key not set or using default value. Please set a valid OpenWeatherMap API key.")
    
if not default_city:
    default_city = 'Beijing,cn'
    logger.info(f"Using default city: {default_city}")
    
if not mode:
    mode = 'stdio'
    logger.info(f"Using default transport mode: {mode}")
    
# Make config available to other modules
from plugins.weather import set_config
set_config(apikey, default_city)

# Create main MCP server
mcp = FastMCP(name="WeatherServer")

# No resources for now, just focus on the tools

# Mount the weather plugin (sub-server) for weather tools
from plugins.weather import weather_mcp
mcp.mount("weather", weather_mcp)

# Define HTTP streaming handler functions

# Global queue for streaming messages
message_queue = asyncio.Queue()
# Dictionary to store responses for each request
responses = {}

async def handle_root(request):
    """Handle requests to the root path"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weather MCP Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }
            .endpoint { margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>Weather MCP Server</h1>
        <p>This server provides weather information via the OpenWeatherMap API using the Model Context Protocol (MCP).</p>
        
        <div class="endpoint">
            <h2>Available Endpoints:</h2>
            <ul>
                <li><strong>/stream</strong> - HTTP streaming endpoint (GET)</li>
                <li><strong>/sse</strong> - Legacy SSE endpoint (GET)</li>
                <li><strong>/mcp</strong> - MCP request endpoint (POST)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <h2>Example Usage:</h2>
            <p>1. Connect to the streaming endpoint:</p>
            <pre>const eventSource = new EventSource('/stream');</pre>
            
            <p>2. Send a request to the MCP endpoint:</p>
            <pre>
fetch('/mcp', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Client-ID': clientId
  },
  body: JSON.stringify({
    tool: 'weather.get_weather',
    args: {
      city: 'London,uk'
    }
  })
});
            </pre>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

async def handle_options(request):
    """Handle OPTIONS requests for CORS preflight"""
    logger.info(f"Received OPTIONS request to {request.url.path}")
    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Client-ID",
        "Access-Control-Max-Age": "86400",  # 24 hours
    }
    
    return JSONResponse(content={}, headers=headers)

async def handle_catch_all(request):
    """Handle any request and log it for debugging"""
    logger.info(f"Received {request.method} request to {request.url.path}")
    logger.info(f"Headers: {request.headers}")
    
    # For POST requests, try to log the body
    if request.method == "POST":
        try:
            body = await request.body()
            logger.info(f"Body: {body}")
        except Exception as e:
            logger.info(f"Could not read body: {e}")
    
    # Return a 404 response
    return JSONResponse(
        {"error": f"Endpoint not found: {request.url.path}"},
        status_code=404
    )

async def handle_streaming(request):
    """Handle HTTP streaming connections"""
    # Log the request method and path
    logger.info(f"Received {request.method} request to {request.url.path}")
    
    # Handle POST requests (for FastMCP client)
    if request.method == "POST":
        try:
            # Parse the request body
            data = await request.json()
            logger.info(f"Received POST data to streaming endpoint: {data}")
            
            # Get client ID from header or generate a new one
            client_id = request.headers.get('X-Client-ID', str(uuid.uuid4()))
            
            # Return a success response for non-JSON-RPC requests
            return JSONResponse(
                {"status": "success", "message": "Streaming connection established", "client_id": client_id},
                status_code=200
            )
        except Exception as e:
            logger.error(f"Error processing POST request to streaming endpoint: {str(e)}")
            return JSONResponse(
                {"error": f"Error processing request: {str(e)}"},
                status_code=500
            )
    
    # Handle GET requests (for browser clients)
    client_id = request.query_params.get('client_id')
    if not client_id:
        client_id = str(uuid.uuid4())
    
    logger.info(f"New streaming connection established with client_id: {client_id}")
    
    async def event_generator():
        while True:
            message = await message_queue.get()
            # Only send messages intended for this client or broadcast messages
            if message.get('client_id') == client_id or message.get('broadcast', False):
                yield f"data: {json.dumps(message)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Client-ID": client_id
        }
    )

async def handle_mcp_request(request):
    """Handle MCP requests and send responses via HTTP streaming"""
    try:
        # Get client ID from header or generate a new one
        client_id = request.headers.get('X-Client-ID', str(uuid.uuid4()))
        
        # Parse the request
        data = await request.json()
        logger.info(f"Received MCP request from client {client_id}: {data}")
        
        # Handle MCP tool requests
        if 'tool' in data:
            tool_name = data['tool']
            args = data.get('args', {})
            
            # Split the tool name to get the server and tool
            parts = tool_name.split('.')
            if len(parts) != 2:
                return JSONResponse(
                    {"error": f"Invalid tool name format: {tool_name}. Expected format: server.tool"},
                    status_code=400
                )
            
            server_name, tool = parts
            
            # Get the server from the main MCP server
            server = mcp.servers.get(server_name)
            if not server:
                return JSONResponse(
                    {"error": f"Get the server from the main MCP server Server not found: {server_name}"},
                    status_code=404
                )
            
            # Get the tool from the server
            tool_func = server.tools.get(tool)
            if not tool_func:
                return JSONResponse(
                    {"error": f" Get the tool from the server, tool not found: {tool}"},
                    status_code=404
                )
            
            # Execute the tool
            try:
                result = tool_func(**args)
                
                # Send the result via streaming
                response = {
                    "client_id": client_id,
                    "request_id": data.get('request_id', str(uuid.uuid4())),
                    "result": result
                }
                
                # Store the response and send it via streaming
                responses[response["request_id"]] = response
                await message_queue.put(response)
                
                return JSONResponse(
                    {"status": "success", "request_id": response["request_id"]},
                    status_code=200
                )
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error executing tool {tool_name}: {error_message}")
                
                # Send the error via streaming
                response = {
                    "client_id": client_id,
                    "request_id": data.get('request_id', str(uuid.uuid4())),
                    "error": error_message
                }
                
                await message_queue.put(response)
                
                return JSONResponse(
                    {"status": "error", "error": error_message, "request_id": response["request_id"]},
                    status_code=500
                )
        else:
            return JSONResponse(
                {"error": "Invalid request format. 'tool' field is required."},
                status_code=400
            )
    except Exception as e:
        logger.error(f"Error processing MCP request: {str(e)}")
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"},
            status_code=500
        )

if __name__ == "__main__":
    # Log the raw value of the environment variable
    raw_mode = os.getenv('MCP_TRANSPORT_MODE')
    logger.info(f"MCP_TRANSPORT_MODE environment variable: {raw_mode}")
    
    # Log the value of the mode variable before lowercasing
    logger.info(f"Mode variable before lowercasing: {mode}")
    
    mode = mode.lower() if mode else 'stdio'
    logger.info(f"Starting server in {mode.upper()} mode")
    
    try:
        if mode == 'sse':  # Support all mode names
            # Get host and port from environment or use defaults
            host = os.getenv('HTTP_HOST', os.getenv('SSE_HOST', '127.0.0.1'))
            port = int(os.getenv('HTTP_PORT', os.getenv('SSE_PORT', '8000')))
            
            # For FastMCP compatibility
            logger.info("Using HTTP streaming mode with SSE transport")
            logger.info(f"HTTP server will be available at http://{host}:{port}")
            
            # Create routes for streaming and MCP
            routes = [
                Route("/", endpoint=handle_root, methods=["GET"]),             # Root path with information
                # Legacy endpoint for backward compatibility - accept all methods
                Route("/sse", endpoint=handle_streaming),
                Route("/mcp", endpoint=handle_mcp_request, methods=["POST"]),
                Route("/mcp", endpoint=handle_options, methods=["OPTIONS"]),   # OPTIONS handler for CORS preflight
                # Add routes for all possible FastMCP endpoints
                Route("/tools", endpoint=handle_mcp_request, methods=["POST"]),
                Route("/resources", endpoint=handle_mcp_request, methods=["GET", "POST"]),
                Route("/tools/{tool_name}", endpoint=handle_mcp_request, methods=["POST"]),
                Route("/resources/{resource_name}", endpoint=handle_mcp_request, methods=["GET"]),
                Route("/weather.get_weather", endpoint=handle_mcp_request, methods=["POST"]),
                Route("/weather/get_weather", endpoint=handle_mcp_request, methods=["POST"]),
                # Catch-all route for debugging
                Route("/{path:path}", endpoint=handle_catch_all, methods=["GET", "POST", "OPTIONS"]),
            ]
            
            # Create Starlette app with CORS middleware
            middleware = [
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST", "OPTIONS"],
                    allow_headers=["Content-Type", "X-Client-ID"],
                )
            ]
            starlette_app = Starlette(debug=True, routes=routes, middleware=middleware)
            
            # Start the server with uvicorn
            logger.info(f"Starting HTTP server on port {port}")
            uvicorn.run(starlette_app, host=host, port=port)
        else:
            # Default to stdio mode
            mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error during server startup: {str(e)}")
        print(f"Error during server startup: {str(e)}")
        exit(1)
