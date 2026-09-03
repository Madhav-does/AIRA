"""
ARIA Clipboard & Typing Control
Read from clipboard, write to clipboard, type text.
"""

import subprocess
import time

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the Windows clipboard."""
    try:
        if PYPERCLIP_AVAILABLE:
            pyperclip.copy(text)
        else:
            # Fallback using PowerShell
            subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{text}"'],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print(f"[Clipboard] Copied: {text[:50]}...")
        return True
    except Exception as e:
        print(f"[Clipboard] Copy error: {e}")
        return False


def get_clipboard() -> str:
    """Get current clipboard text."""
    try:
        if PYPERCLIP_AVAILABLE:
            return pyperclip.paste()
        else:
            result = subprocess.run(
                ['powershell', '-command', 'Get-Clipboard'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip()
    except Exception as e:
        print(f"[Clipboard] Get error: {e}")
        return ""


def type_text(text: str, delay: float = 0.3) -> bool:
    """Type text into the currently focused window."""
    try:
        time.sleep(delay)
        if PYAUTOGUI_AVAILABLE:
            # Use pyperclip + paste for Unicode support (handles all characters)
            if PYPERCLIP_AVAILABLE:
                pyperclip.copy(text)
                import pyautogui as pag
                pag.hotkey('ctrl', 'v')
            else:
                pyautogui.write(text, interval=0.03)
        print(f"[Clipboard] Typed: {text[:50]}")
        return True
    except Exception as e:
        print(f"[Clipboard] Type error: {e}")
        return False
