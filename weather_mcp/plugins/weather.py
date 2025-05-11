from fastmcp import FastMCP
import requests
import logging
import asyncio
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

# No resources for now, just focus on the tools

# Helper to convert temperature from Kelvin to Celsius (if needed)
def kelvin_to_celsius(kelvin):
    return kelvin - 273.15

@weather_mcp.tool()
async def get_weather(city: str = None, days: int = 0) -> dict:
    """
    Get weather for a city and day offset (0=today/current, 1=+1 day, ... up to 15).
    Returns a dictionary with date, temperature (including min/max), and weather description.
    
    Args:
        city: City name, optionally with country code (e.g., "London,uk")
        days: Day offset (0=today/current, 1=tomorrow, ..., 15=fifteen days from now)
        
    Returns:
        Dictionary with city, date, temperature (Celsius), min/max temperature, and weather description
    """
    global apikey, default_city
    
    if not apikey:
        raise RuntimeError("API key not configured. Please set a valid OpenWeatherMap API key in config.yaml")
    
    city = city or default_city  # Use default if none provided
    
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("`days` parameter must be an integer 0-15")
        
    if days < 0 or days > 15:
        raise ValueError("`days` must be between 0 and 15")

    logger.info(f"Fetching weather for city={city}, days={days}")

    # Current weather (day=0) vs forecast (day>0)
    try:
        if days == 0:
            # Use the current weather API (free and supports city query)
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": apikey, "units": "metric"}
            
            # Use asyncio to run the request in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params)
            )
            
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
            
            # Use asyncio to run the request in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, params=params)
            )
            
            if response.status_code != 200:
                # If daily forecast API fails (it might require paid subscription),
                # fall back to the 5-day/3-hour forecast API and aggregate
                logger.warning("Daily forecast API failed, falling back to 5-day/3-hour forecast")
                return await get_forecast_fallback_async(city, days)
                
            data = response.json()
            
            # The first element is today, so pick index=days
            entry = data["list"][days]
            date = datetime.utcfromtimestamp(entry["dt"]).strftime("%Y-%m-%d")
            temp = entry["temp"]["day"]
            temp_min = entry["temp"]["min"]
            temp_max = entry["temp"]["max"]
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

    # For current weather (days=0), we need to handle min/max differently
    if days == 0:
        result = {
            "city": city,
            "date": date,
            "temperature_C": temp,
            "min_temperature_C": data["main"].get("temp_min", temp),
            "max_temperature_C": data["main"].get("temp_max", temp),
            "weather": desc
        }
    else:
        result = {
            "city": city,
            "date": date,
            "temperature_C": temp,
            "min_temperature_C": temp_min,
            "max_temperature_C": temp_max,
            "weather": desc
        }
    logger.info(f"Result: {result}")
    return result

async def get_forecast_fallback_async(city, days):
    """
    Fallback method using the 5-day/3-hour forecast API when daily forecast is unavailable.
    This is useful for free tier OpenWeatherMap accounts.
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": apikey, "units": "metric"}
    
    # Use asyncio to run the request in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: requests.get(url, params=params)
    )
    
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
    
    # Calculate average, min, and max temperature and find most common weather description
    temps = [item["main"]["temp"] for item in day_forecasts]
    avg_temp = sum(temps) / len(temps)
    min_temp = min(item["main"]["temp_min"] for item in day_forecasts)
    max_temp = max(item["main"]["temp_max"] for item in day_forecasts)
    
    # Find most common weather description
    descriptions = [item["weather"][0]["description"] for item in day_forecasts]
    desc = max(set(descriptions), key=descriptions.count)
    
    result = {
        "city": city,
        "date": target_date_str,
        "temperature_C": round(avg_temp, 1),
        "min_temperature_C": round(min_temp, 1),
        "max_temperature_C": round(max_temp, 1),
        "weather": desc
    }
    
    logger.info(f"Fallback result: {result}")
    return result

# Keep the original function for backward compatibility
def get_forecast_fallback(city, days):
    """
    Synchronous version of the fallback method for backward compatibility.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_forecast_fallback_async(city, days))
    finally:
        loop.close()
