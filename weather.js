import fetch from 'node-fetch';
import config from './config.js';

/**
 * Fetch current weather data for a specific city
 * @param {string} city - City name (and optional country code)
 * @returns {Promise<Object>} - Weather data
 */
async function fetchCurrentWeather(city) {
  const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(city)}&APPID=${config.apiKey}&units=metric`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `API returned ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    return formatCurrentWeatherData(data);
  } catch (error) {
    console.error(`Error fetching current weather for ${city}:`, error.message);
    throw error;
  }
}

/**
 * Fetch forecast weather data for a specific city and number of days
 * @param {string} city - City name (and optional country code)
 * @param {number} days - Number of days to forecast (1-5)
 * @returns {Promise<Object>} - Weather forecast data
 */
async function fetchForecastWeather(city, days) {
  // Limit days to a reasonable range (1-5)
  const limitedDays = Math.min(Math.max(1, days), 5);
  
  // Each day has approximately 8 time slots (3-hour intervals)
  const count = limitedDays * 8;
  
  const url = `https://api.openweathermap.org/data/2.5/forecast?q=${encodeURIComponent(city)}&cnt=${count}&appid=${config.apiKey}&units=metric`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `API returned ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    return formatForecastData(data, limitedDays);
  } catch (error) {
    console.error(`Error fetching forecast for ${city}:`, error.message);
    throw error;
  }
}

/**
 * Format current weather data into a standardized structure
 * @param {Object} data - Raw API response
 * @returns {Object} - Formatted weather data
 */
function formatCurrentWeatherData(data) {
  return {
    location: {
      name: data.name,
      country: data.sys.country,
      coordinates: {
        lat: data.coord.lat,
        lon: data.coord.lon
      }
    },
    current: {
      date: new Date(data.dt * 1000).toISOString(),
      temp: data.main.temp,
      feels_like: data.main.feels_like,
      humidity: data.main.humidity,
      pressure: data.main.pressure,
      wind_speed: data.wind.speed,
      wind_direction: data.wind.deg,
      weather: {
        main: data.weather[0].main,
        description: data.weather[0].description,
        icon: data.weather[0].icon
      }
    }
  };
}

/**
 * Format forecast data into a standardized structure grouped by day
 * @param {Object} data - Raw API response
 * @param {number} days - Number of days requested
 * @returns {Object} - Formatted forecast data
 */
function formatForecastData(data, days) {
  const location = {
    name: data.city.name,
    country: data.city.country,
    coordinates: {
      lat: data.city.coord.lat,
      lon: data.city.coord.lon
    }
  };

  // Group forecast data by day
  const forecastsByDay = {};
  
  data.list.forEach(item => {
    const date = new Date(item.dt * 1000);
    const dayKey = date.toISOString().split('T')[0]; // YYYY-MM-DD
    
    if (!forecastsByDay[dayKey]) {
      forecastsByDay[dayKey] = [];
    }
    
    forecastsByDay[dayKey].push({
      time: date.toISOString(),
      temp: item.main.temp,
      feels_like: item.main.feels_like,
      humidity: item.main.humidity,
      pressure: item.main.pressure,
      wind_speed: item.wind.speed,
      wind_direction: item.wind.deg,
      weather: {
        main: item.weather[0].main,
        description: item.weather[0].description,
        icon: item.weather[0].icon
      }
    });
  });
  
  // Convert to array and limit to requested days
  const dailyForecasts = Object.entries(forecastsByDay)
    .map(([date, forecasts]) => {
      // Calculate daily averages
      const avgTemp = forecasts.reduce((sum, f) => sum + f.temp, 0) / forecasts.length;
      const avgHumidity = forecasts.reduce((sum, f) => sum + f.humidity, 0) / forecasts.length;
      
      // Find most common weather condition
      const weatherCounts = {};
      forecasts.forEach(f => {
        const weather = f.weather.main;
        weatherCounts[weather] = (weatherCounts[weather] || 0) + 1;
      });
      
      const mostCommonWeather = Object.entries(weatherCounts)
        .sort((a, b) => b[1] - a[1])[0][0];
      
      // Find a representative forecast for the most common weather
      const representativeForecast = forecasts.find(f => f.weather.main === mostCommonWeather);
      
      return {
        date,
        summary: {
          avg_temp: avgTemp,
          avg_humidity: avgHumidity,
          weather: representativeForecast.weather
        },
        hourly: forecasts
      };
    })
    .slice(0, days);
  
  return {
    location,
    forecast: dailyForecasts
  };
}

/**
 * Get weather data based on city and number of days
 * @param {string} city - City name (and optional country code)
 * @param {number} days - Number of days (default: 1)
 * @returns {Promise<Object>} - Weather data
 */
export async function getWeather(city, days = 1) {
  try {
    // Validate input
    if (!city) {
      throw new Error('City parameter is required');
    }
    
    // Parse days to integer
    const daysNum = parseInt(days, 10);
    
    if (isNaN(daysNum) || daysNum < 1) {
      throw new Error('Days parameter must be a positive number');
    }
    
    // Fetch appropriate data based on days requested
    if (daysNum === 1) {
      return await fetchCurrentWeather(city);
    } else {
      return await fetchForecastWeather(city, daysNum);
    }
  } catch (error) {
    // Rethrow with additional context
    throw new Error(`Weather data error: ${error.message}`);
  }
}

export default {
  getWeather
};
