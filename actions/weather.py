"""
ARIA Weather Module
Fetches live weather data using wttr.in — completely free, no API key needed.
"""

import requests


def get_weather(city: str = '') -> str:
    """
    Fetch current weather conditions.

    Args:
        city: City name (e.g. 'Delhi', 'Mumbai'). Empty string = auto-detect location.

    Returns:
        A human-readable weather string like "Delhi: ⛅ +32°C"
    """
    try:
        location = city.replace(' ', '+') if city else ''
        url = f"https://wttr.in/{location}?format=3"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        result = response.text.strip()
        print(f"[Weather] Got: {result}")
        return result
    except requests.ConnectionError:
        return "I couldn't connect to the weather service. Please check your internet."
    except requests.Timeout:
        return "The weather service took too long to respond. Please try again."
    except Exception as e:
        print(f"[Weather] Error: {e}")
        return "I wasn't able to fetch the weather right now."


def get_detailed_weather(city: str = '') -> str:
    """
    Fetch a slightly more detailed weather line with humidity and wind.

    Returns a string like: "Delhi: ⛅ +32°C, 45% humidity, 12km/h wind"
    """
    try:
        location = city.replace(' ', '+') if city else ''
        fmt = "%l: %c %t, %h humidity, %w wind"
        url = f"https://wttr.in/{location}?format={fmt}"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return response.text.strip()
    except Exception:
        return get_weather(city)
