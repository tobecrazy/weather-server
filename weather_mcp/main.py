# Standard library imports
import os
import logging
from http import HTTPStatus

# Third-party imports
import yaml
from fastapi import Request
from fastmcp import FastMCP
from dotenv import load_dotenv

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

@mcp.get("/mcp/info")
async def get_mcp_info(request: Request):
    return {"status": "healthy", "service": "weather-mcp-server", "path_accessed": "/mcp/info"}

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

# No resources for now, just focus on the tools

# Mount the weather plugin (sub-server) for weather tools
from plugins.weather import weather_mcp
mcp.mount("weather", weather_mcp)

# Define HTTP streaming handler functions


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
            port = int(os.getenv('HTTP_PORT', os.getenv('SSE_PORT', '8000')))
            
            logger.info(f"Starting server with SSE transport at http://{host}:{port}")
            mcp.run(transport="sse", host=host, port=port)
        elif mode == 'streamable-http':
            # Get host and port from environment or use defaults
            host = os.getenv('HTTP_HOST', '127.0.0.1')
            port = int(os.getenv('HTTP_PORT', '8000'))
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
