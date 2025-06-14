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

# Set specific loggers to DEBUG level if needed,
# ensuring debug messages from auth components are captured.
# This is useful if the global log_level is higher (e.g. INFO).
if getattr(logging, log_level, logging.INFO) > logging.DEBUG: # log_level is the string name from env
    logging.getLogger('weather_mcp.AuthMiddleware').setLevel(logging.DEBUG)
    # logging.getLogger('weather_mcp.run_wrapper').setLevel(logging.DEBUG) # run_wrapper is being removed
    logger.info("DEBUG level explicitly set for 'weather_mcp.AuthMiddleware'.")


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
        self.logger = logging.getLogger('weather_mcp.AuthMiddleware') # Get logger first
        self.logger.info(f"AuthMiddleware INSTANCE CREATED. ID: {id(self)}") # Added
        self.expected_token = expected_token
        self.mcp_base_path = mcp_base_path

        # This check is a safeguard. The global EXPECTED_TOKEN is already handled at startup.
        if not self.expected_token:
            self.logger.critical(
                f"Auth ID {id(self)}: CRITICAL: AuthMiddleware initialized with an effectively empty expected_token. " # Enhanced
                "This should have been caught by startup logic. Using a new random token."
            )
            # This ensures self.expected_token is definitely not empty for the middleware's lifetime
            self.expected_token = secrets.token_hex(32)

        self.bypass_paths = [ # Define bypass_paths before logging them
            f"{self.mcp_base_path}/health_check",
            f"{self.mcp_base_path}/info",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc"
        ]
        self.logger.info(f"AuthMiddleware ID {id(self)} configured. Expected token (snippet): '{self.expected_token[:5]}...', MCP Base: '{self.mcp_base_path}', Bypass Paths: {self.bypass_paths}") # Added

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        self.logger.info(f"AuthMiddleware ID {id(self)} DISPATCHING FOR: {request.method} {request.url.path}, Headers: {request.headers}") # Added

        self.logger.debug(f"Auth ID {id(self)}: Evaluating bypass for {request.url.path}. Against: {self.bypass_paths}") # Added
        if request.url.path in self.bypass_paths or \
           any(request.url.path.startswith(p_start) for p_start in ["/docs", "/redoc"]):
            self.logger.info(f"Auth ID {id(self)}: Path {request.url.path} BYPASSED authentication.") # Added
            return await call_next(request)

        self.logger.info(f"Auth ID {id(self)}: Path {request.url.path} NOT BYPASSED. Proceeding to auth checks.") # Added

        # This is a critical safeguard. If server's token is empty here, it's a major issue.
        if not self.expected_token: # Should be guaranteed non-empty by __init__ and startup logic
            self.logger.error(f"Auth ID {id(self)}: SERVER MISCONFIG (Expected Token Empty) for {request.url.path}.") # Enhanced
            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content={"detail": "Server Misconfiguration: Authorization system error."}
            )

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            self.logger.warning(f"Auth ID {id(self)}: UNAUTHORIZED (Header Missing) for {request.url.path}.") # Enhanced
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Missing Authorization header"}
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            self.logger.warning(f"Auth ID {id(self)}: UNAUTHORIZED (Header Format Invalid) for {request.url.path}.") # Enhanced
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Invalid Authorization header format. Expected 'Bearer <token>'."}
            )

        token = parts[1]
        if not token: # Explicitly check if the client sent an empty token string
            self.logger.warning(f"Auth ID {id(self)}: UNAUTHORIZED (Client Token Empty) for {request.url.path}.") # Enhanced
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Client provided an empty token"}
            )

        if token != self.expected_token:
            self.logger.warning(f"Auth ID {id(self)}: UNAUTHORIZED (Token Mismatch) for {request.url.path}. Client token (snippet): '{token[:5]}...', Expected (snippet): '{self.expected_token[:5]}...'") # Enhanced
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Unauthorized: Invalid token"}
            )

        self.logger.info(f"Auth ID {id(self)}: AUTHORIZED for {request.url.path}.") # Added
        response = await call_next(request)
        return response

# create_run_wrapper function is removed. AuthMiddleware will be added directly.

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
    # The mcp.run wrapper is removed. Middleware is added directly below.

    # Log the raw value of the environment variable
    raw_mode = os.getenv('MCP_TRANSPORT_MODE')
    logger.info(f"MCP_TRANSPORT_MODE environment variable: {raw_mode}")
    
    # Log the value of the mode variable before lowercasing
    logger.info(f"Mode variable before lowercasing: {mode}")
    
    mode = mode.lower() if mode else 'stdio'
    logger.info(f"Starting server in {mode.upper()} mode")

    # Directly add AuthMiddleware if mode is SSE or streamable-http
    if mode in ["sse", "streamable-http"]:
        if 'mcp' in globals() and isinstance(mcp, FastAPI):
            # Ensure AuthMiddleware and EXPECTED_TOKEN are defined/imported before this point
            mcp_base_path = getattr(mcp, 'uri_prefix', '/mcp')

            # Check if middleware already added to prevent duplicates if this block were ever re-entered (though unlikely here)
            is_middleware_added = any(
                issubclass(middleware.cls, AuthMiddleware) for middleware in mcp.user_middleware
            )
            if not is_middleware_added:
                logger.info(f"Attempting to add AuthMiddleware directly to FastMCP app instance for {mode} mode.")
                mcp.add_middleware(
                    AuthMiddleware,
                    expected_token=EXPECTED_TOKEN,
                    mcp_base_path=mcp_base_path
                )
                logger.info(f"AuthMiddleware directly ADDED to FastMCP instance. MCP Base Path: {mcp_base_path}")
                logger.debug(f"FastMCP app middleware stack after adding AuthMiddleware: {mcp.user_middleware}")
            else:
                logger.info(f"AuthMiddleware already present in FastMCP instance for {mode} mode.")
        else:
            logger.error(f"Failed to add AuthMiddleware: 'mcp' object not found or not a FastAPI instance for {mode} mode.")
    else:
        logger.info(f"Skipping AuthMiddleware setup for {mode} mode.")

    logger.info(f"Attempting to start server with mode: {mode}, Using mcp.run: {mcp.run}") # mcp.run is now the original
    
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
