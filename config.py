"""
ARIA Configuration Manager
Handles loading and saving user settings to aria_config.json
"""

import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aria_config.json')

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "hotkey": "p",
    "summon_hotkey": "ctrl+space",
    "voice_speed": 175,
    "voice_volume": 0.9,
    "tts_engine": "edge_tts",
    "voice_name": "en-US-GuyNeural",
    "stt_language": "en-IN",
    "weather_city": "",
    "assistant_name": "ARIA",
    "user_name": "Madhav",
    "theme": "dark"
}


def load_config() -> dict:
    """Load configuration from file, merging with defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"[Config] Failed to save: {e}")
        return False
