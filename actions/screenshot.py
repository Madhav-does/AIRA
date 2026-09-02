"""
ARIA Screenshot Module
Captures the full screen and saves it as a PNG file.
"""

import pyautogui
import os
from datetime import datetime


def take_screenshot(save_dir: str = None) -> str | None:
    """
    Take a full-screen screenshot and save it.

    Args:
        save_dir: Directory to save the screenshot.
                  Defaults to the user's Desktop.

    Returns:
        Full file path of the saved screenshot, or None on error.
    """
    if save_dir is None:
        save_dir = os.path.expanduser('~/Desktop')

    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ARIA_Screenshot_{timestamp}.png'
    filepath = os.path.join(save_dir, filename)

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        print(f"[Screenshot] Saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"[Screenshot] Error: {e}")
        return None
