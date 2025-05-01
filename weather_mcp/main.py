from fastmcp import FastMCP
import yaml
import logging
import os
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

# Add a simple resource for server information
@mcp.resource()
def server_info():
    """Provide basic information about the weather server"""
    return {
        "name": "Weather MCP Server",
        "version": "1.0.0",
        "description": "MCP server providing weather information via OpenWeatherMap API",
        "default_city": default_city,
        "api_configured": bool(apikey and apikey not in ["YOUR_OPENWEATHERMAP_API_KEY", "your_api_key_here"])
    }

# Mount the weather plugin (sub-server) for weather tools
from plugins.weather import weather_mcp
mcp.mount("weather", weather_mcp)

if __name__ == "__main__":
    mode = mode.lower() if mode else 'stdio'
    logger.info(f"Starting server in {mode.upper()} mode")
    
    try:
        if mode == 'sse':
            # Get host and port from environment or use defaults
            host = os.getenv('SSE_HOST', '127.0.0.1')
            port = int(os.getenv('SSE_PORT', '8000'))
            logger.info(f"SSE server will be available at http://{host}:{port}")
            
            # Start in HTTP SSE mode
            mcp.run(transport="sse", host=host, port=port)
        else:
            # Default to stdio mode
            mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error during server startup: {str(e)}")
        print(f"Error during server startup: {str(e)}")
        exit(1)
