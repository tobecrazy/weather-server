from fastmcp import FastMCP
import requests
import logging
from datetime import datetime, timedelta

weather_mcp = FastMCP(name="Weather")
logger = logging.getLogger('weather_mcp.weather')

# Global variables for configuration
apikey = None
default_city = None

def set_config(api_key, city):
    """Set configuration values from main module"""
    global apikey, default_city
    apikey = api_key
    default_city = city
    logger.info(f"Weather plugin configured with default_city={default_city}")

@weather_mcp.resource()
def api_info():
    """Provide information about the weather API capabilities"""
    return {
        "name": "OpenWeatherMap API",
        "capabilities": [
            "Current weather for any city",
            "Weather forecasts up to 3 days in advance",
            "Temperature in Celsius",
            "Weather conditions description"
        ],
        "default_city": default_city,
        "api_configured": bool(apikey and apikey not in ["YOUR_OPENWEATHERMAP_API_KEY", "your_api_key_here"])
    }

# Helper to convert temperature from Kelvin to Celsius (if needed)
def kelvin_to_celsius(kelvin):
    return kelvin - 273.15

@weather_mcp.tool()
def get_weather(city: str = None, days: int = 0) -> dict:
    """
    Get weather for a city and day offset (0=today/current, 1=+1 day, ... up to 3).
    Returns a dictionary with date, temperature, and weather description.
    
    Args:
        city: City name, optionally with country code (e.g., "London,uk")
        days: Day offset (0=today/current, 1=tomorrow, 2=day after tomorrow, 3=three days from now)
        
    Returns:
        Dictionary with city, date, temperature (Celsius), and weather description
    """
    global apikey, default_city
    
    if not apikey:
        raise RuntimeError("API key not configured. Please set a valid OpenWeatherMap API key in config.yaml")
    
    city = city or default_city  # Use default if none provided
    
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("`days` parameter must be an integer 0-3")
        
    if days < 0 or days > 3:
        raise ValueError("`days` must be between 0 and 3")

    logger.info(f"Fetching weather for city={city}, days={days}")

    # Current weather (day=0) vs forecast (day>0)
    try:
        if days == 0:
            # Use the current weather API (free and supports city query)
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": apikey, "units": "metric"}
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"OpenWeatherMap API error: {response.status_code} {response.text}")
                raise RuntimeError(f"OpenWeatherMap API error: {response.text}")
                
            data = response.json()
            
            # Extract relevant info
            date = datetime.utcfromtimestamp(data["dt"]).strftime("%Y-%m-%d")
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            
        else:
            # Use daily forecast API. OWM supports up to 16 days via /forecast/daily.
            url = "https://api.openweathermap.org/data/2.5/forecast/daily"
            params = {"q": city, "cnt": days+1, "appid": apikey, "units": "metric"}
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                # If daily forecast API fails (it might require paid subscription),
                # fall back to the 5-day/3-hour forecast API and aggregate
                logger.warning("Daily forecast API failed, falling back to 5-day/3-hour forecast")
                return get_forecast_fallback(city, days)
                
            data = response.json()
            
            # The first element is today, so pick index=days
            entry = data["list"][days]
            date = datetime.utcfromtimestamp(entry["dt"]).strftime("%Y-%m-%d")
            temp = entry["temp"]["day"]
            desc = entry["weather"][0]["description"]
            
    except requests.RequestException as e:
        logger.error(f"Network error when calling OpenWeatherMap API: {str(e)}")
        raise RuntimeError(f"Failed to connect to weather service: {str(e)}")
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected API response format: {str(e)}")
        raise RuntimeError(f"Unexpected weather data format: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise RuntimeError(f"Error processing weather {str(e)}")

    result = {
        "city": city,
        "date": date,
        "temperature_C": temp,
        "weather": desc
    }
    logger.info(f"Result: {result}")
    return result

def get_forecast_fallback(city, days):
    """
    Fallback method using the 5-day/3-hour forecast API when daily forecast is unavailable.
    This is useful for free tier OpenWeatherMap accounts.
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": apikey, "units": "metric"}
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        logger.error(f"Fallback API error: {response.status_code} {response.text}")
        raise RuntimeError(f"Weather API error: {response.text}")
        
    data = response.json()
    
    # Calculate the target date
    target_date = datetime.now().date() + timedelta(days=days)
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    # Filter forecasts for the target date
    day_forecasts = [
        item for item in data["list"] 
        if item["dt_txt"].split()[0] == target_date_str
    ]
    
    if not day_forecasts:
        raise RuntimeError(f"No forecast data available for {target_date_str}")
    
    # Calculate average temperature and find most common weather description
    temps = [item["main"]["temp"] for item in day_forecasts]
    avg_temp = sum(temps) / len(temps)
    
    # Find most common weather description
    descriptions = [item["weather"][0]["description"] for item in day_forecasts]
    desc = max(set(descriptions), key=descriptions.count)
    
    result = {
        "city": city,
        "date": target_date_str,
        "temperature_C": round(avg_temp, 1),
        "weather": desc
    }
    
    logger.info(f"Fallback result: {result}")
    return result
