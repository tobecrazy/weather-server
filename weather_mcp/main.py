# Standard library imports
import os
import logging
from http import HTTPStatus
import secrets # For placeholder if EXPECTED_TOKEN is empty
import sys # For initial stdout logging

# Third-party imports
import yaml
from fastmcp import FastMCP
from fastmcp.resources import TextResource
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException # Added
from starlette.middleware.base import BaseHTTPMiddleware # Added
from starlette.responses import JSONResponse, Response # Added
from typing import Callable # Added

# Load environment variables from .env file if it exists
load_dotenv()

# Initial logging to STDOUT for early messages (e.g. critical token issues)
_initial_log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
_initial_handlers = [logging.StreamHandler(sys.stdout)]
logging.basicConfig(
    level=getattr(logging, _initial_log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_initial_handlers,
    force=True # Ensure these handlers are used
)
_startup_logger = logging.getLogger('weather_mcp.startup')

# Define EXPECTED_TOKEN from MCP_SHARED_SECRET
# Default to an empty string if not set, to explicitly check for this condition.
EXPECTED_TOKEN = os.getenv("MCP_SHARED_SECRET", "")
if not EXPECTED_TOKEN:
    _startup_logger.critical(
        "CRITICAL: MCP_SHARED_SECRET environment variable is not set or is empty. "
        "For security, a random unmatchable token will be generated and used. "
        "No client will be able to authenticate until MCP_SHARED_SECRET is properly configured."
    )
    EXPECTED_TOKEN = secrets.token_hex(32) # Generate a secure, random token

# Main application logger - configured after initial checks and to a file
# This will effectively replace the initial stdout basicConfig for subsequent logs.
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    filename='weather.log',
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True # Replace initial basicConfig handlers
)
logger = logging.getLogger('weather_mcp') # Main application logger
logger.info("Application logging configured to file.")


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


# Authorization Middleware
class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_token: str, mcp_base_path: str = "/mcp"):
        super().__init__(app)
        self.expected_token = expected_token
        self.mcp_base_path = mcp_base_path
        self.logger = logging.getLogger('weather_mcp.AuthMiddleware')

        # This check is a safeguard. The global EXPECTED_TOKEN is already handled at startup.
        if not self.expected_token:
            self.logger.critical(
                "CRITICAL: AuthMiddleware initialized with an effectively empty expected_token. "
                "This should have been caught by startup logic. Using a new random token."
            )
            # This ensures self.expected_token is definitely not empty for the middleware's lifetime
            self.expected_token = secrets.token_hex(32)

        self.logger.info(f"AuthMiddleware initialized. Bypass paths configured for base: {self.mcp_base_path}")
        self.bypass_paths = [
            f"{self.mcp_base_path}/health_check",
            f"{self.mcp_base_path}/info",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.bypass_paths or \
           any(request.url.path.startswith(p_start) for p_start in ["/docs", "/redoc"]):
            self.logger.debug(f"Bypassing auth for exempt path: {request.url.path}")
            return await call_next(request)

        self.logger.debug(f"Applying auth for path: {request.url.path}")

        # This is a critical safeguard. If server's token is empty here, it's a major issue.
        if not self.expected_token: # Should be guaranteed non-empty by __init__ and startup logic
            self.logger.error(
                f"Server Misconfiguration: AuthMiddleware.expected_token is empty at dispatch for {request.url.path}."
            )
            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content={"detail": "Server Misconfiguration: Authorization system error."}
            )

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            self.logger.warning(f"Unauthorized: Missing Authorization header for path {request.url.path}")
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Missing Authorization header"}
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            self.logger.warning(f"Unauthorized: Invalid Authorization header format for path {request.url.path}")
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Invalid Authorization header format. Expected 'Bearer <token>'."}
            )

        token = parts[1]
        if not token: # Explicitly check if the client sent an empty token string
            self.logger.warning(f"Unauthorized: Client provided an empty token for path {request.url.path}")
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Client provided an empty token"}
            )

        if token != self.expected_token:
            self.logger.warning(f"Unauthorized: Invalid token provided by client for path {request.url.path}")
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Invalid token"}
            )

        self.logger.debug(f"Authorized: Token validated successfully for path {request.url.path}")
        response = await call_next(request)
        return response

# Wrapper for mcp.run to conditionally add AuthMiddleware
def create_run_wrapper(original_run_method, mcp_instance):
    logger_wrapper = logging.getLogger('weather_mcp.run_wrapper')

    def wrapped_mcp_run(*args, **kwargs):
        transport_mode = kwargs.get("transport")
        logger_wrapper.info(f"Wrapped mcp.run called. Transport mode: {transport_mode}")

        if transport_mode in ["sse", "streamable-http"]:
            logger_wrapper.info(f"Enabling AuthMiddleware for {transport_mode} mode.")

            actual_app = None
            # FastMCP objects are often FastAPI apps themselves.
            if isinstance(mcp_instance, FastAPI):
                actual_app = mcp_instance
            # Fallback: check if mcp_instance has an 'app' attribute that is a FastAPI app
            elif hasattr(mcp_instance, 'app') and isinstance(mcp_instance.app, FastAPI):
                actual_app = mcp_instance.app
            # Fallback: check mcp_instance.servers (if it's a FastMCP multi-server setup)
            elif hasattr(mcp_instance, 'servers'):
                for server_name, server_obj in mcp_instance.servers.items():
                    if hasattr(server_obj, 'app') and isinstance(server_obj.app, FastAPI):
                        actual_app = server_obj.app
                        logger_wrapper.info(f"Found FastAPI app in mcp.servers['{server_name}'].app")
                        break

            if not actual_app: # If no app found after checks
                logger_wrapper.error("Auth wrapper: Could not find FastAPI app instance to attach middleware.")

            if actual_app:
                # Check if middleware already added
                is_middleware_added = any(
                    issubclass(middleware.cls, AuthMiddleware) for middleware in actual_app.user_middleware
                )
                if not is_middleware_added:
                    mcp_base_path = getattr(mcp_instance, 'uri_prefix', '/mcp')
                    actual_app.add_middleware(AuthMiddleware, expected_token=EXPECTED_TOKEN, mcp_base_path=mcp_base_path)
                    logger_wrapper.info(f"AuthMiddleware added to FastAPI app instance. MCP Base Path: {mcp_base_path}")
                else:
                    logger_wrapper.info("AuthMiddleware already present in FastAPI app instance.")
            # else: # Already logged error if actual_app is None
            #    logger_wrapper.error("Auth wrapper: No FastAPI app instance found. Auth will not be active for HTTP transports.")
        else:
            logger_wrapper.info(f"Skipping AuthMiddleware for {transport_mode} mode.")

        return original_run_method(*args, **kwargs)

    return wrapped_mcp_run

# Create main MCP server
mcp = FastMCP(name="WeatherServer")

# Define a health check tool for Docker
@mcp.tool()
async def health_check() -> dict:
    """
    Health check endpoint for Docker.
    Returns a status indicating if the service is running.
    
    Returns:
        Dictionary with status information
    """
    return {
        "status": "healthy",
        "service": "weather-mcp-server"
    }

# Define a custom 404 error page tool
@mcp.tool()
async def get_404_page() -> dict:
    """
    Get a custom 404 error page.
    Returns HTML content for a nice 404 error page.
    
    Returns:
        Dictionary with HTML content for the 404 page
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>404 - Page Not Found</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                color: #333;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .container {
                text-align: center;
                background-color: white;
                border-radius: 8px;
                padding: 40px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                max-width: 500px;
            }
            h1 {
                font-size: 36px;
                margin-bottom: 10px;
                color: #e74c3c;
            }
            p {
                font-size: 18px;
                margin-bottom: 20px;
            }
            .back-link {
                color: #3498db;
                text-decoration: none;
                font-weight: bold;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            .weather-icon {
                font-size: 72px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="weather-icon">🌦️</div>
            <h1>404 - Page Not Found</h1>
            <p>Oops! The page you're looking for doesn't exist.</p>
            <p>This is a Weather MCP Server. It provides weather information through API endpoints.</p>
            <p>
                <a href="/" class="back-link">Go to Home</a>
            </p>
        </div>
    </body>
    </html>
    """
    return {
        "html": html_content
    }

# Define health check info as a TextResource for GET /mcp/info
health_info_text = '{"status": "healthy", "service": "weather-mcp-server"}'
health_resource = TextResource(
    uri="resource://mcp/info", # Changed to use resource:// scheme
    name="Health Check Information",
    text=health_info_text,
    mime_type="application/json",
    description="Provides a simple health status for the server via GET /mcp/info." # Description might need update later
)
mcp.add_resource(health_resource)

# No resources for now, just focus on the tools

# Mount the weather plugin (sub-server) for weather tools
from plugins.weather import weather_mcp
mcp.mount("weather", weather_mcp)

# Define HTTP streaming handler functions


if __name__ == "__main__":
    # Patch mcp.run before it's called
    if 'mcp' in globals() and isinstance(mcp, FastMCP):
        original_mcp_run = mcp.run
        mcp.run = create_run_wrapper(original_mcp_run, mcp)
        logger.info("mcp.run has been wrapped for authorization.")
    else:
        logger.error("Failed to wrap mcp.run: mcp object not found or not a FastMCP instance.")

    # Log the raw value of the environment variable
    raw_mode = os.getenv('MCP_TRANSPORT_MODE')
    logger.info(f"MCP_TRANSPORT_MODE environment variable: {raw_mode}")
    
    # Log the value of the mode variable before lowercasing
    logger.info(f"Mode variable before lowercasing: {mode}")
    
    mode = mode.lower() if mode else 'stdio'
    logger.info(f"Starting server in {mode.upper()} mode")
    
    try:
        if mode == 'sse':
            # Get host and port from environment or use defaults
            host = os.getenv('HTTP_HOST', os.getenv('SSE_HOST', '127.0.0.1'))
            port = int(os.getenv('HTTP_PORT', os.getenv('SSE_PORT', '3399')))
            
            logger.info(f"Starting server with SSE transport at http://{host}:{port}")
            mcp.run(transport="sse", host=host, port=port)
        elif mode == 'streamable-http':
            # Get host and port from environment or use defaults
            host = os.getenv('HTTP_HOST', '127.0.0.1')
            port = int(os.getenv('HTTP_PORT', '3399'))
            path = os.getenv('HTTP_PATH', '/mcp')
            
            logger.info(f"Starting server with streamable-http transport at http://{host}:{port}{path}")
            mcp.run(transport="streamable-http", host=host, port=port, path=path)
        else:
            # Default to stdio mode
            logger.info("Starting server with stdio transport")
            mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error during server startup: {str(e)}")
        print(f"Error during server startup: {str(e)}")
        exit(1)
