"""
Weather API Client for iPIXEL Controller
"""

import requests
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger()


class WeatherAPI:
    """Handles interaction with OpenWeatherMap API"""
    
    def __init__(self, api_key: str):
        """
        Initialize Weather API client
        
        Args:
            api_key: OpenWeatherMap API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        
    def get_weather(self, location: str, units: str = "metric") -> Dict[str, Any]:
        """
        Fetch current weather data
        
        Args:
            location: City name or location string
            units: 'metric' for Celsius, 'imperial' for Fahrenheit
            
        Returns:
            Dictionary containing city, temp, feels_like, condition, description, humidity, wind_speed, and unit
        """
        logger.info(f"Fetching weather for: {location} (units={units})")
        
        url = f"{self.base_url}?q={location}&appid={self.api_key}&units={units}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                error_data = response.json()
                msg = error_data.get('message', 'Unknown error')
                logger.error(f"Weather API error: {msg}")
                raise ValueError(f"Weather API Error: {msg}")
                
            data = response.json()
            
            unit_symbol = "°C" if units == "metric" else "°F"
            
            result = {
                'city': data['name'],
                'temp': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'condition': data['weather'][0]['main'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'unit': unit_symbol
            }
            
            logger.info(f"Successfully fetched weather for {result['city']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            raise ConnectionError(f"Failed to connect to Weather service: {e}")
