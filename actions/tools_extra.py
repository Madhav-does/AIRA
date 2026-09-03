"""
ARIA Extra Utility Tools
- Google Maps
- Wikipedia search
- Safe Math Calculator
- Native Windows Desktop Notifications
- Window Management (minimize all, maximize, switch)
- WhatsApp web draft
- Empty Recycle Bin
"""

import urllib.parse
import urllib.request
import json
import webbrowser
import subprocess
import ctypes
import re


def search_maps(query: str) -> str:
    """Search Google Maps for a place, address, restaurant, or directions."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/maps/search/{encoded}"
    webbrowser.open(url)
    print(f"[ExtraTools] Opened Google Maps: {query}")
    return f"Opened Google Maps for '{query}'."


def search_wikipedia(query: str) -> str:
    """Look up a summary of any topic, person, place, or concept from Wikipedia."""
    try:
        encoded = urllib.parse.quote(query)
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'ARIA-Assistant/1.0 (Windows)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            extract = data.get('extract', '')
            if extract:
                # Return first 2-3 sentences
                sentences = re.split(r'(?<=[.!?])\s+', extract)
                return " ".join(sentences[:3])
            return f"No summary found for '{query}' on Wikipedia."
    except Exception as e:
        print(f"[ExtraTools] Wikipedia error: {e}")
        # Fallback to opening Wikipedia in browser
        webbrowser.open(f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote_plus(query)}")
        return f"Opened Wikipedia search for '{query}'."


def calculate_math(expression: str) -> str:
    """Safely calculate a math expression like '45 * 12 + 100' or 'sqrt(144)'."""
    import math
    safe_dict = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
        'tan': math.tan, 'pi': math.pi, 'e': math.e,
        'pow': pow, 'log': math.log, 'log10': math.log10,
    }
    # Clean up expression
    cleaned = expression.replace('^', '**').replace('x', '*').replace('X', '*')
    try:
        # Evaluate safely without builtins
        result = eval(cleaned, {"__builtins__": {}}, safe_dict)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Could not calculate '{expression}': {e}"


def notify_desktop(title: str, message: str) -> str:
    """Show a native Windows desktop notification."""
    try:
        # PowerShell notification toast
        ps_cmd = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $toastXml = [xml]$template.GetXml()
        $toastXml.GetElementsByTagName('text')[0].AppendChild($toastXml.CreateTextNode('{title}')) | Out-Null
        $toastXml.GetElementsByTagName('text')[1].AppendChild($toastXml.CreateTextNode('{message}')) | Out-Null
        $notification = [Windows.UI.Notifications.ToastNotification]::new($template)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('ARIA Assistant').Show($notification)
        """
        subprocess.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_cmd],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return f"Notification shown: {title}"
    except Exception:
        return f"Reminder: {title} - {message}"


def send_whatsapp(contact_or_number: str = "", message: str = "") -> str:
    """Open WhatsApp with a pre-filled draft message."""
    encoded_msg = urllib.parse.quote(message)
    # Clean phone digits if a phone number was passed
    digits = re.sub(r'\D', '', contact_or_number)
    if len(digits) >= 10:
        url = f"https://web.whatsapp.com/send?phone={digits}&text={encoded_msg}"
    else:
        url = f"https://web.whatsapp.com/send?text={encoded_msg}"

    webbrowser.open(url)
    target = contact_or_number if contact_or_number else "chat"
    return f"Opened WhatsApp draft to {target}."


def minimize_all_windows() -> str:
    """Minimize all open windows to show the desktop (Win+D)."""
    try:
        import pyautogui
        pyautogui.hotkey('win', 'd')
    except Exception:
        # Use shell COM
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            shell.MinimizeAll()
        except Exception:
            pass
    return "Minimized all windows."


def maximize_window() -> str:
    """Maximize the currently active window (Win+Up)."""
    try:
        import pyautogui
        pyautogui.hotkey('win', 'up')
        return "Maximized active window."
    except Exception:
        return "Could not maximize window."


def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    try:
        # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        if result == 0:
            return "Recycle bin emptied."
        return "Recycle bin was already empty or could not be cleared."
    except Exception as e:
        return f"Error clearing recycle bin: {e}"
