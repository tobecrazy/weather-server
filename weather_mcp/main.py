# Standard library imports
import os
import logging
import secrets
from http import HTTPStatus

# Third-party imports
import yaml
from fastmcp import FastMCP
from fastmcp.resources import TextResource
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Local imports
from utils.auth import validate_token, get_token_from_request

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

# Authentication configuration
behind_auth_proxy = os.getenv('BEHIND_AUTH_PROXY', 'false').lower() == 'true'
auth_enabled = os.getenv('AUTH_ENABLED', 'false').lower() == 'true' and not behind_auth_proxy
auth_secret_key = os.getenv('AUTH_SECRET_KEY')
auth_token_expiry = os.getenv('AUTH_TOKEN_EXPIRY')
if auth_token_expiry:
    try:
        auth_token_expiry = int(auth_token_expiry)
    except ValueError:
        auth_token_expiry = 86400  # Default to 24 hours
else:
    auth_token_expiry = 86400  # Default to 24 hours

# Log if we're behind an auth proxy
if behind_auth_proxy:
    logger.info("Running behind authentication proxy, disabling built-in authentication")

# If environment variables are not set, try config.yaml
if not all([apikey, default_city, mode]) or not auth_secret_key:
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
            
        # Load auth config if not set from environment
        if not auth_secret_key and config.get('auth', {}).get('secret_key'):
            auth_secret_key = config['auth']['secret_key']
            
        if not auth_enabled and config.get('auth', {}).get('enabled') is not None:
            auth_enabled = config['auth']['enabled']
            
        if not auth_token_expiry and config.get('auth', {}).get('token_expiry'):
            auth_token_expiry = config['auth']['token_expiry']
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
    
# Generate a random secret key if not provided and auth is enabled
if auth_enabled and not auth_secret_key:
    auth_secret_key = secrets.token_hex(32)
    logger.warning("No authentication secret key provided. Generated a random key for this session.")
    logger.warning("For production use, please set AUTH_SECRET_KEY in environment or config.yaml.")

# Log authentication configuration
if behind_auth_proxy:
    logger.info("Authentication is handled by external auth proxy")
elif auth_enabled:
    logger.info("Built-in authentication is enabled")
    if auth_token_expiry:
        logger.info(f"Token expiry: {auth_token_expiry} seconds")
else:
    logger.info("Authentication is disabled")
    
# Make config available to other modules
from plugins.weather import set_config
set_config(apikey, default_city)

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

# Define authentication middleware
# Define authentication function
def authenticate_request(request):
    """
    Authenticate a request using Bearer Token.
    
    Args:
        request: The request object
        
    Returns:
        Tuple of (is_authenticated, response)
        - is_authenticated: True if the request is authenticated, False otherwise
        - response: JSONResponse with error message if not authenticated, None otherwise
    """
    # Skip authentication if disabled
    if not auth_enabled:
        logger.info(f"Authentication disabled, allowing request to {request.url.path}")
        return True, None
        
    # Skip authentication for health check endpoint
    if request.url.path == "/mcp/info":
        logger.info(f"Skipping authentication for health check endpoint {request.url.path}")
        return True, None
    
    # Explicitly check for SSE endpoint
    if request.url.path == "/sse" or request.url.path.startswith("/sse/") or request.url.path.startswith("/sse?"):
        logger.info(f"SSE endpoint detected: {request.url.path}")
        
    # Log the request path for debugging
    logger.info(f"Authenticating request to {request.url.path}")
    
    # Extract and validate token
    token = get_token_from_request(request)
    if not token:
        logger.warning(f"Authentication failed: Missing Bearer Token for {request.url.path}")
        return False, JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: Missing Bearer Token"}
        )
        
    logger.info(f"Validating token: {token[:20]}...")
    is_valid, payload = validate_token(token, auth_secret_key)
    if not is_valid:
        logger.warning(f"Authentication failed: Invalid Bearer Token for {request.url.path}")
        return False, JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: Invalid Bearer Token"}
        )
        
    # Token is valid
    logger.info(f"Authentication successful for {request.url.path}")
    return True, None


if __name__ == "__main__":
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
            
            # Add authentication directly to the FastMCP server
            if auth_enabled:
                logger.info("Setting up authentication for SSE transport")
                
                # Since we can't directly modify the FastMCP transport classes,
                # we'll need to use a different approach
                
                # Let's create a custom ASGI middleware that adds authentication
                # to all requests, including the SSE endpoint
                
                from starlette.middleware import Middleware
                from starlette.middleware.base import BaseHTTPMiddleware
                
                class AuthMiddleware(BaseHTTPMiddleware):
                    async def dispatch(self, request, call_next):
                        # Skip authentication for health check endpoint
                        if request.url.path == "/mcp/info":
                            logger.info(f"Skipping authentication for health check endpoint {request.url.path}")
                            return await call_next(request)
                            
                        # Log the request path for debugging
                        logger.info(f"Authenticating request to {request.url.path}")
                        
                        # Extract and validate token
                        token = get_token_from_request(request)
                        if not token:
                            logger.warning(f"Authentication failed: Missing Bearer Token for {request.url.path}")
                            return JSONResponse(
                                status_code=401,
                                content={"error": "Unauthorized: Missing Bearer Token"}
                            )
                            
                        logger.info(f"Validating token: {token[:20]}...")
                        is_valid, payload = validate_token(token, auth_secret_key)
                        if not is_valid:
                            logger.warning(f"Authentication failed: Invalid Bearer Token for {request.url.path}")
                            return JSONResponse(
                                status_code=401,
                                content={"error": "Unauthorized: Invalid Bearer Token"}
                            )
                            
                        # Token is valid, proceed with the request
                        logger.info(f"Authentication successful for {request.url.path}")
                        return await call_next(request)
                
                # Try to add the middleware to the FastMCP app
                try:
                    # Get the underlying Starlette app
                    app = mcp._app
                    
                    # Add the middleware
                    from starlette.applications import Starlette
                    from starlette.routing import Route
                    
                    # Create a new Starlette app with the middleware
                    new_app = Starlette(
                        routes=app.routes,
                        middleware=[Middleware(AuthMiddleware)]
                    )
                    
                    # Replace the FastMCP app with our new app
                    mcp._app = new_app
                    
                    logger.info("Added authentication middleware to FastMCP app")
                except Exception as e:
                    logger.error(f"Failed to add authentication middleware: {str(e)}")
                    logger.warning("Authentication is enabled but not properly implemented")
                    logger.warning("The SSE endpoint will be accessible without authentication")
                    logger.warning("This is a security vulnerability that needs to be fixed")
                
            mcp.run(transport="sse", host=host, port=port)
        elif mode == 'streamable-http':
            # Get host and port from environment or use defaults
            host = os.getenv('HTTP_HOST', '127.0.0.1')
            port = int(os.getenv('HTTP_PORT', '3399'))
            path = os.getenv('HTTP_PATH', '/mcp')
            
            logger.info(f"Starting server with streamable-http transport at http://{host}:{port}{path}")
            logger.info(f"Stream endpoint will be available at http://{host}:{port}/mcp")
            
            # Add authentication for streamable-http transport
            if auth_enabled:
                logger.info("Setting up authentication for streamable-http transport")
                
                try:
                    # Import the transport classes
                    from fastmcp.transports.streamable_http import StreamableHttpTransport
                    from utils.auth_transport import AuthenticatedStreamableHttpTransport
                    
                    # Create a custom transport with authentication
                    transport = StreamableHttpTransport(host=host, port=port, path=path)
                    auth_transport = AuthenticatedStreamableHttpTransport(transport, auth_secret_key)
                    
                    # Run with the authenticated transport
                    logger.info("Running with authenticated streamable-http transport")
                    mcp.run(transport=auth_transport)
                except Exception as e:
                    logger.error(f"Failed to set up authenticated streamable-http transport: {str(e)}")
                    logger.warning("Falling back to standard streamable-http transport without authentication")
                    logger.warning("This is a security vulnerability that needs to be fixed")
                    mcp.run(transport="streamable-http", host=host, port=port, path=path)
            else:
                # Run with standard transport
                logger.info("Authentication is disabled, using standard streamable-http transport")
                mcp.run(transport="streamable-http", host=host, port=port, path=path)
        else:
            # Default to stdio mode
            logger.info("Starting server with stdio transport")
            mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error during server startup: {str(e)}")
        print(f"Error during server startup: {str(e)}")
        exit(1)
